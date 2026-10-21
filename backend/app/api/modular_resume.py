import os
import uuid
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Body
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.job import Job
from app.models.application import Application
from app.models.resume import ResumeVersion
from app.api.auth import get_current_user

from app.services.resume_compiler.candidate_data import load_candidate_library, MODULE_KEYS, MODULE_DISPLAY_NAMES
from app.services.resume_compiler.templates import list_templates, get_template
from app.services.resume_compiler.assembly_engine import generate_assembly_plan
from app.services.resume_compiler.refiner import refine_bullet_truthfully, compute_text_diff
from app.services.resume_compiler.renderer import render_modular_resume
from app.services.resume_compiler.compiler import compile_latex_securely, extract_and_validate_pdf_readability, create_source_archive
from app.services.resume_compiler.version_service import save_immutable_resume_version, compare_resume_versions

router = APIRouter()

# -------------------------------------------------------------
# Request Schemas
# -------------------------------------------------------------

class PlanRequest(BaseModel):
    user_locks: Optional[Dict[str, Any]] = None
    custom_instructions: Optional[str] = None
    target_page_length: Optional[int] = 1


class RefineBulletRequest(BaseModel):
    original_bullet: str
    job_requirement: str
    job_title: str
    context_name: Optional[str] = None
    custom_instructions: Optional[str] = None


class RenderRequest(BaseModel):
    assembly_plan: Dict[str, Any]
    template_name: Optional[str] = "clean_ats"
    template_options: Optional[Dict[str, Any]] = None


class CompileRequest(BaseModel):
    latex_source: str
    job_id: Optional[int] = None


class SaveVersionRequest(BaseModel):
    job_id: Optional[int] = None
    application_id: Optional[int] = None
    name: Optional[str] = None
    latex_source: str
    assembly_plan: Dict[str, Any]
    template_name: Optional[str] = "clean_ats"
    template_options: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    parent_version_id: Optional[int] = None


# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------

@router.get("/candidate-modules")
def get_candidate_modules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves all 11 selectable modules of candidate data from the Content Library.
    """
    library = load_candidate_library(current_user.id, db)
    return {
        "candidate_data": library,
        "module_keys": MODULE_KEYS,
        "module_display_names": MODULE_DISPLAY_NAMES
    }


@router.get("/templates")
def get_available_templates():
    """
    Returns the 5 reusable ATS-compliant resume templates.
    """
    return list_templates()


@router.post("/plan/{job_id}")
def create_assembly_plan(
    job_id: int,
    request: Optional[PlanRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyzes job requirements and generates a structured AI resume assembly plan.
    Ranks modules, records, and individual bullets. Proposes truth-preserving refinements.
    Respects all user-locked choices.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job opening not found")

    candidate_data = load_candidate_library(current_user.id, db)

    job_dict = {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "description": job.description or "",
        "required_skills_json": job.required_skills_json or [],
        "tech_stack_json": job.tech_stack_json or [],
    }

    user_locks = request.user_locks if request else None
    custom_instructions = request.custom_instructions if request else None
    target_page_length = request.target_page_length if request else 1

    plan = generate_assembly_plan(
        candidate_data=candidate_data,
        job=job_dict,
        user_locks=user_locks,
        custom_instructions=custom_instructions,
        target_page_length=target_page_length,
    )

    return plan


@router.post("/refine-bullet")
def refine_single_bullet(
    request: RefineBulletRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Performs truth-preserving refinement on a single bullet point.
    Explains the motivating job requirement and returns word-by-word diff.
    """
    result = refine_bullet_truthfully(
        original_bullet=request.original_bullet,
        job_requirement=request.job_requirement,
        job_title=request.job_title,
        context_name=request.context_name,
        custom_instructions=request.custom_instructions
    )
    return result


