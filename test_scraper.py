import os
import sys
import json

# Add backend to path so we can import from app
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.scraper.yc import scrape_yc_jobs

def test_scraper():
    print("Testing YC scraper...")
    try:
        jobs = scrape_yc_jobs()
        print(f"Scraped {len(jobs)} jobs successfully!")
        print(json.dumps(jobs, indent=2))
    except Exception as e:
        print(f"Error scraping YC jobs: {e}")

if __name__ == "__main__":
    test_scraper()
