from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    category = Column(String, nullable=False, index=True) 
    # Categories:
    # - resume_walkthrough
    # - programming_fundamentals
    # - dsa
    # - languages_frameworks
    # - role_specific (backend / ai_ml / frontend)
    # - software_practices
    # - system_design
    # - behavioral
    # - company_product
    
    difficulty = Column(String, default="medium", index=True) # easy, medium, hard
    question = Column(Text, nullable=False)
    
    why_it_matters = Column(Text, nullable=True)
    what_good_answer_demonstrates = Column(Text, nullable=True)
    suggested_answer = Column(Text, nullable=True)
    likely_follow_ups = Column(JSON, nullable=True, default=list) # list of str
    common_mistakes = Column(JSON, nullable=True, default=list) # list of str
    practice_resources = Column(JSON, nullable=True, default=list) # list of {title, url, type}
    star_framework = Column(JSON, nullable=True, default=dict) # {situation, task, action, result}
    
    is_verified_company_question = Column(Boolean, default=False)
    source_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job")
    user = relationship("User")

    @property
    def star_breakdown(self):
        return self.star_framework


class MockInterviewSession(Base):
    __tablename__ = "mock_interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    
    title = Column(String, nullable=False)
    category = Column(String, default="all")
    difficulty = Column(String, default="medium")
    status = Column(String, default="in_progress") # in_progress, completed
    
    questions_json = Column(JSON, nullable=False, default=list) # list of question objects or IDs
    current_question_index = Column(Integer, default=0)
    
    # answers_json format:
    # {
    #   "<q_idx>": {
    #       "question_id": 12,
    #       "question": "...",
    #       "answer_text": "...",
    #       "score": 85,
    #       "feedback": "...",
    #       "strengths": ["..."],
    #       "improvements": ["..."],
    #       "model_answer": "...",
    #       "evaluated_at": "...",
    #       "retry_count": 0
    #   }
    # }
    answers_json = Column(JSON, nullable=False, default=dict)
    
    overall_score = Column(Float, nullable=True)
    overall_feedback = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User")
    job = relationship("Job")
