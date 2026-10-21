"""Shared GitHub sync logic used by the /github/sync endpoint and the tailoring pipeline."""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.profile import Profile
from app.models.candidate import UserProfile, Project, Skill, UserSkill, Achievement
from app.services.scraper.github import fetch_github_projects

logger = logging.getLogger(__name__)

GITHUB_STALE_HOURS = 24


def normalize_github_username(username: str) -> str:
    username = (username or "").strip()
    if username.startswith("http"):
        username = username.rstrip("/").split("/")[-1]
    import re
    username = re.sub(r"[^a-zA-Z0-9_\-]", "", username)
    return username


def is_github_stale(profile: Optional[Profile], project_count: Optional[int] = None) -> bool:
    """True when we should re-fetch GitHub data before tailoring."""
    if not profile or not profile.github_username:
        return False
    if project_count is None:
        session = Session.object_session(profile)
        if session is None:
            return True
        project_count = session.query(Project).filter(Project.user_id == profile.user_id).count()
    if project_count == 0:
        return True
    if not profile.github_synced_at:
        return True
    synced = profile.github_synced_at
    if synced.tzinfo is None:
        synced = synced.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - synced > timedelta(hours=GITHUB_STALE_HOURS)


def sync_github_for_user(db: Session, user_id: int, username: str) -> dict:
    """
    Fetch GitHub repos and upsert Project / Skill / Achievement rows.
    Commits on success. Raises on fetch failure.
    Does NOT overwrite Profile.projects_json with all projects (that field is
    reserved for job-relevance caches from /github/analyze).
    """
    username = normalize_github_username(username)
    if not username:
        raise ValueError("Valid GitHub username is required.")

    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        profile = Profile(user_id=user_id)
        db.add(profile)
    profile.github_username = username

    user_prof = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if user_prof:
        user_prof.github = f"https://github.com/{username}"
    db.commit()

    raw_projects = fetch_github_projects(username)

    synced_projects = 0
    discovered_skills = set()
    discovered_achievements = 0

    for repo in raw_projects:
        r_name = repo.get("name")
        r_desc = repo.get("description") or ""
        r_url = repo.get("url")
        r_home = repo.get("homepage")
        r_lang = repo.get("language")
        r_topics = repo.get("topics") or []

        techs = []
        if r_lang:
            techs.append(r_lang)
            discovered_skills.add(r_lang)
        for t in r_topics:
            techs.append(t)
            discovered_skills.add(t)

        existing_proj = db.query(Project).filter(
            Project.user_id == user_id,
            (Project.github == r_url) | (Project.name == r_name)
        ).first()

        if not existing_proj:
            existing_proj = Project(
                user_id=user_id,
                name=r_name,
                description=r_desc,
                github=r_url,
                live_link=r_home,
                technologies=techs
            )
            db.add(existing_proj)
        else:
            existing_proj.description = r_desc or existing_proj.description
            existing_proj.github = r_url
            existing_proj.live_link = r_home or existing_proj.live_link
            existing_proj.technologies = list(set((existing_proj.technologies or []) + techs))

        synced_projects += 1

        desc_lower = (r_desc + " " + " ".join(r_topics)).lower()
        if any(keyword in desc_lower for keyword in ["hackathon", "winner", "1st place", "first place", "prize", "award", "devsoc"]):
            existing_ach = db.query(Achievement).filter(
                Achievement.user_id == user_id,
                Achievement.title.ilike(f"%{r_name}%")
            ).first()
            if not existing_ach:
                new_ach = Achievement(
                    user_id=user_id,
                    title=f"GitHub Winner / Highlight Project: {r_name}",
                    category="hackathon",
                    issuer_or_event="GitHub Repositories",
                    year_or_date=str(repo.get("updated_at", ""))[:4] if repo.get("updated_at") else None,
                    description=f"{r_desc} (URL: {r_url})"
                )
                db.add(new_ach)
                discovered_achievements += 1

    for sk_name in discovered_skills:
        clean_sk = sk_name.strip()
        if not clean_sk:
            continue
        skill_obj = db.query(Skill).filter(Skill.name == clean_sk).first()
        if not skill_obj:
            skill_obj = Skill(name=clean_sk)
            db.add(skill_obj)
            db.flush()

        user_sk = db.query(UserSkill).filter(
            UserSkill.user_id == user_id,
            UserSkill.skill_id == skill_obj.id
        ).first()
        if not user_sk:
            user_sk = UserSkill(user_id=user_id, skill_id=skill_obj.id, confidence=4, years_used=1.0)
            db.add(user_sk)

    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    profile.github_synced_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "username": username,
        "synced_projects": synced_projects,
        "discovered_skills_count": len(discovered_skills),
        "discovered_achievements_count": discovered_achievements,
    }


def ensure_github_fresh(db: Session, user_id: int, username: Optional[str] = None) -> bool:
    """
    Auto-sync GitHub if a username is known and data is stale/missing.
    Returns True if a sync ran. Never raises (pipeline must not fail on GitHub errors).
    """
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    resolved = normalize_github_username(username or "") or (
        profile.github_username if profile else None
    )
    if not resolved:
        return False

    if username and profile and profile.github_username != resolved:
        profile.github_username = resolved
        db.commit()

    project_count = db.query(Project).filter(Project.user_id == user_id).count()
    if not username and profile and not is_github_stale(profile, project_count):
        return False

    try:
        result = sync_github_for_user(db, user_id, resolved)
        logger.info("Auto-synced GitHub for user %s: %s", user_id, result)
        return True
    except Exception as e:
        logger.warning("GitHub auto-sync failed for user %s (continuing with stored data): %s", user_id, e)
        return False
