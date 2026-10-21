import asyncio
import io
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parent))

config = types.ModuleType("app.core.config")
config.settings = types.SimpleNamespace(
    DATABASE_URL="sqlite:///:memory:", SECRET_KEY="resume-autofill-unit-test-only",
    ALGORITHM="HS256", ACCESS_TOKEN_EXPIRE_MINUTES=30, AUTH_DISABLED=False,
)
original_config = sys.modules.get("app.core.config")
sys.modules["app.core.config"] = config
try:
    from app.core.database import get_db
    from app.models import Base
    from app.models.user import User
    from app.models.profile import Profile
    from app.models.resume import ResumeVersion
    from app.models.candidate import (
        UserProfile, CandidateExperience, Project, Skill, UserSkill,
        Achievement, CourseCertification, CandidateCapability, UserPreference,
    )
    from app.services.ai import parser
    with patch("app.services.storage.local_storage.LocalStorageProvider"):
        from app.api import resume
finally:
    if original_config is None:
        sys.modules.pop("app.core.config", None)
    else:
        sys.modules["app.core.config"] = original_config


class ResumeAutofillTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:", poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, autoflush=False)()
        self.user = User(email="candidate@example.test", hashed_password="unused")
        self.other = User(email="other@example.test", hashed_password="unused")
        self.db.add_all([self.user, self.other])
        self.db.flush()
        self.legacy = Profile(user_id=self.user.id, raw_resume_text="Example Candidate\nPython developer")
        self.db.add(self.legacy)
        self.db.commit()
        self.payload = {
            "full_name": "Example Candidate", "email": "resume@example.test",
            "phone": "+1 555 0100", "current_location": "Example City",
            "education": [{"institution": "Example University", "degree": "Diploma", "year": 2024, "cgpa": 3.5}],
            "experience": [{"company": "Example Co", "title": "Developer", "start_date": "2023-01", "description": "Built tools"}],
            "projects": [{"name": "Example Tool", "github": "https://github.com/example/tool", "description": "Resume description", "technologies": ["Python", "python", "SQL"]}],
            "skills": [{"name": "Python", "confidence": 3, "years_used": 2.0}, "python", "SQL"],
            "achievements": [{"title": "Example Award", "issuer_or_event": "Example Event", "year_or_date": "2024"}, "Example Award"],
            "courses": [{"name": "Example Course", "issuer": "Example Academy", "skills_covered": ["SQL", "sql"]}, "Example Course"],
        }
        self.provider = Mock()
        self.provider.generate_json.return_value = self.payload
        self.provider_module = types.ModuleType("app.services.llm.gemini_provider")
        self.provider_module.GeminiProvider = Mock(return_value=self.provider)
        self.provider_patch = patch.dict(sys.modules, {"app.services.llm.gemini_provider": self.provider_module})
        self.provider_patch.start()
        self.storage = Mock()
        self.storage.upload_file.return_value = "mock-resume-path"
        self.storage_patch = patch.object(resume, "storage", self.storage)
        self.storage_patch.start()
        self.app = FastAPI()
        self.app.include_router(resume.router, prefix="/api/v1/resume")
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.app.dependency_overrides[resume.get_current_user] = lambda: self.user
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.storage_patch.stop()
        self.provider_patch.stop()
        self.db.close()
        self.engine.dispose()

    def autofill(self):
        return self.client.post("/api/v1/resume/autofill")

    def test_idempotency_and_all_sections(self):
        first = self.autofill()
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["counts"], {
            "profile_fields": 8, "experiences": 1, "projects": 1,
            "skills": 2, "achievements": 1, "courses": 1,
        })
        second = self.autofill()
        self.assertEqual(second.status_code, 200, second.text)
        self.assertTrue(all(count == 0 for count in second.json()["counts"].values()))
        self.assertEqual(self.db.query(Project).one().technologies, ["Python", "SQL"])
        self.assertEqual(self.db.query(CourseCertification).one().skills_covered, ["SQL"])
        self.assertEqual(self.db.query(Achievement).one().issuer_or_event, "Example Event")
        profile = self.db.query(UserProfile).one()
        self.assertEqual(profile.degree, "Diploma")
        self.assertIsNone(profile.visa_required)
        self.assertIsNone(profile.willing_to_relocate)
        sql = self.db.query(UserSkill).join(Skill).filter(Skill.name == "SQL").one()
        self.assertIsNone(sql.confidence)
        self.assertIsNone(sql.years_used)
        self.assertIsNone(self.db.query(CandidateExperience).one().months_of_experience)
        self.assertEqual(self.db.query(CandidateCapability).count(), 0)
        self.assertEqual(self.db.query(UserPreference).count(), 0)

    def test_preserves_manual_github_and_sensitive_data(self):
        profile = UserProfile(
            user_id=self.user.id, full_name="Manual Name", email="manual@example.test",
            degree="Masters", university="Manual University", graduation_year=2020, cgpa=0,
            current_location="Manual City", work_authorization="manual authorization",
            visa_required=True, willing_to_relocate=False, remote_preference="remote",
            preferred_locations=["Manual City"], github="https://github.com/example/manual",
        )
        project = Project(user_id=self.user.id, name="GitHub repository", github="https://github.com/example/tool.git/", description="GitHub description", technologies=["Rust"])
        experience = CandidateExperience(user_id=self.user.id, company="EXAMPLE CO", title="Developer", start_date="January 2023", currently_working=False, months_of_experience=0, description="Manual experience")
        skill = Skill(name="PYTHON")
        self.db.add_all([profile, project, experience, skill])
        self.db.flush()
        self.db.add_all([
            UserSkill(user_id=self.user.id, skill_id=skill.id, confidence=1, years_used=0),
            CandidateCapability(user_id=self.user.id, has_work_authorization=False),
            UserPreference(user_id=self.user.id, minimum_salary=123, remote_only=True),
        ])
        self.legacy.education_json = [{"manual": "education"}]
        self.legacy.projects_json = [{"manual": "project"}]
        self.db.commit()
        self.payload.update({"work_authorization": "inferred", "visa_required": False, "minimum_salary": 0, "capabilities": {"has_work_authorization": True}})
        self.payload["experience"][0].update({"currently_working": True, "months_of_experience": 24})
        result = self.autofill()
        self.assertEqual(result.status_code, 200, result.text)
        self.db.refresh(profile)
        self.assertEqual(profile.full_name, "Manual Name")
        self.assertEqual(profile.email, "manual@example.test")
        self.assertEqual(profile.degree, "Masters")
        self.assertEqual(profile.university, "Manual University")
        self.assertEqual(profile.graduation_year, 2020)
        self.assertEqual(profile.cgpa, 0)
        self.assertEqual(profile.current_location, "Manual City")
        self.assertEqual(profile.work_authorization, "manual authorization")
        self.assertTrue(profile.visa_required)
        self.assertFalse(profile.willing_to_relocate)
        self.assertEqual(profile.preferred_locations, ["Manual City"])
        self.assertEqual(profile.remote_preference, "remote")
        self.assertEqual(profile.github, "https://github.com/example/manual")
        self.assertEqual(profile.phone, "+1 555 0100")
        self.assertEqual(self.db.query(Project).count(), 1)
        self.assertEqual(project.name, "GitHub repository")
        self.assertEqual(project.description, "GitHub description")
        self.assertEqual(project.technologies, ["Rust", "Python", "SQL"])
        self.assertEqual(self.db.query(CandidateExperience).count(), 1)
        self.assertFalse(experience.currently_working)
        self.assertEqual(experience.months_of_experience, 0)
        self.assertEqual(experience.description, "Manual experience")
        link = self.db.query(UserSkill).filter(UserSkill.skill_id == skill.id).one()
        self.assertEqual((link.confidence, link.years_used), (1, 0))
        self.assertFalse(self.db.query(CandidateCapability).one().has_work_authorization)
        self.assertEqual(self.db.query(UserPreference).one().minimum_salary, 123)
        self.assertTrue(self.db.query(UserPreference).one().remote_only)
        self.assertEqual(self.legacy.education_json, [{"manual": "education"}])
        self.assertEqual(self.legacy.projects_json, [{"manual": "project"}])

    def test_missing_degree_not_guessed(self):
        self.provider.generate_json.return_value = {"education": [{"institution": "Example University"}]}
        self.assertEqual(self.autofill().status_code, 200)
        self.assertIsNone(self.db.query(UserProfile).one().degree)

    def test_invalid_extraction_is_atomic_502(self):
        for invalid in (
            None, [], {}, {"education": [{}]}, {"projects": [{"name": " "}]},
            {"full_name": "Valid", "experience": [{"company": "Example"}]},
            {"skills": [{"name": "Python", "confidence": 6}]},
            {"skills": [{"name": "Python", "years_used": float("nan")}]},
            {"education": [{"year": "2024-2028"}]},
            {"experience": [{"company": "Example", "title": "Developer", "currently_working": "false"}]},
            {"github": "javascript:alert(1)"}, {"full_name": 42},
        ):
            with self.subTest(invalid=invalid):
                self.provider.generate_json.return_value = invalid
                result = self.autofill()
                self.assertEqual(result.status_code, 502, result.text)
                self.assertEqual(self.db.query(UserProfile).count(), 0)
                self.assertEqual(self.db.query(Project).count(), 0)

    def test_provider_failure_is_clean_502(self):
        self.provider.generate_json.side_effect = RuntimeError("private upstream detail")
        response = self.autofill()
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("private", response.text)
        self.assertEqual(self.db.query(UserProfile).count(), 0)

    def test_no_resume_and_unreadable_resume(self):
        for text in (None, "", " \n\t", "\x00broken", "\ufffd", "---"):
            with self.subTest(text=text):
                self.legacy.raw_resume_text = text
                self.db.commit()
                self.assertEqual(self.autofill().status_code, 400)
        self.db.delete(self.legacy)
        self.db.commit()
        self.assertEqual(self.autofill().status_code, 400)
        self.provider.generate_json.assert_not_called()

    def test_authentication_and_user_isolation(self):
        del self.app.dependency_overrides[resume.get_current_user]
        self.assertEqual(self.autofill().status_code, 401)
        self.assertEqual(self.client.post("/api/v1/resume/autofill", headers={"Authorization": "Bearer invalid"}).status_code, 401)
        self.app.dependency_overrides[resume.get_current_user] = lambda: self.other
        self.assertEqual(self.autofill().status_code, 400)
        self.provider.generate_json.assert_not_called()
        other_profile = Profile(user_id=self.other.id, raw_resume_text="Other candidate resume")
        self.db.add(other_profile)
        self.db.commit()
        self.assertEqual(self.client.post("/api/v1/resume/autofill", json={"user_id": self.user.id}).status_code, 200)
        self.assertEqual(self.provider.generate_json.call_args.kwargs["user_prompt"], "Other candidate resume")
        for model in (UserProfile, Project, CandidateExperience, UserSkill, Achievement, CourseCertification):
            self.assertEqual(self.db.query(model).filter(model.user_id == self.user.id).count(), 0)
            self.assertGreater(self.db.query(model).filter(model.user_id == self.other.id).count(), 0)

    def test_merge_failure_rolls_back_partial_writes(self):
        original = parser.merge_resume_to_profile

        def failing_merge(*args):
            original(*args)
            raise RuntimeError("private merge error")

        with patch.object(parser, "merge_resume_to_profile", side_effect=failing_merge):
            result = self.autofill()
        self.assertEqual(result.status_code, 500)
        self.assertNotIn("private", result.text)
        for model in (UserProfile, Project, CandidateExperience, Skill, UserSkill, Achievement, CourseCertification):
            self.assertEqual(self.db.query(model).count(), 0)
        self.assertEqual(self.autofill().status_code, 200)

    def test_commit_failure_rolls_back(self):
        with patch.object(self.db, "commit", side_effect=RuntimeError("commit failed")):
            self.assertEqual(self.autofill().status_code, 500)
        self.assertEqual(self.db.query(UserProfile).count(), 0)
        self.assertEqual(self.db.query(Project).count(), 0)

    def test_existing_achievements_courses_fill_only_and_repeated_roles(self):
        achievement = Achievement(user_id=self.user.id, title="EXAMPLE AWARD", description="Manual award")
        course = CourseCertification(user_id=self.user.id, name="EXAMPLE COURSE", skills_covered=["Rust"])
        previous = CandidateExperience(user_id=self.user.id, company="Example Co", title="Developer", start_date="2020-01")
        self.db.add_all([achievement, course, previous])
        self.db.commit()
        self.assertEqual(self.autofill().status_code, 200)
        self.assertEqual(self.db.query(Achievement).count(), 1)
        self.assertEqual(achievement.description, "Manual award")
        self.assertEqual(achievement.issuer_or_event, "Example Event")
        self.assertEqual(self.db.query(CourseCertification).count(), 1)
        self.assertEqual(course.issuer, "Example Academy")
        self.assertEqual(course.skills_covered, ["Rust", "SQL"])
        self.assertEqual(self.db.query(CandidateExperience).count(), 2)
        self.assertTrue(all(value == 0 for value in self.autofill().json()["counts"].values()))

    def test_upload_rejects_invalid_before_storage_or_mutation(self):
        for name, content in (
            (None, b"resume"), ("", b"resume"), ("resume.txt", b""),
            ("resume.txt", b" \n"), ("resume.txt", b"\xff\xfe"),
            ("resume.txt", b"\x00binary"), ("resume.pdf", b"not pdf"),
            ("resume.docx", b"not docx"), ("resume.exe", b"text"),
        ):
            with self.subTest(name=name, content=content):
                file = UploadFile(filename=name, file=io.BytesIO(content))
                with self.assertRaises(HTTPException) as raised:
                    asyncio.run(resume.upload_resume(file=file, current_user=self.user, db=self.db))
                self.assertEqual(raised.exception.status_code, 400)
        self.storage.upload_file.assert_not_called()
        self.assertEqual(self.db.query(ResumeVersion).count(), 0)
        self.assertEqual(self.legacy.raw_resume_text, "Example Candidate\nPython developer")

    def test_upload_does_not_autofill(self):
        result = self.client.post("/api/v1/resume/upload", files={"file": ("resume.txt", b"Example uploaded resume", "text/plain")})
        self.assertEqual(result.status_code, 200, result.text)
        self.provider.generate_json.assert_not_called()
        self.assertEqual(self.db.query(UserProfile).count(), 0)
        self.assertEqual(self.legacy.raw_resume_text, "Example uploaded resume")
        self.assertEqual(self.db.query(ResumeVersion).count(), 1)

    def test_empty_pdf_and_docx_are_rejected(self):
        with patch("pdfminer.high_level.extract_text", return_value=" \n\f"):
            result = self.client.post("/api/v1/resume/upload", files={"file": ("resume.pdf", b"mock pdf")})
        self.assertEqual(result.status_code, 400)
        document = Mock(paragraphs=[], tables=[])
        with patch("docx.Document", return_value=document):
            result = self.client.post("/api/v1/resume/upload", files={"file": ("resume.docx", b"mock docx")})
        self.assertEqual(result.status_code, 400)
        self.storage.upload_file.assert_not_called()

    def test_compatibility_wrapper(self):
        factory = sessionmaker(bind=self.engine, autoflush=False)
        with patch.object(parser, "SessionLocal", factory):
            counts = parser.parse_resume_to_profile(self.legacy.id, "Example candidate resume")
            repeated = parser.parse_resume_to_profile(self.legacy.id, "Example candidate resume")
        self.assertEqual(counts["projects"], 1)
        self.assertTrue(all(value == 0 for value in repeated.values()))


if __name__ == "__main__":
    unittest.main()
