from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Parse Neon database URL and convert to asyncpg format
def get_async_database_url():
    """Convert Neon database URL to asyncpg format"""
    if settings.database_url.startswith("postgresql://"):
        # Remove all query parameters for asyncpg
        base_url = settings.database_url.split("?")[0]
        return base_url
    return settings.database_url

# Create async engine for Neon database
engine = create_async_engine(
    get_async_database_url().replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=5,
    max_overflow=10,
    connect_args={
        "server_settings": {
            "application_name": "mindacuity_backend"
        }
    }
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

# For compatibility with existing sync code
def get_sync_db():
    """Legacy sync database session - use only for migration scripts"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    sync_engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=1800
    )
    SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
    
    db = SyncSessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database error: {e}")
        db.rollback()
        raise
    finally:
        db.close() 