import logging
import os
import uuid
import threading
import concurrent.futures
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.models.job import Job
from app.models.profile import Profile
from app.models.application import Application
from app.models.cover_letter import CoverLetter
from app.models.application_history import ApplicationHistory
from app.models.candidate import Project, JobRequirement, UserSkill
from app.services.ai.job_analyzer import analyze_job_details
from app.services.ai.matcher import analyze_job_match
from app.services.ai.generator import generate_tailored_resume, generate_cover_letter
from app.services.pdf_exporter import compile_latex_to_pdf, export_text_to_pdf
from app.services.llm import get_llm
from app.services.ai.profile_builder import build_profile_text

logger = logging.getLogger(__name__)

def _llm():
    return get_llm()

def update_task_progress(application_id: int, task_name: str, status: str, result=None, error=None):
    """Updates the progress and result dicts of the Application record in a thread-safe way."""
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == application_id).first()
        if app:
            progress = dict(app.analysis_progress or {})
            results = dict(app.analysis_results or {})
            
            progress[task_name] = status
            if error:
                progress[task_name + "_error"] = error
            if result is not None:
                results[task_name] = result
                
            app.analysis_progress = progress
            app.analysis_results = results
            db.commit()
    except Exception as e:
        logger.error(f"Failed to update task progress: {e}")
    finally:
        db.close()

def run_requirement_extraction(application_id: int, job_id: int, job_title: str, job_desc: str):
    update_task_progress(application_id, "parsing_job", "running")
    try:
        details = analyze_job_details(job_title, job_desc)
        
        # Save to Job in DB
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                # Update technologies in job stack
                extracted_techs = details.get("technologies", [])
                job.tech_stack_json = extracted_techs
                
                # Check and update JobRequirement record
                job_req = db.query(JobRequirement).filter(JobRequirement.job_id == job_id).first()
                if not job_req:
                    job_req = JobRequirement(
                        job_id=job_id,
                        minimum_experience=details.get("years_of_experience", 0) or 0,
                        required_skills=extracted_techs,
                        technologies=extracted_techs
                    )
                    db.add(job_req)
                else:
                    job_req.required_skills = extracted_techs
                    job_req.technologies = extracted_techs
                db.commit()
        finally:
            db.close()
            
        update_task_progress(application_id, "parsing_job", "completed", result=details)
        return details
    except Exception as e:
        update_task_progress(application_id, "parsing_job", "failed", error=str(e))
        raise e

def run_resume_match(application_id: int, user_id: int, job_id: int, profile_text: str, job_desc: str, projects_meta: list, latex_resume: str):
    update_task_progress(application_id, "matching_resume", "running")
    try:
        # Load job requirement metadata
        db = SessionLocal()
        job_meta = {}
        try:
            job_req = db.query(JobRequirement).filter(JobRequirement.job_id == job_id).first()
            if job_req:
                job_meta = {
                    "minimum_experience": job_req.minimum_experience,
                    "required_skills": job_req.required_skills or [],
                    "preferred_skills": job_req.preferred_skills or [],
                    "technologies": job_req.technologies or []
                }
        finally:
            db.close()

        analysis = analyze_job_match(
            profile_text=profile_text,
            job_description=job_desc,
            projects_meta=projects_meta,
            latex_resume=latex_resume,
            job_metadata=job_meta
        )
        
        # Save strengths / match rate to the Job table as well
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.requirements_json = analysis
                db.commit()
        finally:
            db.close()

        update_task_progress(application_id, "matching_resume", "completed", result=analysis)
        return analysis
    except Exception as e:
        update_task_progress(application_id, "matching_resume", "failed", error=str(e))
        raise e

