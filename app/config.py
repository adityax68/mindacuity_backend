from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database settings
    database_url: str = "postgresql://neondb_owner:npg_WlCV5sp4qwOe@ep-morning-dream-adq6ukxb-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    
    # JWT settings
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # API settings
    api_v1_prefix: str = "/api/v1"
    project_name: str = "Health App - Mental Health Detection API"
    debug: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings() 