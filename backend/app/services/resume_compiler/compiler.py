import os
import re
import shutil
import subprocess
import tempfile
import zipfile
import json
import logging
from typing import Dict, Any, Optional, Tuple, List

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

logger = logging.getLogger(__name__)

def _clean_latex_inline(s: str) -> str:
    """Cleans inline LaTeX commands into plain, readable ATS text."""
    if not s:
        return ""
    # Convert \href{url}{anchor} -> anchor
    s = re.sub(r'\\href\{[^{}]*\}\{([^{}]*)\}', r'\1', s)
    while r'\href{' in s:
        new_s = re.sub(r'\\href\{[^{}]*\}\{([^{}]*)\}', r'\1', s)
        if new_s == s:
            s = re.sub(r'\\href\{.*?\}\{(.*?)\}', r'\2', s)
            break
        s = new_s

    # Convert \url{url} -> url
    s = re.sub(r'\\url\{([^{}]*)\}', r'\1', s)

    # Strip inline wrappers: \textbf, \textit, \emph, \scshape, \Huge, etc.
    tags = [
        'textbf', 'textit', 'emph', 'text', 'small', 'scshape', 
        'large', 'Large', 'Huge', 'huge', 'normalfont', 'color'
    ]
    for tag in tags:
        s = re.sub(r'\\' + tag + r'\{([^{}]*)\}', r'\1', s)
        s = re.sub(r'\\' + tag + r'\b', ' ', s)

    # Clean math delimiters and separators
    s = s.replace(r'$|$', ' | ').replace('$', '')
    # Convert escaped symbols
    s = s.replace(r'\&', '&').replace(r'\%', '%').replace(r'\#', '#').replace(r'\_', '_').replace(r'\\', ' ')
    # Remove any residual LaTeX command keywords
    s = re.sub(r'\\[a-zA-Z]+', ' ', s)
    # Remove leftover braces
    s = s.replace('{', '').replace('}', '').strip()
    return re.sub(r'\s+', ' ', s)


def _extract_braced_arguments(s: str, start_pos: int = 0, count: int = 2) -> Tuple[List[str], int]:
    """Extracts balanced braced arguments {arg1}{arg2}... from a LaTeX string."""
    args = []
    curr = start_pos
    for _ in range(count):
        idx = s.find('{', curr)
        if idx == -1:
            break
        depth = 0
        start = idx + 1
        found_end = -1
        for j in range(idx, len(s)):
            if s[j] == '{':
                depth += 1
            elif s[j] == '}':
                depth -= 1
                if depth == 0:
                    found_end = j
                    break
        if found_end != -1:
            args.append(s[start:found_end])
            curr = found_end + 1
        else:
            break
    return args, curr


