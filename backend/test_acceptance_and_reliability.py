import io
import os
import sys
import json
import time
import uuid
import unittest
from pathlib import Path
from datetime import datetime, timezone

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import get_db, run_auto_migrations
from app.core import security
from app.core.rate_limiter import limiter
from app.models.base import Base
from app.models.user import User
from app.models.job import Job, UserSavedJob
from app.models.profile import Profile
from app.models.candidate import (
    UserProfile,
    CandidateEducation,
    CandidateExperience,
    Project,
    Skill,
    UserSkill,
    Achievement,
    CourseCertification,
    UserPreference,
    CandidateCapability
)
from app.models.resume import ResumeVersion
from app.models.cover_letter import CoverLetter
from app.models.application import Application
from app.models.application_history import ApplicationHistory
from app.models.company_research import CompanyResearch
from app.models.interview_prep import InterviewQuestion, MockInterviewSession
from app.services.resume_compiler.escaper import escape_latex, format_latex_url
from app.services.resume_compiler.compiler import compile_latex_securely, extract_and_validate_pdf_readability
from app.services.resume_compiler.assembly_engine import generate_assembly_plan
from app.services.resume_compiler.renderer import render_modular_resume
from app.services.job_ingestion.deduplicator import compute_job_dedup_hash, merge_canonical_job_records
from app.services.ai.eligibility import evaluate_eligibility
from app.services.ai.matcher import analyze_job_match
from app.services.company_research.service import generate_company_research
from app.services.interview_prep.service import generate_interview_questions_for_job, create_mock_session, evaluate_mock_answer


class AcceptanceAndReliabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Disable rate limiter during unit/acceptance tests
        limiter.enabled = False

    @classmethod
    def tearDownClass(cls):
        limiter.enabled = True

    def setUp(self):
        # Create an isolated in-memory SQLite database per test
        self.engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.SessionLocal()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        # Create primary test user
        self.test_email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
        self.test_password = "StrongPassword123!"
        self.user = User(
            email=self.test_email,
            hashed_password=security.get_password_hash(self.test_password),
            is_active=True
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        # Login and acquire token / cookies
        token = security.create_access_token(data={"sub": self.user.email})
        self.headers = {"Authorization": f"Bearer {token}"}
        self.cookies = {"access_token": f"Bearer {token}"}

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        Base.metadata.drop_all(self.engine)

    # -------------------------------------------------------------------------
    # 1. Database operations and migrations
    # -------------------------------------------------------------------------
    def test_database_operations_and_migrations(self):
        """Validates that schema inspection, auto-migrations, and table creation succeed without errors."""
        run_auto_migrations(self.engine)
        insp = inspect(self.engine)
        tables = set(insp.get_table_names())
        expected_tables = {
            "users", "user_profiles", "profiles", "jobs", "applications",
            "application_history", "resume_versions", "cover_letters",
            "candidate_educations", "candidate_experiences", "candidate_projects",
            "user_skills", "company_researches", "interview_questions", "mock_interview_sessions"
        }
        for t in expected_tables:
            self.assertIn(t, tables, f"Expected table {t} to exist in database.")

    # -------------------------------------------------------------------------
    # 2. Resume parsing
    # -------------------------------------------------------------------------
    def test_resume_parsing(self):
        """Tests parsing and entity extraction from LaTeX source text."""
        from app.services.ai.latex_parser import LatexResumeParser
        sample_tex = r"""
        \documentclass{article}
        \begin{document}
        \textbf{Jane Doe}
        jane.doe@example.com $|$ (555) 019-2831 $|$ github.com/janedoe $|$ linkedin.com/in/janedoe
        \section{Education}
        \textbf{University of California, Berkeley} \hfill 2020 -- 2024 \\
        B.S. in Computer Science \hfill GPA: 3.9/4.0
        \section{Experience}
        \textbf{Software Engineer Intern} \hfill June 2023 -- Aug 2023 \\
        Stripe \hfill San Francisco, CA
        \begin{itemize}
            \item Built distributed payment reconciliation microservice in Go and PostgreSQL.
            \item Reduced end-of-day batch processing latency by 35\%.
        \end{itemize}
        \section{Projects}
        \textbf{AutoApply Agent} $|$ Python, FastAPI, React
        \begin{itemize}
            \item Designed autonomous recruiting assistant with local LaTeX compilation.
        \end{itemize}
        \section{Skills}
        \textbf{Languages}: Python, Go, TypeScript, SQL \\
        \textbf{Frameworks}: FastAPI, React, Next.js, Docker
        \end{document}
        """
        parser = LatexResumeParser(sample_tex)
        data = parser.parse()
        self.assertIn("profile", data)
        self.assertIn("education", data)
        self.assertIn("experiences", data)
        self.assertIn("projects", data)
        self.assertIn("skills", data)
        self.assertEqual(data["profile"].get("email"), "jane.doe@example.com")
        self.assertTrue(len(data["experiences"]) >= 1)
        self.assertEqual(data["experiences"][0].get("company"), "Stripe")

    # -------------------------------------------------------------------------
    # 3. Project and profile CRUD
    # -------------------------------------------------------------------------
    def test_project_and_profile_crud(self):
        """Validates per-user record ownership and CRUD operations on profile and project portfolio."""
        # Create Project
        resp = self.client.post("/api/v1/profile/projects", json={
            "name": "Cloud Storage Engine",
            "description": "High-throughput object store",
            "technologies": ["Go", "Raft", "gRPC"],
            "role": "Lead Architect",
            "is_visible": True
        }, headers=self.headers, cookies=self.cookies)
        self.assertEqual(resp.status_code, 200)
        proj_id = resp.json()["id"]

        # Read Project
        lib_resp = self.client.get("/api/v1/content-library/modules", headers=self.headers, cookies=self.cookies)
        self.assertEqual(lib_resp.status_code, 200)
        projects = lib_resp.json()["data"]["projects"]
        self.assertTrue(any(p["id"] == proj_id for p in projects))

        # Update Project
        update_resp = self.client.put(f"/api/v1/profile/projects/{proj_id}", json={
            "name": "Distributed Storage Engine",
            "description": "Updated description",
            "technologies": ["Go", "Raft", "gRPC", "RocksDB"]
        }, headers=self.headers, cookies=self.cookies)
        self.assertEqual(update_resp.status_code, 200)
        self.assertEqual(update_resp.json()["name"], "Distributed Storage Engine")

        # Delete Project
        del_resp = self.client.delete(f"/api/v1/profile/projects/{proj_id}", headers=self.headers, cookies=self.cookies)
        self.assertEqual(del_resp.status_code, 200)

        # Verify deletion
        lib_resp2 = self.client.get("/api/v1/content-library/modules", headers=self.headers, cookies=self.cookies)
        self.assertFalse(any(p["id"] == proj_id for p in lib_resp2.json()["data"]["projects"]))

    # -------------------------------------------------------------------------
    # 4. Job normalization and deduplication
    # -------------------------------------------------------------------------
    def test_job_normalization_and_deduplication(self):
        """Verifies that job hashing, deduplication, and record merging work deterministically."""
        hash1 = compute_job_dedup_hash("Stripe", "Software Engineer", "San Francisco, CA", "fulltime")
        hash2 = compute_job_dedup_hash("stripe", "Software Engineer ", "San Francisco, CA", "Full-Time")
        self.assertEqual(hash1, hash2, "Deduplication hash should be case-insensitive and normalized.")

        job1 = Job(
            title="Software Engineer",
            company="Stripe",
            location="San Francisco, CA",
            employment_type="fulltime",
            url="https://stripe.com/jobs/1",
            description="Initial description",
            required_skills_json=["Python"],
            dedup_hash=hash1
        )
        self.db.add(job1)
        self.db.commit()

        incoming_parsed = {
            "title": "Software Engineer",
            "company": "Stripe",
            "location": "San Francisco, CA",
            "description": "Initial description with more details",
            "required_skills_json": ["Python", "Go"],
            "salary_range": "$140,000 - $180,000"
        }
        merge_canonical_job_records(job1, incoming_parsed)
        self.db.commit()
        self.assertIn("Go", job1.required_skills_json)
        self.assertEqual(job1.salary_range, "$140,000 - $180,000")

    # -------------------------------------------------------------------------
    # 5. Job-match calculations and eligibility
    # -------------------------------------------------------------------------
    def test_job_match_and_eligibility(self):
        """Tests deterministic candidate eligibility evaluation and match report structure."""
        job = Job(
            title="Backend Engineering Intern",
            company="Vercel",
            location="Remote",
            work_arrangement="remote",
            employment_type="internship",
            description="Looking for Python and Next.js developers graduating in 2025.",
            required_skills_json=["Python", "FastAPI"],
            graduation_restrictions=["2025", "2026"]
        )
        self.db.add(job)
        self.db.commit()

        # Set user profile graduation year
        u_prof = UserProfile(user_id=self.user.id, graduation_year=2025, current_location="Remote")
        self.db.add(u_prof)
        self.db.commit()

        eligibility = evaluate_eligibility(self.user.id, job.id, self.db, allow_requirement_extraction=False)
        self.assertIn("eligible", eligibility)
        self.assertIn("reason", eligibility)

        # Match report
        match_result = analyze_job_match(
            profile_text="Experienced in Python, FastAPI, and Next.js.",
            job_description="Backend developer with Python and FastAPI skills."
        )
        self.assertIn("match_percentage", match_result)
        self.assertIn("strengths", match_result)
        self.assertIn("missing_skills", match_result)
        self.assertTrue(0 <= match_result["match_percentage"] <= 100)

    # -------------------------------------------------------------------------
    # 6. Module selection and locked-section behavior
    # -------------------------------------------------------------------------
    def test_module_selection_and_locked_sections(self):
        """Verifies modular assembly planning, item relevance scoring, and user-locked section preservation."""
        candidate_data = {
            "profile": {"name": "Test Candidate", "email": "test@example.com"},
            "projects": [
                {"id": 101, "title": "Kafka Streamer", "technologies": ["Kafka", "Python"]},
                {"id": 102, "title": "React Dashboard", "technologies": ["React", "CSS"]},
            ],
            "experiences": [
                {"id": 201, "company": "Acme Corp", "title": "Backend Dev", "technologies": ["Python"]}
            ],
            "skills": {"Languages": [{"name": "Python"}, {"name": "Go"}]}
        }
        job_data = {
            "title": "Data Pipeline Engineer",
            "company": "DataCorp",
            "required_skills_json": ["Kafka", "Python"]
        }

        # User locks project 102 to be included explicitly
        user_locks = {
            "sections": {
                "projects": {"locked_ids": [102], "locked_order": 2}
            }
        }
        plan = generate_assembly_plan(
            candidate_data=candidate_data,
            job=job_data,
            user_locks=user_locks,
            target_page_length=1
        )
        self.assertIn("selected_modules", plan)
        proj_section = plan.get("sections", {}).get("projects", {})
        selected_ids = [item["id"] for item in proj_section.get("items", [])]
        self.assertIn(102, selected_ids, "Locked project ID 102 must be retained in the assembly plan.")

    # -------------------------------------------------------------------------
    # 7. LaTeX escaping and compilation
    # -------------------------------------------------------------------------
    def test_latex_escaping_and_compilation(self):
        """Tests escaping of dangerous primitives and characters, and sandboxed PDF generation."""
        untrusted_input = r"Engineered \write18{malicious_cmd} & 50% speedup with $USD and #1 rank in C++_code"
        escaped = escape_latex(untrusted_input)
        self.assertNotIn(r"\write18", escaped)
        self.assertIn(r"\%", escaped)
        self.assertIn(r"\$", escaped)
        self.assertIn(r"\#", escaped)
        self.assertIn(r"\_", escaped)

        # Compile valid LaTeX via ReportLab/pdflatex
        sample_latex = r"""
        \documentclass{article}
        \begin{document}
        \Huge \textbf{Candidate Name}
        \small candidate@example.com $|$ (555) 123-4567
        \section{Experience}
        \resumeSubheading{Software Engineer}{2023 - Present}{TechCorp}{San Francisco, CA}
        \resumeItem{Implemented low-latency microservices with 99.99\% uptime.}
        \end{document}
        """
        temp_pdf = f"data/temp/{self.user.id}/test_compile_{uuid.uuid4().hex[:6]}.pdf"
        ok, msg = compile_latex_securely(sample_latex, temp_pdf)
        self.assertTrue(ok, f"Compilation should succeed: {msg}")
        self.assertTrue(os.path.exists(temp_pdf))

        # Check readability
        readability = extract_and_validate_pdf_readability(temp_pdf)
        self.assertIn("is_readable", readability)
        self.assertIn("detected_sections", readability)
        if os.path.exists(temp_pdf):
            os.remove(temp_pdf)

    # -------------------------------------------------------------------------
    # 8. Resume and cover letter version persistence
    # -------------------------------------------------------------------------
    def test_resume_and_cover_letter_versioning(self):
        """Verifies immutable version creation, version incrementing, and parent linking."""
        # Create Resume Version 1
        rv1 = ResumeVersion(
            user_id=self.user.id,
            name="General Resume",
            storage_path="storage/resumes/1.pdf",
            file_type="pdf",
            version_number=1,
            is_master=True,
            latex_source="\\documentclass{article}..."
        )
        self.db.add(rv1)
        self.db.commit()

        # Create Resume Version 2 linked to Job and Version 1
        rv2 = ResumeVersion(
            user_id=self.user.id,
            name="Tailored for Stripe",
            storage_path="storage/resumes/2.pdf",
            file_type="pdf",
            version_number=2,
            is_master=False,
            parent_version_id=rv1.id,
            latex_source="\\documentclass{article}..."
        )
        self.db.add(rv2)
        self.db.commit()

        self.assertEqual(rv2.parent_version_id, rv1.id)
        self.assertEqual(rv2.version_number, 2)

        # Cover Letter versioning
        cl1 = CoverLetter(
            user_id=self.user.id,
            job_id=1,
            version_number=1,
            content="Initial cover letter draft.",
            style="concise"
        )
        self.db.add(cl1)
        self.db.commit()

        cl2 = CoverLetter(
            user_id=self.user.id,
            job_id=1,
            version_number=2,
            content="Refined cover letter draft.",
            style="persuasive",
            parent_version_id=cl1.id
        )
        self.db.add(cl2)
        self.db.commit()

        self.assertEqual(cl2.parent_version_id, cl1.id)
        self.assertEqual(cl2.version_number, 2)

    # -------------------------------------------------------------------------
    # 9. Company research source attribution
    # -------------------------------------------------------------------------
    def test_company_research_source_attribution(self):
        """Verifies epistemic honesty, verified facts, unavailable disclosures, and source tracking."""
        job = Job(
            title="Senior Platform Engineer",
            company="Datadog",
            location="New York, NY",
            url="https://datadog.com/careers/123",
            description="Scale distributed metrics collection infrastructure with Go and Kafka."
        )
        self.db.add(job)
        self.db.commit()

        research = generate_company_research(job.id, self.user.id, self.db, force_refresh=True)
        self.assertEqual(research.company_name, "Datadog")
        self.assertIsInstance(research.verified_facts, list)
        self.assertIsInstance(research.sources, list)
        self.assertIsInstance(research.unavailable_fields, list)
        self.assertTrue(len(research.sources) >= 1)
        self.assertEqual(research.sources[0]["url"], "https://datadog.com/careers/123")

    # -------------------------------------------------------------------------
    # 10. Interview question generation
    # -------------------------------------------------------------------------
    def test_interview_question_generation_and_evaluation(self):
        """Verifies interview question creation, STAR framework structure, and answer evaluation."""
        job = Job(
            title="Site Reliability Engineer",
            company="Cloudflare",
            location="Austin, TX",
            description="Manage global edge network resilience and incident response."
        )
        self.db.add(job)
        self.db.commit()

        questions = generate_interview_questions_for_job(job.id, self.user.id, force_refresh=True, db=self.db)
        self.assertTrue(len(questions) >= 3)
        categories = {q.category for q in questions}
        self.assertIn("behavioral", categories)

        # Verify behavioral STAR framework exists
        behavioral_q = next((q for q in questions if q.category == "behavioral"), None)
        self.assertIsNotNone(behavioral_q)
        self.assertIn("situation", behavioral_q.star_framework)

        # Mock interview session
        session = create_mock_session(self.user.id, job.id, category="all", db=self.db)
        self.assertEqual(session.status, "in_progress")
        self.assertTrue(len(session.questions_json) > 0)

        # Answer evaluation
        eval_res = evaluate_mock_answer(
            session_id=session.id,
            question_index=0,
            answer_text="I diagnosed the connection exhaustion using APM traces and fixed the pool limits.",
            user_id=self.user.id,
            db=self.db
        )
        self.assertIn("score", eval_res)
        self.assertIn("feedback", eval_res)

    # -------------------------------------------------------------------------
    # 11. Application status transitions and CRM persistence
    # -------------------------------------------------------------------------
    def test_application_status_transitions_and_history(self):
        """Verifies status transitions, timeline logging, and snapshot retention upon manual confirmation."""
        job = Job(
            title="Full Stack Developer",
            company="Figma",
            location="San Francisco, CA"
        )
        self.db.add(job)
        self.db.commit()

        app_record = Application(
            user_id=self.user.id,
            job_id=job.id,
            status="Preparing"
        )
        self.db.add(app_record)
        self.db.commit()

        # Update status to Ready to Apply
        resp = self.client.post(f"/api/v1/applications/{app_record.id}/status", json={
            "status": "Ready to Apply",
            "notes": "Materials finalized"
        }, headers=self.headers, cookies=self.cookies)
        self.assertEqual(resp.status_code, 200)

        # Confirm submission manually
        confirm_resp = self.client.post(f"/api/v1/applications/{app_record.id}/confirm-submission", json={
            "source": "Figma Careers Portal",
            "notes": "Submitted application directly through portal"
        }, headers=self.headers, cookies=self.cookies)
        self.assertEqual(confirm_resp.status_code, 200)

        # Verify persistence and timeline
        self.db.refresh(app_record)
        self.assertEqual(app_record.status, "Applied")
        self.assertTrue(app_record.submission_confirmed)

        history_resp = self.client.get(f"/api/v1/applications/{app_record.id}/history", headers=self.headers, cookies=self.cookies)
        self.assertEqual(history_resp.status_code, 200)
        events = history_resp.json()
        statuses_logged = [e["status"] for e in events]
        self.assertIn("Ready to Apply", statuses_logged)
        self.assertIn("Applied", statuses_logged)

    # -------------------------------------------------------------------------
    # 12. Analytics calculations
    # -------------------------------------------------------------------------
    def test_analytics_metrics_accuracy(self):
        """Verifies that dashboard and overview analytics reflect actual database records."""
        # Clean state has 0 applications
        dash_resp = self.client.get("/api/v1/analytics/dashboard", headers=self.headers, cookies=self.cookies)
        self.assertEqual(dash_resp.status_code, 200)
        data = dash_resp.json()
        self.assertEqual(data["metrics"]["submitted_applications"], 0)

        # Add a submitted application
        job = Job(title="Systems Engineer", company="Apple", location="Cupertino, CA")
        self.db.add(job)
        self.db.commit()

        app_sub = Application(
            user_id=self.user.id,
            job_id=job.id,
            status="Applied",
            submission_confirmed=True,
            applied_at=datetime.now(timezone.utc)
        )
        self.db.add(app_sub)
        self.db.commit()

        dash_resp2 = self.client.get("/api/v1/analytics/dashboard", headers=self.headers, cookies=self.cookies)
        self.assertEqual(dash_resp2.status_code, 200)
        data2 = dash_resp2.json()
        self.assertEqual(data2["metrics"]["submitted_applications"], 1)

    # -------------------------------------------------------------------------
    # 13. File access permissions & Security
    # -------------------------------------------------------------------------
    def test_file_access_permissions_and_security(self):
        """Tests that another user cannot view or modify the first user's private records."""
        # Create user 2
        user2 = User(
            email="user2@example.com",
            hashed_password=security.get_password_hash("OtherPass123!"),
            is_active=True
        )
        self.db.add(user2)
        self.db.commit()

        user2_token = security.create_access_token(data={"sub": user2.email})
        user2_headers = {"Authorization": f"Bearer {user2_token}"}
        user2_cookies = {"access_token": f"Bearer {user2_token}"}

        # User 1 creates an experience record
        exp1 = CandidateExperience(
            user_id=self.user.id,
            company="Confidential Corp",
            title="Security Engineer"
        )
        self.db.add(exp1)
        self.db.commit()

        # User 2 attempts to delete User 1's experience
        resp_del = self.client.delete(f"/api/v1/profile/experiences/{exp1.id}", headers=user2_headers, cookies=user2_cookies)
        self.assertEqual(resp_del.status_code, 404, "User 2 must receive 404 when attempting to mutate User 1's data.")

        # Test account export and deletion
        export_resp = self.client.get("/api/v1/auth/export-data", headers=self.headers, cookies=self.cookies)
        self.assertEqual(export_resp.status_code, 200)
        export_json = export_resp.json()
        self.assertEqual(export_json["user"]["email"], self.user.email)

        # Delete User 1's account
        del_acc_resp = self.client.request(
            "DELETE",
            "/api/v1/auth/delete-account",
            json={"confirm": True},
            headers=self.headers,
            cookies=self.cookies
        )
        self.assertEqual(del_acc_resp.status_code, 200)
        # Verify user is gone
        deleted_user = self.db.query(User).filter(User.id == self.user.id).first()
        self.assertIsNone(deleted_user)

    # -------------------------------------------------------------------------
    # 14. Full 12-Step End-to-End Acceptance Test
    # -------------------------------------------------------------------------
    def test_e2e_twelve_step_acceptance_pass(self):
        """
        Executes the mandatory 12-step end-to-end acceptance flow:
        1. Upload and review a LaTeX resume.
        2. Create candidate profile and project portfolio.
        3. Import a job from an operational source or labeled fixture.
        4. Generate and inspect an explainable match report.
        5. Build a job-specific resume by selecting and ordering modules.
        6. Compile, preview, and download the resume.
        7. Generate and save a personalized cover letter.
        8. Generate job-specific interview questions.
        9. Create an application and confirm submission manually.
        10. Verify that correct document versions are retained (snapshots).
        11. Change application status and confirm persistence after refresh.
        12. Verify that analytics reflect actual database records.
        """
        # Step 1: Upload and review a LaTeX resume
        sample_tex = r"""
        \documentclass{article}
        \begin{document}
        \textbf{Alex Candidate}
        alex@example.com $|$ (555) 019-9999 $|$ github.com/alexcand
        \section{Education}
        \textbf{MIT} \hfill 2021 -- 2025 \\
        B.S. Computer Science
        \section{Experience}
        \textbf{Software Engineering Intern} \hfill 2023 \\
        Linear \hfill Remote
        \begin{itemize}
            \item Built GraphQL real-time synchronization backend.
        \end{itemize}
        \section{Projects}
        \textbf{Distributed Cache} $|$ Go, Redis, Raft
        \begin{itemize}
            \item High availability multi-node cache.
        \end{itemize}
        \section{Skills}
        \textbf{Languages}: Python, Go, TypeScript
        \end{document}
        """
        upload_resp = self.client.post(
            "/api/v1/resume/upload",
            files={"file": ("resume.tex", io.BytesIO(sample_tex.encode("utf-8")), "application/x-tex")},
            headers=self.headers,
            cookies=self.cookies
        )
        self.assertEqual(upload_resp.status_code, 200)
        uploaded_resume_id = upload_resp.json()["id"]

        # Review and save to master profile
        review_resp = self.client.post("/api/v1/resume/review-and-save", json={
            "resume_id": uploaded_resume_id,
            "apply_to_master_profile": True,
            "extracted_data": upload_resp.json()["extracted_data"]
        }, headers=self.headers, cookies=self.cookies)
        self.assertEqual(review_resp.status_code, 200)

        # Step 2: Create a candidate profile and project portfolio
        prof_resp = self.client.put("/api/v1/profile/", json={
            "full_name": "Alex Candidate",
            "degree": "B.S. Computer Science",
            "graduation_year": 2025,
            "bio": "Systems and backend engineer passionate about distributed infrastructure."
        }, headers=self.headers, cookies=self.cookies)
        self.assertEqual(prof_resp.status_code, 200)

        proj_resp = self.client.post("/api/v1/profile/projects", json={
            "name": "Distributed Raft KV Store",
            "description": "Consensus-based key-value store with snapshotting",
            "technologies": ["Go", "Raft", "gRPC"],
            "role": "Creator"
        }, headers=self.headers, cookies=self.cookies)
        self.assertEqual(proj_resp.status_code, 200)

        # Step 3: Import a job from an explicitly labeled test fixture
        manual_job_resp = self.client.post("/api/v1/jobs/manual", json={
            "title": "Systems Infrastructure Intern",
            "company": "Cloudflare",
            "location": "San Francisco, CA",
            "work_arrangement": "hybrid",
            "employment_type": "internship",
            "description": "Build edge computing services with Go, Python, and distributed systems.",
            "required_skills_json": ["Go", "Python", "Distributed Systems"]
        }, headers=self.headers, cookies=self.cookies)
        self.assertEqual(manual_job_resp.status_code, 200)
        job_id = manual_job_resp.json()["id"]

        # Step 4: Generate and inspect an explainable match report
        analysis_resp = self.client.post(f"/api/v1/jobs/{job_id}/analyze", headers=self.headers, cookies=self.cookies)
        self.assertEqual(analysis_resp.status_code, 200)
        analysis_data = analysis_resp.json()
        self.assertIn("match_percentage", analysis_data)
        self.assertIn("strengths", analysis_data)

        # Step 5: Build a job-specific resume by selecting and ordering modules
        plan_resp = self.client.post(f"/api/v1/resume/plan/{job_id}", json={
            "target_page_length": 1,
            "template_name": "clean_ats"
        }, headers=self.headers, cookies=self.cookies)
        self.assertEqual(plan_resp.status_code, 200)
        assembly_plan = plan_resp.json()

        # Step 6: Compile, preview, and download the resume
        preview_resp = self.client.post("/api/v1/resume/preview", json={
            "assembly_plan": assembly_plan,
            "template_name": "clean_ats"
        }, headers=self.headers, cookies=self.cookies)
        self.assertEqual(preview_resp.status_code, 200)
        self.assertTrue(preview_resp.json()["success"])

        save_res_resp = self.client.post("/api/v1/resume/assemble-and-save", json={
            "job_id": job_id,
            "name": "Cloudflare Systems Tailored Resume",
            "assembly_plan": assembly_plan,
            "template_name": "clean_ats"
        }, headers=self.headers, cookies=self.cookies)
        self.assertEqual(save_res_resp.status_code, 200)
        saved_resume_id = save_res_resp.json()["id"]

        # Download PDF and TeX
        download_pdf = self.client.get(f"/api/v1/resume/versions/{saved_resume_id}/download-pdf", headers=self.headers, cookies=self.cookies)
        self.assertEqual(download_pdf.status_code, 200)
        self.assertEqual(download_pdf.headers["content-type"], "application/pdf")

        download_tex = self.client.get(f"/api/v1/resume/versions/{saved_resume_id}/download-tex", headers=self.headers, cookies=self.cookies)
        self.assertEqual(download_tex.status_code, 200)

        # Step 7: Generate and save a personalized cover letter
        gen_cl_resp = self.client.post(f"/api/v1/cover-letters/generate/{job_id}", json={
            "style": "concise",
            "candidate_motivation": "I admire Cloudflare's work on Workers and edge network reliability."
        }, headers=self.headers, cookies=self.cookies)
        self.assertEqual(gen_cl_resp.status_code, 200)
        cl_data = gen_cl_resp.json()
        self.assertIn("content", cl_data)

        save_cl_resp = self.client.post(f"/api/v1/cover-letters/version/{job_id}", json={
            "content": cl_data["content"],
            "style": "concise",
            "is_approved": True
        }, headers=self.headers, cookies=self.cookies)
        self.assertEqual(save_cl_resp.status_code, 200)
        saved_cl_id = save_cl_resp.json()["id"]

        # Step 8: Generate job-specific interview questions
        questions_resp = self.client.post(f"/api/v1/interview-prep/job/{job_id}/generate", json={
            "force_refresh": True
        }, headers=self.headers, cookies=self.cookies)
        self.assertEqual(questions_resp.status_code, 200)
        questions = questions_resp.json()
        self.assertTrue(len(questions) >= 3)

        # Step 9: Create an application and confirm submission manually
        init_app_resp = self.client.post(f"/api/v1/applications/initialize/{job_id}", headers=self.headers, cookies=self.cookies)
        self.assertEqual(init_app_resp.status_code, 200)
        app_id = init_app_resp.json()["application_id"]

        confirm_sub_resp = self.client.post(f"/api/v1/applications/{app_id}/confirm-submission", json={
            "source": "Official Cloudflare Greenhouse Portal",
            "notes": "Submitted with tailored resume and cover letter."
        }, headers=self.headers, cookies=self.cookies)
        self.assertEqual(confirm_sub_resp.status_code, 200)

        # Step 10: Verify that the correct document versions are retained (snapshots)
        materials_resp = self.client.get(f"/api/v1/applications/{app_id}/submitted-materials", headers=self.headers, cookies=self.cookies)
        self.assertEqual(materials_resp.status_code, 200)
        materials = materials_resp.json()
        self.assertTrue(materials["submission_confirmed"])
        self.assertIsNotNone(materials["submitted_resume_snapshot"])
        self.assertIsNotNone(materials["submitted_cover_letter_snapshot"])

        # Step 11: Change application status and confirm persistence after refresh
        status_update_resp = self.client.post(f"/api/v1/applications/{app_id}/status", json={
            "status": "Interview Scheduled",
            "notes": "Passed technical phone screen, scheduled virtual onsite."
        }, headers=self.headers, cookies=self.cookies)
        self.assertEqual(status_update_resp.status_code, 200)

        # Refresh from database via API
        get_app_resp = self.client.get(f"/api/v1/applications/job/{job_id}", headers=self.headers, cookies=self.cookies)
        self.assertEqual(get_app_resp.status_code, 200)
        self.assertEqual(get_app_resp.json()["status"], "Interview Scheduled")

        # Step 12: Verify that analytics reflect actual database records
        analytics_resp = self.client.get("/api/v1/analytics/dashboard", headers=self.headers, cookies=self.cookies)
        self.assertEqual(analytics_resp.status_code, 200)
        metrics = analytics_resp.json()["metrics"]
        self.assertEqual(metrics["submitted_applications"], 1)
        self.assertEqual(metrics["interviews_scheduled"], 1)


if __name__ == "__main__":
    unittest.main()
