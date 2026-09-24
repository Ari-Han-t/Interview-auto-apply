import os
import re
import html
import subprocess
import tempfile
import shutil
import logging
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

logger = logging.getLogger(__name__)

def _strip_latex_to_text(tex: str) -> str:
    """
    Converts LaTeX resume source into clean readable text for fallback PDF export.
    """
    text = tex
    # Strip comments
    text = re.sub(r'%.*?\n', '\n', text)
    # Remove preamble up to \begin{document}
    if r'\begin{document}' in text:
        text = text.split(r'\begin{document}', 1)[1]
    if r'\end{document}' in text:
        text = text.split(r'\end{document}', 1)[0]
        
    # Convert section headings
    text = re.sub(r'\\section\*?\{([^}]+)\}', r'\n\n# \1\n', text)
    text = re.sub(r'\\subsection\*?\{([^}]+)\}', r'\n## \1\n', text)
    
    # Convert formatting
    text = re.sub(r'\\textbf\{([^}]+)\}', r'**\1**', text)
    text = re.sub(r'\\textit\{([^}]+)\}', r'*\1*', text)
    text = re.sub(r'\\href\{([^}]+)\}\{([^}]+)\}', r'\2 (\1)', text)
    text = re.sub(r'\\url\{([^}]+)\}', r'\1', text)
    text = re.sub(r'\\item\s*', r'- ', text)
    
    # Clean commands
    text = re.sub(r'\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})*', ' ', text)
    text = text.replace('{', '').replace('}', '').replace(r'\\', '\n').replace(r'\&', '&').replace(r'\%', '%').replace(r'\$', '$')
    
    # Clean up whitespace
    lines = [line.strip() for line in text.split('\n')]
    cleaned_lines = []
    for l in lines:
        if l:
            cleaned_lines.append(l)
        elif cleaned_lines and cleaned_lines[-1] != "":
            cleaned_lines.append("")
            
    return '\n'.join(cleaned_lines)

def export_text_to_pdf(text_content: str, filename: str, output_dir: str = "data/exports") -> str:
    """
    Exports a clean markdown/text string to a styled PDF file.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        
    filepath = os.path.join(output_dir, filename)
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    
    y = height - 50
    lines = text_content.split('\n')
    
    c.setFont("Helvetica", 10)
    
    for line in lines:
        if not line.strip():
            y -= 12
            continue
            
        if line.startswith("# "):
            y -= 6
            c.setFont("Helvetica-Bold", 13)
            heading = line.replace("# ", "").strip()
            c.drawString(50, y, heading)
            y -= 4
            c.setStrokeColorRGB(0.7, 0.7, 0.7)
            c.setLineWidth(0.5)
            c.line(50, y, width - 50, y)
            y -= 14
            c.setFont("Helvetica", 10)
            continue
        elif line.startswith("## "):
            c.setFont("Helvetica-Bold", 11)
            line = line.replace("## ", "").strip()
        elif line.startswith("- "):
            c.setFont("Helvetica", 10)
            line = "  • " + line[2:]
        else:
            c.setFont("Helvetica", 10)

        wrapped_lines = simpleSplit(line, "Helvetica", 10, width - 100)
        for wl in wrapped_lines:
            c.drawString(50, y, wl)
            y -= 14
            if y < 50:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 10)
                
    c.save()
    return filepath

def compile_latex_to_pdf(tex_content: str, output_filename: str, output_dir: str = "data/exports") -> str:
    """
    Compiles a LaTeX string to a PDF file using pdflatex if available,
    or smoothly falls back to reportlab PDF generation.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        
    final_pdf_path = os.path.join(output_dir, output_filename)
    
    if shutil.which("pdflatex"):
        with tempfile.TemporaryDirectory() as temp_dir:
            tex_file_path = os.path.join(temp_dir, "resume.tex")
            with open(tex_file_path, "w", encoding="utf-8") as f:
                f.write(tex_content)
                
            try:
                for _ in range(2):
                    subprocess.run(
                        ["pdflatex", "-interaction=nonstopmode", "-output-directory", temp_dir, tex_file_path],
                        capture_output=True,
                        text=True,
                        timeout=30,
                        check=False
                    )
                    
                pdf_file_path = os.path.join(temp_dir, "resume.pdf")
                if os.path.exists(pdf_file_path):
                    shutil.copy2(pdf_file_path, final_pdf_path)
                    return final_pdf_path
            except Exception as e:
                logger.warning(f"pdflatex compilation failed, using fallback: {e}")
                
    # Fallback to high-quality formatted PDF via ReportLab
    clean_text = _strip_latex_to_text(tex_content)
    return export_text_to_pdf(clean_text, output_filename, output_dir)

