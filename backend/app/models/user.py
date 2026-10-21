from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Integer, default=1) # 1=active, 0=inactive (sqlite compatibility)
    last_login = Column(DateTime(timezone=True), nullable=True)
    preferences_json = Column(JSON, nullable=True, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    profile = relationship("Profile", back_populates="user", uselist=False)
    user_profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    educations = relationship("CandidateEducation", back_populates="user", cascade="all, delete-orphan")
    experiences = relationship("CandidateExperience", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    user_skills = relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")
    capabilities = relationship("CandidateCapability", back_populates="user", uselist=False, cascade="all, delete-orphan")
    achievements = relationship("Achievement", back_populates="user", cascade="all, delete-orphan")
    courses = relationship("CourseCertification", back_populates="user", cascade="all, delete-orphan")
    leadership = relationship("CandidateLeadership", back_populates="user", cascade="all, delete-orphan")
    coursework_items = relationship("CandidateCoursework", back_populates="user", cascade="all, delete-orphan")
    publications = relationship("CandidatePublication", back_populates="user", cascade="all, delete-orphan")
    custom_sections = relationship("CandidateCustomSection", back_populates="user", cascade="all, delete-orphan")
    resume_versions = relationship("ResumeVersion", back_populates="user", cascade="all, delete-orphan")
    saved_jobs = relationship("UserSavedJob", back_populates="user", cascade="all, delete-orphan")


