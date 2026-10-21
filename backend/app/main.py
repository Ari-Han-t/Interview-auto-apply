from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, profile, jobs, applications, analytics, resume, github, cover_letters, notifications, content_library, modular_resume, company_research, interview_prep

app = FastAPI(
    title="Interview AutoApply API",
    description="Autonomous recruiting assistant backend.",
    version="1.0.0"
)

from app.core.database import engine
from app.models import Base
from sqlalchemy import inspect, text

Base.metadata.create_all(bind=engine)

# Auto-migrate SQLite columns if missing
_AUTO_MIGRATIONS = [
    ("job_requirements", "company_size", "VARCHAR"),
    ("profiles", "github_synced_at", "TIMESTAMP"),
    ("profiles", "tailoring_instructions", "TEXT"),
    ("applications", "user_instructions", "TEXT"),
    ("user_profiles", "preferred_name", "VARCHAR"),
    ("user_profiles", "website", "VARCHAR"),
    ("user_profiles", "specialization", "VARCHAR"),
    ("user_profiles", "coursework", "JSON"),
    ("user_profiles", "current_semester_or_year", "VARCHAR"),
    ("user_profiles", "bio", "TEXT"),
    ("user_profiles", "availability", "VARCHAR"),
    ("candidate_experiences", "location", "VARCHAR"),
    ("candidate_experiences", "technologies", "JSON"),
    ("candidate_experiences", "highlights", "JSON"),
    ("candidate_experiences", "is_visible", "BOOLEAN DEFAULT 1"),
    ("candidate_projects", "role", "VARCHAR"),
    ("candidate_projects", "start_date", "VARCHAR"),
    ("candidate_projects", "end_date", "VARCHAR"),
    ("candidate_projects", "highlights", "JSON"),
    ("candidate_projects", "is_visible", "BOOLEAN DEFAULT 1"),
    ("user_skills", "category", "VARCHAR DEFAULT 'General'"),
    ("user_skills", "is_visible", "BOOLEAN DEFAULT 1"),
    ("candidate_achievements", "url", "VARCHAR"),
    ("candidate_achievements", "is_visible", "BOOLEAN DEFAULT 1"),
    ("candidate_courses", "credential_id", "VARCHAR"),
    ("candidate_courses", "expiry_date", "VARCHAR"),
    ("candidate_courses", "is_visible", "BOOLEAN DEFAULT 1"),
    ("user_preferences", "availability_duration", "VARCHAR"),
    ("resume_versions", "is_master", "BOOLEAN DEFAULT 0"),
    ("resume_versions", "target_role", "VARCHAR"),
    ("resume_versions", "version_number", "INTEGER DEFAULT 1"),
    ("resume_versions", "latex_source", "TEXT"),
    ("resume_versions", "notes", "TEXT"),
    ("resume_versions", "selected_projects", "JSON"),
    ("resume_versions", "selected_experiences", "JSON"),
    ("resume_versions", "selected_bullets", "JSON"),
    ("resume_versions", "job_id", "INTEGER"),
    ("resume_versions", "application_id", "INTEGER"),
    ("resume_versions", "assembly_plan", "JSON"),
    ("resume_versions", "template_name", "VARCHAR DEFAULT 'clean_ats'"),
    ("resume_versions", "template_options", "JSON"),
    ("resume_versions", "parent_version_id", "INTEGER"),
    ("resume_versions", "updated_at", "TIMESTAMP"),
    ("cover_letters", "style", "VARCHAR DEFAULT 'concise'"),
    ("cover_letters", "candidate_motivation", "TEXT"),
    ("cover_letters", "selected_projects", "JSON"),
    ("cover_letters", "selected_experiences", "JSON"),
    ("cover_letters", "selected_achievements", "JSON"),
    ("cover_letters", "version_number", "INTEGER DEFAULT 1"),
    ("cover_letters", "is_approved", "BOOLEAN DEFAULT 0"),
    ("cover_letters", "approved_at", "TIMESTAMP"),
    ("cover_letters", "parent_version_id", "INTEGER"),
    ("cover_letters", "application_id", "INTEGER"),
    ("cover_letters", "sources_used", "JSON"),
    ("cover_letters", "updated_at", "TIMESTAMP"),
    ("applications", "source", "VARCHAR"),
    ("applications", "submission_confirmed", "BOOLEAN DEFAULT 0"),
    ("applications", "resume_version_id", "INTEGER"),
    ("applications", "cover_letter_id", "INTEGER"),
    ("applications", "submitted_resume_snapshot", "TEXT"),
    ("applications", "submitted_cover_letter_snapshot", "TEXT"),
    ("applications", "match_report", "JSON"),
    ("applications", "assessment_deadline", "TIMESTAMP"),
    ("applications", "assessment_notes", "TEXT"),
    ("applications", "interview_date", "TIMESTAMP"),
    ("applications", "interview_round", "VARCHAR"),
    ("applications", "interview_notes", "TEXT"),
    ("applications", "notes", "TEXT"),
    ("applications", "follow_ups", "JSON"),
    ("applications", "reminders", "JSON"),
    ("applications", "outcome", "VARCHAR"),
    ("applications", "outcome_notes", "TEXT"),
    ("applications", "offer_compensation", "VARCHAR"),
    ("applications", "updated_at", "TIMESTAMP"),
]
try:
    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())
    with engine.connect() as conn:
        for table, column, col_type in _AUTO_MIGRATIONS:
            if table not in existing_tables:
                continue
            cols = [c["name"] for c in insp.get_columns(table)]
            if column not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
        conn.commit()
except Exception as _mig_err:
    pass

from app.core.config import settings

cors_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://127.0.0.1:3002",
    "http://localhost:8000",
    "http://localhost:8001",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8001",
]
if settings.CORS_ORIGINS:
    for o in settings.CORS_ORIGINS.split(","):
        if o.strip():
            cors_origins.append(o.strip())

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=settings.ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["profile"])
app.include_router(resume.router, prefix="/api/v1/resume", tags=["resume"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(applications.router, prefix="/api/v1/applications", tags=["applications"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(github.router, prefix="/api/v1/github", tags=["github"])
app.include_router(cover_letters.router, prefix="/api/v1/cover_letters", tags=["cover_letters"])
app.include_router(cover_letters.router, prefix="/api/v1/cover-letters", tags=["cover-letters"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(content_library.router, prefix="/api/v1/content-library", tags=["content-library"])
app.include_router(modular_resume.router, prefix="/api/v1/modular-resume", tags=["modular-resume"])
app.include_router(company_research.router, prefix="/api/v1/company-research", tags=["company-research"])
app.include_router(interview_prep.router, prefix="/api/v1/interview-prep", tags=["interview-prep"])


@app.get("/")
def read_root():
    return {"message": "Welcome to Interview AutoApply API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
