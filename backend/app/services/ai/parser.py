import json
import logging
import re
import unicodedata
from datetime import datetime
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator
from sqlalchemy import null
from sqlalchemy.sql.elements import Null
from app.core.database import SessionLocal
from app.models.profile import Profile
from app.models.candidate import (
    UserProfile, CandidateEducation, CandidateExperience, Project, Skill, UserSkill,
    Achievement, CourseCertification,
)

logger = logging.getLogger(__name__)
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]


class ResumeParseError(Exception):
    pass


class ResumeTextError(ValueError):
    pass


class ExtractedRecord(BaseModel):
    model_config = ConfigDict(strict=True, extra="ignore", allow_inf_nan=False)

    @field_validator("*", mode="after")
    @classmethod
    def validate_links(cls, value, info):
        if info.field_name in {"github", "linkedin", "portfolio", "live_link", "credential_url"} and value:
            parsed = urlsplit(value)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("Expected a public HTTP(S) URL")
        return value


class EducationExtraction(ExtractedRecord):
    institution: Text | None = None
    degree: Text | None = None
    specialization: Text | None = None
    year: Annotated[int, Field(ge=1900, le=2200)] | None = None
    cgpa: Annotated[float, Field(ge=0, le=100)] | None = None
    coursework: list[Text] = Field(default_factory=list, max_length=200)



class ExperienceExtraction(ExtractedRecord):
    company: Text
    title: Text
    internship_or_fulltime: Literal["internship", "fulltime"] | None = None
    start_date: Text | None = None
    end_date: Text | None = None
    currently_working: bool | None = None
    months_of_experience: Annotated[int, Field(ge=0, le=1200)] | None = None
    description: Text | None = None


class ProjectExtraction(ExtractedRecord):
    name: Text
    description: Text | None = None
    github: Text | None = None
    live_link: Text | None = None
    technologies: list[Text] = Field(default_factory=list, max_length=200)


class SkillExtraction(ExtractedRecord):
    name: Text
    confidence: Annotated[int, Field(ge=1, le=5)] | None = None
    years_used: Annotated[float, Field(ge=0, le=100)] | None = None


class AchievementExtraction(ExtractedRecord):
    title: Text
    category: Literal["hackathon", "award", "prize", "publication", "other"] | None = None
    issuer_or_event: Text | None = None
    year_or_date: Text | None = None
    description: Text | None = None


class CourseExtraction(ExtractedRecord):
    name: Text
    issuer: Text | None = None
    issue_date: Text | None = None
    credential_url: Text | None = None
    skills_covered: list[Text] = Field(default_factory=list, max_length=200)


class ResumeExtraction(ExtractedRecord):
    full_name: Text | None = None
    preferred_name: Text | None = None
    email: Text | None = None
    phone: Text | None = None
    github: Text | None = None
    linkedin: Text | None = None
    portfolio: Text | None = None
    website: Text | None = None
    current_location: Text | None = None
    bio: Text | None = None
    availability: Text | None = None
    education: list[EducationExtraction] = Field(default_factory=list, max_length=100)
    experience: list[ExperienceExtraction] = Field(default_factory=list, max_length=200)
    projects: list[ProjectExtraction] = Field(default_factory=list, max_length=200)
    skills: list[SkillExtraction] = Field(default_factory=list, max_length=500)
    achievements: list[AchievementExtraction] = Field(default_factory=list, max_length=200)
    courses: list[CourseExtraction] = Field(default_factory=list, max_length=200)

    @field_validator("skills", "achievements", "courses", mode="before")
    @classmethod
    def expand_strings(cls, value, info):
        key = "title" if info.field_name == "achievements" else "name"
        if isinstance(value, list):
            return [{key: item} if isinstance(item, str) else item for item in value]
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value):
        if value and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Invalid email")
        return value


def validate_resume_text(text):
    if not isinstance(text, str) or not text.strip() or not any(char.isalnum() for char in text):
        raise ResumeTextError("No readable resume text. Please upload a text-readable resume first.")
    if "\x00" in text or "\ufffd" in text:
        raise ResumeTextError("Resume text is unreadable. Please upload a text-readable resume first.")
    return text.strip()


def _clean_url(val):
    if not isinstance(val, str) or not val.strip():
        return val
    val = val.strip()
    first_part = val.split("/")[0]
    if ":" in first_part:
        return val
    return f"https://{val}"


