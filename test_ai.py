import os

# Parse .env manually to avoid dependencies
env_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value.strip('"\'')

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Ensure stdout can print unicode on Windows
sys.stdout.reconfigure(encoding='utf-8')

from app.services.ai.matcher import analyze_job_match
from app.services.ai.generator import generate_tailored_resume

profile_text = """
Software Engineering student with experience in Python, FastAPI, and Next.js.
Built multiple backend systems and integrated with various APIs.
Familiar with Docker and PostgreSQL.
"""

job_description = """
Looking for a Full Stack Software Engineer.
Requirements:
- Strong knowledge of Python and FastAPI.
- Experience with React or Next.js.
- Bonus points for Kubernetes and AWS experience.
"""

print("--- Testing analyze_job_match ---")
match_result = analyze_job_match(profile_text, job_description)
print(match_result)

print("\n--- Testing generate_tailored_resume (Markdown) ---")
resume_result = generate_tailored_resume(profile_text, job_description, "Full Stack Software Engineer")
print(resume_result[:200] + "...\n")

dummy_latex = r"""
\documentclass{article}
\begin{document}
\section{Projects}
\begin{itemize}
    \item Old Project 1
\end{itemize}
\end{document}
"""

dummy_extracted = [
    {
        "name": "Super AI App",
        "demo_link": "https://super-ai-app.com",
        "tech_stack": ["Python", "FastAPI"],
        "relevance_reason": "Directly matches Python and FastAPI requirements."
    }
]

print("--- Testing generate_tailored_resume (LaTeX) ---")
latex_result = generate_tailored_resume(
    dummy_latex, 
    job_description, 
    "Full Stack Software Engineer", 
    is_latex=True, 
    extracted_projects=dummy_extracted
)
print(latex_result)
