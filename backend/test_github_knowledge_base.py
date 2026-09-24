import os
import sys
from datetime import datetime

sys.path.append(os.path.dirname(__file__))

env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value.strip('"\'')

sys.stdout.reconfigure(encoding='utf-8')

from app.core.database import SessionLocal, engine
from app.models import Base
from app.models.user import User
from app.models.profile import Profile
from app.models.candidate import UserProfile, CandidateExperience, Project, UserSkill, Skill, Achievement, CourseCertification
from app.services.ai.profile_builder import build_profile_text
from app.services.ai.generator import generate_tailored_resume

def run_tests():
    print("=== STARTING MASTER KNOWLEDGE BASE & GITHUB SYNC INTEGRATION TESTS ===")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Create test user
        test_email = f"test_kb_{datetime.now().strftime('%H%M%S')}@example.com"
        user = User(email=test_email, hashed_password="hashedpassword123")
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"[OK] Created test user: {user.id} ({user.email})")

        profile = Profile(user_id=user.id, github_username="octocat")
        db.add(profile)
        
        user_prof = UserProfile(
            user_id=user.id,
            full_name="Arihant Gupta",
            email=user.email,
            github="https://github.com/Ari-Han-t",
            degree="Bachelors",
            university="VIT"
        )
        db.add(user_prof)
        db.commit()

        print("\n--- 1. Testing Achievements, Wins & Prizes Creation ---")
        ach1 = Achievement(
            user_id=user.id,
            title="1st Place -- DEVSOC 2026 Hackathon",
            category="hackathon",
            issuer_or_event="DEVSOC 2026",
            year_or_date="2026",
            description="Built CAPS dual-layer context-aware payment gateway with real-time AI fraud analysis."
        )
        ach2 = Achievement(
            user_id=user.id,
            title="LeetCode 200+ Solved Badge",
            category="award",
            issuer_or_event="LeetCode",
            year_or_date="2025",
            description="Solved 200+ DSA problems covering graphs, DP, trees, and system design."
        )
        db.add_all([ach1, ach2])

        print("--- 2. Testing Courses & Certifications Creation ---")
        crs1 = CourseCertification(
            user_id=user.id,
            name="Deep Learning Specialization",
            issuer="DeepLearning.AI / Coursera",
            issue_date="2025",
            credential_url="https://coursera.org/verify/dl-spec",
            skills_covered=["PyTorch", "Neural Networks", "CNNs", "Transformers"]
        )
        db.add(crs1)
        db.commit()

        # Add sample projects & skills
        proj1 = Project(
            user_id=user.id,
            name="TrialSight Intelligence",
            description="Multi-user RAG system for clinical trial evidence review with Groq LLM streaming.",
            github="https://github.com/Ari-Han-t/TrialSight",
            live_link="https://trialsight.dev",
            technologies=["FastAPI", "SQLite", "Redis", "Groq", "BM25"]
        )
        db.add(proj1)
        
        def get_or_create_skill(name):
            s = db.query(Skill).filter(Skill.name == name).first()
            if not s:
                s = Skill(name=name)
                db.add(s)
                db.flush()
            return s
            
        sk1 = get_or_create_skill("FastAPI")
        sk2 = get_or_create_skill("Redis")
        
        user_sk1 = UserSkill(user_id=user.id, skill_id=sk1.id, confidence=5, years_used=2.0)
        user_sk2 = UserSkill(user_id=user.id, skill_id=sk2.id, confidence=4, years_used=1.5)
        db.add_all([user_sk1, user_sk2])
        db.commit()

        print("\n--- 3. Verifying Master Knowledge Base Profile Text ---")
        profile_text = build_profile_text(user.id, db)
        print("Master Knowledge Profile Text:")
        print(profile_text)
        print("-" * 50)

        assert "Achievements, Prizes & Hackathon Wins:" in profile_text, "Achievements section missing!"
        assert "1st Place -- DEVSOC 2026 Hackathon" in profile_text, "Hackathon win title missing!"
        assert "Courses & Certifications:" in profile_text, "Courses section missing!"
        assert "Deep Learning Specialization" in profile_text, "Course name missing!"

        print("\n--- 4. Testing Resume Generator with Master Knowledge Base ---")
        resume_tex_path = os.path.join(os.path.dirname(__file__), "resume.tex")
        with open(resume_tex_path, "r", encoding="utf-8") as f:
            sample_tex = f.read()

        master_kb = {
            "achievements_and_prizes": [
                {"title": ach1.title, "event": ach1.issuer_or_event, "details": ach1.description},
                {"title": ach2.title, "event": ach2.issuer_or_event, "details": ach2.description}
            ],
            "courses_and_certifications": [
                {"name": crs1.name, "issuer": crs1.issuer, "skills": crs1.skills_covered}
            ],
            "projects": [
                {"name": proj1.name, "description": proj1.description, "tech": proj1.technologies}
            ],
            "skills": ["FastAPI", "Redis", "Python", "Docker"]
        }

        tailored_resume = generate_tailored_resume(
            master_profile=sample_tex,
            job_description="Looking for an AI & Backend Engineer with FastAPI, Redis, LLM integrations, and a track record of winning hackathons or completing deep learning coursework.",
            job_title="AI & Backend Engineer",
            is_latex=True,
            master_knowledge_base=master_kb
        )

        print(f"Tailored Resume Output Length: {len(tailored_resume)} chars")
        assert len(tailored_resume) > 1000, "Generated resume is empty or too short!"
        assert "\\documentclass" in tailored_resume or "\\begin" in tailored_resume, "Invalid LaTeX resume output!"

        print("\n=== ALL MASTER KNOWLEDGE BASE & GITHUB SYNC TESTS PASSED! ===")

    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
