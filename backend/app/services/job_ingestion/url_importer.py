import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.job import Job
from app.services.scraper.adapters.registry import route_url_to_adapter
from app.services.job_ingestion.deduplicator import compute_job_dedup_hash, merge_canonical_job_records

logger = logging.getLogger(__name__)

def import_job_from_url(url: str, db: Session) -> Job:
    """
    Imports a canonical job record directly from any supported source URL
    (Greenhouse, Lever, Ashby, YC, Internshala, LinkedIn, or official company career page).
    """
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        raise ValueError("Invalid URL: must start with http:// or https://")

    # 1. Route to appropriate source adapter
    adapter = route_url_to_adapter(url)
    parsed_data = adapter.parse_job_url(url)
    
    if not parsed_data or not parsed_data.get("title"):
        raise ValueError(f"Could not extract canonical job details from {url}. Ensure the link is active.")

    company = parsed_data.get("company", "Company")
    title = parsed_data.get("title", "Software Engineer")
    location = parsed_data.get("location", "Remote")
    emp_type = parsed_data.get("employment_type", "fulltime")
    
    # 2. Compute deduplication hash
    dedup_hash = compute_job_dedup_hash(company, title, location, emp_type)
    
    # 3. Check for existing duplicate by URL or dedup_hash
    existing = db.query(Job).filter((Job.url == url) | (Job.dedup_hash == dedup_hash)).first()
    
    if existing:
        merge_canonical_job_records(existing, parsed_data)
        existing.dedup_hash = dedup_hash
        db.commit()
        db.refresh(existing)
        return existing

    # 4. Create new canonical Job record
    new_job = Job(
        title=title,
        company=company,
        url=parsed_data.get("url") or url,
        application_url=parsed_data.get("application_url") or url,
        description=parsed_data.get("description", ""),
        responsibilities_json=parsed_data.get("responsibilities_json", []),
        required_skills_json=parsed_data.get("required_skills_json", []),
        preferred_skills_json=parsed_data.get("preferred_skills_json", []),
        requirements_json=parsed_data.get("requirements_json", {}),
        eligibility_criteria_json=parsed_data.get("eligibility_criteria_json", {}),
        graduation_restrictions=parsed_data.get("graduation_restrictions", []),
        status="active",
        deadline=parsed_data.get("deadline"),
        location=location,
        work_arrangement=parsed_data.get("work_arrangement", "onsite"),
        employment_type=emp_type,
        salary_range=parsed_data.get("salary_range"),
        compensation_min=parsed_data.get("compensation_min"),
        compensation_max=parsed_data.get("compensation_max"),
        currency=parsed_data.get("currency", "USD"),
        compensation_interval=parsed_data.get("compensation_interval"),
        is_remote=parsed_data.get("is_remote", False),
        tech_stack_json=parsed_data.get("tech_stack_json", []),
        company_logo_url=parsed_data.get("company_logo_url"),
        source=parsed_data.get("source", adapter.source_id),
        source_job_id=parsed_data.get("source_job_id"),
        source_provenance=parsed_data.get("source_provenance", {}),
        posted_at=parsed_data.get("posted_at") or datetime.utcnow(),
        last_verified_at=datetime.utcnow(),
        is_expired=False,
        dedup_hash=dedup_hash
    )
    
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job
