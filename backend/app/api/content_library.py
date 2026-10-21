import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.database import get_db
from app.models.user import User
from app.models.candidate import (
    UserProfile,
    CandidateEducation,
    CandidateExperience,
    Project,
    Skill,
    UserSkill,
    Achievement,
    CourseCertification,
    CandidateLeadership,
    CandidateCoursework,
    CandidatePublication,
    CandidateCustomSection,
)
from app.models.resume import ResumeVersion
from app.api.auth import get_current_user
from app.services.ai.project_analyzer import parse_project_readme
from app.services.resume_compiler.candidate_data import load_candidate_library, MODULE_KEYS, MODULE_DISPLAY_NAMES

router = APIRouter()


# -------------------------------------------------------------
# Pydantic Request Schemas
# -------------------------------------------------------------

class BulletItem(BaseModel):
    id: Optional[str] = None
    text: str
    is_selected: Optional[bool] = True
    metric: Optional[str] = None


class BulletsUpdateRequest(BaseModel):
    bullets: List[BulletItem]


class ArchiveToggleRequest(BaseModel):
    is_archived: Optional[bool] = None


class GeneralInfoUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    preferred_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    github: Optional[str] = None
    linkedin: Optional[str] = None
    portfolio: Optional[str] = None
    website: Optional[str] = None
    current_location: Optional[str] = None
    preferred_locations: Optional[List[str]] = []
    work_authorization: Optional[str] = None
    visa_required: Optional[bool] = False
    willing_to_relocate: Optional[bool] = True
    remote_preference: Optional[str] = None
    graduation_year: Optional[int] = None
    degree: Optional[str] = None
    specialization: Optional[str] = None
    cgpa: Optional[float] = None
    university: Optional[str] = None
    coursework: Optional[List[str]] = []
    current_semester_or_year: Optional[str] = None
    bio: Optional[str] = None
    availability: Optional[str] = None


class EducationRequest(BaseModel):
    institution: str
    degree: Optional[str] = None
    specialization: Optional[str] = None
    start_year: Optional[int] = None
    graduation_year: Optional[int] = None
    cgpa: Optional[float] = None
    gpa_scale: Optional[str] = "4.0"
    honors: Optional[str] = None
    coursework: Optional[List[str]] = []
    location: Optional[str] = None
    bullets: Optional[List[BulletItem]] = []
    verification_status: Optional[str] = "self_attested"
    evidence_url: Optional[str] = None
    is_visible: Optional[bool] = True
    is_archived: Optional[bool] = False


class ExperienceRequest(BaseModel):
    company: str
    title: str
    experience_type: Optional[str] = "employment"
    internship_or_fulltime: Optional[str] = "fulltime"
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    currently_working: Optional[bool] = False
    months_of_experience: Optional[int] = 0
    responsibilities: Optional[str] = None
    contributions: Optional[str] = None
    metrics: Optional[str] = None
    description: Optional[str] = None
    technologies: Optional[List[str]] = []
    highlights: Optional[List[str]] = []
    bullets: Optional[List[BulletItem]] = []
    verification_status: Optional[str] = "self_attested"
    evidence_url: Optional[str] = None
    is_visible: Optional[bool] = True
    is_archived: Optional[bool] = False


class ProjectRequest(BaseModel):
    name: str
    problem: Optional[str] = None
    description: Optional[str] = None
    personal_contribution: Optional[str] = None
    implementation: Optional[str] = None
    programming_languages: Optional[List[str]] = []
    frameworks: Optional[List[str]] = []
    libraries: Optional[List[str]] = []
    databases: Optional[List[str]] = []
    apis: Optional[List[str]] = []
    ai_ml_techniques: Optional[List[str]] = []
    deployment_technologies: Optional[List[str]] = []
    technologies: Optional[List[str]] = []
    technical_challenges: Optional[str] = None
    verified_outcomes: Optional[List[str]] = []
    role: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    github: Optional[str] = None
    live_link: Optional[str] = None
    supporting_evidence: Optional[str] = None
    evidence_url: Optional[str] = None
    highlights: Optional[List[str]] = []
    bullets: Optional[List[BulletItem]] = []
    verification_status: Optional[str] = "self_attested"
    is_visible: Optional[bool] = True
    is_archived: Optional[bool] = False


class SkillRequest(BaseModel):
    name: str
    category: Optional[str] = "General"
    confidence: Optional[int] = 5
    years_used: Optional[float] = 1.0
    proficiency_level: Optional[str] = "Advanced"
    verification_status: Optional[str] = "self_attested"
    evidence_url: Optional[str] = None
    notes: Optional[str] = None
    is_visible: Optional[bool] = True
    is_archived: Optional[bool] = False


class AchievementRequest(BaseModel):
    title: str
    category: Optional[str] = "award"
    issuer_or_event: Optional[str] = None
    year_or_date: Optional[str] = None
    description: Optional[str] = None
    impact_metrics: Optional[str] = None
    url: Optional[str] = None
    bullets: Optional[List[BulletItem]] = []
    evidence_url: Optional[str] = None
    verification_status: Optional[str] = "self_attested"
    is_visible: Optional[bool] = True
    is_archived: Optional[bool] = False


class CertificationRequest(BaseModel):
    name: str
    issuer: Optional[str] = None
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None
    skills_covered: Optional[List[str]] = []
    bullets: Optional[List[BulletItem]] = []
    evidence_url: Optional[str] = None
    verification_status: Optional[str] = "self_attested"
    is_visible: Optional[bool] = True
    is_archived: Optional[bool] = False


class LeadershipRequest(BaseModel):
    organization: str
    role: str
    category: Optional[str] = "club"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    currently_active: Optional[bool] = False
    description: Optional[str] = None
    responsibilities: Optional[str] = None
    bullets: Optional[List[BulletItem]] = []
    evidence_url: Optional[str] = None
    verification_status: Optional[str] = "self_attested"
    is_visible: Optional[bool] = True
    is_archived: Optional[bool] = False


class CourseworkRequest(BaseModel):
    course_name: str
    course_code: Optional[str] = None
    institution: Optional[str] = None
    term_or_year: Optional[str] = None
    grade: Optional[str] = None
    skills_learned: Optional[List[str]] = []
    description: Optional[str] = None
    topics_covered: Optional[List[str]] = []
    evidence_url: Optional[str] = None
    verification_status: Optional[str] = "self_attested"
    is_visible: Optional[bool] = True
    is_archived: Optional[bool] = False


