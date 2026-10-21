from typing import Dict, Any, Optional
from .base import get_base_preamble

TEMPLATE_KEY = "compact_technical"
DISPLAY_NAME = "Compact Technical"
DESCRIPTION = "High-density engineering format with tight margins and inline tech stacks. Maximum information capacity for backend and systems roles."

def get_preamble(options: Optional[Dict[str, Any]] = None) -> str:
    options = options or {}
    font_size = options.get("font_size", "10pt")
    margins = options.get("margins", "0.45in")
    spacing = options.get("spacing", "tight")
    return get_base_preamble(
        font_size=font_size,
        margins=margins,
        spacing=spacing,
        font_package="",
        section_rule_color="black"
    )
