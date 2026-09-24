from sqlalchemy.orm import Session
from app.models.candidate import UserProfile, CandidateExperience, Project, UserSkill, Achievement, CourseCertification
from app.models.profile import Profile

def build_profile_text(user_id: int, db: Session) -> str:
    """
    Constructs a unified, markdown-style candidate master knowledge profile description from the normalized SQL tables.
    """
    user_prof = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not user_prof:
        return ""
        
    experiences = db.query(CandidateExperience).filter(CandidateExperience.user_id == user_id).all()
    projects = db.query(Project).filter(Project.user_id == user_id).all()
    user_skills = db.query(UserSkill).filter(UserSkill.user_id == user_id).all()
    achievements = db.query(Achievement).filter(Achievement.user_id == user_id).all()
    courses = db.query(CourseCertification).filter(CourseCertification.user_id == user_id).all()
    
    parts = []
    if user_prof.full_name:
        parts.append(f"Name: {user_prof.full_name}")
    if user_prof.email:
        parts.append(f"Email: {user_prof.email}")
    if user_prof.phone:
        parts.append(f"Phone: {user_prof.phone}")
    if user_prof.github:
        parts.append(f"GitHub Profile: {user_prof.github}")
    if user_prof.linkedin:
        parts.append(f"LinkedIn Profile: {user_prof.linkedin}")
    if user_prof.current_location:
        parts.append(f"Location: {user_prof.current_location}")
        
    if user_prof.degree or user_prof.university:
        edu_details = f"Education: {user_prof.degree or ''} from {user_prof.university or ''}"
        if user_prof.graduation_year:
            edu_details += f" (Graduation: {user_prof.graduation_year})"
        if user_prof.cgpa:
            edu_details += f" (CGPA: {user_prof.cgpa})"
        parts.append(edu_details)
        
    if user_skills:
        parts.append("\nSkills:")
        for us in user_skills:
            parts.append(f"- {us.skill.name} (Years used: {us.years_used}, Confidence level: {us.confidence}/5)")
            
    if experiences:
        parts.append("\nExperience & Internships:")
        for exp in experiences:
            job_type = "Internship" if exp.internship_or_fulltime == "internship" else "Full-time"
            duration = f"{exp.start_date or ''} - {exp.end_date or 'Present'}"
            parts.append(f"- {exp.title} at {exp.company} ({job_type}, {duration}, Months: {exp.months_of_experience})")
            if exp.description:
                parts.append(f"  Description: {exp.description}")
                
    if projects:
        parts.append("\nProjects & Engineering Works:")
        for proj in projects:
            proj_line = f"- {proj.name}"
            if proj.github:
                proj_line += f" (GitHub: {proj.github})"
            if proj.live_link:
                proj_line += f" (Demo: {proj.live_link})"
            parts.append(proj_line)
            if proj.description:
                parts.append(f"  Description: {proj.description}")
            if proj.technologies:
                parts.append(f"  Technologies used: {', '.join(proj.technologies)}")

    if achievements:
        parts.append("\nAchievements, Prizes & Hackathon Wins:")
        for ach in achievements:
            ach_line = f"- {ach.title}"
            if ach.issuer_or_event:
                ach_line += f" ({ach.issuer_or_event})"
            if ach.year_or_date:
                ach_line += f" [{ach.year_or_date}]"
            parts.append(ach_line)
            if ach.description:
                parts.append(f"  Details: {ach.description}")

    if courses:
        parts.append("\nCourses & Certifications:")
        for crs in courses:
            crs_line = f"- {crs.name}"
            if crs.issuer:
                crs_line += f" by {crs.issuer}"
            if crs.issue_date:
                crs_line += f" ({crs.issue_date})"
            parts.append(crs_line)
            if crs.skills_covered:
                parts.append(f"  Skills Covered: {', '.join(crs.skills_covered)}")
            if crs.credential_url:
                parts.append(f"  Credential Link: {crs.credential_url}")

    # Global candidate instructions (always available to every prompt path)
    legacy_profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if legacy_profile and legacy_profile.tailoring_instructions:
        parts.append("\nCandidate notes for AI (follow tone/preferences; never invent facts):")
        parts.append(legacy_profile.tailoring_instructions.strip())
                
    return "\n".join(parts)