@router.post("/render")
def render_latex(
    request: RenderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Renders the modular LaTeX source code from an approved assembly plan.
    Assembles ONLY selected modules in the specified order.
    """
    candidate_data = load_candidate_library(current_user.id, db)
    tex_source = render_modular_resume(
        candidate_data=candidate_data,
        assembly_plan=request.assembly_plan,
        template_name=request.template_name,
        template_options=request.template_options,
    )
    return {
        "latex_source": tex_source,
        "template_name": request.template_name,
    }


@router.post("/compile")
def compile_latex(
    request: CompileRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Compiles LaTeX source to PDF in an isolated environment.
    Runs readability validation and extracts text.
    """
    temp_dir = f"data/temp/{current_user.id}"
    os.makedirs(temp_dir, exist_ok=True)
    temp_pdf = os.path.join(temp_dir, f"preview_{uuid.uuid4().hex[:8]}.pdf")

    compile_ok, msg = compile_latex_securely(request.latex_source, temp_pdf)
    readability = extract_and_validate_pdf_readability(temp_pdf)

    latest_pdf = os.path.join(temp_dir, "latest_preview.pdf")
    try:
        import shutil
        shutil.copy2(temp_pdf, latest_pdf)
    except Exception:
        pass

    import time
    return {
        "success": compile_ok,
        "message": msg,
        "preview_path": temp_pdf,
        "preview_url": f"/api/v1/modular-resume/temp-preview/pdf?t={int(time.time())}",
        "readability_report": readability,
        "latex_source": request.latex_source
    }


@router.get("/temp-preview/pdf")
def get_temp_preview_pdf(current_user: User = Depends(get_current_user)):
    """
    Streams the latest compiled temporary preview PDF for the current candidate.
    """
    pdf_path = f"data/temp/{current_user.id}/latest_preview.pdf"
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="No preview compiled yet")
    return FileResponse(pdf_path, media_type="application/pdf")


class VersionCompileRequest(BaseModel):
    latex_source: str
    template_options: Optional[Dict[str, Any]] = None


