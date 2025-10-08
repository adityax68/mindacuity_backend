import logging
import sys
from datetime import datetime

def setup_logging():
    """Setup comprehensive logging configuration for the application"""
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Create file handler for all logs
    file_handler = logging.FileHandler('app.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Create file handler specifically for Google OAuth logs
    google_oauth_handler = logging.FileHandler('google_oauth.log')
    google_oauth_handler.setLevel(logging.DEBUG)
    google_oauth_handler.setFormatter(formatter)
    
    # Create file handler for errors
    error_handler = logging.FileHandler('errors.log')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    # Configure specific loggers
    # Google OAuth specific logging
    google_oauth_logger = logging.getLogger('app.routers.auth')
    google_oauth_logger.addHandler(google_oauth_handler)
    google_oauth_logger.setLevel(logging.DEBUG)
    
    google_service_logger = logging.getLogger('app.services.google_oauth_service')
    google_service_logger.addHandler(google_oauth_handler)
    google_service_logger.setLevel(logging.DEBUG)
    
    # Main app logging
    main_logger = logging.getLogger('app.main')
    main_logger.addHandler(google_oauth_handler)
    main_logger.setLevel(logging.DEBUG)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("LOGGING SYSTEM INITIALIZED")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("Log files:")
    logger.info("  - app.log: All application logs")
    logger.info("  - google_oauth.log: Google OAuth specific logs")
    logger.info("  - errors.log: Error logs only")
    logger.info("=" * 80)

if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Logging configuration test successful")
