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

# Sample permitted public feeds
DEFAULT_FEEDS = [
    {
        "name": "RemoteOK",
        "url": "https://remoteok.com/api",
        "type": "json"
    }
]

class CustomFeedAdapter(BaseJobSourceAdapter):
    source_id = "custom_feed"
    name = "Custom Feeds & Permitted APIs"
    auth_status = "available"
    can_fetch_catalog = True
    access_requirement = "Permitted RSS/Atom feeds and public job endpoints (RemoteOK, WeWorkRemotely feeds)."
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
        kw_list = [k.strip().lower() for k in keywords.split(",")] if keywords else []

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get("https://remoteok.com/api", headers={"User-Agent": "InterviewAutoApply/1.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        for item in data[1:limit+1]: # skip disclaimer item
                            title = item.get("position") or "Software Engineer"
                            company = item.get("company") or "Remote Company"
                            url = item.get("url") or f"https://remoteok.com/l/{item.get('id')}"
                            desc = clean_html(item.get("description") or "")
                            tags = item.get("tags") or []
                            loc = item.get("location") or "Remote"

                            search_space = f"{title} {company} {' '.join(tags)} {desc}".lower()
                            if kw_list and not any(k in search_space for k in kw_list):
                                continue

                            inf = infer_employment_and_arrangement(title, desc, loc)
                            if job_type == "internship" and inf["employment_type"] != "internship":
                                continue
                            if job_type == "fulltime" and inf["employment_type"] == "internship":
                                continue

                            skills = [t.title() for t in tags if len(t) < 20]
                            if not skills:
                                skills = extract_skills_from_text(f"{title} {desc}")
                            comp = parse_compensation(f"{item.get('salary_min', '')} - {item.get('salary_max', '')} USD")

                            epoch = item.get("epoch")
                            posted_at = datetime.fromtimestamp(epoch) if epoch else datetime.utcnow()

                            results.append({
                                "title": title,
                                "company": company,
                                "url": url,
                                "application_url": url,
                                "description": desc[:3000],
                                "responsibilities_json": extract_responsibilities_from_text(desc),
                                "required_skills_json": skills[:6],
                                "preferred_skills_json": skills[6:12],
                                "tech_stack_json": skills,
                                "location": loc,
                                "work_arrangement": "remote",
                                "employment_type": inf["employment_type"],
                                "is_remote": True,
                                "salary_range": comp["raw"],
                                "compensation_min": comp["min"],
                                "compensation_max": comp["max"],
                                "currency": comp["currency"],
                                "compensation_interval": comp["interval"],
                                "source": "custom_feed",
                                "source_job_id": str(item.get("id")),
                                "source_provenance": {
                                    "adapter": "custom_feed",
                                    "feed": "RemoteOK Public API",
                                    "confidence": "verified_feed"
                                },
                                "posted_at": posted_at,
                                "last_verified_at": datetime.utcnow(),
                                "is_expired": False
                            })
        except Exception as e:
            logger.warning(f"Error fetching custom feed: {e}")

        return results

    def parse_job_url(self, url: str) -> Optional[Dict[str, Any]]:
        return None
