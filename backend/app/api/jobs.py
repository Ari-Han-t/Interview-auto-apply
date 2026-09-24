from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.profile import Profile
from app.api.auth import get_current_user
from app.schemas.job import JobResponse, JobAnalysisResult, JobDiscoveryRequest
from app.services.ai.matcher import analyze_job_match
from app.services.ai.job_analyzer import analyze_job_details
from app.models.technology import Technology
from app.workers.scraper_tasks import run_job_discovery
from typing import List

router = APIRouter()

@router.get("/", response_model=List[JobResponse])
def get_jobs(
    skip: int = 0, 
    limit: int = 100, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    jobs = db.query(Job).offset(skip).limit(limit).all()
    
    from app.services.ai.eligibility import evaluate_eligibility
    for job in jobs:
        res = evaluate_eligibility(current_user.id, job.id, db, allow_requirement_extraction=False)
        job.eligible = res["eligible"]
        job.rejection_reason = res["reason"]
        
    return jobs

@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    from app.services.ai.eligibility import evaluate_eligibility
    res = evaluate_eligibility(current_user.id, job.id, db)
    job.eligible = res["eligible"]
    job.rejection_reason = res["reason"]
    
    return job

@router.post("/discover")
def trigger_discovery(
    request: JobDiscoveryRequest = None,
    source: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Triggers background celery task to scrape jobs tailored to candidate preferences & resume."""
    req_source = (request.source if request and request.source else source) or "yc"
    keywords = request.keywords if request else None
    location = request.location if request else None
    job_type = request.job_type if request else "both"
    only_suited = request.only_suited if (request is not None and request.only_suited is not None) else True

    # Auto-derive defaults from user profile & preferences if missing
    if not keywords:
        from app.models.candidate import UserPreference, UserProfile
        pref = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
        
        if pref and pref.preferred_roles:
            keywords = ", ".join(pref.preferred_roles)
        elif profile and profile.degree:
            keywords = "Software Development"
        else:
            keywords = "Software Engineer"

    if not location:
        from app.models.candidate import UserProfile
        profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
        if profile and profile.current_location:
            location = profile.current_location
        else:
            location = "Remote"

    run_job_discovery.delay(
        source=req_source,
        keywords=keywords,
        location=location,
        job_type=job_type,
        only_suited=only_suited,
        user_id=current_user.id
    )
    return {
        "message": f"Discovery task started for source: {req_source}",
        "criteria": {
            "keywords": keywords,
            "location": location,
            "job_type": job_type,
            "only_suited": only_suited
        }
    }

@router.post("/{job_id}/analyze", response_model=JobAnalysisResult)
def analyze_job(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    from app.services.ai.eligibility import evaluate_eligibility
    res = evaluate_eligibility(current_user.id, job.id, db)
    if not res["eligible"]:
        raise HTTPException(status_code=400, detail=f"Cannot analyze ineligible job. Reason: {res['reason']}")
        
    from app.services.ai.profile_builder import build_profile_text
    profile_text = build_profile_text(current_user.id, db)
    if not profile_text:
        raise HTTPException(status_code=400, detail="Profile details not found. Please upload a resume or fill in your details in Settings.")
        
    # Extract detailed job criteria and tech stack
    try:
        details = analyze_job_details(job.title, job.description or "")
    except Exception as e:
        details = {}
        
    # Sync Technologies with DB
    extracted_techs = details.get("technologies", [])
    job.tech_stack_json = extracted_techs
    for tech_name in extracted_techs:
        # Check if technology already exists
        tech = db.query(Technology).filter(Technology.name == tech_name).first()
        if not tech:
            tech = Technology(name=tech_name)
            db.add(tech)
            db.flush()
        if tech not in job.technologies:
            job.technologies.append(tech)

    # 1. Fetch Candidate Projects Metadata
    from app.models.candidate import Project
    projects = db.query(Project).filter(Project.user_id == current_user.id).all()
    projects_meta = []
    for proj in projects:
        projects_meta.append({
            "name": proj.name,
            "description": proj.description,
            "technologies": proj.technologies or [],
            "github": proj.github,
            "live_link": proj.live_link
        })

    # 2. Fetch LaTeX Format Resume
    from app.models.profile import Profile
    profile_old = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    latex_resume = profile_old.latex_template if (profile_old and profile_old.latex_template) else ""

    # 3. Fetch Scraped Job Requirements/Metadata
    from app.models.candidate import JobRequirement
    job_req = db.query(JobRequirement).filter(JobRequirement.job_id == job_id).first()
    job_meta = {}
    if job_req:
        job_meta = {
            "minimum_experience": job_req.minimum_experience,
            "maximum_experience": job_req.maximum_experience,
            "minimum_degree": job_req.minimum_degree,
            "required_skills": job_req.required_skills or [],
            "preferred_skills": job_req.preferred_skills or [],
            "visa_required": job_req.visa_required,
            "location": job_req.location,
            "remote": job_req.remote,
            "salary": job_req.salary,
            "employment_type": job_req.employment_type,
            "technologies": job_req.technologies or [],
            "keywords": job_req.keywords or [],
            "company_size": job_req.company_size
        }

    try:
        analysis = analyze_job_match(
            profile_text=profile_text, 
            job_description=job.description or job.title,
            projects_meta=projects_meta,
            latex_resume=latex_resume,
            job_metadata=job_meta
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI analysis failed: {str(e)}")
    
    # Update job status and requirements json
    job.status = "analyzed"
    job.requirements_json = {
        "match_percentage": analysis.get("match_percentage", 0),
        "strengths": analysis.get("strengths", []),
        "weaknesses": analysis.get("weaknesses", []),
        "missing_keywords": analysis.get("missing_keywords", []),
        "required_skills": details.get("required_skills", []),
        "preferred_skills": details.get("preferred_skills", []),
        "years_of_experience": details.get("years_of_experience"),
        "degree_requirements": details.get("degree_requirements"),
        "keywords": details.get("keywords", []),
        "resume_similarity": analysis.get("resume_similarity", 0),
        "skill_overlap": analysis.get("skill_overlap", 0),
        "github_overlap": analysis.get("github_overlap", 0),
        "keyword_overlap": analysis.get("keyword_overlap", 0),
        "missing_skills": analysis.get("missing_skills", []),
        "reasoning": analysis.get("reasoning", ""),
    }
    db.commit()
    
    return analysis
