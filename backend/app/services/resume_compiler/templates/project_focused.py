from typing import Dict, Any, Optional
from .base import get_base_preamble

TEMPLATE_KEY = "project_focused"
DISPLAY_NAME = "Project-Focused Early-Career"
DESCRIPTION = "Engineered specifically for students and early-career candidates. Emphasizes production-grade projects, GitHub repositories, and hackathon wins."

def get_preamble(options: Optional[Dict[str, Any]] = None) -> str:
    options = options or {}
    font_size = options.get("font_size", "10.5pt")
    margins = options.get("margins", "0.5in")
    spacing = options.get("spacing", "compact")
    return get_base_preamble(
        font_size=font_size,
        margins=margins,
        spacing=spacing,
        font_package="",
        section_rule_color="black"
    )
