import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

def export_text_to_pdf(text_content: str, filename: str, output_dir: str = "/tmp") -> str:
    """
    Exports a simple markdown/text string to a PDF file.
    In a production system, a more robust HTML-to-PDF converter (like weasyprint) is preferred.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    filepath = os.path.join(output_dir, filename)
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    
    y = height - 50
    lines = text_content.split('\n')
    
    c.setFont("Helvetica", 11)
    
    for line in lines:
        if not line.strip():
            y -= 15
            continue
            
        # Handle simple bold formatting for markdown
        if line.startswith("#"):
            c.setFont("Helvetica-Bold", 14)
            line = line.replace("#", "").strip()
        elif line.startswith("-"):
            c.setFont("Helvetica", 11)
            line = "  " + line
        else:
            c.setFont("Helvetica", 11)

        wrapped_lines = simpleSplit(line, "Helvetica", 11, width - 100)
        for wl in wrapped_lines:
            c.drawString(50, y, wl)
            y -= 15
            if y < 50:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 11)
                
    c.save()
    return filepath
