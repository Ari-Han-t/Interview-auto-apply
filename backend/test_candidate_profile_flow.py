import io
import os
import shutil
import sys
import tempfile
import types
import unittest
import zipfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Configure isolated in-memory test environment
config = types.ModuleType("app.core.config")
config.settings = types.SimpleNamespace(
    DATABASE_URL="sqlite:///:memory:",
    SECRET_KEY="candidate-profile-flow-test-key",
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
    from app.models.profile import Profile
    from app.models.resume import ResumeVersion
    from app.models.candidate import (
        UserProfile,
        CandidateEducation,
        CandidateExperience,
        Project,
        Skill,
        UserSkill,
        Achievement,
        CourseCertification,
        CandidateCapability,
        UserPreference,
    )
    from app.services.storage.local_storage import LocalStorageProvider
    from app.services.ai.latex_parser import LatexResumeParser, extract_and_parse_latex_zip
    from app.services.ai.profile_builder import build_profile_text
    from app.api import profile as profile_api
    from app.api import resume as resume_api
finally:
    if original_config is None:
        sys.modules.pop("app.core.config", None)
    else:
        sys.modules["app.core.config"] = original_config


class CandidateProfileFlowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine, autoflush=False)()

        # Isolated storage provider for test files
        self.temp_dir = tempfile.TemporaryDirectory()
        resume_api.storage = LocalStorageProvider(base_dir=self.temp_dir.name)

        # User A and User B to test user ownership isolation
        self.user_a = User(email="alex@example.test", hashed_password="hashed_password_a")
        self.user_b = User(email="bob@example.test", hashed_password="hashed_password_b")
        self.db.add_all([self.user_a, self.user_b])
        self.db.commit()
        self.db.refresh(self.user_a)
        self.db.refresh(self.user_b)

        # TestClient with overridden dependencies
        self.app = FastAPI()
        self.app.include_router(resume_api.router, prefix="/api/v1/resume")
        self.app.include_router(profile_api.router, prefix="/api/v1/profile")

        self.current_user = self.user_a

        def override_get_db():
            yield self.db

        def override_get_current_user():
            return self.current_user

        self.app.dependency_overrides[get_db] = override_get_db
        self.app.dependency_overrides[resume_api.get_current_user] = override_get_current_user
        self.app.dependency_overrides[profile_api.get_current_user] = override_get_current_user
        self.client = TestClient(self.app)

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.temp_dir.cleanup()

    def test_01_latex_parser_macro_recognition_and_flags(self):
        """Test LaTeX parsing recognizes custom and standard macros, coursework, and flags unparsed commands."""
        sample_tex = r"""
\documentclass{article}
\newcommand{\myrole}{Staff Distributed Systems Engineer}
\def\mycompany{Acme Cloud Labs}
\newcommand{\resumeSubheading}[4]{
  \textbf{#1} & #2 \\
  \textit{#3} & \textit{#4} \\
}
\newcommand{\resumeItem}[1]{\item #1}
\begin{document}
\textbf{\huge Alex Developer} \\
Email: alex.dev@example.com $|$ Phone: +1-555-0199 $|$ GitHub: github.com/alexdev $|$ LinkedIn: linkedin.com/in/alexdev $|$ Website: alexdev.io

\section{Education}
\resumeSubheading
  {Stanford University}{Stanford, CA}
  {Bachelor of Science in Computer Science; CGPA: 3.92/4.00}{2021 -- 2025}
Relevant Coursework: Data Structures \& Algorithms, Distributed Systems, Operating Systems, Machine Learning

\section{Experience}
\resumeSubheading
  {\mycompany}{San Francisco, CA}
  {\myrole}{June 2024 -- August 2024}
  \resumeItem{Engineered high-throughput event processing pipelines handling 50k events/sec.}
  \resumeItem{Optimized PostgreSQL query plans reducing p99 tail latency by 45\%.}

\section{Projects}
\textbf{AutoApply Agent} $|$ Python, FastAPI, React \\
\textit{Autonomous job application assistant} \\
Built an AI workflow that parses LaTeX resumes and verifies candidate facts.

\section{Technical Skills}
\textbf{Languages}: Python, TypeScript, Go, C++, SQL \\
\textbf{Frameworks}: FastAPI, Next.js, PyTorch \\
\textbf{Developer Tools}: Docker, Kubernetes, Git, AWS

\section{Achievements}
First Place at Stanford AI Hackathon 2024 $|$ Built real-time multimodal transcription tool.

\unknownMacroWithSpecialSyntax{ArgumentOne}{ArgumentTwo}

\end{document}
"""
        parser = LatexResumeParser()
        extracted = parser.parse_full_latex(sample_tex)

        # Check contact details
        profile = extracted["profile"]
        self.assertEqual(profile["full_name"], "Alex Developer")
        self.assertEqual(profile["email"], "alex.dev@example.com")
        self.assertEqual(profile["phone"], "+1-555-0199")
        self.assertIn("github.com/alexdev", profile["github"])
        self.assertIn("linkedin.com/in/alexdev", profile["linkedin"])

        # Check custom macro substitution (\mycompany and \myrole)
        self.assertTrue(len(extracted["experiences"]) >= 1)
        exp = extracted["experiences"][0]
        self.assertEqual(exp["company"], "Acme Cloud Labs")
        self.assertEqual(exp["title"], "Staff Distributed Systems Engineer")
        self.assertTrue(any("50k events/sec" in h for h in exp.get("highlights", [])))

        # Check education & coursework
        self.assertTrue(len(extracted["education"]) >= 1)
        edu = extracted["education"][0]
        self.assertEqual(edu["institution"], "Stanford University")
        self.assertEqual(edu["degree"], "Bachelor of Science")
        self.assertEqual(edu["specialization"], "Computer Science")
        self.assertEqual(edu["cgpa"], 3.92)
        self.assertEqual(edu["graduation_year"], 2025)
        self.assertTrue(any("Distributed Systems" in c for c in edu.get("coursework", [])))

        # Check skills categorized
        skill_names = [s["name"] for s in extracted["skills"]]
        self.assertIn("Python", skill_names)
        self.assertIn("FastAPI", skill_names)
        self.assertIn("Docker", skill_names)

        # Check unparsed macro was safely flagged without crashing
        flags = extracted.get("flags", [])
        self.assertTrue(any("unknownMacroWithSpecialSyntax" in f.get("message", "") for f in flags))

    def test_02_latex_zip_archive_modular_extraction(self):
        """Test safe extraction of ZIP archive containing modular LaTeX sub-files."""
        main_tex = r"""
\documentclass{article}
\begin{document}
\textbf{Morgan Freeman} \\
Email: morgan@example.com
\input{sections/education}
\input{sections/skills}
\end{document}
"""
        edu_tex = r"""
\section{Education}
\textbf{Massachusetts Institute of Technology} \\
Master of Science in Artificial Intelligence (2023 -- 2025) $|$ CGPA: 4.0
Relevant Coursework: Deep Learning, Computer Vision
"""
        skills_tex = r"""
\section{Skills}
\textbf{Languages}: Rust, Python, Go
"""
        zip_path = os.path.join(self.temp_dir.name, "modular_resume.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("main.tex", main_tex)
            zf.writestr("sections/education.tex", edu_tex)
            zf.writestr("sections/skills.tex", skills_tex)
            zf.writestr("assets/avatar.png", b"fake_png_data")

        extract_dir = os.path.join(self.temp_dir.name, "extracted")
        raw_text, extracted = extract_and_parse_latex_zip(zip_path, extract_dir)

        self.assertIn("Morgan Freeman", raw_text)
        self.assertEqual(extracted["profile"]["full_name"], "Morgan Freeman")
        self.assertEqual(extracted["profile"]["email"], "morgan@example.com")
        self.assertTrue(len(extracted["education"]) >= 1)
        self.assertIn("Massachusetts Institute of Technology", extracted["education"][0]["institution"])
        skill_names = [s["name"] for s in extracted["skills"]]
        self.assertIn("Rust", skill_names)

    def test_03_resume_upload_and_review_workflow(self):
        """Test upload -> parse -> review facts -> save -> verify database persistence across sessions."""
        # 1. Upload LaTeX resume
        tex_bytes = b"""\\documentclass{article}
\\begin{document}
\\textbf{Casey Jordan} \\\\
Email: casey.jordan@example.com
\\section{Education}
UC Berkeley \\\\
Bachelor of Science in Data Science (2022 -- 2026) $|$ CGPA: 3.88
Relevant Coursework: Advanced Algorithms, Cloud Computing
\\section{Skills}
Languages: Python, SQL, C++
\\end{document}"""

        response = self.client.post(
            "/api/v1/resume/upload",
            files={"file": ("resume.tex", io.BytesIO(tex_bytes), "application/x-tex")},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        resume_id = data["id"]
        self.assertIn("extracted_data", data)
        extracted = data["extracted_data"]
        self.assertEqual(extracted["profile"]["full_name"], "Casey Jordan")
        self.assertEqual(extracted["profile"]["email"], "casey.jordan@example.com")

        # Verify that upload alone did NOT prematurely overwrite master profile
        user_prof = self.db.query(UserProfile).filter(UserProfile.user_id == self.user_a.id).first()
        self.assertIsNone(user_prof)

        # 2. Candidate reviews extracted facts, customizes details, and saves
        review_payload = {
            "resume_id": resume_id,
            "apply_to_master_profile": True,
            "version_name": "ML Engineer Resume",
            "target_role": "Machine Learning Engineer",
            "notes": "Reviewed from LaTeX source",
            "is_master": True,
            "extracted_data": {
                "profile": {
                    "full_name": "Casey Jordan",
                    "preferred_name": "CJ",
                    "email": "casey.jordan@example.com",
                    "phone": "+1-415-555-0100",
                    "university": "UC Berkeley",
                    "degree": "Bachelors",
                    "specialization": "Data Science",
                    "graduation_year": 2026,
                    "current_semester_or_year": "Senior Year",
                    "cgpa": 3.88,
                    "coursework": ["Advanced Algorithms", "Cloud Computing", "Distributed Systems"],
                    "bio": "Data science undergraduate specializing in ML engineering.",
                    "availability": "Available immediately for Summer 2026",
                },
                "educations": [
                    {
                        "degree": "Bachelor of Science",
                        "institution": "UC Berkeley",
                        "specialization": "Data Science",
                        "start_year": 2022,
                        "graduation_year": 2026,
                        "cgpa": 3.88,
                        "coursework": ["Advanced Algorithms", "Cloud Computing", "Distributed Systems"],
                        "is_visible": True,
                    }
                ],
                "experiences": [
                    {
                        "company": "Data Insights Co.",
                        "title": "Machine Learning Intern",
                        "internship_or_fulltime": "internship",
                        "start_date": "May 2025",
                        "end_date": "August 2025",
                        "currently_working": False,
                        "months_of_experience": 3,
                        "description": "Implemented automated feature extraction pipeline.",
                        "location": "Berkeley, CA",
                        "technologies": ["Python", "PyTorch", "GCP"],
                        "is_visible": True,
                    }
                ],
                "projects": [
                    {
                        "name": "Neural Semantic Search",
                        "description": "Semantic search engine utilizing vector embeddings.",
                        "role": "Creator & Lead",
                        "technologies": ["Python", "FastAPI", "FAISS"],
                        "github": "https://github.com/casey/neural-search",
                        "is_visible": True,
                    }
                ],
                "skills": [
                    {"name": "Python", "category": "Languages", "confidence": 5, "years_used": 3.0, "is_visible": True},
                    {"name": "PyTorch", "category": "Frameworks", "confidence": 4, "years_used": 2.0, "is_visible": True},
                ],
                "achievements": [
                    {
                        "title": "Berkeley ML Hackathon Winner",
                        "category": "hackathon",
                        "year_or_date": "2024",
                        "description": "Best NLP application.",
                        "is_visible": True,
                    }
                ],
            },
        }

        save_res = self.client.post("/api/v1/resume/review-and-save", json=review_payload)
        self.assertEqual(save_res.status_code, 200)

        # 3. Reload from database and verify persistence
        saved_prof = self.db.query(UserProfile).filter(UserProfile.user_id == self.user_a.id).first()
        self.assertIsNotNone(saved_prof)
        self.assertEqual(saved_prof.full_name, "Casey Jordan")
        self.assertEqual(saved_prof.preferred_name, "CJ")
        self.assertEqual(saved_prof.specialization, "Data Science")
        self.assertEqual(saved_prof.current_semester_or_year, "Senior Year")
        self.assertEqual(saved_prof.cgpa, 3.88)
        self.assertIn("Distributed Systems", saved_prof.coursework)

        saved_edus = self.db.query(CandidateEducation).filter(CandidateEducation.user_id == self.user_a.id).all()
        self.assertEqual(len(saved_edus), 1)
        self.assertEqual(saved_edus[0].institution, "UC Berkeley")
        self.assertEqual(saved_edus[0].graduation_year, 2026)

        saved_exps = self.db.query(CandidateExperience).filter(CandidateExperience.user_id == self.user_a.id).all()
        self.assertEqual(len(saved_exps), 1)
        self.assertEqual(saved_exps[0].company, "Data Insights Co.")

        saved_projs = self.db.query(Project).filter(Project.user_id == self.user_a.id).all()
        self.assertEqual(len(saved_projs), 1)
        self.assertEqual(saved_projs[0].name, "Neural Semantic Search")

        saved_skills = self.db.query(UserSkill).filter(UserSkill.user_id == self.user_a.id).all()
        self.assertEqual(len(saved_skills), 2)

        saved_achs = self.db.query(Achievement).filter(Achievement.user_id == self.user_a.id).all()
        self.assertEqual(len(saved_achs), 1)
        self.assertEqual(saved_achs[0].title, "Berkeley ML Hackathon Winner")

    def test_04_candidate_visibility_controls_and_profile_builder(self):
        """Test candidate controls what appears in applications via is_visible flag in build_profile_text."""
        # Add visible and hidden experiences
        exp_visible = CandidateExperience(
            user_id=self.user_a.id,
            company="Tech Giants Corp",
            title="Senior Engineer",
            internship_or_fulltime="fulltime",
            is_visible=True,
            description="Built microservices architecture.",
        )
        exp_hidden = CandidateExperience(
            user_id=self.user_a.id,
            company="Old Confidential Co",
            title="Junior Role",
            internship_or_fulltime="fulltime",
            is_visible=False,
            description="Secret legacy projects.",
        )
        self.db.add_all([exp_visible, exp_hidden])

        # Add visible and hidden projects
        proj_visible = Project(
            user_id=self.user_a.id,
            name="Public Showcase App",
            description="Interactive open-source tool.",
            is_visible=True,
        )
        proj_hidden = Project(
            user_id=self.user_a.id,
            name="Private Hobby Project",
            description="Unfinished prototype.",
            is_visible=False,
        )
        self.db.add_all([proj_visible, proj_hidden])

        # Add education
        edu = CandidateEducation(
            user_id=self.user_a.id,
            institution="MIT",
            degree="Bachelor of Science",
            specialization="Computer Science",
            graduation_year=2025,
            cgpa=3.95,
            coursework=["Algorithms", "Compilers"],
            is_visible=True,
        )
        self.db.add(edu)
        self.db.commit()

        # Build profile text for AI generation
        profile_text = build_profile_text(self.user_a.id, self.db)

        # Visible entities must be present
        self.assertIn("Tech Giants Corp", profile_text)
        self.assertIn("Public Showcase App", profile_text)
        self.assertIn("MIT", profile_text)

        # Hidden entities must NOT appear in AI generation context
        self.assertNotIn("Old Confidential Co", profile_text)
        self.assertNotIn("Private Hobby Project", profile_text)

        # Test toggle visibility via API endpoint
        toggle_res = self.client.put(
            f"/api/v1/profile/experiences/{exp_visible.id}/visibility",
            json={"is_visible": False},
        )
        self.assertEqual(toggle_res.status_code, 200)
        self.assertFalse(toggle_res.json()["is_visible"])

        # After toggling off, Tech Giants Corp should now be excluded
        refreshed_text = build_profile_text(self.user_a.id, self.db)
        self.assertNotIn("Tech Giants Corp", refreshed_text)

    def test_05_education_crud_endpoints(self):
        """Test CandidateEducation CRUD endpoints."""
        # 1. Create education
        create_payload = {
            "degree": "Master of Science",
            "institution": "Carnegie Mellon University",
            "specialization": "Robotics",
            "start_year": 2024,
            "graduation_year": 2026,
            "cgpa": 3.96,
            "coursework": ["Kinematics", "SLAM", "Deep Reinforcement Learning"],
            "location": "Pittsburgh, PA",
            "is_visible": True,
        }
        res = self.client.post("/api/v1/profile/educations", json=create_payload)
        self.assertEqual(res.status_code, 200)
        edu_id = res.json()["id"]
        self.assertEqual(res.json()["institution"], "Carnegie Mellon University")

        # 2. Update education
        update_payload = {
            **create_payload,
            "cgpa": 4.0,
            "graduation_year": 2025,
        }
        up_res = self.client.put(f"/api/v1/profile/educations/{edu_id}", json=update_payload)
        self.assertEqual(up_res.status_code, 200)
        self.assertEqual(up_res.json()["cgpa"], 4.0)
        self.assertEqual(up_res.json()["graduation_year"], 2025)

        # 3. Toggle visibility
        vis_res = self.client.put(f"/api/v1/profile/educations/{edu_id}/visibility", json={"is_visible": False})
        self.assertEqual(vis_res.status_code, 200)
        self.assertFalse(vis_res.json()["is_visible"])

        # 4. Delete education
        del_res = self.client.delete(f"/api/v1/profile/educations/{edu_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertIsNone(self.db.query(CandidateEducation).filter(CandidateEducation.id == edu_id).first())

    def test_06_multiple_resume_versions_and_master_distinction(self):
        """Test distinction between master profile and individual resume versions with version history."""
        # 1. Create base resume in DB
        base_resume = ResumeVersion(
            user_id=self.user_a.id,
            name="Original Uploaded Resume",
            storage_path="private/resumes/orig.pdf",
            file_type="pdf",
            is_master=True,
            version_number=1,
            target_role="Full Stack Engineer",
        )
        self.db.add(base_resume)
        self.db.commit()

        # 2. Create second version variant for AI/ML roles via API
        v2_payload = {
            "name": "Machine Learning Specialist",
            "target_role": "AI/ML Engineer",
            "notes": "Tailored for applied AI roles",
            "base_resume_id": base_resume.id,
            "selected_projects": [],
            "selected_experiences": [],
        }
        v2_res = self.client.post("/api/v1/resume/versions", json=v2_payload)
        self.assertEqual(v2_res.status_code, 200)
        v2_id = v2_res.json()["id"]
        self.assertEqual(v2_res.json()["version_number"], 2)
        self.assertFalse(v2_res.json()["is_master"])

        # Verify version list
        versions_res = self.client.get("/api/v1/resume/versions")
        self.assertEqual(versions_res.status_code, 200)
        self.assertEqual(len(versions_res.json()), 2)

        # 3. Promote v2 to master -> base_resume must automatically lose is_master flag
        set_master_res = self.client.post(f"/api/v1/resume/versions/{v2_id}/set-master")
        self.assertEqual(set_master_res.status_code, 200)
        self.assertTrue(set_master_res.json()["is_master"])

        # Verify in DB
        self.db.refresh(base_resume)
        v2_db = self.db.query(ResumeVersion).filter(ResumeVersion.id == v2_id).first()
        self.assertFalse(base_resume.is_master)
        self.assertTrue(v2_db.is_master)

    def test_07_user_ownership_backend_isolation(self):
        """Enforce strict backend ownership isolation: User B cannot view or modify User A's data."""
        # User A creates a resume version
        v_a = ResumeVersion(
            user_id=self.user_a.id,
            name="User A Private Resume",
            storage_path="private/user_a/resume.pdf",
            file_type="pdf",
            target_role="Confidential Role",
            is_master=True,
            version_number=1,
        )
        # User A creates an education record
        edu_a = CandidateEducation(
            user_id=self.user_a.id,
            institution="User A University",
            degree="BSc",
        )
        self.db.add_all([v_a, edu_a])
        self.db.commit()

        # Switch active user to User B
        self.current_user = self.user_b

        # User B lists versions -> must NOT see User A's resume
        b_versions = self.client.get("/api/v1/resume/versions").json()
        self.assertEqual(len(b_versions), 0)

        # User B tries to view User A's preview -> 404
        b_preview = self.client.get(f"/api/v1/resume/{v_a.id}/preview")
        self.assertEqual(b_preview.status_code, 404)

        # User B tries to set master on User A's resume -> 404
        b_set_master = self.client.post(f"/api/v1/resume/versions/{v_a.id}/set-master")
        self.assertEqual(b_set_master.status_code, 404)

        # User B tries to delete User A's education -> 404
        b_del_edu = self.client.delete(f"/api/v1/profile/educations/{edu_a.id}")
        self.assertEqual(b_del_edu.status_code, 404)

        # Verify User A's records remain untouched
        self.assertIsNotNone(self.db.query(ResumeVersion).filter(ResumeVersion.id == v_a.id).first())
        self.assertIsNotNone(self.db.query(CandidateEducation).filter(CandidateEducation.id == edu_a.id).first())


if __name__ == "__main__":
    unittest.main()
