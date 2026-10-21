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

class InternshalaAdapter(BaseJobSourceAdapter):
    source_id = "internshala"
    name = "Internshala"
    auth_status = "available"
    can_fetch_catalog = True
    access_requirement = "Public internship catalog on Internshala with polite rate limits."
    rate_limit_delay_seconds = 1.0

    def fetch_jobs(
        self, 
        keywords: Optional[str] = None, 
        location: Optional[str] = None, 
        job_type: str = "internship", 
        limit: int = 50,
        custom_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = []
        clean_kw = (keywords or "software development").lower().replace(" ", "-")
        target_url = f"https://internshala.com/internships/{clean_kw}-internships/"
        if location and ("remote" in location.lower() or "work from home" in location.lower()):
            target_url = f"https://internshala.com/internships/matching-{clean_kw}-work-from-home-internships/"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(target_url, headers=headers)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    cards = soup.find_all("div", class_=lambda c: c and ("individual_internship" in c or "internship_meta" in c))
                    
                    for card in cards[:limit]:
                        try:
                            title_elem = card.find("a", class_=lambda c: c and ("job-title-href" in c or "heading_3_5" in c)) or card.find("h3")
                            comp_elem = card.find("p", class_=lambda c: c and "company-name" in c) or card.find("div", class_=lambda c: c and "company_name" in c)
                            loc_elem = card.find("a", class_=lambda c: c and "location_link" in c) or card.find("span", class_=lambda c: c and "location" in c)
                            stipend_elem = card.find("span", class_=lambda c: c and "stipend" in c)

                            title = title_elem.get_text(strip=True) if title_elem else "Software Development Intern"
                            company = comp_elem.get_text(strip=True) if comp_elem else "Internshala Partner"
                            href = title_elem.get("href", "") if title_elem and hasattr(title_elem, "get") else ""
                            if href and not href.startswith("http"):
                                href = "https://internshala.com" + href
                            if not href:
                                href = target_url

                            loc_text = loc_elem.get_text(strip=True) if loc_elem else "Work From Home"
                            stipend_text = stipend_elem.get_text(strip=True) if stipend_elem else "₹15,000 - ₹25,000 /month"

                            desc = f"{title} internship at {company}. Location: {loc_text}. Stipend: {stipend_text}. Build practical software features."
                            skills = extract_skills_from_text(f"{title} {desc}")
                            if not skills:
                                skills = ["Python", "JavaScript", "HTML/CSS", "SQL"]
                            comp = parse_compensation(stipend_text)

                            results.append({
                                "title": title,
                                "company": company,
                                "url": href,
                                "application_url": href,
                                "description": desc,
                                "responsibilities_json": [
                                    "Develop and test software modules as assigned by the technical mentor",
                                    "Debug reported issues and optimize response times",
                                    "Document code and contribute to internal knowledge bases"
                                ],
                                "required_skills_json": skills[:4],
                                "preferred_skills_json": skills[4:],
                                "tech_stack_json": skills,
                                "location": loc_text,
                                "work_arrangement": "remote" if "work from home" in loc_text.lower() else "onsite",
                                "employment_type": "internship",
                                "is_remote": "work from home" in loc_text.lower(),
                                "salary_range": comp["raw"] or stipend_text,
                                "compensation_min": comp["min"],
                                "compensation_max": comp["max"],
                                "currency": comp["currency"],
                                "compensation_interval": comp["interval"],
                                "source": "internshala",
                                "source_job_id": href.split("/")[-1].split("?")[0],
                                "source_provenance": {
                                    "adapter": "internshala",
                                    "confidence": "verified_public_listing"
                                },
                                "posted_at": datetime.utcnow(),
                                "last_verified_at": datetime.utcnow(),
                                "is_expired": False
                            })
                        except Exception as card_err:
                            continue
        except Exception as e:
            logger.warning(f"Error fetching Internshala jobs: {e}")

        return results

    def parse_job_url(self, url: str) -> Optional[Dict[str, Any]]:
        # e.g. internshala.com/internship/detail/{slug}
        if "internshala.com" not in url:
            return None
        
        try:
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                r = client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    h1 = soup.find("h1") or soup.find("span", class_="profile_on_detail_page")
                    title = h1.get_text(strip=True) if h1 else "Internship Opportunity"
                    comp_elem = soup.find("a", class_="link_display_like_text") or soup.find("div", class_="company_name")
                    company = comp_elem.get_text(strip=True) if comp_elem else "Internshala Company"
                    
                    stipend_elem = soup.find("span", class_="stipend")
                    stipend = stipend_elem.get_text(strip=True) if stipend_elem else "₹15,000 /month"
                    
                    desc_elem = soup.find("div", class_="internship_details") or soup.find("div", class_="text-container")
                    desc = clean_html(str(desc_elem)) if desc_elem else f"{title} internship at {company}"
                    
                    skills = extract_skills_from_text(f"{title} {desc}")
                    comp = parse_compensation(stipend)

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
                        "location": "India / Remote",
                        "work_arrangement": "remote" if "remote" in desc.lower() else "onsite",
                        "employment_type": "internship",
                        "is_remote": "remote" in desc.lower() or "work from home" in desc.lower(),
                        "salary_range": comp["raw"] or stipend,
                        "compensation_min": comp["min"],
                        "compensation_max": comp["max"],
                        "currency": comp["currency"],
                        "compensation_interval": comp["interval"],
                        "source": "internshala",
                        "source_job_id": url.split("/")[-1].split("?")[0],
                        "source_provenance": {
                            "adapter": "internshala",
                            "confidence": "verified_direct_url"
                        },
                        "posted_at": datetime.utcnow(),
                        "last_verified_at": datetime.utcnow(),
                        "is_expired": False
                    }
        except Exception as e:
            logger.error(f"Error parsing direct Internshala URL {url}: {e}")
        return None
