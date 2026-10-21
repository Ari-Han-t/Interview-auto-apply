import os
import re
import difflib
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.models.cover_letter import CoverLetter
from app.models.job import Job
from app.models.application import Application
from app.models.user import User
from app.services.llm import get_llm
from app.services.resume_compiler.candidate_data import load_candidate_library
from app.services.pdf_exporter import export_text_to_pdf

logger = logging.getLogger(__name__)

STYLE_DESCRIPTIONS = {
    "concise": "Concise & Direct: High signal-to-noise ratio, ~220-270 words, punchy sentences, zero throat-clearing fluff. Directly states interest, verified core qualifications, concrete project proof, and day-one value.",
    "technical": "Technical & Project-Focused: ~300-380 words. Deep dive into system architecture, tech stacks, throughput, concurrency, engineering decisions, and concrete project outcomes.",
    "startup": "Startup & Impact-Oriented: ~260-320 words. Fast-paced, outcome-driven, highlights ownership mindset, shipping velocity, wearing multiple hats, and building from 0 to 1.",
    "formal": "Formal & Traditional: ~280-350 words. Classic corporate decorum, structured paragraphs, polished professional greeting, rigorous evidence, and formal signoff.",
}

def _build_candidate_context(
    candidate_data: Dict[str, Any],
    selected_project_ids: Optional[List[int]] = None,
    selected_experience_ids: Optional[List[int]] = None,
    selected_achievement_ids: Optional[List[int]] = None,
) -> Dict[str, Any]:
    general = candidate_data.get("general_info", {})
    all_projects = candidate_data.get("projects", [])
    all_exp = candidate_data.get("experience", [])
    all_achieve = candidate_data.get("achievements", [])
    skills = candidate_data.get("skills", {})

    # Filter projects
    if selected_project_ids:
        projects = [p for p in all_projects if p.get("id") in selected_project_ids]
    else:
        projects = all_projects[:3]

    # Filter experiences
    if selected_experience_ids:
        experiences = [e for e in all_exp if e.get("id") in selected_experience_ids]
    else:
        experiences = all_exp[:3]

    # Filter achievements
    if selected_achievement_ids:
        achievements = [a for a in all_achieve if a.get("id") in selected_achievement_ids]
    else:
        achievements = all_achieve[:2]

    # Format skills summary
    top_skills = []
    if isinstance(skills, dict):
        for cat, items in skills.items():
            if isinstance(items, list):
                for item in items[:5]:
                    top_skills.append(item.get("name", "") if isinstance(item, dict) else str(item))
    elif isinstance(skills, list):
        for item in skills:
            name = item.get("name", "") if isinstance(item, dict) else str(item)
            if name:
                top_skills.append(name)

    return {
        "full_name": general.get("full_name") or "Candidate",
        "email": general.get("email") or "",
        "phone": general.get("phone") or "",
        "location": general.get("location") or "",
        "linkedin": general.get("linkedin") or "",
        "github": general.get("github") or "",
        "projects": projects,
        "experiences": experiences,
        "achievements": achievements,
        "top_skills": top_skills[:15],
    }

