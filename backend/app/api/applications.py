from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.profile import Profile
from app.models.application import Application
from app.api.auth import get_current_user
from app.schemas.application import ApplicationResponse, GenerationResponse
from app.services.ai.generator import generate_tailored_resume, generate_cover_letter
from app.services.ai.matcher import analyze_job_match
from app.services.pdf_exporter import export_text_to_pdf
from app.workers.application_tasks import trigger_automation, resume_automation
from typing import List
import uuid

router = APIRouter()

@router.post("/generate/{job_id}", response_model=GenerationResponse)
def generate_application_materials(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile or not profile.raw_resume_text:
        raise HTTPException(status_code=400, detail="Profile or resume not found. Upload resume first.")

    # 1. Quick re-analysis to get strengths for Cover Letter
    analysis = analyze_job_match(profile.raw_resume_text, job.description or job.title)
    
    # 2. Generate Content
    if profile.latex_template:
        resume_text = generate_tailored_resume(profile.latex_template, job.description or job.title, job.title, is_latex=True)
        # We save the raw latex code to a local file instead of converting to PDF via reportlab
        run_id = str(uuid.uuid4())[:8]
        import os
        os.makedirs(f"data/applications/{current_user.id}", exist_ok=True)
        resume_pdf_path = f"data/applications/{current_user.id}/resume_{run_id}.tex"
        with open(resume_pdf_path, "w", encoding="utf-8") as f:
            f.write(resume_text)
    else:
        resume_text = generate_tailored_resume(profile.raw_resume_text, job.description or job.title, job.title)
        run_id = str(uuid.uuid4())[:8]
        resume_pdf_path = export_text_to_pdf(resume_text, f"resume_{current_user.id}_{run_id}.pdf")
        
    cl_text = generate_cover_letter(profile.raw_resume_text, job.company, job.title, analysis["strengths"])
    
    # 3. Export CL to PDF (or leave as markdown if preferred, but keeping pdf export for now)
    if 'run_id' not in locals():
        run_id = str(uuid.uuid4())[:8]
    cl_pdf_path = export_text_to_pdf(cl_text, f"cl_{current_user.id}_{run_id}.pdf")
    
    # 4. Create or update Application record
    application = db.query(Application).filter(Application.job_id == job_id, Application.user_id == current_user.id).first()
    if not application:
        application = Application(
            job_id=job_id,
            user_id=current_user.id,
            status="generated",
            resume_version_url=resume_pdf_path,
            cover_letter_url=cl_pdf_path,
            next_action="Review and Apply"
        )
        db.add(application)
    else:
        application.status = "generated"
        application.resume_version_url = resume_pdf_path
        application.cover_letter_url = cl_pdf_path
        application.next_action = "Review and Apply"
        
    db.commit()
    db.refresh(application)
    
    return {
        "application_id": application.id,
        "status": application.status,
        "resume_preview": resume_text,
        "cover_letter_preview": cl_text
    }

@router.post("/{application_id}/submit")
def submit_application_endpoint(application_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == application_id, Application.user_id == current_user.id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
        
    application.status = "applying"
    application.next_action = "Running automation..."
    db.commit()
    
    trigger_automation.delay(application.id)
    return {"message": "Automation triggered successfully."}

@router.post("/{application_id}/resume")
def resume_application_endpoint(application_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == application_id, Application.user_id == current_user.id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
        
    if application.status != "intervention_required":
        raise HTTPException(status_code=400, detail="Application is not paused for intervention.")
        
    application.status = "applying"
    application.next_action = "Resuming automation..."
    db.commit()
    
    resume_automation.delay(application.id)
    return {"message": "Automation resumed."}
