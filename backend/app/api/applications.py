from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Optional
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.profile import Profile
from app.models.application import Application
from app.models.cover_letter import CoverLetter
from app.models.application_history import ApplicationHistory
from app.api.auth import get_current_user
from app.schemas.application import ApplicationResponse, GenerationResponse, ApplicationWithJobResponse
from app.services.ai.generator import generate_tailored_resume, generate_cover_letter
from app.services.ai.matcher import analyze_job_match
from app.services.pdf_exporter import export_text_to_pdf
from app.services.notification import create_notification
from app.workers.application_tasks import trigger_automation, resume_automation
from typing import List, Optional
from pydantic import BaseModel
import uuid

router = APIRouter()

class InitializeApplicationRequest(BaseModel):
    user_instructions: Optional[str] = None
    github_username: Optional[str] = None

@router.get("/", response_model=List[ApplicationWithJobResponse])
def get_applications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    apps = db.query(Application, Job).join(Job, Application.job_id == Job.id).filter(Application.user_id == current_user.id).all()
    result = []
    for app, job in apps:
        result.append(ApplicationWithJobResponse(
            id=app.id,
            job_id=app.job_id,
            status=app.status,
            applied_at=app.applied_at,
            resume_version_url=app.resume_version_url,
            cover_letter_url=app.cover_letter_url,
            next_action=app.next_action,
            company=job.company,
            role=job.title,
            job_url=job.url
        ))
    return result

from app.services.ai.pipeline import start_background_analysis_thread

