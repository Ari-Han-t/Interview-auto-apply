from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    status = Column(String, default="generating") # generating, generated, applying, applied, interview, rejected, offer
    applied_at = Column(DateTime(timezone=True), nullable=True)
    
    resume_version_url = Column(String, nullable=True)
    cover_letter_url = Column(String, nullable=True)
    
    next_action = Column(String, nullable=True)

    job = relationship("Job", back_populates="applications")
    user = relationship("User")
