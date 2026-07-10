from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, profile, jobs, applications, analytics, resume

app = FastAPI(
    title="Interview AutoApply API",
    description="Autonomous recruiting assistant backend.",
    version="1.0.0"
)

from app.core.database import engine
from app.models import Base
Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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


@app.get("/")
def read_root():
    return {"message": "Welcome to Interview AutoApply API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
