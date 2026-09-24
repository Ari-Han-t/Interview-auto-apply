import os
import sys
import json

# Parse .env manually
env_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value.strip('"\'')

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.scraper.github import fetch_github_projects
from app.services.ai.github_analyzer import analyze_github_projects

def test_github_flow():
    # Use a well-known github user or ask for one
    username = "octocat"
    job_description = "Looking for a software engineer with Ruby experience who has built open source tools or demoable projects."
    
    print(f"--- 1. Fetching GitHub Projects for '{username}' ---")
    try:
        raw_projects = fetch_github_projects(username)
        print(f"Found {len(raw_projects)} projects.")
    except Exception as e:
        print(f"Error fetching: {e}")
        return
        
    if not raw_projects:
        print("No projects found.")
        return
        
    print(f"\n--- 2. Analyzing with AI for relevance ---")
    try:
        analyzed_data = analyze_github_projects(raw_projects, job_description)
        print("Analysis Result:")
        print(json.dumps(analyzed_data, indent=2))
    except Exception as e:
        print(f"Error analyzing: {e}")

if __name__ == "__main__":
    test_github_flow()
