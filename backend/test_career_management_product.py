import unittest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db
from app.models.base import Base
from app.models.user import User
from app.models.job import Job, UserSavedJob
from app.models.application import Application
from app.models.candidate import UserProfile, CandidateExperience, Project, UserPreference, CandidateCapability
from app.models.company_research import CompanyResearch
from app.models.resume import ResumeVersion
from app.api.auth import get_current_user


class TestCareerManagementProduct(unittest.TestCase):
    def setUp(self):
        # In-memory SQLite with StaticPool per test
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(self.engine)

        self.db = self.TestingSessionLocal()

        # Seed authenticated user
        self.user = User(
            id=101,
            email="candidate.pro@example.com",
            hashed_password="mock_hash",
            is_active=1,
        )
        self.db.add(self.user)
        self.db.commit()

        # Seed profile
        self.profile = UserProfile(
            user_id=self.user.id,
            full_name="Alex Mercer",
            email=self.user.email,
            phone="+1 555-0199",
            current_location="San Francisco, CA",
            preferred_locations=["San Francisco, CA", "Remote"],
        )
        self.db.add(self.profile)

        # Seed experience
        self.exp = CandidateExperience(
            user_id=self.user.id,
            company="Tech Corp",
            title="Senior Backend Engineer",
            start_date="2023-01",
            end_date="2025-01",
            description="Architected distributed Kafka pipelines processing 1M events/sec.",
            technologies=["Python", "FastAPI", "Kafka", "PostgreSQL"],
        )
        self.db.add(self.exp)

        # Seed project
        self.proj = Project(
            user_id=self.user.id,
            name="Raft Distributed Consensus",
            role="Creator",
            description="Implemented consensus state machine with heartbeat monitors.",
            technologies=["Rust", "Docker"],
            github="https://github.com/alex/raft",
        )
        self.db.add(self.proj)

        # Seed preferences
        self.prefs = UserPreference(
            user_id=self.user.id,
            preferred_roles=["Senior Backend Engineer", "Distributed Systems Engineer"],
            preferred_locations=["San Francisco, CA", "Remote"],
        )
        self.db.add(self.prefs)

        # Seed resume version
        self.resume_ver = ResumeVersion(
            id=1,
            user_id=self.user.id,
            name="Backend Infrastructure Specialist",
            storage_path="mock/path/resume.pdf",
            file_type="pdf",
            version_number=1,
        )
        self.db.add(self.resume_ver)

        # Seed jobs
        now = datetime.now(timezone.utc)
        self.job1 = Job(
            id=201,
            title="Senior Distributed Systems Engineer",
            company="CloudScale",
            location="Remote",
            source="greenhouse",
            url="https://cloudscale.io/jobs/201",
            required_skills_json=["Python", "Kafka", "PostgreSQL", "Docker"],
            tech_stack_json=["Python", "AWS", "Kubernetes"],
            requirements_json={"match_score": 92},
            created_at=now - timedelta(days=2),
        )
        self.job2 = Job(
            id=202,
            title="Infrastructure Engineer",
            company="Datastream",
            location="San Francisco, CA",
            source="linkedin",
            url="https://datastream.com/jobs/202",
            required_skills_json=["Python", "FastAPI", "Redis"],
            requirements_json={"match_score": 85},
            created_at=now - timedelta(days=5),
        )
        self.db.add_all([self.job1, self.job2])

        # Seed Applications
        self.app1 = Application(
            id=301,
            user_id=self.user.id,
            job_id=self.job1.id,
            status="Interview Scheduled",
            source="greenhouse",
            applied_at=now - timedelta(days=6),
            submission_confirmed=True,
            resume_version_id=self.resume_ver.id,
            interview_date=now + timedelta(days=3),
            interview_round="System Architecture Round",
            assessment_deadline=now + timedelta(days=2),
            follow_ups=[{"id": "fu-1", "title": "Review architecture doc", "due_date": (now + timedelta(days=1)).isoformat(), "completed": False}],
        )
        self.app2 = Application(
            id=302,
            user_id=self.user.id,
            job_id=self.job2.id,
            status="Applied",
            source="linkedin",
            applied_at=now - timedelta(days=3),
            submission_confirmed=True,
            resume_version_id=self.resume_ver.id,
        )
        self.db.add_all([self.app1, self.app2])

        # Seed company research
        self.research = CompanyResearch(
            id=401,
            job_id=self.job1.id,
            user_id=self.user.id,
            company_name="CloudScale",
            company_overview="CloudScale provides autonomous cloud orchestration platforms.",
            products_and_services=["AutoScale Mesh", "Telemetry Insights"],
            industry_and_business_model="B2B SaaS Enterprise Subscriptions",
            target_customers_or_markets="Tier-1 Cloud Engineering Organizations",
            engineering_challenges=["Sub-millisecond state coordination", "Zero-downtime rolling updates"],
            key_skills_in_position=["Distributed Systems", "Kafka", "Python", "Fault Tolerance"],
            candidate_relevant_experience=["Senior Backend Engineer experience with Kafka processing 1M events/sec"],
            interview_topics_to_prep=["Consensus algorithms", "Queue partitioning", "Idempotency"],
            verified_facts=[{"claim": "CloudScale is actively hiring for Senior Distributed Systems Engineer.", "source": "Official Job Board", "date": "2026-10-11"}],
            inferred_insights=[{"insight": "High emphasis on partition tolerance given cloud mesh offering.", "rationale": "Deduced from product architecture"}],
            unavailable_fields=["Internal microservice cluster headcount not disclosed"],
            sources=[{"label": "Official Job Posting"}],
            retrieval_date=now,
        )
        self.db.add(self.research)
        self.db.commit()

        # TestClient override
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
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_dashboard_metrics_endpoint(self):
        """Validates real metrics for opportunities, matches, saved, submissions, interviews, and deadlines."""
        resp = self.client.get("/api/v1/analytics/dashboard")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        metrics = data["metrics"]
        self.assertGreaterEqual(metrics["new_opportunities"], 2)
        self.assertGreaterEqual(metrics["strongly_matching"], 2)
        self.assertEqual(metrics["applications_submitted"], 2)
        self.assertEqual(metrics["interviews_scheduled"], 1)
        self.assertEqual(metrics["assessments_due"], 1)
        self.assertEqual(metrics["followups_due"], 1)

        # Onboarding checks
        onboarding = data["onboarding"]
        self.assertTrue(onboarding["has_profile"])
        self.assertTrue(onboarding["has_experience"])
        self.assertTrue(onboarding["has_projects"])
        self.assertTrue(onboarding["has_resume"])
        self.assertTrue(onboarding["has_preferences"])
        self.assertEqual(onboarding["readiness_percentage"], 100)

        # Upcoming events & recent applications
        self.assertGreaterEqual(len(data["upcoming_events"]), 1)
        self.assertEqual(data["upcoming_events"][0]["type"], "assessment")
        self.assertEqual(len(data["recent_applications"]), 2)

    def test_analytics_overview_empirical_calculations(self):
        """Validates pipeline distribution, conversion rates with explicit denominators, and disclaimers."""
        resp = self.client.get("/api/v1/analytics/overview")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # Pipeline distribution includes 13 canonical statuses
        pipeline = data["pipeline_distribution"]
        statuses = [p["status"] for p in pipeline]
        self.assertIn("Applied", statuses)
        self.assertIn("Interview Scheduled", statuses)
        self.assertIn("Offer Received", statuses)

        # Conversion rates with explicit denominators
        cr = data["conversion_rates"]
        self.assertEqual(cr["interview_rate"]["count"], 1)
        self.assertEqual(cr["interview_rate"]["denominator"], 2)
        self.assertEqual(cr["interview_rate"]["percentage"], 50.0)
        self.assertEqual(cr["interview_rate"]["label"], "1 of 2 submitted")
        self.assertTrue(cr["interview_rate"]["is_small_sample"])
        self.assertIsNotNone(cr["interview_rate"]["caveat"])

        # Weekly activity (8 weeks)
        self.assertEqual(len(data["weekly_activity"]), 8)

        # Technologies frequency
        self.assertGreaterEqual(len(data["top_technologies"]), 1)
        tech_names = [t["technology"] for t in data["top_technologies"]]
        self.assertIn("Python", tech_names)

        # Outcomes by source
        sources = [s["source"] for s in data["outcomes_by_source"]]
        self.assertIn("Greenhouse", sources)

        # Resume performance
        self.assertGreaterEqual(len(data["resume_performance"]), 1)
        self.assertFalse(data["resume_performance"][0]["is_statistically_adequate"])

    def test_company_research_listing_and_brief(self):
        """Validates company research list, search, and detailed brief retrieval."""
        # List endpoint
        list_resp = self.client.get("/api/v1/company-research/")
        self.assertEqual(list_resp.status_code, 200)
        list_data = list_resp.json()
        self.assertEqual(list_data["total_briefs"], 1)
        self.assertEqual(list_data["briefs"][0]["company_name"], "CloudScale")
        self.assertGreaterEqual(len(list_data["available_jobs"]), 1)

        # Search query filter
        search_resp = self.client.get("/api/v1/company-research/?q=CloudScale")
        self.assertEqual(search_resp.status_code, 200)
        self.assertEqual(len(search_resp.json()["briefs"]), 1)

        # Job brief retrieval
        brief_resp = self.client.get(f"/api/v1/company-research/job/{self.job1.id}")
        self.assertEqual(brief_resp.status_code, 200)
        brief = brief_resp.json()
        self.assertEqual(brief["company_name"], "CloudScale")
        self.assertGreaterEqual(len(brief["verified_facts"]), 1)
        self.assertGreaterEqual(len(brief["inferred_insights"]), 1)
        self.assertGreaterEqual(len(brief["unavailable_fields"]), 1)

    def test_candidate_data_export_and_clear(self):
        """Validates GDPR-compliant JSON data export and safe history reset."""
        # Data export
        export_resp = self.client.get("/api/v1/profile/export-all-data")
        self.assertEqual(export_resp.status_code, 200)
        export_data = export_resp.json()

        self.assertEqual(export_data["export_metadata"]["email"], self.user.email)
        self.assertEqual(export_data["candidate_profile"]["full_name"], "Alex Mercer")
        self.assertEqual(len(export_data["experiences"]), 1)
        self.assertEqual(len(export_data["projects"]), 1)
        self.assertEqual(export_data["applications_count"], 2)

        # Reset application data requires explicit confirm=true
        no_confirm_resp = self.client.delete("/api/v1/profile/clear-career-data")
        self.assertEqual(no_confirm_resp.status_code, 400)

        # Safe reset with confirm=true
        confirm_resp = self.client.delete("/api/v1/profile/clear-career-data?confirm=true")
        self.assertEqual(confirm_resp.status_code, 200)

        # Verify applications removed while profile remains
        remaining_apps = self.db.query(Application).filter(Application.user_id == self.user.id).count()
        self.assertEqual(remaining_apps, 0)
        prof_check = self.db.query(UserProfile).filter(UserProfile.user_id == self.user.id).first()
        self.assertIsNotNone(prof_check)
        self.assertEqual(prof_check.full_name, "Alex Mercer")


if __name__ == "__main__":
    unittest.main()
