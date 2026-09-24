import logging
import json
from typing import List, Dict, Any
from app.services.llm import get_llm

logger = logging.getLogger(__name__)

def analyze_github_projects(projects: List[Dict[str, Any]], job_description: str) -> Dict[str, Any]:
    """
    Analyzes a list of GitHub projects and a job description using an LLM.
    Returns a curated list of relevant, demoable projects with generated metadata.
    """
    if not projects:
        return {"relevant_projects": []}
        
    logger.info("Analyzing GitHub projects for relevance...")
    
    provider = get_llm()
    
    system_prompt = (
        "You are an expert technical recruiter and software engineering mentor. "
        "Your task is to review a candidate's GitHub projects and a target job description, "
        "and select the projects that are most relevant and demoable for that specific role. "
        "Compare candidate's repositories, languages, topics, and descriptions with the job description. "
        "Return the output as a valid JSON object with the following schema:\n"
        "{\n"
        "  \"relevant_projects\": [\n"
        "     { \"name\": \"str\", \"url\": \"str\", \"demo_link\": \"str\", \"tech_stack\": [\"str\"], \"relevance_reason\": \"str\" }\n"
        "  ],\n"
        "  \"top_projects\": [\"projectName1\", \"projectName2\"],\n"
        "  \"missing_skills\": [\"skill1\", \"skill2\"],\n"
        "  \"strength_score\": int (0-100),\n"
        "  \"reasoning\": \"str summary\"\n"
        "}"
    )
    
    # We serialize the projects to pass them to the LLM, but limit to top 15 to avoid context bloat
    projects_subset = projects[:15]
    
    user_prompt = f"""
    Job Description:
    {job_description}
    
    Candidate's GitHub Projects:
    {json.dumps(projects_subset, indent=2)}
    
    Please return the JSON object with the required schema.
    """
    
    try:
        result = provider.generate_json(system_prompt, user_prompt)
        return result
    except Exception as e:
        logger.error(f"Failed to analyze GitHub projects: {e}")
        return {
            "relevant_projects": [],
            "top_projects": [],
            "missing_skills": [],
            "strength_score": 0,
            "reasoning": "Failed to analyze GitHub projects due to an error."
        }
