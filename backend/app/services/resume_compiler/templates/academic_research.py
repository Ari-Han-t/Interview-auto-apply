from typing import Dict, Any, Optional
from .base import get_base_preamble

TEMPLATE_KEY = "academic_research"
DISPLAY_NAME = "Academic / Research"
DESCRIPTION = "Scholarly format optimized for research institutes, AI labs, graduate programs, and scientific positions. Highlights publications and coursework."

def get_preamble(options: Optional[Dict[str, Any]] = None) -> str:
    options = options or {}
    font_size = options.get("font_size", "10.5pt")
    margins = options.get("margins", "0.6in")
    spacing = options.get("spacing", "compact")
    return get_base_preamble(
        font_size=font_size,
        margins=margins,
        spacing=spacing,
        font_package="",
        section_rule_color="black"
    )
