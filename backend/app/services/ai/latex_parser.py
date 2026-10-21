import os
import re
import zipfile
import shutil
import tempfile
from typing import Dict, List, Any, Optional, Tuple


def strip_latex_formatting(text: str) -> str:
    """
    Cleans LaTeX commands, braces, and escape sequences to return clean, readable plain text.
    """
    if not text:
        return ""

    # Replace escaped characters
    s = text.replace(r"\%", "%").replace(r"\&", "&").replace(r"\$", "$").replace(r"\_", "_")
    s = s.replace(r"\#", "#").replace(r"\{", "{").replace(r"\}", "}")
    s = s.replace(r"\~", "~").replace(r"\^", "^")

    # Replace \href{url}{text} -> text (or text if url is similar)
    s = re.sub(r'\\href\{([^}]+)\}\{([^}]+)\}', r'\2', s)
    s = re.sub(r'\\url\{([^}]+)\}', r'\1', s)

    # Strip icon commands like \faGithub, \faLinkedin, \faEnvelope
    s = re.sub(r'\\fa[A-Za-z0-9]+', '', s)

    # Strip styling commands \textbf{...}, \textit{...}, \text{...}, \scshape, etc.
    s = re.sub(r'\\(?:textbf|textit|textbf|textsc|emph|text|underline|color\{[^}]+\}|scshape)\s*\{([^}]*)\}', r'\1', s)
    s = re.sub(r'\\(?:textbf|textit|textsc|emph|scshape|large|Large|Huge|small|footnotesize|normalfont)\b', '', s)

    # Remove spacing and horizontal lines
    s = re.sub(r'\\(?:vspace|hspace)\*?\{[^}]+\}', ' ', s)
    s = re.sub(r'\\(?:titlerule|hrule|hfill|quad|qquad|break|newline)\b', ' ', s)
    s = s.replace(r"\\", "\n")

    # Clean leftover LaTeX commands like \cmd or \cmd{arg}
    s = re.sub(r'\\[a-zA-Z]+(?:\*|\b)(?:\{[^}]*\})?', ' ', s)

    # Clean leftover braces
    s = s.replace("{", "").replace("}", "")

    # Clean pipe separators and extra whitespace
    s = re.sub(r'[ \t]+', ' ', s)
    s = re.sub(r'\n\s*\n+', '\n', s)
    return s.strip()


def extract_braced_arguments(text: str, start_pos: int = 0) -> List[str]:
    """
    Extracts consecutive {arg} blocks starting from start_pos.
    Handles nested braces properly.
    """
    args = []
    i = start_pos
    n = len(text)

    while i < n:
        # Skip whitespace
        while i < n and text[i].isspace():
            i += 1
        if i >= n or text[i] != '{':
            break

        # Found open brace
        brace_count = 1
        arg_chars = []
        i += 1
        while i < n and brace_count > 0:
            char = text[i]
            if char == '{' and (i == 0 or text[i - 1] != '\\'):
                brace_count += 1
                arg_chars.append(char)
            elif char == '}' and (i == 0 or text[i - 1] != '\\'):
                brace_count -= 1
                if brace_count > 0:
                    arg_chars.append(char)
            else:
                arg_chars.append(char)
            i += 1

        args.append("".join(arg_chars).strip())

    return args


