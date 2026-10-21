import os
import sys
import json
import unittest
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.user import User
from app.models.job import Job
from app.models.application import Application
from app.models.resume import ResumeVersion
from app.models.candidate import (
    UserProfile,
    CandidateEducation,
    CandidateExperience,
    Project,
    UserSkill,
    Skill,
    Achievement,
    CourseCertification,
    CandidateLeadership,
    CandidateCoursework,
    CandidatePublication,
    CandidateCustomSection,
)

from app.services.resume_compiler.escaper import escape_latex, format_latex_url
from app.services.resume_compiler.candidate_data import load_candidate_library, normalize_bullets, MODULE_KEYS
from app.services.resume_compiler.assembly_engine import (
    generate_assembly_plan,
    detect_candidate_level,
    detect_role_type,
    score_item_relevance
)
from app.services.resume_compiler.refiner import refine_bullet_truthfully, compute_text_diff
from app.services.resume_compiler.templates import list_templates, get_template
from app.services.resume_compiler.renderer import render_modular_resume
from app.services.resume_compiler.compiler import (
    compile_latex_securely,
    extract_and_validate_pdf_readability,
    create_source_archive
)
from app.services.resume_compiler.version_service import (
    save_immutable_resume_version,
    compare_resume_versions
)


class TestModularResumeSystem(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.Session()
        self._seed_data()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _seed_data(self):
        # 1. User
        self.user = User(email="alex.chen@example.com", hashed_password="hashed_pw", is_active=True)
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        # 2. General info
        prof = UserProfile(
            user_id=self.user.id,
            full_name="Alex Chen",
            preferred_name="Alex",
            email="alex.chen@example.com",
            phone="+1 (555) 234-5678",
            github="https://github.com/alexchen",
            linkedin="https://linkedin.com/in/alexchen",
            website="https://alexchen.dev",
            current_location="Seattle, WA",
            university="University of Washington",
            degree="B.S. in Computer Science",
            specialization="Distributed Systems",
            cgpa="3.88",
            graduation_year=2024,
        )
        self.db.add(prof)

        # 3. Education
        edu = CandidateEducation(
            user_id=self.user.id,
            institution="University of Washington",
            degree="B.S. in Computer Science",
            specialization="Distributed Systems",
            location="Seattle, WA",
            start_year="2020",
            graduation_year="2024",
            cgpa="3.88",
            gpa_scale="4.0",
            honors="Magna Cum Laude",
            bullets=["Dean's List all 8 semesters", "Teaching Assistant for Distributed Systems (CSE 452)"],
        )
        self.db.add(edu)

        # 4. Experience
        exp1 = CandidateExperience(
            user_id=self.user.id,
            company="Stripe",
            title="Backend Engineering Intern",
            location="Seattle, WA",
            start_date="Jun 2023",
            end_date="Sep 2023",
            currently_working=False,
            technologies=["Python", "Go", "PostgreSQL", "Kafka", "Docker"],
            bullets=[
                "Architected asynchronous webhook ingestion engine handling 12,000 requests/sec with zero dropped events",
                "Optimized SQL query execution plans in PostgreSQL, reducing P99 query latency from 240ms to 38ms",
                "Wrote end-to-end integration tests using Docker containers to maintain 94% test coverage"
            ]
        )
        exp2 = CandidateExperience(
            user_id=self.user.id,
            company="UW Cloud Computing Lab",
            title="Undergraduate Research Assistant",
            location="Seattle, WA",
            start_date="Jan 2023",
            end_date="May 2023",
            currently_working=False,
            technologies=["Rust", "Raft", "gRPC"],
            bullets=[
                "Implemented Raft consensus algorithm in Rust for replicated state machine experiments",
                "Benchmarked leader election failover under simulated network partitions across 5 AWS nodes"
            ]
        )
        self.db.add_all([exp1, exp2])

        # 5. Projects
        proj1 = Project(
            user_id=self.user.id,
            name="AutoApply Distributed Job Matcher",
            role="Lead Systems Developer",
            technologies=["Python", "FastAPI", "PostgreSQL", "Redis", "Celery"],
            github="https://github.com/alexchen/auto-apply",
            live_link="https://autoapply.demo",
            problem="High-latency matching over 50,000 job descriptions",
            bullets=[
                "Engineered concurrent job processing pipeline using Redis queue and Celery workers",
                "Benchmarked matching accuracy using vector cosine similarity achieving 89% precision",
                "Deployed production service on Kubernetes with automated health checking and horizontal autoscaling"
            ]
        )
        proj2 = Project(
            user_id=self.user.id,
            name="Distributed Key-Value Store",
            role="Author",
            technologies=["Go", "Raft", "gRPC", "Protobuf"],
            github="https://github.com/alexchen/dist-kv",
            bullets=[
                "Built linearizable distributed key-value store with sharded partitions and multi-Raft consensus",
                "Integrated gRPC transport layer achieving 18,000 IOPS per cluster node"
            ]
        )
        self.db.add_all([proj1, proj2])

        # 6. Skills
        sk_names = [
            ("Python", "Languages"), ("Go", "Languages"), ("Rust", "Languages"), ("SQL", "Languages"),
            ("FastAPI", "Frameworks"), ("Docker", "Infrastructure"), ("Kubernetes", "Infrastructure"),
            ("PostgreSQL", "Databases"), ("Redis", "Databases"), ("Kafka", "Distributed Systems")
        ]
        for s_name, cat in sk_names:
            sk_obj = Skill(name=s_name)
            self.db.add(sk_obj)
            self.db.flush()
            u_sk = UserSkill(user_id=self.user.id, skill_id=sk_obj.id, category=cat, proficiency_level="Advanced")
            self.db.add(u_sk)

        # 7. Achievements
        ach = Achievement(
            user_id=self.user.id,
            title="1st Place - DubHacks 2023",
            issuer_or_event="DubHacks",
            year_or_date="2023",
            description="Won 1st place out of 800+ participants for building real-time collaborative code editor.",
            bullets=["Built WebRTC data mesh connecting 50 concurrent editors without central coordinator"]
        )
        self.db.add(ach)

        # 8. Certifications
        cert = CourseCertification(
            user_id=self.user.id,
            name="AWS Certified Solutions Architect",
            issuer="Amazon Web Services",
            issue_date="2023",
            skills_covered=["AWS", "VPC", "EC2", "S3", "IAM"],
            bullets=["Certified in cloud architecture and secure multi-tier system designs"]
        )
        self.db.add(cert)

        # 9. Leadership
        lead = CandidateLeadership(
            user_id=self.user.id,
            organization="ACM Student Chapter",
            role="Vice President",
            start_date="2022",
            end_date="2024",
            bullets=["Organized technical workshops for 200+ undergraduate CS students on systems design"]
        )
        self.db.add(lead)

        # 10. Coursework
        course = CandidateCoursework(
            user_id=self.user.id,
            course_name="Distributed Systems",
            course_code="CSE 452",
            grade="4.0",
            term_or_year="Spring 2023"
        )
        self.db.add(course)

        # 11. Publications
        pub = CandidatePublication(
            user_id=self.user.id,
            title="Towards Scalable Consensus in Edge Computing Environments",
            venue_or_publisher="IEEE CloudCom 2023",
            publication_date="2023",
            bullets=["Analyzed Raft consensus latency bounds across heterogeneous network latency distributions"]
        )
        self.db.add(pub)

        # 12. Custom Sections
        custom = CandidateCustomSection(
            user_id=self.user.id,
            section_title="Open Source Contributions",
            title="Contributor to Apache Arrow",
            date_or_year="2023",
            bullets=["Contributed Python binding fixes for memory-mapped IPC streaming"]
        )
        self.db.add(custom)

        # Target Job
        self.job = Job(
            title="Junior Backend Engineer",
            company="Vercel",
            description="We are looking for a backend engineer passionate about high-concurrency APIs, distributed systems, Python, Go, and PostgreSQL.",
            required_skills_json=["Python", "Go", "PostgreSQL", "Distributed Systems", "Docker"],
            tech_stack_json=["Python", "Go", "PostgreSQL", "Redis", "Kafka"]
        )
        self.db.add(self.job)
        self.db.commit()
        self.db.refresh(self.job)

    def test_latex_escaper(self):
        """Validates secure LaTeX character escaping without altering macros."""
        raw = "Working with R&D & 100% test coverage! Costs: $500, Hash: #1, Path: user_id & {param} ~ ^ \\"
        escaped = escape_latex(raw)
        self.assertIn(r"\&", escaped)
        self.assertIn(r"\%", escaped)
        self.assertIn(r"\$", escaped)
        self.assertIn(r"\#", escaped)
        self.assertIn(r"\_", escaped)
        self.assertIn(r"\{", escaped)
        self.assertIn(r"\}", escaped)

        url_tex = format_latex_url("https://github.com/alexchen", "GitHub Profile")
        self.assertEqual(r"\href{https://github.com/alexchen}{GitHub Profile}", url_tex)

    def test_candidate_data_extraction_11_modules(self):
        """Verifies that all 11 modules are extracted with stable IDs and normalized bullets."""
        library = load_candidate_library(self.user.id, self.db)

        self.assertTrue(set(MODULE_KEYS).issubset(set(library.keys())))
        self.assertEqual(library["general_info"]["full_name"], "Alex Chen")
        self.assertEqual(len(library["education"]), 1)
        self.assertEqual(len(library["experience"]), 2)
        self.assertEqual(len(library["projects"]), 2)
        self.assertEqual(len(library["skills"]), 10)
        self.assertEqual(len(library["achievements"]), 1)
        self.assertEqual(len(library["certifications"]), 1)
        self.assertEqual(len(library["leadership"]), 1)
        self.assertEqual(len(library["coursework"]), 1)
        self.assertEqual(len(library["publications"]), 1)
        self.assertEqual(len(library["custom_sections"]), 1)

        # Verify bullet normalization
        proj = library["projects"][0]
        self.assertEqual(len(proj["bullets"]), 3)
        self.assertTrue(all("id" in b and "text" in b for b in proj["bullets"]))

    def test_assembly_planning_and_seniority(self):
        """Tests AI assembly plan creation, seniority detection, ranking, and user locks."""
        library = load_candidate_library(self.user.id, self.db)
        job_dict = {
            "id": self.job.id,
            "title": self.job.title,
            "company": self.job.company,
            "description": self.job.description,
            "required_skills_json": self.job.required_skills_json,
        }

        # Generate plan
        plan = generate_assembly_plan(
            candidate_data=library,
            job=job_dict,
            target_page_length=1
        )

        self.assertEqual(plan["role_category"], "backend")
        self.assertEqual(plan["candidate_level"], "early_career")
        self.assertIn("general_info", plan["sections"])
        self.assertTrue(plan["sections"]["education"]["included"])
        self.assertTrue(plan["sections"]["projects"]["included"])
        self.assertTrue(plan["sections"]["skills"]["included"])

        # User locks: lock section order and specific project
        locked_order = ["general_info", "experience", "projects", "education", "skills"]
        user_locks = {
            "locked_sections": ["certifications"],
            "locked_order": locked_order,
            "locked_items": {"projects": [library["projects"][1]["id"]]}
        }
        plan_with_locks = generate_assembly_plan(
            candidate_data=library,
            job=job_dict,
            user_locks=user_locks
        )

        self.assertEqual(plan_with_locks["section_order"][:5], locked_order)
        self.assertTrue(plan_with_locks["sections"]["certifications"]["locked"])
        self.assertEqual(plan_with_locks["sections"]["projects"]["selected_item_ids"], [library["projects"][1]["id"]])

    def test_truth_preserving_refinement(self):
        """Validates that bullet refinement enhances action verbs without hallucinating facts."""
        original = "Worked on webhooks handling 12000 requests per second in Python."
        res = refine_bullet_truthfully(
            original_bullet=original,
            job_requirement="Python high concurrency APIs",
            job_title="Backend Engineer",
            context_name="Stripe"
        )

        self.assertIn(res["status"], ("refined", "original"))
        self.assertTrue("12" in res["refined_bullet"] or "12000" in res["refined_bullet"])
        self.assertTrue(len(res["diff"]) > 0)
        self.assertIn("reason", res)

    def test_all_five_latex_templates_rendering(self):
        """Verifies that all 5 ATS-compliant templates compile controlled LaTeX without raw errors."""
        library = load_candidate_library(self.user.id, self.db)
        job_dict = {"id": self.job.id, "title": self.job.title, "company": self.job.company, "description": self.job.description}
        plan = generate_assembly_plan(library, job_dict)

        template_keys = [
            "clean_ats",
            "compact_technical",
            "traditional_professional",
            "academic_research",
            "project_focused",
        ]

        for t_key in template_keys:
            tex = render_modular_resume(
                candidate_data=library,
                assembly_plan=plan,
                template_name=t_key
            )
            self.assertIn(r"\documentclass", tex)
            self.assertIn(r"\begin{document}", tex)
            self.assertIn(r"\end{document}", tex)
            self.assertIn("Alex Chen", tex)
            self.assertIn("Stripe", tex)
            self.assertIn("University of Washington", tex)

    def test_compilation_and_readability(self):
        """Validates isolated compilation, ReportLab fallback, and PDF text readability audit."""
        dummy_tex = r"""\documentclass[letterpaper,10.8pt]{article}
\usepackage[utf8]{inputenc}
\begin{document}
\begin{center}
    {\Huge \textbf{Alex Chen}} \\
    \small alex.chen@example.com $|$ +1-555-234-5678 $|$ Seattle, WA
\end{center}
\section{Education}
\resumeSubheading{University of Washington}{2020 -- 2024}{B.S. in Computer Science}{Seattle, WA}
\section{Experience}
\resumeSubheading{Backend Engineering Intern}{Jun 2023 -- Sep 2023}{Stripe}{Seattle, WA}
\resumeItem{Architected asynchronous webhook ingestion engine handling 12,000 requests/sec with zero dropped events.}
\resumeItem{Optimized SQL query execution plans in PostgreSQL, reducing P99 query latency to 38ms.}
\section{Projects}
\resumeProjectHeading{\textbf{AutoApply Distributed Job Matcher} $|$ \emph{Python, Go, Redis}}{2023}
\resumeItem{Engineered concurrent job processing pipeline using Redis queue and Celery workers.}
\resumeItem{Benchmarked matching accuracy using vector cosine similarity achieving 89\% precision.}
\section{Technical Skills}
\resumeItem{\textbf{Languages}: Python, Go, Rust, SQL}
\end{document}
"""
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            output_pdf = os.path.join(td, "compiled_resume.pdf")
            success, msg = compile_latex_securely(dummy_tex, output_pdf)
            self.assertTrue(success)
            self.assertTrue(os.path.exists(output_pdf))
            self.assertGreater(os.path.getsize(output_pdf), 500)

            report = extract_and_validate_pdf_readability(output_pdf)
            self.assertTrue(report["is_readable"])
            self.assertGreaterEqual(report["word_count"], 30)
            self.assertIn("EDUCATION", report["detected_sections"])
            self.assertTrue(report["has_contact_info"])

    def test_source_archive_packaging(self):
        """Tests that create_source_archive packs resume.tex, README.md, and metadata.json."""
        import tempfile
        import zipfile
        with tempfile.TemporaryDirectory() as td:
            tex_code = r"\documentclass{article}\begin{document}Resume Test\end{document}"
            output_zip = os.path.join(td, "resume_source.zip")
            meta = {"job_title": "Backend Engineer", "company": "Vercel", "version": 1}

            create_source_archive(tex_code, output_zip, meta)
            self.assertTrue(os.path.exists(output_zip))

            with zipfile.ZipFile(output_zip, "r") as zf:
                names = zf.namelist()
                self.assertIn("resume.tex", names)
                self.assertIn("README.md", names)
                self.assertIn("metadata.json", names)
                read_meta = json.loads(zf.read("metadata.json").decode("utf-8"))
                self.assertEqual(read_meta["company"], "Vercel")

    def test_immutable_version_persistence_and_diff(self):
        """Tests saving immutable versions linked to Job and computing before/after diffs."""
        library = load_candidate_library(self.user.id, self.db)
        job_dict = {"id": self.job.id, "title": self.job.title, "company": self.job.company, "description": self.job.description}
        plan = generate_assembly_plan(library, job_dict)
        tex_v1 = render_modular_resume(library, plan, template_name="clean_ats")

        # Save Version 1
        v1 = save_immutable_resume_version(
            db=self.db,
            user_id=self.user.id,
            job_id=self.job.id,
            application_id=None,
            name="Vercel - Clean ATS v1",
            latex_source=tex_v1,
            assembly_plan=plan,
            template_name="clean_ats",
        )
        self.assertEqual(v1.version_number, 1)
        self.assertEqual(v1.job_id, self.job.id)

        # Create modified plan for Version 2: switch template and reorder
        plan_v2 = dict(plan)
        plan_v2["template_name"] = "compact_technical"
        plan_v2["section_order"] = ["general_info", "experience", "projects", "skills", "education"]
        tex_v2 = render_modular_resume(library, plan_v2, template_name="compact_technical")

        v2 = save_immutable_resume_version(
            db=self.db,
            user_id=self.user.id,
            job_id=self.job.id,
            application_id=None,
            name="Vercel - Compact Technical v2",
            latex_source=tex_v2,
            assembly_plan=plan_v2,
            template_name="compact_technical",
            parent_version_id=v1.id
        )
        self.assertEqual(v2.version_number, 2)
        self.assertEqual(v2.parent_version_id, v1.id)

        # Compute Diff between Version 1 and Version 2
        diff = compare_resume_versions(self.db, v1.id, v2.id)
        self.assertEqual(diff["v1"]["version_number"], 1)
        self.assertEqual(diff["v2"]["version_number"], 2)
        self.assertTrue(diff["template_changed"])
        self.assertTrue(diff["order_changed"])


class TestModularResumeAPIEndpoints(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from app.main import app
        from app.api.auth import get_current_user
        from app.core.database import get_db

        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.Session()

        # Seed minimal user and job
        self.user = User(email="test.alex@example.com", hashed_password="hashed_pw", is_active=True)
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        prof = UserProfile(
            user_id=self.user.id,
            full_name="Alex Chen",
            email="test.alex@example.com",
            graduation_year=2024,
        )
        self.db.add(prof)

        edu = CandidateEducation(
            user_id=self.user.id,
            institution="UW",
            degree="B.S. CS",
            graduation_year=2024,
            bullets=["Dean's List"]
        )
        self.db.add(edu)

        proj = Project(
            user_id=self.user.id,
            name="Distributed Cache",
            technologies=["Go", "Redis"],
            bullets=["Built high throughput LRU cache"]
        )
        self.db.add(proj)

        self.job = Job(
            title="Backend Software Engineer",
            company="Stripe",
            description="Distributed backend systems with Go and Redis",
            required_skills_json=["Go", "Redis", "Distributed Systems"]
        )
        self.db.add(self.job)
        self.db.commit()
        self.db.refresh(self.job)

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
        from app.main import app
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_modular_resume_pipeline_api(self):
        """End-to-end API test: modules -> plan -> render -> compile -> save -> version list."""
        # 1. Candidate modules
        res_mods = self.client.get("/api/v1/modular-resume/candidate-modules")
        self.assertEqual(res_mods.status_code, 200)
        mods_data = res_mods.json()
        self.assertEqual(len(mods_data["module_keys"]), 11)

        # 2. Templates
        res_tpls = self.client.get("/api/v1/modular-resume/templates")
        self.assertEqual(res_tpls.status_code, 200)
        self.assertEqual(len(res_tpls.json()), 5)

        # 3. Create Plan
        res_plan = self.client.post(
            f"/api/v1/modular-resume/plan/{self.job.id}",
            json={"target_page_length": 1}
        )
        self.assertEqual(res_plan.status_code, 200)
        plan = res_plan.json()
        self.assertIn("sections", plan)
        self.assertIn("section_order", plan)

        # 4. Render LaTeX
        res_render = self.client.post(
            "/api/v1/modular-resume/render",
            json={
                "assembly_plan": plan,
                "template_name": "clean_ats"
            }
        )
        self.assertEqual(res_render.status_code, 200)
        tex_source = res_render.json()["latex_source"]
        self.assertIn(r"\begin{document}", tex_source)

        # 5. Compile LaTeX
        res_compile = self.client.post(
            "/api/v1/modular-resume/compile",
            json={
                "latex_source": tex_source,
                "job_id": self.job.id
            }
        )
        self.assertEqual(res_compile.status_code, 200)
        compile_data = res_compile.json()
        self.assertTrue(compile_data["success"])
        self.assertIn("preview_url", compile_data)

        # 6. Save Immutable Version
        res_save = self.client.post(
            "/api/v1/modular-resume/save-version",
            json={
                "job_id": self.job.id,
                "name": "Stripe Backend Resume",
                "latex_source": tex_source,
                "assembly_plan": plan,
                "template_name": "clean_ats",
                "notes": "Tailored for Stripe Distributed Systems"
            }
        )
        self.assertEqual(res_save.status_code, 200)
        saved_ver = res_save.json()
        v_id = saved_ver["id"]
        self.assertEqual(saved_ver["version_number"], 1)

        # 7. List versions for job
        res_list = self.client.get(f"/api/v1/modular-resume/versions/{self.job.id}")
        self.assertEqual(res_list.status_code, 200)
        self.assertEqual(len(res_list.json()), 1)

        # 8. Resume API routes (/api/v1/resume/...)
        res_plan_alt = self.client.post(
            "/api/v1/resume/plan",
            json={"job_id": self.job.id}
        )
        self.assertEqual(res_plan_alt.status_code, 200)

        res_lib = self.client.get("/api/v1/resume/candidate-library")
        self.assertEqual(res_lib.status_code, 200)
        self.assertIn("candidate_data", res_lib.json())

        res_tpls_alt = self.client.get("/api/v1/resume/templates")
        self.assertEqual(res_tpls_alt.status_code, 200)


if __name__ == "__main__":
    unittest.main()
