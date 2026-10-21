from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class CoverLetter(Base):
    __tablename__ = "cover_letters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    
    content = Column(Text, nullable=False)
    format = Column(String, default="md")  # md, latex, pdf
    style = Column(String, default="concise")  # concise, technical, startup, formal
    candidate_motivation = Column(Text, nullable=True)
    selected_projects = Column(JSON, nullable=True, default=list)
    selected_experiences = Column(JSON, nullable=True, default=list)
    selected_achievements = Column(JSON, nullable=True, default=list)
    
    version_number = Column(Integer, default=1)
    is_approved = Column(Boolean, default=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    parent_version_id = Column(Integer, ForeignKey("cover_letters.id"), nullable=True)
    sources_used = Column(JSON, nullable=True, default=list)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    job = relationship("Job")
    application = relationship("Application", foreign_keys=[application_id])
    parent_version = relationship("CoverLetter", remote_side=[id])
