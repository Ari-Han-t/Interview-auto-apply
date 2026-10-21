from typing import Dict, Any, Optional
from .base import get_base_preamble

TEMPLATE_KEY = "clean_ats"
DISPLAY_NAME = "Clean ATS-Friendly"
DESCRIPTION = "Single-column readable typography with clean section dividers. Highest machine-parsing compatibility across all enterprise ATS systems."

def get_preamble(options: Optional[Dict[str, Any]] = None) -> str:
    options = options or {}
    font_size = options.get("font_size", "10.8pt")
    margins = options.get("margins", "0.5in")
    spacing = options.get("spacing", "compact")
    return get_base_preamble(
        font_size=font_size,
        margins=margins,
        spacing=spacing,
        font_package="",  # Default clean Computer Modern / Latin Modern
        section_rule_color="black"
    )
