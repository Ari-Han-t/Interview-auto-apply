from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.resume import ResumeVersion
from app.api.auth import get_current_user
from app.models.user import User
from app.services.storage.local_storage import LocalStorageProvider
import uuid

router = APIRouter()
storage = LocalStorageProvider()

@router.post("/upload")
async def upload_resume(file: UploadFile = File(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.strip():
        raise HTTPException(status_code=400, detail="A resume filename is required")
    if not file.filename.lower().endswith(('.tex', '.pdf', '.docx', '.txt', '.md')):
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload .tex, .pdf, .docx, .txt, or .md")

    import io
    from app.models.profile import Profile
    from app.services.ai.parser import validate_resume_text

    ext = file.filename.split('.')[-1].lower()
    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(status_code=400, detail="The resume file is empty")
    try:
        if ext in ('tex', 'txt', 'md'):
            text_content = content_bytes.decode('utf-8-sig')
        elif ext == 'pdf':
            from pdfminer.high_level import extract_text as extract_pdf_text
            text_content = extract_pdf_text(io.BytesIO(content_bytes))
        else:
            from docx import Document as DocxDocument
            document = DocxDocument(io.BytesIO(content_bytes))
            lines = [para.text.strip() for para in document.paragraphs if para.text.strip()]
            for table in document.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_text:
                        lines.append(" | ".join(row_text))
            text_content = '\n'.join(lines)
        validate_resume_text(text_content)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read resume text. Please upload a text-readable resume.") from None

    unique_filename = f"{current_user.id}_{uuid.uuid4().hex}.{ext}"
    file_path = storage.upload_file(unique_filename, io.BytesIO(content_bytes), file.content_type or "application/octet-stream")
    try:
        profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
        if profile is None:
            profile = Profile(user_id=current_user.id)
            db.add(profile)
        profile.raw_resume_text = text_content
        if ext == 'tex':
            profile.latex_template = text_content
        new_resume = ResumeVersion(
            user_id=current_user.id, name=file.filename,
            storage_path=file_path, file_type=ext,
        )
        db.add(new_resume)
        db.flush()
        resume_id = new_resume.id
        db.commit()
    except Exception:
        db.rollback()
        storage.delete_file(file_path)
        raise HTTPException(status_code=500, detail="Could not save resume") from None
    return {"message": "Resume uploaded successfully. Use autofill to update your profile.", "id": resume_id}


@router.post("/autofill")
def autofill_resume(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models.profile import Profile
    from app.services.ai.parser import (
        extract_resume, merge_resume_to_profile, ResumeParseError, ResumeTextError,
    )

    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    try:
        extracted = extract_resume(profile.raw_resume_text if profile else None)
    except ResumeTextError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    except ResumeParseError:
        raise HTTPException(status_code=502, detail="Resume extraction failed. Please try again.") from None
    try:
        counts = merge_resume_to_profile(db, current_user.id, extracted)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not merge resume into profile. No changes were saved.") from None
    return {"message": "Resume autofill complete. Existing profile data was preserved.", "counts": counts}

@router.get("/versions")
def get_resume_versions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resumes = db.query(ResumeVersion).filter(ResumeVersion.user_id == current_user.id).all()
    return resumes

@router.delete("/{resume_id}")
def delete_resume(resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = db.query(ResumeVersion).filter(ResumeVersion.id == resume_id, ResumeVersion.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    storage.delete_file(resume.storage_path)
    db.delete(resume)
    db.commit()
    return {"message": "Deleted successfully"}

from fastapi.responses import FileResponse

@router.get("/download/{resume_id}")
def download_resume(resume_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = db.query(ResumeVersion).filter(ResumeVersion.id == resume_id, ResumeVersion.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    import os
    if not os.path.exists(resume.storage_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(path=resume.storage_path, filename=resume.name)
