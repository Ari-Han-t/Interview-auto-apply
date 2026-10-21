import logging
from typing import Dict, List, Optional, Any
from .base import BaseJobSourceAdapter
from .greenhouse import GreenhouseAdapter
from .lever import LeverAdapter
from .ashby import AshbyAdapter
from .yc import YCAdapter
from .internshala import InternshalaAdapter
from .career_page import CareerPageAdapter
from .linkedin import LinkedInAdapter
from .indeed import IndeedAdapter
from .wellfound import WellfoundAdapter
from .glassdoor import GlassdoorAdapter
from .custom_feed import CustomFeedAdapter

logger = logging.getLogger(__name__)

ADAPTERS_MAP: Dict[str, BaseJobSourceAdapter] = {
    "greenhouse": GreenhouseAdapter(),
    "lever": LeverAdapter(),
    "ashby": AshbyAdapter(),
    "yc": YCAdapter(),
    "internshala": InternshalaAdapter(),
    "career_page": CareerPageAdapter(),
    "linkedin": LinkedInAdapter(),
    "indeed": IndeedAdapter(),
    "wellfound": WellfoundAdapter(),
    "glassdoor": GlassdoorAdapter(),
    "custom_feed": CustomFeedAdapter(),
}

def get_adapter(source_id: str) -> Optional[BaseJobSourceAdapter]:
    return ADAPTERS_MAP.get(source_id.lower())

def list_adapters() -> List[BaseJobSourceAdapter]:
    return list(ADAPTERS_MAP.values())

def get_sources_health() -> List[Dict[str, Any]]:
    return [adapter.health_check() for adapter in ADAPTERS_MAP.values()]

def route_url_to_adapter(url: str) -> BaseJobSourceAdapter:
    """Intelligently detects which adapter handles a given job URL."""
    lowered = url.lower()
    if "greenhouse.io" in lowered:
        return ADAPTERS_MAP["greenhouse"]
    if "lever.co" in lowered:
        return ADAPTERS_MAP["lever"]
    if "ashbyhq.com" in lowered:
        return ADAPTERS_MAP["ashby"]
    if "ycombinator.com" in lowered:
        return ADAPTERS_MAP["yc"]
    if "internshala.com" in lowered:
        return ADAPTERS_MAP["internshala"]
    if "linkedin.com" in lowered:
        return ADAPTERS_MAP["linkedin"]
    if "indeed.com" in lowered:
        return ADAPTERS_MAP["indeed"]
    if "wellfound.com" in lowered or "angel.co" in lowered:
        return ADAPTERS_MAP["wellfound"]
    if "glassdoor.com" in lowered:
        return ADAPTERS_MAP["glassdoor"]
    
    # Generic fallback: official company career page JSON-LD parser
    return ADAPTERS_MAP["career_page"]
