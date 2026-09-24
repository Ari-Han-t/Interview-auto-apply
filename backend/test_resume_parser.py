import os
import sys
from datetime import datetime

# Setup environment
sys.path.append(os.path.dirname(__file__))

env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value.strip('"\'')

sys.stdout.reconfigure(encoding='utf-8')

from app.core.database import SessionLocal
from app.models.base import Base
from app.models.user import User
from app.models.profile import Profile
from app.models.candidate import UserProfile, CandidateExperience, Project, UserSkill, Skill
from app.services.ai.parser import parse_resume_to_profile
from app.services.ai.profile_builder import build_profile_text
from app.services.ai.matcher import analyze_job_match
from app.services.ai.generator import generate_tailored_resume

def run_tests():
    print("=== STARTING RESUME PARSER & PROFILE INTEGRATION TESTS ===")
    
    db = SessionLocal()
    try:
        # Create test user
        test_email = f"test_parser_{datetime.now().strftime('%H%M%S')}@example.com"
        user = User(email=test_email, hashed_password="hashedpassword123")
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"[OK] Created test user: {user.id} ({user.email})")

        profile = Profile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        print(f"[OK] Created Profile record ID: {profile.id}")

        # Read actual resume.tex
        resume_tex_path = os.path.join(os.path.dirname(__file__), "resume.tex")
        with open(resume_tex_path, "r", encoding="utf-8") as f:
            resume_text = f.read()

        profile.raw_resume_text = resume_text
        profile.latex_template = resume_text
        db.commit()

        print("\n--- 1. Parsing Resume to Profile via LLM ---")
        parse_resume_to_profile(profile.id, resume_text)

        # Verify populated records in DB
        db.refresh(profile)
        user_prof = db.query(UserProfile).filter(UserProfile.user_id == user.id).first()
        experiences = db.query(CandidateExperience).filter(CandidateExperience.user_id == user.id).all()
        projects = db.query(Project).filter(Project.user_id == user.id).all()
        user_skills = db.query(UserSkill).filter(UserSkill.user_id == user.id).all()

        print(f"UserProfile Full Name: {user_prof.full_name if user_prof else None}")
        print(f"UserProfile Email: {user_prof.email if user_prof else None}")
        print(f"UserProfile Degree: {user_prof.degree if user_prof else None} from {user_prof.university if user_prof else None}")
        print(f"UserProfile Graduation Year: {user_prof.graduation_year if user_prof else None}")
        print(f"Candidate Experiences count: {len(experiences)}")
        print(f"Candidate Projects count: {len(projects)}")
        print(f"Candidate Skills count: {len(user_skills)}")
        
        # Verify JSON fields in Profile
        print(f"Profile JSON Projects count: {len(profile.projects_json or [])}")
        print(f"Profile JSON Skills count: {len(profile.skills_json or [])}")

        assert user_prof is not None, "UserProfile was not created!"
        assert len(projects) > 0, "No projects extracted!"
        assert len(user_skills) > 0, "No skills extracted!"
        assert profile.projects_json is not None, "Profile.projects_json was not set!"

        print("\n--- 2. Building Profile Text from Normalized DB ---")
        profile_text = build_profile_text(user.id, db)
        print("Generated Profile Text Preview:")
        print(profile_text[:300] + "...\n")

        print("\n--- 3. Testing Job Match Analysis with Parsed Profile ---")
        job_desc = "Looking for a Backend & AI Engineer experienced with Python, FastAPI, PostgreSQL, Redis, Kafka, and LLM integrations."
        match_result = analyze_job_match(
            profile_text=profile_text,
            job_description=job_desc,
            projects_meta=profile.projects_json,
            latex_resume=profile.latex_template
        )
        print("Job Match Percentage:", match_result.get("match_percentage"))
        print("Strengths:", match_result.get("strengths"))
        assert match_result.get("match_percentage", 0) > 0, "Match percentage is 0!"

        print("\n--- 4. Testing Tailored Resume Generation (LaTeX) ---")
        extracted_projects = profile.projects_json
        skills_list = [us.skill.name for us in user_skills]
        tailored_tex = generate_tailored_resume(
            master_profile=profile.latex_template,
            job_description=job_desc,
            job_title="Backend & AI Engineer",
            is_latex=True,
            extracted_projects=extracted_projects,
            original_skills=skills_list
        )
        print("Tailored LaTeX resume length:", len(tailored_tex))
        assert "\\documentclass" in tailored_tex or "\\begin" in tailored_tex, "Generated LaTeX is invalid!"

        print("\n=== ALL RESUME PARSER & INTEGRATION TESTS PASSED SUCCESSFULLY! ===")
    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
