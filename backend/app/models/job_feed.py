from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean
from sqlalchemy.sql import func
from .base import Base

class JobFeed(Base):
    __tablename__ = "job_feed"

    id = Column(Integer, primary_key=True, index=True)
    
    company = Column(String, index=True, nullable=False)
    title = Column(String, index=True, nullable=False)
    
    # Internal JD parsed, raw html, etc
    description = Column(Text, nullable=False)
    
    # e.g. "LinkedIn", "Greenhouse", "Lever"
    source = Column(String, nullable=False)
    
    # E.g. https://boards.greenhouse.io/...
    url = Column(String, unique=True, nullable=False)
    
    location = Column(String, nullable=True)
    salary_range = Column(String, nullable=True)
    is_remote = Column(Boolean, default=False)
    
    # "Backend", "Frontend", "AI"
    tags_json = Column(JSON, nullable=True)
    
    posted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
