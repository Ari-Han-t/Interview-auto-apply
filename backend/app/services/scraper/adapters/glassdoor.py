import re
import httpx
import logging
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Optional, Any
from .base import (
    BaseJobSourceAdapter, 
    clean_html, 
    extract_skills_from_text, 
    extract_responsibilities_from_text,
    parse_compensation,
    infer_employment_and_arrangement
)

logger = logging.getLogger(__name__)

class GlassdoorAdapter(BaseJobSourceAdapter):
    source_id = "glassdoor"
    name = "Glassdoor"
    auth_status = "requires_auth"
    can_fetch_catalog = False
    access_requirement = "Glassdoor requires Glassdoor Partner API credentials. Direct web crawling is restricted by Akamai Bot Manager. Direct job URL import (/job-listing/...) and manual job entry are supported alternatives."
    rate_limit_delay_seconds = 2.0

    def fetch_jobs(
        self, 
        keywords: Optional[str] = None, 
        location: Optional[str] = None, 
        job_type: str = "both", 
        limit: int = 25,
        custom_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        logger.info("Glassdoor catalog crawling requires Partner API credentials. Direct URL import supported.")
        return []

    def parse_job_url(self, url: str) -> Optional[Dict[str, Any]]:
        if "glassdoor.com" not in url:
            return None
            
        m = re.search(r'jl=(\d+)', url) or re.search(r'jobListingId=(\d+)', url)
        job_id = m.group(1) if m else re.sub(r'[^a-zA-Z0-9]', '', url)[-16:]

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                r = client.get(url, headers=headers)
                soup = BeautifulSoup(r.text, "html.parser")
                title_elem = soup.find("h1")
                comp_elem = soup.find("div", class_=lambda c: c and "EmployerProfile" in c) or soup.find("span", class_="employer-name")
                desc_elem = soup.find("div", class_=lambda c: c and ("JobDetails_jobDescription" in c or "desc" in c))

                title = title_elem.get_text(strip=True) if title_elem else "Software Engineer"
                company = comp_elem.get_text(strip=True) if comp_elem else "Glassdoor Employer"
                desc = clean_html(str(desc_elem)) if desc_elem else f"{title} at {company}"

                skills = extract_skills_from_text(f"{title} {desc}")
                inf = infer_employment_and_arrangement(title, desc, "Remote")
                comp = parse_compensation(desc)

                return {
                    "title": title,
                    "company": company,
                    "url": url,
                    "application_url": url,
                    "description": desc,
                    "responsibilities_json": extract_responsibilities_from_text(desc),
                    "required_skills_json": skills[:6],
                    "preferred_skills_json": skills[6:12],
                    "tech_stack_json": skills,
                    "location": "Remote",
                    "work_arrangement": inf["work_arrangement"],
                    "employment_type": inf["employment_type"],
                    "is_remote": inf["is_remote"],
                    "salary_range": comp["raw"],
                    "compensation_min": comp["min"],
                    "compensation_max": comp["max"],
                    "currency": comp["currency"],
                    "compensation_interval": comp["interval"],
                    "source": "glassdoor",
                    "source_job_id": str(job_id),
                    "source_provenance": {
                        "adapter": "glassdoor",
                        "confidence": "direct_url_import"
                    },
                    "posted_at": datetime.utcnow(),
                    "last_verified_at": datetime.utcnow(),
                    "is_expired": False
                }
        except Exception as e:
            logger.error(f"Error parsing direct Glassdoor URL: {e}")
        return None
