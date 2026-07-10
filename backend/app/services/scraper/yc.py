import time
# from playwright.sync_api import sync_playwright

def scrape_yc_jobs():
    """
    Mock scraper for YC Jobs for Milestone 2.
    In a real implementation, this uses Playwright to navigate YC jobs,
    handling infinite scroll and extracting job postings.
    """
    print("Running YC scraper (Mock)...")
    time.sleep(2) # Simulate network delay
    return [
        {
            "title": "Software Engineering Intern",
            "company": "Stripe",
            "url": "https://stripe.com/jobs",
            "description": "Looking for a backend intern to work on payment infrastructure.",
            "location": "San Francisco, CA"
        },
        {
            "title": "AI Research Intern",
            "company": "OpenAI",
            "url": "https://openai.com/jobs",
            "description": "Research intern to work on large language models.",
            "location": "San Francisco, CA"
        },
        {
            "title": "Full Stack Intern",
            "company": "Vercel",
            "url": "https://vercel.com/careers",
            "description": "Build Next.js features and collaborate with open source.",
            "location": "Remote"
        }
    ]
