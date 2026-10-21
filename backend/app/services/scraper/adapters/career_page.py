import re
import json
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

class CareerPageAdapter(BaseJobSourceAdapter):
    source_id = "career_page"
    name = "Official Company Career Pages"
    auth_status = "available"
    can_fetch_catalog = True
    access_requirement = "Universal W3C schema.org/JobPosting JSON-LD and OpenGraph metadata extractor for official company career pages."
    rate_limit_delay_seconds = 1.0

    def fetch_jobs(
        self, 
        keywords: Optional[str] = None, 
        location: Optional[str] = None, 
        job_type: str = "both", 
        limit: int = 50,
        custom_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        # If user provides a custom career page URL, parse it
        if custom_token and custom_token.startswith("http"):
            parsed = self.parse_job_url(custom_token)
            return [parsed] if parsed else []
        return []

    def parse_job_url(self, url: str) -> Optional[Dict[str, Any]]:
        if not url.startswith("http"):
            return None
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code != 200:
                    return None
                
                soup = BeautifulSoup(resp.text, "html.parser")
                
                # 1. Search for JSON-LD schema.org/JobPosting
                script_tags = soup.find_all("script", type="application/ld+json")
                for s in script_tags:
                    try:
                        raw = s.string or s.get_text()
                        if not raw:
                            continue
                        data = json.loads(raw.strip())
                        # If list or graph
                        items = data if isinstance(data, list) else data.get("@graph", [data])
                        for item in items:
                            if item.get("@type") == "JobPosting":
                                title = item.get("title", "Software Engineer")
                                org = item.get("hiringOrganization", {})
                                company = org.get("name") if isinstance(org, dict) else (org or "Tech Company")
                                raw_desc = item.get("description", "")
                                clean_desc = clean_html(raw_desc)
                                
                                loc_obj = item.get("jobLocation", {})
                                loc = "Remote"
                                if isinstance(loc_obj, dict):
                                    addr = loc_obj.get("address", {})
                                    loc = addr.get("addressLocality") or addr.get("addressCountry") or "Remote"
                                
                                skills = extract_skills_from_text(f"{title} {clean_desc}")
                                inf = infer_employment_and_arrangement(title, clean_desc, str(loc))
                                comp_obj = item.get("baseSalary", {})
                                salary_str = None
                                if isinstance(comp_obj, dict):
                                    val = comp_obj.get("value", {})
                                    if isinstance(val, dict):
                                        salary_str = f"{val.get('minValue', '')} - {val.get('maxValue', '')} {comp_obj.get('currency', 'USD')}"
                                
                                comp = parse_compensation(salary_str or clean_desc)
                                date_posted_str = item.get("datePosted")
                                posted_at = datetime.fromisoformat(date_posted_str.replace("Z", "+00:00")) if date_posted_str else datetime.utcnow()
                                
                                valid_through = item.get("validThrough")
                                deadline = datetime.fromisoformat(valid_through.replace("Z", "+00:00")) if valid_through else None

                                return {
                                    "title": title,
                                    "company": company,
                                    "url": url,
                                    "application_url": url,
                                    "description": clean_desc,
                                    "responsibilities_json": extract_responsibilities_from_text(clean_desc),
                                    "required_skills_json": skills[:6],
                                    "preferred_skills_json": skills[6:12],
                                    "tech_stack_json": skills,
                                    "location": str(loc),
                                    "work_arrangement": inf["work_arrangement"],
                                    "employment_type": inf["employment_type"],
                                    "is_remote": inf["is_remote"],
                                    "salary_range": comp["raw"],
                                    "compensation_min": comp["min"],
                                    "compensation_max": comp["max"],
                                    "currency": comp["currency"],
                                    "compensation_interval": comp["interval"],
                                    "source": "career_page",
                                    "source_job_id": re.sub(r'[^a-zA-Z0-9]', '', url)[-16:],
                                    "source_provenance": {
                                        "adapter": "career_page",
                                        "schema_type": "schema.org/JobPosting",
                                        "confidence": "verified_json_ld"
                                    },
                                    "posted_at": posted_at,
                                    "deadline": deadline,
                                    "last_verified_at": datetime.utcnow(),
                                    "is_expired": False
                                }
                    except Exception:
                        continue

                # 2. Fallback to OpenGraph and semantic HTML
                og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "twitter:title"})
                og_site = soup.find("meta", property="og:site_name")
                og_desc = soup.find("meta", property="og:description")
                h1 = soup.find("h1")

                title = og_title.get("content") if og_title else (h1.get_text(strip=True) if h1 else "Software Engineering Position")
                company = og_site.get("content") if og_site else "Tech Company"
                desc = og_desc.get("content") if og_desc else soup.get_text()[:1500]

                skills = extract_skills_from_text(f"{title} {desc}")
                inf = infer_employment_and_arrangement(title, desc, "Remote")
                comp = parse_compensation(desc)

                return {
                    "title": title,
                    "company": company,
                    "url": url,
                    "application_url": url,
                    "description": clean_html(desc),
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
                    "source": "career_page",
                    "source_job_id": re.sub(r'[^a-zA-Z0-9]', '', url)[-16:],
                    "source_provenance": {
                        "adapter": "career_page",
                        "schema_type": "html_metadata",
                        "confidence": "inferred_html"
                    },
                    "posted_at": datetime.utcnow(),
                    "last_verified_at": datetime.utcnow(),
                    "is_expired": False
                }
        except Exception as e:
            logger.error(f"Error parsing career page {url}: {e}")
        return None
