from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func
from app.core.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.application import Application
from app.api.auth import get_current_user

router = APIRouter()

@router.get("/overview")
def get_analytics_overview(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns analytics overview for the current user's applications."""
    total_applications = db.query(Application).filter(Application.user_id == current_user.id).count()
    total_jobs = db.query(Job).count()

    from app.services.ai.eligibility import evaluate_eligibility
    all_jobs = db.query(Job).all()
    eligible_count = 0
    ineligible_count = 0
    for job in all_jobs:
        res = evaluate_eligibility(current_user.id, job.id, db, allow_requirement_extraction=False)
        if res["eligible"]:
            eligible_count += 1
        else:
            ineligible_count += 1

    responded_count = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.status.in_(["interview", "rejected", "offer"])
    ).count()

    interview_count = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.status.in_(["interview", "offer"])
    ).count()

    response_rate = (responded_count / total_applications * 100) if total_applications > 0 else 0.0
    interview_rate = (interview_count / total_applications * 100) if total_applications > 0 else 0.0

    # Status breakdown
    status_counts = {}
    status_rows = (
        db.query(Application.status, sql_func.count(Application.id))
        .filter(Application.user_id == current_user.id)
        .group_by(Application.status)
        .all()
    )
    for status, count in status_rows:
        status_counts[status] = count

    # Keyword performance from real applications (placeholder until we track per-keyword outcomes)
    ab_testing_data = []

    return {
        "total_applications": total_applications,
        "total_jobs": total_jobs,
        "eligible_jobs": eligible_count,
        "ineligible_jobs": ineligible_count,
        "response_rate": round(response_rate, 1),
        "interview_rate": round(interview_rate, 1),
        "status_breakdown": status_counts,
        "ab_testing": ab_testing_data,
    }
