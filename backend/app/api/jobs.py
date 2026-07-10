from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.profile import Profile
from app.api.auth import get_current_user
from app.schemas.job import JobResponse, JobAnalysisResult
from app.services.ai.matcher import analyze_job_match
from app.workers.scraper_tasks import run_job_discovery
from typing import List

router = APIRouter()

@router.get("/", response_model=List[JobResponse])
def get_jobs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    jobs = db.query(Job).offset(skip).limit(limit).all()
    return jobs

@router.post("/discover")
def trigger_discovery(source: str = "yc", current_user: User = Depends(get_current_user)):
    """Triggers background celery task to scrape jobs."""
    run_job_discovery.delay(source)
    return {"message": f"Discovery task started for source: {source}"}

@router.post("/{job_id}/analyze", response_model=JobAnalysisResult)
def analyze_job(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile or not profile.raw_resume_text:
        raise HTTPException(status_code=400, detail="Profile or resume not found. Upload resume first.")
        
    analysis = analyze_job_match(profile.raw_resume_text, job.description or job.title)
    
    # Update job status
    job.status = "analyzed"
    db.commit()
    
    return analysis
