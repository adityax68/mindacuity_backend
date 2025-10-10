from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from app.database import get_db
from app.auth import get_current_active_user
from app.models import User
from app.schemas import (
    EmailVerificationRequest, EmailVerificationResponse,
    ResendVerificationRequest, ResendVerificationResponse,
    VerificationStatusResponse
)
from app.services.email_verification_service import email_verification_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["email-verification"])

def get_client_ip(request: Request) -> str:
    """Get client IP address"""
    # Check for forwarded headers (for reverse proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection
    return request.client.host if request.client else "unknown"

@router.post("/verify-email", response_model=EmailVerificationResponse)
async def verify_email(
    request: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """
    Verify email address with verification token (POST endpoint for API calls)
    
    - **token**: Email verification token from the verification email
    """
    try:
        success, message = await email_verification_service.verify_email(
            token=request.token,
            db=db
        )
        
        if success:
            return EmailVerificationResponse(
                success=True,
                message=message,
                verified=True
            )
        else:
            return EmailVerificationResponse(
                success=False,
                message=message,
                verified=False
            )
            
    except Exception as e:
        logger.error(f"Error in verify_email endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during email verification"
        )

@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email_get(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Verify email address with verification token (GET endpoint for email links)
    
    - **token**: Email verification token from the verification email
    """
    try:
        success, message = await email_verification_service.verify_email(
            token=token,
            db=db
        )
        
        if success:
            # Return a success HTML page
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Email Verified - MindAcuity</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f5f5f5; }}
                    .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .success {{ color: #28a745; font-size: 24px; margin-bottom: 20px; }}
                    .message {{ color: #333; font-size: 16px; margin-bottom: 30px; }}
                    .button {{ background-color: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="success">✅ Email Verified Successfully!</div>
                    <div class="message">{message}</div>
                    <a href="https://mindacuity.ai/login" class="button">Go to Login</a>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content)
        else:
            # Return an error HTML page
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Verification Failed - MindAcuity</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f5f5f5; }}
                    .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .error {{ color: #dc3545; font-size: 24px; margin-bottom: 20px; }}
                    .message {{ color: #333; font-size: 16px; margin-bottom: 30px; }}
                    .button {{ background-color: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="error">❌ Verification Failed</div>
                    <div class="message">{message}</div>
                    <a href="https://mindacuity.ai/login" class="button">Go to Login</a>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content)
            
    except Exception as e:
        logger.error(f"Error in verify_email_get endpoint: {e}")
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Verification Error - MindAcuity</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background-color: #f5f5f5; }}
                .container {{ max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .error {{ color: #dc3545; font-size: 24px; margin-bottom: 20px; }}
                .message {{ color: #333; font-size: 16px; margin-bottom: 30px; }}
                .button {{ background-color: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error">❌ Verification Error</div>
                <div class="message">An internal error occurred during verification. Please try again later.</div>
                <a href="https://mindacuity.ai/login" class="button">Go to Login</a>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

@router.post("/resend-verification", response_model=ResendVerificationResponse)
async def resend_verification(
    request: ResendVerificationRequest,
    client_ip: str = Depends(get_client_ip),
    db: Session = Depends(get_db)
):
    """
    Resend verification email
    
    - **email**: Email address to resend verification to
    """
    try:
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if already verified
        if user.is_verified:
            return ResendVerificationResponse(
                success=True,
                message="Email is already verified",
                attempts_remaining=None,
                retry_after=None
            )
        
        # Check rate limits
        can_send, message, retry_after = await email_verification_service.can_send_verification(
            request.email, db
        )
        
        if not can_send:
            return ResendVerificationResponse(
                success=False,
                message=message,
                attempts_remaining=None,
                retry_after=retry_after
            )
        
        # Send verification email
        success, send_message = await email_verification_service.send_verification_email(
            user=user,
            db=db
        )
        
        if success:
            # Calculate remaining attempts
            remaining_attempts = max(0, 3 - user.email_verification_attempts)
            
            return ResendVerificationResponse(
                success=True,
                message=send_message,
                attempts_remaining=remaining_attempts,
                retry_after=None
            )
        else:
            return ResendVerificationResponse(
                success=False,
                message=send_message,
                attempts_remaining=None,
                retry_after=None
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in resend_verification endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during verification resend"
        )

@router.get("/verification-status/{email}", response_model=VerificationStatusResponse)
async def get_verification_status(
    email: str,
    db: Session = Depends(get_db)
):
    """
    Get verification status for an email address
    
    - **email**: Email address to check verification status for
    """
    try:
        status_data = await email_verification_service.get_verification_status(email, db)
        
        if "error" in status_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=status_data["error"]
            )
        
        return VerificationStatusResponse(**status_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_verification_status endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error getting verification status"
        )

@router.get("/my-verification-status", response_model=VerificationStatusResponse)
async def get_my_verification_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get verification status for the current authenticated user
    """
    try:
        status_data = await email_verification_service.get_verification_status(
            current_user.email, db
        )
        
        if "error" in status_data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=status_data["error"]
            )
        
        return VerificationStatusResponse(**status_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_my_verification_status endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error getting verification status"
        )
