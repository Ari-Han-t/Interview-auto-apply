import re
import hashlib
from typing import Dict, Any, Optional

COMPANY_NOISE = [
    r'\binc\.?\b', r'\bllc\.?\b', r'\bcorp\.?\b', r'\bcorporation\b',
    r'\bpvt\.?\b', r'\bltd\.?\b', r'\blimited\b', r'\btechnologies\b',
    r'\btechnology\b', r'\blabs\b', r'\bsoftware\b', r'\bgroup\b'
]

TITLE_NORMALIZATION = [
    (r'\binternship\b', 'intern'),
    (r'\bsoftware development engineer\b', 'software engineer'),
    (r'\bsde\s*[-/]?\s*i\b', 'software engineer 1'),
    (r'\bsde\s*[-/]?\s*ii\b', 'software engineer 2'),
    (r'\bsde\b', 'software engineer'),
    (r'\bfull\s*stack\b', 'fullstack'),
    (r'\bback\s*end\b', 'backend'),
    (r'\bfront\s*end\b', 'frontend'),
]

def normalize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    cleaned = text.lower().strip()
    cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
    return re.sub(r'\s+', ' ', cleaned).strip()

def normalize_company(company: Optional[str]) -> str:
    norm = normalize_text(company)
    for pattern in COMPANY_NOISE:
        norm = re.sub(pattern, '', norm)
    return re.sub(r'\s+', ' ', norm).strip()

def normalize_title(title: Optional[str]) -> str:
    norm = normalize_text(title)
    for pattern, replacement in TITLE_NORMALIZATION:
        norm = re.sub(pattern, replacement, norm)
    return re.sub(r'\s+', ' ', norm).strip()

def compute_job_dedup_hash(company: str, title: str, location: Optional[str] = None, emp_type: Optional[str] = None) -> str:
    norm_comp = normalize_company(company)
    norm_title = normalize_title(title)
    norm_emp = re.sub(r'[-_\s]', '', (emp_type or "fulltime").lower().strip())
    is_remote = "remote" if (location and "remote" in location.lower()) else "onsite"
    
    seed = f"{norm_comp}::{norm_title}::{norm_emp}::{is_remote}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]

def merge_canonical_job_records(existing_job: Any, new_data: Dict[str, Any]) -> None:
    """Updates an existing job record with fresh verification data from a cross-posted source."""
    from datetime import datetime
    
    existing_job.last_verified_at = datetime.utcnow()
    existing_job.is_expired = False
    
    # Merge tech stack / skills
    current_skills = set(existing_job.tech_stack_json or [])
    new_skills = set(new_data.get("tech_stack_json") or [])
    existing_job.tech_stack_json = sorted(list(current_skills.union(new_skills)))

    current_req = set(existing_job.required_skills_json or [])
    new_req = set(new_data.get("required_skills_json") or [])
    if new_req:
        existing_job.required_skills_json = sorted(list(current_req.union(new_req)))
    
    # Merge responsibilities if empty
    if not existing_job.responsibilities_json and new_data.get("responsibilities_json"):
        existing_job.responsibilities_json = new_data["responsibilities_json"]
        
    # Update compensation if existing is missing
    if not existing_job.salary_range and new_data.get("salary_range"):
        existing_job.salary_range = new_data["salary_range"]
        existing_job.compensation_min = new_data.get("compensation_min")
        existing_job.compensation_max = new_data.get("compensation_max")
        existing_job.currency = new_data.get("currency")
        existing_job.compensation_interval = new_data.get("compensation_interval")
        
    # Update provenance with cross-posted source
    prov = dict(existing_job.source_provenance or {})
    cross_sources = prov.get("cross_posted_sources", [])
    new_source = new_data.get("source")
    if new_source and new_source not in cross_sources and new_source != existing_job.source:
        cross_sources.append(new_source)
    prov["cross_posted_sources"] = cross_sources
    prov["last_sync_timestamp"] = datetime.utcnow().isoformat()
    existing_job.source_provenance = prov