@router.get("/job/{job_id}", response_model=ApplicationResponse)
def get_application_for_job(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.job_id == job_id, Application.user_id == current_user.id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found for this job")
    return app

@router.post("/initialize/{job_id}")
def initialize_application(
    job_id: int,
    request: Optional[InitializeApplicationRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    import os
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    user_instructions = (request.user_instructions or "").strip() if request else ""
    github_username = (request.github_username or "").strip() if request else ""

    # Persist per-job instructions + optional GitHub username override
    if github_username:
        profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
        if not profile:
            profile = Profile(user_id=current_user.id)
            db.add(profile)
        profile.github_username = github_username

    # Check if application already exists
    app = db.query(Application).filter(Application.job_id == job_id, Application.user_id == current_user.id).first()
    if not app:
        app = Application(
            job_id=job_id,
            user_id=current_user.id,
            status="generating",
            next_action="Initializing background analysis...",
            user_instructions=user_instructions or None,
        )
        db.add(app)
        db.commit()
        db.refresh(app)
        
        # Save history timeline
        history_entry = ApplicationHistory(
            application_id=app.id,
            status="generating",
            notes="Application analysis and tailoring initialized."
        )
        db.add(history_entry)
        db.commit()
    else:
        # Update instructions on re-run (including clearing if empty string sent)
        if request is not None:
            app.user_instructions = user_instructions or None
        # Reset status if it's not already complete
        if app.status not in ["generated", "applied", "interview", "offer", "rejected"]:
            app.status = "generating"
        db.commit()

    # Reset/Initialize progress
    app.analysis_progress = {
        "parsing_job": "pending",
        "matching_resume": "pending",
        "tailoring_resume": "pending",
        "cover_letter": "pending",
        "company_research": "pending",
        "interview_prep": "pending"
    }
    app.analysis_results = {}
    db.commit()

    # Trigger background thread pool analyses
    start_background_analysis_thread(app.id, current_user.id, job_id)

    return {
        "application_id": app.id,
        "status": app.status
    }

@router.get("/{application_id}/progress")
def get_application_progress(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    app = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    return {
        "application_id": app.id,
        "status": app.status,
        "progress": app.analysis_progress or {},
        "results": app.analysis_results or {},
        "resume_version_url": app.resume_version_url,
        "cover_letter_url": app.cover_letter_url,
        "user_instructions": app.user_instructions or "",
    }

@router.post("/generate/{job_id}", response_model=GenerationResponse)
def generate_application_materials(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    import os
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # CACHING LAYER: check if already generated
    application = db.query(Application).filter(Application.job_id == job_id, Application.user_id == current_user.id).first()
    cl_record = db.query(CoverLetter).filter(CoverLetter.job_id == job_id, CoverLetter.user_id == current_user.id).first()
    if application and application.status == "generated" and cl_record:
        resume_text = ""
        if application.resume_version_url and os.path.exists(application.resume_version_url):
            try:
                with open(application.resume_version_url, "r", encoding="utf-8") as f:
                    resume_text = f.read()
            except Exception:
                resume_text = "LaTeX Resume tailored."
        return {
            "application_id": application.id,
            "status": application.status,
            "resume_preview": resume_text,
            "cover_letter_preview": cl_record.content
        }
        
    from app.services.ai.eligibility import evaluate_eligibility
    res = evaluate_eligibility(current_user.id, job.id, db)
    if not res["eligible"]:
        raise HTTPException(status_code=400, detail=f"Cannot generate materials for ineligible job. Reason: {res['reason']}")
        
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    
    from app.services.ai.profile_builder import build_profile_text
    profile_text = build_profile_text(current_user.id, db)
    if not profile_text:
        raise HTTPException(status_code=400, detail="Profile details not found. Please upload a resume or fill in your details in Settings.")

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
    latex_resume = profile.latex_template if (profile and profile.latex_template) else ""

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

    # Quick re-analysis to get strengths for Cover Letter
    analysis = analyze_job_match(
        profile_text=profile_text, 
        job_description=job.description or job.title,
        projects_meta=projects_meta,
        latex_resume=latex_resume,
        job_metadata=job_meta
    )
    
    user_prefix = current_user.email.split('@')[0]
    safe_company = "".join(c for c in (job.company or "company") if c.isalnum() or c in (' ', '_')).replace(' ', '_')
    
    # 2. Generate Content
    from app.models.profile import Profile as ProfileRow
    profile_row = db.query(ProfileRow).filter(ProfileRow.user_id == current_user.id).first()
    global_instructions = (profile_row.tailoring_instructions if profile_row else None) or None
    raw_resume_text = (profile_row.raw_resume_text if profile_row else None) or None
    job_instructions = (application.user_instructions if application else None) or None
    if job_instructions and global_instructions and job_instructions != global_instructions:
        combined_instructions = (
            f"[GLOBAL]\n{global_instructions}\n\n[THIS JOB — higher priority]\n{job_instructions}"
        )
    else:
        combined_instructions = (job_instructions or global_instructions) or None
    if profile and profile.latex_template:
        resume_text = generate_tailored_resume(
            profile.latex_template, 
            job.description or job.title, 
            job.title, 
            is_latex=True,
            extracted_projects=profile.projects_json,
            user_instructions=combined_instructions,
            raw_resume_text=raw_resume_text,
        )
        import os
        from app.services.pdf_exporter import compile_latex_to_pdf
        output_dir = f"data/applications/{current_user.id}"
        os.makedirs(output_dir, exist_ok=True)
        tex_path = os.path.join(output_dir, f"{user_prefix}_{safe_company}_resume.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(resume_text)
            
        try:
            resume_pdf_path = compile_latex_to_pdf(resume_text, f"{user_prefix}_{safe_company}_resume.pdf", output_dir)
        except Exception as e:
            # Fallback to tex path if compilation fails
            resume_pdf_path = tex_path
            print(f"Failed to compile PDF: {e}")
    else:
        resume_text = generate_tailored_resume(
            profile_text, 
            job.description or job.title, 
            job.title,
            extracted_projects=None,
            user_instructions=combined_instructions,
            raw_resume_text=raw_resume_text,
        )
        resume_pdf_path = export_text_to_pdf(resume_text, f"{user_prefix}_{safe_company}_resume.pdf")
        
    cl_text = generate_cover_letter(profile_text, job.company, job.title, analysis["strengths"], user_instructions=combined_instructions)
    
    # 3. Save Cover Letter to CoverLetter table
    cl_record = db.query(CoverLetter).filter(CoverLetter.job_id == job_id, CoverLetter.user_id == current_user.id).first()
    if not cl_record:
        cl_record = CoverLetter(
            user_id=current_user.id,
            job_id=job_id,
            content=cl_text,
            format="md"
        )
        db.add(cl_record)
    else:
        cl_record.content = cl_text
    db.flush()

    # 4. Export CL to PDF
    cl_pdf_path = export_text_to_pdf(cl_text, f"cl_{current_user.id}_{cl_record.id}.pdf")
    
    # 5. Create or update Application record
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
    
    # Save history timeline
    history_entry = ApplicationHistory(
        application_id=application.id,
        status="generated",
        notes="Application materials generated successfully."
    )
    db.add(history_entry)
    db.commit()
    
    create_notification(current_user.id, "resume_generated", f"Tailored resume and cover letter generated for {job.title} at {job.company}.")
    
    return {
        "application_id": application.id,
        "status": application.status,
        "resume_preview": resume_text,
        "cover_letter_preview": cl_text
    }

@router.post("/{application_id}/status")
def update_application_status(
    application_id: int,
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(
        Application.id == application_id, Application.user_id == current_user.id
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    new_status = body.get("status")
    notes = body.get("notes") or f"Status changed manually to {new_status}"
    valid_statuses = [
        "generating", "generated", "applying", "applied", "interview",
        "oa", "rejected", "offer", "intervention_required"
    ]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    application.status = new_status
    
    # Save history timeline
    history_entry = ApplicationHistory(
        application_id=application.id,
        status=new_status,
        notes=notes
    )
    db.add(history_entry)
    db.commit()
    return {"message": f"Status updated to {new_status}"}

@router.get("/{application_id}/history")
def get_application_history(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns the status timeline history for a specific application.
    """
    application = db.query(Application).filter(
        Application.id == application_id, Application.user_id == current_user.id
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
        
    history = db.query(ApplicationHistory).filter(
        ApplicationHistory.application_id == application_id
    ).order_by(ApplicationHistory.created_at.asc()).all()
    
    return [
        {
            "id": h.id,
            "status": h.status,
            "notes": h.notes,
            "created_at": h.created_at
        } for h in history
    ]

@router.post("/{application_id}/submit")
def submit_application_endpoint(application_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == application_id, Application.user_id == current_user.id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
        
    application.status = "applying"
    application.next_action = "Running automation..."
    
    # Save history timeline
    history_entry = ApplicationHistory(
        application_id=application.id,
        status="applying",
        notes="Submission automation triggered."
    )
    db.add(history_entry)
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
    
    # Save history timeline
    history_entry = ApplicationHistory(
        application_id=application.id,
        status="applying",
        notes="Resuming automation after user solved CAPTCHA."
    )
    db.add(history_entry)
    db.commit()
    
    resume_automation.delay(application.id)
    return {"message": "Automation resumed."}

from fastapi.responses import FileResponse

@router.get("/{application_id}/resume.pdf")
def get_application_resume_pdf(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(
        Application.id == application_id, Application.user_id == current_user.id
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
        
    if not application.resume_version_url:
        raise HTTPException(status_code=404, detail="No resume generated for this application")
        
    import os
    pdf_path = application.resume_version_url
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
        
    # If the file saved is a .tex file, compile/convert it to PDF on the fly for preview
    if pdf_path.endswith(".tex"):
        from app.services.pdf_exporter import compile_latex_to_pdf
        with open(pdf_path, "r", encoding="utf-8") as f:
            tex_content = f.read()
        pdf_path = compile_latex_to_pdf(tex_content, os.path.basename(pdf_path).replace(".tex", ".pdf"), os.path.dirname(pdf_path))
        application.resume_version_url = pdf_path
        db.commit()
        
    return FileResponse(path=pdf_path, filename=os.path.basename(pdf_path), media_type="application/pdf")

@router.get("/{application_id}/resume.tex")
def get_application_resume_tex(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    application = db.query(Application).filter(
        Application.id == application_id, Application.user_id == current_user.id
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
        
    import os
    # Check if a .tex file exists in the directory
    if application.resume_version_url:
        tex_path = application.resume_version_url.replace(".pdf", ".tex")
        if os.path.exists(tex_path):
            return FileResponse(path=tex_path, filename=os.path.basename(tex_path), media_type="application/x-tex")
            
    # Fallback to Profile latex_template
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if profile and profile.latex_template:
        import tempfile
        temp_dir = tempfile.gettempdir()
        temp_tex = os.path.join(temp_dir, f"resume_{application_id}.tex")
        with open(temp_tex, "w", encoding="utf-8") as f:
            f.write(profile.latex_template)
        return FileResponse(path=temp_tex, filename=f"resume_{application_id}.tex", media_type="application/x-tex")
        
    raise HTTPException(status_code=404, detail="LaTeX resume source not found")