class LatexResumeParser:
    """
    Comprehensive LaTeX parser for academic, engineering, and industry resumes.
    Recognizes custom macros (e.g. Jake's resume, Overleaf templates, moderncv),
    extracts structured candidate profile data, and flags uncertain or unparsed structures.
    """

    KNOWN_RESUME_MACROS = {
        r"\resumeItem",
        r"\resumeSubheading",
        r"\resumeProjectHeading",
        r"\resumeSubSubheading",
        r"\resumeSubHeadingListStart",
        r"\resumeSubHeadingListEnd",
        r"\resumeItemListStart",
        r"\resumeItemListEnd",
        r"\section",
        r"\href",
        r"\url",
        r"\textbf",
        r"\textit",
        r"\item",
    }

    def __init__(self, latex_text: Optional[str] = None):
        self.flags: List[Dict[str, str]] = []
        self.custom_macros: Dict[str, Dict[str, Any]] = {}
        self.recognized_macros: List[str] = []
        self.unparsed_macros: List[str] = []
        self.latex_text: Optional[str] = latex_text

    def parse(self, latex_text: Optional[str] = None) -> Dict[str, Any]:
        """Convenience method forwarding to parse_full_latex."""
        target = latex_text if latex_text is not None else (self.latex_text or "")
        return self.parse_full_latex(target)

    def strip_comments(self, latex_text: str) -> str:
        """Strips LaTeX comments while preserving escaped %."""
        lines = []
        for line in latex_text.splitlines():
            # Match comment symbol % not preceded by backslash
            cleaned = re.sub(r'(?<!\\)%.*$', '', line)
            lines.append(cleaned)
        return "\n".join(lines)

    def extract_custom_macros(self, latex_text: str):
        """Extracts \\newcommand, \\renewcommand, and \\def declarations."""
        # \newcommand{\name}[args]{definition}
        pattern = re.compile(r'\\(?:re)?newcommand\*?\s*\{\\([a-zA-Z0-9]+)\}(?:\[(\d+)\])?')
        for match in pattern.finditer(latex_text):
            cmd_name = match.group(1)
            num_args = int(match.group(2)) if match.group(2) else 0
            end_match = match.end()
            braced = extract_braced_arguments(latex_text, end_match)
            body = braced[0] if braced else ""
            self.custom_macros[f"\\{cmd_name}"] = {
                "name": cmd_name,
                "args": num_args,
                "body": body
            }

        # \def\name{definition}
        def_pattern = re.compile(r'\\def\s*\\([a-zA-Z0-9]+)')
        for match in def_pattern.finditer(latex_text):
            cmd_name = match.group(1)
            end_match = match.end()
            braced = extract_braced_arguments(latex_text, end_match)
            body = braced[0] if braced else ""
            self.custom_macros[f"\\{cmd_name}"] = {
                "name": cmd_name,
                "args": 0,
                "body": body
            }

    def parse_header_contact_info(self, text: str) -> Dict[str, Any]:
        """Extracts candidate contact details, links, and personal information."""
        contact = {
            "full_name": None,
            "email": None,
            "phone": None,
            "github": None,
            "linkedin": None,
            "portfolio": None,
            "current_location": None,
        }

        # Look in document header between \begin{document} and first \section
        doc_start = re.search(r'\\begin\{document\}', text)
        search_start = doc_start.end() if doc_start else 0
        first_section = re.search(r'\\section\*?\{', text[search_start:])
        header_text = text[search_start : search_start + first_section.start()] if first_section else text[search_start : search_start + 1500]

        # Extract name: Look for \Huge \scshape Name or \textbf{\Huge Name} or \textbf{Name}
        name_patterns = [
            r'\\textbf\{(?:\\[Hh]uge|\\LARGE|\\Large)?\s*(?:\\scshape)?\s*([^}]+)\}',
            r'(?:\\[Hh]uge|\\LARGE|\\Large)\s*(?:\\scshape)?\s*\\textbf\{([^}]+)\}',
            r'\\textbf\{([A-Za-z\s.\'-]{2,40})\}',
            r'(?:\\[Hh]uge|\\LARGE|\\Large)\s*(?:\\scshape)?\s*([A-Za-z\s.\'-]{2,40})\\\\',
            r'(?:\\[Hh]uge|\\LARGE|\\Large)\s*(?:\\scshape)?\s*([A-Za-z\s.\'-]{2,40})\n',
            r'\\title\{([^}]+)\}',
            r'\\author\{([^}]+)\}',
            r'\\name\{([^}]+)\}',
        ]
        for p in name_patterns:
            for m in re.finditer(p, header_text):
                raw_name = strip_latex_formatting(m.group(1)).strip()
                if raw_name and len(raw_name) > 2 and len(raw_name) < 50:
                    if not any(k in raw_name.lower() for k in ["begin", "documentclass", "section", "resume", "item"]) and '#' not in raw_name:
                        contact["full_name"] = raw_name
                        break
            if contact["full_name"]:
                break

        # Fallback to comment header "Author : Name"
        if not contact["full_name"]:
            author_m = re.search(r'Author\s*:\s*([A-Za-z\s.\'-]{2,40})', text[:500], re.IGNORECASE)
            if author_m:
                contact["full_name"] = author_m.group(1).strip()

        # Extract email
        email_m = re.search(r'\\href\{mailto:([^}]+)\}', header_text)
        if email_m:
            contact["email"] = email_m.group(1).strip()
        else:
            email_plain = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', header_text)
            if email_plain:
                contact["email"] = email_plain.group(0).strip()

        # Extract phone
        phone_m = re.search(r'(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4}', header_text)
        if phone_m:
            contact["phone"] = phone_m.group(0).strip()

        # Extract links via \href or plain URLs
        href_matches = re.findall(r'\\href\{([^}]+)\}\{([^}]+)\}', header_text)
        for url, anchor in href_matches:
            url_clean = url.strip()
            anchor_clean = anchor.strip()

            combined = f"{url_clean} {anchor_clean}".lower()
            if "github.com" in combined:
                # normalize github url
                gh_user = re.search(r'github\.com/([A-Za-z0-9_.-]+)', combined)
                contact["github"] = f"https://github.com/{gh_user.group(1)}" if gh_user else url_clean
            elif "linkedin.com" in combined:
                li_user = re.search(r'linkedin\.com/in/([A-Za-z0-9_.-]+)', combined)
                contact["linkedin"] = f"https://linkedin.com/in/{li_user.group(1)}" if li_user else url_clean
            elif not contact["portfolio"] and not url_clean.startswith("mailto:"):
                contact["portfolio"] = url_clean if url_clean.startswith("http") else f"https://{url_clean}"

        # Search for github and linkedin plain text if not yet found
        if not contact["github"]:
            gh_m = re.search(r'github\.com/([A-Za-z0-9_.-]+)', header_text)
            if gh_m:
                contact["github"] = f"https://github.com/{gh_m.group(1)}"

        if not contact["linkedin"]:
            li_m = re.search(r'linkedin\.com/in/([A-Za-z0-9_.-]+)', header_text)
            if li_m:
                contact["linkedin"] = f"https://linkedin.com/in/{li_m.group(1)}"

        return contact

    def extract_sections(self, latex_text: str) -> Dict[str, str]:
        """Segments document into labeled section blocks."""
        sections = {}
        # Find all \section{Title}
        pattern = re.compile(r'\\section\*?\{([^}]+)\}')
        matches = list(pattern.finditer(latex_text))

        for idx, match in enumerate(matches):
            title = strip_latex_formatting(match.group(1)).strip().upper()
            start_pos = match.end()
            end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(latex_text)
            section_body = latex_text[start_pos:end_pos].strip()
            sections[title] = section_body

        return sections

    def parse_education_section(self, section_text: str) -> List[Dict[str, Any]]:
        """Parses education degrees, institutions, GPA, and coursework."""
        educations = []

        # Look for \resumeSubheading{Inst}{Location}{Degree}{Dates}
        subheading_pattern = re.compile(r'\\resumeSubheading\b')
        matches = list(subheading_pattern.finditer(section_text))

        for idx, match in enumerate(matches):
            args = extract_braced_arguments(section_text, match.end())
            if len(args) >= 4:
                inst = strip_latex_formatting(args[0])
                location = strip_latex_formatting(args[1])
                degree_spec = strip_latex_formatting(args[2])
                dates = strip_latex_formatting(args[3])

                # Extract degree, specialization, and CGPA from degree_spec
                degree = None
                specialization = None
                cgpa = None

                # CGPA regex
                cgpa_m = re.search(r'(?:CGPA|GPA)\s*:\s*([\d.]+)(?:/[\d.]+)?', degree_spec, re.IGNORECASE)
                if cgpa_m:
                    try:
                        cgpa = float(cgpa_m.group(1))
                    except ValueError:
                        pass

                # Degree and Specialization
                spec_clean = re.sub(r';?\s*(?:CGPA|GPA)\s*:\s*[\d.]+(?:/[\d.]+)?', '', degree_spec, flags=re.IGNORECASE).strip()
                if " in " in spec_clean:
                    parts = spec_clean.split(" in ", 1)
                    degree = parts[0].strip()
                    specialization = parts[1].strip()
                elif " - " in spec_clean:
                    parts = spec_clean.split(" - ", 1)
                    degree = parts[0].strip()
                    specialization = parts[1].strip()
                else:
                    degree = spec_clean

                # Graduation year from dates (e.g. "2024 -- 2028" -> 2028)
                grad_year = None
                years = re.findall(r'\b(20\d{2}|19\d{2})\b', dates)
                if years:
                    grad_year = int(years[-1])

                # Check for coursework in next lines before the next subheading
                end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(section_text)
                sub_body = section_text[match.end():end_pos]
                coursework = []

                course_m = re.search(r'(?:Coursework|Courses)\s*:\s*\}?\s*([^\n]+)', sub_body, re.IGNORECASE)
                if course_m:
                    raw_courses = strip_latex_formatting(course_m.group(1))
                    # Remove trailing braces or linebreaks
                    raw_courses = re.sub(r'[\}\\]+$', '', raw_courses).strip()
                    coursework = [c.strip() for c in re.split(r'[,|;]', raw_courses) if c.strip()]

                educations.append({
                    "institution": inst,
                    "location": location,
                    "degree": degree,
                    "specialization": specialization,
                    "cgpa": cgpa,
                    "graduation_year": grad_year,
                    "dates": dates,
                    "coursework": coursework
                })
            else:
                self.flags.append({
                    "category": "macro",
                    "field": "education",
                    "message": f"\\resumeSubheading had fewer than 4 arguments ({len(args)} found).",
                    "severity": "warning"
                })

        # Fallback if no \resumeSubheading found: parse itemized or plain blocks
        if not educations and section_text.strip():
            plain = strip_latex_formatting(section_text)
            lines = [l.strip() for l in plain.splitlines() if l.strip()]
            inst = lines[0] if lines else "University"
            years = re.findall(r'\b(20\d{2}|19\d{2})\b', plain)
            grad_year = int(years[-1]) if years else None
            cgpa_m = re.search(r'(?:CGPA|GPA)\s*:\s*([\d.]+)', plain, re.IGNORECASE)
            cgpa = float(cgpa_m.group(1)) if cgpa_m else None

            educations.append({
                "institution": inst,
                "location": None,
                "degree": lines[1] if len(lines) > 1 else "Bachelors",
                "specialization": None,
                "cgpa": cgpa,
                "graduation_year": grad_year,
                "coursework": []
            })
            self.flags.append({
                "category": "section",
                "field": "education",
                "message": "Education parsed from unstructured text; please review degree and institution.",
                "severity": "info"
            })

        return educations

    def parse_experience_section(self, section_text: str) -> List[Dict[str, Any]]:
        """Parses professional work experiences and internships."""
        experiences = []
        subheading_pattern = re.compile(r'\\resumeSubheading\b')
        matches = list(subheading_pattern.finditer(section_text))

        for idx, match in enumerate(matches):
            args = extract_braced_arguments(section_text, match.end())
            if len(args) >= 3:
                # Typically: {Title or Company}{Location or Dates}{Company or Title}{Dates or Location}
                arg1 = strip_latex_formatting(args[0])
                arg2 = strip_latex_formatting(args[1]) if len(args) > 1 else ""
                arg3 = strip_latex_formatting(args[2]) if len(args) > 2 else ""
                arg4 = strip_latex_formatting(args[3]) if len(args) > 3 else ""

                # Infer title vs company
                title, company, location, dates = self._infer_role_and_company(arg1, arg2, arg3, arg4)

                # Extract bullet items between this subheading and the next
                end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(section_text)
                sub_body = section_text[match.end():end_pos]
                bullets = self._extract_bullet_items(sub_body)

                is_internship = any(
                    "intern" in (x or "").lower()
                    for x in [title, company, " ".join(bullets)]
                )

                # Parse start / end dates
                start_date, end_date, currently_working = self._parse_date_range(dates)

                experiences.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "start_date": start_date,
                    "end_date": end_date,
                    "currently_working": currently_working,
                    "internship_or_fulltime": "internship" if is_internship else "fulltime",
                    "description": "\n".join(f"• {b}" for b in bullets) if bullets else None,
                    "highlights": bullets,
                    "technologies": []
                })

        # Fallback for standard LaTeX experience blocks without \resumeSubheading
        if not experiences and section_text.strip():
            bullets = self._extract_bullet_items(section_text)
            
            # Split before itemize to get heading lines
            heading_text = section_text.split(r"\begin{itemize}")[0] if r"\begin{itemize}" in section_text else section_text
            lines = [l.strip() for l in heading_text.splitlines() if l.strip()]
            
            part1, part2, part3, part4 = "", "", "", ""
            if lines:
                parts_l1 = [p.strip() for p in re.split(r'\\hfill|\\\\|\|', lines[0]) if p.strip()]
                part1 = strip_latex_formatting(parts_l1[0]) if parts_l1 else ""
                part2 = strip_latex_formatting(parts_l1[1]) if len(parts_l1) > 1 else ""
            if len(lines) > 1:
                parts_l2 = [p.strip() for p in re.split(r'\\hfill|\\\\|\|', lines[1]) if p.strip()]
                part3 = strip_latex_formatting(parts_l2[0]) if parts_l2 else ""
                part4 = strip_latex_formatting(parts_l2[1]) if len(parts_l2) > 1 else ""

            title, company, location, dates = self._infer_role_and_company(part1, part2, part3, part4)
            if not company or company == title:
                if any(w in part1.lower() for w in ["engineer", "intern", "developer", "lead", "analyst", "manager"]):
                    title = part1
                    company = part3 or "Company"
                else:
                    company = part1
                    title = part3 or "Software Engineer"
            
            start_date, end_date, currently_working = self._parse_date_range(dates)
            is_internship = any("intern" in (x or "").lower() for x in [title, company, " ".join(bullets)])

            experiences.append({
                "title": title.strip() or "Software Engineer",
                "company": company.strip() or "Company",
                "location": location.strip() if location else None,
                "start_date": start_date,
                "end_date": end_date,
                "currently_working": currently_working,
                "internship_or_fulltime": "internship" if is_internship else "fulltime",
                "description": "\n".join(f"• {b}" for b in bullets) if bullets else None,
                "highlights": bullets,
                "technologies": []
            })

        return experiences

    def parse_projects_section(self, section_text: str) -> List[Dict[str, Any]]:
        """Parses projects, repository links, technologies, and bullet achievements."""
        projects = []

        # Split section into project items either by \resumeProjectHeading or by \item
        project_chunks = []
        if r"\resumeProjectHeading" in section_text:
            chunks = re.split(r'\\resumeProjectHeading\b', section_text)
            for c in chunks[1:]:
                project_chunks.append(("heading", c))
        else:
            # Split by top-level \item
            chunks = re.split(r'(?<!\\item)\s*\\item\b', section_text)
            for c in chunks[1:]:
                project_chunks.append(("item", c))

        for chunk_type, raw_chunk in project_chunks:
            # Extract links
            github_url = None
            live_url = None
            hrefs = re.findall(r'\\href\{([^}]+)\}\{([^}]+)\}', raw_chunk)
            for url, anchor in hrefs:
                if "github.com" in url.lower() or "github" in anchor.lower():
                    github_url = url.strip()
                elif not live_url and not url.startswith("mailto:"):
                    live_url = url.strip()

            # Extract name and technologies
            # Often: \textbf{Name} | \textit{Tech1, Tech2}
            # or in resumeProjectHeading: {\textbf{Name} $|$ \emph{Tech}}{Date}
            first_line = raw_chunk.split(r"\resumeItemListStart")[0] if r"\resumeItemListStart" in raw_chunk else raw_chunk.splitlines()[0]
            clean_first = strip_latex_formatting(first_line)

            # Name extraction
            name_m = re.search(r'\\textbf\{([^}]+)\}', first_line)
            proj_name = strip_latex_formatting(name_m.group(1)) if name_m else clean_first.split("|")[0].strip()
            # Clean up pipe decorations
            proj_name = re.sub(r'\s*\|\s*.*$', '', proj_name).strip()

            # Tech stack extraction: \textit{Python, FastAPI, ...}
            techs = []
            tech_m = re.search(r'\\(?:textit|emph)\{([^}]+)\}', first_line)
            if tech_m:
                tech_text = strip_latex_formatting(tech_m.group(1))
                techs = [t.strip() for t in re.split(r'[,|;]', tech_text) if t.strip()]

            # Date extraction
            date_m = re.search(r'\b(20\d{2}(?:\s*[-–—]\s*20\d{2})?)\b', first_line)
            proj_date = date_m.group(1) if date_m else None

            # Bullets
            bullets = self._extract_bullet_items(raw_chunk)

            if proj_name:
                projects.append({
                    "name": proj_name,
                    "github": github_url,
                    "live_link": live_url,
                    "technologies": techs,
                    "date": proj_date,
                    "description": "\n".join(f"• {b}" for b in bullets) if bullets else clean_first,
                    "highlights": bullets
                })

        return projects

    def parse_skills_section(self, section_text: str) -> List[Dict[str, Any]]:
        """Parses technical skills with category categorization."""
        skills = []
        clean_text = self.strip_comments(section_text)

        # Categorized lines: \textbf{Category:} Skill1, Skill2, Skill3
        category_lines = re.findall(r'\\textbf\{([^}]+)\}\s*:?\s*([^\n]+)', clean_text)
        if category_lines:
            for cat_raw, skills_raw in category_lines:
                category = strip_latex_formatting(cat_raw).replace(":", "").strip()
                clean_skills = strip_latex_formatting(skills_raw)
                clean_skills = re.sub(r'[\}\\]+$', '', clean_skills).strip()
                for item in re.split(r'[,|;]', clean_skills):
                    sk_name = item.strip()
                    if sk_name and len(sk_name) < 50:
                        skills.append({
                            "name": sk_name,
                            "category": category,
                            "confidence": 5,
                            "years_used": 1.0
                        })
        else:
            # Fallback to comma-separated list of items
            plain = strip_latex_formatting(clean_text)
            for item in re.split(r'[,|;\n•]', plain):
                sk_name = item.strip()
                if sk_name and len(sk_name) < 40 and not sk_name.lower().startswith("section"):
                    skills.append({
                        "name": sk_name,
                        "category": "General",
                        "confidence": 5,
                        "years_used": 1.0
                    })

        return skills

    def parse_achievements_section(self, section_text: str) -> List[Dict[str, Any]]:
        """Parses awards, hackathon wins, prizes, and honors."""
        achievements = []
        bullets = self._extract_bullet_items(section_text)

        for b in bullets:
            # Infer category (hackathon, award, prize, publication)
            b_lower = b.lower()
            category = "other"
            if "hackathon" in b_lower:
                category = "hackathon"
            elif any(w in b_lower for w in ["award", "scholarship", "medal", "honors"]):
                category = "award"
            elif any(w in b_lower for w in ["1st", "2nd", "3rd", "first place", "second place", "winner", "prize"]):
                category = "prize"
            elif any(w in b_lower for w in ["published", "paper", "journal", "conference"]):
                category = "publication"

            # Date extraction
            year_m = re.search(r'\b(20\d{2}|19\d{2})\b', b)
            year_or_date = year_m.group(1) if year_m else None

            achievements.append({
                "title": b,
                "category": category,
                "issuer_or_event": None,
                "year_or_date": year_or_date,
                "description": b
            })

        return achievements

    def parse_courses_section(self, section_text: str) -> List[Dict[str, Any]]:
        """Parses courses, licenses, and certifications."""
        courses = []
        bullets = self._extract_bullet_items(section_text)

        for b in bullets:
            courses.append({
                "name": b,
                "issuer": None,
                "issue_date": None,
                "credential_url": None,
                "skills_covered": []
            })

        return courses

    def parse_full_latex(self, latex_text: str) -> Dict[str, Any]:
        """
        Main entry point: parses complete LaTeX document, recognizes custom commands,
        maps sections, flags unparsed elements, and returns normalized candidate data.
        """
        self.flags = []
        self.custom_macros = {}
        self.recognized_macros = []
        self.unparsed_macros = []

        cleaned_text = self.strip_comments(latex_text)
        self.extract_custom_macros(latex_text)

        # Detect macros in document
        for macro in self.KNOWN_RESUME_MACROS:
            if macro in latex_text:
                self.recognized_macros.append(macro)

        # Find unknown macros: \cmd not in KNOWN or standard LaTeX
        all_macros = set(re.findall(r'\\([a-zA-Z]+)', latex_text))
        standard_tex = {
            "documentclass", "usepackage", "begin", "end", "pagestyle", "addtolength",
            "setlength", "titleformat", "input", "include", "small", "large", "Huge",
            "textbf", "textit", "textsc", "emph", "color", "href", "url", "vspace",
            "hspace", "item", "hfill", "newline", "raggedright", "pdfgentounicode"
        }
        custom_names = {v["name"] for v in self.custom_macros.values()}
        for m in all_macros:
            if m not in standard_tex and m not in custom_names and f"\\{m}" not in self.KNOWN_RESUME_MACROS:
                self.unparsed_macros.append(f"\\{m}")

        if self.unparsed_macros:
            self.flags.append({
                "category": "macros",
                "field": "macros",
                "message": f"Found {len(self.unparsed_macros)} unrecognized LaTeX macro(s): {', '.join(self.unparsed_macros[:5])}.",
                "severity": "info"
            })

        # Expand recognized custom 0-argument macros in cleaned text
        for macro_call, macro_def in self.custom_macros.items():
            if macro_def.get("args") == 0 and macro_def.get("body"):
                cleaned_text = re.sub(re.escape(macro_call) + r'(?![a-zA-Z])', lambda m, b=macro_def["body"]: b, cleaned_text)

        # Header contact details
        contact = self.parse_header_contact_info(cleaned_text)

        # Segment sections
        sections = self.extract_sections(cleaned_text)

        education_list = []
        experience_list = []
        projects_list = []
        skills_list = []
        achievements_list = []
        courses_list = []

        # Map each detected section
        for title, body in sections.items():
            t_upper = title.upper()
            if any(k in t_upper for k in ["EDUCATION", "ACADEMIC", "DEGREE"]):
                education_list.extend(self.parse_education_section(body))
            elif any(k in t_upper for k in ["EXPERIENCE", "EMPLOYMENT", "WORK", "INTERNSHIP"]):
                experience_list.extend(self.parse_experience_section(body))
            elif any(k in t_upper for k in ["PROJECT", "ENGINEERING"]):
                projects_list.extend(self.parse_projects_section(body))
            elif any(k in t_upper for k in ["SKILL", "TECHNOLOG", "COMPETENC"]):
                skills_list.extend(self.parse_skills_section(body))
            elif any(k in t_upper for k in ["ACHIEVEMENT", "AWARD", "HONOR", "PRIZE"]):
                achievements_list.extend(self.parse_achievements_section(body))
            elif any(k in t_upper for k in ["CERTIF", "COURSE"]):
                courses_list.extend(self.parse_courses_section(body))
            else:
                self.flags.append({
                    "category": "section",
                    "field": title,
                    "message": f"Unrecognized section '{title}'; review manually.",
                    "severity": "warning"
                })

        # Set primary profile education fields from top education item
        primary_edu = education_list[0] if education_list else {}
        profile_data = {
            "full_name": contact.get("full_name"),
            "email": contact.get("email"),
            "phone": contact.get("phone"),
            "github": contact.get("github"),
            "linkedin": contact.get("linkedin"),
            "portfolio": contact.get("portfolio"),
            "current_location": contact.get("current_location") or primary_edu.get("location"),
            "university": primary_edu.get("institution"),
            "degree": primary_edu.get("degree"),
            "specialization": primary_edu.get("specialization"),
            "cgpa": primary_edu.get("cgpa"),
            "graduation_year": primary_edu.get("graduation_year"),
            "coursework": primary_edu.get("coursework", []),
        }

        return {
            "profile": profile_data,
            "education": education_list,
            "experiences": experience_list,
            "projects": projects_list,
            "skills": skills_list,
            "achievements": achievements_list,
            "courses": courses_list,
            "custom_macros": self.custom_macros,
            "recognized_macros": self.recognized_macros,
            "flags": self.flags,
            "raw_text_preview": strip_latex_formatting(cleaned_text)[:2000]
        }

    def _infer_role_and_company(self, arg1: str, arg2: str, arg3: str, arg4: str) -> Tuple[str, str, str, str]:
        """Disambiguates role vs company and dates vs location across common resume templates."""
        # Typically Jake's resume:
        # \resumeSubheading
        #   {Role / Company}{Dates / Location}
        #   {Company / Role}{Location / Dates}
        # Check if arg1 or arg3 looks like dates
        dates = ""
        location = ""
        for arg in [arg2, arg4]:
            if re.search(r'\b(20\d{2}|19\d{2}|present)\b', arg, re.IGNORECASE):
                dates = arg
            elif arg and not location:
                location = arg

        # Disambiguate company vs title
        title = arg1
        company = arg3
        # If arg3 contains common job titles and arg1 doesn't, swap
        job_words = ["engineer", "developer", "intern", "lead", "analyst", "assistant", "manager", "architect", "fellow"]
        if any(w in arg3.lower() for w in job_words) and not any(w in arg1.lower() for w in job_words):
            title = arg3
            company = arg1

        return title, company, location, dates

    def _extract_bullet_items(self, text: str) -> List[str]:
        """Extracts bullet list items from \\resumeItem{...} and \\item ..."""
        bullets = []

        # 1. \resumeItem{content}
        resume_items = re.findall(r'\\resumeItem\b', text)
        if resume_items:
            for m in re.finditer(r'\\resumeItem\b', text):
                args = extract_braced_arguments(text, m.end())
                if args:
                    clean = strip_latex_formatting(args[0]).strip()
                    if clean:
                        bullets.append(clean)

        # 2. Plain \item content
        if not bullets:
            chunks = re.split(r'\\item\b', text)
            for c in chunks[1:]:
                clean = strip_latex_formatting(c).strip()
                if clean:
                    # Keep first sentence or line
                    first_line = clean.splitlines()[0]
                    bullets.append(first_line)

        return bullets

    def _parse_date_range(self, date_str: str) -> Tuple[Optional[str], Optional[str], bool]:
        """Parses start date, end date, and currently working status."""
        if not date_str:
            return None, None, False

        currently_working = "present" in date_str.lower() or "current" in date_str.lower()
        years = re.findall(r'\b(20\d{2}|19\d{2})\b', date_str)
        start_date = years[0] if years else None
        end_date = "Present" if currently_working else (years[-1] if len(years) > 1 else None)
        return start_date, end_date, currently_working


