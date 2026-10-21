from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.company_research import CompanyResearch
from app.models.job import Job
from app.models.application import Application
from app.api.auth import get_current_user
from app.services.company_research.service import generate_company_research

router = APIRouter()

class CompanyResearchRequest(BaseModel):
    force_refresh: bool = False

def _serialize_research(research: CompanyResearch, job: Optional[Job] = None) -> Dict[str, Any]:
    return {
        "id": research.id,
        "job_id": research.job_id,
        "company_name": research.company_name,
        "role": job.title if job else "Software Engineer",
        "job_location": job.location if job else None,
        "job_url": job.url if job else None,
        "company_overview": research.company_overview,
        "products_and_services": research.products_and_services or [],
        "industry_and_business_model": research.industry_and_business_model,
        "target_customers_or_markets": research.target_customers_or_markets,
        "recent_announcements": research.recent_announcements or [],
        "engineering_challenges": research.engineering_challenges or [],
        "key_skills_in_position": research.key_skills_in_position or [],
        "candidate_relevant_experience": research.candidate_relevant_experience or [],
        "interview_topics_to_prep": research.interview_topics_to_prep or [],
        "verified_facts": research.verified_facts or [],
        "inferred_insights": research.inferred_insights or [],
        "unavailable_fields": research.unavailable_fields or [],
        "sources": research.sources or [],
        "summary_markdown": research.summary_markdown,
        "retrieval_date": research.retrieval_date,
        "created_at": research.created_at,
    }

@router.get("/")
def list_company_research(
    q: Optional[str] = Query(None, description="Search query for company name or role"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Lists all saved company research briefs and provides available jobs ready for research.
    """
    query = db.query(CompanyResearch, Job).join(Job, CompanyResearch.job_id == Job.id).filter(
        (CompanyResearch.user_id == current_user.id) | (CompanyResearch.user_id.is_(None))
    )
    if q:
        search_pattern = f"%{q.strip()}%"
        query = query.filter(
            (CompanyResearch.company_name.ilike(search_pattern)) |
            (Job.title.ilike(search_pattern))
        )

    briefs = query.order_by(CompanyResearch.created_at.desc()).all()
    serialized_briefs = [_serialize_research(res, job) for res, job in briefs]

    # Also return list of jobs for research selection
    researched_job_ids = {res.job_id for res, _ in briefs}
    available_jobs_query = db.query(Job).order_by(Job.created_at.desc())
    if q:
        available_jobs_query = available_jobs_query.filter(
            (Job.company.ilike(f"%{q.strip()}%")) | (Job.title.ilike(f"%{q.strip()}%"))
        )
    candidate_jobs = available_jobs_query.limit(30).all()

    available_jobs = [
        {
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location,
            "work_arrangement": j.work_arrangement,
            "has_research": j.id in researched_job_ids,
        }
        for j in candidate_jobs
    ]

    return {
        "briefs": serialized_briefs,
        "available_jobs": available_jobs,
        "total_briefs": len(serialized_briefs),
    }

@router.get("/job/{job_id}")
def get_job_company_research(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves existing company research brief for a specific job."""
    research = (
        db.query(CompanyResearch)
        .filter(
            CompanyResearch.job_id == job_id,
            (CompanyResearch.user_id == current_user.id) | (CompanyResearch.user_id.is_(None))
        )
        .order_by(CompanyResearch.id.desc())
        .first()
    )
    if not research:
        return None

    job = db.query(Job).filter(Job.id == job_id).first()
    return _serialize_research(research, job)

@router.post("/job/{job_id}")
def create_or_refresh_company_research(
    job_id: int,
    req: CompanyResearchRequest = CompanyResearchRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generates or refreshes a company and role research brief for a specific job."""
    try:
        record = generate_company_research(
            job_id=job_id,
            user_id=current_user.id,
            db=db,
            force_refresh=req.force_refresh,
        )

        job = db.query(Job).filter(Job.id == job_id).first()
        return _serialize_research(record, job)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Company research generation failed: {str(e)}")
