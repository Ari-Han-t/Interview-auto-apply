from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.profile import Profile
from app.models.candidate import (
    UserProfile,
    CandidateEducation,
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
from app.services.github_sync import normalize_github_username
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, field_validator

router = APIRouter()

# Schema definitions for requests
class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    preferred_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None
    portfolio: Optional[str] = None
    website: Optional[str] = None
    current_location: Optional[str] = None
    preferred_locations: Optional[Union[List[str], str]] = []
    work_authorization: Optional[str] = None
    visa_required: Optional[bool] = False
    willing_to_relocate: Optional[bool] = True
    remote_preference: Optional[str] = None
    graduation_year: Optional[Union[int, str]] = None
    degree: Optional[str] = None
    specialization: Optional[str] = None
    cgpa: Optional[Union[float, str]] = None
    university: Optional[str] = None
    coursework: Optional[Union[List[str], str]] = []
    current_semester_or_year: Optional[str] = None
    bio: Optional[str] = None
    availability: Optional[str] = None
    tailoring_instructions: Optional[str] = None

    @field_validator("coursework", mode="before")
    @classmethod
    def parse_coursework(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        if v is None:
            return []
        return v

    @field_validator("preferred_locations", mode="before")
    @classmethod
    def parse_preferred_locations(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        if v is None:
            return []
        return v

    @field_validator("graduation_year", mode="before")
    @classmethod
    def parse_graduation_year(cls, v):
        if v == "" or v is None:
            return None
        try:
            return int(v)
        except (ValueError, TypeError):
            return None

    @field_validator("cgpa", mode="before")
    @classmethod
    def parse_cgpa(cls, v):
        if v == "" or v is None:
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None


class EducationCreateUpdate(BaseModel):
    institution: str
    degree: Optional[str] = None
    specialization: Optional[str] = None
    start_year: Optional[int] = None
    graduation_year: Optional[int] = None
    cgpa: Optional[float] = None
    coursework: Optional[List[str]] = []
    location: Optional[str] = None
    is_visible: Optional[bool] = True

class ExperienceCreateUpdate(BaseModel):
    company: str
    title: str
    internship_or_fulltime: Optional[str] = "fulltime"
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    currently_working: Optional[bool] = False
    months_of_experience: Optional[int] = 0
    description: Optional[str] = None
    technologies: Optional[List[str]] = []
    highlights: Optional[List[str]] = []
    is_visible: Optional[bool] = True

class ProjectCreateUpdate(BaseModel):
    name: str
    description: Optional[str] = None
    github: Optional[str] = None
    live_link: Optional[str] = None
    technologies: Optional[List[str]] = []
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    highlights: Optional[List[str]] = []
    is_visible: Optional[bool] = True

class SkillCreate(BaseModel):
    name: str
    confidence: Optional[int] = 5
    years_used: Optional[float] = 0.0
    category: Optional[str] = "General"
    is_visible: Optional[bool] = True

class AchievementCreateUpdate(BaseModel):
    title: str
    category: Optional[str] = "hackathon" # hackathon, award, prize, publication, other
    issuer_or_event: Optional[str] = None
    year_or_date: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    is_visible: Optional[bool] = True

class CourseCreateUpdate(BaseModel):
    name: str
    issuer: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None
    skills_covered: Optional[List[str]] = []
    is_visible: Optional[bool] = True

class VisibilityToggle(BaseModel):
    is_visible: bool

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
    availability_duration: Optional[str] = None
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
    needs_commit = False
    if not user_prof:
        # Create empty default profile
        user_prof = UserProfile(user_id=current_user.id, email=current_user.email)
        db.add(user_prof)
        needs_commit = True
        
    capabilities = db.query(CandidateCapability).filter(CandidateCapability.user_id == current_user.id).first()
    if not capabilities:
        capabilities = CandidateCapability(user_id=current_user.id)
        db.add(capabilities)
        needs_commit = True
        
    preferences = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
    if not preferences:
        preferences = UserPreference(user_id=current_user.id)
        db.add(preferences)
        needs_commit = True
        
    if needs_commit:
        db.commit()

    db.refresh(user_prof)
    db.refresh(capabilities)
    db.refresh(preferences)

    legacy_profile = _get_or_create_profile_row(db, current_user.id)
    # Sync GitHub representation between legacy Profile and UserProfile if one is set
    if not user_prof.github and legacy_profile.github_username:
        user_prof.github = f"https://github.com/{legacy_profile.github_username}"
    elif user_prof.github and not legacy_profile.github_username:
        norm_user = normalize_github_username(user_prof.github)
        if norm_user:
            legacy_profile.github_username = norm_user
            db.commit()
    
    experiences = db.query(CandidateExperience).filter(CandidateExperience.user_id == current_user.id).all()
    projects = db.query(Project).filter(Project.user_id == current_user.id).all()
    achievements = db.query(Achievement).filter(Achievement.user_id == current_user.id).all()
    courses = db.query(CourseCertification).filter(CourseCertification.user_id == current_user.id).all()
    educations = db.query(CandidateEducation).filter(CandidateEducation.user_id == current_user.id).all()
    
    # Skills mapped to user
    user_skills = db.query(UserSkill).filter(UserSkill.user_id == current_user.id).all()
    skills_payload = []
    for us in user_skills:
        skills_payload.append({
            "name": us.skill.name,
            "confidence": us.confidence,
            "years_used": us.years_used,
            "category": getattr(us, "category", "General"),
            "is_visible": getattr(us, "is_visible", True)
        })
        
    return {
        "profile": user_prof,
        "educations": educations,
        "experiences": experiences,
        "projects": projects,
        "skills": skills_payload,
        "achievements": achievements,
        "courses": courses,
        "preferences": preferences,
        "capabilities": capabilities,
        "tailoring_instructions": (legacy_profile.tailoring_instructions or ""),
        "github_username": (legacy_profile.github_username or ""),
    }

@router.put("/")
def update_profile(profile_data: UserProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_prof = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not user_prof:
        user_prof = UserProfile(user_id=current_user.id)
        db.add(user_prof)

    data = profile_data.model_dump(exclude_unset=True)
    # tailoring_instructions lives on the legacy Profile row, not UserProfile
    profile_row = _get_or_create_profile_row(db, current_user.id)
    if "tailoring_instructions" in data:
        raw = data.pop("tailoring_instructions")
        profile_row.tailoring_instructions = (raw or "").strip() or None

    # Sync github_username if github was passed
    if "github" in data and data["github"]:
        norm_user = normalize_github_username(data["github"])
        if norm_user:
            profile_row.github_username = norm_user

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
            years_used=sk.years_used,
            category=sk.category or "General",
            is_visible=sk.is_visible if sk.is_visible is not None else True,
        )
        db.add(user_sk)
    else:
        user_sk.confidence = sk.confidence
        user_sk.years_used = sk.years_used
        if sk.category:
            user_sk.category = sk.category
        if sk.is_visible is not None:
            user_sk.is_visible = sk.is_visible
        
    db.commit()
    return {
        "name": skill_obj.name,
        "confidence": user_sk.confidence,
        "years_used": user_sk.years_used,
        "category": getattr(user_sk, "category", "General"),
        "is_visible": getattr(user_sk, "is_visible", True),
    }

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


# CRUD Educations
@router.post("/educations")
def create_education(edu: EducationCreateUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    new_edu = CandidateEducation(
        user_id=current_user.id,
        **edu.model_dump()
    )
    db.add(new_edu)
    db.commit()
    db.refresh(new_edu)
    return new_edu


@router.put("/educations/{edu_id}")
def update_education(edu_id: int, edu: EducationCreateUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_edu = db.query(CandidateEducation).filter(CandidateEducation.id == edu_id, CandidateEducation.user_id == current_user.id).first()
    if not db_edu:
        raise HTTPException(status_code=404, detail="Education record not found")

    for key, val in edu.model_dump().items():
        setattr(db_edu, key, val)

    db.commit()
    db.refresh(db_edu)
    return db_edu


@router.delete("/educations/{edu_id}")
def delete_education(edu_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_edu = db.query(CandidateEducation).filter(CandidateEducation.id == edu_id, CandidateEducation.user_id == current_user.id).first()
    if not db_edu:
        raise HTTPException(status_code=404, detail="Education record not found")

    db.delete(db_edu)
    db.commit()
    return {"message": "Education record deleted"}


# Visibility Toggles
@router.put("/experiences/{exp_id}/visibility")
def toggle_experience_visibility(exp_id: int, body: VisibilityToggle, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    exp = db.query(CandidateExperience).filter(CandidateExperience.id == exp_id, CandidateExperience.user_id == current_user.id).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experience record not found")
    exp.is_visible = body.is_visible
    db.commit()
    return {"message": "Visibility updated", "is_visible": exp.is_visible}


@router.put("/projects/{proj_id}/visibility")
def toggle_project_visibility(proj_id: int, body: VisibilityToggle, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    proj = db.query(Project).filter(Project.id == proj_id, Project.user_id == current_user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    proj.is_visible = body.is_visible
    db.commit()
    return {"message": "Visibility updated", "is_visible": proj.is_visible}


@router.put("/skills/{name}/visibility")
def toggle_skill_visibility(name: str, body: VisibilityToggle, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    skill = db.query(Skill).filter(Skill.name == name.strip()).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    user_sk = db.query(UserSkill).filter(UserSkill.user_id == current_user.id, UserSkill.skill_id == skill.id).first()
    if not user_sk:
        raise HTTPException(status_code=404, detail="User skill not found")
    user_sk.is_visible = body.is_visible
    db.commit()
    return {"message": "Visibility updated", "is_visible": user_sk.is_visible}


@router.put("/achievements/{ach_id}/visibility")
def toggle_achievement_visibility(ach_id: int, body: VisibilityToggle, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ach = db.query(Achievement).filter(Achievement.id == ach_id, Achievement.user_id == current_user.id).first()
    if not ach:
        raise HTTPException(status_code=404, detail="Achievement not found")
    ach.is_visible = body.is_visible
    db.commit()
    return {"message": "Visibility updated", "is_visible": ach.is_visible}


@router.put("/courses/{course_id}/visibility")
def toggle_course_visibility(course_id: int, body: VisibilityToggle, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    crs = db.query(CourseCertification).filter(CourseCertification.id == course_id, CourseCertification.user_id == current_user.id).first()
    if not crs:
        raise HTTPException(status_code=404, detail="Course not found")
    crs.is_visible = body.is_visible
    db.commit()
    return {"message": "Visibility updated", "is_visible": crs.is_visible}


@router.put("/educations/{edu_id}/visibility")
def toggle_education_visibility(edu_id: int, body: VisibilityToggle, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    edu = db.query(CandidateEducation).filter(CandidateEducation.id == edu_id, CandidateEducation.user_id == current_user.id).first()
    if not edu:
        raise HTTPException(status_code=404, detail="Education not found")
    edu.is_visible = body.is_visible
    db.commit()
    return {"message": "Visibility updated", "is_visible": edu.is_visible}


@router.get("/export-all-data")
def export_all_candidate_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Exports full candidate career profile, content library, and applications as structured JSON."""
    from app.models.application import Application
    from app.models.resume import ResumeVersion
    from app.models.cover_letter import CoverLetter

    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    educations = db.query(CandidateEducation).filter(CandidateEducation.user_id == current_user.id).all()
    experiences = db.query(CandidateExperience).filter(CandidateExperience.user_id == current_user.id).all()
    projects = db.query(Project).filter(Project.user_id == current_user.id).all()
    skills = db.query(UserSkill).filter(UserSkill.user_id == current_user.id).all()
    achievements = db.query(Achievement).filter(Achievement.user_id == current_user.id).all()
    courses = db.query(CourseCertification).filter(CourseCertification.user_id == current_user.id).all()
    preferences = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
    capabilities = db.query(CandidateCapability).filter(CandidateCapability.user_id == current_user.id).first()
    apps = db.query(Application).filter(Application.user_id == current_user.id).all()
    resumes = db.query(ResumeVersion).filter(ResumeVersion.user_id == current_user.id).all()
    cover_letters = db.query(CoverLetter).filter(CoverLetter.user_id == current_user.id).all()

    return {
        "export_metadata": {
            "user_id": current_user.id,
            "email": current_user.email,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "format_version": "1.0",
        },
        "candidate_profile": {
            "full_name": profile.full_name if profile else None,
            "email": profile.email if profile else current_user.email,
            "phone": profile.phone if profile else None,
            "location": profile.current_location if profile else None,
            "linkedin": profile.linkedin if profile else None,
            "github": profile.github if profile else None,
            "portfolio": profile.portfolio if profile else None,
            "summary": profile.bio if profile else None,
        },
        "educations": [
            {
                "institution": e.institution,
                "degree": e.degree,
                "field_of_study": getattr(e, "field_of_study", None) or getattr(e, "specialization", None),
                "start_year": e.start_year,
                "end_year": getattr(e, "end_year", None) or getattr(e, "graduation_year", None),
                "cgpa": e.cgpa,
            }
            for e in educations
        ],
        "experiences": [
            {
                "company": exp.company,
                "title": exp.title,
                "type": exp.internship_or_fulltime,
                "location": exp.location,
                "start_date": exp.start_date,
                "end_date": exp.end_date,
                "description": exp.description,
                "technologies": exp.technologies,
            }
            for exp in experiences
        ],
        "projects": [
            {
                "name": p.name,
                "description": p.description,
                "github": p.github,
                "live_link": p.live_link,
                "technologies": p.technologies,
            }
            for p in projects
        ],
        "skills": [
            {"name": s.skill.name, "category": getattr(s, "category", "General"), "confidence": s.confidence}
            for s in skills if s.skill
        ],
        "achievements": [
            {"title": a.title, "category": a.category, "issuer": a.issuer_or_event, "year": a.year_or_date, "description": a.description}
            for a in achievements
        ],
        "courses": [
            {"name": c.name, "issuer": c.issuer, "issue_date": c.issue_date, "url": c.credential_url}
            for c in courses
        ],
        "applications_count": len(apps),
        "resumes_count": len(resumes),
        "cover_letters_count": len(cover_letters),
    }


@router.delete("/clear-career-data")
def clear_candidate_career_data(
    confirm: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Safely clears user application history and resets temporary preferences upon explicit user confirmation."""
    if not confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation required to clear career data.")

    from app.models.application import Application
    from app.models.job import UserSavedJob

    # Remove saved jobs
    db.query(UserSavedJob).filter(UserSavedJob.user_id == current_user.id).delete()
    # Remove applications
    db.query(Application).filter(Application.user_id == current_user.id).delete()
    db.commit()

    return {"message": "Candidate application history and saved records have been successfully reset."}



