import logging
from app.services.llm.groq_provider import GroqProvider

logger = logging.getLogger(__name__)
llm = GroqProvider()

def generate_tailored_resume(master_profile: str, job_description: str, job_title: str, is_latex: bool = False) -> str:
    """
    Takes the master profile and tailors the bullet points to match the job description.
    Rules: Strictly factual, no hallucinated experience.
    """
    if is_latex:
        system_prompt = "You are an expert LaTeX editor. Read the provided LaTeX resume template and tailor the text content to the job description. Do NOT alter the LaTeX formatting, commands, styling, or document structure. Return the FULL updated LaTeX document in pure raw text format without markdown code blocks."
    else:
        system_prompt = "You are a professional resume writer. Tailor the following profile to the job description without fabricating any experience. Output the tailored resume in pure Markdown format."

    user_prompt = f"Profile/Template:\n{master_profile}\n\nJob Description:\n{job_description}\n\nTarget Job Title: {job_title}"
    
    content = llm.generate_text(system_prompt=system_prompt, user_prompt=user_prompt)
    
    if is_latex:
        if content.startswith("```latex"):
            content = content[8:-3]
        elif content.startswith("```tex"):
            content = content[6:-3]
        elif content.startswith("```"):
            content = content[3:-3]
        return content.strip()
    return content

def generate_cover_letter(master_profile: dict, job_company: str, job_title: str, match_strengths: list) -> str:
    """
    Generates a personalized cover letter.
    """
    strengths_str = ", ".join(match_strengths) if match_strengths else "relevant technical skills"

    system_prompt = "You are a professional career coach. Write a concise, compelling cover letter (max 300 words) tailored to the company and role based on the user's profile and strengths. Output in pure text/markdown format."
    user_prompt = f"Profile:\n{master_profile}\n\nCompany: {job_company}\nJob Title: {job_title}\nKey Strengths for this role: {strengths_str}"
    
    return llm.generate_text(system_prompt=system_prompt, user_prompt=user_prompt)

def analyze_ats_keywords(resume_text: str, job_description: str) -> dict:
    """
    Analyzes ATS keywords and compares the resume against the job description.
    """
    system_prompt = "You are an expert ATS (Applicant Tracking System). Analyze the provided resume against the job description. Output a JSON object with keys: 'ats_score' (int 0-100), 'missing_keywords' (list of str), 'matched_keywords' (list of str), 'improvement_suggestions' (list of str)."
    user_prompt = f"Resume:\n{resume_text}\n\nJob Description:\n{job_description}"
    
    return llm.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)

