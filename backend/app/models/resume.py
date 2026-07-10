from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # E.g. "Software Engineer Version", "Backend Specialization"
    name = Column(String, nullable=False)
    
    # Path/URL in storage
    storage_path = Column(String, nullable=False)
    
    # "pdf", "docx", "latex"
    file_type = Column(String, nullable=False)
    
    # Optional: the extracted structured data specific to this version
    parsed_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User")
