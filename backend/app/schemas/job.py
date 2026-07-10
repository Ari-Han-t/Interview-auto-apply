from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime

class JobBase(BaseModel):
    title: str
    company: str
    url: Optional[str] = None
    location: Optional[str] = None
    status: str

class JobResponse(JobBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class JobAnalysisResult(BaseModel):
    match_percentage: int
    strengths: List[str]
    weaknesses: List[str]
    missing_keywords: List[str]
    likelihood: str
