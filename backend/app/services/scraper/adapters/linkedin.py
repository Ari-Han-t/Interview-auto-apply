import re
import urllib.parse
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

class LinkedInAdapter(BaseJobSourceAdapter):
    source_id = "linkedin"
    name = "LinkedIn"
    auth_status = "limited"
    can_fetch_catalog = True
    access_requirement = "LinkedIn Official Jobs API requires LinkedIn Talent Solutions Partner agreement and OAuth 2.0 credentials. Unauthenticated guest endpoint is heavily rate-limited and intermittently challenged. Direct job URL import (/jobs/view/...) and manual entry are supported alternatives."
    rate_limit_delay_seconds = 2.0

    def fetch_jobs(
        self, 
        keywords: Optional[str] = None, 
        location: Optional[str] = None, 
        job_type: str = "both", 
        limit: int = 25,
        custom_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        search_kw = keywords or "Software Engineer"
        if job_type == "internship" and "intern" not in search_kw.lower():
            search_kw += " intern"
            
        enc_kw = urllib.parse.quote(search_kw)
        enc_loc = urllib.parse.quote(location or "Remote")
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={enc_kw}&location={enc_loc}&start=0"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        results = []
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    cards = soup.find_all("div", class_=lambda c: c and "base-card" in c)
                    for card in cards[:limit]:
                        try:
                            title_elem = card.find("h3", class_=lambda c: c and "title" in c)
                            comp_elem = card.find("h4", class_=lambda c: c and "subtitle" in c)
                            loc_elem = card.find("span", class_=lambda c: c and "location" in c)
                            link_elem = card.find("a", class_=lambda c: c and "full-link" in c) or card.find("a", href=True)

                            title = title_elem.get_text(strip=True) if title_elem else "Software Engineer"
                            company = comp_elem.get_text(strip=True) if comp_elem else "Tech Company"
                            loc_str = loc_elem.get_text(strip=True) if loc_elem else (location or "Remote")
                            raw_href = link_elem["href"] if link_elem and "href" in link_elem.attrs else ""
                            clean_url = raw_href.split("?")[0] if raw_href else f"https://www.linkedin.com/jobs/search?keywords={enc_kw}"

                            desc = f"{title} opportunity at {company} ({loc_str}). View requirements and apply on LinkedIn."
                            skills = extract_skills_from_text(f"{title} {desc}")
                            inf = infer_employment_and_arrangement(title, desc, loc_str)
                            comp = parse_compensation(desc)

                            results.append({
                                "title": title,
                                "company": company,
                                "url": clean_url,
                                "application_url": clean_url,
                                "description": desc,
                                "responsibilities_json": [
                                    f"Execute engineering projects and product development at {company}",
                                    "Maintain technical quality, performance, and security across the stack"
                                ],
                                "required_skills_json": skills[:4] if skills else ["Python", "JavaScript", "SQL"],
                                "preferred_skills_json": skills[4:],
                                "tech_stack_json": skills,
                                "location": loc_str,
                                "work_arrangement": inf["work_arrangement"],
                                "employment_type": inf["employment_type"],
                                "is_remote": inf["is_remote"],
                                "salary_range": comp["raw"],
                                "compensation_min": comp["min"],
                                "compensation_max": comp["max"],
                                "currency": comp["currency"],
                                "compensation_interval": comp["interval"],
                                "source": "linkedin",
                                "source_job_id": re.search(r'/view/(\d+)', clean_url).group(1) if re.search(r'/view/(\d+)', clean_url) else "",
                                "source_provenance": {
                                    "adapter": "linkedin",
                                    "confidence": "guest_search_endpoint"
                                },
                                "posted_at": datetime.utcnow(),
                                "last_verified_at": datetime.utcnow(),
                                "is_expired": False
                            })
                        except Exception:
                            continue
        except Exception as e:
            logger.warning(f"LinkedIn guest scrape limited/failed: {e}")

        return results

    def parse_job_url(self, url: str) -> Optional[Dict[str, Any]]:
        if "linkedin.com" not in url:
            return None
        m = re.search(r'/jobs/view/(\d+)', url)
        job_id = m.group(1) if m else re.sub(r'[^0-9]', '', url)[-10:]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        try:
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                r = client.get(url, headers=headers)
                soup = BeautifulSoup(r.text, "html.parser")
                title_elem = soup.find("h1") or soup.find("h2", class_=lambda c: c and "topcard__title" in c)
                comp_elem = soup.find("a", class_=lambda c: c and "topcard__org-name-link" in c) or soup.find("span", class_="topcard__flavor")
                desc_elem = soup.find("div", class_=lambda c: c and "show-more-less-html" in c) or soup.find("div", class_="description__text")

                title = title_elem.get_text(strip=True) if title_elem else "Software Engineer"
                company = comp_elem.get_text(strip=True) if comp_elem else "LinkedIn Employer"
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
                    "source": "linkedin",
                    "source_job_id": str(job_id),
                    "source_provenance": {
                        "adapter": "linkedin",
                        "confidence": "verified_direct_url"
                    },
                    "posted_at": datetime.utcnow(),
                    "last_verified_at": datetime.utcnow(),
                    "is_expired": False
                }
        except Exception as e:
            logger.error(f"Error parsing direct LinkedIn URL: {e}")
        return None
