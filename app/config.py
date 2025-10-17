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
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    token_refresh_threshold_minutes: int = int(os.getenv("TOKEN_REFRESH_THRESHOLD_MINUTES", "5"))
    
    # API settings - Now using environment variables
    api_v1_prefix: str = os.getenv("API_V1_PREFIX", "/api/v1")
    project_name: str = os.getenv("PROJECT_NAME", "Health App - Mental Health Detection API")
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # OpenAI Configuration
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # Anthropic Configuration
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Redis Configuration
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Encryption Configuration
    encryption_key: str = os.getenv("ENCRYPTION_KEY", "")
    
    # Environment Configuration
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    # AWS S3 Configuration
    aws_access_key_id: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    aws_secret_access_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    s3_bucket_name: str = os.getenv("S3_BUCKET_NAME", "")
    s3_base_url: str = os.getenv("S3_BASE_URL", "")
    
    # AWS SES Configuration
    ses_from_email: str = os.getenv("SES_FROM_EMAIL", "noreply@mindacuity.ai")
    ses_from_name: str = os.getenv("SES_FROM_NAME", "MindAcuity")
    ses_reply_to: str = os.getenv("SES_REPLY_TO", "support@mindacuity.ai")
    ses_configuration_set: str = os.getenv("SES_CONFIGURATION_SET", "")
    ses_bounce_topic_arn: str = os.getenv("SES_BOUNCE_TOPIC_ARN", "")
    ses_complaint_topic_arn: str = os.getenv("SES_COMPLAINT_TOPIC_ARN", "")
    ses_delivery_topic_arn: str = os.getenv("SES_DELIVERY_TOPIC_ARN", "")
    
    # Google OAuth Configuration
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_android_client_id: str = os.getenv("GOOGLE_ANDROID_CLIENT_ID", "")
    google_ios_client_id: str = os.getenv("GOOGLE_IOS_CLIENT_ID", "")
    
    # Frontend URL Configuration
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields from .env file

settings = Settings() 