class PublicationRequest(BaseModel):
    title: str
    publication_type: Optional[str] = "conference_paper"
    venue_or_publisher: Optional[str] = None
    publication_date: Optional[str] = None
    authors: Optional[List[str]] = []
    url: Optional[str] = None
    doi_or_id: Optional[str] = None
    description: Optional[str] = None
    citation_count_or_metrics: Optional[str] = None
    bullets: Optional[List[BulletItem]] = []
    evidence_url: Optional[str] = None
    verification_status: Optional[str] = "self_attested"
    is_visible: Optional[bool] = True
    is_archived: Optional[bool] = False


class CustomSectionRequest(BaseModel):
    section_title: str
    title: str
    subtitle: Optional[str] = None
    date_or_year: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    bullets: Optional[List[BulletItem]] = []
    url: Optional[str] = None
    evidence_url: Optional[str] = None
    verification_status: Optional[str] = "self_attested"
    is_visible: Optional[bool] = True
    is_archived: Optional[bool] = False


class ProjectImportAnalyzeRequest(BaseModel):
    text: str
    github_url: Optional[str] = None
    name: Optional[str] = None


# -------------------------------------------------------------
# Helper Utilities
# -------------------------------------------------------------

def normalize_bullets(bullets_in: Optional[List[Any]]) -> List[Dict[str, Any]]:
    """Ensures each bullet has a stable identifier and required attributes."""
    if not bullets_in:
        return []
    normalized = []
    for b in bullets_in:
        if isinstance(b, dict):
            b_id = b.get("id") or f"b_{uuid.uuid4().hex[:8]}"
            text = b.get("text", "")
            is_selected = b.get("is_selected", True)
            metric = b.get("metric")
        elif hasattr(b, "text"):
            b_id = getattr(b, "id", None) or f"b_{uuid.uuid4().hex[:8]}"
            text = b.text
            is_selected = getattr(b, "is_selected", True)
            metric = getattr(b, "metric", None)
        else:
            b_id = f"b_{uuid.uuid4().hex[:8]}"
            text = str(b)
            is_selected = True
            metric = None

        if text.strip():
            normalized.append({
                "id": b_id,
                "text": text.strip(),
                "is_selected": bool(is_selected),
                "metric": metric
            })
    return normalized


# -------------------------------------------------------------
# 1. Overview & Cross-Module Search
# -------------------------------------------------------------

@router.get("/overview")
def get_library_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns overview counts, active vs archived items, and verification breakdown."""
    edus = db.query(CandidateEducation).filter(CandidateEducation.user_id == current_user.id).all()
    exps = db.query(CandidateExperience).filter(CandidateExperience.user_id == current_user.id).all()
    projs = db.query(Project).filter(Project.user_id == current_user.id).all()
    skills = db.query(UserSkill).filter(UserSkill.user_id == current_user.id).all()
    achs = db.query(Achievement).filter(Achievement.user_id == current_user.id).all()
    certs = db.query(CourseCertification).filter(CourseCertification.user_id == current_user.id).all()
    leaders = db.query(CandidateLeadership).filter(CandidateLeadership.user_id == current_user.id).all()
    courses = db.query(CandidateCoursework).filter(CandidateCoursework.user_id == current_user.id).all()
    pubs = db.query(CandidatePublication).filter(CandidatePublication.user_id == current_user.id).all()
    customs = db.query(CandidateCustomSection).filter(CandidateCustomSection.user_id == current_user.id).all()
    user_prof = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    total_bullets = (
        sum(len(e.bullets or []) for e in exps) +
        sum(len(p.bullets or []) for p in projs) +
        sum(len(l.bullets or []) for l in leaders) +
        sum(len(a.bullets or []) for a in achs)
    )

    return {
        "general_info_completed": bool(user_prof and user_prof.full_name and user_prof.email),
        "modules": {
            "education": {"total": len(edus), "active": len([e for e in edus if not getattr(e, "is_archived", False)])},
            "experience": {"total": len(exps), "active": len([e for e in exps if not getattr(e, "is_archived", False)])},
            "projects": {"total": len(projs), "active": len([p for p in projs if not getattr(p, "is_archived", False)])},
            "skills": {"total": len(skills), "active": len([s for s in skills if not getattr(s, "is_archived", False)])},
            "achievements": {"total": len(achs), "active": len([a for a in achs if not getattr(a, "is_archived", False)])},
            "certifications": {"total": len(certs), "active": len([c for c in certs if not getattr(c, "is_archived", False)])},
            "leadership": {"total": len(leaders), "active": len([l for l in leaders if not getattr(l, "is_archived", False)])},
            "coursework": {"total": len(courses), "active": len([c for c in courses if not getattr(c, "is_archived", False)])},
            "publications": {"total": len(pubs), "active": len([p for p in pubs if not getattr(p, "is_archived", False)])},
            "custom_sections": {"total": len(customs), "active": len([c for c in customs if not getattr(c, "is_archived", False)])},
        },
        "total_bullets_cataloged": total_bullets,
    }


@router.get("/modules")
def get_library_modules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns candidate library modules for content review and modular resume assembly."""
    library = load_candidate_library(current_user.id, db)
    return {
        "status": "success",
        "data": library,
        "candidate_data": library,
        "module_keys": MODULE_KEYS,
        "module_display_names": MODULE_DISPLAY_NAMES
    }


