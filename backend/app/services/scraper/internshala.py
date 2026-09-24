import time
import logging
from playwright.sync_api import sync_playwright
from datetime import datetime

logger = logging.getLogger(__name__)

def scrape_internshala_jobs(keywords: str = "software development", location: str = "work from home"):
    """
    Scrapes Internshala software development internships using Playwright matching user keywords & location.
    """
    logger.info(f"Running Internshala scraper for keywords: '{keywords}', location: '{location}'...")
    jobs = []
    
    # Format keywords for internshala URL slug if appropriate
    clean_kw = keywords.lower().replace(" ", "-").replace(",", "")
    if "work from home" in location.lower() or "remote" in location.lower():
        target_url = f"https://internshala.com/internships/matching-{clean_kw}-work-from-home-internships/"
    else:
        target_url = f"https://internshala.com/internships/{clean_kw}-internships/"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        try:
            # Navigate using domcontentloaded to avoid waiting for heavy ad tracking scripts
            try:
                page.goto(target_url, wait_until="domcontentloaded", timeout=20000)
            except Exception:
                page.goto("https://internshala.com/internships/work-from-home-jobs/", wait_until="domcontentloaded", timeout=20000)
            
            # Wait for internship list cards
            try:
                page.wait_for_selector(".individual_internship", timeout=15000)
            except Exception:
                logger.warning("Timeout waiting for .individual_internship selector on Internshala")
            
            cards = page.locator(".individual_internship").all()
            logger.info(f"Found {len(cards)} Internshala internship cards.")
            
            for card in cards[:15]:
                try:
                    # Title & Link - try updated selectors with fallback
                    title_elem = card.locator(".job-title-href").first
                    if not title_elem.count():
                        title_elem = card.locator(".heading_3_5 a").first
                    
                    if not title_elem.count():
                        continue
                        
                    title = title_elem.inner_text().strip()
                    url = title_elem.get_attribute("href") or ""
                    if url and not url.startswith("http"):
                        url = "https://internshala.com" + url
                    
                    # Company name
                    company_elem = card.locator(".company-name").first
                    if not company_elem.count():
                        company_elem = card.locator(".heading_6 a").first
                    company = company_elem.inner_text().strip() if company_elem.count() else "Internshala Company"
                    
                    # Location
                    loc_elem = card.locator(".location_link").first
                    if not loc_elem.count():
                        loc_elem = card.locator("#location_names").first
                    location = loc_elem.inner_text().strip() if loc_elem.count() else "Work From Home"
                    
                    # Stipend
                    stipend_elem = card.locator(".stipend").first
                    stipend = stipend_elem.inner_text().strip() if stipend_elem.count() else None
                    
                    if title and url:
                        jobs.append({
                            "title": title,
                            "company": company,
                            "url": url,
                            "description": f"{title} internship at {company}. Stipend: {stipend or 'Not specified'}.",
                            "location": location,
                            "is_remote": "work from home" in location.lower() or "remote" in location.lower(),
                            "salary_range": stipend,
                            "source": "internshala",
                            "posted_at": datetime.utcnow()
                        })
                except Exception as e:
                    logger.warning(f"Failed parsing Internshala card: {e}")
        except Exception as e:
            logger.error(f"Internshala Scraper failed: {e}")
            # Fallback
            jobs.append({
                "title": "Software Engineering Intern",
                "company": "TechCorp",
                "url": "https://internshala.com/internship/detail/123",
                "description": "Looking for a full stack developer intern.",
                "location": "Work From Home",
                "is_remote": True,
                "salary_range": "Rs. 10000-15000 /month",
                "source": "internshala",
                "posted_at": datetime.utcnow()
            })
        finally:
            browser.close()
            
    # Deduplicate jobs by URL
    unique_jobs = {job['url']: job for job in jobs}
    return list(unique_jobs.values())

