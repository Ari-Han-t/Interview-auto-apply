import re
import html
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# Common skill dictionary for canonical extraction
TECH_TAXONOMY = {
    "python": "Python",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "react": "React",
    "react.js": "React",
    "next.js": "Next.js",
    "vue": "Vue",
    "angular": "Angular",
    "node": "Node.js",
    "node.js": "Node.js",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "express": "Express",
    "java": "Java",
    "spring": "Spring Boot",
    "c++": "C++",
    "c#": "C#",
    ".net": ".NET",
    "golang": "Go",
    "go": "Go",
    "rust": "Rust",
    "sql": "SQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    "git": "Git",
    "graphql": "GraphQL",
    "rest": "REST APIs",
    "api": "APIs",
    "apis": "APIs",
    "cloud": "Cloud Deployment",
    "cloud deployment": "Cloud Deployment",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit-learn": "Scikit-Learn",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "ai": "Artificial Intelligence",
    "llm": "LLMs",
    "rag": "RAG",
    "linux": "Linux"
}

def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', raw_html)
    clean = html.unescape(clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def extract_skills_from_text(text: str) -> List[str]:
    if not text:
        return []
    text_lower = text.lower()
    found = set()
    for kw, standard_name in TECH_TAXONOMY.items():
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, text_lower):
            found.add(standard_name)
    return sorted(list(found))

def extract_responsibilities_from_text(text: str) -> List[str]:
    if not text:
        return []
    lines = text.split("\n")
    bullet_items = []
    for line in lines:
        cleaned = line.strip()
        if re.match(r'^[-*•]\s+', cleaned):
            item = re.sub(r'^[-*•]\s+', '', cleaned).strip()
            if len(item) > 15:
                bullet_items.append(item)
    return bullet_items[:8]

def parse_compensation(text: str) -> Dict[str, Any]:
    """Extract structured compensation numbers from raw text when available."""
    if not text:
        return {"raw": None, "min": None, "max": None, "currency": "USD", "interval": None}
    
    # Check for Indian Rupee
    inr_match = re.search(r'(?:₹|rs\.?|inr)\s*([\d,]+)(?:\s*-\s*([\d,]+))?', text, re.IGNORECASE)
    if inr_match:
        min_val = float(inr_match.group(1).replace(",", ""))
        max_val = float(inr_match.group(2).replace(",", "")) if inr_match.group(2) else min_val
        interval = "monthly" if "month" in text.lower() else "yearly"
        return {"raw": text.strip(), "min": min_val, "max": max_val, "currency": "INR", "interval": interval}

    # Check for USD / EUR / GBP
    usd_match = re.search(r'(\$|€|£)\s*([\d,]+)(?:\s*(?:k|K))?(?:\s*-\s*(?:\$|€|£)?\s*([\d,]+)(?:\s*(?:k|K))?)?', text)
    if usd_match:
        curr_symbol = usd_match.group(1)
        curr = "USD" if curr_symbol == "$" else ("EUR" if curr_symbol == "€" else "GBP")
        val1 = float(usd_match.group(2).replace(",", ""))
        if "k" in text.lower() and val1 < 1000:
            val1 *= 1000
        val2 = float(usd_match.group(3).replace(",", "")) if usd_match.group(3) else val1
        if "k" in text.lower() and val2 < 1000:
            val2 *= 1000
        interval = "yearly" if val1 > 20000 else ("monthly" if val1 > 1000 else "hourly")
        return {"raw": text.strip(), "min": val1, "max": val2, "currency": curr, "interval": interval}
    
    return {"raw": text.strip(), "min": None, "max": None, "currency": "USD", "interval": None}

def infer_employment_and_arrangement(title: str, desc: str, location: str) -> Dict[str, Any]:
    text = f"{title} {desc} {location}".lower()
    
    # Employment Type
    if "intern" in text or "internship" in text:
        emp_type = "internship"
    elif "contract" in text or "freelance" in text:
        emp_type = "contract"
    elif "part-time" in text or "part time" in text:
        emp_type = "parttime"
    else:
        emp_type = "fulltime"
        
    # Work arrangement
    if "remote" in text or "work from home" in text or "anywhere" in text:
        arrangement = "remote"
        is_remote = True
    elif "hybrid" in text:
        arrangement = "hybrid"
        is_remote = False
    else:
        arrangement = "onsite"
        is_remote = False
        
    return {"employment_type": emp_type, "work_arrangement": arrangement, "is_remote": is_remote}


class BaseJobSourceAdapter(ABC):
    source_id: str = "generic"
    name: str = "Generic Adapter"
    auth_status: str = "available" # available, limited, requires_auth, blocked_for_scraping
    can_fetch_catalog: bool = True
    access_requirement: str = "Publicly accessible."
    rate_limit_delay_seconds: float = 1.0

    @abstractmethod
    def fetch_jobs(
        self, 
        keywords: Optional[str] = None, 
        location: Optional[str] = None, 
        job_type: str = "both", 
        limit: int = 50,
        custom_token: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch jobs matching criteria from this source."""
        pass

    @abstractmethod
    def parse_job_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse a direct job posting URL for this source."""
        pass

    def check_job_active(self, url: str) -> bool:
        """Check if an existing job is still active at the source."""
        return True

    def health_check(self) -> Dict[str, Any]:
        """Verify if source adapter is functioning or reachable."""
        return {
            "source_id": self.source_id,
            "name": self.name,
            "auth_status": self.auth_status,
            "can_fetch_catalog": self.can_fetch_catalog,
            "access_requirement": self.access_requirement,
            "healthy": self.auth_status in ("available", "limited")
        }
