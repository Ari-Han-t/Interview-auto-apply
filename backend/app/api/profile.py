from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.profile import Profile
from app.api.auth import get_current_user

router = APIRouter()

@router.get("/")
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...), 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    # TODO: In future milestones, integrate actual PDF parsing and LLM structuring here.
    # For Milestone 1, we simulate parsing by just saving raw content.
    
    content = await file.read()
    text_content = content.decode('utf-8', errors='ignore')
    
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        profile = Profile(
            user_id=current_user.id,
            raw_resume_text=text_content,
            education_json=[],
            experience_json=[],
            projects_json=[],
            skills_json={"languages": [], "frameworks": []}
        )
        db.add(profile)
    else:
        profile.raw_resume_text = text_content
        
    db.commit()
    db.refresh(profile)
    return {"message": "Resume uploaded and profile initialized", "profile_id": profile.id}

@router.post("/upload-latex")
async def upload_latex_resume(
    file: UploadFile = File(...), 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.tex'):
        raise HTTPException(status_code=400, detail="File must be a .tex file")
        
    content = await file.read()
    text_content = content.decode('utf-8', errors='ignore')
    
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        profile = Profile(
            user_id=current_user.id,
            latex_template=text_content
        )
        db.add(profile)
    else:
        profile.latex_template = text_content
        
    db.commit()
    return {"message": "LaTeX template uploaded successfully"}