@router.get("/search")
def search_content_library(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cross-module search across all 11 library entities."""
    query_str = f"%{q.lower()}%"
    results: Dict[str, List[Any]] = {
        "education": [],
        "experience": [],
        "projects": [],
        "skills": [],
        "achievements": [],
        "certifications": [],
        "leadership": [],
        "coursework": [],
        "publications": [],
        "custom_sections": []
    }

    # Education
    for e in db.query(CandidateEducation).filter(
        CandidateEducation.user_id == current_user.id,
        or_(
            CandidateEducation.institution.ilike(query_str),
            CandidateEducation.degree.ilike(query_str),
            CandidateEducation.specialization.ilike(query_str),
        )
    ).all():
        results["education"].append({"id": e.id, "title": e.institution, "subtitle": e.degree})

    # Experiences
    for exp in db.query(CandidateExperience).filter(
        CandidateExperience.user_id == current_user.id,
        or_(
            CandidateExperience.company.ilike(query_str),
            CandidateExperience.title.ilike(query_str),
            CandidateExperience.description.ilike(query_str),
        )
    ).all():
        results["experience"].append({"id": exp.id, "title": f"{exp.title} at {exp.company}", "subtitle": exp.start_date})

    # Projects
    for p in db.query(Project).filter(
        Project.user_id == current_user.id,
        or_(
            Project.name.ilike(query_str),
            Project.description.ilike(query_str),
            Project.problem.ilike(query_str),
        )
    ).all():
        results["projects"].append({"id": p.id, "title": p.name, "subtitle": p.role or "Project"})

    # Skills
    for s in db.query(UserSkill).join(Skill).filter(
        UserSkill.user_id == current_user.id,
        Skill.name.ilike(query_str)
    ).all():
        results["skills"].append({"id": s.skill_id, "title": s.skill.name, "subtitle": s.category})

    # Achievements
    for a in db.query(Achievement).filter(
        Achievement.user_id == current_user.id,
        or_(Achievement.title.ilike(query_str), Achievement.description.ilike(query_str))
    ).all():
        results["achievements"].append({"id": a.id, "title": a.title, "subtitle": a.issuer_or_event})

    # Certifications
    for c in db.query(CourseCertification).filter(
        CourseCertification.user_id == current_user.id,
        or_(CourseCertification.name.ilike(query_str), CourseCertification.issuer.ilike(query_str))
    ).all():
        results["certifications"].append({"id": c.id, "title": c.name, "subtitle": c.issuer})

    # Leadership
    for l in db.query(CandidateLeadership).filter(
        CandidateLeadership.user_id == current_user.id,
        or_(CandidateLeadership.organization.ilike(query_str), CandidateLeadership.role.ilike(query_str))
    ).all():
        results["leadership"].append({"id": l.id, "title": f"{l.role} - {l.organization}", "subtitle": l.category})

    # Coursework
    for cw in db.query(CandidateCoursework).filter(
        CandidateCoursework.user_id == current_user.id,
        or_(CandidateCoursework.course_name.ilike(query_str), CandidateCoursework.course_code.ilike(query_str))
    ).all():
        results["coursework"].append({"id": cw.id, "title": cw.course_name, "subtitle": cw.course_code})

    # Publications
    for pb in db.query(CandidatePublication).filter(
        CandidatePublication.user_id == current_user.id,
        or_(CandidatePublication.title.ilike(query_str), CandidatePublication.venue_or_publisher.ilike(query_str))
    ).all():
        results["publications"].append({"id": pb.id, "title": pb.title, "subtitle": pb.venue_or_publisher})

    # Custom sections
    for cs in db.query(CandidateCustomSection).filter(
        CandidateCustomSection.user_id == current_user.id,
        or_(CandidateCustomSection.title.ilike(query_str), CandidateCustomSection.section_title.ilike(query_str))
    ).all():
        results["custom_sections"].append({"id": cs.id, "title": cs.title, "subtitle": cs.section_title})

    total_count = sum(len(v) for v in results.values())
    return {"query": q, "total_matches": total_count, "results": results}


# -------------------------------------------------------------
# 2. General Information Module
# -------------------------------------------------------------

@router.get("/general-info")
def get_general_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    prof = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not prof:
        return {}
    return {
        "id": prof.id,
        "full_name": prof.full_name,
        "preferred_name": prof.preferred_name,
        "email": prof.email or current_user.email,
        "phone": prof.phone,
        "github": prof.github,
        "linkedin": prof.linkedin,
        "portfolio": prof.portfolio,
        "website": prof.website,
        "current_location": prof.current_location,
        "preferred_locations": prof.preferred_locations or [],
        "work_authorization": prof.work_authorization,
        "visa_required": prof.visa_required,
        "willing_to_relocate": prof.willing_to_relocate,
        "remote_preference": prof.remote_preference,
        "graduation_year": prof.graduation_year,
        "degree": prof.degree,
        "specialization": prof.specialization,
        "cgpa": prof.cgpa,
        "university": prof.university,
        "coursework": prof.coursework or [],
        "current_semester_or_year": prof.current_semester_or_year,
        "bio": prof.bio,
        "availability": prof.availability,
    }


@router.put("/general-info")
def update_general_info(
    req: GeneralInfoUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    prof = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not prof:
        prof = UserProfile(user_id=current_user.id)
        db.add(prof)

    for field, val in req.model_dump(exclude_unset=True).items():
        setattr(prof, field, val)

    db.commit()
    db.refresh(prof)
    return {"message": "General information updated", "profile": prof}


# -------------------------------------------------------------
# 3. Education Module
# -------------------------------------------------------------

@router.get("/educations")
def list_educations(
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(CandidateEducation).filter(CandidateEducation.user_id == current_user.id)
    if not include_archived:
        query = query.filter(CandidateEducation.is_archived.is_(False))
    return query.order_by(CandidateEducation.graduation_year.desc()).all()


@router.post("/educations")
def create_education(
    req: EducationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data = req.model_dump()
    data["bullets"] = normalize_bullets(data.get("bullets"))
    edu = CandidateEducation(user_id=current_user.id, **data)
    db.add(edu)
    db.commit()
    db.refresh(edu)
    return edu


@router.put("/educations/{item_id}")
def update_education(
    item_id: int,
    req: EducationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    edu = db.query(CandidateEducation).filter(
        CandidateEducation.id == item_id,
        CandidateEducation.user_id == current_user.id
    ).first()
    if not edu:
        raise HTTPException(status_code=404, detail="Education record not found")

    data = req.model_dump()
    if "bullets" in data:
        data["bullets"] = normalize_bullets(data.get("bullets"))

    for k, v in data.items():
        setattr(edu, k, v)
    db.commit()
    db.refresh(edu)
    return edu


@router.post("/educations/{item_id}/duplicate")
def duplicate_education(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    edu = db.query(CandidateEducation).filter(
        CandidateEducation.id == item_id,
        CandidateEducation.user_id == current_user.id
    ).first()
    if not edu:
        raise HTTPException(status_code=404, detail="Education record not found")

    new_bullets = [{**b, "id": f"b_{uuid.uuid4().hex[:8]}"} for b in (edu.bullets or [])]
    clone = CandidateEducation(
        user_id=current_user.id,
        institution=f"{edu.institution} (Copy)",
        degree=edu.degree,
        specialization=edu.specialization,
        start_year=edu.start_year,
        graduation_year=edu.graduation_year,
        cgpa=edu.cgpa,
        gpa_scale=edu.gpa_scale,
        honors=edu.honors,
        coursework=edu.coursework or [],
        location=edu.location,
        bullets=new_bullets,
        verification_status=edu.verification_status,
        evidence_url=edu.evidence_url,
        is_visible=edu.is_visible,
        is_archived=False
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


@router.put("/educations/{item_id}/archive")
def archive_education(
    item_id: int,
    req: Optional[ArchiveToggleRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    edu = db.query(CandidateEducation).filter(
        CandidateEducation.id == item_id,
        CandidateEducation.user_id == current_user.id
    ).first()
    if not edu:
        raise HTTPException(status_code=404, detail="Education record not found")

    edu.is_archived = req.is_archived if req and req.is_archived is not None else not edu.is_archived
    db.commit()
    return {"id": edu.id, "is_archived": edu.is_archived}


@router.delete("/educations/{item_id}")
def delete_education(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    edu = db.query(CandidateEducation).filter(
        CandidateEducation.id == item_id,
        CandidateEducation.user_id == current_user.id
    ).first()
    if not edu:
        raise HTTPException(status_code=404, detail="Education record not found")
    db.delete(edu)
    db.commit()
    return {"message": "Education deleted successfully"}


# -------------------------------------------------------------
# 4. Experience Module
# -------------------------------------------------------------

@router.get("/experiences")
def list_experiences(
    include_archived: bool = False,
    exp_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(CandidateExperience).filter(CandidateExperience.user_id == current_user.id)
    if not include_archived:
        query = query.filter(CandidateExperience.is_archived.is_(False))
    if exp_type:
        query = query.filter(CandidateExperience.experience_type == exp_type)
    return query.order_by(CandidateExperience.start_date.desc()).all()


@router.post("/experiences")
def create_experience(
    req: ExperienceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data = req.model_dump()
    data["bullets"] = normalize_bullets(data.get("bullets"))
    exp = CandidateExperience(user_id=current_user.id, **data)
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp


@router.put("/experiences/{item_id}")
def update_experience(
    item_id: int,
    req: ExperienceRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    exp = db.query(CandidateExperience).filter(
        CandidateExperience.id == item_id,
        CandidateExperience.user_id == current_user.id
    ).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experience record not found")

    data = req.model_dump()
    if "bullets" in data:
        data["bullets"] = normalize_bullets(data.get("bullets"))

    for k, v in data.items():
        setattr(exp, k, v)
    db.commit()
    db.refresh(exp)
    return exp


@router.put("/experiences/{item_id}/bullets")
def update_experience_bullets(
    item_id: int,
    req: BulletsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    exp = db.query(CandidateExperience).filter(
        CandidateExperience.id == item_id,
        CandidateExperience.user_id == current_user.id
    ).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experience not found")

    exp.bullets = normalize_bullets(req.bullets)
    db.commit()
    return {"id": exp.id, "bullets": exp.bullets}


@router.post("/experiences/{item_id}/duplicate")
def duplicate_experience(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    exp = db.query(CandidateExperience).filter(
        CandidateExperience.id == item_id,
        CandidateExperience.user_id == current_user.id
    ).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experience not found")

    new_bullets = [{**b, "id": f"b_{uuid.uuid4().hex[:8]}"} for b in (exp.bullets or [])]
    clone = CandidateExperience(
        user_id=current_user.id,
        company=f"{exp.company} (Copy)",
        title=exp.title,
        experience_type=exp.experience_type,
        internship_or_fulltime=exp.internship_or_fulltime,
        location=exp.location,
        start_date=exp.start_date,
        end_date=exp.end_date,
        currently_working=exp.currently_working,
        months_of_experience=exp.months_of_experience,
        responsibilities=exp.responsibilities,
        contributions=exp.contributions,
        metrics=exp.metrics,
        description=exp.description,
        technologies=exp.technologies or [],
        highlights=exp.highlights or [],
        bullets=new_bullets,
        verification_status=exp.verification_status,
        evidence_url=exp.evidence_url,
        is_visible=exp.is_visible,
        is_archived=False
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


@router.put("/experiences/{item_id}/archive")
def archive_experience(
    item_id: int,
    req: Optional[ArchiveToggleRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    exp = db.query(CandidateExperience).filter(
        CandidateExperience.id == item_id,
        CandidateExperience.user_id == current_user.id
    ).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experience not found")

    exp.is_archived = req.is_archived if req and req.is_archived is not None else not exp.is_archived
    db.commit()
    return {"id": exp.id, "is_archived": exp.is_archived}


@router.delete("/experiences/{item_id}")
def delete_experience(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    exp = db.query(CandidateExperience).filter(
        CandidateExperience.id == item_id,
        CandidateExperience.user_id == current_user.id
    ).first()
    if not exp:
        raise HTTPException(status_code=404, detail="Experience not found")
    db.delete(exp)
    db.commit()
    return {"message": "Experience deleted successfully"}


# -------------------------------------------------------------
# 5. Project Module & README Importer
# -------------------------------------------------------------

@router.get("/projects")
def list_projects(
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Project).filter(Project.user_id == current_user.id)
    if not include_archived:
        query = query.filter(Project.is_archived.is_(False))
    return query.order_by(Project.created_at.desc()).all()


@router.post("/projects")
def create_project(
    req: ProjectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data = req.model_dump()
    data["bullets"] = normalize_bullets(data.get("bullets"))
    # Merge categorized technologies into general technologies list if needed
    all_techs = set(data.get("technologies") or [])
    for cat in ["programming_languages", "frameworks", "libraries", "databases", "apis", "ai_ml_techniques", "deployment_technologies"]:
        for t in (data.get(cat) or []):
            all_techs.add(t)
    data["technologies"] = sorted(list(all_techs))

    proj = Project(user_id=current_user.id, **data)
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


@router.put("/projects/{item_id}")
def update_project(
    item_id: int,
    req: ProjectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    proj = db.query(Project).filter(
        Project.id == item_id,
        Project.user_id == current_user.id
    ).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    data = req.model_dump()
    if "bullets" in data:
        data["bullets"] = normalize_bullets(data.get("bullets"))

    all_techs = set(data.get("technologies") or [])
    for cat in ["programming_languages", "frameworks", "libraries", "databases", "apis", "ai_ml_techniques", "deployment_technologies"]:
        for t in (data.get(cat) or []):
            all_techs.add(t)
    data["technologies"] = sorted(list(all_techs))

    for k, v in data.items():
        setattr(proj, k, v)
    db.commit()
    db.refresh(proj)
    return proj


@router.put("/projects/{item_id}/bullets")
def update_project_bullets(
    item_id: int,
    req: BulletsUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    proj = db.query(Project).filter(
        Project.id == item_id,
        Project.user_id == current_user.id
    ).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    proj.bullets = normalize_bullets(req.bullets)
    db.commit()
    return {"id": proj.id, "bullets": proj.bullets}


@router.post("/projects/{item_id}/duplicate")
def duplicate_project(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    proj = db.query(Project).filter(
        Project.id == item_id,
        Project.user_id == current_user.id
    ).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    new_bullets = [{**b, "id": f"b_{uuid.uuid4().hex[:8]}"} for b in (proj.bullets or [])]
    clone = Project(
        user_id=current_user.id,
        name=f"{proj.name} (Copy)",
        problem=proj.problem,
        description=proj.description,
        personal_contribution=proj.personal_contribution,
        implementation=proj.implementation,
        programming_languages=proj.programming_languages or [],
        frameworks=proj.frameworks or [],
        libraries=proj.libraries or [],
        databases=proj.databases or [],
        apis=proj.apis or [],
        ai_ml_techniques=proj.ai_ml_techniques or [],
        deployment_technologies=proj.deployment_technologies or [],
        technologies=proj.technologies or [],
        technical_challenges=proj.technical_challenges,
        verified_outcomes=proj.verified_outcomes or [],
        role=proj.role,
        start_date=proj.start_date,
        end_date=proj.end_date,
        github=proj.github,
        live_link=proj.live_link,
        supporting_evidence=proj.supporting_evidence,
        evidence_url=proj.evidence_url,
        highlights=proj.highlights or [],
        bullets=new_bullets,
        verification_status=proj.verification_status,
        is_visible=proj.is_visible,
        is_archived=False
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


@router.put("/projects/{item_id}/archive")
def archive_project(
    item_id: int,
    req: Optional[ArchiveToggleRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    proj = db.query(Project).filter(
        Project.id == item_id,
        Project.user_id == current_user.id
    ).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    proj.is_archived = req.is_archived if req and req.is_archived is not None else not proj.is_archived
    db.commit()
    return {"id": proj.id, "is_archived": proj.is_archived}


@router.delete("/projects/{item_id}")
def delete_project(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    proj = db.query(Project).filter(
        Project.id == item_id,
        Project.user_id == current_user.id
    ).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(proj)
    db.commit()
    return {"message": "Project deleted successfully"}


@router.post("/projects/analyze-import")
def analyze_project_import(
    req: ProjectImportAnalyzeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Parses candidate-provided description, README, or documentation.
    Extracts structured architecture and suggests categorized technologies for review.
    """
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Documentation or README text is required")

    parsed = parse_project_readme(
        text=req.text,
        github_url=req.github_url,
        candidate_name=req.name
    )
    return parsed


# -------------------------------------------------------------
# 6. Skills Module
# -------------------------------------------------------------

@router.get("/skills")
def list_skills(
    category: Optional[str] = None,
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(UserSkill).join(Skill).filter(UserSkill.user_id == current_user.id)
    if not include_archived:
        query = query.filter(UserSkill.is_archived.is_(False))
    if category:
        query = query.filter(UserSkill.category == category)

    records = query.order_by(Skill.name.asc()).all()
    return [
        {
            "id": r.skill_id,
            "name": r.skill.name,
            "category": r.category or "General",
            "confidence": r.confidence,
            "years_used": r.years_used,
            "proficiency_level": r.proficiency_level or "Advanced",
            "verification_status": r.verification_status or "self_attested",
            "evidence_url": r.evidence_url,
            "notes": r.notes,
            "is_visible": r.is_visible,
            "is_archived": getattr(r, "is_archived", False)
        }
        for r in records
    ]


@router.post("/skills")
def create_skill(
    req: SkillRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    clean_name = req.name.strip()
    skill_obj = db.query(Skill).filter(Skill.name.ilike(clean_name)).first()
    if not skill_obj:
        skill_obj = Skill(name=clean_name)
        db.add(skill_obj)
        db.flush()

    user_skill = db.query(UserSkill).filter(
        UserSkill.user_id == current_user.id,
        UserSkill.skill_id == skill_obj.id
    ).first()

    if not user_skill:
        user_skill = UserSkill(
            user_id=current_user.id,
            skill_id=skill_obj.id,
            confidence=req.confidence or 5,
            years_used=req.years_used or 1.0,
            category=req.category or "General",
            proficiency_level=req.proficiency_level or "Advanced",
            verification_status=req.verification_status or "self_attested",
            evidence_url=req.evidence_url,
            notes=req.notes,
            is_visible=req.is_visible,
            is_archived=req.is_archived or False
        )
        db.add(user_skill)
    else:
        user_skill.confidence = req.confidence or user_skill.confidence
        user_skill.years_used = req.years_used or user_skill.years_used
        user_skill.category = req.category or user_skill.category
        user_skill.proficiency_level = req.proficiency_level or user_skill.proficiency_level
        user_skill.verification_status = req.verification_status or user_skill.verification_status
        user_skill.evidence_url = req.evidence_url or user_skill.evidence_url
        user_skill.notes = req.notes or user_skill.notes
        user_skill.is_visible = req.is_visible
        user_skill.is_archived = req.is_archived or False

    db.commit()
    return {
        "id": skill_obj.id,
        "name": skill_obj.name,
        "category": user_skill.category,
        "confidence": user_skill.confidence,
        "years_used": user_skill.years_used,
        "proficiency_level": user_skill.proficiency_level,
        "verification_status": user_skill.verification_status,
        "evidence_url": user_skill.evidence_url,
        "notes": user_skill.notes,
        "is_visible": user_skill.is_visible,
        "is_archived": user_skill.is_archived
    }


@router.put("/skills/{skill_id}")
def update_skill(
    skill_id: int,
    req: SkillRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_skill = db.query(UserSkill).filter(
        UserSkill.user_id == current_user.id,
        UserSkill.skill_id == skill_id
    ).first()
    if not user_skill:
        raise HTTPException(status_code=404, detail="Skill not found for user")

    user_skill.category = req.category or user_skill.category
    user_skill.confidence = req.confidence or user_skill.confidence
    user_skill.years_used = req.years_used or user_skill.years_used
    user_skill.proficiency_level = req.proficiency_level or user_skill.proficiency_level
    user_skill.verification_status = req.verification_status or user_skill.verification_status
    user_skill.evidence_url = req.evidence_url
    user_skill.notes = req.notes
    user_skill.is_visible = req.is_visible
    if req.is_archived is not None:
        user_skill.is_archived = req.is_archived

    db.commit()
    return {"message": "Skill updated successfully", "id": skill_id}


@router.put("/skills/{skill_id}/archive")
def archive_skill(
    skill_id: int,
    req: Optional[ArchiveToggleRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_skill = db.query(UserSkill).filter(
        UserSkill.user_id == current_user.id,
        UserSkill.skill_id == skill_id
    ).first()
    if not user_skill:
        raise HTTPException(status_code=404, detail="Skill not found for user")

    user_skill.is_archived = req.is_archived if req and req.is_archived is not None else not user_skill.is_archived
    db.commit()
    return {"id": skill_id, "is_archived": user_skill.is_archived}


@router.delete("/skills/{skill_id}")
def delete_skill(
    skill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user_skill = db.query(UserSkill).filter(
        UserSkill.user_id == current_user.id,
        UserSkill.skill_id == skill_id
    ).first()
    if not user_skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    db.delete(user_skill)
    db.commit()
    return {"message": "Skill removed successfully"}


# -------------------------------------------------------------
# 7. Achievements & Awards Module
# -------------------------------------------------------------

@router.get("/achievements")
def list_achievements(
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Achievement).filter(Achievement.user_id == current_user.id)
    if not include_archived:
        query = query.filter(Achievement.is_archived.is_(False))
    return query.order_by(Achievement.year_or_date.desc()).all()


@router.post("/achievements")
def create_achievement(
    req: AchievementRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data = req.model_dump()
    data["bullets"] = normalize_bullets(data.get("bullets"))
    ach = Achievement(user_id=current_user.id, **data)
    db.add(ach)
    db.commit()
    db.refresh(ach)
    return ach


@router.put("/achievements/{item_id}")
def update_achievement(
    item_id: int,
    req: AchievementRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ach = db.query(Achievement).filter(
        Achievement.id == item_id,
        Achievement.user_id == current_user.id
    ).first()
    if not ach:
        raise HTTPException(status_code=404, detail="Achievement not found")

    data = req.model_dump()
    if "bullets" in data:
        data["bullets"] = normalize_bullets(data.get("bullets"))

    for k, v in data.items():
        setattr(ach, k, v)
    db.commit()
    db.refresh(ach)
    return ach


@router.post("/achievements/{item_id}/duplicate")
def duplicate_achievement(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ach = db.query(Achievement).filter(
        Achievement.id == item_id,
        Achievement.user_id == current_user.id
    ).first()
    if not ach:
        raise HTTPException(status_code=404, detail="Achievement not found")

    new_bullets = [{**b, "id": f"b_{uuid.uuid4().hex[:8]}"} for b in (ach.bullets or [])]
    clone = Achievement(
        user_id=current_user.id,
        title=f"{ach.title} (Copy)",
        category=ach.category,
        issuer_or_event=ach.issuer_or_event,
        year_or_date=ach.year_or_date,
        description=ach.description,
        impact_metrics=ach.impact_metrics,
        url=ach.url,
        bullets=new_bullets,
        evidence_url=ach.evidence_url,
        verification_status=ach.verification_status,
        is_visible=ach.is_visible,
        is_archived=False
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


@router.put("/achievements/{item_id}/archive")
def archive_achievement(
    item_id: int,
    req: Optional[ArchiveToggleRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ach = db.query(Achievement).filter(
        Achievement.id == item_id,
        Achievement.user_id == current_user.id
    ).first()
    if not ach:
        raise HTTPException(status_code=404, detail="Achievement not found")

    ach.is_archived = req.is_archived if req and req.is_archived is not None else not ach.is_archived
    db.commit()
    return {"id": ach.id, "is_archived": ach.is_archived}


@router.delete("/achievements/{item_id}")
def delete_achievement(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ach = db.query(Achievement).filter(
        Achievement.id == item_id,
        Achievement.user_id == current_user.id
    ).first()
    if not ach:
        raise HTTPException(status_code=404, detail="Achievement not found")
    db.delete(ach)
    db.commit()
    return {"message": "Achievement deleted successfully"}


# -------------------------------------------------------------
# 8. Certifications & Training Module
# -------------------------------------------------------------

@router.get("/certifications")
def list_certifications(
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(CourseCertification).filter(CourseCertification.user_id == current_user.id)
    if not include_archived:
        query = query.filter(CourseCertification.is_archived.is_(False))
    return query.order_by(CourseCertification.issue_date.desc()).all()


@router.post("/certifications")
def create_certification(
    req: CertificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data = req.model_dump()
    data["bullets"] = normalize_bullets(data.get("bullets"))
    cert = CourseCertification(user_id=current_user.id, **data)
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert


@router.put("/certifications/{item_id}")
def update_certification(
    item_id: int,
    req: CertificationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cert = db.query(CourseCertification).filter(
        CourseCertification.id == item_id,
        CourseCertification.user_id == current_user.id
    ).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")

    data = req.model_dump()
    if "bullets" in data:
        data["bullets"] = normalize_bullets(data.get("bullets"))

    for k, v in data.items():
        setattr(cert, k, v)
    db.commit()
    db.refresh(cert)
    return cert


@router.post("/certifications/{item_id}/duplicate")
def duplicate_certification(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cert = db.query(CourseCertification).filter(
        CourseCertification.id == item_id,
        CourseCertification.user_id == current_user.id
    ).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")

    clone = CourseCertification(
        user_id=current_user.id,
        name=f"{cert.name} (Copy)",
        issuer=cert.issuer,
        issue_date=cert.issue_date,
        expiry_date=cert.expiry_date,
        credential_id=cert.credential_id,
        credential_url=cert.credential_url,
        skills_covered=cert.skills_covered or [],
        bullets=[{**b, "id": f"b_{uuid.uuid4().hex[:8]}"} for b in (cert.bullets or [])],
        evidence_url=cert.evidence_url,
        verification_status=cert.verification_status,
        is_visible=cert.is_visible,
        is_archived=False
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


@router.put("/certifications/{item_id}/archive")
def archive_certification(
    item_id: int,
    req: Optional[ArchiveToggleRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cert = db.query(CourseCertification).filter(
        CourseCertification.id == item_id,
        CourseCertification.user_id == current_user.id
    ).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")

    cert.is_archived = req.is_archived if req and req.is_archived is not None else not cert.is_archived
    db.commit()
    return {"id": cert.id, "is_archived": cert.is_archived}


@router.delete("/certifications/{item_id}")
def delete_certification(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cert = db.query(CourseCertification).filter(
        CourseCertification.id == item_id,
        CourseCertification.user_id == current_user.id
    ).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")
    db.delete(cert)
    db.commit()
    return {"message": "Certification deleted successfully"}


# -------------------------------------------------------------
# 9. Leadership & Extracurricular Activities Module
# -------------------------------------------------------------

@router.get("/leadership")
def list_leadership(
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(CandidateLeadership).filter(CandidateLeadership.user_id == current_user.id)
    if not include_archived:
        query = query.filter(CandidateLeadership.is_archived.is_(False))
    return query.order_by(CandidateLeadership.created_at.desc()).all()


@router.post("/leadership")
def create_leadership(
    req: LeadershipRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data = req.model_dump()
    data["bullets"] = normalize_bullets(data.get("bullets"))
    leader = CandidateLeadership(user_id=current_user.id, **data)
    db.add(leader)
    db.commit()
    db.refresh(leader)
    return leader


@router.put("/leadership/{item_id}")
def update_leadership(
    item_id: int,
    req: LeadershipRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    leader = db.query(CandidateLeadership).filter(
        CandidateLeadership.id == item_id,
        CandidateLeadership.user_id == current_user.id
    ).first()
    if not leader:
        raise HTTPException(status_code=404, detail="Leadership record not found")

    data = req.model_dump()
    if "bullets" in data:
        data["bullets"] = normalize_bullets(data.get("bullets"))

    for k, v in data.items():
        setattr(leader, k, v)
    db.commit()
    db.refresh(leader)
    return leader


@router.post("/leadership/{item_id}/duplicate")
def duplicate_leadership(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    leader = db.query(CandidateLeadership).filter(
        CandidateLeadership.id == item_id,
        CandidateLeadership.user_id == current_user.id
    ).first()
    if not leader:
        raise HTTPException(status_code=404, detail="Leadership record not found")

    clone = CandidateLeadership(
        user_id=current_user.id,
        organization=f"{leader.organization} (Copy)",
        role=leader.role,
        category=leader.category,
        start_date=leader.start_date,
        end_date=leader.end_date,
        currently_active=leader.currently_active,
        description=leader.description,
        responsibilities=leader.responsibilities,
        bullets=[{**b, "id": f"b_{uuid.uuid4().hex[:8]}"} for b in (leader.bullets or [])],
        evidence_url=leader.evidence_url,
        verification_status=leader.verification_status,
        is_visible=leader.is_visible,
        is_archived=False
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


@router.put("/leadership/{item_id}/archive")
def archive_leadership(
    item_id: int,
    req: Optional[ArchiveToggleRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    leader = db.query(CandidateLeadership).filter(
        CandidateLeadership.id == item_id,
        CandidateLeadership.user_id == current_user.id
    ).first()
    if not leader:
        raise HTTPException(status_code=404, detail="Leadership record not found")

    leader.is_archived = req.is_archived if req and req.is_archived is not None else not leader.is_archived
    db.commit()
    return {"id": leader.id, "is_archived": leader.is_archived}


@router.delete("/leadership/{item_id}")
def delete_leadership(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    leader = db.query(CandidateLeadership).filter(
        CandidateLeadership.id == item_id,
        CandidateLeadership.user_id == current_user.id
    ).first()
    if not leader:
        raise HTTPException(status_code=404, detail="Leadership record not found")
    db.delete(leader)
    db.commit()
    return {"message": "Leadership record deleted successfully"}


# -------------------------------------------------------------
# 10. Relevant Coursework Module
# -------------------------------------------------------------

@router.get("/coursework")
def list_coursework(
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(CandidateCoursework).filter(CandidateCoursework.user_id == current_user.id)
    if not include_archived:
        query = query.filter(CandidateCoursework.is_archived.is_(False))
    return query.order_by(CandidateCoursework.created_at.desc()).all()


@router.post("/coursework")
def create_coursework(
    req: CourseworkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data = req.model_dump()
    cw = CandidateCoursework(user_id=current_user.id, **data)
    db.add(cw)
    db.commit()
    db.refresh(cw)
    return cw


@router.put("/coursework/{item_id}")
def update_coursework(
    item_id: int,
    req: CourseworkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cw = db.query(CandidateCoursework).filter(
        CandidateCoursework.id == item_id,
        CandidateCoursework.user_id == current_user.id
    ).first()
    if not cw:
        raise HTTPException(status_code=404, detail="Coursework record not found")

    for k, v in req.model_dump().items():
        setattr(cw, k, v)
    db.commit()
    db.refresh(cw)
    return cw


@router.post("/coursework/{item_id}/duplicate")
def duplicate_coursework(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cw = db.query(CandidateCoursework).filter(
        CandidateCoursework.id == item_id,
        CandidateCoursework.user_id == current_user.id
    ).first()
    if not cw:
        raise HTTPException(status_code=404, detail="Coursework record not found")

    clone = CandidateCoursework(
        user_id=current_user.id,
        course_name=f"{cw.course_name} (Copy)",
        course_code=cw.course_code,
        institution=cw.institution,
        term_or_year=cw.term_or_year,
        grade=cw.grade,
        skills_learned=cw.skills_learned or [],
        description=cw.description,
        topics_covered=cw.topics_covered or [],
        evidence_url=cw.evidence_url,
        verification_status=cw.verification_status,
        is_visible=cw.is_visible,
        is_archived=False
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


@router.put("/coursework/{item_id}/archive")
def archive_coursework(
    item_id: int,
    req: Optional[ArchiveToggleRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cw = db.query(CandidateCoursework).filter(
        CandidateCoursework.id == item_id,
        CandidateCoursework.user_id == current_user.id
    ).first()
    if not cw:
        raise HTTPException(status_code=404, detail="Coursework record not found")

    cw.is_archived = req.is_archived if req and req.is_archived is not None else not cw.is_archived
    db.commit()
    return {"id": cw.id, "is_archived": cw.is_archived}


@router.delete("/coursework/{item_id}")
def delete_coursework(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cw = db.query(CandidateCoursework).filter(
        CandidateCoursework.id == item_id,
        CandidateCoursework.user_id == current_user.id
    ).first()
    if not cw:
        raise HTTPException(status_code=404, detail="Coursework record not found")
    db.delete(cw)
    db.commit()
    return {"message": "Coursework record deleted successfully"}


# -------------------------------------------------------------
# 11. Publications & Open Source Contributions Module
# -------------------------------------------------------------

@router.get("/publications")
def list_publications(
    include_archived: bool = False,
    pub_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(CandidatePublication).filter(CandidatePublication.user_id == current_user.id)
    if not include_archived:
        query = query.filter(CandidatePublication.is_archived.is_(False))
    if pub_type:
        query = query.filter(CandidatePublication.publication_type == pub_type)
    return query.order_by(CandidatePublication.publication_date.desc()).all()


@router.post("/publications")
def create_publication(
    req: PublicationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data = req.model_dump()
    data["bullets"] = normalize_bullets(data.get("bullets"))
    pub = CandidatePublication(user_id=current_user.id, **data)
    db.add(pub)
    db.commit()
    db.refresh(pub)
    return pub


@router.put("/publications/{item_id}")
def update_publication(
    item_id: int,
    req: PublicationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pub = db.query(CandidatePublication).filter(
        CandidatePublication.id == item_id,
        CandidatePublication.user_id == current_user.id
    ).first()
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")

    data = req.model_dump()
    if "bullets" in data:
        data["bullets"] = normalize_bullets(data.get("bullets"))

    for k, v in data.items():
        setattr(pub, k, v)
    db.commit()
    db.refresh(pub)
    return pub


@router.post("/publications/{item_id}/duplicate")
def duplicate_publication(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pub = db.query(CandidatePublication).filter(
        CandidatePublication.id == item_id,
        CandidatePublication.user_id == current_user.id
    ).first()
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")

    clone = CandidatePublication(
        user_id=current_user.id,
        title=f"{pub.title} (Copy)",
        publication_type=pub.publication_type,
        venue_or_publisher=pub.venue_or_publisher,
        publication_date=pub.publication_date,
        authors=pub.authors or [],
        url=pub.url,
        doi_or_id=pub.doi_or_id,
        description=pub.description,
        citation_count_or_metrics=pub.citation_count_or_metrics,
        bullets=[{**b, "id": f"b_{uuid.uuid4().hex[:8]}"} for b in (pub.bullets or [])],
        evidence_url=pub.evidence_url,
        verification_status=pub.verification_status,
        is_visible=pub.is_visible,
        is_archived=False
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


@router.put("/publications/{item_id}/archive")
def archive_publication(
    item_id: int,
    req: Optional[ArchiveToggleRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pub = db.query(CandidatePublication).filter(
        CandidatePublication.id == item_id,
        CandidatePublication.user_id == current_user.id
    ).first()
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")

    pub.is_archived = req.is_archived if req and req.is_archived is not None else not pub.is_archived
    db.commit()
    return {"id": pub.id, "is_archived": pub.is_archived}


@router.delete("/publications/{item_id}")
def delete_publication(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    pub = db.query(CandidatePublication).filter(
        CandidatePublication.id == item_id,
        CandidatePublication.user_id == current_user.id
    ).first()
    if not pub:
        raise HTTPException(status_code=404, detail="Publication not found")
    db.delete(pub)
    db.commit()
    return {"message": "Publication deleted successfully"}


# -------------------------------------------------------------
# 12. Custom Additional Sections Module
# -------------------------------------------------------------

@router.get("/custom-sections")
def list_custom_sections(
    section_title: Optional[str] = None,
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(CandidateCustomSection).filter(CandidateCustomSection.user_id == current_user.id)
    if not include_archived:
        query = query.filter(CandidateCustomSection.is_archived.is_(False))
    if section_title:
        query = query.filter(CandidateCustomSection.section_title == section_title)
    return query.order_by(CandidateCustomSection.created_at.desc()).all()


@router.post("/custom-sections")
def create_custom_section(
    req: CustomSectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    data = req.model_dump()
    data["bullets"] = normalize_bullets(data.get("bullets"))
    cs = CandidateCustomSection(user_id=current_user.id, **data)
    db.add(cs)
    db.commit()
    db.refresh(cs)
    return cs


@router.put("/custom-sections/{item_id}")
def update_custom_section(
    item_id: int,
    req: CustomSectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cs = db.query(CandidateCustomSection).filter(
        CandidateCustomSection.id == item_id,
        CandidateCustomSection.user_id == current_user.id
    ).first()
    if not cs:
        raise HTTPException(status_code=404, detail="Custom section record not found")

    data = req.model_dump()
    if "bullets" in data:
        data["bullets"] = normalize_bullets(data.get("bullets"))

    for k, v in data.items():
        setattr(cs, k, v)
    db.commit()
    db.refresh(cs)
    return cs


@router.post("/custom-sections/{item_id}/duplicate")
def duplicate_custom_section(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cs = db.query(CandidateCustomSection).filter(
        CandidateCustomSection.id == item_id,
        CandidateCustomSection.user_id == current_user.id
    ).first()
    if not cs:
        raise HTTPException(status_code=404, detail="Custom section record not found")

    clone = CandidateCustomSection(
        user_id=current_user.id,
        section_title=cs.section_title,
        title=f"{cs.title} (Copy)",
        subtitle=cs.subtitle,
        date_or_year=cs.date_or_year,
        location=cs.location,
        description=cs.description,
        bullets=[{**b, "id": f"b_{uuid.uuid4().hex[:8]}"} for b in (cs.bullets or [])],
        url=cs.url,
        evidence_url=cs.evidence_url,
        verification_status=cs.verification_status,
        is_visible=cs.is_visible,
        is_archived=False
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


@router.put("/custom-sections/{item_id}/archive")
def archive_custom_section(
    item_id: int,
    req: Optional[ArchiveToggleRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cs = db.query(CandidateCustomSection).filter(
        CandidateCustomSection.id == item_id,
        CandidateCustomSection.user_id == current_user.id
    ).first()
    if not cs:
        raise HTTPException(status_code=404, detail="Custom section record not found")

    cs.is_archived = req.is_archived if req and req.is_archived is not None else not cs.is_archived
    db.commit()
    return {"id": cs.id, "is_archived": cs.is_archived}


@router.delete("/custom-sections/{item_id}")
def delete_custom_section(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    cs = db.query(CandidateCustomSection).filter(
        CandidateCustomSection.id == item_id,
        CandidateCustomSection.user_id == current_user.id
    ).first()
    if not cs:
        raise HTTPException(status_code=404, detail="Custom section record not found")
    db.delete(cs)
    db.commit()
    return {"message": "Custom section record deleted successfully"}
