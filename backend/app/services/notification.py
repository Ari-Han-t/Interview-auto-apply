from app.core.database import SessionLocal
from app.models.notification import Notification
import logging

logger = logging.getLogger(__name__)

def create_notification(user_id: int, notif_type: str, message: str):
    """
    Creates a new notification record in the database for the user.
    """
    db = SessionLocal()
    try:
        notif = Notification(user_id=user_id, type=notif_type, message=message)
        db.add(notif)
        db.commit()
        logger.info(f"Notification created for user {user_id}: [{notif_type}] {message}")
    except Exception as e:
        logger.error(f"Failed to create notification for user {user_id}: {e}")
    finally:
        db.close()
