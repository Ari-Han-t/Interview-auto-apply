from sqlalchemy import Column, Integer, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from .base import Base

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    raw_resume_text = Column(Text, nullable=True)
    latex_template = Column(Text, nullable=True)
    
    # Store structured data extracted from resume as JSON
    education_json = Column(JSON, nullable=True, default=list)
    experience_json = Column(JSON, nullable=True, default=list)
    projects_json = Column(JSON, nullable=True, default=list)
    skills_json = Column(JSON, nullable=True, default=dict)

    user = relationship("User", back_populates="profile")
