import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.models.candidate import (
    UserProfile,
    CandidateEducation,
    CandidateExperience,
    Project,
    UserSkill,
    Skill,
    Achievement,
    CourseCertification,
    CandidateLeadership,
    CandidateCoursework,
    CandidatePublication,
    CandidateCustomSection,
)

logger = logging.getLogger(__name__)

MODULE_KEYS = [
    "general_info",
    "education",
    "experience",
    "projects",
    "skills",
    "achievements",
    "certifications",
    "leadership",
    "coursework",
    "publications",
    "custom_sections",
]

MODULE_DISPLAY_NAMES = {
    "general_info": "Contact & General Info",
    "education": "Education",
    "experience": "Experience",
    "projects": "Projects",
    "skills": "Technical Skills",
    "achievements": "Achievements & Awards",
    "certifications": "Certifications & Training",
    "leadership": "Leadership & Activities",
    "coursework": "Relevant Coursework",
    "publications": "Publications & Open Source",
    "custom_sections": "Additional Sections",
}

def normalize_bullets(bullets_raw: Any, item_type: str, item_id: int) -> List[Dict[str, Any]]:
    """
    Normalizes bullet items into a consistent dictionary structure with stable IDs.
    Handles raw strings, dicts, and nested lists.
    """
    if not bullets_raw:
        return []
    
    if isinstance(bullets_raw, str):
        lines = [line.strip().lstrip("-*• ").strip() for line in bullets_raw.split("\n") if line.strip()]
        bullets_raw = lines

    normalized = []
    for idx, b in enumerate(bullets_raw):
        if isinstance(b, dict):
            b_id = b.get("id") or f"{item_type}_{item_id}_b{idx}"
            text = b.get("text") or b.get("description") or ""
            metric = b.get("metric")
        elif isinstance(b, str):
            b_id = f"{item_type}_{item_id}_b{idx}"
            text = b
            metric = None
        else:
            continue

        clean_text = str(text).strip().lstrip("-*• ").strip()
        if clean_text:
            normalized.append({
                "id": b_id,
                "text": clean_text,
                "original": clean_text,
                "metric": metric,
                "item_id": item_id,
                "item_type": item_type
            })
    return normalized


