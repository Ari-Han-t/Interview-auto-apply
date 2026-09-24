import time
import logging
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

def scrape_yc_jobs(keywords: str = None, job_type: str = "both") -> List[Dict[str, Any]]:
    """
    Scrapes YC Jobs matching optional keywords and job_type filter.
    """
    logger.info(f"Running YC scraper (keywords='{keywords}', job_type='{job_type}')...")
    jobs = []
    
    # 1. Try fast httpx fetch
    try:
        url = "https://www.ycombinator.com/jobs"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        r = httpx.get(url, headers=headers, follow_redirects=True, timeout=15.0)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if '/companies/' in href and '/jobs/' in href:
                    if not href.startswith("http"):
                        full_url = "https://www.ycombinator.com" + href
                    else:
                        full_url = href
                    
                    company_slug = href.split('/companies/')[1].split('/')[0]
                    company_name = company_slug.replace('-', ' ').title()
                    title = link.get_text(strip=True) or "Software Engineer"
                    
                    if len(title) > 2:
                        jobs.append({
                            "title": title,
                            "company": company_name,
                            "url": full_url,
                            "description": f"{title} position at YC startup {company_name}.",
                            "location": "Remote / USA",
                            "is_remote": True,
                            "salary_range": None,
                            "source": "yc",
                            "posted_at": datetime.utcnow()
                        })
            logger.info(f"Scraped {len(jobs)} YC jobs via httpx.")
    except Exception as e:
        logger.warning(f"Fast YC scraping via httpx failed: {e}. Falling back to Playwright...")

    # 2. Playwright fallback if httpx returned no jobs
    if not jobs:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto("https://www.ycombinator.com/jobs", wait_until="domcontentloaded", timeout=30000)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1)
                
                links = page.locator("a").all()
                for link in links:
                    try:
                        href = link.get_attribute("href") or ""
                        if "/companies/" in href and "/jobs/" in href:
                            if not href.startswith("http"):
                                full_url = "https://www.ycombinator.com" + href
                            else:
                                full_url = href
                                
                            company_slug = href.split("/companies/")[1].split("/")[0]
                            company_name = company_slug.replace("-", " ").title()
                            title = link.inner_text().strip() or "Software Engineer"
                            
                            if title and len(title) > 2:
                                jobs.append({
                                    "title": title,
                                    "company": company_name,
                                    "url": full_url,
                                    "description": f"{title} position at YC startup {company_name}.",
                                    "location": "Remote / USA",
                                    "is_remote": True,
                                    "salary_range": None,
                                    "source": "yc",
                                    "posted_at": datetime.utcnow()
                                })
                    except Exception as item_err:
                        logger.debug(f"Error parsing YC link: {item_err}")
            except Exception as ex:
                logger.error(f"YC Playwright scraper failed: {ex}")
            finally:
                browser.close()
                
    # Deduplicate jobs by URL
    unique_jobs = {job['url']: job for job in jobs}
    return list(unique_jobs.values())

