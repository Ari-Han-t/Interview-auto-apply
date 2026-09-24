from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.profile import Profile
from app.models.candidate import (
    UserProfile,
    CandidateExperience,
    Project,
    Skill,
    UserSkill,
    UserPreference,
    CandidateCapability,
    Achievement,
    CourseCertification
)
from app.api.auth import get_current_user
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

router = APIRouter()

# Schema definitions for requests
class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None
    portfolio: Optional[str] = None
    current_location: Optional[str] = None
    preferred_locations: Optional[List[str]] = []
    work_authorization: Optional[str] = None
    visa_required: Optional[bool] = False
    willing_to_relocate: Optional[bool] = True
    remote_preference: Optional[str] = None
    graduation_year: Optional[int] = None
    degree: Optional[str] = None
    cgpa: Optional[float] = None
    university: Optional[str] = None
    tailoring_instructions: Optional[str] = None

class ExperienceCreateUpdate(BaseModel):
    company: str
    title: str
    internship_or_fulltime: Optional[str] = "fulltime"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    currently_working: Optional[bool] = False
    months_of_experience: Optional[int] = 0
    description: Optional[str] = None

class ProjectCreateUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    github: Optional[str] = None
    live_link: Optional[str] = None
    technologies: Optional[List[str]] = []

class SkillCreate(BaseModel):
    name: str
    confidence: Optional[int] = 5
    years_used: Optional[float] = 0.0

class AchievementCreateUpdate(BaseModel):
    title: str
    category: Optional[str] = "hackathon" # hackathon, award, prize, publication, other
    issuer_or_event: Optional[str] = None
    year_or_date: Optional[str] = None
    description: Optional[str] = None

class CourseCreateUpdate(BaseModel):
    name: str
    issuer: Optional[str] = None
    issue_date: Optional[str] = None
    credential_url: Optional[str] = None
    skills_covered: Optional[List[str]] = []


class PreferencesUpdate(BaseModel):
    minimum_salary: Optional[int] = 0
    maximum_salary: Optional[int] = None
    preferred_locations: Optional[List[str]] = []
    remote_only: Optional[bool] = False
    hybrid_allowed: Optional[bool] = True
    onsite_allowed: Optional[bool] = True
    preferred_roles: Optional[List[str]] = []
    preferred_domains: Optional[List[str]] = []
    company_size: Optional[str] = None
    preferred_industries: Optional[List[str]] = []
    maximum_experience_required: Optional[int] = None
    minimum_experience_required: Optional[int] = None
    exclude_companies: Optional[List[str]] = []
    exclude_keywords: Optional[List[str]] = []
    preferred_job_type: Optional[str] = "both"
    preferred_internship: Optional[bool] = True
    preferred_fulltime: Optional[bool] = True
    notice_period: Optional[int] = 0
    earliest_joining_date: Optional[str] = None
    maximum_daily_applications: Optional[int] = 5

class CapabilitiesUpdate(BaseModel):
    can_relocate: Optional[bool] = True
    can_work_remote: Optional[bool] = True
    can_do_internship: Optional[bool] = True
    can_do_fulltime: Optional[bool] = True
    can_work_parttime: Optional[bool] = True
    can_work_contract: Optional[bool] = True
    can_work_night_shift: Optional[bool] = False
    has_work_authorization: Optional[bool] = True
    needs_sponsorship: Optional[bool] = False
    open_to_startup: Optional[bool] = True
    open_to_enterprise: Optional[bool] = True
    open_to_research: Optional[bool] = True