def load_candidate_library(user_id: int, db: Session) -> Dict[str, Any]:
    """
    Loads all 11 modules of verified candidate data from the database.
    Ensures every item has a normalized ID, title, dates, and bullets with deterministic bullet IDs.
    """
    # 1. General Info
    profile_row = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    general_info = {}
    if profile_row:
        general_info = {
            "id": profile_row.id,
            "full_name": profile_row.full_name or "",
            "preferred_name": profile_row.preferred_name or "",
            "email": profile_row.email or "",
            "phone": profile_row.phone or "",
            "github": profile_row.github or "",
            "linkedin": profile_row.linkedin or "",
            "portfolio": profile_row.portfolio or profile_row.website or "",
            "current_location": profile_row.current_location or "",
            "bio": profile_row.bio or "",
            "university": profile_row.university or "",
            "degree": profile_row.degree or "",
            "specialization": profile_row.specialization or "",
            "cgpa": profile_row.cgpa,
            "graduation_year": profile_row.graduation_year,
            "coursework": profile_row.coursework or [],
        }

    # 2. Education
    edu_rows = db.query(CandidateEducation).filter(
        CandidateEducation.user_id == user_id,
        CandidateEducation.is_archived.is_(False)
    ).all()
    educations = []
    for e in edu_rows:
        bullets = normalize_bullets(e.bullets, "edu", e.id)
        start = str(e.start_year) if e.start_year else ""
        end = str(e.graduation_year) if e.graduation_year else ""
        spec = e.specialization or ""
        cw = e.coursework or []
        cgpa_val = e.cgpa
        loc = e.location or ""
        deg = e.degree or "Bachelor of Technology"
        
        # Enrich from profile_row if available
        if profile_row:
            if not spec and profile_row.specialization:
                spec = profile_row.specialization
            if not cw and profile_row.coursework:
                cw = profile_row.coursework
            if not cgpa_val and profile_row.cgpa:
                cgpa_val = profile_row.cgpa
            if not loc and profile_row.current_location:
                loc = profile_row.current_location
            # If graduation year looks like a typo (< 2015 for early career), fallback to profile_row
            if (not end or (e.graduation_year and e.graduation_year < 2015)) and profile_row.graduation_year:
                end = str(profile_row.graduation_year)
                if not start:
                    start = str(profile_row.graduation_year - 4)

        dates = f"{start} -- {end}".strip(" -")
        educations.append({
            "id": e.id,
            "institution": e.institution,
            "degree": deg,
            "field_of_study": spec,
            "specialization": spec,
            "location": loc,
            "start_date": start,
            "end_date": end,
            "dates": dates,
            "cgpa": cgpa_val,
            "gpa": cgpa_val,
            "gpa_scale": e.gpa_scale or "10.0",
            "honors": e.honors or "",
            "coursework": cw,
            "bullets": bullets,
            "verification_status": e.verification_status or "self_attested",
            "evidence_url": e.evidence_url,
            "is_visible": e.is_visible,
        })

    # 3. Experience
    exp_rows = db.query(CandidateExperience).filter(
        CandidateExperience.user_id == user_id,
        CandidateExperience.is_archived.is_(False)
    ).all()
    experiences = []
    for exp in exp_rows:
        bullets = normalize_bullets(exp.bullets, "exp", exp.id)
        if not bullets:
            # Fallback to synthesis using XYZ formula so no experience has 0 bullets
            from app.services.resume_compiler.section_renderers import synthesize_experience_bullets
            syn_raw = synthesize_experience_bullets({
                "company": exp.company,
                "title": exp.title,
                "technologies": exp.technologies or [],
                "description": exp.description or exp.responsibilities or "",
            })
            bullets = normalize_bullets(syn_raw, "exp", exp.id)
        experiences.append({
            "id": exp.id,
            "company": exp.company,
            "title": exp.title,
            "location": exp.location or "",
            "start_date": exp.start_date or "",
            "end_date": "Present" if exp.currently_working else (exp.end_date or ""),
            "is_current": bool(exp.currently_working),
            "experience_type": exp.experience_type or "employment",
            "months_of_experience": exp.months_of_experience or 0,
            "technologies": exp.technologies or [],
            "bullets": bullets,
            "description": exp.description or "",
            "verification_status": exp.verification_status or "self_attested",
            "evidence_url": exp.evidence_url,
            "is_visible": exp.is_visible,
        })

    # 4. Projects
    proj_rows = db.query(Project).filter(
        Project.user_id == user_id,
        Project.is_archived.is_(False)
    ).all()
    projects = []
    for p in proj_rows:
        bullets = normalize_bullets(p.bullets, "proj", p.id)
        if not bullets:
            # Fallback to highlights, description or personal_contribution
            raw_sources = p.highlights or ([p.personal_contribution] if p.personal_contribution else [p.description] if p.description else [])
            bullets = normalize_bullets(raw_sources, "proj", p.id)
        
        techs = p.technologies or []
        if isinstance(techs, str):
            techs = [t.strip() for t in techs.split(",") if t.strip()]

        if not bullets:
            # Fallback to synthesis using XYZ formula with quantifiable metrics
            from app.services.resume_compiler.section_renderers import synthesize_project_bullets
            syn_raw = synthesize_project_bullets({
                "name": p.name,
                "role": p.role or "Lead Developer",
                "technologies": techs,
                "description": p.description or "",
            })
            bullets = normalize_bullets(syn_raw, "proj", p.id)

        start = p.start_date or ""
        end = p.end_date or ""
        dates = f"{start} -- {end}".strip(" -") if (start or end) else ""

        projects.append({
            "id": p.id,
            "name": p.name,
            "role": p.role or "Lead Developer",
            "technologies": techs,
            "github": p.github,
            "live_link": p.live_link,
            "start_date": start,
            "end_date": end,
            "dates": dates,
            "description": p.description or "",
            "problem": p.problem or "",
            "personal_contribution": p.personal_contribution or "",
            "bullets": bullets,
            "verification_status": p.verification_status or "self_attested",
            "evidence_url": p.evidence_url,
            "is_visible": p.is_visible,
        })

    # 5. Skills
    user_skills = db.query(UserSkill, Skill).join(Skill, UserSkill.skill_id == Skill.id).filter(
        UserSkill.user_id == user_id,
        UserSkill.is_archived.is_(False)
    ).all()
    skills = []
    for us, s in user_skills:
        skills.append({
            "id": us.skill_id,
            "name": s.name,
            "category": us.category or "General",
            "proficiency_level": us.proficiency_level or "Advanced",
            "confidence": us.confidence or 5,
            "years_used": us.years_used or 0.0,
            "verification_status": us.verification_status or "self_attested",
            "is_visible": us.is_visible,
        })

    # 6. Achievements
    ach_rows = db.query(Achievement).filter(
        Achievement.user_id == user_id,
        Achievement.is_archived.is_(False)
    ).all()
    achievements = []
    for a in ach_rows:
        bullets = normalize_bullets(a.bullets, "ach", a.id)
        achievements.append({
            "id": a.id,
            "title": a.title,
            "category": a.category or "hackathon",
            "issuer_or_event": a.issuer_or_event or "",
            "year_or_date": a.year_or_date or "",
            "description": a.description or "",
            "impact_metrics": a.impact_metrics or "",
            "url": a.url or "",
            "bullets": bullets,
            "verification_status": a.verification_status or "self_attested",
            "evidence_url": a.evidence_url,
            "is_visible": a.is_visible,
        })

    # 7. Certifications
    cert_rows = db.query(CourseCertification).filter(
        CourseCertification.user_id == user_id,
        CourseCertification.is_archived.is_(False)
    ).all()
    certifications = []
    for c in cert_rows:
        bullets = normalize_bullets(c.bullets, "cert", c.id)
        certifications.append({
            "id": c.id,
            "name": c.name,
            "issuer": c.issuer or "",
            "issue_date": c.issue_date or "",
            "expiry_date": c.expiry_date or "",
            "credential_id": c.credential_id or "",
            "credential_url": c.credential_url or "",
            "skills_covered": c.skills_covered or [],
            "bullets": bullets,
            "verification_status": c.verification_status or "self_attested",
            "evidence_url": c.evidence_url,
            "is_visible": c.is_visible,
        })

    # 8. Leadership & Extracurriculars
    lead_rows = db.query(CandidateLeadership).filter(
        CandidateLeadership.user_id == user_id,
        CandidateLeadership.is_archived.is_(False)
    ).all()
    leadership = []
    for l in lead_rows:
        bullets = normalize_bullets(l.bullets, "lead", l.id)
        leadership.append({
            "id": l.id,
            "organization": l.organization,
            "role": l.role,
            "role_title": l.role,
            "category": l.category or "club",
            "start_date": l.start_date or "",
            "end_date": "Present" if l.currently_active else (l.end_date or ""),
            "currently_active": bool(l.currently_active),
            "description": l.description or "",
            "bullets": bullets,
            "verification_status": l.verification_status or "self_attested",
            "evidence_url": l.evidence_url,
            "is_visible": l.is_visible,
        })

    # 9. Relevant Coursework
    course_rows = db.query(CandidateCoursework).filter(
        CandidateCoursework.user_id == user_id,
        CandidateCoursework.is_archived.is_(False)
    ).all()
    coursework = []
    for cr in course_rows:
        coursework.append({
            "id": cr.id,
            "course_name": cr.course_name,
            "course_code": cr.course_code or "",
            "institution": cr.institution or "",
            "term_or_year": cr.term_or_year or "",
            "grade": cr.grade or "",
            "skills_learned": cr.skills_learned or [],
            "description": cr.description or "",
            "verification_status": cr.verification_status or "self_attested",
            "is_visible": cr.is_visible,
        })

    # 10. Publications & Open Source
    pub_rows = db.query(CandidatePublication).filter(
        CandidatePublication.user_id == user_id,
        CandidatePublication.is_archived.is_(False)
    ).all()
    publications = []
    for p in pub_rows:
        bullets = normalize_bullets(p.bullets, "pub", p.id)
        publications.append({
            "id": p.id,
            "title": p.title,
            "publication_type": p.publication_type or "conference_paper",
            "venue_or_publisher": p.venue_or_publisher or "",
            "publisher_or_venue": p.venue_or_publisher or "",
            "publication_date": p.publication_date or "",
            "authors": p.authors or [],
            "url": p.url or "",
            "doi_or_url": p.url or p.doi_or_id or "",
            "doi_or_id": p.doi_or_id or "",
            "description": p.description or "",
            "bullets": bullets,
            "verification_status": p.verification_status or "self_attested",
            "is_visible": p.is_visible,
        })

    # 11. Custom Sections
    custom_rows = db.query(CandidateCustomSection).filter(
        CandidateCustomSection.user_id == user_id,
        CandidateCustomSection.is_archived.is_(False)
    ).all()
    custom_sections = []
    for cs in custom_rows:
        bullets = normalize_bullets(cs.bullets, "cust", cs.id)
        custom_sections.append({
            "id": cs.id,
            "section_title": cs.section_title or "Additional Experience",
            "title": cs.title,
            "item_title": cs.title,
            "subtitle": cs.subtitle or "",
            "date_or_year": cs.date_or_year or "",
            "dates": cs.date_or_year or "",
            "location": cs.location or "",
            "description": cs.description or "",
            "url": cs.url or "",
            "bullets": bullets,
            "verification_status": cs.verification_status or "self_attested",
            "is_visible": cs.is_visible,
        })

    return {
        "user_id": user_id,
        "general_info": general_info,
        "education": educations,
        "experience": experiences,
        "projects": projects,
        "skills": skills,
        "achievements": achievements,
        "certifications": certifications,
        "leadership": leadership,
        "coursework": coursework,
        "publications": publications,
        "custom_sections": custom_sections,
    }
