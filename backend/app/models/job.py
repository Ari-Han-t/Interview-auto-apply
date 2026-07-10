from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    url = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    # Store extracted requirements like required_skills, preferred_skills, experience
    requirements_json = Column(JSON, nullable=True, default=dict)
    
    status = Column(String, default="discovered") # discovered, analyzed, applied, ignored
    deadline = Column(DateTime(timezone=True), nullable=True)
    location = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    applications = relationship("Application", back_populates="job")
