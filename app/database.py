from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from app.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OPTIMIZED: Create engine with highly optimized connection handling
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=10,  # Increased pool size for better performance
    max_overflow=20,  # Increased max overflow for high traffic
    pool_pre_ping=False,  # Disabled pre-ping to eliminate 1.5s delay
    pool_recycle=1800,   # Recycle connections every 30 minutes (better than 1 hour)
    pool_timeout=5,      # Reduced connection timeout for faster failures
    connect_args={
        "connect_timeout": 3,  # Reduced connection timeout for faster failures
        "application_name": "health_app"
    },
    # Additional performance optimizations
    echo=False,  # Disable SQL logging in production
    future=True,  # Use SQLAlchemy 2.0 style
    query_cache_size=1200,  # Cache query plans
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close() 