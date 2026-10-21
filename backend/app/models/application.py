from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Canonical CRM Statuses:
    # Discovered, Saved, Shortlisted, Preparing, Ready to Apply, Applied,
    # Assessment Received, Interview Scheduled, Interview Completed,
    # Offer Received, Rejected, Withdrawn, Position Closed
    status = Column(String, default="Preparing", index=True)
    source = Column(String, nullable=True) # greenhouse, lever, ashby, yc, direct, linkedin
    applied_at = Column(DateTime(timezone=True), nullable=True)
    submission_confirmed = Column(Boolean, default=False)
    
    # Exact Submitted Material References & Immutable Snapshots
    resume_version_id = Column(Integer, ForeignKey("resume_versions.id"), nullable=True)
    cover_letter_id = Column(Integer, ForeignKey("cover_letters.id"), nullable=True)
    submitted_resume_snapshot = Column(Text, nullable=True)
    submitted_cover_letter_snapshot = Column(Text, nullable=True)
    match_report = Column(JSON, nullable=True, default=dict)

    # Legacy file paths
    resume_version_url = Column(String, nullable=True)
    cover_letter_url = Column(String, nullable=True)
    
    # Dates, Deadlines & CRM Follow-ups
    assessment_deadline = Column(DateTime(timezone=True), nullable=True)
    assessment_notes = Column(Text, nullable=True)
    interview_date = Column(DateTime(timezone=True), nullable=True)
    interview_round = Column(String, nullable=True)
    interview_notes = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    follow_ups = Column(JSON, nullable=True, default=list) # [{id, text, due_date, completed}]
    reminders = Column(JSON, nullable=True, default=list) # [{id, type, remind_at, message, completed}]
    
    # Outcome tracking
    outcome = Column(String, nullable=True) # offer_received, rejected, withdrawn, pending
    outcome_notes = Column(Text, nullable=True)
    offer_compensation = Column(String, nullable=True)
    
    next_action = Column(String, nullable=True)
    user_instructions = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    analysis_progress = Column(JSON, nullable=True, default=dict)
    analysis_results = Column(JSON, nullable=True, default=dict)

    job = relationship("Job", back_populates="applications")
    user = relationship("User")
    history = relationship("ApplicationHistory", back_populates="application", cascade="all, delete-orphan")
    resume_version = relationship("ResumeVersion", foreign_keys=[resume_version_id])
    cover_letter = relationship("CoverLetter", foreign_keys=[cover_letter_id])