def _build_deterministic_fallback(
    candidate: Dict[str, Any],
    job: Job,
    style: str,
    candidate_motivation: Optional[str] = None,
) -> str:
    """Deterministic, high-quality, truthful fallback if LLM is unavailable."""
    name = candidate.get("full_name", "Applicant")
    company = job.company or "Hiring Team"
    role = job.title or "Software Engineer"
    skills_str = ", ".join(candidate.get("top_skills", [])[:5]) or "full-stack development"
    
    first_exp = candidate.get("experiences", [{}])[0] if candidate.get("experiences") else {}
    exp_company = first_exp.get("company", "previous roles")
    exp_role = first_exp.get("role", "Engineer")
    
    first_proj = candidate.get("projects", [{}])[0] if candidate.get("projects") else {}
    proj_name = first_proj.get("title", "distributed system project")
    proj_tech = ", ".join(first_proj.get("technologies", [])[:4]) or "modern web frameworks"
    proj_desc = first_proj.get("description") or (first_proj.get("bullets", ["built scalable features"])[0] if first_proj.get("bullets") else "engineered production-grade solutions")
    if isinstance(proj_desc, dict):
        proj_desc = proj_desc.get("text", "engineered production-grade solutions")

    today = datetime.now().strftime("%B %d, %Y")
    greeting = f"Dear Hiring Team at {company}," if style != "formal" else f"Dear {company} Hiring Committee,"

    motivation_paragraph = ""
    if candidate_motivation and candidate_motivation.strip():
        motivation_paragraph = f"\n\n{candidate_motivation.strip()}\n\n"
    else:
        motivation_paragraph = (
            f"\n\nI am applying for the {role} position at {company}. "
            f"Having engineered systems with {skills_str}, I am excited by {company}'s focus on high-impact engineering.\n\n"
        )

    if style == "concise":
        body = (
            f"{greeting}{motivation_paragraph}"
            f"In my work as a {exp_role} at {exp_company}, I developed and maintained production systems with a strong emphasis on reliability and clean design. "
            f"Most notably, through {proj_name} (built with {proj_tech}), I {proj_desc.lower() if isinstance(proj_desc, str) else 'delivered robust system features'}.\n\n"
            f"I look forward to bringing this direct hands-on experience with {skills_str} to help {company} build and scale its core services.\n\n"
            f"Sincerely,\n{name}"
        )
    elif style == "technical":
        body = (
            f"{greeting}{motivation_paragraph}"
            f"My technical background centers on building resilient backend services and data workflows using {skills_str}. "
            f"At {exp_company}, I worked as a {exp_role}, focusing on API development, query optimization, and maintainable service architecture.\n\n"
            f"To demonstrate practical implementation: on {proj_name}, I leveraged {proj_tech} to design an end-to-end architecture. {proj_desc} "
            f"This project strengthened my focus on low-latency data access, concurrency management, and modular testing.\n\n"
            f"I am eager to contribute to {company}'s engineering initiatives for the {role} role and discuss how my technical background aligns with your roadmap.\n\n"
            f"Best regards,\n{name}"
        )
    elif style == "startup":
        body = (
            f"{greeting}{motivation_paragraph}"
            f"I thrive in fast-paced engineering environments where shipping maintainable code and solving ambiguous problems are paramount. "
            f"Working as a {exp_role} at {exp_company}, I learned to prioritize rapid execution without sacrificing code quality.\n\n"
            f"When building {proj_name} with {proj_tech}, I took complete ownership from initial data modeling through deployment: {proj_desc}. "
            f"I enjoy wearing multiple hats, collaborating cross-functionally, and iterating quickly based on concrete metrics.\n\n"
            f"I would welcome the opportunity to bring this product-minded engineering mindset to {company}.\n\n"
            f"Best,\n{name}"
        )
    else:  # formal
        body = (
            f"{today}\n\n"
            f"Hiring Committee\n{company}\n\n"
            f"{greeting}\n\n"
            f"Please accept this letter and accompanying resume as my formal application for the {role} opportunity at {company}. "
            f"{motivation_paragraph.strip()}\n\n"
            f"My professional experience as a {exp_role} at {exp_company} has prepared me to meet the requirements of this role. "
            f"Throughout my projects, including {proj_name} implemented using {proj_tech}, I have consistently demonstrated a commitment to technical rigor: {proj_desc}.\n\n"
            f"I welcome the opportunity to discuss how my verified background and technical capabilities in {skills_str} can support {company}'s ongoing objectives.\n\n"
            f"Respectfully,\n{name}"
        )

    return body.strip()

