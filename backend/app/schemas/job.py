from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class JobBase(BaseModel):
    title: str
    company: str
    url: Optional[str] = None
    location: Optional[str] = None
    status: str
    salary_range: Optional[str] = None
    is_remote: Optional[bool] = False
    tech_stack_json: Optional[List[str]] = []
    company_logo_url: Optional[str] = None
    source: Optional[str] = None
    posted_at: Optional[datetime] = None

class JobResponse(JobBase):
    id: int
    created_at: datetime
    eligible: Optional[bool] = True
    rejection_reason: Optional[str] = None
    
    class Config:
        from_attributes = True

class JobAnalysisResult(BaseModel):
    match_percentage: int
    strengths: List[str]
    weaknesses: List[str]
    missing_keywords: Optional[List[str]] = []
    likelihood: Optional[str] = None
    resume_similarity: Optional[int] = 0
    skill_overlap: Optional[int] = 0
    github_overlap: Optional[int] = 0
    keyword_overlap: Optional[int] = 0
    missing_skills: Optional[List[str]] = []
    reasoning: Optional[str] = ""

class JobDiscoveryRequest(BaseModel):
    source: Optional[str] = "yc"
    keywords: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = "both"
    only_suited: Optional[bool] = True

