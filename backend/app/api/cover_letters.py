import os
import tempfile
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.cover_letter import CoverLetter
from app.models.job import Job
from app.models.application import Application
from app.api.auth import get_current_user
from app.services.pdf_exporter import export_text_to_pdf
from app.services.cover_letter.service import (
    generate_personalized_cover_letter,
    save_cover_letter_version,
    approve_cover_letter,
    compare_cover_letter_versions,
    STYLE_DESCRIPTIONS,
)

router = APIRouter()

class GenerateCoverLetterRequest(BaseModel):
    style: str = "concise"
    candidate_motivation: Optional[str] = None
    selected_project_ids: Optional[List[int]] = None
    selected_experience_ids: Optional[List[int]] = None
    selected_achievement_ids: Optional[List[int]] = None
    application_id: Optional[int] = None

class SaveVersionRequest(BaseModel):
    content: str
    style: Optional[str] = "concise"
    candidate_motivation: Optional[str] = None
    selected_projects: Optional[List[int]] = None
    selected_experiences: Optional[List[int]] = None
    selected_achievements: Optional[List[int]] = None
    is_approved: Optional[bool] = False
    application_id: Optional[int] = None

@router.get("/styles")
def get_supported_styles():
    """Returns available cover letter writing styles and descriptions."""
    return [
        {"id": k, "name": k.replace("_", " ").title(), "description": v}
        for k, v in STYLE_DESCRIPTIONS.items()
    ]

