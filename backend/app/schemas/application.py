from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ApplicationBase(BaseModel):
    job_id: int

class ApplicationResponse(ApplicationBase):
    id: int
    status: str
    applied_at: Optional[datetime] = None
    resume_version_url: Optional[str] = None
    cover_letter_url: Optional[str] = None
    next_action: Optional[str] = None
    user_instructions: Optional[str] = None

    class Config:
        from_attributes = True

class GenerationResponse(BaseModel):
    application_id: int
    status: str
    resume_preview: str
    cover_letter_preview: str

class ApplicationWithJobResponse(ApplicationResponse):
    company: str
    role: str
    job_url: str