def _strip_latex_to_structured_items(tex: str) -> List[Dict[str, Any]]:
    """
    Parses clean LaTeX source into structured document elements for ReportLab PDF generation.
    Preserves document structure, headings, bold text, dates, project headings, and bullet items.
    """
    elements = []
    
    # Process only the document body
    doc_body = tex
    if r"\begin{document}" in doc_body:
        doc_body = doc_body.split(r"\begin{document}", 1)[1]
    if r"\end{document}" in doc_body:
        doc_body = doc_body.split(r"\end{document}", 1)[0]

    # Pre-process text: normalize linebreaks around critical LaTeX commands so macros don't collide
    normalized = doc_body.replace(r"\\", "\n")
    normalized = re.sub(r"(\\section\{[^}]+\})", r"\n\1\n", normalized)
    normalized = re.sub(r"(\\resumeProjectHeading)", r"\n\1", normalized)
    normalized = re.sub(r"(\\resumeSubheading)", r"\n\1", normalized)
    normalized = re.sub(r"(\\resumeItem)", r"\n\1", normalized)
    normalized = re.sub(r"(\\begin\{center\})", r"\n\1\n", normalized)
    normalized = re.sub(r"(\\end\{center\})", r"\n\1\n", normalized)

    lines = [l.strip() for l in normalized.split("\n") if l.strip()]
    i = 0
    while i < len(lines):
        line_s = lines[i].strip()
        if not line_s:
            i += 1
            continue

        # Header / Name
        if (r"\Huge" in line_s or r"\huge" in line_s or r"\scshape" in line_s) and r"\textbf{" in line_s:
            name_m = re.search(r'\\textbf\{([^}]+)\}', line_s)
            if name_m:
                elements.append({"type": "name", "text": _clean_latex_inline(name_m.group(1))})
                i += 1
                continue

        # Contact line
        if r"\small" in line_s or ("$|$" in line_s and ("@" in line_s or "linkedin" in line_s or "github" in line_s)):
            clean_contact = _clean_latex_inline(line_s)
            if clean_contact:
                elements.append({"type": "contact", "text": clean_contact})
                i += 1
                continue

        # Section
        sec_m = re.search(r'\\section\{([^}]+)\}', line_s)
        if sec_m:
            elements.append({"type": "section", "text": _clean_latex_inline(sec_m.group(1))})
            i += 1
            continue

        # Layout structural command filtering
        if any(line_s.startswith(cmd) for cmd in [
            r"\vspace", r"\resumeItemListStart", r"\resumeItemListEnd",
            r"\resumeSubHeadingListStart", r"\resumeSubHeadingListEnd",
            r"\begin{itemize}", r"\end{itemize}"
        ]):
            i += 1
            continue

        # Project Heading (can span across consecutive lines)
        if r"\resumeProjectHeading" in line_s:
            combined = line_s
            j = i + 1
            idx_start = combined.find(r"\resumeProjectHeading") + len(r"\resumeProjectHeading")
            args, _ = _extract_braced_arguments(combined, idx_start, count=2)
            while len(args) < 2 and j < len(lines) and j < i + 5:
                combined += " " + lines[j].strip()
                j += 1
                args, _ = _extract_braced_arguments(combined, idx_start, count=2)
            if args:
                title_tech = _clean_latex_inline(args[0])
                dates = _clean_latex_inline(args[1]) if len(args) > 1 else ""
                elements.append({
                    "type": "project_heading",
                    "text": title_tech,
                    "dates": dates
                })
            i = j
            continue

        # Subheading (Role/Degree & Company/School) (can span across consecutive lines)
        if r"\resumeSubheading" in line_s:
            combined = line_s
            j = i + 1
            idx_start = combined.find(r"\resumeSubheading") + len(r"\resumeSubheading")
            args, _ = _extract_braced_arguments(combined, idx_start, count=4)
            while len(args) < 4 and j < len(lines) and j < i + 6:
                combined += " " + lines[j].strip()
                j += 1
                args, _ = _extract_braced_arguments(combined, idx_start, count=4)
            if len(args) >= 2:
                elements.append({
                    "type": "subheading",
                    "left1": _clean_latex_inline(args[0]),
                    "right1": _clean_latex_inline(args[1]) if len(args) > 1 else "",
                    "left2": _clean_latex_inline(args[2]) if len(args) > 2 else "",
                    "right2": _clean_latex_inline(args[3]) if len(args) > 3 else ""
                })
            i = j
            continue

        # Bullet Item
        if r"\resumeItem" in line_s or line_s.startswith(r"\item"):
            combined = line_s
            j = i + 1
            if r"\resumeItem" in line_s:
                idx_start = combined.find(r"\resumeItem") + len(r"\resumeItem")
                args, _ = _extract_braced_arguments(combined, idx_start, count=1)
                while not args and j < len(lines) and j < i + 6:
                    combined += " " + lines[j].strip()
                    j += 1
                    args, _ = _extract_braced_arguments(combined, idx_start, count=1)
                b_text = args[0] if args else combined
            else:
                b_text = line_s.replace(r"\item", "").strip()

            clean_b = _clean_latex_inline(b_text)
            if clean_b:
                # If bullet is formatted as a skill category (e.g. \textbf{Languages}: Python, Java)
                if ":" in clean_b and any(k in clean_b.lower() for k in ["languages:", "backend:", "frontend:", "database", "cloud", "tools:", "core cs:", "ai engineering:"]):
                    elements.append({"type": "skill_category", "text": clean_b})
                else:
                    elements.append({"type": "bullet", "text": clean_b})
            i = j
            continue

        # Skills line (e.g. \textbf{Languages}: Python, Java \\ or General: ...)
        if (r"\textbf{" in line_s and ":" in line_s) or line_s.lower().startswith("general:") or (":" in line_s and any(c in line_s.lower() for c in ["skills", "languages", "backend", "frameworks", "tools", "databases"])):
            clean_sk = _clean_latex_inline(line_s)
            if clean_sk:
                elements.append({"type": "skill_category", "text": clean_sk})
            i += 1
            continue

        # Generic bold subheading fallback (e.g. \textbf{Stanford University} -- BS Computer Science)
        if line_s.startswith(r"\textbf{") and ("--" in line_s or "-" in line_s or "|" in line_s):
            clean_sub = _clean_latex_inline(line_s)
            parts = [p.strip() for p in re.split(r'--|-|\|', clean_sub, maxsplit=1)]
            elements.append({
                "type": "subheading",
                "left1": parts[0] if parts else clean_sub,
                "right1": parts[1] if len(parts) > 1 else "",
                "left2": "",
                "right2": ""
            })
            i += 1
            continue

        i += 1

    return elements


