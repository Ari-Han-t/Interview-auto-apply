from fastapi import APIRouter, Depends, HTTPException, Body, Response
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.profile import Profile
from app.models.application import Application
from app.models.cover_letter import CoverLetter
from app.models.resume import ResumeVersion
from app.models.application_history import ApplicationHistory
from app.api.auth import get_current_user
from app.schemas.application import ApplicationResponse, GenerationResponse, ApplicationWithJobResponse
from app.services.ai.generator import generate_tailored_resume, generate_cover_letter
from app.services.ai.matcher import analyze_job_match
from app.services.pdf_exporter import export_text_to_pdf
from app.services.calendar_exporter import generate_ics_calendar
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
    apps = db.query(Application, Job).join(Job, Application.job_id == Job.id).filter(Application.user_id == current_user.id).order_by(Application.id.desc()).all()
    result = []
    for app, job in apps:
        result.append(ApplicationWithJobResponse(
            id=app.id,
            job_id=app.job_id,
            status=app.status or "Discovered",
            source=app.source or "Manual",
            applied_at=app.applied_at,
            submission_confirmed=bool(app.submission_confirmed),
            resume_version_id=app.resume_version_id,
            cover_letter_id=app.cover_letter_id,
            submitted_resume_snapshot=app.submitted_resume_snapshot,
            submitted_cover_letter_snapshot=app.submitted_cover_letter_snapshot,
            match_report=app.match_report,
            assessment_deadline=app.assessment_deadline,
            assessment_notes=app.assessment_notes,
            interview_date=app.interview_date,
            interview_round=app.interview_round,
            interview_notes=app.interview_notes,
            notes=app.notes,
            follow_ups=app.follow_ups or [],
            reminders=app.reminders or [],
            outcome=app.outcome,
            outcome_notes=app.outcome_notes,
            offer_compensation=app.offer_compensation,
            resume_version_url=app.resume_version_url,
            cover_letter_url=app.cover_letter_url,
            next_action=app.next_action,
            user_instructions=app.user_instructions,
            created_at=app.created_at,
            updated_at=app.updated_at,
            company=job.company,
            role=job.title,
            job_url=job.url,
            application_url=getattr(job, "application_url", None) or job.url,
            job_location=job.location,
            job_salary=getattr(job, "salary_range", None) or getattr(job, "salary", None),
            employment_type=getattr(job, "employment_type", None) or "Full-time"
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
        app.status = "generating"
        app.next_action = "Analyzing job requirements and tailoring resume..."
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
        "cover_letter_preview": cl_text,
        "resume_url": application.resume_version_url,
        "cover_letter": cl_text
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
        "Discovered", "Saved", "Shortlisted", "Preparing", "Ready to Apply", "Applied",
        "Assessment Received", "Interview Scheduled", "Interview Completed",
        "Offer Received", "Rejected", "Withdrawn", "Position Closed",
        "generating", "generated", "failed", "applying", "interview",
        "oa", "intervention_required"
    ]
    valid_lower = {s.lower(): s for s in valid_statuses}
    if not new_status or new_status.lower() not in valid_lower:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    normalized_status = valid_lower[new_status.lower()]
    application.status = normalized_status
    
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
    
    try:
        trigger_automation.delay(application.id)
    except Exception as celery_err:
        import threading
        target_fn = trigger_automation.run if hasattr(trigger_automation, "run") else trigger_automation
        threading.Thread(target=target_fn, args=(application.id,), daemon=True).start()
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
    
    try:
        resume_automation.delay(application.id)
    except Exception as celery_err:
        import threading
        target_fn = resume_automation.run if hasattr(resume_automation, "run") else resume_automation
        threading.Thread(target=target_fn, args=(application.id,), daemon=True).start()
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
        
    import os
    from app.services.pdf_exporter import compile_latex_to_pdf, export_text_to_pdf
    pdf_path = application.resume_version_url

    # If pdf_path exists on disk
    if pdf_path and os.path.exists(pdf_path):
        if pdf_path.endswith(".tex"):
            with open(pdf_path, "r", encoding="utf-8") as f:
                tex_content = f.read()
            compiled = compile_latex_to_pdf(tex_content, os.path.basename(pdf_path).replace(".tex", ".pdf"), os.path.dirname(pdf_path))
            application.resume_version_url = compiled
            db.commit()
            pdf_path = compiled
        return FileResponse(path=pdf_path, filename=os.path.basename(pdf_path), media_type="application/pdf")

    # If companion .tex exists on disk
    if pdf_path:
        tex_path = pdf_path.replace(".pdf", ".tex")
        if os.path.exists(tex_path):
            with open(tex_path, "r", encoding="utf-8") as f:
                tex_content = f.read()
            compiled = compile_latex_to_pdf(tex_content, os.path.basename(pdf_path), os.path.dirname(pdf_path))
            application.resume_version_url = compiled
            db.commit()
            return FileResponse(path=compiled, filename=os.path.basename(compiled), media_type="application/pdf")

    # Fallback to Profile latex_template or profile data
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    output_dir = f"data/applications/{current_user.id}"
    os.makedirs(output_dir, exist_ok=True)
    out_filename = f"application_{application_id}_resume.pdf"
    
    if profile and profile.latex_template:
        compiled = compile_latex_to_pdf(profile.latex_template, out_filename, output_dir)
        application.resume_version_url = compiled
        db.commit()
        return FileResponse(path=compiled, filename=out_filename, media_type="application/pdf")
        
    if profile:
        from app.services.ai.profile_builder import build_profile_text
        profile_text = build_profile_text(current_user.id, db)
        if profile_text:
            compiled = export_text_to_pdf(profile_text, out_filename, output_dir)
            application.resume_version_url = compiled
            db.commit()
            return FileResponse(path=compiled, filename=out_filename, media_type="application/pdf")

    raise HTTPException(status_code=404, detail="No resume generated for this application yet. Please click Analyse & Apply.")

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
        
    # Generate fallback basic LaTeX from profile text
    from app.services.ai.profile_builder import build_profile_text
    profile_text = build_profile_text(current_user.id, db) if profile else ""
    user_name = current_user.email.split("@")[0].replace(".", " ").title()
    fallback_tex = (
        "\\documentclass[letterpaper,10pt]{article}\n"
        "\\usepackage[utf8]{inputenc}\n"
        "\\usepackage[margin=0.75in]{geometry}\n"
        "\\begin{document}\n"
        f"\\textbf{{\\Large {user_name}}}\\\\\n"
        f"Email: {current_user.email}\\\\\n"
        "\\hrulefill\n\n"
        "\\section*{Profile & Experience}\n"
        f"{profile_text or 'Software Engineer profile'}\n"
        "\\end{document}\n"
    )
    import tempfile
    temp_dir = tempfile.gettempdir()
    temp_tex = os.path.join(temp_dir, f"resume_{application_id}.tex")
    with open(temp_tex, "w", encoding="utf-8") as f:
        f.write(fallback_tex)
    return FileResponse(path=temp_tex, filename=f"resume_{application_id}.tex", media_type="application/x-tex")


# ==============================================================================
# APPLICATION CRM & TRACKING WORKSPACE ENDPOINTS
# ==============================================================================

CANONICAL_CRM_STATUSES = [
    {"status": "Discovered", "label": "Discovered", "stage": "early", "color": "slate", "description": "Found opportunity, not yet reviewed."},
    {"status": "Saved", "label": "Saved", "stage": "early", "color": "blue", "description": "Saved to review or tailor later."},
    {"status": "Shortlisted", "label": "Shortlisted", "stage": "early", "color": "indigo", "description": "High-priority opportunity aligned with candidate profile."},
    {"status": "Preparing", "label": "Preparing", "stage": "active", "color": "amber", "description": "Customizing resume, cover letter, or studying company."},
    {"status": "Ready to Apply", "label": "Ready to Apply", "stage": "active", "color": "emerald", "description": "Tailored materials generated and approved, ready to submit."},
    {"status": "Applied", "label": "Applied", "stage": "submitted", "color": "teal", "description": "Confirmed candidate submission through official portal."},
    {"status": "Assessment Received", "label": "Assessment Received", "stage": "screening", "color": "orange", "description": "Online coding assessment or take-home assignment received."},
    {"status": "Interview Scheduled", "label": "Interview Scheduled", "stage": "interview", "color": "purple", "description": "Recruiter screen, technical, or system design interview scheduled."},
    {"status": "Interview Completed", "label": "Interview Completed", "stage": "interview", "color": "violet", "description": "Interview rounds finished, awaiting recruiter decision."},
    {"status": "Offer Received", "label": "Offer Received", "stage": "outcome", "color": "green", "description": "Formal offer or compensation proposal received."},
    {"status": "Rejected", "label": "Rejected", "stage": "outcome", "color": "rose", "description": "Application closed or rejected by company."},
    {"status": "Withdrawn", "label": "Withdrawn", "stage": "outcome", "color": "zinc", "description": "Candidate voluntarily withdrew application."},
    {"status": "Position Closed", "label": "Position Closed", "stage": "outcome", "color": "gray", "description": "Company halted hiring or role was filled."},
]

class UpdateCRMApplicationRequest(BaseModel):
    status: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    interview_date: Optional[datetime] = None
    interview_round: Optional[str] = None
    interview_notes: Optional[str] = None
    assessment_deadline: Optional[datetime] = None
    assessment_notes: Optional[str] = None
    outcome: Optional[str] = None
    outcome_notes: Optional[str] = None
    offer_compensation: Optional[str] = None
    follow_ups: Optional[List[Dict[str, Any]]] = None
    reminders: Optional[List[Dict[str, Any]]] = None
    applied_at: Optional[datetime] = None
    next_action: Optional[str] = None
    submission_confirmed: Optional[bool] = None

class ConfirmSubmissionRequest(BaseModel):
    submission_date: Optional[datetime] = None
    source: Optional[str] = "Company Portal"
    notes: Optional[str] = None

class AddReminderRequest(BaseModel):
    title: str
    remind_at: datetime
    reminder_type: str = "follow_up"
    notes: Optional[str] = None

class AddFollowUpRequest(BaseModel):
    id: Optional[str] = None
    title: str
    due_date: Optional[datetime] = None
    completed: bool = False
    notes: Optional[str] = None


def _to_app_with_job(app: Application, job: Job) -> ApplicationWithJobResponse:
    return ApplicationWithJobResponse(
        id=app.id,
        job_id=app.job_id,
        status=app.status or "Discovered",
        source=app.source or "Manual",
        applied_at=app.applied_at,
        submission_confirmed=bool(app.submission_confirmed),
        resume_version_id=app.resume_version_id,
        cover_letter_id=app.cover_letter_id,
        submitted_resume_snapshot=app.submitted_resume_snapshot,
        submitted_cover_letter_snapshot=app.submitted_cover_letter_snapshot,
        match_report=app.match_report,
        assessment_deadline=app.assessment_deadline,
        assessment_notes=app.assessment_notes,
        interview_date=app.interview_date,
        interview_round=app.interview_round,
        interview_notes=app.interview_notes,
        notes=app.notes,
        follow_ups=app.follow_ups or [],
        reminders=app.reminders or [],
        outcome=app.outcome,
        outcome_notes=app.outcome_notes,
        offer_compensation=app.offer_compensation,
        resume_version_url=app.resume_version_url,
        cover_letter_url=app.cover_letter_url,
        next_action=app.next_action,
        user_instructions=app.user_instructions,
        created_at=app.created_at,
        updated_at=app.updated_at,
        company=job.company if job else "Unknown",
        role=job.title if job else "Unknown",
        job_url=job.url if job else "",
        application_url=(getattr(job, "application_url", None) or job.url) if job else "",
        job_location=job.location if job else "",
        job_salary=(getattr(job, "salary_range", None) or getattr(job, "salary", None)) if job else "",
        employment_type=(getattr(job, "employment_type", None) or "Full-time") if job else "Full-time"
    )


@router.get("/crm/statuses")
def get_crm_statuses():
    """Returns canonical configurable application CRM statuses."""
    return {"statuses": CANONICAL_CRM_STATUSES}


@router.get("/calendar/export.ics")
def export_all_calendar_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Exports all user interview dates, assessment deadlines, and follow-ups as RFC 5545 iCalendar."""
    apps = db.query(Application, Job).join(Job, Application.job_id == Job.id).filter(
        Application.user_id == current_user.id
    ).all()

    events = []
    for app, job in apps:
        if app.interview_date:
            events.append({
                "uid": f"interview-{app.id}-{int(app.interview_date.timestamp())}",
                "summary": f"Interview: {job.title} at {job.company} ({app.interview_round or 'Round'})",
                "description": f"Role: {job.title}\nCompany: {job.company}\nRound: {app.interview_round or 'N/A'}\nNotes: {app.interview_notes or 'None'}\nJob Link: {job.url or ''}",
                "start_date": app.interview_date,
                "duration_hours": 1,
                "location": "Remote / Video Conference",
            })
        if app.assessment_deadline:
            events.append({
                "uid": f"assessment-{app.id}-{int(app.assessment_deadline.timestamp())}",
                "summary": f"Assessment Due: {job.title} at {job.company}",
                "description": f"Take-home / coding assessment deadline.\nRole: {job.title}\nNotes: {app.assessment_notes or 'None'}",
                "start_date": app.assessment_deadline,
                "duration_hours": 1,
                "location": "Online Portal",
            })
        if app.follow_ups:
            for idx, fu in enumerate(app.follow_ups):
                due_val = fu.get("due_date")
                if due_val and not fu.get("completed"):
                    try:
                        if isinstance(due_val, str):
                            due_dt = datetime.fromisoformat(due_val.replace("Z", "+00:00"))
                        else:
                            due_dt = due_val
                        events.append({
                            "uid": f"followup-{app.id}-{idx}",
                            "summary": f"Follow-up: {fu.get('title', 'Check status')} ({job.company})",
                            "description": f"Follow-up action for {job.title} at {job.company}.\nNotes: {fu.get('notes', '')}",
                            "start_date": due_dt,
                            "duration_hours": 1,
                            "location": "Email / LinkedIn",
                        })
                    except Exception:
                        pass
        if app.reminders:
            for idx, rem in enumerate(app.reminders):
                rem_val = rem.get("remind_at")
                if rem_val:
                    try:
                        if isinstance(rem_val, str):
                            rem_dt = datetime.fromisoformat(rem_val.replace("Z", "+00:00"))
                        else:
                            rem_dt = rem_val
                        events.append({
                            "uid": f"reminder-{app.id}-{idx}",
                            "summary": f"Reminder: {rem.get('title')}",
                            "description": f"Reminder for {job.title} at {job.company} ({rem.get('reminder_type', 'General')}).\nNotes: {rem.get('notes', '')}",
                            "start_date": rem_dt,
                            "duration_hours": 1,
                            "location": "Calendar Reminder",
                        })
                    except Exception:
                        pass

    ics_content = generate_ics_calendar(events, cal_name=f"{current_user.email} Applications Calendar")
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=all_applications_calendar.ics"}
    )


@router.get("/{application_id}", response_model=ApplicationWithJobResponse)
def get_application_by_id(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves single application with associated job details."""
    app = db.query(Application).filter(
        Application.id == application_id, Application.user_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    job = db.query(Job).filter(Job.id == app.job_id).first()
    return _to_app_with_job(app, job)


@router.put("/{application_id}/crm", response_model=ApplicationWithJobResponse)
def update_application_crm(
    application_id: int,
    request: UpdateCRMApplicationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates CRM status, notes, dates, follow-ups, and outcomes for an application."""
    app = db.query(Application).filter(
        Application.id == application_id, Application.user_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    job = db.query(Job).filter(Job.id == app.job_id).first()

    old_status = app.status
    if request.status is not None:
        app.status = request.status
        if old_status != request.status:
            history = ApplicationHistory(
                application_id=app.id,
                status=request.status,
                notes=f"Status transitioned from '{old_status}' to '{request.status}' via CRM workspace."
            )
            db.add(history)

    if request.source is not None:
        app.source = request.source
    if request.notes is not None:
        app.notes = request.notes
    if request.interview_date is not None:
        app.interview_date = request.interview_date
    if request.interview_round is not None:
        app.interview_round = request.interview_round
    if request.interview_notes is not None:
        app.interview_notes = request.interview_notes
    if request.assessment_deadline is not None:
        app.assessment_deadline = request.assessment_deadline
    if request.assessment_notes is not None:
        app.assessment_notes = request.assessment_notes
    if request.outcome is not None:
        app.outcome = request.outcome
    if request.outcome_notes is not None:
        app.outcome_notes = request.outcome_notes
    if request.offer_compensation is not None:
        app.offer_compensation = request.offer_compensation
    if request.follow_ups is not None:
        app.follow_ups = request.follow_ups
    if request.reminders is not None:
        app.reminders = request.reminders
    if request.applied_at is not None:
        app.applied_at = request.applied_at
    if request.next_action is not None:
        app.next_action = request.next_action
    if request.submission_confirmed is not None:
        app.submission_confirmed = request.submission_confirmed

    app.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(app)
    return _to_app_with_job(app, job)


@router.post("/{application_id}/confirm-submission", response_model=ApplicationWithJobResponse)
def confirm_application_submission(
    application_id: int,
    request: ConfirmSubmissionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Explicit user confirmation that the application was submitted.
    Freezes and permanently snapshots the submitted resume and cover letter content.
    Future edits to the candidate profile or master resume will never alter these frozen snapshots.
    """
    app = db.query(Application).filter(
        Application.id == application_id, Application.user_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    job = db.query(Job).filter(Job.id == app.job_id).first()

    # 1. Snapshot Resume Content
    resume_snapshot = None
    if app.resume_version_id:
        rv = db.query(ResumeVersion).filter(ResumeVersion.id == app.resume_version_id).first()
        if rv and rv.latex_source:
            resume_snapshot = rv.latex_source
    if not resume_snapshot:
        rv_job = db.query(ResumeVersion).filter(
            ResumeVersion.job_id == app.job_id, ResumeVersion.user_id == current_user.id
        ).order_by(ResumeVersion.id.desc()).first()
        if rv_job and rv_job.latex_source:
            resume_snapshot = rv_job.latex_source
            app.resume_version_id = rv_job.id
    if not resume_snapshot:
        rv_master = db.query(ResumeVersion).filter(
            ResumeVersion.user_id == current_user.id, ResumeVersion.is_master == True
        ).first()
        if rv_master and rv_master.latex_source:
            resume_snapshot = rv_master.latex_source
            app.resume_version_id = rv_master.id
    if not resume_snapshot:
        prof = db.query(Profile).filter(Profile.user_id == current_user.id).first()
        if prof and prof.latex_template:
            resume_snapshot = prof.latex_template

    # 2. Snapshot Cover Letter Content
    cover_letter_snapshot = None
    if app.cover_letter_id:
        cl = db.query(CoverLetter).filter(CoverLetter.id == app.cover_letter_id).first()
        if cl and cl.content:
            cover_letter_snapshot = cl.content
    if not cover_letter_snapshot:
        cl_job = db.query(CoverLetter).filter(
            CoverLetter.job_id == app.job_id, CoverLetter.user_id == current_user.id
        ).order_by(CoverLetter.is_approved.desc(), CoverLetter.id.desc()).first()
        if cl_job and cl_job.content:
            cover_letter_snapshot = cl_job.content
            app.cover_letter_id = cl_job.id

    # 3. Freeze into application record
    submission_time = request.submission_date or datetime.utcnow()
    app.submission_confirmed = True
    app.status = "Applied"
    app.applied_at = submission_time
    app.source = request.source or app.source or "Company Portal"
    if resume_snapshot:
        app.submitted_resume_snapshot = resume_snapshot
    if cover_letter_snapshot:
        app.submitted_cover_letter_snapshot = cover_letter_snapshot

    if request.notes:
        app.notes = (app.notes + "\n" if app.notes else "") + f"[Confirmed Submission]: {request.notes}"

    app.next_action = "Application submitted. Monitoring responses and upcoming assessment/recruiter screens."
    app.updated_at = datetime.utcnow()

    # 4. Auto-schedule 7-day follow-up reminder if none present
    existing_followups = list(app.follow_ups or [])
    if not existing_followups:
        followup_due = submission_time + timedelta(days=7)
        existing_followups.append({
            "id": str(uuid.uuid4()),
            "title": "Recruiter follow-up if no response received",
            "due_date": followup_due.isoformat(),
            "completed": False,
            "notes": "Send polite status check email or connect with recruiter on LinkedIn."
        })
        app.follow_ups = existing_followups

    # 5. Timeline history entry
    history = ApplicationHistory(
        application_id=app.id,
        status="Applied",
        notes=f"Explicit submission confirmed by candidate via {app.source}. Submitted resume and cover letter versions snapshot-frozen permanently."
    )
    db.add(history)

    # 6. Notification
    create_notification(
        current_user.id,
        "application_submitted",
        f"You successfully submitted your application for {job.title} at {job.company}. Submitted documents have been snapshot-frozen."
    )

    db.commit()
    db.refresh(app)
    return _to_app_with_job(app, job)


@router.get("/{application_id}/submitted-materials")
def get_submitted_materials(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves the permanently frozen snapshots of submitted materials.
    Also returns the active master resume to verify that master changes do not alter frozen snapshots.
    """
    app = db.query(Application).filter(
        Application.id == application_id, Application.user_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == app.job_id).first()

    master_rv = db.query(ResumeVersion).filter(
        ResumeVersion.user_id == current_user.id, ResumeVersion.is_master == True
    ).first()
    master_latex = master_rv.latex_source if master_rv else None

    return {
        "application_id": app.id,
        "company": job.company if job else "Unknown",
        "role": job.title if job else "Unknown",
        "submission_confirmed": bool(app.submission_confirmed),
        "applied_at": app.applied_at,
        "source": app.source,
        "submitted_resume_snapshot": app.submitted_resume_snapshot,
        "submitted_cover_letter_snapshot": app.submitted_cover_letter_snapshot,
        "resume_version_id": app.resume_version_id,
        "cover_letter_id": app.cover_letter_id,
        "current_master_resume_preview": master_latex[:300] if master_latex else None,
        "is_snapshot_immutable": True,
        "has_frozen_resume": bool(app.submitted_resume_snapshot),
        "has_frozen_cover_letter": bool(app.submitted_cover_letter_snapshot),
    }


@router.post("/{application_id}/reminders", response_model=ApplicationWithJobResponse)
def add_application_reminder(
    application_id: int,
    request: AddReminderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adds a scheduled reminder for interview, assessment deadline, or follow-up."""
    app = db.query(Application).filter(
        Application.id == application_id, Application.user_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == app.job_id).first()

    reminders = list(app.reminders or [])
    reminders.append({
        "id": str(uuid.uuid4()),
        "title": request.title,
        "remind_at": request.remind_at.isoformat(),
        "reminder_type": request.reminder_type,
        "notes": request.notes,
        "created_at": datetime.utcnow().isoformat(),
    })
    app.reminders = reminders
    app.updated_at = datetime.utcnow()

    create_notification(
        current_user.id,
        f"reminder_{request.reminder_type}",
        f"{request.title} for {job.company} ({request.reminder_type}) scheduled for {request.remind_at.strftime('%b %d, %Y %H:%M')}"
    )

    db.commit()
    db.refresh(app)
    return _to_app_with_job(app, job)


@router.post("/{application_id}/follow-ups", response_model=ApplicationWithJobResponse)
def manage_application_follow_up(
    application_id: int,
    request: AddFollowUpRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Adds or updates a follow-up checklist item for an application."""
    app = db.query(Application).filter(
        Application.id == application_id, Application.user_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == app.job_id).first()

    follow_ups = list(app.follow_ups or [])
    found = False
    if request.id:
        for idx, item in enumerate(follow_ups):
            if item.get("id") == request.id:
                follow_ups[idx]["title"] = request.title
                follow_ups[idx]["due_date"] = request.due_date.isoformat() if request.due_date else None
                follow_ups[idx]["completed"] = request.completed
                follow_ups[idx]["notes"] = request.notes
                found = True
                break
    
    if not found:
        follow_ups.append({
            "id": request.id or str(uuid.uuid4()),
            "title": request.title,
            "due_date": request.due_date.isoformat() if request.due_date else None,
            "completed": request.completed,
            "notes": request.notes,
        })

    app.follow_ups = follow_ups
    app.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(app)
    return _to_app_with_job(app, job)


@router.delete("/{application_id}/reminders/{reminder_id}", response_model=ApplicationWithJobResponse)
def delete_application_reminder(
    application_id: int,
    reminder_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes or cancels a scheduled reminder."""
    app = db.query(Application).filter(
        Application.id == application_id, Application.user_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == app.job_id).first()
    reminders = [r for r in (app.reminders or []) if str(r.get("id")) != str(reminder_id)]
    app.reminders = reminders
    app.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(app)
    return _to_app_with_job(app, job)


@router.delete("/{application_id}/follow-ups/{followup_id}", response_model=ApplicationWithJobResponse)
def delete_application_follow_up(
    application_id: int,
    followup_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a follow-up checklist item."""
    app = db.query(Application).filter(
        Application.id == application_id, Application.user_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == app.job_id).first()
    follow_ups = [f for f in (app.follow_ups or []) if str(f.get("id")) != str(followup_id)]
    app.follow_ups = follow_ups
    app.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(app)
    return _to_app_with_job(app, job)


@router.get("/{application_id}/calendar.ics")
def export_single_application_calendar(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Exports this single application's interview dates, deadlines, and follow-ups as RFC 5545 iCalendar."""
    app = db.query(Application).filter(
        Application.id == application_id, Application.user_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == app.job_id).first()

    events = []
    if app.interview_date:
        events.append({
            "uid": f"interview-{app.id}",
            "summary": f"Interview: {job.title} at {job.company} ({app.interview_round or 'Round'})",
            "description": f"Role: {job.title}\nCompany: {job.company}\nRound: {app.interview_round or 'Interview'}\nNotes: {app.interview_notes or ''}\nJob: {job.url or ''}",
            "start_date": app.interview_date,
            "duration_hours": 1,
            "location": "Video Call / Interview",
        })
    if app.assessment_deadline:
        events.append({
            "uid": f"assessment-{app.id}",
            "summary": f"Assessment Due: {job.title} at {job.company}",
            "description": f"Assessment deadline for {job.company}.\nNotes: {app.assessment_notes or ''}",
            "start_date": app.assessment_deadline,
            "duration_hours": 1,
            "location": "Online Portal",
        })
    if app.follow_ups:
        for idx, fu in enumerate(app.follow_ups):
            due_val = fu.get("due_date")
            if due_val and not fu.get("completed"):
                try:
                    if isinstance(due_val, str):
                        due_dt = datetime.fromisoformat(due_val.replace("Z", "+00:00"))
                    else:
                        due_dt = due_val
                    events.append({
                        "uid": f"followup-{app.id}-{idx}",
                        "summary": f"Follow-up: {fu.get('title')} ({job.company})",
                        "description": f"Check status or reply for {job.title} at {job.company}.\nNotes: {fu.get('notes', '')}",
                        "start_date": due_dt,
                        "duration_hours": 1,
                        "location": "Email",
                    })
                except Exception:
                    pass
    if app.reminders:
        for idx, rem in enumerate(app.reminders):
            rem_val = rem.get("remind_at")
            if rem_val:
                try:
                    if isinstance(rem_val, str):
                        rem_dt = datetime.fromisoformat(rem_val.replace("Z", "+00:00"))
                    else:
                        rem_dt = rem_val
                    events.append({
                        "uid": f"reminder-{app.id}-{idx}",
                        "summary": f"Reminder: {rem.get('title')}",
                        "description": f"Reminder for {job.title} at {job.company} ({rem.get('reminder_type', 'General')}).\nNotes: {rem.get('notes', '')}",
                        "start_date": rem_dt,
                        "duration_hours": 1,
                        "location": "Calendar Reminder",
                    })
                except Exception:
                    pass

    ics_content = generate_ics_calendar(events, cal_name=f"{job.company} - {job.title} Application Calendar")
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": f"attachment; filename=application_{application_id}.ics"}
    )


