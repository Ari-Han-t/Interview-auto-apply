from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Boolean, Float, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, index=True)
    company = Column(String, nullable=False, index=True)
    url = Column(String, nullable=True) # original url
    application_url = Column(String, nullable=True) # direct apply url
    description = Column(Text, nullable=True)
    
    # Responsibilities and skills lists
    responsibilities_json = Column(JSON, nullable=True, default=list)
    required_skills_json = Column(JSON, nullable=True, default=list)
    preferred_skills_json = Column(JSON, nullable=True, default=list)
    
    # Extracted requirements & eligibility
    requirements_json = Column(JSON, nullable=True, default=dict)
    eligibility_criteria_json = Column(JSON, nullable=True, default=dict)
    graduation_restrictions = Column(JSON, nullable=True, default=list)
    
    status = Column(String, default="active", index=True) # active, expired, discovered, applied, ignored
    deadline = Column(DateTime(timezone=True), nullable=True)
    location = Column(String, nullable=True, index=True)
    work_arrangement = Column(String, nullable=True, default="onsite") # remote, hybrid, onsite
    employment_type = Column(String, nullable=True, default="fulltime", index=True) # internship, fulltime, contract, parttime
    
    salary_range = Column(String, nullable=True)
    compensation_min = Column(Float, nullable=True)
    compensation_max = Column(Float, nullable=True)
    currency = Column(String, nullable=True, default="USD")
    compensation_interval = Column(String, nullable=True) # yearly, monthly, hourly
    
    is_remote = Column(Boolean, default=False)
    tech_stack_json = Column(JSON, nullable=True, default=list)
    company_logo_url = Column(String, nullable=True)
    source = Column(String, nullable=True, index=True) # greenhouse, lever, ashby, yc, internshala, linkedin, indeed, career_page, wellfound, glassdoor, custom_feed
    source_job_id = Column(String, nullable=True)
    source_provenance = Column(JSON, nullable=True, default=dict)
    
    posted_at = Column(DateTime(timezone=True), nullable=True)
    last_verified_at = Column(DateTime(timezone=True), server_default=func.now())
    is_expired = Column(Boolean, default=False, index=True)
    expired_at = Column(DateTime(timezone=True), nullable=True)
    dedup_hash = Column(String, nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    applications = relationship("Application", back_populates="job")
    technologies = relationship("Technology", secondary="job_technologies")
    requirements = relationship("JobRequirement", back_populates="job", uselist=False, cascade="all, delete-orphan")
    saved_by_users = relationship("UserSavedJob", back_populates="job", cascade="all, delete-orphan")


class UserSavedJob(Base):
    __tablename__ = "user_saved_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_saved_job"),
    )

    user = relationship("User", back_populates="saved_jobs")
    job = relationship("Job", back_populates="saved_by_users")


class JobSourceSyncLog(Base):
    __tablename__ = "job_source_sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False) # success, partial, failed, blocked
    items_found = Column(Integer, default=0)
    items_imported = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    access_requirement = Column(Text, nullable=True)
    duration_ms = Column(Integer, default=0)
    triggered_by = Column(String, default="manual") # manual, scheduled, system
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)


class JobSourceConfig(Base):
    __tablename__ = "job_source_configs"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    is_enabled = Column(Boolean, default=True)
    config_json = Column(JSON, nullable=True, default=dict)
    auth_status = Column(String, default="available") # available, limited, requires_auth, blocked_for_scraping
    access_requirement = Column(Text, nullable=True)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