@router.post("/version/{version_id}/compile")
def compile_version_source(
    version_id: int,
    request: VersionCompileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Recompiles an existing saved resume version when manual edits are made to the LaTeX source.
    Safely re-compiles with shell escape disabled, updates the storage PDF, and revalidates readability.
    """
    v = db.query(ResumeVersion).filter(
        ResumeVersion.id == version_id,
        ResumeVersion.user_id == current_user.id
    ).first()

    if not v:
        raise HTTPException(status_code=404, detail="Resume version not found")

    pdf_path = v.storage_path
    compile_ok, msg = compile_latex_securely(request.latex_source, pdf_path)
    readability = extract_and_validate_pdf_readability(pdf_path)

    v.latex_source = request.latex_source
    if request.template_options:
        v.template_options = request.template_options

    parsed = dict(v.parsed_json or {})
    parsed["readability"] = readability
    parsed["compilation_message"] = msg
    v.parsed_json = parsed

    # Update source archive if available
    zip_path = parsed.get("zip_path")
    if zip_path:
        create_source_archive(request.latex_source, zip_path, {"version": v.version_number})

    db.commit()
    db.refresh(v)

    return {
        "success": compile_ok,
        "message": msg,
        "readability_report": readability,
        "version_id": v.id,
        "version_number": v.version_number,
    }


@router.post("/save-version")
def save_version(
    request: SaveVersionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Persists an approved tailored resume as an immutable version linked to its job and application.
    """
    version = save_immutable_resume_version(
        db=db,
        user_id=current_user.id,
        job_id=request.job_id,
        application_id=request.application_id,
        name=request.name or "Tailored Resume",
        latex_source=request.latex_source,
        assembly_plan=request.assembly_plan,
        template_name=request.template_name or "clean_ats",
        template_options=request.template_options,
        notes=request.notes,
        parent_version_id=request.parent_version_id
    )

    return {
        "id": version.id,
        "version_number": version.version_number,
        "name": version.name,
        "template_name": version.template_name,
        "storage_path": version.storage_path,
        "created_at": str(version.created_at)
    }


@router.get("/versions/{job_id}")
def list_job_resume_versions(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lists all saved resume versions for a specific job opening.
    """
    versions = db.query(ResumeVersion).filter(
        ResumeVersion.user_id == current_user.id,
        ResumeVersion.job_id == job_id
    ).order_by(ResumeVersion.version_number.desc()).all()

    return [
        {
            "id": v.id,
            "version_number": v.version_number,
            "name": v.name,
            "template_name": v.template_name,
            "created_at": str(v.created_at),
            "notes": v.notes,
        }
        for v in versions
    ]


@router.get("/version/{version_id}")
def get_version_details(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves complete details, assembly plan, and LaTeX source for a saved version.
    """
    v = db.query(ResumeVersion).filter(
        ResumeVersion.id == version_id,
        ResumeVersion.user_id == current_user.id
    ).first()

    if not v:
        raise HTTPException(status_code=404, detail="Resume version not found")

    return {
        "id": v.id,
        "job_id": v.job_id,
        "application_id": v.application_id,
        "version_number": v.version_number,
        "name": v.name,
        "template_name": v.template_name,
        "template_options": v.template_options,
        "assembly_plan": v.assembly_plan,
        "latex_source": v.latex_source,
        "notes": v.notes,
        "created_at": str(v.created_at),
        "parsed_json": v.parsed_json
    }


@router.post("/version/{version_id}/restore")
def restore_version(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Restores a previous resume version as the active resume for its application.
    """
    v = db.query(ResumeVersion).filter(
        ResumeVersion.id == version_id,
        ResumeVersion.user_id == current_user.id
    ).first()

    if not v:
        raise HTTPException(status_code=404, detail="Resume version not found")

    if v.application_id:
        app = db.query(Application).filter(Application.id == v.application_id).first()
        if app:
            app.resume_version_url = v.storage_path
            db.commit()

    return {"message": f"Version {v.version_number} restored successfully as active application resume"}


@router.get("/version/{version_id_1}/compare/{version_id_2}")
def compare_versions_endpoint(
    version_id_1: int,
    version_id_2: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Compares two saved resume versions and returns granular diffs.
    """
    diff_data = compare_resume_versions(db, version_id_1, version_id_2)
    return diff_data


@router.get("/download/{version_id}/pdf")
def download_pdf(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Downloads compiled PDF for a resume version.
    """
    v = db.query(ResumeVersion).filter(
        ResumeVersion.id == version_id,
        ResumeVersion.user_id == current_user.id
    ).first()

    if not v or not v.storage_path or not os.path.exists(v.storage_path):
        raise HTTPException(status_code=404, detail="PDF file not found")

    filename = f"{v.name.replace(' ', '_')}.pdf"
    return FileResponse(v.storage_path, media_type="application/pdf", filename=filename)


@router.get("/download/{version_id}/tex")
def download_tex(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Downloads LaTeX (.tex) source file for a resume version.
    """
    v = db.query(ResumeVersion).filter(
        ResumeVersion.id == version_id,
        ResumeVersion.user_id == current_user.id
    ).first()

    if not v or not v.latex_source:
        raise HTTPException(status_code=404, detail="LaTeX source not found")

    filename = f"{v.name.replace(' ', '_')}.tex"
    return Response(
        content=v.latex_source,
        media_type="text/x-tex",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/download/{version_id}/zip")
def download_source_zip(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Downloads full source package archive (.zip) with .tex and metadata.
    """
    v = db.query(ResumeVersion).filter(
        ResumeVersion.id == version_id,
        ResumeVersion.user_id == current_user.id
    ).first()

    if not v:
        raise HTTPException(status_code=404, detail="Resume version not found")

    zip_path = (v.parsed_json or {}).get("zip_path")
    if not zip_path or not os.path.exists(zip_path):
        # Regenerate on the fly
        storage_dir = f"data/resumes/{current_user.id}"
        os.makedirs(storage_dir, exist_ok=True)
        zip_path = os.path.join(storage_dir, f"source_v{v.version_number}.zip")
        create_source_archive(v.latex_source or "", zip_path, {"version": v.version_number})

    filename = f"{v.name.replace(' ', '_')}_source.zip"
    return FileResponse(zip_path, media_type="application/zip", filename=filename)


@router.get("/preview/{version_id}/pdf")
def preview_pdf(
    version_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Inline PDF stream for iframe viewer.
    """
    v = db.query(ResumeVersion).filter(
        ResumeVersion.id == version_id,
        ResumeVersion.user_id == current_user.id
    ).first()

    if not v or not v.storage_path or not os.path.exists(v.storage_path):
        raise HTTPException(status_code=404, detail="PDF not found")

    return FileResponse(v.storage_path, media_type="application/pdf")
