import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import engine
from app.models import Base
from app.routers import auth, clinical, admin, chat, user_auth

# Initialize FastAPI app
app = FastAPI(
    title=settings.project_name,
    description="A rule-based mental health detection API for anxiety, stress, and depression analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware - Configure for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
# New Organization/Employee authentication system
app.include_router(auth.router)  # No prefix needed as auth router has /api/auth prefix

# Original user authentication system (restored)
app.include_router(user_auth.router, prefix=settings.api_v1_prefix)  # This creates /api/v1/auth/*

# Other existing routers
app.include_router(clinical.router, prefix=settings.api_v1_prefix)
app.include_router(admin.router, prefix=settings.api_v1_prefix)
app.include_router(chat.router, prefix=settings.api_v1_prefix)

@app.on_event("startup")
async def startup_event():
    """Create database tables on startup"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Clinical Mental Health Assessment API",
        "version": "1.0.0",
        "description": "Clinical assessment using validated scales (PHQ-9, GAD-7, PSS-10)",
        "docs": "/docs",
        "redoc": "/redoc",
        "assessment_types": ["PHQ-9 (Depression)", "GAD-7 (Anxiety)", "PSS-10 (Stress)"],
        "new_features": ["Organization/Employee Authentication System"],
        "auth_systems": {
            "user_auth": "/api/v1/auth/* (Original user authentication)",
            "org_emp_auth": "/api/auth/* (New Organization/Employee authentication)"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "clinical-mental-health-api"}

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom exception handler for better error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler for unexpected errors."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if getattr(settings, 'debug', False) else "An unexpected error occurred"
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 