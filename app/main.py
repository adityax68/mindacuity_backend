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
from app.routers import auth, clinical, admin, access, hr, complaints, tests, session_chat

# Create database tables done
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title=settings.project_name,
    description="A rule-based mental health detection API for anxiety, stress, and depression analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
# In development, be more permissive for React Native
if os.getenv("ENVIRONMENT") == "production":
    # Production: strict CORS
    allowed_origins = [
        "https://mindacuity.ai",
        "https://www.mindacuity.ai",
    ]
else:
    # Development: allow web and mobile development
    allowed_origins = [
        "https://mindacuity.ai",
        "https://www.mindacuity.ai",
        "http://localhost:3000",          # React web dev
        "http://localhost:5173",          # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        # React Native development
        "*"  # Allow all origins in development only
    ]

# Debug CORS configuration
print(f"CORS allowed origins: {allowed_origins}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(clinical.router, prefix=settings.api_v1_prefix)
app.include_router(admin.router, prefix=settings.api_v1_prefix)
app.include_router(session_chat.router, prefix=settings.api_v1_prefix)
app.include_router(access.router, prefix=settings.api_v1_prefix)
app.include_router(hr.router, prefix=settings.api_v1_prefix)
app.include_router(complaints.router, prefix=settings.api_v1_prefix)
app.include_router(tests.router, prefix=settings.api_v1_prefix)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    print('api working')
    return {
        "message": "Clinical Mental Health Assessment API",
        "version": "1.0.0",
        "description": "Clinical assessment using validated scales (PHQ-9, GAD-7, PSS-10)",
        "docs": "/docs",
        "redoc": "/redoc",
        "assessment_types": ["PHQ-9 (Depression)", "GAD-7 (Anxiety)", "PSS-10 (Stress)"]
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