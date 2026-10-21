from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from collections import Counter
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func, desc

from app.core.database import get_db
from app.models.user import User
from app.models.job import Job, UserSavedJob
from app.models.application import Application
from app.models.candidate import UserProfile, CandidateExperience, Project, UserPreference
from app.models.resume import ResumeVersion
from app.api.auth import get_current_user

router = APIRouter()

CANONICAL_CRM_STATUSES = [
    "Discovered",
    "Saved",
    "Shortlisted",
    "Preparing",
    "Ready to Apply",
    "Applied",
    "Assessment Received",
    "Interview Scheduled",
    "Interview Completed",
    "Offer Received",
    "Rejected",
    "Withdrawn",
    "Position Closed",
]

def _normalize_crm_status(raw: Optional[str]) -> str:
    if not raw:
        return "Preparing"
    val = raw.strip()
    mapping = {
        "applied": "Applied",
        "submitted": "Applied",
        "interview": "Interview Scheduled",
        "interviewing": "Interview Scheduled",
        "interview scheduled": "Interview Scheduled",
        "interview completed": "Interview Completed",
        "assessment": "Assessment Received",
        "assessment received": "Assessment Received",
        "offer": "Offer Received",
        "offer received": "Offer Received",
        "rejected": "Rejected",
        "withdrawn": "Withdrawn",
        "saved": "Saved",
        "discovered": "Discovered",
        "shortlisted": "Shortlisted",
        "preparing": "Preparing",
        "ready to apply": "Ready to Apply",
        "ready_to_apply": "Ready to Apply",
        "position closed": "Position Closed",
        "position_closed": "Position Closed",
        "closed": "Position Closed",
    }
    low = val.lower()
    return mapping.get(low, val)

def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