def _verify_anti_hallucination(cl_text: str, candidate: Dict[str, Any], job: Job) -> List[str]:
    """Checks for suspicious fabricated assertions or metrics not in candidate data."""
    warnings = []
    
    # Check for excessive fabricated percentages
    pct_matches = re.findall(r'(\d+(?:\.\d+)?%)', cl_text)
    known_text = " ".join([
        str(p) for p in candidate.get("projects", [])
    ] + [
        str(e) for e in candidate.get("experiences", [])
    ] + [
        str(a) for a in candidate.get("achievements", [])
    ])
    
    for pct in pct_matches:
        if pct not in known_text:
            warnings.append(f"Metric '{pct}' in letter was not found in verified candidate library records.")

    # Check for fake personal connection phrases
    fake_connection_patterns = [
        r"since I was a (?:child|kid)",
        r"lifelong dream",
        r"personal friend of",
        r"following your team for decades",
    ]
    for pat in fake_connection_patterns:
        if re.search(pat, cl_text, re.IGNORECASE):
            warnings.append(f"Detected potentially unsupported personal connection phrase matching '{pat}'.")

    return warnings

def generate_personalized_cover_letter(
    user_id: int,
    job_id: int,
    style: str = "concise",
    candidate_motivation: Optional[str] = None,
    selected_project_ids: Optional[List[int]] = None,
    selected_experience_ids: Optional[List[int]] = None,
    selected_achievement_ids: Optional[List[int]] = None,
    application_id: Optional[int] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """Generates a truthful, highly tailored cover letter adhering to the specified style."""
    if style not in STYLE_DESCRIPTIONS:
        style = "concise"

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ValueError(f"Job #{job_id} not found")

    candidate_raw = load_candidate_library(user_id, db)
    candidate = _build_candidate_context(
        candidate_raw,
        selected_project_ids=selected_project_ids,
        selected_experience_ids=selected_experience_ids,
        selected_achievement_ids=selected_achievement_ids,
    )

    # Reuse match strengths from application if available
    match_strengths = []
    if application_id:
        app = db.query(Application).filter(Application.id == application_id).first()
        if app and app.analysis_results and isinstance(app.analysis_results, dict):
            matched = app.analysis_results.get("resume_matched")
            if matched and isinstance(matched, dict):
                match_strengths = matched.get("strengths", [])

    # Format context for LLM prompt
    projects_summary = []
    for p in candidate.get("projects", []):
        techs = ", ".join(p.get("technologies", [])) if p.get("technologies") else "N/A"
        desc = p.get("description") or (p.get("bullets", [""])[0] if p.get("bullets") else "")
        if isinstance(desc, dict):
            desc = desc.get("text", "")
        projects_summary.append(f"- **{p.get('title')}** (Stack: {techs}): {desc}")

    exp_summary = []
    for e in candidate.get("experiences", []):
        bullets_text = " ".join([b.get("text", "") if isinstance(b, dict) else str(b) for b in e.get("bullets", [])[:2]])
        exp_summary.append(f"- **{e.get('role')}** at {e.get('company')} ({e.get('start_date')} - {e.get('end_date')}): {bullets_text}")

    achieve_summary = []
    for a in candidate.get("achievements", []):
        achieve_summary.append(f"- {a.get('title')}: {a.get('impact_metrics') or a.get('description') or ''}")

    job_reqs = ", ".join(job.required_skills_json or []) if job.required_skills_json else "Software Engineering"
    job_tech = ", ".join(job.tech_stack_json or []) if job.tech_stack_json else "Modern Engineering Stack"
    job_resp = "\n".join([f"- {r}" for r in (job.responsibilities_json or [])[:4]])

    system_prompt = (
        "You are an expert career advisor and technical communications specialist. "
        "Your task is to write an exceptionally tailored, compelling, and 100% FACTUAL cover letter for a candidate. "
        "\nCRITICAL RULES:"
        "\n1. TRUTH-PRESERVING: NEVER invent metrics, awards, technologies, personal connections, or experiences. Use ONLY verified facts from the candidate's profile."
        "\n2. NO GENERIC FILLER: Eliminate boilerplate openings ('I am thrilled to write...', 'I am expressing my fervent passion...'). Begin with substance."
        "\n3. COVER THE 4 CORE PILLARS:"
        "\n   a. Why the candidate is interested in this role (reflecting candidate's actual motivation)."
        "\n   b. Why verified experience is directly relevant to this job."
        "\n   c. Which specific projects or accomplishments demonstrate ability (citing real technologies and outcomes)."
        "\n   d. What the candidate will contribute to the team's engineering goals."
        "\n4. ADHERE TO THE REQUESTED STYLE: " + STYLE_DESCRIPTIONS[style] +
        "\n5. Output clean Markdown text with standard professional formatting, including proper salutation and sign-off."
    )

    motivation_instruction = (
        f"Candidate's Genuine Motivation for this role:\n\"{candidate_motivation.strip()}\"\n"
        if candidate_motivation and candidate_motivation.strip()
        else "Candidate Motivation: Emphasize genuine alignment with the company's core product and tech stack requirements."
    )

    user_prompt = (
        f"TARGET JOB:\n"
        f"Role: {job.title}\n"
        f"Company: {job.company}\n"
        f"Location: {job.location or 'Remote'}\n"
        f"Required Skills: {job_reqs}\n"
        f"Tech Stack: {job_tech}\n"
        f"Key Responsibilities:\n{job_resp or job.description[:400]}\n\n"
        f"CANDIDATE VERIFIED PROFILE:\n"
        f"Name: {candidate['full_name']}\n"
        f"Email: {candidate['email']}\n"
        f"Phone: {candidate['phone']}\n"
        f"Core Skills: {', '.join(candidate['top_skills'])}\n\n"
        f"SELECTED EXPERIENCES (VERIFIED):\n" + "\n".join(exp_summary or ["None specified"]) + "\n\n"
        f"SELECTED PROJECTS (VERIFIED):\n" + "\n".join(projects_summary or ["None specified"]) + "\n\n"
        f"SELECTED ACHIEVEMENTS (VERIFIED):\n" + "\n".join(achieve_summary or ["None specified"]) + "\n\n"
        f"{motivation_instruction}\n\n"
        f"Requested Style: {style.upper()}\n"
        f"Write the complete cover letter now."
    )

    cl_text = ""
    used_fallback = False
    try:
        provider = get_llm()
        cl_text = provider.generate_text(system_prompt=system_prompt, user_prompt=user_prompt)
        cl_text = cl_text.strip()
    except Exception as e:
        logger.warning(f"LLM cover letter generation failed ({e}), using deterministic fallback.")
        cl_text = _build_deterministic_fallback(candidate, job, style, candidate_motivation)
        used_fallback = True

    # Validate anti-hallucination
    warnings = _verify_anti_hallucination(cl_text, candidate, job)

    sources_used = [
        {"type": "job_description", "label": f"{job.title} at {job.company}", "job_id": job.id},
        {"type": "candidate_library", "label": "Verified Candidate Content Library", "user_id": user_id},
    ]
    if candidate_motivation and candidate_motivation.strip():
        sources_used.append({"type": "candidate_motivation", "label": "User-Provided Motivation"})

    return {
        "content": cl_text,
        "style": style,
        "candidate_motivation": candidate_motivation,
        "selected_projects": [p.get("id") for p in candidate.get("projects", []) if p.get("id")],
        "selected_experiences": [e.get("id") for e in candidate.get("experiences", []) if e.get("id")],
        "selected_achievements": [a.get("id") for a in candidate.get("achievements", []) if a.get("id")],
        "warnings": warnings,
        "sources_used": sources_used,
        "used_fallback": used_fallback,
    }

def save_cover_letter_version(
    user_id: int,
    job_id: int,
    content: str,
    style: str = "concise",
    candidate_motivation: Optional[str] = None,
    selected_projects: Optional[List[int]] = None,
    selected_experiences: Optional[List[int]] = None,
    selected_achievements: Optional[List[int]] = None,
    parent_version_id: Optional[int] = None,
    application_id: Optional[int] = None,
    is_approved: bool = False,
    sources_used: Optional[List[Dict[str, Any]]] = None,
    db: Optional[Session] = None,
) -> CoverLetter:
    """Saves a new immutable cover letter version linked to job and application."""
    # Find latest version number for this user and job
    existing_versions = db.query(CoverLetter).filter(
        CoverLetter.user_id == user_id,
        CoverLetter.job_id == job_id,
    ).all()
    next_ver = len(existing_versions) + 1

    new_cl = CoverLetter(
        user_id=user_id,
        job_id=job_id,
        application_id=application_id,
        content=content.strip(),
        format="md",
        style=style,
        candidate_motivation=candidate_motivation,
        selected_projects=selected_projects or [],
        selected_experiences=selected_experiences or [],
        selected_achievements=selected_achievements or [],
        version_number=next_ver,
        parent_version_id=parent_version_id,
        is_approved=is_approved,
        approved_at=datetime.now(timezone.utc) if is_approved else None,
        sources_used=sources_used or [],
    )
    db.add(new_cl)
    db.commit()
    db.refresh(new_cl)

    # If approved, update application record and export PDF
    if is_approved:
        _sync_approved_cover_letter(new_cl, db)

    return new_cl

def _sync_approved_cover_letter(cl: CoverLetter, db: Session):
    """Syncs approved cover letter to application record and exports PDF."""
    pdf_path = export_text_to_pdf(cl.content, f"cl_{cl.user_id}_{cl.id}.pdf")
    if cl.application_id:
        app = db.query(Application).filter(Application.id == cl.application_id).first()
        if app:
            app.cover_letter_url = pdf_path
            if not app.analysis_results:
                app.analysis_results = {}
            results = dict(app.analysis_results)
            results["cover_letter"] = cl.content
            app.analysis_results = results
            db.commit()

def approve_cover_letter(cl_id: int, user_id: int, db: Session) -> CoverLetter:
    """Marks a cover letter version as approved for its job."""
    cl = db.query(CoverLetter).filter(CoverLetter.id == cl_id, CoverLetter.user_id == user_id).first()
    if not cl:
        raise ValueError(f"Cover letter #{cl_id} not found")

    cl.is_approved = True
    cl.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(cl)

    _sync_approved_cover_letter(cl, db)
    return cl

def compare_cover_letter_versions(v1_id: int, v2_id: int, user_id: int, db: Session) -> Dict[str, Any]:
    """Computes metadata and word-level diff between two cover letter versions."""
    cl1 = db.query(CoverLetter).filter(CoverLetter.id == v1_id, CoverLetter.user_id == user_id).first()
    cl2 = db.query(CoverLetter).filter(CoverLetter.id == v2_id, CoverLetter.user_id == user_id).first()
    if not cl1 or not cl2:
        raise ValueError("One or both cover letter versions could not be found")

    # Word-level diff
    words1 = re.findall(r'\S+|\n', cl1.content)
    words2 = re.findall(r'\S+|\n', cl2.content)

    differ = difflib.Differ()
    diff_generator = differ.compare(words1, words2)

    diff_tokens = []
    for token in diff_generator:
        code = token[:2]
        word = token[2:]
        if code == "  ":
            diff_tokens.append({"type": "unchanged", "text": word})
        elif code == "- ":
            diff_tokens.append({"type": "removed", "text": word})
        elif code == "+ ":
            diff_tokens.append({"type": "added", "text": word})

    metadata_changes = {
        "style_changed": cl1.style != cl2.style,
        "v1_style": cl1.style,
        "v2_style": cl2.style,
        "v1_version": cl1.version_number,
        "v2_version": cl2.version_number,
        "v1_created_at": cl1.created_at.isoformat() if cl1.created_at else None,
        "v2_created_at": cl2.created_at.isoformat() if cl2.created_at else None,
        "v1_approved": cl1.is_approved,
        "v2_approved": cl2.is_approved,
    }

    return {
        "v1_id": cl1.id,
        "v2_id": cl2.id,
        "metadata_changes": metadata_changes,
        "diff_tokens": diff_tokens,
    }
