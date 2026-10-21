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

DEFAULT_GREENHOUSE_BOARDS = ["stripe", "figma", "cloudflare", "datadog", "airbnb", "uber", "affirm"]

class GreenhouseAdapter(BaseJobSourceAdapter):
    source_id = "greenhouse"
    name = "Greenhouse Career Boards"
    auth_status = "available"
    can_fetch_catalog = True
    access_requirement = "Official Greenhouse Public Board API. No authentication required."
    rate_limit_delay_seconds = 0.5

    def fetch_jobs(
        self, 
        keywords: Optional[str] = None, 
        location: Optional[str] = None, 
        job_type: str = "both", 
        limit: int = 50,
        custom_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        boards = [custom_token.strip().lower()] if custom_token else DEFAULT_GREENHOUSE_BOARDS
        results = []
        kw_list = [k.strip().lower() for k in keywords.split(",")] if keywords else []

        for board in boards:
            if len(results) >= limit:
                break
            url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
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
                        job_url = item.get("absolute_url") or f"https://boards.greenhouse.io/{board}/jobs/{job_id}"
                        raw_desc = item.get("content") or ""
                        clean_desc = clean_html(raw_desc)
                        
                        loc_obj = item.get("location", {})
                        loc_name = loc_obj.get("name") if isinstance(loc_obj, dict) else "Remote"
                        if not loc_name:
                            loc_name = "Remote"
                            
                        # Keywords matching
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
                        
                        updated_at_str = item.get("updated_at")
                        posted_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00")) if updated_at_str else datetime.utcnow()

                        results.append({
                            "title": title,
                            "company": board.replace("-", " ").title(),
                            "url": job_url,
                            "application_url": job_url,
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
                            "source": "greenhouse",
                            "source_job_id": job_id,
                            "source_provenance": {
                                "adapter": "greenhouse",
                                "board_token": board,
                                "api_endpoint": url,
                                "confidence": "verified_official_api"
                            },
                            "posted_at": posted_at,
                            "last_verified_at": datetime.utcnow(),
                            "is_expired": False
                        })
            except Exception as e:
                logger.warning(f"Failed to fetch Greenhouse board {board}: {e}")

        return results

    def parse_job_url(self, url: str) -> Optional[Dict[str, Any]]:
        # e.g. boards.greenhouse.io/{board}/jobs/{id}
        m = re.search(r'boards\.greenhouse\.io/([^/]+)/jobs/(\d+)', url)
        if not m:
            m = re.search(r'boards\.greenhouse\.io/embed/job_app\?for=([^&]+)&token=(\d+)', url)
        if not m:
            return None
        
        board_token = m.group(1)
        job_id = m.group(2)
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"
        
        try:
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                r = client.get(api_url)
                if r.status_code == 200:
                    data = r.json()
                    title = data.get("title", "Software Engineer")
                    clean_desc = clean_html(data.get("content", ""))
                    loc = data.get("location", {}).get("name", "Remote") if isinstance(data.get("location"), dict) else "Remote"
                    skills = extract_skills_from_text(f"{title} {clean_desc}")
                    inf = infer_employment_and_arrangement(title, clean_desc, loc)
                    comp = parse_compensation(clean_desc)
                    
                    return {
                        "title": title,
                        "company": board_token.capitalize(),
                        "url": url,
                        "application_url": url,
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
                        "source": "greenhouse",
                        "source_job_id": str(job_id),
                        "source_provenance": {
                            "adapter": "greenhouse",
                            "board_token": board_token,
                            "confidence": "verified_direct_url"
                        },
                        "posted_at": datetime.utcnow(),
                        "last_verified_at": datetime.utcnow(),
                        "is_expired": False
                    }
        except Exception as e:
            logger.error(f"Error parsing direct Greenhouse URL {url}: {e}")
        return None

    def check_job_active(self, url: str) -> bool:
        parsed = self.parse_job_url(url)
        return parsed is not None
