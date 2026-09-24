from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.models.user import User
from app.models.profile import Profile
from app.models.job import Job
from app.api.auth import get_current_user
from app.services.scraper.github import fetch_github_projects
from app.services.ai.github_analyzer import analyze_github_projects
from app.services.github_sync import sync_github_for_user, normalize_github_username

router = APIRouter()

class GithubAnalyzeRequest(BaseModel):
    job_id: int
    github_username: Optional[str] = None

@router.post("/analyze")
def analyze_github(
    request: GithubAnalyzeRequest, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Profile not found.")
        
    username = request.github_username or profile.github_username
    if not username:
        raise HTTPException(status_code=400, detail="GitHub username is required either in request or profile.")
        
    # Update the profile with the provided username if new
    if request.github_username and profile.github_username != request.github_username:
        profile.github_username = request.github_username
        db.commit()
        
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
        
    job_desc = job.description or job.title
    
    # 1. Fetch from GitHub
    raw_projects = fetch_github_projects(username)
    if not raw_projects:
        return {"relevant_projects": []}
        
    # 2. Analyze with AI
    analyzed_data = analyze_github_projects(raw_projects, job_desc)
    
    # 3. Store job-relevant projects in profile.projects_json (relevance cache only;
    #    full project list lives in the Project table via /sync)
    if analyzed_data and "relevant_projects" in analyzed_data:
        profile.projects_json = analyzed_data["relevant_projects"]
        db.commit()
        
    return analyzed_data

class GithubSyncRequest(BaseModel):
    github_username: str

@router.post("/sync")
def sync_github_profile(
    request: GithubSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    username = normalize_github_username(request.github_username)
    if not username:
        raise HTTPException(status_code=400, detail="Valid GitHub username is required.")

    try:
        result = sync_github_for_user(db, current_user.id, username)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch GitHub projects: {e}")

    return {
        "message": f"Successfully synced GitHub profile '{result['username']}'",
        "synced_projects": result["synced_projects"],
        "discovered_skills_count": result["discovered_skills_count"],
        "discovered_achievements_count": result["discovered_achievements_count"],
    }
