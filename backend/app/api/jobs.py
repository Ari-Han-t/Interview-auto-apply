from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc
from app.core.database import get_db
from app.models.user import User
from app.models.job import Job, UserSavedJob, JobSourceSyncLog, JobSourceConfig
from app.models.profile import Profile
from app.api.auth import get_current_user
from app.schemas.job import (
    JobResponse, 
    JobAnalysisResult, 
    JobDiscoveryRequest,
    JobImportUrlRequest,
    JobCreateManual,
    JobSaveRequest,
    SourceHealthInfo,
    SyncLogResponse,
    JobSearchResponse
)
from app.services.ai.matcher import analyze_job_match
from app.services.ai.job_analyzer import analyze_job_details
from app.models.technology import Technology
from app.workers.scraper_tasks import run_job_discovery
from app.services.scraper.adapters.registry import (
    get_adapter, 
    list_adapters, 
    get_sources_health, 
    route_url_to_adapter
)
from app.services.job_ingestion.engine import JobIngestionEngine
from app.services.job_ingestion.url_importer import import_job_from_url
from app.services.job_ingestion.nl_query_parser import parse_natural_language_job_query
from app.services.job_ingestion.deduplicator import compute_job_dedup_hash
from datetime import datetime
from typing import List, Optional, Dict, Any

router = APIRouter()

