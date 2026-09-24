from sqlalchemy import Column, Integer, Text, ForeignKey, JSON, String, DateTime
from sqlalchemy.orm import relationship
from .base import Base

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    raw_resume_text = Column(Text, nullable=True)
    latex_template = Column(Text, nullable=True)
    github_username = Column(String, nullable=True)
    github_synced_at = Column(DateTime(timezone=True), nullable=True)
    tailoring_instructions = Column(Text, nullable=True)
    
    # Store structured data extracted from resume as JSON
    education_json = Column(JSON, nullable=True, default=list)
    experience_json = Column(JSON, nullable=True, default=list)
    projects_json = Column(JSON, nullable=True, default=list)
    skills_json = Column(JSON, nullable=True, default=dict)
    achievements_json = Column(JSON, nullable=True, default=list)

    user = relationship("User", back_populates="profile")
