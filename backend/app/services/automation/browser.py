import time
import logging

logger = logging.getLogger(__name__)

def submit_application(job_url: str, resume_path: str, cover_letter_path: str) -> dict:
    """
    Mock Playwright function to submit an application.
    Simulates navigating to the ATS, filling out the form, and encountering a CAPTCHA.
    """
    logger.info(f"Navigating to {job_url} via Playwright...")
    time.sleep(1)
    
    logger.info("Filling out standard profile fields (Name, Email, Phone)...")
    time.sleep(1)
    
    logger.info(f"Uploading Resume: {resume_path}")
    logger.info(f"Uploading Cover Letter: {cover_letter_path}")
    time.sleep(1)
    
    # Simulate a CAPTCHA interruption 50% of the time, 
    # but for this milestone we'll force it so we can test the intervention flow.
    logger.warning("CAPTCHA detected! Pausing automation for user intervention.")
    
    return {
        "status": "intervention_required",
        "message": "Encountered CAPTCHA on the application page.",
        "screenshot_url": "https://placehold.co/600x400/png?text=CAPTCHA+Screenshot" # Mock screenshot
    }

def resume_application(session_id: str) -> dict:
    """
    Mock function to resume Playwright session after user solves the CAPTCHA.
    """
    logger.info(f"Resuming Playwright session {session_id}...")
    time.sleep(2)
    
    logger.info("Submitting application...")
    
    return {
        "status": "applied",
        "message": "Application submitted successfully."
    }
