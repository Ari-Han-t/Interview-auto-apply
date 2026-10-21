from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class JobBase(BaseModel):
    title: str
    company: str
    url: Optional[str] = None
    application_url: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = "active"
    salary_range: Optional[str] = None
    compensation_min: Optional[float] = None
    compensation_max: Optional[float] = None
    currency: Optional[str] = "USD"
    compensation_interval: Optional[str] = None
    work_arrangement: Optional[str] = "onsite"
    employment_type: Optional[str] = "fulltime"
    is_remote: Optional[bool] = False
    tech_stack_json: Optional[List[str]] = []
    responsibilities_json: Optional[List[str]] = []
    required_skills_json: Optional[List[str]] = []
    preferred_skills_json: Optional[List[str]] = []
    requirements_json: Optional[Dict[str, Any]] = {}
    eligibility_criteria_json: Optional[Dict[str, Any]] = {}
    graduation_restrictions: Optional[List[str]] = []
    company_logo_url: Optional[str] = None
    source: Optional[str] = None
    source_job_id: Optional[str] = None
    source_provenance: Optional[Dict[str, Any]] = {}
    posted_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    description: Optional[str] = None

class JobCreateManual(JobBase):
    pass

class JobResponse(JobBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    is_expired: Optional[bool] = False
    expired_at: Optional[datetime] = None
    dedup_hash: Optional[str] = None
    eligible: Optional[bool] = True
    rejection_reason: Optional[str] = None
    match_percentage: Optional[int] = None
    is_saved: Optional[bool] = False
    
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
    source: Optional[str] = "all"
    keywords: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = "both"
    only_suited: Optional[bool] = True
    custom_token: Optional[str] = None # e.g. custom board for greenhouse / lever / ashby

class JobImportUrlRequest(BaseModel):
    url: str

class JobSaveRequest(BaseModel):
    notes: Optional[str] = None

class SourceHealthInfo(BaseModel):
    source_id: str
    display_name: str
    auth_status: str # available, limited, requires_auth, blocked_for_scraping
    can_fetch_catalog: bool
    access_requirement: str
    last_sync_at: Optional[datetime] = None
    is_healthy: bool
    total_jobs_indexed: int = 0
    recent_sync_status: Optional[str] = None

class SyncLogResponse(BaseModel):
    id: int
    source_id: str
    status: str
    items_found: int
    items_imported: int
    items_updated: int
    error_message: Optional[str] = None
    duration_ms: int
    triggered_by: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class JobSearchResponse(BaseModel):
    items: List[JobResponse]
    total: int
    page: int
    page_size: int
    parsed_criteria: Optional[Dict[str, Any]] = None
