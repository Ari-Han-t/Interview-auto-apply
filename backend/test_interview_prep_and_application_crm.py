import json
import os
import sys
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.models.base import Base
from app.models.user import User
from app.models.job import Job
from app.models.application import Application
from app.models.application_history import ApplicationHistory
from app.models.resume import ResumeVersion
from app.models.cover_letter import CoverLetter
from app.models.interview_prep import InterviewQuestion, MockInterviewSession
from app.models.candidate import (
    UserProfile,
    CandidateEducation,
    CandidateExperience,
    Project,
    UserSkill,
    Skill,
)
from app.services.interview_prep.service import (
    generate_interview_questions_for_job,
    create_mock_session,
    evaluate_mock_answer,
    INTERVIEW_CATEGORIES,
)
from app.api.auth import get_current_user
from app.api.applications import router as applications_router
from app.api.interview_prep import router as interview_prep_router


class TestInterviewPrepAndApplicationCRM(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.db = self.TestingSessionLocal()

        self.app = FastAPI()
        self.app.include_router(
            applications_router, prefix="/api/v1/applications", tags=["applications"]
        )
        self.app.include_router(
            interview_prep_router, prefix="/api/v1/interview-prep", tags=["interview_prep"]
        )

        def override_get_db():
            db = self.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        def override_get_current_user():
            db = self.TestingSessionLocal()
            try:
                user = db.query(User).filter(User.id == 1).first()
                if not user:
                    user = User(
                        id=1,
                        email="candidate@test.com",
                        hashed_password="hashed_pw_test",
                    )
                    db.add(user)
                    db.commit()
                return user
            finally:
                db.close()

        self.app.dependency_overrides[get_db] = override_get_db
        self.app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(self.app)

        # Patch get_llm to avoid external API calls during testing
        self.llm_patcher = mock.patch("app.services.interview_prep.service.get_llm")
        mock_get_llm = self.llm_patcher.start()
        mock_get_llm.side_effect = RuntimeError("Offline LLM test fallback")

        # Create test user
        self.user = User(
            id=1,
            email="candidate@test.com",
            hashed_password="hashed_pw_test",
        )
        self.db.add(self.user)

        self.job = Job(
            id=101,
            title="Lead Backend Infrastructure Engineer",
            company="Stripe",
            description=(
                "We are seeking an engineer to build payment processing distributed infrastructure. "
                "Requirements: Go, Python, PostgreSQL, Kafka, distributed systems, system design, high availability."
            ),
            required_skills_json=["Go", "Python", "Kafka", "PostgreSQL", "Distributed Systems"],
            url="https://stripe.com/jobs/101",
            application_url="https://stripe.com/apply/101",
            status="active",
        )
        self.db.add(self.job)
        self.db.flush()

        # Create candidate profile & verified experience
        self.profile = UserProfile(
            user_id=1,
            full_name="Alex Candidate",
            email="candidate@test.com",
            phone="+1-555-0199",
            current_location="San Francisco, CA",
            linkedin="https://linkedin.com/in/alexcandidate",
            github="https://github.com/alexcandidate",
            portfolio="https://alexcandidate.dev",
        )
        self.db.add(self.profile)

        self.exp1 = CandidateExperience(
            user_id=1,
            company="CloudScale Systems",
            title="Senior Distributed Systems Engineer",
            start_date="2022-01",
            end_date="2024-05",
            currently_working=False,
            bullets=[
                "Architected Kafka event-streaming pipeline processing 25M msgs/day with 99.99% reliability.",
                "Reduced p99 query latency from 850ms to 42ms through Redis caching and PostgreSQL query optimization.",
            ],
            technologies=["Kafka", "Go", "PostgreSQL", "Redis"],
        )
        self.db.add(self.exp1)

        self.proj1 = Project(
            user_id=1,
            name="Distributed Fault-Tolerant Cache",
            role="Creator & Lead Developer",
            description="Built Raft-consensus in-memory key-value store in Go with gRPC streaming.",
            bullets=[
                "Implemented Raft leader election and log replication with sub-50ms failover.",
            ],
            technologies=["Go", "Raft", "gRPC"],
        )
        self.db.add(self.proj1)

        # Create master resume version
        self.resume_ver = ResumeVersion(
            id=201,
            user_id=1,
            version_number=1,
            name="Master Backend Resume v1",
            storage_path="test_resumes/master_v1.pdf",
            file_type="pdf",
            latex_source="\\documentclass{article}\\begin{document}Alex Candidate - Master Resume v1\\end{document}",
            is_master=True,
        )
        self.db.add(self.resume_ver)

        # Create master cover letter
        self.cover_letter = CoverLetter(
            id=301,
            user_id=1,
            job_id=101,
            content="Dear Stripe Team, I am thrilled to apply for the Backend Infrastructure Engineer role...",
            format="md",
            style="technical",
        )
        self.db.add(self.cover_letter)
        self.db.flush()

        # Create Application
        self.application = Application(
            id=501,
            user_id=1,
            job_id=101,
            status="Preparing",
            source="Company Website",
            resume_version_id=201,
            cover_letter_id=301,
            submission_confirmed=False,
            applied_at=None,
            notes="Initial application preparation phase.",
            match_report={"overall_score": 94.5, "strengths": ["Kafka", "Go"]},
        )
        self.db.add(self.application)
        self.db.commit()

    def tearDown(self):
        self.llm_patcher.stop()
        self.db.close()
        self.engine.dispose()

    # =========================================================================
    # PART 1: INTERVIEW PREPARATION WORKSPACE TESTS
    # =========================================================================

    def test_interview_prep_generates_all_nine_categories(self):
        """Test that question bank generation covers all 9 required categories."""
        questions = generate_interview_questions_for_job(
            job_id=101, user_id=1, db=self.db, force_refresh=True
        )

        self.assertIsNotNone(questions)
        self.assertGreaterEqual(len(questions), 9)

        generated_categories = {q.category for q in questions}
        expected_categories = {
            "resume_walkthrough",
            "programming_fundamentals",
            "dsa",
            "languages_frameworks",
            "role_specific",
            "software_practices",
            "system_design",
            "behavioral",
            "company_product",
        }

        for cat in expected_categories:
            self.assertIn(
                cat,
                generated_categories,
                f"Missing required interview question category: {cat}",
            )

        # Also test API endpoint
        resp = self.client.get("/api/v1/interview-prep/categories")
        self.assertEqual(resp.status_code, 200)
        api_cats = [c["id"] for c in resp.json()]
        for cat in expected_categories:
            self.assertIn(cat, api_cats)

    def test_interview_prep_question_structure_and_epistemic_honesty(self):
        """
        Verify each question contains:
        why_it_matters, what_good_answer_demonstrates, suggested_answer,
        likely_follow_ups, common_mistakes, practice_resources.
        Also verify epistemic honesty: is_verified_company_question == False.
        """
        questions = generate_interview_questions_for_job(
            job_id=101, user_id=1, db=self.db, force_refresh=True
        )

        for q in questions:
            # Epistemic honesty check: do not claim company definitely asks question unless verified
            self.assertFalse(
                q.is_verified_company_question,
                f"Question '{q.question}' must not claim to be verified company question without verification",
            )

            # Core required fields
            self.assertTrue(bool(q.why_it_matters), f"Question {q.id} missing why_it_matters")
            self.assertTrue(bool(q.what_good_answer_demonstrates), f"Question {q.id} missing what_good_answer_demonstrates")
            self.assertTrue(bool(q.suggested_answer), f"Question {q.id} missing suggested_answer")
            self.assertIsInstance(q.likely_follow_ups, list)
            self.assertGreater(len(q.likely_follow_ups), 0, f"Question {q.id} missing likely_follow_ups")
            self.assertIsInstance(q.common_mistakes, list)
            self.assertGreater(len(q.common_mistakes), 0, f"Question {q.id} missing common_mistakes")
            self.assertIsInstance(q.practice_resources, list)

            # Practice resources format check (title and url)
            for res in q.practice_resources:
                self.assertIn("title", res)
                self.assertIn("url", res)

    def test_behavioral_questions_use_star_framework(self):
        """Verify behavioral questions contain structured STAR breakdown (Situation, Task, Action, Result)."""
        questions = generate_interview_questions_for_job(
            job_id=101, user_id=1, db=self.db, force_refresh=True
        )

        behavioral_qs = [q for q in questions if q.category == "behavioral"]
        self.assertGreater(len(behavioral_qs), 0)

        for bq in behavioral_qs:
            star = bq.star_framework
            self.assertIsNotNone(star, f"Behavioral question '{bq.question}' missing STAR framework")
            self.assertIn("situation", star)
            self.assertIn("task", star)
            self.assertIn("action", star)
            self.assertIn("result", star)
            self.assertTrue(bool(star["situation"]))
            self.assertTrue(bool(star["action"]))
            self.assertTrue(bool(star["result"]))

            # Frontend compatibility alias check
            self.assertEqual(bq.star_breakdown, star)

    def test_suggested_answers_grounded_in_candidate_experience(self):
        """Verify suggested answers are grounded in the verified candidate library (projects/experience)."""
        questions = generate_interview_questions_for_job(
            job_id=101, user_id=1, db=self.db, force_refresh=True
        )

        # Resume walkthrough or role-specific should reference real candidate project/company
        all_suggested = " ".join([q.suggested_answer for q in questions])
        self.assertTrue(
            "CloudScale Systems" in all_suggested
            or "Distributed Fault-Tolerant Cache" in all_suggested
            or "Kafka" in all_suggested,
            "Suggested answers should be grounded in candidate's verified experience/projects",
        )

    def test_mock_interview_session_interactive_flow(self):
        """
        Build interactive mock interview session with:
        - One question at a time
        - Configurable difficulty and category
        - Saved answers and constructive feedback (score, strengths, improvements, model answer)
        - Retries incrementing retry count
        - Session history persistence
        """
        # 1. Start mock session via API
        create_resp = self.client.post(
            "/api/v1/interview-prep/sessions",
            json={
                "job_id": 101,
                "category": "system_design",
                "difficulty": "medium",
                "question_count": 2,
            },
        )
        self.assertEqual(create_resp.status_code, 200)
        session_data = create_resp.json()

        self.assertIsNotNone(session_data.get("id"))
        session_id = session_data["id"]
        self.assertEqual(session_data["category"], "system_design")
        self.assertEqual(session_data["status"], "in_progress")
        self.assertGreaterEqual(len(session_data["questions_json"]), 1)

        # 2. Evaluate answer on question index 0
        eval_resp = self.client.post(
            f"/api/v1/interview-prep/sessions/{session_id}/answer",
            json={
                "question_index": 0,
                "answer_text": (
                    "I would architect the payment ingestion system using an event-driven pattern with Kafka. "
                    "Each transaction payload is assigned an idempotency key and published to a partition keyed by merchant_id. "
                    "Workers consume the events, record state transitions in PostgreSQL with ACID isolation, and emit downstream webhooks."
                ),
            },
        )
        self.assertEqual(eval_resp.status_code, 200)
        eval_data = eval_resp.json()

        # Check root-level feedback keys for frontend compatibility
        self.assertIn("score", eval_data)
        self.assertIn("feedback", eval_data)
        self.assertIn("strengths", eval_data)
        self.assertIn("improvements", eval_data)
        self.assertIn("model_answer", eval_data)
        self.assertIn("retry_count", eval_data)

        self.assertGreaterEqual(eval_data["score"], 50)
        self.assertEqual(eval_data["retry_count"], 0)
        self.assertIsInstance(eval_data["strengths"], list)
        self.assertIsInstance(eval_data["improvements"], list)

        # 3. Test retry on the same question (index 0)
        retry_resp = self.client.post(
            f"/api/v1/interview-prep/sessions/{session_id}/answer",
            json={
                "question_index": 0,
                "answer_text": (
                    "Refined answer: To ensure strict zero-data-loss, I implement distributed consensus using Raft, "
                    "combined with WAL log replication and PostgreSQL optimistic concurrency control with idempotency keys."
                ),
            },
        )
        self.assertEqual(retry_resp.status_code, 200)
        retry_data = retry_resp.json()

        self.assertEqual(retry_data["retry_count"], 1)
        self.assertGreaterEqual(retry_data["score"], 60)

        # 4. Check session details and history
        detail_resp = self.client.get(f"/api/v1/interview-prep/sessions/{session_id}")
        self.assertEqual(detail_resp.status_code, 200)
        details = detail_resp.json()

        self.assertIn("0", details["answers"])
        answer0 = details["answers"]["0"]
        self.assertEqual(answer0["retry_count"], 1)
        self.assertIn("Refined answer", answer0["answer_text"])

        # Check session list history
        list_resp = self.client.get(f"/api/v1/interview-prep/sessions?job_id=101")
        self.assertEqual(list_resp.status_code, 200)
        history_list = list_resp.json()
        self.assertGreaterEqual(len(history_list), 1)
        self.assertEqual(history_list[0]["id"], session_id)

    # =========================================================================
    # PART 2: APPLICATION TRACKER CRM & CANONICAL STATUSES
    # =========================================================================

    def test_crm_supports_all_thirteen_canonical_statuses(self):
        """
        Verify that CRM supports all 13 canonical statuses:
        Discovered, Saved, Shortlisted, Preparing, Ready to Apply, Applied,
        Assessment Received, Interview Scheduled, Interview Completed,
        Offer Received, Rejected, Withdrawn, Position Closed.
        """
        canonical_statuses = [
            "Discovered",
            "Saved",
            "Shortlisted",
            "Preparing",
            "Ready to Apply",
            "Applied",
            "Assessment Received",
            "Interview Scheduled",
            "Interview Completed",
            "Offer Received",
            "Rejected",
            "Withdrawn",
            "Position Closed",
        ]

        for status in canonical_statuses:
            resp = self.client.put(
                f"/api/v1/applications/{self.application.id}/crm",
                json={"status": status, "notes": f"Testing transition to {status}"},
            )
            self.assertEqual(
                resp.status_code,
                200,
                f"Failed to update status to {status}: {resp.text}",
            )
            data = resp.json()
            self.assertEqual(data["status"], status)

        # Verify status transitions are recorded in history
        history_resp = self.client.get(f"/api/v1/applications/{self.application.id}/history")
        self.assertEqual(history_resp.status_code, 200)
        history_items = history_resp.json()
        self.assertGreaterEqual(len(history_items), len(canonical_statuses))

    def test_crm_application_record_retention(self):
        """
        Each application must retain its job, source, match report,
        assessment deadlines, interview dates, notes, follow-ups, and outcome.
        """
        deadline = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        interview_time = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()

        update_payload = {
            "status": "Interview Scheduled",
            "source": "LinkedIn Referral",
            "notes": "Spoke with recruiter; technical screen scheduled.",
            "assessment_deadline": deadline,
            "assessment_notes": "HackerRank 90 min coding challenge",
            "interview_date": interview_time,
            "interview_round": "Technical Architecture Round 1",
            "interview_notes": "Deep dive into distributed systems & Kafka",
            "outcome": "Pending Interview",
            "outcome_notes": "Preparation underway using Interview Prep Workspace",
            "offer_compensation": None,
            "next_action": "Complete mock interview session",
        }

        resp = self.client.put(
            f"/api/v1/applications/{self.application.id}/crm",
            json=update_payload,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertEqual(data["status"], "Interview Scheduled")
        self.assertEqual(data["source"], "LinkedIn Referral")
        self.assertEqual(data["interview_round"], "Technical Architecture Round 1")
        self.assertEqual(data["assessment_notes"], "HackerRank 90 min coding challenge")
        self.assertEqual(data["next_action"], "Complete mock interview session")

    # =========================================================================
    # PART 3: EXPLICIT CONFIRMATION & IMMUTABLE MATERIAL SNAPSHOTTING
    # =========================================================================

    def test_never_mark_as_applied_without_explicit_confirmation(self):
        """
        Never mark an application as submitted just because the user
        opened an external link or generated materials.
        Require explicit confirmation.
        """
        # Fetch initial state
        resp = self.client.get(f"/api/v1/applications/{self.application.id}")
        self.assertEqual(resp.status_code, 200)
        app_data = resp.json()

        self.assertFalse(app_data.get("submission_confirmed", False))
        self.assertNotEqual(app_data.get("status"), "Applied")
        self.assertIsNone(app_data.get("applied_at"))
        self.assertIsNone(app_data.get("submitted_resume_snapshot"))
        self.assertIsNone(app_data.get("submitted_cover_letter_snapshot"))

    def test_explicit_submission_freezes_exact_material_snapshots(self):
        """
        When user explicitly confirms submission, exact submitted resume version
        and exact submitted cover letter must be snapshotted and frozen.
        """
        confirm_resp = self.client.post(
            f"/api/v1/applications/{self.application.id}/confirm-submission",
            json={
                "source": "Employer Portal",
                "notes": "Submitted via Stripe careers portal with custom resume v1",
            },
        )
        self.assertEqual(confirm_resp.status_code, 200)
        confirmed_data = confirm_resp.json()

        self.assertEqual(confirmed_data["status"], "Applied")
        self.assertTrue(confirmed_data["submission_confirmed"])
        self.assertIsNotNone(confirmed_data["applied_at"])
        self.assertIn("Alex Candidate - Master Resume v1", confirmed_data["submitted_resume_snapshot"])
        self.assertIn("Dear Stripe Team", confirmed_data["submitted_cover_letter_snapshot"])

        # Check dedicated submitted-materials endpoint
        mat_resp = self.client.get(f"/api/v1/applications/{self.application.id}/submitted-materials")
        self.assertEqual(mat_resp.status_code, 200)
        materials = mat_resp.json()

        self.assertTrue(materials["submission_confirmed"])
        self.assertTrue(materials["has_frozen_resume"])
        self.assertTrue(materials["has_frozen_cover_letter"])
        self.assertTrue(materials["is_snapshot_immutable"])

    def test_immutability_guarantee_master_resume_edit_does_not_mutate_snapshot(self):
        """
        CRITICAL REQUIREMENT:
        Test that submitted materials remain unchanged even when the master resume
        or candidate profile is later edited.
        """
        # 1. First, explicitly confirm submission
        confirm_resp = self.client.post(
            f"/api/v1/applications/{self.application.id}/confirm-submission",
            json={"source": "Direct Apply", "notes": "Freezing snapshot v1"},
        )
        self.assertEqual(confirm_resp.status_code, 200)
        original_snapshot = confirm_resp.json()["submitted_resume_snapshot"]
        original_cover_snapshot = confirm_resp.json()["submitted_cover_letter_snapshot"]

        self.assertIn("Master Resume v1", original_snapshot)

        # 2. Later, candidate radically updates their master resume version
        resume_record = self.db.query(ResumeVersion).filter(ResumeVersion.id == 201).first()
        resume_record.latex_source = (
            "\\documentclass{article}\\begin{document}MUTATED RESUME V2 - COMPLETELY DIFFERENT CONTENT\\end{document}"
        )
        resume_record.name = "Master Resume v2 (Updated Months Later)"

        # Also mutate cover letter
        cl_record = self.db.query(CoverLetter).filter(CoverLetter.id == 301).first()
        cl_record.content = "MUTATED COVER LETTER - THIS SHOULD NEVER OVERWRITE SUBMITTED SNAPSHOT"

        self.db.commit()

        # 3. Retrieve the application's frozen submitted materials
        mat_resp = self.client.get(f"/api/v1/applications/{self.application.id}/submitted-materials")
        self.assertEqual(mat_resp.status_code, 200)
        materials = mat_resp.json()

        # 4. Strict assertions: submitted snapshot is 100% frozen and completely decoupled from master edits
        self.assertEqual(
            materials["submitted_resume_snapshot"],
            original_snapshot,
            "Submitted resume snapshot MUST NOT change when master resume is edited!",
        )
        self.assertNotIn(
            "MUTATED RESUME V2",
            materials["submitted_resume_snapshot"],
            "Submitted resume snapshot contained mutated master content!",
        )

        self.assertEqual(
            materials["submitted_cover_letter_snapshot"],
            original_cover_snapshot,
            "Submitted cover letter snapshot MUST NOT change when cover letter is edited!",
        )
        self.assertNotIn(
            "MUTATED COVER LETTER",
            materials["submitted_cover_letter_snapshot"],
            "Submitted cover letter snapshot contained mutated cover letter content!",
        )

    # =========================================================================
    # PART 4: REMINDERS & RFC 5545 CALENDAR EXPORT
    # =========================================================================

    def test_reminders_and_followups_crud(self):
        """Test scheduling reminders, follow-up items, and deleting them."""
        # 1. Add follow-up
        fu_resp = self.client.post(
            f"/api/v1/applications/{self.application.id}/follow-ups",
            json={"title": "Follow up with recruiter on LinkedIn", "due_date": "2026-10-20"},
        )
        self.assertEqual(fu_resp.status_code, 200)
        fu_data = fu_resp.json()
        self.assertEqual(len(fu_data["follow_ups"]), 1)
        fu_id = fu_data["follow_ups"][0]["id"]

        # 2. Add scheduled reminder
        rem_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        rem_resp = self.client.post(
            f"/api/v1/applications/{self.application.id}/reminders",
            json={
                "title": "Prepare System Design presentation",
                "remind_at": rem_time,
                "reminder_type": "interview",
                "notes": "Review Stripe API idempotency patterns",
            },
        )
        self.assertEqual(rem_resp.status_code, 200)
        rem_data = rem_resp.json()
        self.assertEqual(len(rem_data["reminders"]), 1)
        rem_id = rem_data["reminders"][0]["id"]

        # 3. Delete follow-up
        del_fu = self.client.delete(f"/api/v1/applications/{self.application.id}/follow-ups/{fu_id}")
        self.assertEqual(del_fu.status_code, 200)
        self.assertEqual(len(del_fu.json()["follow_ups"]), 0)

        # 4. Delete reminder
        del_rem = self.client.delete(f"/api/v1/applications/{self.application.id}/reminders/{rem_id}")
        self.assertEqual(del_rem.status_code, 200)
        self.assertEqual(len(del_rem.json()["reminders"]), 0)

    def test_calendar_export_rfc5545(self):
        """
        Test RFC 5545 iCalendar stream generation for single application
        and all applications export.
        """
        # Set interview date & assessment deadline
        interview_dt = (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()
        deadline_dt = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

        self.client.put(
            f"/api/v1/applications/{self.application.id}/crm",
            json={
                "interview_date": interview_dt,
                "interview_round": "Technical Deep Dive",
                "assessment_deadline": deadline_dt,
                "assessment_notes": "Online Coding Assessment",
            },
        )

        # Also add a reminder
        self.client.post(
            f"/api/v1/applications/{self.application.id}/reminders",
            json={
                "title": "Stripe Recruiter Sync Call",
                "remind_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
                "reminder_type": "interview",
                "notes": "15-minute phone screen",
            },
        )

        # Test single application .ics
        single_cal_resp = self.client.get(f"/api/v1/applications/{self.application.id}/calendar.ics")
        self.assertEqual(single_cal_resp.status_code, 200)
        self.assertIn("text/calendar", single_cal_resp.headers["content-type"])
        ics_content = single_cal_resp.text

        self.assertIn("BEGIN:VCALENDAR", ics_content)
        self.assertIn("END:VCALENDAR", ics_content)
        self.assertIn("BEGIN:VEVENT", ics_content)
        self.assertIn("SUMMARY:Interview: Lead Backend Infrastructure Engineer at Stripe (Technical Deep Dive)", ics_content)
        self.assertIn("SUMMARY:Assessment Due: Lead Backend Infrastructure Engineer at Stripe", ics_content)
        self.assertIn("SUMMARY:Reminder: Stripe Recruiter Sync Call", ics_content)

        # Test master all-applications .ics export
        master_cal_resp = self.client.get("/api/v1/applications/calendar/export.ics")
        self.assertEqual(master_cal_resp.status_code, 200)
        self.assertIn("text/calendar", master_cal_resp.headers["content-type"])
        master_ics = master_cal_resp.text

        self.assertIn("BEGIN:VCALENDAR", master_ics)
        self.assertIn("Stripe", master_ics)


if __name__ == "__main__":
    unittest.main()
