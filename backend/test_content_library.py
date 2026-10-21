import io
import sys
import types
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parent))

config = types.ModuleType("app.core.config")
config.settings = types.SimpleNamespace(
    DATABASE_URL="sqlite:///:memory:",
    SECRET_KEY="content-library-test-key",
    ALGORITHM="HS256",
    ACCESS_TOKEN_EXPIRE_MINUTES=30,
    AUTH_DISABLED=False,
)
original_config = sys.modules.get("app.core.config")
sys.modules["app.core.config"] = config

try:
    from app.core.database import get_db
    from app.models import Base
    from app.models.user import User
    from app.models.candidate import (
        UserProfile,
        CandidateEducation,
        CandidateExperience,
        Project,
        Skill,
        UserSkill,
        Achievement,
        CourseCertification,
        CandidateLeadership,
        CandidateCoursework,
        CandidatePublication,
        CandidateCustomSection,
    )
    from app.models.resume import ResumeVersion
    from app.api import content_library
finally:
    if original_config is None:
        sys.modules.pop("app.core.config", None)
    else:
        sys.modules["app.core.config"] = original_config


class ContentLibraryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, autoflush=False)()

        self.user_a = User(email="candidate_a@example.test", hashed_password="pw_a")
        self.user_b = User(email="candidate_b@example.test", hashed_password="pw_b")
        self.db.add_all([self.user_a, self.user_b])
        self.db.commit()

        self.app = FastAPI()
        self.app.include_router(content_library.router, prefix="/api/v1/content-library")

        self.current_user = self.user_a

        def override_get_db():
            yield self.db

        def override_get_current_user():
            return self.current_user

        self.app.dependency_overrides[get_db] = override_get_db
        self.app.dependency_overrides[content_library.get_current_user] = override_get_current_user
        self.client = TestClient(self.app)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def test_01_all_11_modules_crud_and_fields(self):
        """Test full creation, retrieval, and updating across all 11 independent modules."""
        # 1. General Info
        gen_res = self.client.put("/api/v1/content-library/general-info", json={
            "full_name": "Taylor Swift",
            "preferred_name": "Tay",
            "email": "taylor@example.test",
            "phone": "+1 555 1234",
            "github": "https://github.com/taylor",
            "linkedin": "https://linkedin.com/in/taylor",
            "current_location": "New York, NY",
            "preferred_locations": ["New York, NY", "San Francisco, CA"],
            "bio": "Lead Software Engineer specializing in distributed architectures.",
            "availability": "Immediate",
            "degree": "Bachelors",
            "specialization": "Computer Science",
            "cgpa": 3.95,
            "graduation_year": 2024
        })
        self.assertEqual(gen_res.status_code, 200)
        get_gen = self.client.get("/api/v1/content-library/general-info").json()
        self.assertEqual(get_gen["preferred_name"], "Tay")
        self.assertEqual(get_gen["availability"], "Immediate")

        # 2. Education
        edu_res = self.client.post("/api/v1/content-library/educations", json={
            "institution": "Columbia University",
            "degree": "Master of Science",
            "specialization": "Machine Learning",
            "start_year": 2024,
            "graduation_year": 2026,
            "cgpa": 3.98,
            "gpa_scale": "4.0",
            "honors": "Dean's Honor List",
            "coursework": ["Deep Learning", "Distributed Systems"],
            "location": "New York, NY",
            "bullets": [{"text": "Teaching Assistant for CS4111 Databases", "is_selected": True}],
            "evidence_url": "https://columbia.edu/verify/123",
            "verification_status": "verified"
        })
        self.assertEqual(edu_res.status_code, 200)
        edu_id = edu_res.json()["id"]
        self.assertTrue(edu_res.json()["bullets"][0]["id"].startswith("b_"))

        # 3. Experience (with role types & selectable accomplishment bullets)
        exp_res = self.client.post("/api/v1/content-library/experiences", json={
            "company": "Stripe",
            "title": "Software Engineer Intern",
            "experience_type": "internship",
            "location": "San Francisco, CA",
            "start_date": "May 2024",
            "end_date": "August 2024",
            "responsibilities": "Owned payment reconciliation worker queues.",
            "contributions": "Designed idempotent batch processor in Go.",
            "metrics": "Processed $20M+ daily transaction volume with 0 dropped events.",
            "technologies": ["Go", "Redis", "Kafka", "PostgreSQL"],
            "bullets": [
                {"text": "Engineered idempotent transaction processor in Go handling $20M/day volume.", "is_selected": True, "metric": "$20M/day"},
                {"text": "Decreased queue reconciliation tail latency by 35%.", "is_selected": True, "metric": "35%"}
            ],
            "evidence_url": "https://linkedin.com/recommendation/123",
            "verification_status": "verified"
        })
        self.assertEqual(exp_res.status_code, 200)
        exp_id = exp_res.json()["id"]
        self.assertEqual(len(exp_res.json()["bullets"]), 2)

        # 4. Projects (comprehensive technical portfolio fields)
        proj_res = self.client.post("/api/v1/content-library/projects", json={
            "name": "AutoApply Agent",
            "problem": "Job hunting requires repetitive entry of identical candidate facts across portals.",
            "description": "Autonomous AI platform for managing candidate master profile and generating tailored materials.",
            "personal_contribution": "Architected backend API, data modeling, and LaTeX macro extraction pipeline.",
            "implementation": "FastAPI asynchronous service with SQLAlchemy, SQLite/PostgreSQL, and Next.js frontend.",
            "programming_languages": ["Python", "TypeScript"],
            "frameworks": ["FastAPI", "Next.js", "React"],
            "libraries": ["Pydantic", "SQLAlchemy", "TailwindCSS"],
            "databases": ["PostgreSQL", "SQLite", "Redis"],
            "apis": ["REST API", "GitHub API"],
            "ai_ml_techniques": ["RAG", "Prompt Engineering"],
            "deployment_technologies": ["Docker", "Vercel", "GitHub Actions"],
            "technical_challenges": "Handling custom TeX macros and zip archives safely without zip-slip vulnerabilities.",
            "verified_outcomes": ["Reduced profile assembly time by 90% in synthetic evaluations."],
            "github": "https://github.com/example/autoapply",
            "live_link": "https://autoapply.dev",
            "supporting_evidence": "https://github.com/example/autoapply/releases/tag/v1.0",
            "bullets": [
                {"text": "Architected resilient candidate profile engine supporting 11 distinct modules with 100% test coverage.", "is_selected": True, "metric": "100%"},
                {"text": "Constructed deterministic regex and heuristic technology taxonomy scanner across 7 domains.", "is_selected": True}
            ],
            "verification_status": "project_backed"
        })
        self.assertEqual(proj_res.status_code, 200)
        proj_id = proj_res.json()["id"]
        self.assertIn("Python", proj_res.json()["programming_languages"])
        self.assertIn("FastAPI", proj_res.json()["frameworks"])

        # 5. Skills (categorized with verification and proficiency)
        skill_res = self.client.post("/api/v1/content-library/skills", json={
            "name": "FastAPI",
            "category": "Frameworks",
            "confidence": 5,
            "years_used": 3.5,
            "proficiency_level": "Expert",
            "verification_status": "project_backed",
            "evidence_url": "https://github.com/example/autoapply",
            "notes": "Used in 4 production backend services."
        })
        self.assertEqual(skill_res.status_code, 200)

        # 6. Achievements & Awards
        ach_res = self.client.post("/api/v1/content-library/achievements", json={
            "title": "First Place - HackMIT 2024",
            "category": "hackathon",
            "issuer_or_event": "MIT Tech Club",
            "year_or_date": "2024",
            "description": "Won $10,000 grand prize among 1,200 participants for multimodal accessibility tool.",
            "impact_metrics": "1st place out of 300+ teams, 1200 participants",
            "url": "https://hackmit.org/winners-2024",
            "evidence_url": "https://devpost.com/software/winning-project",
            "verification_status": "verified"
        })
        self.assertEqual(ach_res.status_code, 200)
        ach_id = ach_res.json()["id"]

        # 7. Certifications & Training
        cert_res = self.client.post("/api/v1/content-library/certifications", json={
            "name": "AWS Certified Solutions Architect - Associate",
            "issuer": "Amazon Web Services",
            "issue_date": "2024-03",
            "expiry_date": "2027-03",
            "credential_id": "AWS-SAA-987654",
            "credential_url": "https://aws.amazon.com/verify/AWS-SAA-987654",
            "skills_covered": ["AWS", "EC2", "S3", "VPC", "IAM"],
            "verification_status": "certified"
        })
        self.assertEqual(cert_res.status_code, 200)
        cert_id = cert_res.json()["id"]

        # 8. Leadership & Extracurricular Activities
        lead_res = self.client.post("/api/v1/content-library/leadership", json={
            "organization": "ACM Student Chapter",
            "role": "President",
            "category": "club",
            "start_date": "2023",
            "end_date": "2024",
            "currently_active": False,
            "description": "Led collegiate computing organization of 450+ members.",
            "responsibilities": "Managed $15,000 budget and organized 12 technical workshops.",
            "bullets": [{"text": "Grew active membership by 65% through industry speaker series.", "is_selected": True, "metric": "65%"}],
            "evidence_url": "https://acm.columbia.edu/leadership",
            "verification_status": "verified"
        })
        self.assertEqual(lead_res.status_code, 200)
        lead_id = lead_res.json()["id"]

        # 9. Relevant Coursework
        cw_res = self.client.post("/api/v1/content-library/coursework", json={
            "course_name": "Distributed Operating Systems",
            "course_code": "CS4118",
            "institution": "Columbia University",
            "term_or_year": "Spring 2024",
            "grade": "A+",
            "skills_learned": ["Raft Consensus", "RPC", "Concurrency", "Linux Kernel"],
            "description": "Implemented Raft distributed consensus protocol from scratch in Go.",
            "topics_covered": ["Consensus", "Fault Tolerance", "Virtual Memory"],
            "verification_status": "verified"
        })
        self.assertEqual(cw_res.status_code, 200)
        cw_id = cw_res.json()["id"]

        # 10. Publications & Open Source Contributions
        pub_res = self.client.post("/api/v1/content-library/publications", json={
            "title": "Optimizing Tail Latency in Asynchronous RPC Message Brokers",
            "publication_type": "conference_paper",
            "venue_or_publisher": "IEEE Distributed Systems Conference (ICDCS)",
            "publication_date": "2024-06",
            "authors": ["Taylor Swift", "Dr. Jane Doe"],
            "url": "https://doi.org/10.1109/ICDCS.2024.12345",
            "doi_or_id": "10.1109/ICDCS.2024.12345",
            "description": "Proposed adaptive backpressure mechanism reducing tail latency by 28%.",
            "citation_count_or_metrics": "Cited by 6 publications",
            "bullets": [{"text": "Presented paper at ICDCS 2024 in Jersey City, NJ.", "is_selected": True}],
            "evidence_url": "https://ieeexplore.ieee.org/document/12345",
            "verification_status": "verified"
        })
        self.assertEqual(pub_res.status_code, 200)
        pub_id = pub_res.json()["id"]

        # 11. Custom Additional Sections
        custom_res = self.client.post("/api/v1/content-library/custom-sections", json={
            "section_title": "Patents",
            "title": "Method for Context-Aware Token Compression in Large Language Models",
            "subtitle": "US Patent Application 18/123,456",
            "date_or_year": "2024",
            "location": "US Patent and Trademark Office",
            "description": "Filed patent application covering KV cache reduction techniques.",
            "bullets": [{"text": "Achieved 3x memory reduction without perplexity loss.", "is_selected": True, "metric": "3x"}],
            "url": "https://patents.google.com/patent/US18123456",
            "verification_status": "verified"
        })
        self.assertEqual(custom_res.status_code, 200)
        custom_id = custom_res.json()["id"]

        # Verify list endpoints for all modules
        self.assertEqual(len(self.client.get("/api/v1/content-library/educations").json()), 1)
        self.assertEqual(len(self.client.get("/api/v1/content-library/experiences").json()), 1)
        self.assertEqual(len(self.client.get("/api/v1/content-library/projects").json()), 1)
        self.assertEqual(len(self.client.get("/api/v1/content-library/skills").json()), 1)
        self.assertEqual(len(self.client.get("/api/v1/content-library/achievements").json()), 1)
        self.assertEqual(len(self.client.get("/api/v1/content-library/certifications").json()), 1)
        self.assertEqual(len(self.client.get("/api/v1/content-library/leadership").json()), 1)
        self.assertEqual(len(self.client.get("/api/v1/content-library/coursework").json()), 1)
        self.assertEqual(len(self.client.get("/api/v1/content-library/publications").json()), 1)
        self.assertEqual(len(self.client.get("/api/v1/content-library/custom-sections").json()), 1)

    def test_02_record_duplication_with_fresh_bullet_ids(self):
        """Test record duplication appends (Copy) and re-keys bullet IDs to prevent collisions."""
        # Create a project with bullets
        proj_res = self.client.post("/api/v1/content-library/projects", json={
            "name": "Neural RAG Engine",
            "problem": "Slow search over complex documents",
            "bullets": [
                {"id": "b_orig1234", "text": "Implemented vector indexing with FAISS", "is_selected": True},
                {"id": "b_orig5678", "text": "Reduced query latency by 40%", "is_selected": True, "metric": "40%"}
            ]
        })
        orig_id = proj_res.json()["id"]

        # Duplicate
        dup_res = self.client.post(f"/api/v1/content-library/projects/{orig_id}/duplicate")
        self.assertEqual(dup_res.status_code, 200)
        dup_data = dup_res.json()

        self.assertNotEqual(dup_data["id"], orig_id)
        self.assertEqual(dup_data["name"], "Neural RAG Engine (Copy)")
        self.assertEqual(len(dup_data["bullets"]), 2)

        # Fresh bullet IDs generated
        orig_bullet_ids = {"b_orig1234", "b_orig5678"}
        dup_bullet_ids = {b["id"] for b in dup_data["bullets"]}
        self.assertTrue(all(b_id.startswith("b_") for b_id in dup_bullet_ids))
        self.assertEqual(len(orig_bullet_ids.intersection(dup_bullet_ids)), 0)

    def test_03_record_archiving_and_filtering(self):
        """Test toggling archive status and filtering active vs archived records."""
        exp_res = self.client.post("/api/v1/content-library/experiences", json={
            "company": "Legacy Systems Corp",
            "title": "Junior QA Engineer",
            "start_date": "2020-01",
            "end_date": "2021-01"
        })
        exp_id = exp_res.json()["id"]

        # Archive it
        arch_res = self.client.put(f"/api/v1/content-library/experiences/{exp_id}/archive", json={"is_archived": True})
        self.assertEqual(arch_res.status_code, 200)
        self.assertTrue(arch_res.json()["is_archived"])

        # Default query (include_archived=False) -> should be excluded
        active_list = self.client.get("/api/v1/content-library/experiences").json()
        self.assertEqual(len(active_list), 0)

        # include_archived=True -> should be returned
        all_list = self.client.get("/api/v1/content-library/experiences?include_archived=true").json()
        self.assertEqual(len(all_list), 1)
        self.assertEqual(all_list[0]["id"], exp_id)

        # Unarchive
        unarch_res = self.client.put(f"/api/v1/content-library/experiences/{exp_id}/archive", json={"is_archived": False})
        self.assertFalse(unarch_res.json()["is_archived"])
        self.assertEqual(len(self.client.get("/api/v1/content-library/experiences").json()), 1)

    def test_04_bullet_management_and_stable_ids(self):
        """Test adding and toggling individual resume accomplishment bullets."""
        proj = self.client.post("/api/v1/content-library/projects", json={
            "name": "Distributed Cache",
            "bullets": []
        }).json()
        proj_id = proj["id"]

        update_bullets_payload = {
            "bullets": [
                {"text": "Engineered consistent hashing cluster with zero downtime.", "is_selected": True, "metric": "zero downtime"},
                {"text": "Benchmarked performance using Locust reaching 100k RPS.", "is_selected": False, "metric": "100k RPS"}
            ]
        }
        res = self.client.put(f"/api/v1/content-library/projects/{proj_id}/bullets", json=update_bullets_payload)
        self.assertEqual(res.status_code, 200)
        bullets = res.json()["bullets"]
        self.assertEqual(len(bullets), 2)
        self.assertTrue(bullets[0]["id"].startswith("b_"))
        self.assertTrue(bullets[0]["is_selected"])
        self.assertFalse(bullets[1]["is_selected"])
        self.assertEqual(bullets[0]["metric"], "zero downtime")

    def test_05_project_import_and_technology_suggestions(self):
        """Test importing README text and receiving structured categorized technology suggestions for review."""
        sample_readme = """
# TrialSight AI Clinical Review

## Problem
Reviewing medical oncology trial protocols takes 10+ hours per study due to unstructured PDF literature.

## Architecture & Implementation
We built TrialSight AI using FastAPI, Python, and Next.js.
Documents are indexed in Redis and PostgreSQL using pgvector embeddings and FAISS similarity search.
Our backend calls OpenAI API and Groq models with LangChain for streaming extraction.
Deployed with Docker and AWS ECS with GitHub Actions CI/CD.

## Key Outcomes
- Accelerated trial protocol screening time by 75%.
- Processed 100,000+ medical evidence chunks with 99.4% precision.
"""
        import_req = {
            "text": sample_readme,
            "github_url": "https://github.com/Ari-Han-t/TrialSight",
            "name": "TrialSight AI"
        }
        res = self.client.post("/api/v1/content-library/projects/analyze-import", json=import_req)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["name"], "TrialSight AI")
        self.assertIn("medical oncology", data["problem"].lower())
        self.assertTrue(len(data["bullets"]) >= 2)
        self.assertTrue(any("75%" in b.get("text", "") for b in data["bullets"]))

        # Verify technology suggestions are classified by domain for candidate review
        suggested = data["suggested_technologies"]
        self.assertTrue(any(t["name"] == "Python" for t in suggested["programming_languages"]))
        self.assertTrue(any(t["name"] == "FastAPI" for t in suggested["frameworks"]))
        self.assertTrue(any(t["name"] == "Next.js" for t in suggested["frameworks"]))
        self.assertTrue(any(t["name"] == "PostgreSQL" for t in suggested["databases"]))
        self.assertTrue(any(t["name"] == "Redis" for t in suggested["databases"]))
        self.assertTrue(any(t["name"] == "FAISS" for t in suggested["databases"]))
        self.assertTrue(any(t["name"] == "Docker" for t in suggested["deployment_technologies"]))
        self.assertTrue(any(t["name"] == "AWS" for t in suggested["deployment_technologies"]))
        self.assertTrue(any(t["name"] == "LangChain" for t in suggested["ai_ml_techniques"]))

        # Status must be explicitly flagged as suggested for user review
        for tech_list in suggested.values():
            for item in tech_list:
                self.assertEqual(item["status"], "suggested_for_review")

    def test_06_separation_between_content_library_and_historical_resumes(self):
        """Updating or archiving items in Content Library must never silently mutate existing ResumeVersion records."""
        # 1. Create project in library
        proj = self.client.post("/api/v1/content-library/projects", json={
            "name": "Payment Gateway v1",
            "description": "Original description of payment gateway",
            "bullets": [{"id": "b_fixed1", "text": "Original bullet statement", "is_selected": True}]
        }).json()
        proj_id = proj["id"]

        # 2. Freeze an approved ResumeVersion referencing this project
        historical_resume = ResumeVersion(
            user_id=self.user_a.id,
            name="Senior Backend Resume (Approved)",
            storage_path="private/user_a/resume_v1.pdf",
            file_type="pdf",
            is_master=True,
            version_number=1,
            selected_projects=[proj_id],
            selected_bullets={str(proj_id): ["b_fixed1"]},
            parsed_json={
                "projects": [{"name": "Payment Gateway v1", "description": "Original description of payment gateway"}]
            }
        )
        self.db.add(historical_resume)
        self.db.commit()
        self.db.refresh(historical_resume)

        # 3. Candidate updates and archives the project in Content Library
        self.client.put(f"/api/v1/content-library/projects/{proj_id}", json={
            "name": "Payment Gateway v2 (Brand New System)",
            "description": "Completely revamped microservices architecture",
            "bullets": [{"id": "b_fixed1", "text": "Brand new rewritten bullet statement", "is_selected": True}],
            "is_archived": True
        })

        # 4. Verify historical resume was NOT silently altered
        self.db.refresh(historical_resume)
        self.assertEqual(historical_resume.parsed_json["projects"][0]["name"], "Payment Gateway v1")
        self.assertEqual(historical_resume.parsed_json["projects"][0]["description"], "Original description of payment gateway")
        self.assertEqual(historical_resume.selected_projects, [proj_id])
        self.assertEqual(historical_resume.selected_bullets, {str(proj_id): ["b_fixed1"]})

    def test_07_global_search_and_overview(self):
        """Test cross-module search and library stats overview."""
        self.client.post("/api/v1/content-library/projects", json={
            "name": "Cloud Microservices",
            "description": "Engineered with FastAPI and Docker"
        })
        self.client.post("/api/v1/content-library/skills", json={
            "name": "FastAPI",
            "category": "Frameworks"
        })
        self.client.post("/api/v1/content-library/experiences", json={
            "company": "FastAPI Solutions Inc",
            "title": "Backend Lead"
        })

        # Cross-module search
        search_res = self.client.get("/api/v1/content-library/search?q=FastAPI")
        self.assertEqual(search_res.status_code, 200)
        results = search_res.json()["results"]
        self.assertEqual(len(results["projects"]), 1)
        self.assertEqual(len(results["skills"]), 1)
        self.assertEqual(len(results["experience"]), 1)

        # Library Overview stats
        overview = self.client.get("/api/v1/content-library/overview").json()
        self.assertEqual(overview["modules"]["projects"]["active"], 1)
        self.assertEqual(overview["modules"]["skills"]["active"], 1)
        self.assertEqual(overview["modules"]["experience"]["active"], 1)

    def test_08_user_ownership_isolation(self):
        """Strict isolation: User B cannot access, modify, duplicate, or delete User A's library items."""
        # User A creates a project and coursework
        proj_a = self.client.post("/api/v1/content-library/projects", json={"name": "User A Private Project"}).json()
        proj_id = proj_a["id"]

        # Switch to User B
        self.current_user = self.user_b

        # User B search should find nothing
        b_search = self.client.get("/api/v1/content-library/search?q=Private").json()
        self.assertEqual(b_search["total_matches"], 0)

        # User B updating User A's project -> 404
        self.assertEqual(self.client.put(f"/api/v1/content-library/projects/{proj_id}", json={"name": "Hijacked"}).status_code, 404)

        # User B duplicating User A's project -> 404
        self.assertEqual(self.client.post(f"/api/v1/content-library/projects/{proj_id}/duplicate").status_code, 404)

        # User B archiving User A's project -> 404
        self.assertEqual(self.client.put(f"/api/v1/content-library/projects/{proj_id}/archive").status_code, 404)

        # User B deleting User A's project -> 404
        self.assertEqual(self.client.delete(f"/api/v1/content-library/projects/{proj_id}").status_code, 404)

        # Verify User A's record remains pristine
        self.current_user = self.user_a
        a_projects = self.client.get("/api/v1/content-library/projects").json()
        self.assertEqual(len(a_projects), 1)
        self.assertEqual(a_projects[0]["name"], "User A Private Project")


if __name__ == "__main__":
    unittest.main()
