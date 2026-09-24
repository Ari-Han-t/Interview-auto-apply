from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, profile, jobs, applications, analytics, resume, github, cover_letters, notifications

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001"
    ],
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


@app.get("/")
def read_root():
    return {"message": "Welcome to Interview AutoApply API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
