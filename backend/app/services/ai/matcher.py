import logging
import json
from app.services.llm import get_llm

logger = logging.getLogger(__name__)

def analyze_job_match(
    profile_text: str, 
    job_description: str,
    projects_meta: list = None,
    latex_resume: str = None,
    job_metadata: dict = None
) -> dict:
    """
    Analyzes a job description and scraped metadata against a user's unified profile,
    project metadata, and raw LaTeX resume content to determine matching overlap.
    """
    provider = get_llm()

    system_prompt = (
        "You are an expert technical recruiter and resume builder. Analyze the job description and "
        "extracted job requirements against the candidate's text profile, project metadata (including tech stacks and links), "
        "and their master LaTeX resume format/template.\n\n"
        "Calculate the following dimensions of overlap:\n"
        "1. Resume similarity: Overall content, tone, and experience alignment.\n"
        "2. Skill overlap: Matching technical skills, libraries, and frameworks.\n"
        "3. GitHub/Projects overlap: Alignment of the candidate's projects, technologies, and GitHub descriptions with the job.\n"
        "4. Keyword overlap: Matching key terms and technologies.\n\n"
        "Assess if the projects or LaTeX resume content can be tailored effectively for the role.\n"
        "Respond ONLY in pure JSON format without markdown wrapping.\n"
        "Schema:\n"
        "{\n"
        "  \"match_percentage\": int,\n"
        "  \"resume_similarity\": int,\n"
        "  \"skill_overlap\": int,\n"
        "  \"github_overlap\": int,\n"
        "  \"keyword_overlap\": int,\n"
        "  \"missing_skills\": [\"str\"],\n"
        "  \"strengths\": [\"str\"],\n"
        "  \"weaknesses\": [\"str\"],\n"
        "  \"reasoning\": \"str\"\n"
        "}"
    )

    user_prompt_parts = []
    user_prompt_parts.append(f"Candidate Profile Description:\n{profile_text}")
    
    if latex_resume:
        user_prompt_parts.append(f"Candidate Master LaTeX Resume:\n{latex_resume}")
        
    if projects_meta:
        user_prompt_parts.append(f"Candidate Projects Metadata:\n{json.dumps(projects_meta, indent=2)}")
        
    user_prompt_parts.append(f"Scraped Job Description:\n{job_description}")
    
    if job_metadata:
        user_prompt_parts.append(f"Scraped Job Metadata/Requirements:\n{json.dumps(job_metadata, indent=2)}")

    user_prompt = "\n\n=== SECTION ===\n".join(user_prompt_parts)

    try:
        return provider.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
    except Exception as e:
        logger.error(f"Job match analysis failed: {e}")
        return {
            "match_percentage": 0,
            "resume_similarity": 0,
            "skill_overlap": 0,
            "github_overlap": 0,
            "keyword_overlap": 0,
            "missing_skills": [],
            "strengths": [],
            "weaknesses": ["Analysis failed — check API key configuration"],
            "reasoning": "Failed to analyze job match due to an error."
        }

