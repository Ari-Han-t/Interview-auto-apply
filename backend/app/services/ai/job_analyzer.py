import logging
from app.services.llm import get_llm

logger = logging.getLogger(__name__)

def analyze_job_details(job_title: str, job_description: str) -> dict:
    """
    Uses LLM to extract structured eligibility criteria and details from a job description.
    """
    provider = get_llm()

    system_prompt = (
        "You are an AI assistant specialized in analyzing technical job descriptions. "
        "Extract structured eligibility criteria from the job title and description. "
        "Your output must be in pure JSON format without markdown wrapping.\n"
        "Ensure all fields exactly follow the specified type constraints:\n"
        "{\n"
        "  \"minimum_experience\": integer (the minimum years of experience required, default to 0 if not specified),\n"
        "  \"maximum_experience\": integer or null (the maximum experience expected if a cap is specified, or null),\n"
        "  \"minimum_degree\": string (must be one of: \"Bachelors\", \"Masters\", \"PhD\", \"None\"),\n"
        "  \"required_skills\": list of strings,\n"
        "  \"preferred_skills\": list of strings,\n"
        "  \"visa_required\": boolean (true if visa sponsorship is required / no sponsorship provided, false otherwise),\n"
        "  \"location\": string (location or \"Remote\"),\n"
        "  \"remote\": boolean (true if the job can be done remotely, false otherwise),\n"
        "  \"salary\": integer (the base salary or minimum salary offered if mentioned, default to 0),\n"
        "  \"employment_type\": string (e.g. \"Full-time\", \"Internship\", \"Contract\", \"Part-time\"),\n"
        "  \"internship\": boolean (true if this is specifically an internship role, false otherwise),\n"
        "  \"fulltime\": boolean (true if this is a full-time role, false otherwise),\n"
        "  \"contract\": boolean (true if this is a contract role, false otherwise),\n"
        "  \"technologies\": list of strings,\n"
        "  \"keywords\": list of strings,\n"
        "  \"company_size\": string or null (e.g. \"1-10\", \"11-50\", \"51-200\", \"201-500\", \"500+\", or null)\n"
        "}"
    )
    user_prompt = f"Job Title: {job_title}\n\nJob Description:\n{job_description}"

    try:
        extracted = provider.generate_json(system_prompt=system_prompt, user_prompt=user_prompt)
        
        # Validate types to avoid database insert errors
        validated = {
            "minimum_experience": int(extracted.get("minimum_experience", 0) or 0),
            "maximum_experience": int(extracted.get("maximum_experience")) if extracted.get("maximum_experience") is not None else None,
            "minimum_degree": str(extracted.get("minimum_degree") or "None"),
            "required_skills": list(extracted.get("required_skills") or []),
            "preferred_skills": list(extracted.get("preferred_skills") or []),
            "visa_required": bool(extracted.get("visa_required", False)),
            "location": str(extracted.get("location") or "Remote"),
            "remote": bool(extracted.get("remote", False)),
            "salary": int(extracted.get("salary", 0) or 0),
            "employment_type": str(extracted.get("employment_type") or "Full-time"),
            "internship": bool(extracted.get("internship", False)),
            "fulltime": bool(extracted.get("fulltime", True)),
            "contract": bool(extracted.get("contract", False)),
            "technologies": list(extracted.get("technologies") or []),
            "keywords": list(extracted.get("keywords") or []),
            "company_size": str(extracted.get("company_size")) if extracted.get("company_size") is not None else None,
        }
        return validated
    except Exception as e:
        logger.error(f"Job detailed extraction failed: {e}")
        # Return sensible default values
        is_intern = "intern" in job_title.lower()
        return {
            "minimum_experience": 0,
            "maximum_experience": None,
            "minimum_degree": "None",
            "required_skills": [],
            "preferred_skills": [],
            "visa_required": False,
            "location": "Remote",
            "remote": True,
            "salary": 0,
            "employment_type": "Internship" if is_intern else "Full-time",
            "internship": is_intern,
            "fulltime": not is_intern,
            "contract": False,
            "technologies": [],
            "keywords": [],
            "company_size": None
        }
