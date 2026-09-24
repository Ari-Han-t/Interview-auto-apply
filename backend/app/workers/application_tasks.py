from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.application import Application
from app.models.job import Job
from app.models.application_history import ApplicationHistory
from app.services.automation.browser import submit_application, resume_application
from app.services.notification import create_notification
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
            logger.info("Application paused for user intervention.")
            
            history_entry = ApplicationHistory(
                application_id=app_record.id,
                status="intervention_required",
                notes="Encountered CAPTCHA during submission. Pausing for user intervention."
            )
            db.add(history_entry)
            create_notification(app_record.user_id, "error", f"Application for {job.title} at {job.company} paused: CAPTCHA detected.")
        else:
            app_record.status = "applied"
            app_record.next_action = "Wait for response"
            
            history_entry = ApplicationHistory(
                application_id=app_record.id,
                status="applied",
                notes="Application submitted successfully via automated browser."
            )
            db.add(history_entry)
            create_notification(app_record.user_id, "application_completed", f"Application for {job.title} at {job.company} submitted successfully.")
            
        db.commit()
    except Exception as e:
        logger.error(f"Automation failed: {str(e)}")
        db.rollback()
        if 'app_record' in locals() and app_record:
            try:
                history_entry = ApplicationHistory(
                    application_id=app_record.id,
                    status="failed",
                    notes=f"Automation failed: {str(e)}"
                )
                db.add(history_entry)
                db.commit()
            except Exception as hist_err:
                logger.error(f"Failed to save error history: {hist_err}")
            create_notification(app_record.user_id, "error", f"Application automation failed: {str(e)}")
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
            
        job = db.query(Job).filter(Job.id == app_record.job_id).first()
        result = resume_application("dummy_session_id")
        
        if result["status"] == "applied":
            app_record.status = "applied"
            app_record.next_action = "Wait for response"
            
            history_entry = ApplicationHistory(
                application_id=app_record.id,
                status="applied",
                notes="Application submitted successfully after CAPTCHA was solved."
            )
            db.add(history_entry)
            create_notification(app_record.user_id, "application_completed", f"Application for {job.title} at {job.company} submitted successfully after CAPTCHA.")
            
        db.commit()
    except Exception as e:
        logger.error(f"Resume failed: {str(e)}")
        db.rollback()
        if 'app_record' in locals() and app_record:
            create_notification(app_record.user_id, "error", f"Failed to resume application submission: {str(e)}")
    finally:
        db.close()
