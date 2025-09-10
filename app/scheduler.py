import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ChatAttachment
from pathlib import Path
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def simple_cleanup_task():
    """Simple cleanup task for expired chat attachments"""
    try:
        db = next(get_db())
        
        # Find expired attachments
        expired_attachments = db.query(ChatAttachment).filter(
            ChatAttachment.expires_at < datetime.utcnow()
        ).all()
        
        cleaned_count = 0
        for attachment in expired_attachments:
            try:
                # Delete physical file if it exists
                if attachment.file_path and os.path.exists(attachment.file_path):
                    os.unlink(attachment.file_path)
                    logger.info(f"Deleted expired file: {attachment.file_path}")
                
                # Delete database record
                db.delete(attachment)
                cleaned_count += 1
                
            except Exception as e:
                logger.error(f"Error cleaning up attachment {attachment.id}: {e}")
                # Still delete the database record
                db.delete(attachment)
                cleaned_count += 1
        
        db.commit()
        logger.info(f"Cleaned up {cleaned_count} expired attachments")
        return {"cleaned": cleaned_count}
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return {"error": str(e)}
    finally:
        db.close()

class CleanupScheduler:
    """Simple scheduler for running cleanup tasks"""
    
    def __init__(self):
        self.running = False
        self.cleanup_interval = 3600  # 1 hour in seconds
    
    async def start(self):
        """Start the cleanup scheduler"""
        if self.running:
            logger.warning("Cleanup scheduler is already running")
            return
        
        self.running = True
        logger.info("Starting cleanup scheduler")
        
        while self.running:
            try:
                # Run cleanup task
                result = simple_cleanup_task()
                logger.info(f"Cleanup task result: {result}")
                
                # Wait for next cleanup
                await asyncio.sleep(self.cleanup_interval)
                
            except Exception as e:
                logger.error(f"Error in cleanup scheduler: {e}")
                # Wait a bit before retrying
                await asyncio.sleep(300)  # 5 minutes
    
    def stop(self):
        """Stop the cleanup scheduler"""
        logger.info("Stopping cleanup scheduler")
        self.running = False
    
    def set_interval(self, seconds: int):
        """Set cleanup interval in seconds"""
        self.cleanup_interval = seconds
        logger.info(f"Cleanup interval set to {seconds} seconds")

# Global scheduler instance
cleanup_scheduler = CleanupScheduler()

async def start_cleanup_scheduler():
    """Start the cleanup scheduler (call this from main.py)"""
    await cleanup_scheduler.start()

def stop_cleanup_scheduler():
    """Stop the cleanup scheduler"""
    cleanup_scheduler.stop()
