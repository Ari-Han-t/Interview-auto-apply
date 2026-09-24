import logging
from sqlalchemy.orm import Session
from app.models.candidate import UserProfile, CandidateExperience, UserPreference, CandidateCapability, JobRequirement

logger = logging.getLogger(__name__)

def evaluate_eligibility(
    user_id: int,
    job_id: int,
    db: Session,
    allow_requirement_extraction: bool = True,
) -> dict:
    """
    Evaluates the eligibility of a candidate for a specific job based on deterministic filters.
    Returns:
        {
            "eligible": bool,
            "reason": str
        }
    """
    # 1. Fetch job requirements
    job_req = db.query(JobRequirement).filter(JobRequirement.job_id == job_id).first()
    if not job_req:
        if not allow_requirement_extraction:
            return {
                "eligible": True,
                "reason": "Eligibility pending (requirements not parsed yet)",
            }

        # If requirements are not yet cached, extract them on the fly
        from app.models.job import Job
        from app.services.ai.job_analyzer import analyze_job_details
        
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return {"eligible": False, "reason": "Job not found in database."}
            
        try:
            req_data = analyze_job_details(job.title, job.description or "")
            job_req = JobRequirement(
                job_id=job_id,
                minimum_experience=req_data["minimum_experience"],
                maximum_experience=req_data["maximum_experience"],
                minimum_degree=req_data["minimum_degree"],
                required_skills=req_data["required_skills"],
                preferred_skills=req_data["preferred_skills"],
                visa_required=req_data["visa_required"],
                location=req_data["location"],
                remote=req_data["remote"],
                salary=req_data["salary"],
                employment_type=req_data["employment_type"],
                internship=req_data["internship"],
                fulltime=req_data["fulltime"],
                contract=req_data["contract"],
                technologies=req_data["technologies"],
                keywords=req_data["keywords"],
                company_size=req_data["company_size"]
            )
            db.add(job_req)
            db.commit()
            db.refresh(job_req)
        except Exception as e:
            logger.error(f"Error parsing job req for eligibility: {e}")
            return {"eligible": True, "reason": "Passed eligibility (requirements missing)"}

    # 2. Fetch candidate profile, capabilities, preferences, and experiences
    user_profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    capabilities = db.query(CandidateCapability).filter(CandidateCapability.user_id == user_id).first()
    preferences = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    experiences = db.query(CandidateExperience).filter(CandidateExperience.user_id == user_id).all()

    # If the user has not set up their profile, return eligible with warning to let them complete profile
    if not user_profile:
        return {"eligible": True, "reason": "Passed eligibility (Please set up your profile for hard filtering)"}

    # 3. Calculate candidate's total experience in months and years
    total_months = sum(exp.months_of_experience or 0 for exp in experiences)
    total_years = total_months / 12.0

    # 4. Check Experience Range
    if job_req.minimum_experience > 0:
        if total_years < job_req.minimum_experience:
            return {
                "eligible": False,
                "reason": f"Requires {job_req.minimum_experience} years of experience. You have {total_years:.1f} years ({total_months} months)."
            }

    # 0 years experience special constraints
    if total_years < 0.5: # 0 years experience
        # Only allow 0-1 years required, or internship
        if job_req.minimum_experience >= 2:
            return {
                "eligible": False,
                "reason": f"Requires {job_req.minimum_experience} years experience. You have 0 years of experience."
            }

    # Check against user preference max experience filter
    if preferences and preferences.maximum_experience_required is not None:
        if job_req.minimum_experience > preferences.maximum_experience_required:
            return {
                "eligible": False,
                "reason": f"Job experience requirements ({job_req.minimum_experience} years) exceed your preferred maximum of {preferences.maximum_experience_required} years."
            }

    # 5. Check Degree requirements
    degree_ranks = {"None": 0, "Bachelors": 1, "Masters": 2, "PhD": 3}
    user_degree = user_profile.degree or "None"
    req_degree = job_req.minimum_degree or "None"
    
    user_rank = degree_ranks.get(user_degree, 1) # Default to Bachelors if not found
    req_rank = degree_ranks.get(req_degree, 0)
    
    if user_rank < req_rank:
        return {
            "eligible": False,
            "reason": f"Requires a minimum of {req_degree} degree. You have a {user_profile.degree} degree."
        }

    # 6. Check Location / Relocation
    is_job_remote = bool(job_req.remote)
    
    # If job is not remote, check location and relocation willingness
    if not is_job_remote:
        # Determine candidate relocation preference
        can_relocate = True
        if capabilities and capabilities.can_relocate is False:
            can_relocate = False
        if user_profile.willing_to_relocate is False:
            can_relocate = False

        if not can_relocate:
            # Check if job location is in candidate's current or preferred locations
            curr_loc = (user_profile.current_location or "").lower()
            pref_locs = [l.lower() for l in (user_profile.preferred_locations or [])]
            if preferences and preferences.preferred_locations:
                pref_locs.extend([l.lower() for l in preferences.preferred_locations])
            
            job_loc = (job_req.location or "").lower()
            
            # Check if job location matches current or preferred locations
            matches_location = False
            if curr_loc and curr_loc in job_loc:
                matches_location = True
            for loc in pref_locs:
                if loc and loc in job_loc:
                    matches_location = True
            
            if not matches_location:
                return {
                    "eligible": False,
                    "reason": f"Role is onsite/hybrid in {job_req.location}, which is not in your preferred locations, and relocation is disabled."
                }

    # 7. Check Employment / Job Type Preferences
    is_internship_role = bool(job_req.internship)
    is_fulltime_role = bool(job_req.fulltime)
    
    # If internship role
    if is_internship_role:
        if capabilities and capabilities.can_do_internship is False:
            return {
                "eligible": False,
                "reason": "Role is an internship, but your capabilities exclude internships."
            }
        if preferences and preferences.preferred_internship is False:
            return {
                "eligible": False,
                "reason": "Role is an internship, but your preferences exclude internships."
            }

    # If full-time role and user only wants internships
    if is_fulltime_role:
        if preferences and preferences.preferred_fulltime is False and preferences.preferred_internship is True:
            return {
                "eligible": False,
                "reason": "Role is full-time, but you only want internships."
            }
        if capabilities and capabilities.can_do_fulltime is False:
            return {
                "eligible": False,
                "reason": "Role is full-time, but you cannot work full-time."
            }

    # 8. Check Salary Preference
    if job_req.salary > 0 and preferences and preferences.minimum_salary > 0:
        if job_req.salary < preferences.minimum_salary:
            return {
                "eligible": False,
                "reason": f"Salary (${job_req.salary:,}) is below your preferred minimum of (${preferences.minimum_salary:,})."
            }

    # 9. Check Work Authorization / Visa sponsorship
    if job_req.visa_required:
        needs_sponsor = False
        if capabilities and capabilities.needs_sponsorship:
            needs_sponsor = True
        if user_profile.visa_required:
            needs_sponsor = True
        if capabilities and capabilities.has_work_authorization is False:
            needs_sponsor = True
            
        if needs_sponsor:
            return {
                "eligible": False,
                "reason": "Job requires existing work authorization, but you require visa sponsorship."
            }

    return {"eligible": True, "reason": "Passed eligibility"}
