import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core import security
from app.core.rate_limiter import rate_limit
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token, ChangePassword
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)

class DeleteAccountRequest(BaseModel):
    password: Optional[str] = None
    confirm: bool = True

def get_current_user(request: Request, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    # Check bearer header first; fallback to cookie if header not provided
    if not token:
        cookie_token = request.cookies.get("access_token")
        if cookie_token and cookie_token.startswith("Bearer "):
            token = cookie_token.split(" ")[1]
        elif cookie_token:
            token = cookie_token

    # Check query parameter token fallback (e.g. for iframes, window.open, and direct downloads)
    if not token:
        query_token = request.query_params.get("token")
        if query_token and query_token.startswith("Bearer "):
            token = query_token.split(" ")[1]
        elif query_token:
            token = query_token

    if not token and getattr(security.settings, "AUTH_DISABLED", False):
        demo_user = db.query(User).filter(User.is_active.is_(True)).order_by(User.id.asc()).first()
        if demo_user is not None:
            return demo_user
        
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
        
    try:
        payload = security.jwt.decode(token, security.settings.SECRET_KEY, algorithms=[security.settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except security.JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/register", response_model=UserResponse, dependencies=[Depends(rate_limit("register", max_requests=10, window_seconds=60))])
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = security.get_password_hash(user_in.password)
    new_user = User(email=user_in.email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.post("/login", dependencies=[Depends(rate_limit("login", max_requests=15, window_seconds=60))])
def login(request: Request, response: Response, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    
    access_token = security.create_access_token(data={"sub": user.email})
    
    origin = request.headers.get("origin", "")
    is_cross_origin = origin.startswith("https://") or request.url.scheme == "https"
    
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=True if is_cross_origin else False,
        samesite="none" if is_cross_origin else "lax",
        max_age=security.settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return {
        "message": "Login successful",
        "token_type": "bearer",
        "access_token": access_token
    }

@router.post("/logout")
def logout(request: Request, response: Response):
    origin = request.headers.get("origin", "")
    is_cross_origin = origin.startswith("https://") or request.url.scheme == "https"
    response.delete_cookie(
        "access_token",
        secure=True if is_cross_origin else False,
        samesite="none" if is_cross_origin else "lax"
    )
    return {"message": "Logged out successfully"}

@router.post("/change-password", dependencies=[Depends(rate_limit("change-password", max_requests=10, window_seconds=60))])
def change_password(
    data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not security.verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    current_user.hashed_password = security.get_password_hash(data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}

@router.get("/export-data")
def export_user_account_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Exports comprehensive GDPR-compliant user data library and history in JSON format.
    """
    from app.models.profile import Profile
    from app.models.candidate import (
        UserProfile, CandidateEducation, CandidateExperience, Project,
        Skill, UserSkill, Achievement, CourseCertification,
        CandidateLeadership, CandidateCoursework, CandidatePublication,
        CandidateCustomSection, UserPreference, CandidateCapability
    )
    from app.models.resume import ResumeVersion
    from app.models.cover_letter import CoverLetter
    from app.models.application import Application
    from app.models.application_history import ApplicationHistory
    from app.models.company_research import CompanyResearch
    from app.models.interview_prep import InterviewQuestion, MockInterviewSession
    from app.models.notification import Notification
    from app.models.job import UserSavedJob

    # User profile
    u_prof = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    p_row = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    prefs = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
    caps = db.query(CandidateCapability).filter(CandidateCapability.user_id == current_user.id).first()

    # Content Library entries
    educations = db.query(CandidateEducation).filter(CandidateEducation.user_id == current_user.id).all()
    experiences = db.query(CandidateExperience).filter(CandidateExperience.user_id == current_user.id).all()
    projects = db.query(Project).filter(Project.user_id == current_user.id).all()
    achievements = db.query(Achievement).filter(Achievement.user_id == current_user.id).all()
    courses = db.query(CourseCertification).filter(CourseCertification.user_id == current_user.id).all()
    leaderships = db.query(CandidateLeadership).filter(CandidateLeadership.user_id == current_user.id).all()
    courseworks = db.query(CandidateCoursework).filter(CandidateCoursework.user_id == current_user.id).all()
    publications = db.query(CandidatePublication).filter(CandidatePublication.user_id == current_user.id).all()
    custom_secs = db.query(CandidateCustomSection).filter(CandidateCustomSection.user_id == current_user.id).all()

    # User skills
    user_skills = (
        db.query(UserSkill, Skill)
        .join(Skill, UserSkill.skill_id == Skill.id)
        .filter(UserSkill.user_id == current_user.id)
        .all()
    )

    # Generated documents & CRM
    resumes = db.query(ResumeVersion).filter(ResumeVersion.user_id == current_user.id).all()
    cover_letters = db.query(CoverLetter).filter(CoverLetter.user_id == current_user.id).all()
    applications = db.query(Application).filter(Application.user_id == current_user.id).all()
    app_ids = [a.id for a in applications]
    histories = db.query(ApplicationHistory).filter(ApplicationHistory.application_id.in_(app_ids)).all() if app_ids else []
    researches = db.query(CompanyResearch).filter(CompanyResearch.user_id == current_user.id).all()
    mock_sessions = db.query(MockInterviewSession).filter(MockInterviewSession.user_id == current_user.id).all()
    saved_jobs = db.query(UserSavedJob).filter(UserSavedJob.user_id == current_user.id).all()
    notifications = db.query(Notification).filter(Notification.user_id == current_user.id).all()

    export_payload = {
        "export_timestamp": datetime.now(timezone.utc).isoformat(),
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        },
        "profile": {
            "full_name": u_prof.full_name if u_prof else None,
            "preferred_name": u_prof.preferred_name if u_prof else None,
            "email": u_prof.email if u_prof else None,
            "phone": u_prof.phone if u_prof else None,
            "github": u_prof.github if u_prof else None,
            "linkedin": u_prof.linkedin if u_prof else None,
            "portfolio": u_prof.portfolio if u_prof else None,
            "website": u_prof.website if u_prof else None,
            "location": u_prof.current_location if u_prof else None,
            "degree": u_prof.degree if u_prof else None,
            "university": u_prof.university if u_prof else None,
            "cgpa": u_prof.cgpa if u_prof else None,
            "bio": u_prof.bio if u_prof else None,
            "tailoring_instructions": p_row.tailoring_instructions if p_row else None,
            "raw_resume_text": p_row.raw_resume_text if p_row else None,
        },
        "preferences": {
            "preferred_roles": prefs.preferred_roles if prefs else [],
            "preferred_locations": prefs.preferred_locations if prefs else [],
            "work_authorization": prefs.work_authorization if prefs else None,
            "visa_required": prefs.visa_required if prefs else False,
            "remote_preference": prefs.remote_preference if prefs else None,
        } if prefs else {},
        "capabilities": {
            "can_frontend": caps.can_frontend if caps else False,
            "can_backend": caps.can_backend if caps else False,
            "can_ai_ml": caps.can_ai_ml if caps else False,
            "can_devops": caps.can_devops if caps else False,
        } if caps else {},
        "content_library": {
            "educations": [
                {
                    "id": e.id, "institution": e.institution, "degree": e.degree,
                    "specialization": e.specialization, "graduation_year": e.graduation_year,
                    "cgpa": e.cgpa, "bullets": e.bullets or []
                } for e in educations
            ],
            "experiences": [
                {
                    "id": ex.id, "company": ex.company, "title": ex.title,
                    "location": ex.location, "start_date": ex.start_date, "end_date": ex.end_date,
                    "description": ex.description, "technologies": ex.technologies or [],
                    "bullets": ex.bullets or []
                } for ex in experiences
            ],
            "projects": [
                {
                    "id": p.id, "name": p.name, "description": p.description,
                    "github": p.github, "live_link": p.live_link,
                    "technologies": p.technologies or [], "bullets": p.bullets or []
                } for p in projects
            ],
            "skills": [
                {
                    "name": sk.name, "category": usk.category,
                    "confidence": usk.confidence, "years_used": usk.years_used
                } for usk, sk in user_skills
            ],
            "achievements": [
                {
                    "id": a.id, "title": a.title, "category": a.category,
                    "issuer_or_event": a.issuer_or_event, "year_or_date": a.year_or_date,
                    "description": a.description
                } for a in achievements
            ],
            "courses": [
                {
                    "id": c.id, "name": c.name, "issuer": c.issuer,
                    "credential_url": c.credential_url
                } for c in courses
            ],
            "leaderships": [
                {
                    "id": l.id, "role": l.role, "organization": l.organization,
                    "description": l.description
                } for l in leaderships
            ],
            "courseworks": [
                {
                    "id": cw.id, "course_name": cw.course_name, "institution": cw.institution
                } for cw in courseworks
            ],
            "publications": [
                {
                    "id": pub.id, "title": pub.title, "publisher": pub.publisher,
                    "url": pub.url
                } for pub in publications
            ],
            "custom_sections": [
                {
                    "id": cs.id, "section_title": cs.section_title, "content": cs.content
                } for cs in custom_secs
            ],
        },
        "resumes": [
            {
                "id": r.id, "name": r.name, "version_number": r.version_number,
                "is_master": bool(r.is_master), "target_role": r.target_role,
                "notes": r.notes, "template_name": r.template_name,
                "latex_source": r.latex_source, "created_at": r.created_at.isoformat() if r.created_at else None
            } for r in resumes
        ],
        "cover_letters": [
            {
                "id": cl.id, "job_id": cl.job_id, "style": cl.style,
                "content": cl.content, "version_number": cl.version_number,
                "is_approved": bool(cl.is_approved), "created_at": cl.created_at.isoformat() if cl.created_at else None
            } for cl in cover_letters
        ],
        "applications": [
            {
                "id": app.id, "job_id": app.job_id, "status": app.status,
                "submission_confirmed": bool(app.submission_confirmed),
                "applied_at": app.applied_at.isoformat() if app.applied_at else None,
                "notes": app.notes, "match_report": app.match_report,
                "interview_date": app.interview_date.isoformat() if app.interview_date else None,
                "history": [
                    {"status": h.status, "notes": h.notes, "created_at": h.created_at.isoformat() if h.created_at else None}
                    for h in histories if h.application_id == app.id
                ]
            } for app in applications
        ],
        "company_researches": [
            {
                "id": cr.id, "job_id": cr.job_id, "company_name": cr.company_name,
                "summary_markdown": cr.summary_markdown, "sources": cr.sources or []
            } for cr in researches
        ],
        "mock_interviews": [
            {
                "id": mi.id, "job_id": mi.job_id, "title": mi.title,
                "status": mi.status, "overall_score": mi.overall_score
            } for mi in mock_sessions
        ],
        "saved_jobs": [
            {"job_id": sj.job_id, "notes": sj.notes} for sj in saved_jobs
        ],
        "notifications": [
            {"id": n.id, "type": n.type, "message": n.message, "is_read": bool(n.is_read)} for n in notifications
        ]
    }
    return export_payload

@router.delete("/delete-account", dependencies=[Depends(rate_limit("delete-account", max_requests=5, window_seconds=60))])
def delete_user_account(
    req: DeleteAccountRequest = DeleteAccountRequest(),
    response: Response = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permanently deletes user account, all associated database records, and private storage assets.
    """
    if req.password and not security.verify_password(req.password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect password verification.")

    user_id = current_user.id

    from app.models.profile import Profile
    from app.models.candidate import (
        UserProfile, CandidateEducation, CandidateExperience, Project,
        Skill, UserSkill, Achievement, CourseCertification,
        CandidateLeadership, CandidateCoursework, CandidatePublication,
        CandidateCustomSection, UserPreference, CandidateCapability
    )
    from app.models.resume import ResumeVersion
    from app.models.cover_letter import CoverLetter
    from app.models.application import Application
    from app.models.application_history import ApplicationHistory
    from app.models.company_research import CompanyResearch
    from app.models.interview_prep import InterviewQuestion, MockInterviewSession
    from app.models.notification import Notification
    from app.models.job import UserSavedJob

    try:
        # 1. Applications & history
        user_apps = db.query(Application).filter(Application.user_id == user_id).all()
        for app in user_apps:
            db.query(ApplicationHistory).filter(ApplicationHistory.application_id == app.id).delete()
            db.delete(app)
        db.flush()

        # 2. Resumes, Cover Letters, Researches, Prep
        db.query(ResumeVersion).filter(ResumeVersion.user_id == user_id).delete()
        db.query(CoverLetter).filter(CoverLetter.user_id == user_id).delete()
        db.query(CompanyResearch).filter(CompanyResearch.user_id == user_id).delete()
        db.query(InterviewQuestion).filter(InterviewQuestion.user_id == user_id).delete()
        db.query(MockInterviewSession).filter(MockInterviewSession.user_id == user_id).delete()
        db.query(UserSavedJob).filter(UserSavedJob.user_id == user_id).delete()
        db.query(Notification).filter(Notification.user_id == user_id).delete()

        # 3. Content library
        db.query(UserSkill).filter(UserSkill.user_id == user_id).delete()
        db.query(CandidateEducation).filter(CandidateEducation.user_id == user_id).delete()
        db.query(CandidateExperience).filter(CandidateExperience.user_id == user_id).delete()
        db.query(Project).filter(Project.user_id == user_id).delete()
        db.query(Achievement).filter(Achievement.user_id == user_id).delete()
        db.query(CourseCertification).filter(CourseCertification.user_id == user_id).delete()
        db.query(CandidateLeadership).filter(CandidateLeadership.user_id == user_id).delete()
        db.query(CandidateCoursework).filter(CandidateCoursework.user_id == user_id).delete()
        db.query(CandidatePublication).filter(CandidatePublication.user_id == user_id).delete()
        db.query(CandidateCustomSection).filter(CandidateCustomSection.user_id == user_id).delete()
        db.query(CandidateCapability).filter(CandidateCapability.user_id == user_id).delete()
        db.query(UserPreference).filter(UserPreference.user_id == user_id).delete()
        db.query(UserProfile).filter(UserProfile.user_id == user_id).delete()
        db.query(Profile).filter(Profile.user_id == user_id).delete()

        # 4. User record
        db.delete(current_user)
        db.commit()

        # 5. Clean up filesystem
        for folder in [f"data/resumes/{user_id}", f"data/temp/{user_id}", f"data/applications/{user_id}"]:
            if os.path.exists(folder):
                try:
                    shutil.rmtree(folder)
                except Exception:
                    pass

        if response:
            response.delete_cookie("access_token")

        return {"message": "Account and all associated records permanently deleted."}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete account: {str(e)}")
