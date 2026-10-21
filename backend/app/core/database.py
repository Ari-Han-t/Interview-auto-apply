from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

connect_args = {"check_same_thread": False, "timeout": 30} if "sqlite" in settings.DATABASE_URL else {}

engine = create_engine(
    settings.DATABASE_URL, 
    connect_args=connect_args
)

if "sqlite" in settings.DATABASE_URL:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()

_CONTENT_AUTO_MIGRATIONS = [
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
    ("candidate_educations", "gpa_scale", "VARCHAR DEFAULT '4.0'"),
    ("candidate_educations", "honors", "VARCHAR"),
    ("candidate_educations", "bullets", "JSON"),
    ("candidate_educations", "is_archived", "BOOLEAN DEFAULT 0"),
    ("candidate_educations", "verification_status", "VARCHAR DEFAULT 'self_attested'"),
    ("candidate_educations", "evidence_url", "VARCHAR"),
    ("candidate_educations", "created_at", "TIMESTAMP"),
    ("candidate_educations", "updated_at", "TIMESTAMP"),
    ("candidate_experiences", "location", "VARCHAR"),
    ("candidate_experiences", "technologies", "JSON"),
    ("candidate_experiences", "highlights", "JSON"),
    ("candidate_experiences", "is_visible", "BOOLEAN DEFAULT 1"),
    ("candidate_experiences", "experience_type", "VARCHAR DEFAULT 'employment'"),
    ("candidate_experiences", "responsibilities", "TEXT"),
    ("candidate_experiences", "contributions", "TEXT"),
    ("candidate_experiences", "metrics", "TEXT"),
    ("candidate_experiences", "bullets", "JSON"),
    ("candidate_experiences", "is_archived", "BOOLEAN DEFAULT 0"),
    ("candidate_experiences", "verification_status", "VARCHAR DEFAULT 'self_attested'"),
    ("candidate_experiences", "evidence_url", "VARCHAR"),
    ("candidate_experiences", "created_at", "TIMESTAMP"),
    ("candidate_experiences", "updated_at", "TIMESTAMP"),
    ("candidate_projects", "role", "VARCHAR"),
    ("candidate_projects", "start_date", "VARCHAR"),
    ("candidate_projects", "end_date", "VARCHAR"),
    ("candidate_projects", "highlights", "JSON"),
    ("candidate_projects", "is_visible", "BOOLEAN DEFAULT 1"),
    ("candidate_projects", "problem", "TEXT"),
    ("candidate_projects", "personal_contribution", "TEXT"),
    ("candidate_projects", "implementation", "TEXT"),
    ("candidate_projects", "programming_languages", "JSON"),
    ("candidate_projects", "frameworks", "JSON"),
    ("candidate_projects", "libraries", "JSON"),
    ("candidate_projects", "databases", "JSON"),
    ("candidate_projects", "apis", "JSON"),
    ("candidate_projects", "ai_ml_techniques", "JSON"),
    ("candidate_projects", "deployment_technologies", "JSON"),
    ("candidate_projects", "technical_challenges", "TEXT"),
    ("candidate_projects", "verified_outcomes", "JSON"),
    ("candidate_projects", "supporting_evidence", "TEXT"),
    ("candidate_projects", "evidence_url", "VARCHAR"),
    ("candidate_projects", "bullets", "JSON"),
    ("candidate_projects", "is_archived", "BOOLEAN DEFAULT 0"),
    ("candidate_projects", "verification_status", "VARCHAR DEFAULT 'self_attested'"),
    ("candidate_projects", "created_at", "TIMESTAMP"),
    ("candidate_projects", "updated_at", "TIMESTAMP"),
    ("user_skills", "category", "VARCHAR DEFAULT 'General'"),
    ("user_skills", "proficiency_level", "VARCHAR DEFAULT 'Advanced'"),
    ("user_skills", "verification_status", "VARCHAR DEFAULT 'self_attested'"),
    ("user_skills", "evidence_url", "VARCHAR"),
    ("user_skills", "notes", "TEXT"),
    ("user_skills", "is_visible", "BOOLEAN DEFAULT 1"),
    ("user_skills", "is_archived", "BOOLEAN DEFAULT 0"),
    ("candidate_achievements", "url", "VARCHAR"),
    ("candidate_achievements", "impact_metrics", "TEXT"),
    ("candidate_achievements", "bullets", "JSON"),
    ("candidate_achievements", "evidence_url", "VARCHAR"),
    ("candidate_achievements", "verification_status", "VARCHAR DEFAULT 'self_attested'"),
    ("candidate_achievements", "is_visible", "BOOLEAN DEFAULT 1"),
    ("candidate_achievements", "is_archived", "BOOLEAN DEFAULT 0"),
    ("candidate_achievements", "created_at", "TIMESTAMP"),
    ("candidate_achievements", "updated_at", "TIMESTAMP"),
    ("candidate_courses", "credential_id", "VARCHAR"),
    ("candidate_courses", "expiry_date", "VARCHAR"),
    ("candidate_courses", "bullets", "JSON"),
    ("candidate_courses", "evidence_url", "VARCHAR"),
    ("candidate_courses", "verification_status", "VARCHAR DEFAULT 'self_attested'"),
    ("candidate_courses", "is_visible", "BOOLEAN DEFAULT 1"),
    ("candidate_courses", "is_archived", "BOOLEAN DEFAULT 0"),
    ("candidate_courses", "created_at", "TIMESTAMP"),
    ("candidate_courses", "updated_at", "TIMESTAMP"),
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
    ("jobs", "application_url", "VARCHAR"),
    ("jobs", "responsibilities_json", "JSON"),
    ("jobs", "required_skills_json", "JSON"),
    ("jobs", "preferred_skills_json", "JSON"),
    ("jobs", "eligibility_criteria_json", "JSON"),
    ("jobs", "graduation_restrictions", "JSON"),
    ("jobs", "work_arrangement", "VARCHAR DEFAULT 'onsite'"),
    ("jobs", "employment_type", "VARCHAR DEFAULT 'fulltime'"),
    ("jobs", "compensation_min", "REAL"),
    ("jobs", "compensation_max", "REAL"),
    ("jobs", "currency", "VARCHAR DEFAULT 'USD'"),
    ("jobs", "compensation_interval", "VARCHAR"),
    ("jobs", "source_job_id", "VARCHAR"),
    ("jobs", "source_provenance", "JSON"),
    ("jobs", "last_verified_at", "TIMESTAMP"),
    ("jobs", "is_expired", "BOOLEAN DEFAULT 0"),
    ("jobs", "expired_at", "TIMESTAMP"),
    ("jobs", "dedup_hash", "VARCHAR"),
    ("jobs", "updated_at", "TIMESTAMP"),
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

def run_auto_migrations(target_engine):
    try:
        from app.models.base import Base
        Base.metadata.create_all(bind=target_engine)
        insp = inspect(target_engine)
        existing_tables = set(insp.get_table_names())
        with target_engine.connect() as conn:
            for table, column, col_type in _CONTENT_AUTO_MIGRATIONS:
                if table not in existing_tables:
                    continue
                cols = [c["name"] for c in insp.get_columns(table)]
                if column not in cols:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
            conn.commit()
    except Exception:
        pass

if "sqlite" in settings.DATABASE_URL and ":memory:" not in settings.DATABASE_URL:
    try:
        run_auto_migrations(engine)
    except Exception:
        pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