def run_resume_tailoring(
    application_id: int,
    user_id: int,
    job_id: int,
    user_prefix: str,
    safe_company: str,
    latex_resume: str,
    job_desc: str,
    job_title: str,
    skills_list: list,
    global_instructions: str = None,
    job_instructions: str = None,
    raw_resume_text: str = None,
):
    update_task_progress(application_id, "tailoring_resume", "running")
    try:
        db = SessionLocal()
        master_kb = {}
        projects_json = None
        try:
            profile = db.query(Profile).filter(Profile.user_id == user_id).first()
            projects_json = profile.projects_json if profile else None
            if raw_resume_text is None and profile:
                raw_resume_text = profile.raw_resume_text
            if global_instructions is None and profile:
                global_instructions = profile.tailoring_instructions

            from app.models.candidate import Achievement, CourseCertification, Project
            achievements = db.query(Achievement).filter(Achievement.user_id == user_id).all()
            courses = db.query(CourseCertification).filter(CourseCertification.user_id == user_id).all()
            projects = db.query(Project).filter(Project.user_id == user_id).all()
            
            master_kb = {
                "achievements_and_prizes": [{"title": a.title, "event": a.issuer_or_event, "year": a.year_or_date, "details": a.description} for a in achievements],
                "courses_and_certifications": [{"name": c.name, "issuer": c.issuer, "skills": c.skills_covered} for c in courses],
                "projects": [{"name": p.name, "description": p.description, "tech": p.technologies, "link": p.live_link or p.github} for p in projects],
                "skills": skills_list
            }
        finally:
            db.close()

        # Merge instruction layers: per-job overrides global in priority (both are
        # passed separately so the prompt can label them).
        effective_job_instructions = (job_instructions or "").strip() or None
        effective_global = (global_instructions or "").strip() or None

        common_kwargs = dict(
            job_description=job_desc,
            job_title=job_title,
            original_skills=skills_list,
            master_knowledge_base=master_kb,
            user_instructions=effective_job_instructions or effective_global,
            raw_resume_text=raw_resume_text,
            extracted_projects=projects_json,
        )

        # When both layers exist, pass a combined labeled block as user_instructions
        if effective_job_instructions and effective_global and effective_job_instructions != effective_global:
            common_kwargs["user_instructions"] = (
                f"[GLOBAL]\n{effective_global}\n\n[THIS JOB — higher priority]\n{effective_job_instructions}"
            )

        # Load candidate Content Library for modular assembly
        from app.services.resume_compiler.candidate_data import load_candidate_library
        from app.services.resume_compiler.assembly_engine import generate_assembly_plan
        from app.services.resume_compiler.renderer import render_modular_resume
        from app.services.resume_compiler.version_service import save_immutable_resume_version
        from app.services.resume_compiler.compiler import compile_latex_securely

        db = SessionLocal()
        candidate_data = {}
        job_dict = {}
        try:
            candidate_data = load_candidate_library(user_id, db)
            job_obj = db.query(Job).filter(Job.id == job_id).first()
            if job_obj:
                job_dict = {
                    "id": job_obj.id,
                    "title": job_obj.title,
                    "company": job_obj.company,
                    "description": job_obj.description or "",
                    "required_skills_json": job_obj.required_skills_json or [],
                    "tech_stack_json": job_obj.tech_stack_json or [],
                }
        finally:
            db.close()

        # Check if candidate has structured data in Content Library
        has_library_content = bool(
            candidate_data.get("projects") or 
            candidate_data.get("experience") or 
            candidate_data.get("education") or 
            candidate_data.get("skills")
        )

        plan = None
        version_id = None

        if has_library_content:
            # Generate structured assembly plan
            effective_instructions = (job_instructions or global_instructions or "").strip() or None
            plan = generate_assembly_plan(
                candidate_data=candidate_data,
                job=job_dict,
                custom_instructions=effective_instructions,
                target_page_length=1
            )

            # Render controlled modular LaTeX document
            resume_text = render_modular_resume(
                candidate_data=candidate_data,
                assembly_plan=plan,
                template_name=plan.get("template_name", "clean_ats"),
                template_options=plan.get("template_options")
            )

            # Persist immutable version linked to job and application
            db = SessionLocal()
            try:
                version_record = save_immutable_resume_version(
                    db=db,
                    user_id=user_id,
                    job_id=job_id,
                    application_id=application_id,
                    name=f"{safe_company} - Tailored Modular Resume",
                    latex_source=resume_text,
                    assembly_plan=plan,
                    template_name=plan.get("template_name", "clean_ats"),
                    template_options=plan.get("template_options"),
                    notes=f"Auto-generated modular plan for {job_title} at {safe_company}"
                )
                version_id = version_record.id
                resume_pdf_path = version_record.storage_path
            finally:
                db.close()

        elif latex_resume:
            resume_text = generate_tailored_resume(
                master_profile=latex_resume,
                is_latex=True,
                **common_kwargs,
            )
            output_dir = f"data/applications/{user_id}"
            os.makedirs(output_dir, exist_ok=True)
            tex_path = os.path.join(output_dir, f"{user_prefix}_{safe_company}_resume.tex")
            with open(tex_path, "w", encoding="utf-8") as f:
                f.write(resume_text)
                
            try:
                resume_pdf_path = compile_latex_to_pdf(resume_text, f"{user_prefix}_{safe_company}_resume.pdf", output_dir)
            except Exception as e:
                resume_pdf_path = tex_path
                logger.warning(f"Compilation fallback to .tex due to error: {e}")
        else:
            # Markdown/text resume
            db = SessionLocal()
            try:
                profile_text = build_profile_text(user_id, db)
            finally:
                db.close()
            resume_text = generate_tailored_resume(
                master_profile=profile_text,
                is_latex=False,
                **common_kwargs,
            )
            resume_pdf_path = export_text_to_pdf(resume_text, f"{user_prefix}_{safe_company}_resume.pdf")

        # Update application table
        db = SessionLocal()
        try:
            app = db.query(Application).filter(Application.id == application_id).first()
            if app:
                app.resume_version_url = resume_pdf_path
                db.commit()
        finally:
            db.close()

        update_task_progress(
            application_id, 
            "tailoring_resume", 
            "completed", 
            result={
                "path": resume_pdf_path,
                "plan": plan,
                "version_id": version_id,
                "is_modular": has_library_content
            }
        )
        return resume_pdf_path
    except Exception as e:
        update_task_progress(application_id, "tailoring_resume", "failed", error=str(e))
        raise e

