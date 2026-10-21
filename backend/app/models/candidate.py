from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, Float, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    full_name = Column(String, nullable=True)
    preferred_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    github = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    portfolio = Column(String, nullable=True)
    website = Column(String, nullable=True)
    current_location = Column(String, nullable=True)
    preferred_locations = Column(JSON, nullable=True, default=list)
    work_authorization = Column(String, nullable=True)
    visa_required = Column(Boolean, default=False)
    willing_to_relocate = Column(Boolean, default=True)
    remote_preference = Column(String, nullable=True) # "remote", "onsite", "hybrid", "any"
    graduation_year = Column(Integer, nullable=True)
    degree = Column(String, nullable=True) # "Bachelors", "Masters", "PhD", "None"
    specialization = Column(String, nullable=True)
    cgpa = Column(Float, nullable=True)
    university = Column(String, nullable=True)
    coursework = Column(JSON, nullable=True, default=list)
    current_semester_or_year = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    availability = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="user_profile")

class CandidateEducation(Base):
    __tablename__ = "candidate_educations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    institution = Column(String, nullable=False)
    degree = Column(String, nullable=True)
    specialization = Column(String, nullable=True)
    start_year = Column(Integer, nullable=True)
    graduation_year = Column(Integer, nullable=True)
    cgpa = Column(Float, nullable=True)
    gpa_scale = Column(String, nullable=True, default="4.0")
    honors = Column(String, nullable=True)
    coursework = Column(JSON, nullable=True, default=list)
    location = Column(String, nullable=True)
    bullets = Column(JSON, nullable=True, default=list)
    is_visible = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    verification_status = Column(String, nullable=True, default="self_attested")
    evidence_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="educations")

class CandidateExperience(Base):
    __tablename__ = "candidate_experiences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company = Column(String, nullable=False)
    title = Column(String, nullable=False)
    experience_type = Column(String, nullable=True, default="employment") # "employment", "internship", "freelance", "research", "leadership"
    internship_or_fulltime = Column(String, nullable=True) # "internship" or "fulltime"
    location = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    currently_working = Column(Boolean, default=False)
    months_of_experience = Column(Integer, default=0)
    responsibilities = Column(Text, nullable=True)
    contributions = Column(Text, nullable=True)
    metrics = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    technologies = Column(JSON, nullable=True, default=list)
    highlights = Column(JSON, nullable=True, default=list)
    bullets = Column(JSON, nullable=True, default=list)
    is_visible = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    verification_status = Column(String, nullable=True, default="self_attested")
    evidence_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="experiences")

class Project(Base):
    __tablename__ = "candidate_projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    problem = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    personal_contribution = Column(Text, nullable=True)
    implementation = Column(Text, nullable=True)
    programming_languages = Column(JSON, nullable=True, default=list)
    frameworks = Column(JSON, nullable=True, default=list)
    libraries = Column(JSON, nullable=True, default=list)
    databases = Column(JSON, nullable=True, default=list)
    apis = Column(JSON, nullable=True, default=list)
    ai_ml_techniques = Column(JSON, nullable=True, default=list)
    deployment_technologies = Column(JSON, nullable=True, default=list)
    technologies = Column(JSON, nullable=True, default=list)
    technical_challenges = Column(Text, nullable=True)
    verified_outcomes = Column(JSON, nullable=True, default=list)
    role = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    github = Column(String, nullable=True)
    live_link = Column(String, nullable=True)
    supporting_evidence = Column(Text, nullable=True)
    evidence_url = Column(String, nullable=True)
    highlights = Column(JSON, nullable=True, default=list)
    bullets = Column(JSON, nullable=True, default=list)
    is_visible = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    verification_status = Column(String, nullable=True, default="self_attested")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

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
    category = Column(String, default="General")
    proficiency_level = Column(String, nullable=True, default="Advanced") # "Beginner", "Intermediate", "Advanced", "Expert"
    verification_status = Column(String, nullable=True, default="self_attested") # "unverified", "self_attested", "project_backed", "certified", "verified"
    evidence_url = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    is_visible = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)

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
    availability_duration = Column(String, nullable=True) # e.g. "Immediate", "3-6 months"
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
    impact_metrics = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    bullets = Column(JSON, nullable=True, default=list)
    evidence_url = Column(String, nullable=True)
    verification_status = Column(String, nullable=True, default="self_attested")
    is_visible = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="achievements")

class CourseCertification(Base):
    __tablename__ = "candidate_courses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    issuer = Column(String, nullable=True) # "Coursera", "Udemy", "AWS", etc.
    issue_date = Column(String, nullable=True)
    expiry_date = Column(String, nullable=True)
    credential_id = Column(String, nullable=True)
    credential_url = Column(String, nullable=True)
    skills_covered = Column(JSON, nullable=True, default=list)
    bullets = Column(JSON, nullable=True, default=list)
    evidence_url = Column(String, nullable=True)
    verification_status = Column(String, nullable=True, default="self_attested")
    is_visible = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="courses")

class CandidateLeadership(Base):
    __tablename__ = "candidate_leadership"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization = Column(String, nullable=False)
    role = Column(String, nullable=False)
    category = Column(String, nullable=True, default="club") # "club", "student_government", "volunteer", "sports", "mentorship", "professional", "other"
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    currently_active = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)
    bullets = Column(JSON, nullable=True, default=list)
    evidence_url = Column(String, nullable=True)
    verification_status = Column(String, nullable=True, default="self_attested")
    is_visible = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="leadership")

class CandidateCoursework(Base):
    __tablename__ = "candidate_coursework"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    course_name = Column(String, nullable=False)
    course_code = Column(String, nullable=True)
    institution = Column(String, nullable=True)
    term_or_year = Column(String, nullable=True)
    grade = Column(String, nullable=True)
    skills_learned = Column(JSON, nullable=True, default=list)
    description = Column(Text, nullable=True)
    topics_covered = Column(JSON, nullable=True, default=list)
    evidence_url = Column(String, nullable=True)
    verification_status = Column(String, nullable=True, default="self_attested")
    is_visible = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="coursework_items")

class CandidatePublication(Base):
    __tablename__ = "candidate_publications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    publication_type = Column(String, nullable=True, default="conference_paper") # "conference_paper", "journal_article", "preprint", "open_source_pr", "tech_blog", "book_chapter", "other"
    venue_or_publisher = Column(String, nullable=True)
    publication_date = Column(String, nullable=True)
    authors = Column(JSON, nullable=True, default=list)
    url = Column(String, nullable=True)
    doi_or_id = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    citation_count_or_metrics = Column(String, nullable=True)
    bullets = Column(JSON, nullable=True, default=list)
    evidence_url = Column(String, nullable=True)
    verification_status = Column(String, nullable=True, default="self_attested")
    is_visible = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="publications")

class CandidateCustomSection(Base):
    __tablename__ = "candidate_custom_sections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    section_title = Column(String, nullable=False) # e.g. "Patents", "Speaking Engagements", "Military Experience"
    title = Column(String, nullable=False)
    subtitle = Column(String, nullable=True)
    date_or_year = Column(String, nullable=True)
    location = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    bullets = Column(JSON, nullable=True, default=list)
    url = Column(String, nullable=True)
    evidence_url = Column(String, nullable=True)
    verification_status = Column(String, nullable=True, default="self_attested")
    is_visible = Column(Boolean, default=True)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="custom_sections")

