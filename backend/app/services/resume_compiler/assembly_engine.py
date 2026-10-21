import json
import logging
from typing import Dict, List, Any, Optional

from app.services.llm import get_llm
from .refiner import refine_bullet_truthfully

logger = logging.getLogger(__name__)

ALL_SECTIONS = [
    "general_info",
    "education",
    "skills",
    "projects",
    "experience",
    "achievements",
    "certifications",
    "leadership",
    "coursework",
    "publications",
    "custom_sections",
]

def detect_candidate_level(candidate_data: Dict[str, Any]) -> str:
    """
    Determines if candidate is early-career / student or experienced.
    """
    gen_info = candidate_data.get("general_info") or {}
    experiences = candidate_data.get("experience") or []
    
    total_months = sum(e.get("months_of_experience", 0) for e in experiences)
    grad_year = gen_info.get("graduation_year")
    
    # If graduation year is recent or future, or experience < 24 months
    if grad_year and grad_year >= 2024:
        return "early_career"
    if total_months < 24:
        return "early_career"
    return "experienced"


def detect_role_type(job_title: str, job_desc: str) -> str:
    """
    Categorizes job role type: backend, frontend, fullstack, ai_ml, systems, research, general.
    """
    combined = f"{job_title} {job_desc}".lower()
    if any(k in combined for k in ["research", "phd", "scientist", "academic", "fellow"]):
        return "research"
    if any(k in combined for k in ["backend", "distributed", "api", "database", "infrastructure"]):
        return "backend"
    if any(k in combined for k in ["ai", "machine learning", "ml", "nlp", "llm", "deep learning"]):
        return "ai_ml"
    if any(k in combined for k in ["frontend", "ui", "ux", "react", "next.js", "web"]):
        return "frontend"
    return "fullstack"


def score_item_relevance(item_tokens: List[str], job_keywords: List[str]) -> float:
    """Calculates keyword overlap score."""
    if not job_keywords or not item_tokens:
        return 0.0
    item_set = set(t.lower() for t in item_tokens)
    score = 0.0
    for kw in job_keywords:
        kw_l = kw.lower()
        if kw_l in item_set:
            score += 2.0
        elif any(kw_l in tok for tok in item_set):
            score += 1.0
    return score