def run_cover_letter(
    application_id: int,
    user_id: int,
    job_id: int,
    profile_text: str,
    company: str,
    job_title: str,
    safe_company: str,
    user_instructions: str = None,
):
    update_task_progress(application_id, "cover_letter", "running")
    db = SessionLocal()
    try:
        from app.services.cover_letter.service import (
            generate_personalized_cover_letter,
            save_cover_letter_version,
        )

        gen_res = generate_personalized_cover_letter(
            user_id=user_id,
            job_id=job_id,
            style="concise",
            candidate_motivation=user_instructions,
            application_id=application_id,
            db=db,
        )

        cl_record = save_cover_letter_version(
            user_id=user_id,
            job_id=job_id,
            content=gen_res["content"],
            style=gen_res["style"],
            candidate_motivation=gen_res["candidate_motivation"],
            selected_projects=gen_res["selected_projects"],
            selected_experiences=gen_res["selected_experiences"],
            selected_achievements=gen_res["selected_achievements"],
            application_id=application_id,
            is_approved=True,
            sources_used=gen_res["sources_used"],
            db=db,
        )

        cl_pdf_path = export_text_to_pdf(cl_record.content, f"cl_{user_id}_{cl_record.id}.pdf")
        app = db.query(Application).filter(Application.id == application_id).first()
        if app:
            app.cover_letter_url = cl_pdf_path
            db.commit()

        update_task_progress(
            application_id,
            "cover_letter",
            "completed",
            result={"path": cl_pdf_path, "preview": cl_record.content, "version_id": cl_record.id},
        )
        return cl_record.content
    except Exception as e:
        logger.error(f"Cover letter generation failed in pipeline: {e}")
        update_task_progress(application_id, "cover_letter", "failed", error=str(e))
        raise e
    finally:
        db.close()

def run_company_research(application_id: int, user_id: int, job_id: int, company: str, job_title: str, profile_text: str):
    update_task_progress(application_id, "company_research", "running")
    db = SessionLocal()
    try:
        from app.services.company_research.service import generate_company_research

        research_record = generate_company_research(
            job_id=job_id,
            user_id=user_id,
            db=db,
            force_refresh=False,
        )

        result_content = research_record.summary_markdown or research_record.company_overview
        update_task_progress(application_id, "company_research", "completed", result=result_content)
        return result_content
    except Exception as e:
        logger.error(f"Company research generation failed in pipeline: {e}")
        update_task_progress(application_id, "company_research", "failed", error=str(e))
        raise e
    finally:
        db.close()

def run_interview_prep(application_id: int, company: str, job_title: str, profile_text: str, job_desc: str):
    update_task_progress(application_id, "interview_prep", "running")
    try:
        prompt = (
            f"Generate exactly 5 highly relevant technical/behavioral interview preparation questions with detailed answers.\n"
            f"Tailor them to a candidate applying for '{job_title}' at '{company}' with this background: {profile_text[:600]}\n"
            f"and this job description: {job_desc[:600]}.\n"
            f"Respond ONLY with a JSON array of objects, where each object has 'question' (string) and 'answer' (string) keys. Do NOT include markdown blocks."
        )
        qa_data = _llm().generate_json(system_prompt="You are an expert technical interviewer.", user_prompt=prompt)
        
        # If qa_data is not list, wrap it or parse
        if not isinstance(qa_data, list):
            qa_data = [
                {
                    "question": "Tell me about your experience related to this role.",
                    "answer": "Discuss projects that highlight matching tech stack."
                }
            ]
        update_task_progress(application_id, "interview_prep", "completed", result=qa_data)
        return qa_data
    except Exception as e:
        update_task_progress(application_id, "interview_prep", "failed", error=str(e))
        raise e

