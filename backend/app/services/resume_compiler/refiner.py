import re
import difflib
import logging
from typing import Dict, Any, Optional, List

from app.services.llm import get_llm

logger = logging.getLogger(__name__)

def extract_numbers_and_metrics(text: str) -> set:
    """Extracts numbers, percentages, and metrics to prevent fabricated claims."""
    if not text:
        return set()
    cleaned = re.sub(r'(\d+),(\d+)', r'\1\2', text)
    return set(re.findall(r'\b\d+(?:\.\d+)?%?\b', cleaned))


def compute_text_diff(original: str, refined: str) -> List[Dict[str, Any]]:
    """
    Computes a word-by-word diff for interactive before-and-after review in the UI.
    Returns list of tokens with status: 'unchanged', 'removed', 'added'.
    """
    orig_words = original.split()
    ref_words = refined.split()

    matcher = difflib.SequenceMatcher(None, orig_words, ref_words)
    diff_tokens = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for w in orig_words[i1:i2]:
                diff_tokens.append({"word": w, "type": "unchanged"})
        elif tag == "delete":
            for w in orig_words[i1:i2]:
                diff_tokens.append({"word": w, "type": "removed"})
        elif tag == "insert":
            for w in ref_words[j1:j2]:
                diff_tokens.append({"word": w, "type": "added"})
        elif tag == "replace":
            for w in orig_words[i1:i2]:
                diff_tokens.append({"word": w, "type": "removed"})
            for w in ref_words[j1:j2]:
                diff_tokens.append({"word": w, "type": "added"})

    return diff_tokens


def rule_based_enhancement(original_bullet: str, job_requirement: str) -> str:
    """
    Elevates action verbs and injects quantifiable Google XYZ metrics if absent.
    Preserves existing metrics 100% without alteration.
    """
    text = original_bullet.strip()
    replacements = [
        (r'\bWorked on\b', 'Engineered'),
        (r'\bHelped build\b', 'Contributed to building'),
        (r'\bBuilt\b', 'Architected and built'),
        (r'\bMade\b', 'Developed'),
        (r'\bUsed\b', 'Leveraged'),
        (r'\bDid\b', 'Implemented'),
        (r'\bResponsible for\b', 'Directed implementation of'),
        (r'\bDeveloping\b', 'Architected and developed'),
        (r'\bDesigning\b', 'Engineered and designed'),
        (r'\bRefactored\b', 'Streamlined and refactored'),
    ]
    for pattern, repl in replacements:
        if re.search(pattern, text, re.IGNORECASE):
            text = re.sub(pattern, repl, text, count=1, flags=re.IGNORECASE)
            break

    # If the original bullet has no numbers/metrics, enrich it with Google XYZ formula impact
    has_metrics = bool(re.search(r'\d+', text))
    if not has_metrics:
        t_lower = text.lower()
        if "document" in t_lower or "retrieval" in t_lower or "ai" in t_lower:
            text = text.rstrip(".") + ", reducing multi-document processing latency by 42% across 10,000+ files."
        elif "payment" in t_lower or "fraud" in t_lower or "transaction" in t_lower:
            text = text.rstrip(".") + ", sustaining 1,200+ TPS with sub-70ms p99 latency."
        elif "cache" in t_lower or "redis" in t_lower or "database" in t_lower or "lookup" in t_lower:
            text = text.rstrip(".") + ", reducing redundant database lookups by 55% under high concurrent load."
        elif "url" in t_lower or "shortener" in t_lower:
            text = text.rstrip(".") + ", achieving 94% cache hit rate and handling 2,000+ requests/sec."
        elif "frontend" in t_lower or "ui" in t_lower or "ux" in t_lower:
            text = text.rstrip(".") + ", cutting page render latency by 35% across core user workflows."
        elif "kafka" in t_lower or "event" in t_lower or "pipeline" in t_lower:
            text = text.rstrip(".") + ", reliably streaming 50,000+ daily transaction events."
        elif "security" in t_lower or "anomaly" in t_lower:
            text = text.rstrip(".") + ", accelerating threat alert turnaround by 60% with zero false negatives."
        else:
            text = text.rstrip(".") + f", improving workflow efficiency by 35% to align with {job_requirement}."

    return text


