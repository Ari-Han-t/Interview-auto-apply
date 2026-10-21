import logging
from typing import Dict, Any, Optional, List

from .templates import get_template
from .section_renderers import (
    render_general_info,
    render_education,
    render_experience,
    render_projects,
    render_skills,
    render_achievements,
    render_certifications,
    render_leadership,
    render_coursework,
    render_publications,
    render_custom_sections,
)

logger = logging.getLogger(__name__)

RENDERER_REGISTRY = {
    "general_info": render_general_info,
    "education": render_education,
    "experience": render_experience,
    "projects": render_projects,
    "skills": render_skills,
    "achievements": render_achievements,
    "certifications": render_certifications,
    "leadership": render_leadership,
    "coursework": render_coursework,
    "publications": render_publications,
    "custom_sections": render_custom_sections,
}

def extract_active_refined_bullets(plan: Dict[str, Any]) -> Dict[str, str]:
    """
    Extracts bullet refinements that should be applied to the rendered LaTeX.
    Applies refinements with status 'accepted' or 'proposed' (unless explicitly 'rejected').
    """
    refinements = plan.get("refinements") or {}
    active_bullets = {}
    for bullet_id, ref in refinements.items():
        if isinstance(ref, dict):
            status = ref.get("status", "proposed")
            if status != "rejected":
                text = ref.get("refined") or ref.get("text")
                if text:
                    active_bullets[bullet_id] = text
        elif isinstance(ref, str) and ref.strip():
            active_bullets[bullet_id] = ref.strip()
    return active_bullets


def render_modular_resume(
    candidate_data: Dict[str, Any],
    assembly_plan: Dict[str, Any],
    template_name: Optional[str] = None,
    template_options: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Assembles a modular, ATS-compliant LaTeX resume document.
    Strictly follows the approved section order, included modules, and bullet selections.
    Does not regenerate uncontrolled LaTeX boilerplate.
    """
    t_name = template_name or assembly_plan.get("template_name") or "clean_ats"
    template_mod = get_template(t_name)
    
    t_options = dict(assembly_plan.get("template_options") or {})
    if template_options:
        t_options.update(template_options)

    # 1. Generate Preamble
    preamble = template_mod.get_preamble(t_options)

    # 2. Extract refined bullets
    refined_bullets = extract_active_refined_bullets(assembly_plan)

    # 3. Determine Section Order & Inclusions
    section_order: List[str] = assembly_plan.get("section_order") or [
        "general_info",
        "education",
        "skills",
        "projects",
        "experience",
        "achievements"
    ]

    sections_config: Dict[str, Any] = assembly_plan.get("sections") or {}

    rendered_body_parts: List[str] = []

    for section_key in section_order:
        sec_cfg = sections_config.get(section_key, {})
        # If explicitly excluded, omit
        if not sec_cfg.get("included", True):
            continue

        renderer = RENDERER_REGISTRY.get(section_key)
        if not renderer:
            logger.warning(f"No renderer found for section key '{section_key}'")
            continue

        selected_ids = sec_cfg.get("selected_item_ids")
        selected_bullets = sec_cfg.get("selected_bullets")

        try:
            if section_key == "general_info":
                contact_fields = sec_cfg.get("contact_fields")
                block = render_general_info(
                    candidate_data.get("general_info", {}),
                    contact_fields=contact_fields,
                    options=t_options
                )
            elif section_key == "education":
                block = render_education(
                    candidate_data.get("education", []),
                    selected_ids=selected_ids,
                    options=t_options
                )
            elif section_key == "experience":
                block = render_experience(
                    candidate_data.get("experience", []),
                    selected_ids=selected_ids,
                    selected_bullets=selected_bullets,
                    refined_bullets=refined_bullets,
                    options=t_options
                )
            elif section_key == "projects":
                block = render_projects(
                    candidate_data.get("projects", []),
                    selected_ids=selected_ids,
                    selected_bullets=selected_bullets,
                    refined_bullets=refined_bullets,
                    options=t_options
                )
            elif section_key == "skills":
                selected_cats = sec_cfg.get("selected_categories")
                block = render_skills(
                    candidate_data.get("skills", []),
                    selected_categories=selected_cats,
                    selected_skill_ids=selected_ids,
                    options=t_options
                )
            elif section_key == "achievements":
                block = render_achievements(
                    candidate_data.get("achievements", []),
                    selected_ids=selected_ids,
                    selected_bullets=selected_bullets,
                    refined_bullets=refined_bullets,
                    options=t_options
                )
            elif section_key == "certifications":
                block = render_certifications(
                    candidate_data.get("certifications", []),
                    selected_ids=selected_ids,
                    options=t_options
                )
            elif section_key == "leadership":
                block = render_leadership(
                    candidate_data.get("leadership", []),
                    selected_ids=selected_ids,
                    selected_bullets=selected_bullets,
                    refined_bullets=refined_bullets,
                    options=t_options
                )
            elif section_key == "coursework":
                block = render_coursework(
                    candidate_data.get("coursework", []),
                    selected_ids=selected_ids,
                    options=t_options
                )
            elif section_key == "publications":
                block = render_publications(
                    candidate_data.get("publications", []),
                    selected_ids=selected_ids,
                    selected_bullets=selected_bullets,
                    refined_bullets=refined_bullets,
                    options=t_options
                )
            elif section_key == "custom_sections":
                block = render_custom_sections(
                    candidate_data.get("custom_sections", []),
                    selected_ids=selected_ids,
                    selected_bullets=selected_bullets,
                    refined_bullets=refined_bullets,
                    options=t_options
                )
            else:
                block = ""

            if block and block.strip():
                rendered_body_parts.append(block.strip())

        except Exception as e:
            logger.error(f"Error rendering section '{section_key}': {e}", exc_info=True)

    # 4. Assemble Complete Document
    full_body = "\n\n".join(rendered_body_parts)

    tex_document = f"""{preamble}

\\begin{{document}}

{full_body}

\\end{{document}}
"""
    return tex_document.strip()
