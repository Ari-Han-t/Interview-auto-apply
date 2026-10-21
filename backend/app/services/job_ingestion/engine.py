import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from app.models.job import Job, JobSourceSyncLog, JobSourceConfig
from app.services.scraper.adapters.registry import get_adapter, list_adapters, ADAPTERS_MAP
from app.services.job_ingestion.deduplicator import compute_job_dedup_hash, merge_canonical_job_records

logger = logging.getLogger(__name__)

class JobIngestionEngine:
    """
    Ingestion engine that coordinates multi-platform job synchronization,
    rate-limiting, error isolation, deduplication, and expiration tracking.
    """

    @staticmethod
    def sync_source(
        source_id: str,
        db: Session,
        keywords: Optional[str] = None,
        location: Optional[str] = None,
        job_type: str = "both",
        limit: int = 50,
        custom_token: Optional[str] = None,
        triggered_by: str = "manual"
    ) -> Dict[str, Any]:
        adapter = get_adapter(source_id)
        if not adapter:
            raise ValueError(f"Unknown source adapter: {source_id}")

        start_time = datetime.utcnow()
        start_ticks = time.time()
        items_found = 0
        items_imported = 0
        items_updated = 0
        status = "success"
        error_msg = None

        if not adapter.can_fetch_catalog:
            # Source requires authorization or partner credentials
            status = "blocked"
            error_msg = adapter.access_requirement
            log_entry = JobSourceSyncLog(
                source_id=source_id,
                status=status,
                items_found=0,
                items_imported=0,
                items_updated=0,
                error_message=error_msg,
                access_requirement=adapter.access_requirement,
                duration_ms=int((time.time() - start_ticks) * 1000),
                triggered_by=triggered_by,
                started_at=start_time,
                completed_at=datetime.utcnow()
            )
            db.add(log_entry)
            db.commit()
            return {
                "source_id": source_id,
                "status": status,
                "items_found": 0,
                "items_imported": 0,
                "items_updated": 0,
                "message": adapter.access_requirement
            }

        # Attempt fetching with retry logic
        fetched_jobs = []
        max_retries = 2
        for attempt in range(max_retries):
            try:
                fetched_jobs = adapter.fetch_jobs(
                    keywords=keywords,
                    location=location,
                    job_type=job_type,
                    limit=limit,
                    custom_token=custom_token
                )
                break
            except Exception as e:
                logger.warning(f"Error fetching {source_id} (attempt {attempt+1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    status = "failed"
                    error_msg = str(e)
                time.sleep(1.0 * (attempt + 1))

        items_found = len(fetched_jobs)

        # Ingestion & Deduplication
        if fetched_jobs:
            for job_data in fetched_jobs:
                try:
                    comp = job_data.get("company", "Company")
                    title = job_data.get("title", "Role")
                    loc = job_data.get("location", "Remote")
                    emp = job_data.get("employment_type", "fulltime")
                    url = job_data.get("url") or ""

                    dedup_hash = compute_job_dedup_hash(comp, title, loc, emp)
                    existing = db.query(Job).filter(
                        (Job.url == url) | (Job.dedup_hash == dedup_hash)
                    ).first()

                    if existing:
                        merge_canonical_job_records(existing, job_data)
                        existing.dedup_hash = dedup_hash
                        items_updated += 1
                    else:
                        new_job = Job(
                            title=title,
                            company=comp,
                            url=url,
                            application_url=job_data.get("application_url") or url,
                            description=job_data.get("description", ""),
                            responsibilities_json=job_data.get("responsibilities_json", []),
                            required_skills_json=job_data.get("required_skills_json", []),
                            preferred_skills_json=job_data.get("preferred_skills_json", []),
                            requirements_json=job_data.get("requirements_json", {}),
                            eligibility_criteria_json=job_data.get("eligibility_criteria_json", {}),
                            graduation_restrictions=job_data.get("graduation_restrictions", []),
                            status="active",
                            deadline=job_data.get("deadline"),
                            location=loc,
                            work_arrangement=job_data.get("work_arrangement", "onsite"),
                            employment_type=emp,
                            salary_range=job_data.get("salary_range"),
                            compensation_min=job_data.get("compensation_min"),
                            compensation_max=job_data.get("compensation_max"),
                            currency=job_data.get("currency", "USD"),
                            compensation_interval=job_data.get("compensation_interval"),
                            is_remote=job_data.get("is_remote", False),
                            tech_stack_json=job_data.get("tech_stack_json", []),
                            company_logo_url=job_data.get("company_logo_url"),
                            source=source_id,
                            source_job_id=str(job_data.get("source_job_id", "")),
                            source_provenance=job_data.get("source_provenance", {}),
                            posted_at=job_data.get("posted_at") or datetime.utcnow(),
                            last_verified_at=datetime.utcnow(),
                            is_expired=False,
                            dedup_hash=dedup_hash
                        )
                        db.add(new_job)
                        items_imported += 1
                except Exception as ingest_err:
                    logger.warning(f"Error persisting job item: {ingest_err}")
                    continue

            db.commit()

        # Update JobSourceConfig if exists
        cfg = db.query(JobSourceConfig).filter(JobSourceConfig.source_id == source_id).first()
        if not cfg:
            cfg = JobSourceConfig(
                source_id=source_id,
                display_name=adapter.name,
                auth_status=adapter.auth_status,
                access_requirement=adapter.access_requirement,
                last_sync_at=datetime.utcnow()
            )
            db.add(cfg)
        else:
            cfg.last_sync_at = datetime.utcnow()

        # Record Sync Log
        duration_ms = int((time.time() - start_ticks) * 1000)
        log_entry = JobSourceSyncLog(
            source_id=source_id,
            status=status,
            items_found=items_found,
            items_imported=items_imported,
            items_updated=items_updated,
            error_message=error_msg,
            access_requirement=adapter.access_requirement,
            duration_ms=duration_ms,
            triggered_by=triggered_by,
            started_at=start_time,
            completed_at=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()

        return {
            "source_id": source_id,
            "status": status,
            "items_found": items_found,
            "items_imported": items_imported,
            "items_updated": items_updated,
            "duration_ms": duration_ms,
            "error_message": error_msg
        }

    @classmethod
    def sync_all_sources(
        cls,
        db: Session,
        keywords: Optional[str] = None,
        location: Optional[str] = None,
        job_type: str = "both",
        triggered_by: str = "scheduled"
    ) -> Dict[str, Any]:
        """
        Runs synchronization across all configured sources with strict error isolation.
        One source failure will never break or abort the rest.
        """
        # Sources with public catalog fetching capabilities
        active_sources = ["greenhouse", "lever", "ashby", "yc", "internshala", "custom_feed"]
        results = {}
        
        for src in active_sources:
            try:
                res = cls.sync_source(
                    source_id=src,
                    db=db,
                    keywords=keywords,
                    location=location,
                    job_type=job_type,
                    limit=20,
                    triggered_by=triggered_by
                )
                results[src] = res
            except Exception as e:
                logger.error(f"Sync source {src} encountered unhandled error: {e}")
                results[src] = {"status": "failed", "error": str(e)}

        # Update expired jobs
        cls.update_expired_jobs(db)

        return results

    @staticmethod
    def update_expired_jobs(db: Session) -> int:
        """Marks jobs past deadline as expired."""
        now = datetime.utcnow()
        expired_count = 0
        expired_jobs = db.query(Job).filter(
            Job.is_expired == False,
            Job.deadline.isnot(None),
            Job.deadline < now
        ).all()
        for job in expired_jobs:
            job.is_expired = True
            job.expired_at = now
            job.status = "expired"
            expired_count += 1
        if expired_count > 0:
            db.commit()
        return expired_count
