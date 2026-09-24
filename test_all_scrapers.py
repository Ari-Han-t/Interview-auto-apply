import os
import sys
import json
import logging

logging.basicConfig(level=logging.INFO)

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.scraper.greenhouse import scrape_greenhouse_jobs
from app.services.scraper.lever import scrape_lever_jobs
from app.services.scraper.github import fetch_github_projects
from app.services.scraper.linkedin import scrape_linkedin_jobs
from app.services.scraper.internshala import scrape_internshala_jobs
from app.services.scraper.yc import scrape_yc_jobs

def test_all():
    print("\n==============================================")
    print("       TESTING ALL JOB SCRAPERS & SERVICES")
    print("==============================================\n")
    
    results = {}

    print("---> 1. Testing Greenhouse Scraper (stripe)...")
    gh_jobs = scrape_greenhouse_jobs("stripe")
    results['greenhouse'] = len(gh_jobs)
    print(f"Greenhouse (stripe): {len(gh_jobs)} jobs scraped.")
    if gh_jobs:
        print("Sample:", json.dumps(gh_jobs[0], default=str, indent=2))

    print("\n---> 2. Testing Lever Scraper (spotify)...")
    lever_jobs = scrape_lever_jobs("spotify")
    results['lever'] = len(lever_jobs)
    print(f"Lever (spotify): {len(lever_jobs)} jobs scraped.")
    if lever_jobs:
        print("Sample:", json.dumps(lever_jobs[0], default=str, indent=2))

    print("\n---> 3. Testing GitHub Projects Scraper (octocat)...")
    try:
        gh_projects = fetch_github_projects("octocat")
        results['github'] = len(gh_projects)
        print(f"GitHub (octocat): {len(gh_projects)} projects scraped.")
        if gh_projects:
            print("Sample:", json.dumps(gh_projects[0], default=str, indent=2))
    except Exception as e:
        print(f"GitHub Scraper error: {e}")

    print("\n---> 4. Testing LinkedIn Scraper (software engineer)...")
    li_jobs = scrape_linkedin_jobs("software engineer", "Remote")
    results['linkedin'] = len(li_jobs)
    print(f"LinkedIn: {len(li_jobs)} jobs scraped.")
    if li_jobs:
        print("Sample:", json.dumps(li_jobs[0], default=str, indent=2))

    print("\n---> 5. Testing YC Scraper...")
    yc_jobs = scrape_yc_jobs()
    results['yc'] = len(yc_jobs)
    print(f"YC: {len(yc_jobs)} jobs scraped.")
    if yc_jobs:
        print("Sample:", json.dumps(yc_jobs[0], default=str, indent=2))

    print("\n---> 6. Testing Internshala Scraper...")
    ishala_jobs = scrape_internshala_jobs()
    results['internshala'] = len(ishala_jobs)
    print(f"Internshala: {len(ishala_jobs)} jobs scraped.")
    if ishala_jobs:
        print("Sample:", json.dumps(ishala_jobs[0], default=str, indent=2))

    print("\n==============================================")
    print("                SUMMARY RESULTS")
    print("==============================================")
    for source, count in results.items():
        status = "PASSED (Live data)" if count > 0 else "FAILED"
        print(f"  {source.upper():<15}: {count:<4} jobs | Status: {status}")

if __name__ == "__main__":
    test_all()
