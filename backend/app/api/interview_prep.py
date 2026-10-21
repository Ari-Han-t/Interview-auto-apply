from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.interview_prep import InterviewQuestion, MockInterviewSession
from app.models.job import Job
from app.api.auth import get_current_user
from app.services.interview_prep.service import (
    generate_interview_questions_for_job,
    create_mock_session,
    evaluate_mock_answer,
    INTERVIEW_CATEGORIES,
)

router = APIRouter()

class GenerateQuestionsRequest(BaseModel):
    categories: Optional[List[str]] = None
    force_refresh: bool = False

class CreateMockSessionRequest(BaseModel):
    job_id: int
    category: Optional[str] = "all"
    difficulty: Optional[str] = "medium"
    question_count: Optional[int] = 5

class SubmitAnswerRequest(BaseModel):
    question_index: int
    answer_text: str

@router.get("/categories")
def get_categories():
    """Returns the list of supported interview preparation question categories."""
    return INTERVIEW_CATEGORIES

@router.get("/job/{job_id}/questions")
def get_job_questions(
    job_id: int,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(InterviewQuestion).filter(
        InterviewQuestion.job_id == job_id,
        (InterviewQuestion.user_id == current_user.id) | (InterviewQuestion.user_id.is_(None))
    )
    if category and category != "all":
        query = query.filter(InterviewQuestion.category == category)
    questions = query.all()

    if not questions:
        # Generate automatically on first visit
        questions = generate_interview_questions_for_job(job_id=job_id, user_id=current_user.id, db=db)
        if category and category != "all":
            questions = [q for q in questions if q.category == category]

    return questions

@router.post("/job/{job_id}/generate")
def generate_questions(
    job_id: int,
    req: GenerateQuestionsRequest = GenerateQuestionsRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generates or refreshes interview questions for a job across all categories."""
    try:
        questions = generate_interview_questions_for_job(
            job_id=job_id,
            user_id=current_user.id,
            categories=req.categories,
            force_refresh=req.force_refresh,
            db=db,
        )
        return questions
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Interview question generation failed: {str(e)}")

@router.post("/sessions")
def start_mock_session(
    req: CreateMockSessionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Initializes a new interactive mock interview session."""
    try:
        session = create_mock_session(
            user_id=current_user.id,
            job_id=req.job_id,
            category=req.category or "all",
            difficulty=req.difficulty or "medium",
            question_count=req.question_count or 5,
            db=db,
        )
        return session
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start mock session: {str(e)}")

@router.get("/sessions")
def get_user_mock_sessions(
    job_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns mock interview session history for the user."""
    query = db.query(MockInterviewSession).filter(MockInterviewSession.user_id == current_user.id)
    if job_id:
        query = query.filter(MockInterviewSession.job_id == job_id)
    sessions = query.order_by(MockInterviewSession.created_at.desc()).all()
    
    result = []
    for s in sessions:
        job = db.query(Job).filter(Job.id == s.job_id).first()
        result.append({
            "id": s.id,
            "job_id": s.job_id,
            "company": job.company if job else "Unknown",
            "role": job.title if job else "Role",
            "title": s.title,
            "category": s.category,
            "difficulty": s.difficulty,
            "status": s.status,
            "total_questions": len(s.questions_json or []),
            "answered_count": len(s.answers_json or {}),
            "overall_score": s.overall_score,
            "created_at": s.created_at,
            "completed_at": s.completed_at,
        })
    return result

@router.get("/sessions/{session_id}")
def get_mock_session_details(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves full details, questions, answers, and evaluations for a session."""
    session = db.query(MockInterviewSession).filter(
        MockInterviewSession.id == session_id,
        MockInterviewSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Mock session not found")

    job = db.query(Job).filter(Job.id == session.job_id).first()
    return {
        "id": session.id,
        "job_id": session.job_id,
        "company": job.company if job else "Unknown",
        "role": job.title if job else "Role",
        "title": session.title,
        "category": session.category,
        "difficulty": session.difficulty,
        "status": session.status,
        "questions": session.questions_json or [],
        "current_question_index": session.current_question_index,
        "answers": session.answers_json or {},
        "overall_score": session.overall_score,
        "overall_feedback": session.overall_feedback,
        "created_at": session.created_at,
        "completed_at": session.completed_at,
    }

@router.post("/sessions/{session_id}/answer")
def submit_mock_answer_endpoint(
    session_id: int,
    req: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submits candidate's answer, evaluates it, and advances the session."""
    try:
        eval_data = evaluate_mock_answer(
            session_id=session_id,
            question_index=req.question_index,
            answer_text=req.answer_text,
            user_id=current_user.id,
            db=db,
        )
        return eval_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Answer evaluation failed: {str(e)}")
