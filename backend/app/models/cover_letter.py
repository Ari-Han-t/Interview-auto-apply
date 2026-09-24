from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class CoverLetter(Base):
    __tablename__ = "cover_letters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    
    content = Column(Text, nullable=False)
    format = Column(String, default="md")  # md, latex, pdf
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    job = relationship("Job")
