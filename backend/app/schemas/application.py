from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ApplicationBase(BaseModel):
    job_id: int

class ApplicationResponse(ApplicationBase):
    id: int
    status: str
    source: Optional[str] = None
    applied_at: Optional[datetime] = None
    submission_confirmed: bool = False
    resume_version_id: Optional[int] = None
    cover_letter_id: Optional[int] = None
    submitted_resume_snapshot: Optional[str] = None
    submitted_cover_letter_snapshot: Optional[str] = None
    match_report: Optional[Dict[str, Any]] = None
    assessment_deadline: Optional[datetime] = None
    assessment_notes: Optional[str] = None
    interview_date: Optional[datetime] = None
    interview_round: Optional[str] = None
    interview_notes: Optional[str] = None
    notes: Optional[str] = None
    follow_ups: Optional[List[Dict[str, Any]]] = None
    reminders: Optional[List[Dict[str, Any]]] = None
    outcome: Optional[str] = None
    outcome_notes: Optional[str] = None
    offer_compensation: Optional[str] = None
    resume_version_url: Optional[str] = None
    cover_letter_url: Optional[str] = None
    next_action: Optional[str] = None
    user_instructions: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class GenerationResponse(BaseModel):
    application_id: int
    status: str
    resume_preview: str
    cover_letter_preview: str
    resume_url: Optional[str] = None
    cover_letter: Optional[str] = None

class ApplicationWithJobResponse(ApplicationResponse):
    company: str
    role: str
    job_url: Optional[str] = None
    application_url: Optional[str] = None
    job_location: Optional[str] = None
    job_salary: Optional[str] = None
    employment_type: Optional[str] = None