def render_reportlab_ats_pdf(tex_content: str, output_filepath: str) -> str:
    """
    Renders high-quality ATS-styled PDF directly from LaTeX structure using ReportLab.
    Ensures single-column layout, clear dividers, proper margins, and readable text.
    """
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    c = canvas.Canvas(output_filepath, pagesize=letter)
    width, height = letter

    margin_x = 38
    content_width = width - (margin_x * 2)
    y = height - 36

    elements = _strip_latex_to_structured_items(tex_content)

    for el in elements:
        el_type = el.get("type")

        if el_type == "name":
            c.setFont("Helvetica-Bold", 17)
            name_text = el.get("text", "")
            c.drawCentredString(width / 2.0, y, name_text)
            y -= 13

        elif el_type == "contact":
            c.setFont("Helvetica", 8.8)
            contact_text = el.get("text", "")
            c.drawCentredString(width / 2.0, y, contact_text)
            y -= 14

        elif el_type == "section":
            y -= 6
            if y < 55:
                c.showPage()
                y = height - 36
            c.setFont("Helvetica-Bold", 10.5)
            c.drawString(margin_x, y, el.get("text", "").upper())
            y -= 2.5
            c.setStrokeColorRGB(0.25, 0.25, 0.25)
            c.setLineWidth(0.8)
            c.line(margin_x, y, width - margin_x, y)
            y -= 9.5

        elif el_type == "subheading":
            y -= 1.5
            if y < 45:
                c.showPage()
                y = height - 36
            
            # Row 1: Company / School (Bold 9.8pt) & Location / Right 1 (9.5pt)
            l1 = el.get("left1", "")
            r1 = el.get("right1", "")
            l2 = el.get("left2", "")
            r2 = el.get("right2", "")

            # Render row 1
            c.setFont("Helvetica-Bold", 9.8)
            c.drawString(margin_x, y, l1)
            if r1:
                c.setFont("Helvetica", 9.2)
                c.drawRightString(width - margin_x, y, r1)
            y -= 10.5

            # Render row 2 if present: Role / Degree (Italic 9.2pt) & Dates (9pt)
            if l2 or r2:
                c.setFont("Helvetica-Oblique", 9.2)
                c.drawString(margin_x, y, l2)
                if r2:
                    c.setFont("Helvetica", 9)
                    c.drawRightString(width - margin_x, y, r2)
                y -= 11

        elif el_type == "project_heading":
            y -= 1.5
            if y < 45:
                c.showPage()
                y = height - 36
            c.setFont("Helvetica-Bold", 9.8)
            proj_text = el.get("text", "")
            dates_text = el.get("dates", "")
            if dates_text:
                c.setFont("Helvetica", 9.2)
                c.drawRightString(width - margin_x, y, dates_text)
                eff_width = content_width - c.stringWidth(dates_text, "Helvetica", 9.2) - 15
            else:
                eff_width = content_width
            wrapped = simpleSplit(proj_text, "Helvetica-Bold", 9.8, eff_width)
            for w in wrapped:
                c.drawString(margin_x, y, w)
                y -= 10.5

        elif el_type == "bullet":
            if y < 40:
                c.showPage()
                y = height - 36
            c.setFont("Helvetica", 9)
            bullet_char = "• "
            c.drawString(margin_x + 5, y, bullet_char)
            wrapped_lines = simpleSplit(el.get("text", ""), "Helvetica", 9, content_width - 16)
            for idx, wl in enumerate(wrapped_lines):
                c.drawString(margin_x + 15, y, wl)
                y -= 10.5
                if y < 40:
                    c.showPage()
                    y = height - 36

        elif el_type == "skill_category":
            if y < 40:
                c.showPage()
                y = height - 36
            raw_sk = el.get("text", "")
            # If line has category prefix e.g. "Languages: Python, Java"
            if ":" in raw_sk:
                cat_label, rest = raw_sk.split(":", 1)
                cat_label = cat_label.strip() + ": "
                c.setFont("Helvetica-Bold", 9)
                label_width = c.stringWidth(cat_label, "Helvetica-Bold", 9)
                c.drawString(margin_x, y, cat_label)
                
                c.setFont("Helvetica", 9)
                wrapped = simpleSplit(rest.strip(), "Helvetica", 9, content_width - label_width)
                for idx, w in enumerate(wrapped):
                    if idx == 0:
                        c.drawString(margin_x + label_width, y, w)
                    else:
                        y -= 10.5
                        c.drawString(margin_x + label_width, y, w)
                y -= 11
            else:
                c.setFont("Helvetica", 9)
                wrapped = simpleSplit(raw_sk, "Helvetica", 9, content_width)
                for w in wrapped:
                    c.drawString(margin_x, y, w)
                    y -= 10.5

    c.save()
    return output_filepath