def _clean_empty_strings(data):
    if isinstance(data, dict):
        return {k: _clean_empty_strings(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_clean_empty_strings(v) for v in data]
    if isinstance(data, str) and not data.strip():
        return None
    return data


def _sanitize_extracted_dict(data):
    if not isinstance(data, dict):
        return data
    cleaned = _clean_empty_strings(data)
    for key in ("github", "linkedin", "portfolio", "live_link", "credential_url"):
        if key in cleaned:
            cleaned[key] = _clean_url(cleaned[key])
    for section in ("projects", "experience", "education", "courses", "achievements"):
        items = cleaned.get(section)
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    for key in ("github", "linkedin", "portfolio", "live_link", "credential_url"):
                        if key in item:
                            item[key] = _clean_url(item[key])
    return cleaned


def extract_resume(text_content):
    text_content = validate_resume_text(text_content)
    try:
        from app.services.llm.gemini_provider import GeminiProvider

        provider = GeminiProvider()
        concise_schema = {
            "full_name": "string (or null)",
            "email": "string (or null)",
            "phone": "string (or null)",
            "github": "string (http/https URL or null)",
            "linkedin": "string (http/https URL or null)",
            "portfolio": "string (http/https URL or null)",
            "current_location": "string (or null)",
            "education": [{"institution": "string", "degree": "string", "year": 2028, "cgpa": 8.5}],
            "experience": [{"company": "string", "title": "string", "internship_or_fulltime": "internship or fulltime", "start_date": "YYYY-MM", "end_date": "string", "currently_working": False, "description": "string"}],
            "projects": [{"name": "string", "description": "string", "github": "string URL (or null)", "live_link": "string URL (or null)", "technologies": ["string"]}],
            "skills": [{"name": "string", "confidence": 5, "years_used": 1.0}],
            "achievements": [{"title": "string", "category": "hackathon, award, prize, publication, or other", "issuer_or_event": "string", "year_or_date": "string", "description": "string"}],
            "courses": [{"name": "string", "issuer": "string", "issue_date": "string", "credential_url": "string URL (or null)", "skills_covered": ["string"]}]
        }

        system_prompt = (
            "You are an expert resume parsing engine. Extract ONLY facts explicitly stated in the resume into the following JSON schema.\n"
            "STRICT RULES:\n"
            "1. Output ONLY a valid JSON object matching the schema. No markdown fences, no conversational text, and NO thoughts or analysis inside the JSON.\n"
            "2. Start immediately with '{' and provide all extracted facts.\n"
            "3. Omit absent fields or use null for absent scalar values and [] for absent lists.\n"
            "4. Preserve stated institution, degree, projects, technologies, and skills.\n"
            f"Schema:\n{json.dumps(concise_schema, indent=2)}"
        )

        extracted = provider.generate_json(
            system_prompt=system_prompt,
            user_prompt=text_content,
            max_tokens=4096,
        )
        if not isinstance(extracted, dict):
            raise ValueError("Expected a JSON object from resume extraction")
        extracted = _sanitize_extracted_dict(dict(extracted))
        result = ResumeExtraction.model_validate(extracted)
        if not any(
            value for key, value in result.model_dump(exclude_none=True).items()
            if key != "education"
        ) and not any(edu.institution or edu.degree or edu.year is not None for edu in result.education):
            raise ValueError("No profile facts extracted")
        return result
    except Exception as exc:
        raise ResumeParseError("Resume extraction failed. Please try again.") from exc


def _key(value):
    return " ".join(unicodedata.normalize("NFKC", value or "").casefold().split())


def _url_key(value):
    return re.sub(r"^https?://(?:www\.)?", "", _key(value)).rstrip("/").removesuffix(".git")


def _date_key(value):
    value = _key(value)
    for fmt in ("%Y-%m", "%Y-%m-%d", "%m/%Y", "%B %Y", "%b %Y"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m")
        except ValueError:
            pass
    return value


def _missing(value):
    if value is None or isinstance(value, Null):
        return True
    if isinstance(value, str):
        val_str = value.strip()
        return not val_str or val_str in ("[]", "{}", '""', "null")
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _fill_missing(record, values):
    changed = 0
    for field, value in values.items():
        if value is None:
            continue
        existing = getattr(record, field)
        if isinstance(existing, str) and existing.strip() in ("[]", "{}"):
            existing = [] if existing.strip() == "[]" else {}
            setattr(record, field, existing)

        if isinstance(value, list):
            if isinstance(existing, str):
                try:
                    existing = json.loads(existing) if existing.strip() else []
                except Exception:
                    existing = []
            merged = list(existing or [])
            seen = {_key(item) for item in merged}
            for item in value:
                if _key(item) not in seen:
                    merged.append(item)
                    seen.add(_key(item))
            if merged != (existing or []):
                setattr(record, field, merged)
                changed += 1
        elif _missing(existing):
            setattr(record, field, value)
            changed += 1
    return changed


def _compatible(left, right, key=_key):
    return _missing(left) or _missing(right) or key(left) == key(right)


def _matches(record, values, section):
    if section == "projects":
        return _key(record.name) == _key(values["name"]) or any(
            values.get(field) and getattr(record, field)
            and _url_key(values[field]) == _url_key(getattr(record, field))
            for field in ("github", "live_link")
        )
    if section == "experiences":
        return (
            _key(record.company) == _key(values["company"])
            and _key(record.title) == _key(values["title"])
            and _compatible(record.start_date, values.get("start_date"), _date_key)
        )
    name, issuer, date = (
        ("title", "issuer_or_event", "year_or_date") if section == "achievements"
        else ("name", "issuer", "issue_date")
    )
    if section == "courses" and values.get("credential_url") and record.credential_url:
        if _url_key(values["credential_url"]) == _url_key(record.credential_url):
            return True
    return (
        _key(getattr(record, name)) == _key(values[name])
        and _compatible(getattr(record, issuer), values.get(issuer))
        and _compatible(getattr(record, date), values.get(date), _date_key)
    )


def merge_resume_to_profile(db, user_id, extracted):
    extracted = ResumeExtraction.model_validate(extracted)
    counts = dict.fromkeys(("profile_fields", "experiences", "projects", "skills", "achievements", "courses"), 0)
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if profile is None:
        profile = UserProfile(user_id=user_id, visa_required=null(), willing_to_relocate=null())
        db.add(profile)
    contacts = extracted.model_dump(exclude_none=True, exclude={
        "education", "experience", "projects", "skills", "achievements", "courses",
    })
    counts["profile_fields"] += _fill_missing(profile, contacts)
    for education in extracted.education:
        if not _compatible(profile.university, education.institution) or not _compatible(profile.degree, education.degree):
            continue
        if profile.graduation_year is not None and education.year is not None and profile.graduation_year != education.year:
            continue
        counts["profile_fields"] += _fill_missing(profile, {
            "university": education.institution, "degree": education.degree,
            "specialization": education.specialization,
            "graduation_year": education.year, "cgpa": education.cgpa,
            "coursework": education.coursework,
        })
        # Synchronize CandidateEducation record
        edu_rec = db.query(CandidateEducation).filter(
            CandidateEducation.user_id == user_id,
            CandidateEducation.is_archived.is_(False)
        ).first()
        if edu_rec is None:
            edu_rec = CandidateEducation(user_id=user_id)
            db.add(edu_rec)
        if education.institution and _missing(edu_rec.institution):
            edu_rec.institution = education.institution
        if education.degree and _missing(edu_rec.degree):
            edu_rec.degree = education.degree
        if education.specialization and _missing(edu_rec.specialization):
            edu_rec.specialization = education.specialization
        if education.year and not edu_rec.graduation_year:
            edu_rec.graduation_year = education.year
            if not edu_rec.start_year:
                edu_rec.start_year = education.year - 4
        if education.cgpa and not edu_rec.cgpa:
            edu_rec.cgpa = education.cgpa
            edu_rec.gpa_scale = "10.0" if education.cgpa > 4.0 else "4.0"
        if education.coursework and _missing(edu_rec.coursework):
            edu_rec.coursework = education.coursework
        if education.institution or education.degree or education.year is not None:
            break

    for section, model, items in (
        ("experiences", CandidateExperience, extracted.experience),
        ("projects", Project, extracted.projects),
        ("achievements", Achievement, extracted.achievements),
        ("courses", CourseCertification, extracted.courses),
    ):
        records = db.query(model).filter(model.user_id == user_id).all()
        touched = set()
        for item in items:
            values = item.model_dump(exclude_none=True)
            record = next((row for row in records if _matches(row, values, section)), None)
            if record is None:
                record = model(user_id=user_id)
                db.add(record)
                records.append(record)
                if section == "experiences":
                    record.currently_working = values.pop("currently_working", null())
                    record.months_of_experience = values.pop("months_of_experience", null())
                _fill_missing(record, values)
                touched.add(id(record))
            elif _fill_missing(record, values):
                touched.add(id(record))
        counts[section] = len(touched)

    skills = {_key(skill.name): skill for skill in db.query(Skill).all()}
    links = {
        _key(link.skill.name): link
        for link in db.query(UserSkill).filter(UserSkill.user_id == user_id).all()
    }
    touched = set()
    for item in extracted.skills:
        key = _key(item.name)
        values = item.model_dump(exclude={"name"}, exclude_none=True)
        if key in links:
            if _fill_missing(links[key], values):
                touched.add(key)
            continue
        skill = skills.get(key)
        if skill is None:
            skill = Skill(name=item.name)
            db.add(skill)
            db.flush()
            skills[key] = skill
        link = UserSkill(user_id=user_id, skill_id=skill.id,
                         confidence=values.get("confidence", null()),
                         years_used=values.get("years_used", null()))
        db.add(link)
        links[key] = link
        touched.add(key)
    counts["skills"] = len(touched)
    db.flush()

    # Sync JSON fields on legacy Profile if not already set (preserves manual edits)
    profile_legacy = db.query(Profile).filter(Profile.user_id == user_id).first()
    if profile_legacy:
        if not profile_legacy.projects_json:
            db_projects = db.query(Project).filter(Project.user_id == user_id).all()
            profile_legacy.projects_json = [
                {
                    "name": p.name,
                    "description": p.description,
                    "github": p.github,
                    "live_link": p.live_link,
                    "technologies": p.technologies or []
                }
                for p in db_projects
            ]
        if not profile_legacy.skills_json:
            db_skills = db.query(UserSkill).filter(UserSkill.user_id == user_id).all()
            profile_legacy.skills_json = [
                {"name": us.skill.name, "confidence": us.confidence, "years_used": us.years_used}
                for us in db_skills
            ]
        db.flush()

    return counts


def parse_resume_to_profile(profile_id: int, text_content: str):
    with SessionLocal() as db:
        try:
            profile = db.query(Profile).filter(Profile.id == profile_id).first()
            if profile is None:
                return None
            extracted = extract_resume(text_content)
            counts = merge_resume_to_profile(db, profile.user_id, extracted)
            db.commit()
            return counts
        except Exception:
            db.rollback()
            logger.warning("Resume autofill failed for profile %s", profile_id)
            raise


def apply_reviewed_profile_data(db, user_id: int, review_data: dict) -> dict:
    """
    Applies user-reviewed facts to the candidate master profile across all normalized tables.
    Preserves and updates all approved entities with transaction safety.
    """
    counts = dict.fromkeys(("profile_fields", "education", "experiences", "projects", "skills", "achievements", "courses"), 0)
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id)
        db.add(profile)
        db.flush()

    prof_in = review_data.get("profile", {})
    if prof_in:
        for k, v in prof_in.items():
            if hasattr(profile, k) and v is not None:
                setattr(profile, k, v)
                counts["profile_fields"] += 1

    # Candidate Educations
    edus_in = review_data.get("education") or review_data.get("educations") or []
    if edus_in:
        from app.models.candidate import CandidateEducation
        existing_edus = db.query(CandidateEducation).filter(CandidateEducation.user_id == user_id).all()
        for edu_item in edus_in:
            inst = edu_item.get("institution")
            if not inst:
                continue
            match = next((e for e in existing_edus if _key(e.institution) == _key(inst)), None)
            if not match:
                match = CandidateEducation(user_id=user_id, institution=inst)
                db.add(match)
                existing_edus.append(match)
            for k in ("degree", "specialization", "start_year", "graduation_year", "cgpa", "coursework", "location", "is_visible"):
                if k in edu_item and edu_item[k] is not None:
                    setattr(match, k, edu_item[k])
            counts["education"] += 1

    # Experiences
    exps_in = review_data.get("experiences", [])
    if exps_in:
        existing_exps = db.query(CandidateExperience).filter(CandidateExperience.user_id == user_id).all()
        for exp_item in exps_in:
            comp = exp_item.get("company")
            title = exp_item.get("title")
            if not comp or not title:
                continue
            match = next((e for e in existing_exps if _key(e.company) == _key(comp) and _key(e.title) == _key(title)), None)
            if not match:
                match = CandidateExperience(user_id=user_id, company=comp, title=title)
                db.add(match)
                existing_exps.append(match)
            for k in ("internship_or_fulltime", "location", "start_date", "end_date", "currently_working", "months_of_experience", "description", "technologies", "highlights", "is_visible"):
                if k in exp_item and exp_item[k] is not None:
                    setattr(match, k, exp_item[k])
            counts["experiences"] += 1

    # Projects
    projs_in = review_data.get("projects", [])
    if projs_in:
        existing_projs = db.query(Project).filter(Project.user_id == user_id).all()
        for proj_item in projs_in:
            name = proj_item.get("name")
            if not name:
                continue
            match = next((p for p in existing_projs if _key(p.name) == _key(name)), None)
            if not match:
                match = Project(user_id=user_id, name=name)
                db.add(match)
                existing_projs.append(match)
            for k in ("description", "github", "live_link", "technologies", "role", "start_date", "end_date", "highlights", "is_visible"):
                if k in proj_item and proj_item[k] is not None:
                    setattr(match, k, proj_item[k])
            counts["projects"] += 1

    # Skills
    skills_in = review_data.get("skills", [])
    if skills_in:
        existing_skills = {_key(s.name): s for s in db.query(Skill).all()}
        existing_links = {_key(us.skill.name): us for us in db.query(UserSkill).filter(UserSkill.user_id == user_id).all()}
        for sk_item in skills_in:
            sk_name = sk_item.get("name") if isinstance(sk_item, dict) else str(sk_item)
            sk_name = sk_name.strip()
            if not sk_name:
                continue
            k = _key(sk_name)
            skill_row = existing_skills.get(k)
            if not skill_row:
                skill_row = Skill(name=sk_name)
                db.add(skill_row)
                db.flush()
                existing_skills[k] = skill_row
            link = existing_links.get(k)
            if not link:
                link = UserSkill(user_id=user_id, skill_id=skill_row.id)
                db.add(link)
                existing_links[k] = link
            if isinstance(sk_item, dict):
                if "confidence" in sk_item and sk_item["confidence"] is not None:
                    link.confidence = sk_item["confidence"]
                if "years_used" in sk_item and sk_item["years_used"] is not None:
                    link.years_used = sk_item["years_used"]
                if "category" in sk_item and sk_item["category"]:
                    link.category = sk_item["category"]
                if "is_visible" in sk_item and sk_item["is_visible"] is not None:
                    link.is_visible = sk_item["is_visible"]
            counts["skills"] += 1

    # Achievements
    achs_in = review_data.get("achievements", [])
    if achs_in:
        existing_achs = db.query(Achievement).filter(Achievement.user_id == user_id).all()
        for ach_item in achs_in:
            title = ach_item.get("title") if isinstance(ach_item, dict) else str(ach_item)
            if not title:
                continue
            match = next((a for a in existing_achs if _key(a.title) == _key(title)), None)
            if not match:
                match = Achievement(user_id=user_id, title=title)
                db.add(match)
                existing_achs.append(match)
            if isinstance(ach_item, dict):
                for k in ("category", "issuer_or_event", "year_or_date", "description", "url", "is_visible"):
                    if k in ach_item and ach_item[k] is not None:
                        setattr(match, k, ach_item[k])
            counts["achievements"] += 1

    # Courses
    courses_in = review_data.get("courses", [])
    if courses_in:
        existing_courses = db.query(CourseCertification).filter(CourseCertification.user_id == user_id).all()
        for crs_item in courses_in:
            name = crs_item.get("name") if isinstance(crs_item, dict) else str(crs_item)
            if not name:
                continue
            match = next((c for c in existing_courses if _key(c.name) == _key(name)), None)
            if not match:
                match = CourseCertification(user_id=user_id, name=name)
                db.add(match)
                existing_courses.append(match)
            if isinstance(crs_item, dict):
                for k in ("issuer", "issue_date", "expiry_date", "credential_id", "credential_url", "skills_covered", "is_visible"):
                    if k in crs_item and crs_item[k] is not None:
                        setattr(match, k, crs_item[k])
            counts["courses"] += 1

    db.flush()

    # Sync legacy Profile row
    profile_legacy = db.query(Profile).filter(Profile.user_id == user_id).first()
    if profile_legacy:
        db_projects = db.query(Project).filter(Project.user_id == user_id).all()
        profile_legacy.projects_json = [
            {"name": p.name, "description": p.description, "github": p.github, "live_link": p.live_link, "technologies": p.technologies or []}
            for p in db_projects
        ]
        db_skills = db.query(UserSkill).filter(UserSkill.user_id == user_id).all()
        profile_legacy.skills_json = [
            {"name": us.skill.name, "confidence": us.confidence, "years_used": us.years_used, "category": us.category}
            for us in db_skills
        ]
        db.flush()

    return counts

