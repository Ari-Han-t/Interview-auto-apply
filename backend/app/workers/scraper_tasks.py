from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.job import Job
from app.services.scraper.yc import scrape_yc_jobs
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def run_job_discovery(source: str):
    logger.info(f"Starting job discovery for source: {source}")
    try:
        if source == "yc":
            jobs = scrape_yc_jobs()
            db = SessionLocal()
            try:
                for job_data in jobs:
                    existing = db.query(Job).filter(Job.url == job_data["url"]).first()
                    if not existing:
                        new_job = Job(
                            title=job_data["title"],
                            company=job_data["company"],
                            url=job_data["url"],
                            description=job_data["description"],
                            location=job_data.get("location", ""),
                            status="discovered"
                        )
                        db.add(new_job)
                db.commit()
            finally:
                db.close()
        else:
            logger.warning(f"Unknown source: {source}")
    except Exception as e:
        logger.error(f"Scraping failed for {source}: {str(e)}")
