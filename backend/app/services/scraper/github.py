import httpx
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

def fetch_github_projects(username: str) -> List[Dict[str, Any]]:
    """
    Fetches the public repositories for a given GitHub username.
    Filters out forks to only return original projects.
    """
    logger.info(f"Fetching GitHub projects for user: {username}")
    
    url = f"https://api.github.com/users/{username}/repos"
    params = {
        "type": "owner",
        "sort": "updated",
        "per_page": 100
    }
    
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AutoApply-App"
    }
    
    projects = []
    try:
        response = httpx.get(url, params=params, headers=headers, timeout=10.0)
        
        if response.status_code == 404:
            logger.warning(f"GitHub user {username} not found.")
            return []
            
        response.raise_for_status()
        repos = response.json()
        
        for repo in repos:
            if repo.get("fork"):
                continue  # Skip forks
                
            project_data = {
                "name": repo.get("name"),
                "description": repo.get("description"),
                "url": repo.get("html_url"),
                "homepage": repo.get("homepage"), # Good indicator of a demo
                "language": repo.get("language"),
                "topics": repo.get("topics", []),
                "stars": repo.get("stargazers_count", 0),
                "updated_at": repo.get("updated_at")
            }
            projects.append(project_data)
            
        logger.info(f"Successfully fetched {len(projects)} original projects for {username}.")
        return projects
        
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred while fetching GitHub projects: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while fetching GitHub projects: {e}")
        raise
