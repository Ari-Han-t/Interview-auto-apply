from typing import Dict, Any, Optional
from .base import get_base_preamble

TEMPLATE_KEY = "traditional_professional"
DISPLAY_NAME = "Traditional Professional"
DESCRIPTION = "Classic serif typography and standard corporate margins. Ideal for enterprise, finance, management, and traditional corporate recruiters."

def get_preamble(options: Optional[Dict[str, Any]] = None) -> str:
    options = options or {}
    font_size = options.get("font_size", "11pt")
    margins = options.get("margins", "0.65in")
    spacing = options.get("spacing", "normal")
    return get_base_preamble(
        font_size=font_size,
        margins=margins,
        spacing=spacing,
        font_package="",
        section_rule_color="black"
    )
