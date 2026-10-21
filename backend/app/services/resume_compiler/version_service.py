import os
import uuid
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.resume import ResumeVersion
from app.models.application import Application
from app.models.job import Job
from .compiler import compile_latex_securely, extract_and_validate_pdf_readability, create_source_archive

logger = logging.getLogger(__name__)

def save_immutable_resume_version(
    db: Session,
    user_id: int,
    job_id: Optional[int],
    application_id: Optional[int],
    name: str,
    latex_source: str,
    assembly_plan: Dict[str, Any],
    template_name: str = "clean_ats",
    template_options: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None,
    parent_version_id: Optional[int] = None
) -> ResumeVersion:
    """
    Saves an approved job-specific resume as an immutable version record.
    Compiles PDF, validates readability, creates source archive, and persists to DB.
    """
    # 1. Calculate version number for this job / user
    latest = db.query(ResumeVersion).filter(
        ResumeVersion.user_id == user_id,
        ResumeVersion.job_id == job_id
    ).order_by(ResumeVersion.version_number.desc()).first()

    next_version = (latest.version_number + 1) if latest else 1

    # 2. Output directories and paths
    storage_dir = f"data/resumes/{user_id}"
    os.makedirs(storage_dir, exist_ok=True)
    
    file_id = uuid.uuid4().hex[:10]
    tex_filename = f"resume_v{next_version}_{file_id}.tex"
    pdf_filename = f"resume_v{next_version}_{file_id}.pdf"
    zip_filename = f"resume_v{next_version}_{file_id}.zip"

    tex_path = os.path.join(storage_dir, tex_filename)
    pdf_path = os.path.join(storage_dir, pdf_filename)
    zip_path = os.path.join(storage_dir, zip_filename)

    # Save .tex source
    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(latex_source)

    # 3. Compile PDF securely
    compile_ok, msg = compile_latex_securely(latex_source, pdf_path)
    
    # 4. Validate readability
    readability_report = extract_and_validate_pdf_readability(pdf_path)

    # 5. Pack source archive
    job_record = db.query(Job).filter(Job.id == job_id).first() if job_id else None
    metadata = {
        "job_id": job_id,
        "job_title": job_record.title if job_record else "General",
        "company": job_record.company if job_record else "",
        "version_number": next_version,
        "template": template_name,
        "readability": readability_report,
    }
    create_source_archive(latex_source, zip_path, metadata)

    # 6. Extract selected items summary
    sections_cfg = assembly_plan.get("sections") or {}
    selected_projs = sections_cfg.get("projects", {}).get("selected_item_ids", [])
    selected_exps = sections_cfg.get("experience", {}).get("selected_item_ids", [])
    selected_bullets = {
        "projects": sections_cfg.get("projects", {}).get("selected_bullets", {}),
        "experience": sections_cfg.get("experience", {}).get("selected_bullets", {}),
    }

    # 7. Create DB record
    version_row = ResumeVersion(
        user_id=user_id,
        job_id=job_id,
        application_id=application_id,
        name=name or f"{job_record.company if job_record else 'Custom'} - v{next_version}",
        storage_path=pdf_path,
        file_type="pdf",
        latex_source=latex_source,
        assembly_plan=assembly_plan,
        template_name=template_name,
        template_options=template_options or {},
        parent_version_id=parent_version_id,
        version_number=next_version,
        notes=notes,
        selected_projects=selected_projs,
        selected_experiences=selected_exps,
        selected_bullets=selected_bullets,
        parsed_json={
            "tex_path": tex_path,
            "pdf_path": pdf_path,
            "zip_path": zip_path,
            "readability": readability_report,
            "compilation_message": msg,
        }
    )

    db.add(version_row)
    db.commit()
    db.refresh(version_row)

    # 8. Link to application if exists
    if application_id:
        app = db.query(Application).filter(Application.id == application_id).first()
        if app:
            app.resume_version_url = pdf_path
            db.commit()

    return version_row


def compare_resume_versions(db: Session, version_id_1: int, version_id_2: int) -> Dict[str, Any]:
    """
    Computes a detailed comparison diff between two resume versions.
    Includes module inclusion differences, section order diffs, template diffs,
    and bullet refinement differences.
    """
    v1 = db.query(ResumeVersion).filter(ResumeVersion.id == version_id_1).first()
    v2 = db.query(ResumeVersion).filter(ResumeVersion.id == version_id_2).first()

    if not v1 or not v2:
        return {"error": "One or both resume versions not found"}

    plan1 = v1.assembly_plan or {}
    plan2 = v2.assembly_plan or {}

    order1 = plan1.get("section_order") or []
    order2 = plan2.get("section_order") or []

    secs1 = plan1.get("sections") or {}
    secs2 = plan2.get("sections") or {}

    all_keys = set(secs1.keys()).union(set(secs2.keys()))
    section_changes = {}

    for k in all_keys:
        inc1 = secs1.get(k, {}).get("included", False)
        inc2 = secs2.get(k, {}).get("included", False)
        items1 = set(secs1.get(k, {}).get("selected_item_ids", []))
        items2 = set(secs2.get(k, {}).get("selected_item_ids", []))

        section_changes[k] = {
            "v1_included": inc1,
            "v2_included": inc2,
            "status": "unchanged" if inc1 == inc2 and items1 == items2 else "modified",
            "added_items": list(items2 - items1),
            "removed_items": list(items1 - items2),
        }

    # Bullet refinement changes
    ref1 = plan1.get("refinements") or {}
    ref2 = plan2.get("refinements") or {}
    all_bullet_ids = set(ref1.keys()).union(set(ref2.keys()))
    bullet_changes = {}
    for bid in all_bullet_ids:
        t1 = (ref1.get(bid) or {}).get("refined") if isinstance(ref1.get(bid), dict) else ref1.get(bid)
        t2 = (ref2.get(bid) or {}).get("refined") if isinstance(ref2.get(bid), dict) else ref2.get(bid)
        if t1 != t2:
            bullet_changes[bid] = {
                "v1_text": t1,
                "v2_text": t2,
            }

    return {
        "v1": {
            "id": v1.id,
            "version_number": v1.version_number,
            "name": v1.name,
            "template": v1.template_name,
            "created_at": str(v1.created_at) if v1.created_at else None
        },
        "v2": {
            "id": v2.id,
            "version_number": v2.version_number,
            "name": v2.name,
            "template": v2.template_name,
            "created_at": str(v2.created_at) if v2.created_at else None
        },
        "order_changed": order1 != order2,
        "v1_order": order1,
        "v2_order": order2,
        "template_changed": v1.template_name != v2.template_name,
        "section_changes": section_changes,
        "bullet_changes": bullet_changes,
    }
