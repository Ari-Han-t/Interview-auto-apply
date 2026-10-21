import re

LATEX_SPECIAL_CHARS = {
    '&': r'\&',
    '%': r'\%',
    '$': r'\$',
    '#': r'\#',
    '_': r'\_',
    '{': r'\{',
    '}': r'\}',
    '~': r'\textasciitilde{}',
    '^': r'\textasciicircum{}',
    '<': r'\textless{}',
    '>': r'\textgreater{}',
}

# Dangerous LaTeX commands to disallow in user inputs to prevent shell injection or arbitrary read/write
DANGEROUS_COMMANDS = [
    r'\write18',
    r'\immediate',
    r'\input',
    r'\include',
    r'\openin',
    r'\openout',
    r'\newwrite',
    r'\read',
    r'\catcode',
    r'\csname',
    r'\def',
    r'\let',
    r'\futurelet',
]

def escape_latex(text: str) -> str:
    """
    Safely escapes special LaTeX characters in user-provided content.
    Prevents injection and compilation errors while preserving normal readable text.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # Normalize newlines and whitespace
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Neutralize dangerous primitives first
    for cmd in DANGEROUS_COMMANDS:
        text = text.replace(cmd, cmd.replace('\\', ''))

    # Escape backslash first to prevent double-escaping
    text = text.replace('\\', r'\textbackslash{}')

    # Replace special characters using dictionary
    for char, replacement in LATEX_SPECIAL_CHARS.items():
        text = text.replace(char, replacement)

    # Normalize unicode hyphens, dashes, spaces, and quotes
    text = text.replace('\u2011', '-')
    text = text.replace('\u2013', '--')
    text = text.replace('\u2014', '---')
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u201c', "``").replace('\u201d', "''")
    text = text.replace('\u2022', '')
    text = text.replace('\u2026', r'\dots{}')
    text = text.replace('\u00a0', ' ')

    # Clean double quotes
    text = text.replace('"', "''")

    # Sanitize URLs or repeated protocols
    text = text.replace("http://http://", "http://").replace("https://https://", "https://")
    
    return text.strip()


def format_latex_link(url: str, label: str) -> str:
    """
    Creates a clickable href in LaTeX if url is valid, else returns label.
    Escapes label and sanitizes URL characters.
    """
    if not url:
        return escape_latex(label)
    clean_url = url.strip()
    if not (clean_url.startswith("http://") or clean_url.startswith("https://") or clean_url.startswith("mailto:")):
        clean_url = f"https://{clean_url}"
    clean_label = escape_latex(label)
    # in href URL parameter, percent and hash need careful handling
    safe_url = clean_url.replace('\\', '').replace('"', '')
    return f"\\href{{{safe_url}}}{{{clean_label}}}"


format_latex_url = format_latex_link
