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

        if latex_resume:
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
            # Markdown/text resume — still ship knowledge base + instructions + raw text
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

        update_task_progress(application_id, "tailoring_resume", "completed", result={"path": resume_pdf_path})
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
    try:
        # Generate cover letter based on profile
        cl_text = generate_cover_letter(
            profile_text,
            company,
            job_title,
            match_strengths=None,
            user_instructions=user_instructions,
        )
        
        # Save to DB
        db = SessionLocal()
        try:
            cl_record = db.query(CoverLetter).filter(CoverLetter.job_id == job_id, CoverLetter.user_id == user_id).first()
            if not cl_record:
                cl_record = CoverLetter(
                    user_id=user_id,
                    job_id=job_id,
                    content=cl_text,
                    format="md"
                )
                db.add(cl_record)
            else:
                cl_record.content = cl_text
            db.commit()
            cl_id = cl_record.id
        finally:
            db.close()
            
        cl_pdf_path = export_text_to_pdf(cl_text, f"cl_{user_id}_{cl_id}.pdf")
        
        db = SessionLocal()
        try:
            app = db.query(Application).filter(Application.id == application_id).first()
            if app:
                app.cover_letter_url = cl_pdf_path
                db.commit()
        finally:
            db.close()

        update_task_progress(application_id, "cover_letter", "completed", result={"path": cl_pdf_path, "preview": cl_text})
        return cl_text
    except Exception as e:
        update_task_progress(application_id, "cover_letter", "failed", error=str(e))
        raise e

def run_company_research(application_id: int, company: str, job_title: str, profile_text: str):
    update_task_progress(application_id, "company_research", "running")
    try:
        prompt = (
            f"You are a professional company research assistant. Research '{company}' for the role of '{job_title}'.\n"
            f"Summarize the following in a neat, clear markdown format (with headers):\n"
            f"1. Core business, products, and services.\n"
            f"2. Known work culture, team values, and mission.\n"
            f"3. Why this candidate fits their mission based on their background summary: {profile_text[:600]}."
        )
        research = _llm().generate_text(system_prompt="You are a corporate research bot.", user_prompt=prompt)
        update_task_progress(application_id, "company_research", "completed", result=research)
        return research
    except Exception as e:
        update_task_progress(application_id, "company_research", "failed", error=str(e))
        raise e

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
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        # Launch concurrently
        futures = {
            executor.submit(
                run_requirement_extraction, application_id, job_id, job_title, job_desc
            ): "parsing_job",
            executor.submit(
                run_resume_match, application_id, user_id, job_id, profile_text, job_desc, projects_meta, latex_resume
            ): "matching_resume",
            executor.submit(
                run_resume_tailoring,
                application_id, user_id, job_id, user_prefix, safe_company,
                latex_resume, job_desc, job_title, skills_list,
                global_instructions, job_instructions, raw_resume_text,
            ): "tailoring_resume",
            executor.submit(
                run_cover_letter, application_id, user_id, job_id, profile_text, company, job_title, safe_company,
                combined_instructions,
            ): "cover_letter",
            executor.submit(
                run_company_research, application_id, company, job_title, profile_text
            ): "company_research",
            executor.submit(
                run_interview_prep, application_id, company, job_title, profile_text, job_desc
            ): "interview_prep"
        }

        # Wait for all tasks to finish
        for future in concurrent.futures.as_completed(futures):
            task_name = futures[future]
            try:
                future.result()
                logger.info(f"Task '{task_name}' completed successfully in pipeline.")
            except Exception as e:
                logger.error(f"Task '{task_name}' failed in pipeline: {e}")

    # Finalize application record
    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == application_id).first()
        if app:
            app.status = "generated"
            app.next_action = "Review and Apply"
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
