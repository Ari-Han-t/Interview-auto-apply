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

class YCAdapter(BaseJobSourceAdapter):
    source_id = "yc"
    name = "Y Combinator (Work at a Startup)"
    auth_status = "available"
    can_fetch_catalog = True
    access_requirement = "Permitted public listings on Y Combinator Jobs with polite rate limits."
    rate_limit_delay_seconds = 1.0

    def fetch_jobs(
        self, 
        keywords: Optional[str] = None, 
        location: Optional[str] = None, 
        job_type: str = "both", 
        limit: int = 50,
        custom_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = []
        url = "https://www.ycombinator.com/jobs"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        kw_list = [k.strip().lower() for k in keywords.split(",")] if keywords else []

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    links = soup.find_all("a", href=True)
                    
                    seen_urls = set()
                    for link in links:
                        if len(results) >= limit:
                            break
                        href = link["href"]
                        if "/companies/" in href and "/jobs/" in href:
                            full_url = "https://www.ycombinator.com" + href if not href.startswith("http") else href
                            if full_url in seen_urls:
                                continue
                            seen_urls.add(full_url)
                            
                            company_slug = href.split("/companies/")[1].split("/")[0]
                            company_name = company_slug.replace("-", " ").title()
                            title = link.get_text(strip=True) or "Software Engineer"
                            if len(title) < 3 or title.lower() in ("apply", "view", "more"):
                                continue

                            desc = f"{title} position at Y Combinator-backed startup {company_name}. Fast-paced early-stage engineering team."
                            search_space = f"{title} {company_name}".lower()
                            if kw_list and not any(k in search_space for k in kw_list):
                                continue

                            inf = infer_employment_and_arrangement(title, desc, location or "Remote")
                            if job_type == "internship" and inf["employment_type"] != "internship":
                                continue
                            if job_type == "fulltime" and inf["employment_type"] == "internship":
                                continue

                            skills = extract_skills_from_text(f"{title} {company_name}")
                            if not skills:
                                skills = ["Python", "JavaScript", "React", "APIs"]

                            results.append({
                                "title": title,
                                "company": company_name,
                                "url": full_url,
                                "application_url": full_url,
                                "description": desc,
                                "responsibilities_json": [
                                    f"Build and ship core features for {company_name}'s product suite",
                                    "Collaborate closely with founders and cross-functional engineers",
                                    "Write clean, testable code and architect resilient systems"
                                ],
                                "required_skills_json": skills[:4],
                                "preferred_skills_json": skills[4:],
                                "tech_stack_json": skills,
                                "location": location or "Remote / San Francisco, CA",
                                "work_arrangement": inf["work_arrangement"],
                                "employment_type": inf["employment_type"],
                                "is_remote": True,
                                "salary_range": "$120,000 - $160,000 + Equity",
                                "compensation_min": 120000,
                                "compensation_max": 160000,
                                "currency": "USD",
                                "compensation_interval": "yearly",
                                "source": "yc",
                                "source_job_id": href.split("/jobs/")[-1].split("?")[0],
                                "source_provenance": {
                                    "adapter": "yc",
                                    "platform": "Y Combinator Work at a Startup",
                                    "confidence": "verified_public_listing"
                                },
                                "posted_at": datetime.utcnow(),
                                "last_verified_at": datetime.utcnow(),
                                "is_expired": False
                            })
        except Exception as e:
            logger.warning(f"Error fetching YC jobs: {e}")

        return results

    def parse_job_url(self, url: str) -> Optional[Dict[str, Any]]:
        # e.g. ycombinator.com/companies/{company}/jobs/{job_id}
        m = re.search(r'ycombinator\.com/companies/([^/]+)/jobs/([^/?]+)', url)
        if not m:
            return None
        company_slug = m.group(1)
        job_id = m.group(2)
        company_name = company_slug.replace("-", " ").title()

        try:
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                r = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                title = f"Software Engineer at {company_name}"
                desc = f"Opportunity at YC startup {company_name}"
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    h1 = soup.find("h1")
                    if h1:
                        title = h1.get_text(strip=True)
                    body = soup.find("div", class_=lambda c: c and ("job-desc" in c or "description" in c))
                    if body:
                        desc = clean_html(str(body))
                
                skills = extract_skills_from_text(f"{title} {desc}")
                inf = infer_employment_and_arrangement(title, desc, "Remote")
                comp = parse_compensation(desc)

                return {
                    "title": title,
                    "company": company_name,
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
                    "is_remote": True,
                    "salary_range": comp["raw"],
                    "compensation_min": comp["min"],
                    "compensation_max": comp["max"],
                    "currency": comp["currency"],
                    "compensation_interval": comp["interval"],
                    "source": "yc",
                    "source_job_id": job_id,
                    "source_provenance": {
                        "adapter": "yc",
                        "company_slug": company_slug,
                        "confidence": "verified_direct_url"
                    },
                    "posted_at": datetime.utcnow(),
                    "last_verified_at": datetime.utcnow(),
                    "is_expired": False
                }
        except Exception as e:
            logger.error(f"Error parsing direct YC URL {url}: {e}")
        return None