def compile_latex_securely(
    tex_content: str,
    output_pdf_path: str,
    timeout_seconds: int = 25
) -> Tuple[bool, str]:
    """
    Compiles LaTeX in an isolated sandbox with shell escape disabled (-no-shell-escape).
    Falls back gracefully to ReportLab ATS compiler if pdflatex is not present.
    Returns (success: bool, message: str).
    """
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    pdflatex_bin = shutil.which("pdflatex")

    if pdflatex_bin:
        with tempfile.TemporaryDirectory() as temp_dir:
            tex_file = os.path.join(temp_dir, "resume.tex")
            with open(tex_file, "w", encoding="utf-8") as f:
                f.write(tex_content)

            cmd = [
                pdflatex_bin,
                "-no-shell-escape",
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-output-directory", temp_dir,
                tex_file
            ]

            try:
                # Run 2 passes to resolve hyperref references
                for pass_num in range(2):
                    res = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=timeout_seconds,
                        check=False
                    )

                temp_pdf = os.path.join(temp_dir, "resume.pdf")
                if os.path.exists(temp_pdf) and os.path.getsize(temp_pdf) > 1000:
                    shutil.copy2(temp_pdf, output_pdf_path)
                    return True, "Compiled successfully with pdflatex."
                else:
                    logger.warning(f"pdflatex pass produced no PDF or empty file. Log: {res.stdout[-400:]}")
            except subprocess.TimeoutExpired:
                logger.warning(f"pdflatex timed out after {timeout_seconds}s. Falling back to ReportLab engine.")
            except Exception as e:
                logger.warning(f"pdflatex compilation error: {e}. Falling back to ReportLab engine.")

    # High-fidelity fallback
    try:
        render_reportlab_ats_pdf(tex_content, output_pdf_path)
        return True, "Compiled successfully with ReportLab ATS Engine."
    except Exception as e:
        logger.error(f"ReportLab PDF generation error: {e}", exc_info=True)
        return False, f"PDF compilation failed: {e}"


def extract_and_validate_pdf_readability(pdf_path: str) -> Dict[str, Any]:
    """
    Extracts text from the compiled PDF and validates machine readability.
    Checks that headings, bullets, and contact info remain parseable.
    """
    if not os.path.exists(pdf_path):
        return {
            "is_readable": False,
            "error": "PDF file does not exist",
            "word_count": 0,
            "character_count": 0,
            "detected_sections": [],
            "validation_status": "failed"
        }

    try:
        from pdfminer.high_level import extract_text
        text = extract_text(pdf_path)
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {e}")
        return {
            "is_readable": False,
            "error": str(e),
            "word_count": 0,
            "character_count": 0,
            "detected_sections": [],
            "validation_status": "failed"
        }

    words = [w for w in text.split() if w.strip()]
    word_count = len(words)
    char_count = len(text)

    # Detect common resume section headings in extracted text
    known_sections = [
        "EDUCATION", "EXPERIENCE", "PROJECTS", "SKILLS", "TECHNICAL SKILLS",
        "ACHIEVEMENTS", "CERTIFICATIONS", "LEADERSHIP", "COURSEWORK", "PUBLICATIONS"
    ]
    detected_sections = []
    text_upper = text.upper()
    for s in known_sections:
        if s in text_upper:
            detected_sections.append(s)

    has_email = "@" in text
    is_readable = word_count >= 20 and (len(detected_sections) >= 1 or has_email)

    return {
        "is_readable": is_readable,
        "word_count": word_count,
        "character_count": char_count,
        "detected_sections": detected_sections,
        "has_contact_info": has_email,
        "sample_preview": text[:400].strip(),
        "validation_status": "passed" if is_readable else "warning"
    }


def create_source_archive(
    tex_content: str,
    output_zip_path: str,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Creates a downloadable .zip source archive containing resume.tex, README.md,
    and structured metadata for manual compilation on Overleaf or local TeX engines.
    """
    os.makedirs(os.path.dirname(output_zip_path), exist_ok=True)
    
    readme_content = """# Tailored LaTeX Resume Package
Generated by Interview AutoApply

## Contents:
- `resume.tex`: Complete modular LaTeX resume source.
- `metadata.json`: Job alignment details, targeted role, and assembly plan settings.

## How to Compile:
1. **Online (Recommended):** Upload this `.zip` directly to [Overleaf](https://www.overleaf.com) and click **Recompile**.
2. **Local TeX Live / MacTeX:**
   ```bash
   pdflatex -interaction=nonstopmode resume.tex
   ```
"""

    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("resume.tex", tex_content)
        zf.writestr("README.md", readme_content)
        if metadata:
            zf.writestr("metadata.json", json.dumps(metadata, indent=2))

    return output_zip_path
