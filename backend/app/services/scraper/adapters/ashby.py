import re
import httpx
import logging
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

DEFAULT_ASHBY_ORGS = ["ramp", "linear", "retool", "notion", "synthesia", "cursor"]

class AshbyAdapter(BaseJobSourceAdapter):
    source_id = "ashby"
    name = "Ashby Career Pages"
    auth_status = "available"
    can_fetch_catalog = True
    access_requirement = "Official Ashby Job Board Posting API. No authentication required."
    rate_limit_delay_seconds = 0.5

    def fetch_jobs(
        self, 
        keywords: Optional[str] = None, 
        location: Optional[str] = None, 
        job_type: str = "both", 
        limit: int = 50,
        custom_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        orgs = [custom_token.strip().lower()] if custom_token else DEFAULT_ASHBY_ORGS
        results = []
        kw_list = [k.strip().lower() for k in keywords.split(",")] if keywords else []

        for org in orgs:
            if len(results) >= limit:
                break
            url = f"https://api.ashbyhq.com/posting-api/job-board/{org}"
            try:
                with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                    resp = client.get(url, headers={"User-Agent": "InterviewAutoApply/1.0"})
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    jobs_list = data.get("jobs", [])
                    
                    for item in jobs_list:
                        title = item.get("title") or "Software Engineer"
                        job_id = str(item.get("id", ""))
                        hosted_url = item.get("jobUrl") or f"https://jobs.ashbyhq.com/{org}/{job_id}"
                        apply_url = item.get("applyUrl") or hosted_url
                        
                        raw_desc = item.get("descriptionHtml") or item.get("descriptionPlain") or ""
                        clean_desc = clean_html(raw_desc)
                        
                        loc_name = item.get("location") or "Remote"
                        
                        search_space = f"{title} {clean_desc}".lower()
                        if kw_list and not any(k in search_space for k in kw_list):
                            continue
                            
                        inf = infer_employment_and_arrangement(title, clean_desc, loc_name)
                        if job_type == "internship" and inf["employment_type"] != "internship":
                            continue
                        if job_type == "fulltime" and inf["employment_type"] == "internship":
                            continue
                            
                        skills = extract_skills_from_text(f"{title} {clean_desc}")
                        resps = extract_responsibilities_from_text(clean_desc)
                        comp = parse_compensation(clean_desc)
                        
                        published_at = item.get("publishedAt")
                        posted_at = datetime.fromisoformat(published_at.replace("Z", "+00:00")) if published_at else datetime.utcnow()

                        results.append({
                            "title": title,
                            "company": org.replace("-", " ").title(),
                            "url": hosted_url,
                            "application_url": apply_url,
                            "description": clean_desc,
                            "responsibilities_json": resps,
                            "required_skills_json": skills[:6],
                            "preferred_skills_json": skills[6:12],
                            "tech_stack_json": skills,
                            "location": loc_name,
                            "work_arrangement": inf["work_arrangement"],
                            "employment_type": inf["employment_type"],
                            "is_remote": inf["is_remote"],
                            "salary_range": comp["raw"],
                            "compensation_min": comp["min"],
                            "compensation_max": comp["max"],
                            "currency": comp["currency"],
                            "compensation_interval": comp["interval"],
                            "source": "ashby",
                            "source_job_id": job_id,
                            "source_provenance": {
                                "adapter": "ashby",
                                "organization": org,
                                "api_endpoint": url,
                                "confidence": "verified_official_api"
                            },
                            "posted_at": posted_at,
                            "last_verified_at": datetime.utcnow(),
                            "is_expired": False
                        })
            except Exception as e:
                logger.warning(f"Failed to fetch Ashby postings for {org}: {e}")

        return results

    def parse_job_url(self, url: str) -> Optional[Dict[str, Any]]:
        # e.g. jobs.ashbyhq.com/{org}/{id}
        m = re.search(r'jobs\.ashbyhq\.com/([^/]+)/([a-f0-9\-]+)', url)
        if not m:
            return None
            
        org = m.group(1)
        job_id = m.group(2)
        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{org}"
        
        try:
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                r = client.get(api_url)
                if r.status_code == 200:
                    data = r.json()
                    jobs_list = data.get("jobs", [])
                    matched = next((j for j in jobs_list if str(j.get("id")) == job_id), None)
                    if matched:
                        title = matched.get("title", "Software Engineer")
                        clean_desc = clean_html(matched.get("descriptionHtml") or matched.get("descriptionPlain") or "")
                        loc = matched.get("location") or "Remote"
                        skills = extract_skills_from_text(f"{title} {clean_desc}")
                        inf = infer_employment_and_arrangement(title, clean_desc, loc)
                        comp = parse_compensation(clean_desc)
                        
                        return {
                            "title": title,
                            "company": org.capitalize(),
                            "url": url,
                            "application_url": matched.get("applyUrl") or url,
                            "description": clean_desc,
                            "responsibilities_json": extract_responsibilities_from_text(clean_desc),
                            "required_skills_json": skills[:6],
                            "preferred_skills_json": skills[6:12],
                            "tech_stack_json": skills,
                            "location": loc,
                            "work_arrangement": inf["work_arrangement"],
                            "employment_type": inf["employment_type"],
                            "is_remote": inf["is_remote"],
                            "salary_range": comp["raw"],
                            "compensation_min": comp["min"],
                            "compensation_max": comp["max"],
                            "currency": comp["currency"],
                            "compensation_interval": comp["interval"],
                            "source": "ashby",
                            "source_job_id": str(job_id),
                            "source_provenance": {
                                "adapter": "ashby",
                                "organization": org,
                                "confidence": "verified_direct_url"
                            },
                            "posted_at": datetime.utcnow(),
                            "last_verified_at": datetime.utcnow(),
                            "is_expired": False
                        }
        except Exception as e:
            logger.error(f"Error parsing direct Ashby URL {url}: {e}")
        return None

    def check_job_active(self, url: str) -> bool:
        parsed = self.parse_job_url(url)
        return parsed is not None
