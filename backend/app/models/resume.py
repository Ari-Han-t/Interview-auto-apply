from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Boolean
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
    
    # "pdf", "docx", "latex", "tex", "zip"
    file_type = Column(String, nullable=False)
    
    # Extracted structured data specific to this version
    parsed_json = Column(JSON, nullable=True)

    # Master resume indicator
    is_master = Column(Boolean, default=False)

    # Targeted role, e.g. "Backend Engineer", "AI/ML Engineer"
    target_role = Column(String, nullable=True)

    # Version tracking number
    version_number = Column(Integer, default=1)

    # Raw LaTeX source text if available
    latex_source = Column(Text, nullable=True)

    # Candidate notes or tailoring remarks
    notes = Column(Text, nullable=True)

    # Selected project / experience IDs for modular resume assembly
    selected_projects = Column(JSON, nullable=True, default=list)
    selected_experiences = Column(JSON, nullable=True, default=list)
    selected_bullets = Column(JSON, nullable=True, default=dict)

    # Job & Application linkage for immutable job-specific versions
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True)

    # Modular resume assembly plan & template settings
    assembly_plan = Column(JSON, nullable=True)
    template_name = Column(String, nullable=True, default="clean_ats")
    template_options = Column(JSON, nullable=True)
    parent_version_id = Column(Integer, ForeignKey("resume_versions.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="resume_versions")
    job = relationship("Job")
    application = relationship("Application", foreign_keys=[application_id])

