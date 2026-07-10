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
    if not file.filename.endswith(('.tex', '.pdf', '.docx')):
        raise HTTPException(status_code=400, detail="Unsupported file format")

    ext = file.filename.split('.')[-1]
    unique_filename = f"{current_user.id}_{uuid.uuid4().hex}.{ext}"
    
    file_path = storage.upload_file(unique_filename, file.file, file.content_type)
    
    # Also update the main profile so the AI Tailoring engine has content to work with
    from app.models.profile import Profile
    file.file.seek(0)
    content_bytes = file.file.read()
    
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        profile = Profile(user_id=current_user.id)
        db.add(profile)
        
    try:
        text_content = content_bytes.decode('utf-8', errors='ignore')
        if ext == 'tex':
            profile.latex_template = text_content
            # Keep raw resume text for general analysis
            profile.raw_resume_text = text_content
        elif ext in ['pdf', 'docx']:
            # For now, just save raw bytes string (TODO: parse pdf/docx properly)
            profile.raw_resume_text = text_content
    except Exception as e:
        pass
        
    
    new_resume = ResumeVersion(
        user_id=current_user.id,
        name=file.filename,
        storage_path=file_path,
        file_type=ext
    )
    db.add(new_resume)
    db.commit()
    db.refresh(new_resume)
    
    return {"message": "Resume uploaded successfully", "id": new_resume.id}

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
