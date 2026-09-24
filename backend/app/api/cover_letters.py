from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.cover_letter import CoverLetter
from app.models.job import Job
from app.api.auth import get_current_user
from app.services.pdf_exporter import export_text_to_pdf
import os
import tempfile

router = APIRouter()

@router.get("/")
def get_cover_letters(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Returns list of all cover letters generated for the user.
    """
    cls = db.query(CoverLetter, Job).join(Job, CoverLetter.job_id == Job.id).filter(CoverLetter.user_id == current_user.id).all()
    result = []
    for cl, job in cls:
        result.append({
            "id": cl.id,
            "job_id": cl.job_id,
            "company": job.company,
            "role": job.title,
            "content": cl.content,
            "format": cl.format,
            "created_at": cl.created_at
        })
    return result

@router.get("/{cl_id}")
def get_cover_letter(cl_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Returns a single cover letter by id.
    """
    cl = db.query(CoverLetter).filter(CoverLetter.id == cl_id, CoverLetter.user_id == current_user.id).first()
    if not cl:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    
    job = db.query(Job).filter(Job.id == cl.job_id).first()
    return {
        "id": cl.id,
        "job_id": cl.job_id,
        "company": job.company if job else "Unknown",
        "role": job.title if job else "Unknown",
        "content": cl.content,
        "format": cl.format,
        "created_at": cl.created_at
    }

@router.put("/{cl_id}")
def update_cover_letter(cl_id: int, body: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Updates the content of a cover letter.
    """
    cl = db.query(CoverLetter).filter(CoverLetter.id == cl_id, CoverLetter.user_id == current_user.id).first()
    if not cl:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    
    if "content" in body:
        cl.content = body["content"]
    if "format" in body:
        cl.format = body["format"]
        
    db.commit()
    return {"message": "Cover letter updated successfully"}

@router.delete("/{cl_id}")
def delete_cover_letter(cl_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Deletes a cover letter by id.
    """
    cl = db.query(CoverLetter).filter(CoverLetter.id == cl_id, CoverLetter.user_id == current_user.id).first()
    if not cl:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    
    db.delete(cl)
    db.commit()
    return {"message": "Cover letter deleted successfully"}

@router.get("/download/{cl_id}")
def download_cover_letter(cl_id: int, format: str = "md", current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Downloads a cover letter as PDF or plain text/markdown.
    """
    cl = db.query(CoverLetter).filter(CoverLetter.id == cl_id, CoverLetter.user_id == current_user.id).first()
    if not cl:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    
    job = db.query(Job).filter(Job.id == cl.job_id).first()
    company_name = job.company if job else "company"
    safe_company = "".join(c for c in company_name if c.isalnum() or c in (' ', '_')).replace(' ', '_')
    
    requested_format = (format or "md").lower()
    if requested_format not in {"pdf", "md", "txt"}:
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'pdf' or 'md'.")

    if requested_format == "pdf":
        pdf_path = export_text_to_pdf(cl.content, f"cl_{current_user.id}_{cl_id}.pdf")
        return FileResponse(path=pdf_path, filename=f"Cover_Letter_{safe_company}.pdf", media_type="application/pdf")

    # Default text export (markdown/text)
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"cl_{current_user.id}_{cl_id}.md")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(cl.content)
    return FileResponse(path=temp_path, filename=f"Cover_Letter_{safe_company}.md", media_type="text/markdown")