def generate_assembly_plan(
    candidate_data: Dict[str, Any],
    job: Dict[str, Any],
    user_locks: Optional[Dict[str, Any]] = None,
    custom_instructions: Optional[str] = None,
    target_page_length: int = 1,
) -> Dict[str, Any]:
    """
    Generates a structured, validated resume assembly plan.
    Selects, ranks, and orders modules and bullets tailored to the target job.
    Never alters user-locked choices.
    """
    user_locks = user_locks or {}
    locked_sections = set(user_locks.get("locked_sections") or [])
    locked_order = user_locks.get("locked_order")
    locked_bullets = dict(user_locks.get("locked_bullets") or {})
    locked_items = dict(user_locks.get("locked_items") or {})

    # Support nested user_locks format: {"sections": {sec_name: {"locked_ids": [...], "locked": True, ...}}}
    if isinstance(user_locks.get("sections"), dict):
        for sec_name, sec_cfg in user_locks["sections"].items():
            if isinstance(sec_cfg, dict):
                if sec_cfg.get("locked"):
                    locked_sections.add(sec_name)
                if "locked_ids" in sec_cfg:
                    locked_items.setdefault(sec_name, []).extend(sec_cfg["locked_ids"])
                if "locked_bullets" in sec_cfg:
                    locked_bullets.setdefault(sec_name, {}).update(sec_cfg["locked_bullets"])

    job_title = job.get("title") or "Software Engineer"
    job_company = job.get("company") or "Company"
    job_desc = job.get("description") or ""
    req_skills = job.get("required_skills_json") or job.get("tech_stack_json") or []
    if isinstance(req_skills, str):
        try:
            req_skills = json.loads(req_skills)
        except Exception:
            req_skills = [s.strip() for s in req_skills.split(",") if s.strip()]

    candidate_level = detect_candidate_level(candidate_data)
    role_type = detect_role_type(job_title, job_desc)

    # 1. Determine recommended template and section ordering
    if role_type == "research":
        default_template = "academic_research"
        default_order = ["general_info", "education", "publications", "experience", "skills", "projects", "coursework"]
    elif candidate_level == "early_career":
        default_template = "project_focused" if role_type != "backend" else "compact_technical"
        default_order = ["general_info", "education", "skills", "projects", "experience", "achievements"]
    else:
        default_template = "clean_ats"
        default_order = ["general_info", "experience", "skills", "projects", "education", "achievements"]

    # If user provided locked order, respect it
    if locked_order and isinstance(locked_order, list):
        section_order = [s for s in locked_order if s in ALL_SECTIONS]
        for s in ALL_SECTIONS:
            if s not in section_order:
                section_order.append(s)
    else:
        section_order = default_order
        for s in ALL_SECTIONS:
            if s not in section_order:
                section_order.append(s)

    # 2. Extract job keywords for scoring
    job_keywords = list(req_skills)
    job_words = [w.strip(",.;()").lower() for w in f"{job_title} {job_desc}".split() if len(w) > 3]
    job_keywords.extend(job_words[:30])

    # 3. Analyze and select items for each module
    sections: Dict[str, Any] = {}

    # --- GENERAL INFO ---
    sections["general_info"] = {
        "included": True,
        "locked": "general_info" in locked_sections,
        "reason": "Standard contact details and verified credentials",
        "contact_fields": ["email", "phone", "location", "linkedin", "github", "portfolio"],
        "matching_requirements": ["Direct candidate contact information"]
    }

    def _item_id(item: Any, default: Any = None) -> Any:
        if isinstance(item, dict):
            return item.get("id", default)
        return getattr(item, "id", default)

    def _bullet_id(b: Any, default: Any = None) -> Any:
        if isinstance(b, dict):
            return b.get("id", default)
        return getattr(b, "id", default)

    # --- EDUCATION ---
    edu_list = candidate_data.get("education") or []
    has_edu = len(edu_list) > 0
    sections["education"] = {
        "included": has_edu,
        "locked": "education" in locked_sections,
        "reason": "Provides required academic qualifications, degree, and GPA",
        "selected_item_ids": [_item_id(e, idx) for idx, e in enumerate(edu_list)],
        "matching_requirements": ["Degree in Computer Science or technical discipline"]
    }

    # --- SKILLS ---
    skills_list = candidate_data.get("skills") or []
    matched_skills = []
    other_skills = []
    for idx, sk in enumerate(skills_list):
        if isinstance(sk, dict):
            sk_name = sk.get("name", "")
            sk_id = sk.get("id", idx)
        else:
            sk_name = str(sk)
            sk_id = getattr(sk, "id", idx)
        if any(sk_name.lower() in kw.lower() or kw.lower() in sk_name.lower() for kw in job_keywords):
            matched_skills.append(sk_id)
        else:
            other_skills.append(sk_id)
    
    # Cap skills for 1-page target
    selected_skill_ids = matched_skills + other_skills[:max(0, 24 - len(matched_skills))]
    sections["skills"] = {
        "included": len(skills_list) > 0,
        "locked": "skills" in locked_sections,
        "reason": f"Directly demonstrates {len(matched_skills)} core technical skills required for the role",
        "selected_item_ids": selected_skill_ids,
        "matching_requirements": req_skills[:6] if req_skills else ["Technical stack proficiency"]
    }

    # --- PROJECTS ---
    proj_list = candidate_data.get("projects") or []
    scored_projs = []
    TRIVIAL_PROJECT_PATTERNS = {
        "neetcode", "leetcode", "dsa", "algorithm", "practice", "interview-prep",
        "submission", "problem", "exercise", "homework", "sample", "test-repo", "temp"
    }
    for p in proj_list:
        p_name = (p.get("name") or p.get("title") or "").strip().lower()
        desc = (p.get("description") or "").lower()
        techs = [str(t).lower() for t in (p.get("technologies") or [])]
        tokens = techs + [p_name, desc]
        sc = score_item_relevance(tokens, job_keywords)

        # Penalize trivial/exercise repos
        if any(pat in p_name for pat in TRIVIAL_PROJECT_PATTERNS):
            sc -= 12.0
        # Penalize repos with empty description and 0 bullets
        if not p.get("description") and not p.get("bullets"):
            sc -= 4.0

        # Reward projects with architectural depth and modern tech stacks
        tech_set = set(techs)
        architectural_tech = {"fastapi", "kafka", "redis", "postgresql", "docker", "kubernetes", "aws", "nginx", "pytorch", "microservices"}
        overlap = tech_set & architectural_tech
        if overlap:
            sc += 2.0 + (len(overlap) * 0.5)

        # Reward projects that have curated bullets
        b_count = len(p.get("bullets") or [])
        if b_count >= 2:
            sc += 3.0

        scored_projs.append((sc, p))
    scored_projs.sort(key=lambda x: x[0], reverse=True)

    # For 1-page target, pick top 2 or 3 projects
    max_projs = 3 if candidate_level == "early_career" else 2
    forced_projs = locked_items.get("projects") or []
    if forced_projs:
        selected_proj_ids = list(forced_projs)
    else:
        selected_proj_ids = [p["id"] for sc, p in scored_projs[:max_projs]]
    
    proj_selected_bullets: Dict[str, List[str]] = {}
    for sc, p in scored_projs:
        p_id = str(p["id"])
        if p["id"] in selected_proj_ids:
            all_b = p.get("bullets") or []
            if p_id in locked_bullets and locked_bullets[p_id]:
                proj_selected_bullets[p_id] = locked_bullets[p_id]
            else:
                b_ids = [b["id"] for b in all_b[:3] if isinstance(b, dict) and b.get("id")]
                if not b_ids:
                    # Provide default deterministic IDs so renderer never receives empty list
                    b_ids = [f"proj_{p_id}_b0", f"proj_{p_id}_b1"]
                proj_selected_bullets[p_id] = b_ids

    sections["projects"] = {
        "included": len(selected_proj_ids) > 0,
        "locked": "projects" in locked_sections,
        "reason": "Exhibits verified hands-on development, architecture, and technology implementation",
        "selected_item_ids": selected_proj_ids,
        "items": [{"id": pid} for pid in selected_proj_ids],
        "selected_bullets": proj_selected_bullets,
        "matching_requirements": [f"Practical project experience with {t}" for t in req_skills[:3]] if req_skills else ["Real-world software engineering"]
    }

    # --- EXPERIENCE ---
    exp_list = candidate_data.get("experience") or []
    scored_exps = []
    for exp in exp_list:
        tokens = (exp.get("technologies") or []) + [exp.get("title", ""), exp.get("company", ""), exp.get("description", "")]
        sc = score_item_relevance(tokens, job_keywords)
        # boost current or longer experiences
        if exp.get("is_current"):
            sc += 2.0
        b_count = len(exp.get("bullets") or [])
        if b_count >= 2:
            sc += 2.0
        scored_exps.append((sc, exp))
    scored_exps.sort(key=lambda x: x[0], reverse=True)

    max_exps = 2 if candidate_level == "early_career" else 3
    selected_exp_ids = locked_items.get("experience") or [e["id"] for sc, e in scored_exps[:max_exps]]
    
    exp_selected_bullets: Dict[str, List[str]] = {}
    for sc, exp in scored_exps:
        exp_id = str(exp["id"])
        if exp["id"] in selected_exp_ids:
            all_b = exp.get("bullets") or []
            if exp_id in locked_bullets and locked_bullets[exp_id]:
                exp_selected_bullets[exp_id] = locked_bullets[exp_id]
            else:
                b_ids = [b["id"] for b in all_b[:3] if isinstance(b, dict) and b.get("id")]
                if not b_ids:
                    # Provide default deterministic IDs so renderer never receives empty list
                    b_ids = [f"exp_{exp_id}_b0", f"exp_{exp_id}_b1"]
                exp_selected_bullets[exp_id] = b_ids

    sections["experience"] = {
        "included": len(selected_exp_ids) > 0,
        "locked": "experience" in locked_sections,
        "reason": "Demonstrates commercial and software engineering track record",
        "selected_item_ids": selected_exp_ids,
        "items": [{"id": eid} for eid in selected_exp_ids],
        "selected_bullets": exp_selected_bullets,
        "matching_requirements": ["Software engineering industry experience"]
    }

    # --- ACHIEVEMENTS ---
    ach_list = candidate_data.get("achievements") or []
    selected_ach_ids = locked_items.get("achievements") or [_item_id(a, idx) for idx, a in enumerate(ach_list[:2])]
    sections["achievements"] = {
        "included": len(selected_ach_ids) > 0 and (candidate_level == "early_career" or "achievements" in locked_sections),
        "locked": "achievements" in locked_sections,
        "reason": "Hackathon prizes and awards demonstrate peer-recognized problem-solving velocity",
        "selected_item_ids": selected_ach_ids,
        "matching_requirements": ["Competitive problem-solving and rapid delivery"]
    }

    # --- CERTIFICATIONS ---
    cert_list = candidate_data.get("certifications") or []
    sections["certifications"] = {
        "included": "certifications" in locked_sections or (len(cert_list) > 0 and len(selected_exp_ids) <= 1),
        "locked": "certifications" in locked_sections,
        "reason": "Validates formal technical training and certifications",
        "selected_item_ids": [_item_id(c, idx) for idx, c in enumerate(cert_list[:2])],
        "matching_requirements": ["Industry recognized certifications"]
    }

    # --- LEADERSHIP ---
    lead_list = candidate_data.get("leadership") or []
    sections["leadership"] = {
        "included": "leadership" in locked_sections,
        "locked": "leadership" in locked_sections,
        "reason": "Highlights extracurricular initiative and mentorship",
        "selected_item_ids": [_item_id(l, idx) for idx, l in enumerate(lead_list[:2])],
        "matching_requirements": ["Team leadership and cross-functional collaboration"]
    }

    # --- COURSEWORK ---
    course_list = candidate_data.get("coursework") or []
    sections["coursework"] = {
        "included": "coursework" in locked_sections or (candidate_level == "early_career" and len(course_list) > 0 and not sections["experience"]["included"]),
        "locked": "coursework" in locked_sections,
        "reason": "Demonstrates theoretical rigor in core computer science subjects",
        "selected_item_ids": [_item_id(c, idx) for idx, c in enumerate(course_list[:4])],
        "matching_requirements": ["Computer science foundational coursework"]
    }

    # --- PUBLICATIONS ---
    pub_list = candidate_data.get("publications") or []
    sections["publications"] = {
        "included": "publications" in locked_sections or (role_type == "research" and len(pub_list) > 0),
        "locked": "publications" in locked_sections,
        "reason": "Peer-reviewed research contributions and technical publications",
        "selected_item_ids": [_item_id(p, idx) for idx, p in enumerate(pub_list[:2])],
        "matching_requirements": ["Research papers and technical publications"]
    }

    # --- CUSTOM SECTIONS ---
    cust_list = candidate_data.get("custom_sections") or []
    sections["custom_sections"] = {
        "included": "custom_sections" in locked_sections,
        "locked": "custom_sections" in locked_sections,
        "reason": "Custom candidate modules",
        "selected_item_ids": [_item_id(c, idx) for idx, c in enumerate(cust_list)],
        "matching_requirements": ["Additional verified accomplishments"]
    }

    # 4. Propose Truth-Preserving Refinements for key bullets
    refinements: Dict[str, Any] = {}
    
    # Collect top bullets from selected projects and experiences
    bullets_to_refine = []
    for sc, p in scored_projs:
        if p["id"] in selected_proj_ids:
            for b in p.get("bullets") or []:
                if b["id"] in proj_selected_bullets.get(str(p["id"]), []):
                    bullets_to_refine.append((b, p["name"], "project"))

    for sc, exp in scored_exps:
        if exp["id"] in selected_exp_ids:
            for b in exp.get("bullets") or []:
                if b["id"] in exp_selected_bullets.get(str(exp["id"]), []):
                    bullets_to_refine.append((b, exp["company"], "experience"))

    # Refine top 3 bullets that align with job requirements
    target_req = req_skills[0] if req_skills else "asynchronous systems and backend architecture"
    for b_item, context_name, item_kind in bullets_to_refine[:3]:
        b_id = b_item["id"]
        original_text = b_item["text"]
        refinement_result = refine_bullet_truthfully(
            original_bullet=original_text,
            job_requirement=target_req,
            job_title=job_title,
            context_name=context_name,
            custom_instructions=custom_instructions
        )
        refinements[b_id] = {
            "original": original_text,
            "refined": refinement_result["refined_bullet"],
            "reason": refinement_result["reason"],
            "job_requirement": target_req,
            "status": "proposed"
        }

    # Build Complete Plan
    plan = {
        "job_id": job.get("id"),
        "job_title": job_title,
        "job_company": job_company,
        "role_category": role_type,
        "candidate_level": candidate_level,
        "recommended_template": default_template,
        "template_name": default_template,
        "template_options": {
            "font_size": "10pt" if default_template == "compact_technical" else "10.8pt",
            "margins": "0.45in" if default_template == "compact_technical" else "0.5in",
            "spacing": "tight" if default_template == "compact_technical" else "compact",
            "page_target": target_page_length
        },
        "section_order": section_order,
        "selected_modules": [s for s, s_data in sections.items() if s_data.get("included")],
        "sections": sections,
        "refinements": refinements,
        "summary": (
            f"Tailored for {job_title} at {job_company}. Prioritized {len(selected_proj_ids)} core projects "
            f"and {len(selected_skill_ids)} technical skills to target 1-page ATS format."
        )
    }

    return plan
