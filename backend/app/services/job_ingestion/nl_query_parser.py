import re
import logging
from typing import Dict, Any, List, Optional
from app.services.scraper.adapters.base import TECH_TAXONOMY

logger = logging.getLogger(__name__)

COMMON_LOCATIONS = [
    "india", "bangalore", "bengaluru", "delhi", "mumbai", "hyderabad", "pune", "gurgaon", "noida",
    "usa", "united states", "san francisco", "new york", "seattle", "austin", "california",
    "canada", "toronto", "vancouver", "uk", "london", "europe", "germany", "berlin", "remote"
]

def parse_natural_language_job_query(query: str) -> Dict[str, Any]:
    """
    Parses a natural language search query into structured job search parameters.
    Example: "Find backend engineering internships in India requiring Python, APIs, PostgreSQL, and cloud deployment."
    """
    if not query:
        return {}

    q_lower = query.lower().strip()
    
    # 1. Job Type
    job_type = "both"
    if "internship" in q_lower or "intern" in q_lower:
        job_type = "internship"
    elif "full-time" in q_lower or "fulltime" in q_lower or "entry-level" in q_lower or "entry level" in q_lower:
        job_type = "fulltime"
    elif "contract" in q_lower or "freelance" in q_lower:
        job_type = "contract"

    # 2. Work arrangement
    work_arrangement = "all"
    if "remote" in q_lower or "work from home" in q_lower or "wfh" in q_lower:
        work_arrangement = "remote"
    elif "hybrid" in q_lower:
        work_arrangement = "hybrid"
    elif "onsite" in q_lower or "in-office" in q_lower or "in office" in q_lower:
        work_arrangement = "onsite"

    # 3. Location
    detected_location = None
    for loc in COMMON_LOCATIONS:
        if re.search(r'\b' + re.escape(loc) + r'\b', q_lower):
            detected_location = loc.title()
            break

    # 4. Extract Skills
    detected_skills = []
    for kw, standard_name in TECH_TAXONOMY.items():
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, q_lower):
            if standard_name not in detected_skills:
                detected_skills.append(standard_name)

    # 5. Extract role keywords
    # Remove query noise words
    noise_patterns = [
        r'\bfind\b', r'\bsearch\b', r'\blooking for\b', r'\bjobs?\b', r'\binternships?\b',
        r'\brequiring\b', r'\bwith\b', r'\band\b', r'\bin\b', r'\bfor\b', r'\bat\b',
        r'\busing\b', r'\bneeded\b', r'\bmust have\b', r'\bskills?\b'
    ]
    cleaned_query = q_lower
    for np in noise_patterns:
        cleaned_query = re.sub(np, ' ', cleaned_query)
    
    # Remove extracted locations and skills from role keywords
    if detected_location:
        cleaned_query = re.sub(r'\b' + re.escape(detected_location.lower()) + r'\b', ' ', cleaned_query)
    for sk in detected_skills:
        cleaned_query = re.sub(r'\b' + re.escape(sk.lower()) + r'\b', ' ', cleaned_query)

    role_keywords = re.sub(r'\s+', ' ', cleaned_query).strip()
    if not role_keywords or len(role_keywords) < 2:
        if "backend" in q_lower:
            role_keywords = "backend"
        elif "frontend" in q_lower:
            role_keywords = "frontend"
        elif "fullstack" in q_lower:
            role_keywords = "fullstack"
        elif "ai" in q_lower or "machine learning" in q_lower:
            role_keywords = "ai machine learning"
        else:
            role_keywords = ""

    # 6. Graduation year
    grad_match = re.search(r'\b(202[4-9]|2030)\b', q_lower)
    grad_year = grad_match.group(1) if grad_match else None

    # 7. Compensation
    comp_match = re.search(r'(?:\$|₹|rs\.?|inr)?\s*(\d{2,3}(?:,\d{3})*|\d{2,3}k)', q_lower)
    min_comp = None
    if comp_match:
        try:
            val_str = comp_match.group(1).replace(",", "").lower()
            if "k" in val_str:
                min_comp = float(val_str.replace("k", "")) * 1000
            else:
                min_comp = float(val_str)
        except Exception:
            pass

    return {
        "raw_query": query,
        "role_keywords": role_keywords,
        "skills": detected_skills,
        "job_type": job_type,
        "work_arrangement": work_arrangement,
        "location": detected_location,
        "graduation_year": grad_year,
        "min_compensation": min_comp
    }
