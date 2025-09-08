import asyncio
import logging
from datetime import datetime, timedelta
from app.services.file_cleanup_service import run_cleanup_task

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
                result = run_cleanup_task()
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
