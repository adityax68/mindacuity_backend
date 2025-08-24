from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Database settings - Now using environment variables
    database_url: str = os.getenv("DATABASE_URL", "postgresql://localhost/health_app")
    
    # JWT settings - Now using environment variables
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # API settings - Now using environment variables
    api_v1_prefix: str = os.getenv("API_V1_PREFIX", "/api/v1")
    project_name: str = os.getenv("PROJECT_NAME", "Health App - Mental Health Detection API")
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # OpenAI Configuration
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Encryption Configuration
    encryption_key: str = os.getenv("ENCRYPTION_KEY", "")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings() 