import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ChatAttachment

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileCleanupService:
    """Service for cleaning up expired chat attachments"""
    
    def __init__(self):
        self.temp_dir = Path(os.path.join(os.path.dirname(__file__), "../../temp_uploads"))
        self.temp_dir.mkdir(exist_ok=True)
    
    def cleanup_expired_files(self, db: Session) -> int:
        """Clean up expired files and their database records"""
        try:
            # Find expired attachments
            expired_attachments = db.query(ChatAttachment).filter(
                ChatAttachment.expires_at < datetime.utcnow()
            ).all()
            
            cleaned_count = 0
            
            for attachment in expired_attachments:
                try:
                    # Delete physical file if it exists
                    file_path = Path(attachment.file_path)
                    if file_path.exists():
                        file_path.unlink()
                        logger.info(f"Deleted expired file: {file_path}")
                    
                    # Delete database record
                    db.delete(attachment)
                    cleaned_count += 1
                    
                except Exception as e:
                    logger.error(f"Error cleaning up attachment {attachment.id}: {e}")
                    # Still delete the database record even if file deletion fails
                    db.delete(attachment)
                    cleaned_count += 1
            
            db.commit()
            logger.info(f"Cleaned up {cleaned_count} expired attachments")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during file cleanup: {e}")
            db.rollback()
            return 0
    
    def cleanup_orphaned_files(self, db: Session) -> int:
        """Clean up files that exist on disk but not in database"""
        try:
            # Get all file paths from database
            db_files = set()
            attachments = db.query(ChatAttachment).all()
            for attachment in attachments:
                if attachment.file_path:
                    db_files.add(Path(attachment.file_path))
            
            # Find files in temp directory that aren't in database
            orphaned_count = 0
            if self.temp_dir.exists():
                for file_path in self.temp_dir.iterdir():
                    if file_path.is_file() and file_path not in db_files:
                        try:
                            file_path.unlink()
                            logger.info(f"Deleted orphaned file: {file_path}")
                            orphaned_count += 1
                        except Exception as e:
                            logger.error(f"Error deleting orphaned file {file_path}: {e}")
            
            logger.info(f"Cleaned up {orphaned_count} orphaned files")
            return orphaned_count
            
        except Exception as e:
            logger.error(f"Error during orphaned file cleanup: {e}")
            return 0
    
    def get_storage_stats(self, db: Session) -> dict:
        """Get storage statistics"""
        try:
            total_attachments = db.query(ChatAttachment).count()
            total_size = db.query(ChatAttachment).with_entities(
                db.func.sum(ChatAttachment.file_size)
            ).scalar() or 0
            
            expired_count = db.query(ChatAttachment).filter(
                ChatAttachment.expires_at < datetime.utcnow()
            ).count()
            
            return {
                "total_attachments": total_attachments,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "expired_count": expired_count,
                "temp_directory": str(self.temp_dir)
            }
            
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {}
    
    def force_cleanup_all(self, db: Session) -> int:
        """Force cleanup of all attachments (use with caution)"""
        try:
            attachments = db.query(ChatAttachment).all()
            cleaned_count = 0
            
            for attachment in attachments:
                try:
                    # Delete physical file
                    file_path = Path(attachment.file_path)
                    if file_path.exists():
                        file_path.unlink()
                    
                    # Delete database record
                    db.delete(attachment)
                    cleaned_count += 1
                    
                except Exception as e:
                    logger.error(f"Error force cleaning attachment {attachment.id}: {e}")
            
            db.commit()
            logger.warning(f"Force cleaned up {cleaned_count} attachments")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during force cleanup: {e}")
            db.rollback()
            return 0

# Global cleanup service instance
cleanup_service = FileCleanupService()

def run_cleanup_task():
    """Run cleanup task - can be called from a scheduler"""
    try:
        db = next(get_db())
        expired_count = cleanup_service.cleanup_expired_files(db)
        orphaned_count = cleanup_service.cleanup_orphaned_files(db)
        
        logger.info(f"Cleanup task completed: {expired_count} expired, {orphaned_count} orphaned files cleaned")
        return {"expired": expired_count, "orphaned": orphaned_count}
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        return {"error": str(e)}
    finally:
        db.close()
