import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging first
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logging_config import setup_logging
setup_logging()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import engine
from app.models import Base
from app.routers import auth, clinical, admin, access, hr, complaints, tests, session_chat, researches

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
        "https://localhost:5173",         # HTTPS for Google OAuth
        "https://127.0.0.1:5173",        # HTTPS for Google OAuth
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

# Add custom middleware to handle Cross-Origin-Opener-Policy and logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import time

logger = logging.getLogger(__name__)

class COOPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log incoming request
        start_time = time.time()
        logger.info(f"=== INCOMING REQUEST ===")
        logger.info(f"Method: {request.method}")
        logger.info(f"URL: {request.url}")
        logger.info(f"Path: {request.url.path}")
        logger.info(f"Query params: {dict(request.query_params)}")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info(f"Client IP: {request.client.host if request.client else 'Unknown'}")
        
        # Special logging for Google OAuth endpoint
        if request.url.path == "/api/v1/auth/google":
            logger.info("*** GOOGLE OAUTH ENDPOINT HIT ***")
            if request.method == "POST":
                try:
                    # Try to read the body for logging (but don't consume it)
                    body = await request.body()
                    logger.info(f"Request body size: {len(body)} bytes")
                    if body:
                        logger.info(f"Request body preview: {body[:200]}...")
                except Exception as e:
                    logger.warning(f"Could not read request body: {e}")
        
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(f"=== RESPONSE ===")
        logger.info(f"Status: {response.status_code}")
        logger.info(f"Process time: {process_time:.3f}s")
        logger.info(f"Response headers: {dict(response.headers)}")
        
        # Set Cross-Origin-Opener-Policy to allow Google OAuth popups
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin-allow-popups"
        response.headers["Cross-Origin-Embedder-Policy"] = "unsafe-none"
        
        return response

app.add_middleware(COOPMiddleware)

# Include routers
app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(clinical.router, prefix=settings.api_v1_prefix)
app.include_router(admin.router, prefix=settings.api_v1_prefix)
app.include_router(session_chat.router, prefix=settings.api_v1_prefix)
app.include_router(access.router, prefix=settings.api_v1_prefix)
app.include_router(hr.router, prefix=settings.api_v1_prefix)
app.include_router(complaints.router, prefix=settings.api_v1_prefix)
app.include_router(tests.router, prefix=settings.api_v1_prefix)
app.include_router(researches.router, prefix=settings.api_v1_prefix)


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