@router.get("/")
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Returns the complete normalized user profile payload.
    """
    # Ensure profile, capabilities and preferences exist for the user
    user_prof = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not user_prof:
        # Create empty default profile
        user_prof = UserProfile(user_id=current_user.id, email=current_user.email)
        db.add(user_prof)
        db.flush()
        
    capabilities = db.query(CandidateCapability).filter(CandidateCapability.user_id == current_user.id).first()
    if not capabilities:
        capabilities = CandidateCapability(user_id=current_user.id)
        db.add(capabilities)
        db.flush()
        
    preferences = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
    if not preferences:
        preferences = UserPreference(user_id=current_user.id)
        db.add(preferences)
        db.flush()
        
    db.commit()
    
    experiences = db.query(CandidateExperience).filter(CandidateExperience.user_id == current_user.id).all()
    projects = db.query(Project).filter(Project.user_id == current_user.id).all()
    achievements = db.query(Achievement).filter(Achievement.user_id == current_user.id).all()
    courses = db.query(CourseCertification).filter(CourseCertification.user_id == current_user.id).all()
    
    # Skills mapped to user
    user_skills = db.query(UserSkill).filter(UserSkill.user_id == current_user.id).all()
    skills_payload = []
    for us in user_skills:
        skills_payload.append({
            "name": us.skill.name,
            "confidence": us.confidence,
            "years_used": us.years_used
        })
        
    return {
        "profile": user_prof,
        "experiences": experiences,
        "projects": projects,
        "skills": skills_payload,
        "achievements": achievements,
        "courses": courses,
        "preferences": preferences,
        "capabilities": capabilities,
        "tailoring_instructions": (_get_or_create_profile_row(db, current_user.id).tailoring_instructions or ""),
        "github_username": (_get_or_create_profile_row(db, current_user.id).github_username or ""),
    }

@router.put("/")
def update_profile(profile_data: UserProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_prof = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not user_prof:
        user_prof = UserProfile(user_id=current_user.id)
        db.add(user_prof)

    data = profile_data.model_dump(exclude_unset=True)
    # tailoring_instructions lives on the legacy Profile row, not UserProfile
    if "tailoring_instructions" in data:
        profile_row = _get_or_create_profile_row(db, current_user.id)
        raw = data.pop("tailoring_instructions")
        profile_row.tailoring_instructions = (raw or "").strip() or None

    for key, val in data.items():
        if hasattr(user_prof, key):
            setattr(user_prof, key, val)

    db.commit()
    db.refresh(user_prof)
    return user_prof

class TailoringInstructionsUpdate(BaseModel):
    tailoring_instructions: Optional[str] = None

def _get_or_create_profile_row(db: Session, user_id: int) -> Profile:
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        profile = Profile(user_id=user_id)
        db.add(profile)
        db.flush()
    return profile

@router.get("/tailoring-instructions")
def get_tailoring_instructions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = _get_or_create_profile_row(db, current_user.id)
    db.commit()
    return {"tailoring_instructions": profile.tailoring_instructions or ""}

@router.put("/tailoring-instructions")
def update_tailoring_instructions(
    body: TailoringInstructionsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = _get_or_create_profile_row(db, current_user.id)
    profile.tailoring_instructions = (body.tailoring_instructions or "").strip() or None
    db.commit()
    db.refresh(profile)
    return {"tailoring_instructions": profile.tailoring_instructions or ""}

@router.get("/preferences")
def get_preferences(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    preferences = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
    if not preferences:
        preferences = UserPreference(user_id=current_user.id)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)
    return preferences

@router.put("/preferences")
def update_preferences(prefs: PreferencesUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    preferences = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
    if not preferences:
        preferences = UserPreference(user_id=current_user.id)
        db.add(preferences)
        
    for key, val in prefs.model_dump(exclude_unset=True).items():
        setattr(preferences, key, val)
        
    db.commit()
    db.refresh(preferences)
    return preferences

@router.get("/capabilities")
def get_capabilities(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    capabilities = db.query(CandidateCapability).filter(CandidateCapability.user_id == current_user.id).first()
    if not capabilities:
        capabilities = CandidateCapability(user_id=current_user.id)
        db.add(capabilities)
        db.commit()
        db.refresh(capabilities)
    return capabilities

@router.put("/capabilities")
def update_capabilities(caps: CapabilitiesUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    capabilities = db.query(CandidateCapability).filter(CandidateCapability.user_id == current_user.id).first()
    if not capabilities:
        capabilities = CandidateCapability(user_id=current_user.id)
        db.add(capabilities)
        
    for key, val in caps.model_dump(exclude_unset=True).items():
        setattr(capabilities, key, val)
        
    db.commit()
    db.refresh(capabilities)
    return capabilities

# CRUD Experiences
@router.post("/experiences")
def create_experience(exp: ExperienceCreateUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_exp = CandidateExperience(
        user_id=current_user.id,
        **exp.model_dump()
    )
    db.add(new_exp)
    db.commit()
    db.refresh(new_exp)
    return new_exp

@router.put("/experiences/{exp_id}")
def update_experience(exp_id: int, exp: ExperienceCreateUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_exp = db.query(CandidateExperience).filter(CandidateExperience.id == exp_id, CandidateExperience.user_id == current_user.id).first()
    if not db_exp:
        raise HTTPException(status_code=404, detail="Experience record not found")
        
    for key, val in exp.model_dump().items():
        setattr(db_exp, key, val)
        
    db.commit()
    db.refresh(db_exp)
    return db_exp

@router.delete("/experiences/{exp_id}")
def delete_experience(exp_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_exp = db.query(CandidateExperience).filter(CandidateExperience.id == exp_id, CandidateExperience.user_id == current_user.id).first()
    if not db_exp:
        raise HTTPException(status_code=404, detail="Experience record not found")
        
    db.delete(db_exp)
    db.commit()
    return {"message": "Experience record deleted"}

# CRUD Projects
@router.post("/projects")
def create_project(proj: ProjectCreateUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_proj = Project(
        user_id=current_user.id,
        **proj.model_dump()
    )
    db.add(new_proj)
    db.commit()
    db.refresh(new_proj)
    return new_proj

@router.put("/projects/{proj_id}")
def update_project(proj_id: int, proj: ProjectCreateUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_proj = db.query(Project).filter(Project.id == proj_id, Project.user_id == current_user.id).first()
    if not db_proj:
        raise HTTPException(status_code=404, detail="Project not found")
        
    for key, val in proj.model_dump().items():
        setattr(db_proj, key, val)
        
    db.commit()
    db.refresh(db_proj)
    return db_proj

@router.delete("/projects/{proj_id}")
def delete_project(proj_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_proj = db.query(Project).filter(Project.id == proj_id, Project.user_id == current_user.id).first()
    if not db_proj:
        raise HTTPException(status_code=404, detail="Project not found")
        
    db.delete(db_proj)
    db.commit()
    return {"message": "Project deleted"}

# CRUD Skills
@router.post("/skills")
def add_skill(sk: SkillCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sk_name = sk.name.strip()
    if not sk_name:
        raise HTTPException(status_code=400, detail="Skill name cannot be empty")
        
    skill_obj = db.query(Skill).filter(Skill.name == sk_name).first()
    if not skill_obj:
        skill_obj = Skill(name=sk_name)
        db.add(skill_obj)
        db.flush()
        
    # Check if user already has skill
    user_sk = db.query(UserSkill).filter(UserSkill.user_id == current_user.id, UserSkill.skill_id == skill_obj.id).first()
    if not user_sk:
        user_sk = UserSkill(
            user_id=current_user.id,
            skill_id=skill_obj.id,
            confidence=sk.confidence,
            years_used=sk.years_used
        )
        db.add(user_sk)
    else:
        user_sk.confidence = sk.confidence
        user_sk.years_used = sk.years_used
        
    db.commit()
    return {"name": skill_obj.name, "confidence": user_sk.confidence, "years_used": user_sk.years_used}

@router.delete("/skills/{name}")
def remove_skill(name: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    skill_obj = db.query(Skill).filter(Skill.name == name.strip()).first()
    if not skill_obj:
        raise HTTPException(status_code=404, detail="Skill not found")
        
    user_sk = db.query(UserSkill).filter(UserSkill.user_id == current_user.id, UserSkill.skill_id == skill_obj.id).first()
    if not user_sk:
        raise HTTPException(status_code=404, detail="User does not have this skill")
        
    db.delete(user_sk)
    db.commit()
    return {"message": "Skill removed"}

# CRUD Achievements
@router.post("/achievements")
def create_achievement(ach: AchievementCreateUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_ach = Achievement(
        user_id=current_user.id,
        **ach.model_dump()
    )
    db.add(new_ach)
    db.commit()
    db.refresh(new_ach)
    return new_ach

@router.put("/achievements/{ach_id}")
def update_achievement(ach_id: int, ach: AchievementCreateUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_ach = db.query(Achievement).filter(Achievement.id == ach_id, Achievement.user_id == current_user.id).first()
    if not db_ach:
        raise HTTPException(status_code=404, detail="Achievement not found")
        
    for key, val in ach.model_dump().items():
        setattr(db_ach, key, val)
        
    db.commit()
    db.refresh(db_ach)
    return db_ach

@router.delete("/achievements/{ach_id}")
def delete_achievement(ach_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_ach = db.query(Achievement).filter(Achievement.id == ach_id, Achievement.user_id == current_user.id).first()
    if not db_ach:
        raise HTTPException(status_code=404, detail="Achievement not found")
        
    db.delete(db_ach)
    db.commit()
    return {"message": "Achievement deleted"}

# CRUD Courses & Certifications
@router.post("/courses")
def create_course(course: CourseCreateUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_course = CourseCertification(
        user_id=current_user.id,
        **course.model_dump()
    )
    db.add(new_course)
    db.commit()
    db.refresh(new_course)
    return new_course

@router.put("/courses/{course_id}")
def update_course(course_id: int, course: CourseCreateUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_course = db.query(CourseCertification).filter(CourseCertification.id == course_id, CourseCertification.user_id == current_user.id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course/Certification not found")
        
    for key, val in course.model_dump().items():
        setattr(db_course, key, val)
        
    db.commit()
    db.refresh(db_course)
    return db_course

@router.delete("/courses/{course_id}")
def delete_course(course_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_course = db.query(CourseCertification).filter(CourseCertification.id == course_id, CourseCertification.user_id == current_user.id).first()
    if not db_course:
        raise HTTPException(status_code=404, detail="Course/Certification not found")
        
    db.delete(db_course)
    db.commit()
    return {"message": "Course/Certification deleted"}

