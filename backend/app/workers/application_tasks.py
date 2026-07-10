from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.application import Application
from app.models.job import Job
from app.services.automation.browser import submit_application, resume_application
import logging

logger = logging.getLogger(__name__)

@celery_app.task
def trigger_automation(application_id: int):
    logger.info(f"Triggering automation for application ID: {application_id}")
    db = SessionLocal()
    try:
        app_record = db.query(Application).filter(Application.id == application_id).first()
        if not app_record:
            logger.error("Application not found.")
            return

        job = db.query(Job).filter(Job.id == app_record.job_id).first()
        
        # In real life, Playwright would run here. We simulate the intervention flow.
        result = submit_application(job.url, app_record.resume_version_url, app_record.cover_letter_url)
        
        if result["status"] == "intervention_required":
            app_record.status = "intervention_required"
            app_record.next_action = "Solve CAPTCHA"
            # Here we would normally store the websocket/session ID to resume later
            logger.info("Application paused for user intervention.")
        else:
            app_record.status = "applied"
            app_record.next_action = "Wait for response"
            
        db.commit()
    except Exception as e:
        logger.error(f"Automation failed: {str(e)}")
        db.rollback()
    finally:
        db.close()

@celery_app.task
def resume_automation(application_id: int):
    logger.info(f"Resuming automation for application ID: {application_id}")
    db = SessionLocal()
    try:
        app_record = db.query(Application).filter(Application.id == application_id).first()
        if not app_record:
            return
            
        result = resume_application("dummy_session_id")
        
        if result["status"] == "applied":
            app_record.status = "applied"
            app_record.next_action = "Wait for response"
            
        db.commit()
    except Exception as e:
        logger.error(f"Resume failed: {str(e)}")
        db.rollback()
    finally:
        db.close()