@router.get("/dashboard")
def get_dashboard_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns verified, database-backed metrics for the primary Dashboard.
    Includes:
    - New opportunities discovered
    - Strongly matching jobs
    - Saved jobs
    - Applications submitted
    - Interviews scheduled
    - Assessments due
    - Follow-ups due
    - Offers and rejections
    - Onboarding readiness status & next action
    - Upcoming critical dates
    - Recent applications
    """
    now_utc = datetime.now(timezone.utc)
    seven_days_ago = now_utc - timedelta(days=7)
    fourteen_days_ahead = now_utc + timedelta(days=14)

    # 1. Opportunities & Job Discovery counts
    total_jobs = db.query(Job).count()
    new_jobs_count = db.query(Job).filter(
        (Job.created_at >= seven_days_ago) | (Job.posted_at >= seven_days_ago)
    ).count()

    # Match scores / eligibility
    jobs = db.query(Job).all()
    strongly_matching_count = sum(
        1 for j in jobs if (getattr(j, "is_eligible", False) is True) or ((j.requirements_json or {}).get("match_score", 0) >= 75)
    )

    # Saved jobs count (via UserSavedJob or Saved/Shortlisted applications)
    saved_via_table = db.query(UserSavedJob).filter(UserSavedJob.user_id == current_user.id).count()
    saved_applications_count = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.status.in_(["Saved", "Shortlisted", "saved", "shortlisted"])
    ).count()
    saved_jobs_count = max(saved_via_table, saved_applications_count)

    # 2. Applications & CRM metrics
    apps = db.query(Application, Job).join(Job, Application.job_id == Job.id).filter(
        Application.user_id == current_user.id
    ).all()

    submitted_count = 0
    interviews_scheduled_count = 0
    assessments_due_count = 0
    followups_due_count = 0
    offers_count = 0
    rejections_count = 0
    upcoming_events = []
    recent_applications = []

    submitted_statuses = {
        "Applied", "Assessment Received", "Interview Scheduled",
        "Interview Completed", "Offer Received", "Rejected", "Withdrawn", "Position Closed"
    }

    for app, job in apps:
        norm_status = _normalize_crm_status(app.status)
        int_dt = _to_utc(app.interview_date)
        ass_dt = _to_utc(app.assessment_deadline)

        if norm_status in submitted_statuses or app.submission_confirmed:
            submitted_count += 1

        if norm_status == "Interview Scheduled" or (int_dt and int_dt >= now_utc):
            interviews_scheduled_count += 1

        if norm_status == "Assessment Received" or (ass_dt and ass_dt >= now_utc):
            assessments_due_count += 1

        if norm_status == "Offer Received":
            offers_count += 1

        if norm_status == "Rejected":
            rejections_count += 1

        # Check follow-ups
        if app.follow_ups:
            for fu in app.follow_ups:
                if not fu.get("completed"):
                    followups_due_count += 1

        # Collect upcoming events in next 14 days
        if int_dt and int_dt >= now_utc and int_dt <= fourteen_days_ahead:
            upcoming_events.append({
                "type": "interview",
                "title": f"Interview: {job.company}",
                "subtitle": f"{job.title} ({app.interview_round or 'Technical'})",
                "date": int_dt.isoformat(),
                "application_id": app.id,
                "job_id": job.id,
            })

        if ass_dt and ass_dt >= now_utc and ass_dt <= fourteen_days_ahead:
            upcoming_events.append({
                "type": "assessment",
                "title": f"Assessment Due: {job.company}",
                "subtitle": f"{job.title}",
                "date": ass_dt.isoformat(),
                "application_id": app.id,
                "job_id": job.id,
            })

    # Sort upcoming events chronologically
    upcoming_events.sort(key=lambda x: x["date"])

    # Recent 5 applications
    def _sort_key(pair):
        a = pair[0]
        dt = _to_utc(a.applied_at) or _to_utc(a.updated_at) or _to_utc(a.created_at)
        return dt or datetime.min.replace(tzinfo=timezone.utc)

    sorted_apps = sorted(apps, key=_sort_key, reverse=True)
    for app, job in sorted_apps[:5]:
        recent_applications.append({
            "id": app.id,
            "job_id": job.id,
            "company": job.company,
            "role": job.title,
            "status": _normalize_crm_status(app.status),
            "applied_at": app.applied_at.isoformat() if app.applied_at else None,
            "updated_at": app.updated_at.isoformat() if app.updated_at else None,
            "source": app.source or job.source or "Direct",
            "submission_confirmed": bool(app.submission_confirmed),
        })

    # 3. Onboarding Readiness Assessment
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    experiences_count = db.query(CandidateExperience).filter(CandidateExperience.user_id == current_user.id).count()
    projects_count = db.query(Project).filter(Project.user_id == current_user.id).count()
    resumes_count = db.query(ResumeVersion).filter(ResumeVersion.user_id == current_user.id).count()
    preferences = db.query(UserPreference).filter(UserPreference.user_id == current_user.id).first()

    has_profile = bool(profile and (profile.full_name or profile.email))
    has_experience = experiences_count > 0
    has_projects = projects_count > 0
    has_resume = resumes_count > 0
    has_preferences = bool(preferences and (preferences.preferred_roles or preferences.preferred_locations))
    has_jobs_discovered = total_jobs > 0

    readiness_checks = [
        has_profile,
        has_experience,
        has_projects,
        has_resume,
        has_preferences,
        has_jobs_discovered,
    ]
    readiness_percentage = int((sum(1 for c in readiness_checks if c) / len(readiness_checks)) * 100)

    # Contextual next recommended action
    if not has_resume:
        next_action = "Upload your master resume in Career Profile to enable automated bullet extraction and instant tailoring."
        next_action_link = "/profile"
    elif not has_preferences:
        next_action = "Configure your target job titles and preferred locations in Settings to calibrate role matching."
        next_action_link = "/settings"
    elif not has_jobs_discovered:
        next_action = "Explore the Job Feed to discover opportunities matching your background."
        next_action_link = "/jobs"
    elif submitted_count == 0:
        next_action = "Select a high-match role and prepare your first tailored application in Discover Jobs."
        next_action_link = "/jobs"
    elif followups_due_count > 0:
        next_action = f"You have {followups_due_count} pending follow-up action(s) to review in your Application CRM."
        next_action_link = "/applications"
    elif interviews_scheduled_count > 0:
        next_action = f"You have {interviews_scheduled_count} interview(s) scheduled. Practice role-specific questions in Interview Prep."
        next_action_link = "/interview-prep"
    else:
        next_action = "Your pipeline is healthy. Monitor new matching postings or optimize your modular resume variants."
        next_action_link = "/jobs"

    return {
        "metrics": {
            "new_opportunities": new_jobs_count,
            "total_jobs_tracked": total_jobs,
            "strongly_matching": strongly_matching_count,
            "saved_jobs": saved_jobs_count,
            "applications_submitted": submitted_count,
            "submitted_applications": submitted_count,
            "interviews_scheduled": interviews_scheduled_count,
            "assessments_due": assessments_due_count,
            "followups_due": followups_due_count,
            "offers_received": offers_count,
            "rejections": rejections_count,
        },
        "onboarding": {
            "readiness_percentage": readiness_percentage,
            "has_profile": has_profile,
            "has_experience": has_experience,
            "has_projects": has_projects,
            "has_resume": has_resume,
            "has_preferences": has_preferences,
            "has_jobs_discovered": has_jobs_discovered,
            "next_recommended_action": next_action,
            "next_recommended_link": next_action_link,
        },
        "upcoming_events": upcoming_events,
        "recent_applications": recent_applications,
    }


@router.get("/overview")
def get_analytics_overview(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns database-backed career analytics including:
    - Application pipeline distribution across canonical statuses
    - Weekly application activity (8 weeks)
    - Conversion rates with explicit denominators & sample size caveats
    - Response time distribution
    - Match-score distribution
    - Frequently requested technologies
    - Outcomes by job source
    - Resume-version performance
    - Actionable insights
    """
    now_utc = datetime.now(timezone.utc)

    # 1. Pipeline Status Breakdown
    all_user_apps = db.query(Application, Job).join(Job, Application.job_id == Job.id).filter(
        Application.user_id == current_user.id
    ).all()

    total_apps_count = len(all_user_apps)
    pipeline_counts = {status: 0 for status in CANONICAL_CRM_STATUSES}

    for app, _ in all_user_apps:
        norm = _normalize_crm_status(app.status)
        if norm in pipeline_counts:
            pipeline_counts[norm] += 1
        else:
            pipeline_counts["Preparing"] += 1

    pipeline_distribution = [
        {
            "status": status,
            "count": count,
            "percentage": round((count / total_apps_count * 100), 1) if total_apps_count > 0 else 0.0,
        }
        for status, count in pipeline_counts.items()
    ]

    # 2. Submitted Applications & Funnels
    submitted_statuses = {
        "Applied", "Assessment Received", "Interview Scheduled",
        "Interview Completed", "Offer Received", "Rejected", "Withdrawn", "Position Closed"
    }

    submitted_apps = [
        (app, job) for (app, job) in all_user_apps
        if _normalize_crm_status(app.status) in submitted_statuses or app.submission_confirmed
    ]
    submitted_count = len(submitted_apps)

    interview_apps = [
        (app, job) for (app, job) in submitted_apps
        if _normalize_crm_status(app.status) in ["Interview Scheduled", "Interview Completed", "Offer Received"] or app.interview_date
    ]
    interview_count = len(interview_apps)

    offer_apps = [
        (app, job) for (app, job) in submitted_apps
        if _normalize_crm_status(app.status) == "Offer Received"
    ]
    offer_count = len(offer_apps)

    assessment_apps = [
        (app, job) for (app, job) in submitted_apps
        if _normalize_crm_status(app.status) in ["Assessment Received", "Interview Scheduled", "Interview Completed", "Offer Received"] or app.assessment_deadline
    ]
    assessment_count = len(assessment_apps)

    rejection_apps = [
        (app, job) for (app, job) in submitted_apps
        if _normalize_crm_status(app.status) == "Rejected"
    ]
    rejection_count = len(rejection_apps)

    # 3. Conversion Rates with Denominators & Statistical Caveats
    sample_size_threshold = 10
    is_small_sample = submitted_count < sample_size_threshold

    conversion_rates = {
        "interview_rate": {
            "count": interview_count,
            "denominator": submitted_count,
            "percentage": round((interview_count / submitted_count * 100), 1) if submitted_count > 0 else 0.0,
            "label": f"{interview_count} of {submitted_count} submitted",
            "is_small_sample": is_small_sample,
            "caveat": "Sample size below 10: rate should be interpreted as directional preliminary data." if is_small_sample else None,
        },
        "offer_rate": {
            "count": offer_count,
            "denominator": submitted_count,
            "percentage": round((offer_count / submitted_count * 100), 1) if submitted_count > 0 else 0.0,
            "label": f"{offer_count} of {submitted_count} submitted",
            "is_small_sample": is_small_sample,
            "caveat": "Small sample size. Meaningful offer conversion metrics stabilize over 20+ applications." if is_small_sample else None,
        },
        "assessment_rate": {
            "count": assessment_count,
            "denominator": submitted_count,
            "percentage": round((assessment_count / submitted_count * 100), 1) if submitted_count > 0 else 0.0,
            "label": f"{assessment_count} of {submitted_count} submitted",
            "is_small_sample": is_small_sample,
            "caveat": None,
        },
    }

    # 4. Weekly Application Activity (Past 8 Weeks)
    weekly_activity = []
    for week_idx in range(7, -1, -1):
        start_of_week = now_utc - timedelta(days=(week_idx + 1) * 7)
        end_of_week = now_utc - timedelta(days=week_idx * 7)

        count = sum(
            1 for (app, _) in submitted_apps
            if _to_utc(app.applied_at) and (_to_utc(app.applied_at) >= start_of_week) and (_to_utc(app.applied_at) < end_of_week)
        )
        label = start_of_week.strftime("%b %d")
        weekly_activity.append({
            "week_label": label,
            "count": count,
            "start_date": start_of_week.isoformat(),
        })

    # 5. Application Response Times
    response_durations_days = []
    for app, _ in submitted_apps:
        app_applied = _to_utc(app.applied_at)
        if app_applied:
            earliest_response = None
            int_dt = _to_utc(app.interview_date)
            upd_dt = _to_utc(app.updated_at)
            if int_dt and int_dt > app_applied:
                earliest_response = int_dt
            elif _normalize_crm_status(app.status) in ["Assessment Received", "Interview Scheduled", "Offer Received", "Rejected"]:
                if upd_dt and upd_dt > app_applied:
                    earliest_response = upd_dt

            if earliest_response:
                diff_days = (earliest_response - app_applied).total_seconds() / 86400.0
                if diff_days >= 0:
                    response_durations_days.append(round(diff_days, 1))

    if len(response_durations_days) >= 3:
        avg_days = round(sum(response_durations_days) / len(response_durations_days), 1)
        sorted_days = sorted(response_durations_days)
        median_days = sorted_days[len(sorted_days) // 2]
        response_time_stats = {
            "has_enough_data": True,
            "observations_count": len(response_durations_days),
            "average_days": avg_days,
            "median_days": median_days,
            "min_days": min(response_durations_days),
            "max_days": max(response_durations_days),
            "notice": f"Calculated across {len(response_durations_days)} recorded employer responses.",
        }
    else:
        response_time_stats = {
            "has_enough_data": False,
            "observations_count": len(response_durations_days),
            "average_days": None,
            "median_days": None,
            "min_days": None,
            "max_days": None,
            "notice": f"Insufficient data: at least 3 employer responses required (currently {len(response_durations_days)} observed).",
        }

    # 6. Match-Score Distribution
    # Bracket counts for all jobs vs applied jobs
    match_brackets = {
        "90-100%": {"discovered": 0, "applied": 0},
        "75-89%": {"discovered": 0, "applied": 0},
        "60-74%": {"discovered": 0, "applied": 0},
        "<60%": {"discovered": 0, "applied": 0},
    }

    all_jobs = db.query(Job).all()
    for j in all_jobs:
        score = (j.requirements_json or {}).get("match_score") or (85 if getattr(j, "is_eligible", False) else 50)
        if score >= 90:
            match_brackets["90-100%"]["discovered"] += 1
        elif score >= 75:
            match_brackets["75-89%"]["discovered"] += 1
        elif score >= 60:
            match_brackets["60-74%"]["discovered"] += 1
        else:
            match_brackets["<60%"]["discovered"] += 1

    for app, job in submitted_apps:
        score = (app.match_report or {}).get("overall_score") or (job.requirements_json or {}).get("match_score") or 70
        if score >= 90:
            match_brackets["90-100%"]["applied"] += 1
        elif score >= 75:
            match_brackets["75-89%"]["applied"] += 1
        elif score >= 60:
            match_brackets["60-74%"]["applied"] += 1
        else:
            match_brackets["<60%"]["applied"] += 1

    # 7. Frequently Requested Technologies across tracked roles
    tech_counter = Counter()
    for _, job in all_user_apps:
        req_skills = job.required_skills_json or []
        tech_stack = job.tech_stack_json or []
        for s in (req_skills + tech_stack):
            if isinstance(s, str) and len(s) > 1:
                tech_counter[s.strip()] += 1

    # Fallback to general jobs if user hasn't tracked many
    if len(tech_counter) < 5:
        for j in all_jobs[:30]:
            for s in (j.required_skills_json or []) + (j.tech_stack_json or []):
                if isinstance(s, str) and len(s) > 1:
                    tech_counter[s.strip()] += 1

    top_technologies = [
        {"technology": tech, "frequency": count}
        for tech, count in tech_counter.most_common(10)
    ]

    # 8. Outcomes by Job Source
    source_stats_map = {}
    for app, job in submitted_apps:
        src = (app.source or job.source or "Direct / Other").strip().title()
        if src not in source_stats_map:
            source_stats_map[src] = {"applied": 0, "interviews": 0, "offers": 0}
        source_stats_map[src]["applied"] += 1
        if _normalize_crm_status(app.status) in ["Interview Scheduled", "Interview Completed", "Offer Received"] or app.interview_date:
            source_stats_map[src]["interviews"] += 1
        if _normalize_crm_status(app.status) == "Offer Received":
            source_stats_map[src]["offers"] += 1

    outcomes_by_source = []
    for src, counts in source_stats_map.items():
        applied_n = counts["applied"]
        rate = round((counts["interviews"] / applied_n * 100), 1) if applied_n > 0 else 0.0
        outcomes_by_source.append({
            "source": src,
            "applied": applied_n,
            "interviews": counts["interviews"],
            "offers": counts["offers"],
            "interview_rate": rate,
            "sample_warning": "Sample size < 5" if applied_n < 5 else None,
        })
    outcomes_by_source.sort(key=lambda x: x["applied"], reverse=True)

    # 9. Resume Version Performance
    resume_stats_map = {}
    resume_versions = {r.id: r.name for r in db.query(ResumeVersion).filter(ResumeVersion.user_id == current_user.id).all()}

    for app, _ in submitted_apps:
        v_id = app.resume_version_id
        v_name = resume_versions.get(v_id, f"Resume #{v_id}" if v_id else "Default / Unversioned")
        if v_name not in resume_stats_map:
            resume_stats_map[v_name] = {"applied": 0, "interviews": 0, "offers": 0}
        resume_stats_map[v_name]["applied"] += 1
        if _normalize_crm_status(app.status) in ["Interview Scheduled", "Interview Completed", "Offer Received"] or app.interview_date:
            resume_stats_map[v_name]["interviews"] += 1
        if _normalize_crm_status(app.status) == "Offer Received":
            resume_stats_map[v_name]["offers"] += 1

    resume_performance = []
    for v_name, counts in resume_stats_map.items():
        applied_n = counts["applied"]
        rate = round((counts["interviews"] / applied_n * 100), 1) if applied_n > 0 else 0.0
        resume_performance.append({
            "version_name": v_name,
            "applied": applied_n,
            "interviews": counts["interviews"],
            "offers": counts["offers"],
            "interview_rate": rate,
            "is_statistically_adequate": applied_n >= 15,
            "sample_warning": "Small variant sample size (< 15 observations): correlation only, does not imply statistical causation." if applied_n < 15 else None,
        })
    resume_performance.sort(key=lambda x: x["applied"], reverse=True)

    # 10. Objective Actionable Insights (Non-speculative)
    insights = []
    if submitted_count == 0:
        insights.append({
            "type": "opportunity",
            "title": "Initial Pipeline Launch",
            "description": "No applications have been marked as submitted yet. Focus on targeting 3-5 strongly matching roles to start recording response dynamics.",
        })
    else:
        if interview_count > 0:
            top_src = outcomes_by_source[0]["source"] if outcomes_by_source else "Direct"
            insights.append({
                "type": "strength",
                "title": f"Active Interview Conversion ({conversion_rates['interview_rate']['percentage']}%)",
                "description": f"You have achieved {interview_count} interview invites across {submitted_count} submitted applications. Sourcing from {top_src} shows the highest volume in your pipeline.",
            })

        if match_brackets["75-89%"]["applied"] + match_brackets["90-100%"]["applied"] > 0:
            high_match_pct = round(((match_brackets["75-89%"]["applied"] + match_brackets["90-100%"]["applied"]) / submitted_count * 100), 1)
            insights.append({
                "type": "targeting",
                "title": "Profile Alignment Rigor",
                "description": f"{high_match_pct}% of your submitted applications target positions where your skills meet or exceed 75% match threshold.",
            })

        if is_small_sample:
            insights.append({
                "type": "methodology",
                "title": "Statistical Sample Size Note",
                "description": "Your current pipeline has fewer than 10 submitted applications. Individual stage conversion rates will fluctuate until a larger observation sample is recorded.",
            })

    insights.append({
        "type": "compliance",
        "title": "Transparent Analytics Notice",
        "description": "All analytics represent verified activity in your database. Internal hiring decisions depend on private organizational budgets and team priorities that external tools cannot measure.",
    })

    return {
        "summary": {
            "total_applications": total_apps_count,
            "submitted_applications": submitted_count,
            "interviews_scheduled": interview_count,
            "offers_received": offer_count,
            "assessments_received": assessment_count,
            "rejections": rejection_count,
        },
        "pipeline_distribution": pipeline_distribution,
        "weekly_activity": weekly_activity,
        "conversion_rates": conversion_rates,
        "response_time_stats": response_time_stats,
        "match_brackets": match_brackets,
        "top_technologies": top_technologies,
        "outcomes_by_source": outcomes_by_source,
        "resume_performance": resume_performance,
        "actionable_insights": insights,
    }