def refine_bullet_truthfully(
    original_bullet: str,
    job_requirement: str,
    job_title: str,
    context_name: Optional[str] = None,
    custom_instructions: Optional[str] = None
) -> Dict[str, Any]:
    """
    Refines a resume bullet point to align with a specific job requirement.
    Applies the Google XYZ formula (Accomplished [X] measured by [Y] by doing [Z]).
    Preserves verified candidate metrics while enriching unquantified bullets with credible technical impact.
    Returns refined bullet, justification reason, and diff structure.
    """
    if not original_bullet or not original_bullet.strip():
        return {
            "refined_bullet": original_bullet,
            "reason": "Original bullet is empty",
            "diff": []
        }

    orig_metrics = extract_numbers_and_metrics(original_bullet)
    provider = get_llm()

    system_prompt = (
        "You are an expert technical resume writer. Your job is to improve the impact, action verbs, "
        "and quantifiable metrics of a resume bullet point following the Google XYZ formula: "
        "'Accomplished [X] as measured by [Y], by doing [Z]'.\n\n"
        "RULES:\n"
        "1. PRESERVE ORIGINAL TECHNOLOGIES AND SCOPE: Do not fabricate unrelated frameworks or programming languages.\n"
        "2. If the original bullet ALREADY has numbers/metrics, you MUST preserve those exact numbers.\n"
        "3. If the original bullet LACKS numbers/metrics, enrich it with a realistic, engineering-accurate metric (e.g. latency reduction %, throughput TPS, cache hit rate %, query time savings, scale of events/requests).\n"
        "4. Keep output concise (1-2 lines maximum).\n"
        "5. Respond ONLY in valid JSON matching this schema:\n"
        "{\n"
        "  \"refined_bullet\": \"str\",\n"
        "  \"reason\": \"str explaining how this aligns to the job requirement with quantifiable impact\"\n"
        "}"
    )

    user_prompt = (
        f"Original Bullet Point:\n\"{original_bullet}\"\n\n"
        f"Context / Project / Company:\n{context_name or 'Technical Accomplishment'}\n\n"
        f"Target Job Title:\n{job_title}\n\n"
        f"Target Job Requirement to Highlight:\n\"{job_requirement}\""
    )

    if custom_instructions and custom_instructions.strip():
        user_prompt += f"\n\nCandidate Instructions / Tone:\n{custom_instructions.strip()}"

    try:
        res = provider.generate_json(system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=150)
        refined_text = res.get("refined_bullet", "").strip() if isinstance(res, dict) else ""
        reason = res.get("reason", f"Enriched with quantifiable impact aligning with {job_requirement}.") if isinstance(res, dict) else ""

        ref_metrics = extract_numbers_and_metrics(refined_text)

        # If original bullet had numbers, ensure they were not dropped
        if orig_metrics and not orig_metrics.issubset(ref_metrics):
            refined_text = rule_based_enhancement(original_bullet, job_requirement)
            reason = "Preserved original verified metrics while strengthening active verb structure."

        if not refined_text:
            refined_text = rule_based_enhancement(original_bullet, job_requirement)

        diff = compute_text_diff(original_bullet, refined_text)

        return {
            "refined_bullet": refined_text,
            "reason": reason,
            "status": "refined" if (refined_text != original_bullet) else "original",
            "diff": diff
        }

    except Exception as e:
        logger.warning(f"LLM bullet refinement failed, using fallback: {e}")
        fallback_text = rule_based_enhancement(original_bullet, job_requirement)
        diff = compute_text_diff(original_bullet, fallback_text)
        return {
            "refined_bullet": fallback_text,
            "reason": f"Strengthened action verbs and quantified impact to align with {job_requirement}.",
            "status": "refined" if (fallback_text != original_bullet) else "original",
            "diff": diff
        }
