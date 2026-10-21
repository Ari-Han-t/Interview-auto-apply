import unittest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base
from app.core.database import get_db, run_auto_migrations
from app.models.user import User
from app.models.job import Job, UserSavedJob, JobSourceSyncLog, JobSourceConfig
from app.api.auth import get_current_user
from app.services.scraper.adapters.registry import (
    get_adapter, 
    list_adapters, 
    get_sources_health, 
    route_url_to_adapter
)
from app.services.job_ingestion.deduplicator import compute_job_dedup_hash, merge_canonical_job_records
from app.services.job_ingestion.nl_query_parser import parse_natural_language_job_query
from app.services.job_ingestion.engine import JobIngestionEngine

# Test in-memory SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_job_discovery.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class TestJobDiscoveryAndIngestion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        run_auto_migrations(engine)

    @classmethod
    def tearDownClass(cls):
        Base.metadata.drop_all(bind=engine)

    def setUp(self):
        self.db = TestingSessionLocal()
        # Clean jobs and logs
        self.db.query(UserSavedJob).delete()
        self.db.query(JobSourceSyncLog).delete()
        self.db.query(JobSourceConfig).delete()
        self.db.query(Job).delete()
        self.db.query(User).delete()
        self.db.commit()

        # Create test user
        self.user = User(email="candidate@career.ai", hashed_password="pw", is_active=1)
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        def override_get_db():
            try:
                yield self.db
            finally:
                pass

        def override_get_current_user():
            return self.user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

    def tearDown(self):
        self.db.close()
        app.dependency_overrides.clear()

    def test_01_adapter_registry_and_auth_requirements(self):
        """Verifies that all 11 source adapters exist and blocked sources report explicit access requirements."""
        adapters = list_adapters()
        self.assertGreaterEqual(len(adapters), 10)
        
        # Check available adapters
        gh = get_adapter("greenhouse")
        self.assertIsNotNone(gh)
        self.assertEqual(gh.auth_status, "available")
        self.assertTrue(gh.can_fetch_catalog)

        ashby = get_adapter("ashby")
        self.assertIsNotNone(ashby)
        self.assertEqual(ashby.auth_status, "available")

        lever = get_adapter("lever")
        self.assertIsNotNone(lever)
        self.assertEqual(lever.auth_status, "available")

        # Check sources with auth / protection barriers
        indeed = get_adapter("indeed")
        self.assertIsNotNone(indeed)
        self.assertEqual(indeed.auth_status, "requires_auth")
        self.assertFalse(indeed.can_fetch_catalog)
        self.assertIn("Indeed Publisher API", indeed.access_requirement)

        wellfound = get_adapter("wellfound")
        self.assertIsNotNone(wellfound)
        self.assertEqual(wellfound.auth_status, "requires_auth")
        self.assertIn("Cloudflare Turnstile", wellfound.access_requirement)

        linkedin = get_adapter("linkedin")
        self.assertIsNotNone(linkedin)
        self.assertEqual(linkedin.auth_status, "limited")
        self.assertIn("LinkedIn Official Jobs API", linkedin.access_requirement)

    def test_02_url_routing_to_adapters(self):
        """Tests that direct URLs route to the appropriate specialized adapter."""
        gh_adapter = route_url_to_adapter("https://boards.greenhouse.io/stripe/jobs/12345")
        self.assertEqual(gh_adapter.source_id, "greenhouse")

        lever_adapter = route_url_to_adapter("https://jobs.lever.co/spotify/abc-123")
        self.assertEqual(lever_adapter.source_id, "lever")

        ashby_adapter = route_url_to_adapter("https://jobs.ashbyhq.com/ramp/xyz-789")
        self.assertEqual(ashby_adapter.source_id, "ashby")

        yc_adapter = route_url_to_adapter("https://www.ycombinator.com/companies/retool/jobs/456")
        self.assertEqual(yc_adapter.source_id, "yc")

        ishala_adapter = route_url_to_adapter("https://internshala.com/internship/detail/fullstack-intern-123")
        self.assertEqual(ishala_adapter.source_id, "internshala")

        generic_adapter = route_url_to_adapter("https://careers.uber.com/jobs/999")
        self.assertEqual(generic_adapter.source_id, "career_page")

    def test_03_deduplication_and_merging(self):
        """Tests deduplication hash generation and cross-platform information merging."""
        hash1 = compute_job_dedup_hash("Stripe Inc.", "Software Engineer Intern", "Remote", "internship")
        hash2 = compute_job_dedup_hash("Stripe", "Software Engineer Internship", "remote", "internship")
        self.assertEqual(hash1, hash2, "Normalized company and title variations must yield identical dedup hash")

        # Create base job
        job = Job(
            title="Backend Engineer",
            company="Acme Corp",
            url="https://acme.com/jobs/1",
            description="Acme backend job",
            tech_stack_json=["Python"],
            source="greenhouse",
            dedup_hash=hash1
        )
        self.db.add(job)
        self.db.commit()

        # Merge secondary posting from another platform
        new_data = {
            "source": "lever",
            "tech_stack_json": ["Python", "FastAPI", "PostgreSQL"],
            "salary_range": "$120,000 - $140,000",
            "compensation_min": 120000,
            "compensation_max": 140000,
            "currency": "USD"
        }
        merge_canonical_job_records(job, new_data)
        self.db.commit()

        self.assertIn("PostgreSQL", job.tech_stack_json)
        self.assertEqual(job.salary_range, "$120,000 - $140,000")
        self.assertIn("lever", job.source_provenance.get("cross_posted_sources", []))

    def test_04_natural_language_query_parser(self):
        """Verifies natural language query decomposition into structured parameters."""
        q = "Find backend engineering internships in India requiring Python, APIs, PostgreSQL, and cloud deployment."
        parsed = parse_natural_language_job_query(q)

        self.assertEqual(parsed["job_type"], "internship")
        self.assertEqual(parsed["location"], "India")
        self.assertIn("Python", parsed["skills"])
        self.assertIn("PostgreSQL", parsed["skills"])
        self.assertIn("APIs", parsed["skills"])
        self.assertIn("backend", parsed["role_keywords"].lower())

    def test_05_manual_job_creation_and_import_url(self):
        """Tests manual canonical job creation and direct URL import."""
        # 1. Manual Creation
        payload = {
            "title": "AI Research Intern",
            "company": "DeepMind Partner",
            "url": "https://deepmind.com/jobs/ai-intern",
            "location": "London, UK",
            "work_arrangement": "hybrid",
            "employment_type": "internship",
            "salary_range": "£45,000 - £60,000",
            "compensation_min": 45000,
            "compensation_max": 60000,
            "currency": "GBP",
            "tech_stack_json": ["PyTorch", "Python", "Transformers"],
            "required_skills_json": ["PyTorch", "Python"],
            "preferred_skills_json": ["Transformers"],
            "graduation_restrictions": ["2025", "2026"],
            "description": "Conduct cutting-edge research on agentic systems."
        }
        res = self.client.post("/api/v1/jobs/manual", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["title"], "AI Research Intern")
        self.assertEqual(data["company"], "DeepMind Partner")
        self.assertEqual(data["work_arrangement"], "hybrid")
        self.assertIn("2025", data["graduation_restrictions"])

    def test_06_bookmarking_and_saved_jobs_filter(self):
        """Tests saving/bookmarking jobs and filtering by saved status."""
        job1 = Job(title="Dev 1", company="Alpha", url="https://a.com", status="active", source="greenhouse")
        job2 = Job(title="Dev 2", company="Beta", url="https://b.com", status="active", source="lever")
        self.db.add_all([job1, job2])
        self.db.commit()

        # Save Dev 1
        res = self.client.post(f"/api/v1/jobs/{job1.id}/save", json={"notes": "Top choice"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["is_saved"])

        # Query all jobs
        all_res = self.client.get("/api/v1/jobs/")
        self.assertEqual(len(all_res.json()), 2)

        # Query saved_only
        saved_res = self.client.get("/api/v1/jobs/?saved_only=true")
        self.assertEqual(len(saved_res.json()), 1)
        self.assertEqual(saved_res.json()[0]["id"], job1.id)
        self.assertTrue(saved_res.json()[0]["is_saved"])

        # Unsave Dev 1
        unsave_res = self.client.delete(f"/api/v1/jobs/{job1.id}/save")
        self.assertEqual(unsave_res.status_code, 200)
        self.assertFalse(unsave_res.json()["is_saved"])

    def test_07_job_expiration_and_verification(self):
        """Tests marking past-deadline jobs as expired and live status probe."""
        past_date = datetime.utcnow() - timedelta(days=2)
        job = Job(
            title="Expired Role",
            company="Old Corp",
            url="https://old.com/job",
            status="active",
            deadline=past_date,
            is_expired=False,
            source="yc"
        )
        self.db.add(job)
        self.db.commit()

        # Run expiration update
        expired_count = JobIngestionEngine.update_expired_jobs(self.db)
        self.assertEqual(expired_count, 1)

        self.db.refresh(job)
        self.assertTrue(job.is_expired)
        self.assertEqual(job.status, "expired")

        # Verify endpoint status probe
        res = self.client.post(f"/api/v1/jobs/{job.id}/verify-status")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "expired")

    def test_08_sources_health_and_sync_logs(self):
        """Tests health inspection and sync logging across sources."""
        # 1. Health inspection
        res = self.client.get("/api/v1/jobs/sources/health")
        self.assertEqual(res.status_code, 200)
        health_data = res.json()
        self.assertGreaterEqual(len(health_data), 10)
        
        gh_info = next((h for h in health_data if h["source_id"] == "greenhouse"), None)
        self.assertIsNotNone(gh_info)
        self.assertTrue(gh_info["is_healthy"])

        indeed_info = next((h for h in health_data if h["source_id"] == "indeed"), None)
        self.assertIsNotNone(indeed_info)
        self.assertEqual(indeed_info["auth_status"], "requires_auth")

        # 2. Trigger sync on blocked source (verifies error isolation without crashing)
        sync_res = self.client.post("/api/v1/jobs/sync?source=indeed")
        self.assertEqual(sync_res.status_code, 200)
        self.assertEqual(sync_res.json()["result"]["status"], "blocked")

        # 3. Check logs
        log_res = self.client.get("/api/v1/jobs/sources/logs")
        self.assertEqual(log_res.status_code, 200)
        logs = log_res.json()
        self.assertGreaterEqual(len(logs), 1)
        self.assertEqual(logs[0]["source_id"], "indeed")

if __name__ == "__main__":
    unittest.main()