def execute_analysis_pipeline(application_id: int, user_id: int, job_id: int):
    """Runs all analyses concurrently in background thread pool."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        job = db.query(Job).filter(Job.id == job_id).first()
        profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        application = db.query(Application).filter(Application.id == application_id).first()
        
        if not user or not job:
            logger.error(f"Cannot run analysis pipeline: User {user_id} or Job {job_id} not found.")
            return

        # --- GitHub freshness: auto-sync if username set and data stale ---
        try:
            from app.services.github_sync import ensure_github_fresh
            ensure_github_fresh(db, user_id, username=None)
            db.expire_all()
            profile = db.query(Profile).filter(Profile.user_id == user_id).first()
        except Exception as e:
            logger.warning(f"GitHub freshness check failed (continuing): {e}")

        profile_text = build_profile_text(user_id, db)
        latex_resume = profile.latex_template if (profile and profile.latex_template) else ""
        raw_resume_text = profile.raw_resume_text if profile else None
        global_instructions = profile.tailoring_instructions if profile else None
        job_instructions = application.user_instructions if application else None

        # Fetch candidate projects
        projects = db.query(Project).filter(Project.user_id == user_id).all()
        projects_meta = []
        for proj in projects:
            projects_meta.append({
                "name": proj.name,
                "description": proj.description,
                "technologies": proj.technologies or [],
                "github": proj.github,
                "live_link": proj.live_link
            })

        # Fetch candidate skills list
        user_skills = db.query(UserSkill).filter(UserSkill.user_id == user_id).all()
        skills_list = [us.skill.name for us in user_skills]

        user_prefix = user.email.split('@')[0]
        safe_company = "".join(c for c in (job.company or "company") if c.isalnum() or c in (' ', '_')).replace(' ', '_')
        job_title = job.title
        job_desc = job.description or job.title
        company = job.company or "Company"

    finally:
        db.close()

    # Combined instructions for cover letter / other tasks
    if job_instructions and global_instructions and job_instructions != global_instructions:
        combined_instructions = (
            f"[GLOBAL]\n{global_instructions}\n\n[THIS JOB — higher priority]\n{job_instructions}"
        )
    else:
        combined_instructions = (job_instructions or global_instructions) or None

    # Define tasks to run concurrently
    tasks = {
        "parsing_job": (
            run_requirement_extraction,
            (application_id, job_id, job_title, job_desc),
        ),
        "matching_resume": (
            run_resume_match,
            (application_id, user_id, job_id, profile_text, job_desc, projects_meta, latex_resume),
        ),
        "tailoring_resume": (
            run_resume_tailoring,
            (
                application_id, user_id, job_id, user_prefix, safe_company,
                latex_resume, job_desc, job_title, skills_list,
                global_instructions, job_instructions, raw_resume_text,
            ),
        ),
        "cover_letter": (
            run_cover_letter,
            (application_id, user_id, job_id, profile_text, company, job_title, safe_company, combined_instructions),
        ),
        "company_research": (
            run_company_research,
            (application_id, user_id, job_id, company, job_title, profile_text),
        ),
        "interview_prep": (
            run_interview_prep,
            (application_id, company, job_title, profile_text, job_desc),
        ),
    }

    # Run concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(fn, *args): name
            for name, (fn, args) in tasks.items()
        }

        # Wait for all tasks to finish
        failed_tasks = []
        for future in concurrent.futures.as_completed(futures):
            task_name = futures[future]
            try:
                future.result()
                logger.info(f"Task '{task_name}' completed successfully in pipeline.")
            except Exception as e:
                logger.error(f"Task '{task_name}' failed in pipeline: {e}")
                failed_tasks.append(task_name)

    # One sequential retry pass — long LLM calls occasionally fail on
    # transient connection errors even with client-level retries.
    for task_name in failed_tasks:
        fn, args = tasks[task_name]
        logger.warning(f"Retrying pipeline task '{task_name}' once after failure.")
        try:
            fn(*args)
        except Exception as e:
            logger.error(f"Retry of pipeline task '{task_name}' failed: {e}")

    # Finalize application record
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == application_id).first()
        if app:
            resume_ok = bool(app.resume_version_url) and os.path.exists(app.resume_version_url)
            if resume_ok:
                app.status = "generated"
                app.next_action = "Review and Apply"
            else:
                app.status = "failed"
                app.next_action = "Generation failed — run Analyse & Apply again"
                db.add(ApplicationHistory(
                    application_id=application_id,
                    status="failed",
                    notes="Resume generation failed after retry. Please re-run the pipeline.",
                ))
            db.commit()
    except Exception as e:
        logger.error(f"Failed to finalize application status: {e}")
    finally:
        db.close()

def start_background_analysis_thread(application_id: int, user_id: int, job_id: int):
    """Starts the pipeline in a separate daemon thread to avoid blocking the API request."""
    thread = threading.Thread(
        target=execute_analysis_pipeline,
        args=(application_id, user_id, job_id)
    )
    thread.daemon = True
    thread.start()
    logger.info(f"Started background analysis thread for Application {application_id}")
