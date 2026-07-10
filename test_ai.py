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

print("\n--- Testing generate_tailored_resume ---")
resume_result = generate_tailored_resume(profile_text, job_description, "Full Stack Software Engineer")
print(resume_result)
