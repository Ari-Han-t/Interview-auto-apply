from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class CompanyResearch(Base):
    __tablename__ = "company_researches"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    company_name = Column(String, nullable=False, index=True)
    
    # Structured Research Brief Sections
    company_overview = Column(Text, nullable=True)
    products_and_services = Column(JSON, nullable=True, default=list)
    industry_and_business_model = Column(Text, nullable=True)
    target_customers_or_markets = Column(Text, nullable=True)
    recent_announcements = Column(JSON, nullable=True, default=list) # [{title, date, summary, source_url}]
    engineering_challenges = Column(JSON, nullable=True, default=list)
    key_skills_in_position = Column(JSON, nullable=True, default=list)
    candidate_relevant_experience = Column(JSON, nullable=True, default=list)
    interview_topics_to_prep = Column(JSON, nullable=True, default=list)
    
    # Epistemic Honesty & Provenance
    verified_facts = Column(JSON, nullable=True, default=list) # [{claim, source, date}]
    inferred_insights = Column(JSON, nullable=True, default=list) # [{insight, rationale}]
    unavailable_fields = Column(JSON, nullable=True, default=list) # ["Funding history not disclosed", ...]
    sources = Column(JSON, nullable=True, default=list) # [{url, label, retrieved_at, is_verified}]
    
    summary_markdown = Column(Text, nullable=True)
    retrieval_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    job = relationship("Job")
    user = relationship("User")