@router.get("/", response_model=List[JobResponse])
def get_jobs(
    q: Optional[str] = Query(None, description="Free-text or natural language query"),
    skills: Optional[str] = Query(None, description="Comma-separated skill names"),
    company: Optional[str] = Query(None, description="Company name"),
    location: Optional[str] = Query(None, description="Location"),
    work_arrangement: Optional[str] = Query("all", description="remote, hybrid, onsite, all"),
    job_type: Optional[str] = Query("all", description="internship, fulltime, contract, all"),
    min_compensation: Optional[float] = Query(None, description="Minimum compensation"),
    graduation_year: Optional[str] = Query(None, description="Graduation year restriction"),
    source: Optional[str] = Query("all", description="Specific source or all"),
    saved_only: bool = Query(False, description="Filter to jobs saved by current user"),
    exclude_expired: bool = Query(True, description="Filter out expired jobs"),
    sort_by: str = Query("newest", description="newest, match_score, compensation, deadline"),
    skip: int = 0, 
    limit: int = 50, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    query = db.query(Job)

    # Saved jobs filtering
    saved_job_ids = {
        s.job_id for s in db.query(UserSavedJob).filter(UserSavedJob.user_id == current_user.id).all()
    }
    if saved_only:
        query = query.filter(Job.id.in_(saved_job_ids if saved_job_ids else [-1]))

    # Expired filter
    if exclude_expired:
        query = query.filter(Job.is_expired == False)

    # Natural Language / Keyword Search
    parsed_nl = {}
    if q and q.strip():
        parsed_nl = parse_natural_language_job_query(q.strip())
        role_kw = parsed_nl.get("role_keywords") or q.strip()
        
        # Apply role keywords if present
        if role_kw:
            terms = [t for t in role_kw.split() if len(t) > 2]
            if terms:
                kw_conditions = []
                for term in terms:
                    kw_conditions.append(Job.title.ilike(f"%{term}%"))
                    kw_conditions.append(Job.description.ilike(f"%{term}%"))
                    kw_conditions.append(Job.company.ilike(f"%{term}%"))
                query = query.filter(or_(*kw_conditions))
            else:
                query = query.filter(or_(
                    Job.title.ilike(f"%{q}%"),
                    Job.company.ilike(f"%{q}%"),
                    Job.description.ilike(f"%{q}%")
                ))

        # Merge NL-detected filters if not explicitly overridden by query params
        if parsed_nl.get("job_type") and parsed_nl["job_type"] != "both" and job_type == "all":
            job_type = parsed_nl["job_type"]
        if parsed_nl.get("work_arrangement") and parsed_nl["work_arrangement"] != "all" and work_arrangement == "all":
            work_arrangement = parsed_nl["work_arrangement"]
        if parsed_nl.get("location") and not location:
            location = parsed_nl["location"]
        if parsed_nl.get("skills") and not skills:
            skills = ",".join(parsed_nl["skills"])
        if parsed_nl.get("min_compensation") and not min_compensation:
            min_compensation = parsed_nl["min_compensation"]
        if parsed_nl.get("graduation_year") and not graduation_year:
            graduation_year = parsed_nl["graduation_year"]

    # Filter: Company
    if company and company.strip():
        query = query.filter(Job.company.ilike(f"%{company.strip()}%"))

    # Filter: Location
    if location and location.strip():
        query = query.filter(Job.location.ilike(f"%{location.strip()}%"))

    # Filter: Work Arrangement
    if work_arrangement and work_arrangement != "all":
        if work_arrangement == "remote":
            query = query.filter(or_(Job.work_arrangement == "remote", Job.is_remote == True))
        else:
            query = query.filter(Job.work_arrangement == work_arrangement)

    # Filter: Job Type
    if job_type and job_type != "all" and job_type != "both":
        query = query.filter(Job.employment_type == job_type)

    # Filter: Source
    if source and source != "all":
        query = query.filter(Job.source == source)

    # Filter: Minimum Compensation
    if min_compensation is not None:
        query = query.filter(or_(
            Job.compensation_min >= min_compensation,
            Job.compensation_max >= min_compensation
        ))

    # Filter: Graduation Year
    if graduation_year:
        query = query.filter(Job.graduation_restrictions.cast(str).ilike(f"%{graduation_year}%"))

    # Filter: Skills
    if skills and skills.strip():
        skill_list = [s.strip().lower() for s in skills.split(",") if s.strip()]
        for sk in skill_list:
            query = query.filter(or_(
                Job.description.ilike(f"%{sk}%"),
                Job.title.ilike(f"%{sk}%"),
                Job.tech_stack_json.cast(str).ilike(f"%{sk}%"),
                Job.required_skills_json.cast(str).ilike(f"%{sk}%")
            ))

    # Sorting
    if sort_by == "deadline":
        query = query.order_by(asc(Job.deadline).nullslast(), desc(Job.posted_at))
    elif sort_by == "compensation":
        query = query.order_by(desc(Job.compensation_max).nullslast(), desc(Job.posted_at))
    else: # newest
        query = query.order_by(desc(Job.posted_at).nullslast(), desc(Job.id))

    jobs = query.offset(skip).limit(limit).all()

    # Calculate eligibility & saved status
    from app.services.ai.eligibility import evaluate_eligibility
    for job in jobs:
        res = evaluate_eligibility(current_user.id, job.id, db, allow_requirement_extraction=False)
        job.eligible = res["eligible"]
        job.rejection_reason = res["reason"]
        job.is_saved = job.id in saved_job_ids

    return jobs

@router.get("/sources/health", response_model=List[SourceHealthInfo])
def get_sources_health_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns source health, catalog capabilities, and authentication requirements for all sources."""
    adapters = list_adapters()
    health_list = []
    
    for a in adapters:
        cfg = db.query(JobSourceConfig).filter(JobSourceConfig.source_id == a.source_id).first()
        total_jobs = db.query(Job).filter(Job.source == a.source_id).count()
        recent_log = db.query(JobSourceSyncLog).filter(
            JobSourceSyncLog.source_id == a.source_id
        ).order_by(desc(JobSourceSyncLog.id)).first()

        health_list.append(SourceHealthInfo(
            source_id=a.source_id,
            display_name=a.name,
            auth_status=a.auth_status,
            can_fetch_catalog=a.can_fetch_catalog,
            access_requirement=a.access_requirement,
            last_sync_at=cfg.last_sync_at if cfg else (recent_log.started_at if recent_log else None),
            is_healthy=a.auth_status in ("available", "limited"),
            total_jobs_indexed=total_jobs,
            recent_sync_status=recent_log.status if recent_log else None
        ))
        
    return health_list

@router.get("/sources/logs", response_model=List[SyncLogResponse])
def get_sources_sync_logs(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns recent synchronization and health audit logs."""
    logs = db.query(JobSourceSyncLog).order_by(desc(JobSourceSyncLog.id)).limit(limit).all()
    return logs

@router.post("/sync")
def trigger_synchronization(
    source: str = Query("all", description="Specific source or all"),
    keywords: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    job_type: str = Query("both"),
    custom_token: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Triggers immediate synchronization across source adapters with error isolation.
    """
    if source == "all":
        results = JobIngestionEngine.sync_all_sources(
            db=db,
            keywords=keywords,
            location=location,
            job_type=job_type,
            triggered_by="manual"
        )
        return {
            "message": "Synchronization complete across all active sources",
            "results": results
        }
    else:
        res = JobIngestionEngine.sync_source(
            source_id=source,
            db=db,
            keywords=keywords,
            location=location,
            job_type=job_type,
            custom_token=custom_token,
            triggered_by="manual"
        )
        return {
            "message": f"Synchronization complete for source '{source}'",
            "result": res
        }

@router.post("/import-url", response_model=JobResponse)
def import_job_url(
    req: JobImportUrlRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Imports a canonical job record from any supported job URL
    (Greenhouse, Lever, Ashby, YC, Internshala, LinkedIn, or official company career page).
    """
    try:
        job = import_job_from_url(req.url, db)
        return job
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/manual", response_model=JobResponse)
def create_manual_job(
    data: JobCreateManual,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a canonical job record directly from manual input."""
    dedup_hash = compute_job_dedup_hash(
        data.company, 
        data.title, 
        data.location, 
        data.employment_type
    )
    
    job = Job(
        title=data.title,
        company=data.company,
        url=data.url,
        application_url=data.application_url or data.url,
        description=data.description or f"{data.title} position at {data.company}",
        responsibilities_json=data.responsibilities_json or [],
        required_skills_json=data.required_skills_json or [],
        preferred_skills_json=data.preferred_skills_json or [],
        requirements_json=data.requirements_json or {},
        eligibility_criteria_json=data.eligibility_criteria_json or {},
        graduation_restrictions=data.graduation_restrictions or [],
        status="active",
        deadline=data.deadline,
        location=data.location or "Remote",
        work_arrangement=data.work_arrangement or "onsite",
        employment_type=data.employment_type or "fulltime",
        salary_range=data.salary_range,
        compensation_min=data.compensation_min,
        compensation_max=data.compensation_max,
        currency=data.currency or "USD",
        compensation_interval=data.compensation_interval,
        is_remote=data.is_remote or False,
        tech_stack_json=data.tech_stack_json or [],
        company_logo_url=data.company_logo_url,
        source=data.source or "manual",
        source_job_id=data.source_job_id,
        source_provenance={
            "adapter": "manual_entry",
            "created_by_user": current_user.id,
            "confidence": "candidate_attested"
        },
        posted_at=data.posted_at or datetime.utcnow(),
        last_verified_at=datetime.utcnow(),
        is_expired=False,
        dedup_hash=dedup_hash
    )
    
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

@router.post("/{job_id}/save")
def save_job(
    job_id: int,
    req: Optional[JobSaveRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Saves / bookmarks a job for the candidate."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing = db.query(UserSavedJob).filter(
        UserSavedJob.user_id == current_user.id,
        UserSavedJob.job_id == job_id
    ).first()

    if not existing:
        saved = UserSavedJob(
            user_id=current_user.id,
            job_id=job_id,
            notes=req.notes if req else None
        )
        db.add(saved)
        db.commit()

    return {"message": "Job bookmarked successfully", "job_id": job_id, "is_saved": True}

@router.delete("/{job_id}/save")
def unsave_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Removes a job bookmark for the candidate."""
    saved = db.query(UserSavedJob).filter(
        UserSavedJob.user_id == current_user.id,
        UserSavedJob.job_id == job_id
    ).first()

    if saved:
        db.delete(saved)
        db.commit()

    return {"message": "Job removed from saved bookmarks", "job_id": job_id, "is_saved": False}

@router.post("/{job_id}/verify-status")
def verify_job_status(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Probes source URL to verify if job is active or expired."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # If deadline has passed
    if job.deadline and job.deadline < datetime.utcnow():
        job.is_expired = True
        job.status = "expired"
        job.last_verified_at = datetime.utcnow()
        db.commit()
        return {"status": "expired", "reason": "Deadline has passed", "last_verified_at": job.last_verified_at}

    if job.url:
        adapter = route_url_to_adapter(job.url)
        is_active = adapter.check_job_active(job.url)
        if not is_active:
            job.is_expired = True
            job.status = "expired"
        else:
            job.is_expired = False
            job.status = "active"
            
    job.last_verified_at = datetime.utcnow()
    db.commit()
    return {
        "status": "expired" if job.is_expired else "active",
        "last_verified_at": job.last_verified_at
    }

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

    # Check saved status
    saved = db.query(UserSavedJob).filter(
        UserSavedJob.user_id == current_user.id,
        UserSavedJob.job_id == job.id
    ).first()
    job.is_saved = bool(saved)
    
    return job

@router.post("/discover")
def trigger_discovery(
    request: JobDiscoveryRequest = None,
    source: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Triggers background celery task or thread to scrape jobs tailored to candidate preferences & resume."""
    req_source = (request.source if request and request.source else source) or "all"
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

    try:
        run_job_discovery.delay(
            source=req_source,
            keywords=keywords,
            location=location,
            job_type=job_type,
            only_suited=only_suited,
            user_id=current_user.id
        )
    except Exception as celery_err:
        import threading
        target_fn = run_job_discovery.run if hasattr(run_job_discovery, "run") else run_job_discovery
        threading.Thread(
            target=target_fn,
            kwargs={
                "source": req_source,
                "keywords": keywords,
                "location": location,
                "job_type": job_type,
                "only_suited": only_suited,
                "user_id": current_user.id
            },
            daemon=True
        ).start()
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
        tech = db.query(Technology).filter(Technology.name == tech_name).first()
        if not tech:
            tech = Technology(name=tech_name)
            db.add(tech)
            db.flush()
        if tech not in job.technologies:
            job.technologies.append(tech)

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

    from app.models.profile import Profile
    profile_old = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    latex_resume = profile_old.latex_template if (profile_old and profile_old.latex_template) else ""

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
