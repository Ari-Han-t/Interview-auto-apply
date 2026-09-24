import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Setup path so app is importable
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app.models.base import Base
from app.models.user import User
from app.models.job import Job
from app.models.candidate import (
    UserProfile,
    CandidateExperience,
    UserPreference,
    CandidateCapability,
    JobRequirement
)
from app.services.ai.eligibility import evaluate_eligibility

# Setup in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def run_tests():
    print("Running eligibility engine unit tests...")
    
    # Initialize DB schema
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    try:
        # Test Case 1: Experience Mismatch
        print("- Test Case 1: Experience mismatch filtering...")
        user1 = User(email="user1@example.com", hashed_password="mock_password")
        db.add(user1)
        db.flush()
        
        profile1 = UserProfile(user_id=user1.id, degree="Bachelors")
        db.add(profile1)
        
        # 8 months experience (0.67 years)
        exp1 = CandidateExperience(
            user_id=user1.id,
            company="Tech Corp",
            title="Software Engineer",
            months_of_experience=8,
            internship_or_fulltime="fulltime"
        )
        db.add(exp1)
        
        caps1 = CandidateCapability(
            user_id=user1.id,
            can_relocate=True,
            can_work_remote=True,
            can_do_internship=True,
            can_do_fulltime=True,
            has_work_authorization=True,
            needs_sponsorship=False
        )
        db.add(caps1)
        
        prefs1 = UserPreference(
            user_id=user1.id,
            minimum_salary=0,
            preferred_job_type="both"
        )
        db.add(prefs1)
        
        # Job requiring 2-4 years
        job1 = Job(title="Mid-Level Engineer", company="Enterprise Inc")
        db.add(job1)
        db.flush()
        
        req1 = JobRequirement(
            job_id=job1.id,
            minimum_experience=2,
            maximum_experience=4,
            minimum_degree="Bachelors",
            visa_required=False
        )
        db.add(req1)
        db.commit()
        
        res1 = evaluate_eligibility(user1.id, job1.id, db)
        assert res1["eligible"] is False, f"Should be ineligible due to experience mismatch: {res1}"
        assert "experience" in res1["reason"].lower(), f"Unexpected reason: {res1['reason']}"
        print("  [PASSED]")

        # Test Case 2: Internship eligibility
        print("- Test Case 2: Internship eligibility check...")
        job2 = Job(title="Engineering Intern", company="Enterprise Inc")
        db.add(job2)
        db.flush()
        
        req2 = JobRequirement(
            job_id=job2.id,
            minimum_experience=0,
            maximum_experience=1,
            minimum_degree="Bachelors",
            visa_required=False,
            internship=True,
            fulltime=False
        )
        db.add(req2)
        db.commit()
        
        res2 = evaluate_eligibility(user1.id, job2.id, db)
        assert res2["eligible"] is True, f"Should be eligible for internship: {res2['reason']}"
        print("  [PASSED]")

        # Test Case 3: Degree Mismatch
        print("- Test Case 3: Degree mismatch filtering...")
        user3 = User(email="user3@example.com", hashed_password="mock_password")
        db.add(user3)
        db.flush()
        
        profile3 = UserProfile(user_id=user3.id, degree="Bachelors")
        db.add(profile3)
        
        caps3 = CandidateCapability(user_id=user3.id, has_work_authorization=True, needs_sponsorship=False)
        db.add(caps3)
        prefs3 = UserPreference(user_id=user3.id, minimum_salary=0)
        db.add(prefs3)
        
        # Job requiring Masters degree
        job3 = Job(title="Research Scientist", company="Lab Corp")
        db.add(job3)
        db.flush()
        
        req3 = JobRequirement(
            job_id=job3.id,
            minimum_experience=0,
            minimum_degree="Masters",
            visa_required=False
        )
        db.add(req3)
        db.commit()
        
        res3 = evaluate_eligibility(user3.id, job3.id, db)
        assert res3["eligible"] is False, "Should be ineligible due to degree level mismatch"
        assert "degree" in res3["reason"].lower(), f"Unexpected reason: {res3['reason']}"
        print("  [PASSED]")

        # Test Case 4: Visa Sponsorship Mismatch
        print("- Test Case 4: Visa sponsorship filtering...")
        user4 = User(email="user4@example.com", hashed_password="mock_password")
        db.add(user4)
        db.flush()
        
        profile4 = UserProfile(user_id=user4.id)
        db.add(profile4)
        
        caps4 = CandidateCapability(user_id=user4.id, needs_sponsorship=True, has_work_authorization=False)
        db.add(caps4)
        
        prefs4 = UserPreference(user_id=user4.id, minimum_salary=0)
        db.add(prefs4)
        
        # Job that requires work auth / visa required is True for sponsorship check
        job4 = Job(title="Security Developer", company="GovTech")
        db.add(job4)
        db.flush()
        
        req4 = JobRequirement(
            job_id=job4.id,
            minimum_experience=0,
            visa_required=True
        )
        db.add(req4)
        db.commit()
        
        res4 = evaluate_eligibility(user4.id, job4.id, db)
        assert res4["eligible"] is False, "Should be ineligible due to sponsorship requirements"
        assert "sponsorship" in res4["reason"].lower(), f"Unexpected reason: {res4['reason']}"
        print("  [PASSED]")

        print("\nAll eligibility engine integration tests completed successfully!")
        
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

if __name__ == "__main__":
    run_tests()