@router.get("/")
def get_cover_letters(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns list of all cover letters generated for the user."""
    cls = (
        db.query(CoverLetter, Job)
        .join(Job, CoverLetter.job_id == Job.id)
        .filter(CoverLetter.user_id == current_user.id)
        .order_by(CoverLetter.created_at.desc())
        .all()
    )
    result = []
    for cl, job in cls:
        result.append({
            "id": cl.id,
            "job_id": cl.job_id,
            "application_id": cl.application_id,
            "company": job.company,
            "role": job.title,
            "content": cl.content,
            "format": cl.format,
            "style": cl.style or "concise",
            "version_number": cl.version_number or 1,
            "is_approved": bool(cl.is_approved),
            "approved_at": cl.approved_at,
            "candidate_motivation": cl.candidate_motivation,
            "parent_version_id": cl.parent_version_id,
            "created_at": cl.created_at,
            "updated_at": cl.updated_at,
        })
    return result

@router.get("/job/{job_id}")
def get_job_cover_letter(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns the latest active cover letter for a specific job."""
    cl = (
        db.query(CoverLetter)
        .filter(CoverLetter.job_id == job_id, CoverLetter.user_id == current_user.id)
        .order_by(CoverLetter.version_number.desc(), CoverLetter.id.desc())
        .first()
    )
    if not cl:
        return None

    job = db.query(Job).filter(Job.id == job_id).first()
    return {
        "id": cl.id,
        "job_id": cl.job_id,
        "application_id": cl.application_id,
        "company": job.company if job else "Unknown",
        "role": job.title if job else "Unknown",
        "content": cl.content,
        "format": cl.format,
        "style": cl.style or "concise",
        "version_number": cl.version_number or 1,
        "is_approved": bool(cl.is_approved),
        "approved_at": cl.approved_at,
        "candidate_motivation": cl.candidate_motivation,
        "selected_projects": cl.selected_projects or [],
        "selected_experiences": cl.selected_experiences or [],
        "selected_achievements": cl.selected_achievements or [],
        "parent_version_id": cl.parent_version_id,
        "sources_used": cl.sources_used or [],
        "created_at": cl.created_at,
        "updated_at": cl.updated_at,
    }

@router.get("/job/{job_id}/versions")
def get_job_cover_letter_versions(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns full version history of cover letters for a specific job."""
    versions = (
        db.query(CoverLetter)
        .filter(CoverLetter.job_id == job_id, CoverLetter.user_id == current_user.id)
        .order_by(CoverLetter.version_number.desc(), CoverLetter.id.desc())
        .all()
    )
    job = db.query(Job).filter(Job.id == job_id).first()
    return [
        {
            "id": v.id,
            "job_id": v.job_id,
            "application_id": v.application_id,
            "company": job.company if job else "Unknown",
            "role": job.title if job else "Unknown",
            "style": v.style or "concise",
            "version_number": v.version_number or 1,
            "is_approved": bool(v.is_approved),
            "approved_at": v.approved_at,
            "candidate_motivation": v.candidate_motivation,
            "char_count": len(v.content),
            "parent_version_id": v.parent_version_id,
            "created_at": v.created_at,
        }
        for v in versions
    ]

@router.post("/generate/{job_id}")
@router.post("/job/{job_id}/generate")
def generate_cover_letter_for_job(
    job_id: int,
    req: GenerateCoverLetterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generates or regenerates a personalized, tailored cover letter for a job."""
    try:
        gen_result = generate_personalized_cover_letter(
            user_id=current_user.id,
            job_id=job_id,
            style=req.style,
            candidate_motivation=req.candidate_motivation,
            selected_project_ids=req.selected_project_ids,
            selected_experience_ids=req.selected_experience_ids,
            selected_achievement_ids=req.selected_achievement_ids,
            application_id=req.application_id,
            db=db,
        )

        # Save as a draft version in database
        saved_cl = save_cover_letter_version(
            user_id=current_user.id,
            job_id=job_id,
            content=gen_result["content"],
            style=gen_result["style"],
            candidate_motivation=gen_result["candidate_motivation"],
            selected_projects=gen_result["selected_projects"],
            selected_experiences=gen_result["selected_experiences"],
            selected_achievements=gen_result["selected_achievements"],
            application_id=req.application_id,
            is_approved=False,
            sources_used=gen_result["sources_used"],
            db=db,
        )

        job = db.query(Job).filter(Job.id == job_id).first()

        return {
            "id": saved_cl.id,
            "job_id": saved_cl.job_id,
            "application_id": saved_cl.application_id,
            "company": job.company if job else "Unknown",
            "role": job.title if job else "Unknown",
            "content": saved_cl.content,
            "style": saved_cl.style,
            "version_number": saved_cl.version_number,
            "is_approved": saved_cl.is_approved,
            "candidate_motivation": saved_cl.candidate_motivation,
            "selected_projects": saved_cl.selected_projects,
            "selected_experiences": saved_cl.selected_experiences,
            "selected_achievements": saved_cl.selected_achievements,
            "warnings": gen_result.get("warnings", []),
            "sources_used": gen_result.get("sources_used", []),
            "used_fallback": gen_result.get("used_fallback", False),
            "created_at": saved_cl.created_at,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate cover letter: {str(e)}")

@router.post("/{cl_id}/save-version")
def save_version(
    cl_id: int,
    req: SaveVersionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Saves edited content as a new immutable version in the version history."""
    parent = db.query(CoverLetter).filter(CoverLetter.id == cl_id, CoverLetter.user_id == current_user.id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Parent cover letter not found")

    new_version = save_cover_letter_version(
        user_id=current_user.id,
        job_id=parent.job_id,
        content=req.content,
        style=req.style or parent.style or "concise",
        candidate_motivation=req.candidate_motivation or parent.candidate_motivation,
        selected_projects=req.selected_projects or parent.selected_projects,
        selected_experiences=req.selected_experiences or parent.selected_experiences,
        selected_achievements=req.selected_achievements or parent.selected_achievements,
        parent_version_id=parent.id,
        application_id=req.application_id or parent.application_id,
        is_approved=bool(req.is_approved),
        sources_used=parent.sources_used,
        db=db,
    )

    return {
        "message": "New version saved successfully",
        "id": new_version.id,
        "version_number": new_version.version_number,
        "is_approved": new_version.is_approved,
        "created_at": new_version.created_at,
    }

@router.post("/version/{job_id}")
def save_version_for_job(
    job_id: int,
    req: SaveVersionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Saves a cover letter version directly for a job."""
    parent = (
        db.query(CoverLetter)
        .filter(CoverLetter.job_id == job_id, CoverLetter.user_id == current_user.id)
        .order_by(CoverLetter.version_number.desc())
        .first()
    )
    parent_id = parent.id if parent else None
    new_version = save_cover_letter_version(
        user_id=current_user.id,
        job_id=job_id,
        content=req.content,
        style=req.style or (parent.style if parent else "concise"),
        candidate_motivation=req.candidate_motivation or (parent.candidate_motivation if parent else None),
        selected_projects=req.selected_projects or (parent.selected_projects if parent else None),
        selected_experiences=req.selected_experiences or (parent.selected_experiences if parent else None),
        selected_achievements=req.selected_achievements or (parent.selected_achievements if parent else None),
        parent_version_id=parent_id,
        application_id=req.application_id or (parent.application_id if parent else None),
        is_approved=bool(req.is_approved),
        sources_used=parent.sources_used if parent else [],
        db=db,
    )
    return {
        "message": "Cover letter version saved successfully",
        "id": new_version.id,
        "version_number": new_version.version_number,
        "is_approved": new_version.is_approved,
        "created_at": new_version.created_at,
    }

@router.post("/{cl_id}/approve")
def approve_letter(
    cl_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Approves a cover letter version and syncs it with the job's application record."""
    try:
        approved = approve_cover_letter(cl_id=cl_id, user_id=current_user.id, db=db)
        return {
            "message": "Cover letter approved successfully",
            "id": approved.id,
            "version_number": approved.version_number,
            "is_approved": approved.is_approved,
            "approved_at": approved.approved_at,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/version/{v1_id}/compare/{v2_id}")
def compare_versions(
    v1_id: int,
    v2_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compares two cover letter versions and returns word-level diff tokens."""
    try:
        diff_data = compare_cover_letter_versions(v1_id, v2_id, current_user.id, db)
        return diff_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/version/{cl_id}/restore")
def restore_version(
    cl_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Restores an older cover letter version by creating a new active head version copying its content."""
    old = db.query(CoverLetter).filter(CoverLetter.id == cl_id, CoverLetter.user_id == current_user.id).first()
    if not old:
        raise HTTPException(status_code=404, detail="Version not found")

    restored = save_cover_letter_version(
        user_id=current_user.id,
        job_id=old.job_id,
        content=old.content,
        style=old.style,
        candidate_motivation=old.candidate_motivation,
        selected_projects=old.selected_projects,
        selected_experiences=old.selected_experiences,
        selected_achievements=old.selected_achievements,
        parent_version_id=old.id,
        application_id=old.application_id,
        is_approved=old.is_approved,
        sources_used=old.sources_used,
        db=db,
    )
    return {
        "message": f"Restored version {old.version_number} as new version {restored.version_number}",
        "id": restored.id,
        "version_number": restored.version_number,
    }

@router.get("/{cl_id}")
def get_cover_letter(cl_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns a single cover letter by id."""
    cl = db.query(CoverLetter).filter(CoverLetter.id == cl_id, CoverLetter.user_id == current_user.id).first()
    if not cl:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    
    job = db.query(Job).filter(Job.id == cl.job_id).first()
    return {
        "id": cl.id,
        "job_id": cl.job_id,
        "application_id": cl.application_id,
        "company": job.company if job else "Unknown",
        "role": job.title if job else "Unknown",
        "content": cl.content,
        "format": cl.format,
        "style": cl.style or "concise",
        "version_number": cl.version_number or 1,
        "is_approved": bool(cl.is_approved),
        "approved_at": cl.approved_at,
        "candidate_motivation": cl.candidate_motivation,
        "selected_projects": cl.selected_projects or [],
        "selected_experiences": cl.selected_experiences or [],
        "selected_achievements": cl.selected_achievements or [],
        "parent_version_id": cl.parent_version_id,
        "sources_used": cl.sources_used or [],
        "created_at": cl.created_at,
        "updated_at": cl.updated_at,
    }

@router.put("/{cl_id}")
def update_cover_letter(cl_id: int, body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Updates the content or style of a cover letter in place."""
    cl = db.query(CoverLetter).filter(CoverLetter.id == cl_id, CoverLetter.user_id == current_user.id).first()
    if not cl:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    
    if "content" in body:
        cl.content = body["content"]
    if "style" in body:
        cl.style = body["style"]
    if "candidate_motivation" in body:
        cl.candidate_motivation = body["candidate_motivation"]
    if "is_approved" in body:
        cl.is_approved = bool(body["is_approved"])
        
    db.commit()
    db.refresh(cl)
    return {"message": "Cover letter updated successfully", "id": cl.id}

@router.delete("/{cl_id}")
def delete_cover_letter(cl_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Deletes a cover letter by id."""
    cl = db.query(CoverLetter).filter(CoverLetter.id == cl_id, CoverLetter.user_id == current_user.id).first()
    if not cl:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    
    db.delete(cl)
    db.commit()
    return {"message": "Cover letter deleted successfully"}

@router.get("/download/{cl_id}")
def download_cover_letter(cl_id: int, format: str = "pdf", current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Downloads a cover letter as PDF, Markdown (.md), or plain text (.txt)."""
    cl = db.query(CoverLetter).filter(CoverLetter.id == cl_id, CoverLetter.user_id == current_user.id).first()
    if not cl:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    
    job = db.query(Job).filter(Job.id == cl.job_id).first()
    company_name = job.company if job else "company"
    safe_company = "".join(c for c in company_name if c.isalnum() or c in (' ', '_')).replace(' ', '_')
    
    requested_format = (format or "pdf").lower()
    if requested_format not in {"pdf", "md", "txt"}:
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'pdf', 'md', or 'txt'.")

    if requested_format == "pdf":
        pdf_path = export_text_to_pdf(cl.content, f"cl_{current_user.id}_{cl_id}.pdf")
        return FileResponse(path=pdf_path, filename=f"Cover_Letter_{safe_company}.pdf", media_type="application/pdf")

    temp_dir = tempfile.gettempdir()
    ext = "md" if requested_format == "md" else "txt"
    media_type = "text/markdown" if requested_format == "md" else "text/plain"
    temp_path = os.path.join(temp_dir, f"cl_{current_user.id}_{cl_id}.{ext}")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(cl.content)
    return FileResponse(path=temp_path, filename=f"Cover_Letter_{safe_company}.{ext}", media_type=media_type)
