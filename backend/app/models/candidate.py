from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, Float, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    github = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    portfolio = Column(String, nullable=True)
    current_location = Column(String, nullable=True)
    preferred_locations = Column(JSON, nullable=True, default=list)
    work_authorization = Column(String, nullable=True)
    visa_required = Column(Boolean, default=False)
    willing_to_relocate = Column(Boolean, default=True)
    remote_preference = Column(String, nullable=True) # "remote", "onsite", "hybrid", "any"
    graduation_year = Column(Integer, nullable=True)
    degree = Column(String, nullable=True) # "Bachelors", "Masters", "PhD", "None"
    cgpa = Column(Float, nullable=True)
    university = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="user_profile")

class CandidateExperience(Base):
    __tablename__ = "candidate_experiences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company = Column(String, nullable=False)
    title = Column(String, nullable=False)
    internship_or_fulltime = Column(String, nullable=True) # "internship" or "fulltime"
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    currently_working = Column(Boolean, default=False)
    months_of_experience = Column(Integer, default=0)
    description = Column(Text, nullable=True)

    user = relationship("User", back_populates="experiences")

class Project(Base):
    __tablename__ = "candidate_projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    github = Column(String, nullable=True)
    live_link = Column(String, nullable=True)
    technologies = Column(JSON, nullable=True, default=list)

    user = relationship("User", back_populates="projects")

class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

class UserSkill(Base):
    __tablename__ = "user_skills"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    skill_id = Column(Integer, ForeignKey("skills.id"), primary_key=True)
    confidence = Column(Integer, default=5) # 1-5
    years_used = Column(Float, default=0.0)

    user = relationship("User", back_populates="user_skills")
    skill = relationship("Skill")

class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True, unique=True)
    minimum_salary = Column(Integer, default=0)
    maximum_salary = Column(Integer, nullable=True)
    preferred_locations = Column(JSON, nullable=True, default=list)
    remote_only = Column(Boolean, default=False)
    hybrid_allowed = Column(Boolean, default=True)
    onsite_allowed = Column(Boolean, default=True)
    preferred_roles = Column(JSON, nullable=True, default=list)
    preferred_domains = Column(JSON, nullable=True, default=list)
    company_size = Column(String, nullable=True)
    preferred_industries = Column(JSON, nullable=True, default=list)
    maximum_experience_required = Column(Integer, nullable=True)
    minimum_experience_required = Column(Integer, nullable=True)
    exclude_companies = Column(JSON, nullable=True, default=list)
    exclude_keywords = Column(JSON, nullable=True, default=list)
    preferred_job_type = Column(String, default="both") # "internship", "fulltime", "both"
    preferred_internship = Column(Boolean, default=True)
    preferred_fulltime = Column(Boolean, default=True)
    notice_period = Column(Integer, default=0)
    earliest_joining_date = Column(String, nullable=True)
    maximum_daily_applications = Column(Integer, default=5)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="preferences")

class CandidateCapability(Base):
    __tablename__ = "candidate_capabilities"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True, unique=True)
    can_relocate = Column(Boolean, default=True)
    can_work_remote = Column(Boolean, default=True)
    can_do_internship = Column(Boolean, default=True)
    can_do_fulltime = Column(Boolean, default=True)
    can_work_parttime = Column(Boolean, default=True)
    can_work_contract = Column(Boolean, default=True)
    can_work_night_shift = Column(Boolean, default=False)
    has_work_authorization = Column(Boolean, default=True)
    needs_sponsorship = Column(Boolean, default=False)
    open_to_startup = Column(Boolean, default=True)
    open_to_enterprise = Column(Boolean, default=True)
    open_to_research = Column(Boolean, default=True)

    user = relationship("User", back_populates="capabilities")

class JobRequirement(Base):
    __tablename__ = "job_requirements"

    job_id = Column(Integer, ForeignKey("jobs.id"), primary_key=True, unique=True)
    minimum_experience = Column(Integer, default=0)
    maximum_experience = Column(Integer, nullable=True)
    minimum_degree = Column(String, nullable=True) # "Bachelors", "Masters", "PhD", "None"
    required_skills = Column(JSON, nullable=True, default=list)
    preferred_skills = Column(JSON, nullable=True, default=list)
    visa_required = Column(Boolean, default=False)
    location = Column(String, nullable=True)
    remote = Column(Boolean, default=False)
    salary = Column(Integer, default=0)
    employment_type = Column(String, nullable=True) # "Full-time", "Internship", "Contract"
    internship = Column(Boolean, default=False)
    fulltime = Column(Boolean, default=True)
    contract = Column(Boolean, default=False)
    technologies = Column(JSON, nullable=True, default=list)
    keywords = Column(JSON, nullable=True, default=list)
    company_size = Column(String, nullable=True)
    job = relationship("Job", back_populates="requirements")

class Achievement(Base):
    __tablename__ = "candidate_achievements"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    category = Column(String, nullable=True) # "hackathon", "award", "prize", "publication", "other"
    issuer_or_event = Column(String, nullable=True)
    year_or_date = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    user = relationship("User", back_populates="achievements")

class CourseCertification(Base):
    __tablename__ = "candidate_courses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    issuer = Column(String, nullable=True) # "Coursera", "Udemy", "AWS", etc.
    issue_date = Column(String, nullable=True)
    credential_url = Column(String, nullable=True)
    skills_covered = Column(JSON, nullable=True, default=list)

    user = relationship("User", back_populates="courses")