def extract_and_parse_latex_zip(zip_path: str, extract_dir: str) -> Tuple[str, Dict[str, Any]]:
    """
    Safely unpacks a LaTeX project ZIP archive, identifies the main .tex document,
    resolves \\input and \\include statements, and returns combined LaTeX and parsed facts.
    """
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        # Validate entry paths against zip slip
        for member in zf.infolist():
            target_path = os.path.abspath(os.path.join(extract_dir, member.filename))
            if not target_path.startswith(os.path.abspath(extract_dir)):
                raise ValueError(f"Unsafe ZIP archive member: {member.filename}")
        zf.extractall(extract_dir)

    # Find main .tex file
    tex_files = []
    for root, _, files in os.walk(extract_dir):
        for f in files:
            if f.endswith(".tex"):
                tex_files.append(os.path.join(root, f))

    if not tex_files:
        raise ValueError("No LaTeX (.tex) files found in the uploaded ZIP archive.")

    # Score candidates for main document
    best_file = tex_files[0]
    best_score = -1

    for fpath in tex_files:
        score = 0
        fname = os.path.basename(fpath).lower()
        if fname in ("main.tex", "resume.tex", "cv.tex"):
            score += 10
        try:
            with open(fpath, "r", encoding="utf-8-sig", errors="replace") as f:
                content = f.read()
                if r"\documentclass" in content:
                    score += 20
                if r"\begin{document}" in content:
                    score += 20
        except Exception:
            pass

        if score > best_score:
            best_score = score
            best_file = fpath

    # Read and resolve sub-files
    main_dir = os.path.dirname(best_file)
    with open(best_file, "r", encoding="utf-8-sig", errors="replace") as f:
        main_content = f.read()

    def resolve_inputs(match):
        rel_target = match.group(1).strip()
        if not rel_target.endswith(".tex"):
            rel_target += ".tex"
        sub_path = os.path.join(main_dir, rel_target)
        if os.path.exists(sub_path):
            try:
                with open(sub_path, "r", encoding="utf-8-sig", errors="replace") as sf:
                    return f"\n% --- Inlined from {rel_target} ---\n" + sf.read() + "\n"
            except Exception:
                pass
        return match.group(0)

    # Resolve \input{file} and \include{file}
    combined_tex = re.sub(r'\\(?:input|include)\{([^}]+)\}', resolve_inputs, main_content)

    parser = LatexResumeParser()
    parsed_data = parser.parse_full_latex(combined_tex)
    parsed_data["main_tex_file"] = os.path.relpath(best_file, extract_dir)
    parsed_data["total_project_files"] = len(tex_files)

    return combined_tex, parsed_data
