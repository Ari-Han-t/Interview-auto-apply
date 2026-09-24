import logging
import re
import shutil
from app.services.llm import get_llm

logger = logging.getLogger(__name__)

def llm():
    return get_llm()

def extract_clean_latex(text: str) -> str:
    """
    Extracts strictly the raw LaTeX source code from an LLM response,
    stripping markdown fences, conversational commentary, and trailing text.
    """
    if not text:
        return ""
    
    cleaned = text.strip()
    
    # Strip markdown block fences
    if "```" in cleaned:
        # Match code block containing LaTeX
        match = re.search(r'```(?:latex|tex)?\s*([\s\S]*?)\s*```', cleaned, re.IGNORECASE)
        if match:
            cleaned = match.group(1).strip()
        else:
            # Strip loose backticks
            cleaned = re.sub(r'^```(?:latex|tex)?\s*', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            cleaned = cleaned.strip()
            
    # Extract from \documentclass or \begin{document} up to \end{document} if conversational wrappers exist
    doc_start = cleaned.find(r"\documentclass")
    if doc_start == -1:
        doc_start = cleaned.find(r"\begin{document}")
    if doc_start == -1:
        # Check if it starts with comment lines followed by documentclass
        doc_start = 0

    doc_end = cleaned.rfind(r"\end{document}")
    if doc_end != -1:
        cleaned = cleaned[doc_start:doc_end + len(r"\end{document}")]
    elif doc_start > 0:
        cleaned = cleaned[doc_start:]

    # Auto-sanitize double HTTP protocol links
    cleaned = cleaned.replace("http://http://", "http://").replace("https://http://", "https://").replace("http://https://", "https://").replace("https://https://", "https://")

    return cleaned.strip()

def validate_latex_resume(generated_tex: str, original_tex: str, original_skills: list = None) -> tuple[bool, str]:
    """
    Validates a generated LaTeX resume for correctness, balance, formatting, and non-hallucination.
    """
    stripped = generated_tex.strip()
    
    if not stripped:
        return False, "Generated LaTeX resume is empty."

    # 1. Must contain valid LaTeX document commands
    if not (stripped.startswith("\\documentclass") or stripped.startswith("%") or stripped.startswith("\\begin") or "\\begin{document}" in stripped):
        return False, "Output does not start with valid LaTeX commands (e.g. \\documentclass or %). Output must be raw LaTeX code."
        
    if "```" in stripped:
        return False, "Markdown backtick block detected inside LaTeX source."

    # 2. Balanced braces check (ignoring escaped \{, \}, and % comments)
    stack = []
    in_comment = False
    for i, char in enumerate(generated_tex):
        if char == '%' and (i == 0 or generated_tex[i-1] != '\\'):
            in_comment = True
        elif char == '\n':
            in_comment = False
            
        if in_comment:
            continue
            
        if char == '{' and (i == 0 or generated_tex[i-1] != '\\'):
            stack.append(i)
        elif char == '}' and (i == 0 or generated_tex[i-1] != '\\'):
            if not stack:
                return False, f"Unbalanced closed brace '}}' at index {i}."
            stack.pop()
    if stack:
        return False, f"Unbalanced open braces '{{'. There are {len(stack)} unclosed braces remaining."

    # 3. Balanced begin/end environments
    begins = re.findall(r'\\begin\{([^}]+)\}', generated_tex)
    ends = re.findall(r'\\end\{([^}]+)\}', generated_tex)
    if len(begins) != len(ends):
        return False, f"The number of \\begin environments ({len(begins)}) does not match \\end environments ({len(ends)})."

    # 4. Check for duplicate sections
    sections = re.findall(r'\\section\{([^}]+)\}', generated_tex)
    section_counts = {}
    for sec in sections:
        sec_name = sec.lower().strip()
        section_counts[sec_name] = section_counts.get(sec_name, 0) + 1
        if section_counts[sec_name] > 1:
            return False, f"Duplicate section detected: '{sec}'. There must be exactly one of each section."

    # 5. Check for double protocol links
    if "http://http://" in generated_tex or "https://http://" in generated_tex or "http://https://" in generated_tex:
        return False, "Double HTTP protocol link detected (e.g. 'http://http://'). Hyperlinks must be clean and valid."

    # 6. Strict Tech non-hallucination check
    allowed_techs = set()
    if original_skills:
        for sk in original_skills:
            if isinstance(sk, dict) and "name" in sk:
                allowed_techs.add(sk["name"].lower().strip())
            elif isinstance(sk, str):
                allowed_techs.add(sk.lower().strip())
                
    original_tex_lower = original_tex.lower()
    
    hallucination_checks = [
        "kubernetes", "graphql", "aws", "gcp", "pytorch", "tensorflow", "microservices", 
        "distributed systems", "enterprise systems", "multiple clients"
    ]
    for tech in hallucination_checks:
        if tech in generated_tex.lower() and tech not in original_tex_lower and tech not in allowed_techs:
            return False, f"Hallucinated technology/term detected: '{tech}'. Do not introduce any skills, technologies, or terms not already present in the user's resume/profile."

    return True, "Valid"

def generate_tailored_resume(
    master_profile: str, 
    job_description: str, 
    job_title: str, 
    is_latex: bool = False, 
    extracted_projects: list = None,
    original_skills: list = None,
    master_knowledge_base: dict = None,
    user_instructions: str = None,
    raw_resume_text: str = None,
) -> str:
    """
    Takes the master profile and complete candidate database (achievements, courses, projects, skills, experience)
    and tailors the resume bullet points and selected items to match the job description.
    Rules: Strictly factual, no hallucinated experience, valid LaTeX syntax, self-correction.
    Optional user_instructions = free-form candidate guidance; raw_resume_text = original uploaded resume content.
    """
    import json
    
    if is_latex:
        system_prompt = (
            "You are an expert LaTeX resume writer.\n"
            "Your task is to tailor the candidate's LaTeX resume to highlight skills, projects, achievements, hackathon wins, and courses that match the job description.\n\n"
            "STRICT RULES:\n"
            "1. Output ONLY the raw LaTeX source code directly. Do NOT wrap output in markdown code blocks like ```latex or ```tex, and do NOT include any conversational text (e.g. 'Here is your resume'). The output must start with the LaTeX document definition (e.g. \\documentclass or %) and end with \\end{document}.\n"
            "2. ABSOLUTELY NO HALLUCINATIONS. Do NOT invent or add any technologies, frameworks, libraries, certifications, tools, metrics, achievements, or experience that are not present in the user's original profile, knowledge base, or resume template.\n"
            "3. PRESERVE ORIGINAL STRUCTURE AND FORMATTING. Improve action verbs, readability, and highlight keywords supported by the candidate's master knowledge base. Maintain all formatting, spacing, margins, indentation, and environments.\n"
            "4. PRESERVE LINKS. Never modify, rewrite, or prepend extra protocols to URLs, GitHub links, deployed app links, IP addresses, or domain names. Do NOT output duplicate URLs or duplicate sections.\n"
            "5. SYNTAX INTEGRITY: Ensure perfectly balanced braces and environments. Every \\begin{env} MUST have a matching \\end{env}, and every '{' must have a matching '}'. Never omit closing brackets or document tags.\n"
            "6. CANDIDATE INSTRUCTIONS: If candidate instructions are provided below, follow their tone, emphasis, and content preferences — but NEVER invent facts to satisfy them.\n"
        )
        if extracted_projects:
            system_prompt += "You have been provided a list of extracted, highly relevant GitHub projects. You MUST intelligently locate the 'Projects' section in the LaTeX file and insert/replace existing projects with these relevant projects, adhering strictly to the existing LaTeX structure and itemization. "
    else:
        system_prompt = (
            "You are a professional resume writer. Tailor the following profile to the job description "
            "using the candidate's master knowledge base without fabricating any experience. "
            "Output the tailored resume in pure Markdown format. "
            "If candidate instructions are provided, follow their tone and emphasis — never invent facts."
        )

    user_prompt = f"Profile/Template:\n{master_profile}\n\nJob Description:\n{job_description}\n\nTarget Job Title: {job_title}"

    if raw_resume_text and raw_resume_text.strip():
        # Avoid re-sending when it's identical to a latex template blob
        if raw_resume_text.strip() != (master_profile or "").strip():
            user_prompt += (
                "\n\n## Original resume as uploaded (source of truth for wording/tone the candidate already wrote)\n"
                f"{raw_resume_text.strip()}"
            )

    if user_instructions and user_instructions.strip():
        user_prompt += (
            "\n\n## Candidate instructions (global — always follow unless they conflict with facts or the job)\n"
            f"{user_instructions.strip()}"
        )

    if master_knowledge_base:
        user_prompt += f"\n\nCandidate Master Knowledge Base (Achievements, Wins, Courses, Projects, Skills):\n{json.dumps(master_knowledge_base, indent=2)}"
    if extracted_projects:
        user_prompt += f"\n\nExtracted Relevant Projects to Include:\n{json.dumps(extracted_projects, indent=2)}"

    max_retries = 3
    feedback = ""
    content = ""
    for attempt in range(max_retries):
        current_system_prompt = system_prompt
        if feedback:
            current_system_prompt += f"\n\nCRITICAL FIX REQUIRED FROM PREVIOUS ATTEMPT:\n{feedback}"
            
        raw_output = llm().generate_text(system_prompt=current_system_prompt, user_prompt=user_prompt)
        
        if is_latex:
            content = extract_clean_latex(raw_output)
            is_valid, reason = validate_latex_resume(content, master_profile, original_skills)
            if is_valid:
                return content
            else:
                feedback = f"Your previous output failed validation: {reason}. Please correct the issues and output the entire raw LaTeX document again."
                logger.warning(f"LaTeX validation failed on attempt {attempt+1}: {reason}")
        else:
            return raw_output

    # Fallback to valid master_profile if retries fail validation
    if is_latex:
        if content:
            is_valid, _ = validate_latex_resume(content, master_profile, original_skills)
            if is_valid:
                return content
        logger.warning("LaTeX validation failed on all attempts; falling back to original master profile template.")
        return master_profile
    return content or master_profile

def generate_cover_letter(master_profile: str, job_company: str, job_title: str, match_strengths: list, user_instructions: str = None) -> str:
    """
    Generates a personalized cover letter.
    """
    strengths_str = ", ".join(match_strengths) if match_strengths else "relevant technical skills"

    system_prompt = (
        "You are a professional career coach. Write a concise, compelling cover letter (max 300 words) "
        "tailored to the company and role based on the user's profile and strengths. "
        "Output in pure text/markdown format. "
        "If candidate instructions are provided, follow their tone and angle — never invent facts."
    )
    user_prompt = f"Profile:\n{master_profile}\n\nCompany: {job_company}\nJob Title: {job_title}\nKey Strengths for this role: {strengths_str}"
    if user_instructions and user_instructions.strip():
        user_prompt += f"\n\nCandidate instructions:\n{user_instructions.strip()}"
    
    return llm().generate_text(system_prompt=system_prompt, user_prompt=user_prompt)

def analyze_ats_keywords(resume_text: str, job_description: str) -> dict:
    """
    Analyzes ATS keywords and compares the resume against the job description.
    """
    system_prompt = "You are an expert ATS (Applicant Tracking System). Analyze the provided resume against the job description. Output a JSON object with keys: 'ats_score' (int 0-100), 'missing_keywords' (list of str), 'matched_keywords' (list of str), 'improvement_suggestions' (list of str)."
    user_prompt = f"Resume:\n{resume_text}\n\nJob Description:\n{job_description}"
    
    return llm().generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
