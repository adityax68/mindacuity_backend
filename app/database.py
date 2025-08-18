from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from app.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create engine with improved connection handling
engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=3,  # Reduced pool size for better stability
    max_overflow=5,  # Reduced max overflow
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=1800,   # Recycle connections every 30 minutes
    pool_timeout=30,     # Connection timeout
    connect_args={
        "connect_timeout": 10,
        "application_name": "health_app",
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    }
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