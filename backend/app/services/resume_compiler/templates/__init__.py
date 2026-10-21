from typing import Dict, Any, List
from . import clean_ats, compact_technical, traditional_professional, academic_research, project_focused

TEMPLATES: Dict[str, Any] = {
    clean_ats.TEMPLATE_KEY: clean_ats,
    compact_technical.TEMPLATE_KEY: compact_technical,
    traditional_professional.TEMPLATE_KEY: traditional_professional,
    academic_research.TEMPLATE_KEY: academic_research,
    project_focused.TEMPLATE_KEY: project_focused,
}

def get_template(template_name: str):
    return TEMPLATES.get(template_name, clean_ats)

def list_templates() -> List[Dict[str, str]]:
    return [
        {
            "id": k,
            "name": mod.DISPLAY_NAME,
            "description": mod.DESCRIPTION
        }
        for k, mod in TEMPLATES.items()
    ]
