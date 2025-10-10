"""
Email Verification Service with Rate Limiting
"""
import secrets
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import User
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

class EmailVerificationService:
    """Service for handling email verification with rate limiting"""
    
    def __init__(self):
        self.email_service = EmailService()
        
        # Rate limiting configuration
        self.MAX_ATTEMPTS_PER_HOUR = 3
        self.MAX_ATTEMPTS_PER_DAY = 10
        self.COOLDOWN_MINUTES = 5
        self.TOKEN_EXPIRY_HOURS = 24
    
    def generate_verification_token(self) -> str:
        """Generate a secure verification token"""
        return secrets.token_urlsafe(32)
    
    def hash_token(self, token: str) -> str:
        """Hash token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    async def can_send_verification(self, email: str, db: Session) -> Tuple[bool, str, Optional[int]]:
        """
        Check if verification email can be sent based on rate limits
        
        Returns:
            (can_send: bool, message: str, retry_after_seconds: Optional[int])
        """
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                return False, "User not found", None
            
            now = datetime.now(timezone.utc)
            
            # Check cooldown period
            if user.last_verification_attempt:
                time_since_last = (now - user.last_verification_attempt).total_seconds()
                if time_since_last < (self.COOLDOWN_MINUTES * 60):
                    remaining = int((self.COOLDOWN_MINUTES * 60) - time_since_last)
                    return False, f"Please wait {self.COOLDOWN_MINUTES} minutes before requesting another verification email", remaining
            
            # Check hourly limit
            if user.email_verification_attempts >= self.MAX_ATTEMPTS_PER_HOUR:
                # Check if it's been more than 1 hour since first attempt
                if user.last_verification_attempt:
                    time_since_first = (now - user.last_verification_attempt).total_seconds()
                    if time_since_first < 3600:  # 1 hour
                        remaining = int(3600 - time_since_first)
                        return False, "Too many verification attempts. Please wait 1 hour", remaining
                    else:
                        # Reset attempts if more than 1 hour has passed
                        user.email_verification_attempts = 0
            
            # Check daily limit (simplified - in production, you'd want more sophisticated tracking)
            if user.email_verification_attempts >= self.MAX_ATTEMPTS_PER_DAY:
                return False, "Daily verification limit reached. Please try again tomorrow", None
            
            return True, "OK", None
            
        except Exception as e:
            logger.error(f"Error checking verification rate limit: {e}")
            return False, "Internal error checking rate limits", None
    
    async def send_verification_email(self, user: User, db: Session) -> Tuple[bool, str]:
        """
        Send verification email to user
        
        Returns:
            (success: bool, message: str)
        """
        try:
            # Check rate limits
            can_send, message, retry_after = await self.can_send_verification(user.email, db)
            if not can_send:
                return False, message
            
            # Generate new verification token
            token = self.generate_verification_token()
            
            # Set expiry time
            expires_at = datetime.now(timezone.utc) + timedelta(hours=self.TOKEN_EXPIRY_HOURS)
            
            # Update user with plain token (we'll hash during verification)
            user.email_verification_token = token
            user.email_verification_expires_at = expires_at
            user.email_verification_attempts += 1
            user.last_verification_attempt = datetime.now(timezone.utc)
            
            db.commit()
            
            # Create verification URL - point to backend API endpoint
            # Use environment variable for base URL, fallback to localhost for development
            import os
            base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
            verification_url = f"{base_url}/api/v1/auth/verify-email?token={token}"
            
            # Send verification email
            result = await self._send_verification_email_template(
                user_email=user.email,
                user_name=user.full_name or "User",
                verification_url=verification_url,
                token=token
            )
            
            if result.get("status") == "success":
                logger.info(f"Verification email sent successfully to {user.email}")
                return True, "Verification email sent successfully"
            else:
                logger.error(f"Failed to send verification email to {user.email}: {result.get('error_message')}")
                return False, "Failed to send verification email"
                
        except Exception as e:
            logger.error(f"Error sending verification email: {e}")
            db.rollback()
            return False, "Internal error sending verification email"
    
    async def _send_verification_email_template(
        self, 
        user_email: str, 
        user_name: str, 
        verification_url: str,
        token: str
    ) -> dict:
        """Send verification email using template"""
        
        subject = "Verify your MindAcuity account"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Verify your MindAcuity account</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; border-radius: 10px; text-align: center; margin-bottom: 30px;">
                <h1 style="color: white; margin: 0; font-size: 28px;">Welcome to MindAcuity</h1>
                <p style="color: white; margin: 10px 0 0 0; font-size: 16px;">Your Mental Health Companion</p>
            </div>
            
            <div style="background: #f8f9fa; padding: 30px; border-radius: 10px; margin-bottom: 30px;">
                <h2 style="color: #2c3e50; margin-top: 0;">Hello {user_name}!</h2>
                <p style="font-size: 16px; margin-bottom: 20px;">
                    Thank you for joining MindAcuity! We're excited to have you on board for your mental health journey.
                </p>
                <p style="font-size: 16px; margin-bottom: 30px;">
                    To complete your registration and start using our services, please verify your email address by clicking the button below:
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_url}" 
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; 
                              padding: 15px 30px; 
                              text-decoration: none; 
                              border-radius: 25px; 
                              display: inline-block; 
                              font-weight: bold; 
                              font-size: 16px;
                              box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);">
                        Verify My Account
                    </a>
                </div>
                
                <p style="font-size: 14px; color: #666; margin-top: 30px;">
                    If the button doesn't work, copy and paste this link into your browser:<br>
                    <a href="{verification_url}" style="color: #667eea; word-break: break-all;">{verification_url}</a>
                </p>
            </div>
            
            <div style="background: #e8f4f8; padding: 20px; border-radius: 10px; margin-bottom: 30px;">
                <h3 style="color: #2c3e50; margin-top: 0;">What's Next?</h3>
                <ul style="color: #555; padding-left: 20px;">
                    <li>Complete your mental health assessment</li>
                    <li>Access our AI-powered chat support</li>
                    <li>Track your mental wellness journey</li>
                    <li>Connect with our support community</li>
                </ul>
            </div>
            
            <div style="background: #fff3cd; padding: 20px; border-radius: 10px; border-left: 4px solid #ffc107;">
                <p style="margin: 0; color: #856404; font-size: 14px;">
                    <strong>Important:</strong> This verification link will expire in 24 hours. 
                    If you don't verify your account within this time, you'll need to request a new verification email.
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee;">
                <p style="color: #666; font-size: 14px; margin: 0;">
                    If you didn't create an account with MindAcuity, please ignore this email.
                </p>
                <p style="color: #666; font-size: 14px; margin: 10px 0 0 0;">
                    Need help? Contact us at <a href="mailto:support@mindacuity.ai" style="color: #667eea;">support@mindacuity.ai</a>
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 20px;">
                <p style="color: #999; font-size: 12px;">
                    © 2024 MindAcuity. All rights reserved.<br>
                    This email was sent to {user_email}
                </p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to MindAcuity!
        
        Hello {user_name},
        
        Thank you for joining MindAcuity! We're excited to have you on board for your mental health journey.
        
        To complete your registration and start using our services, please verify your email address by clicking the link below:
        
        {verification_url}
        
        What's Next?
        - Complete your mental health assessment
        - Access our AI-powered chat support
        - Track your mental wellness journey
        - Connect with our support community
        
        Important: This verification link will expire in 24 hours. If you don't verify your account within this time, you'll need to request a new verification email.
        
        If you didn't create an account with MindAcuity, please ignore this email.
        
        Need help? Contact us at support@mindacuity.ai
        
        © 2024 MindAcuity. All rights reserved.
        This email was sent to {user_email}
        """
        
        return await self.email_service.send_email(
            to_emails=[user_email],
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            template_name="email_verification",
            template_data={
                "user_name": user_name,
                "verification_url": verification_url,
                "token": token
            }
        )
    
    async def verify_email(self, token: str, db: Session) -> Tuple[bool, str]:
        """
        Verify email with token
        
        Returns:
            (success: bool, message: str)
        """
        try:
            # Find user with valid token (compare hashed tokens)
            user = db.query(User).filter(
                and_(
                    User.email_verification_token == token,  # Direct comparison with plain token
                    User.email_verification_expires_at > datetime.now(timezone.utc),
                    User.is_verified == False
                )
            ).first()
            
            if not user:
                return False, "Invalid or expired verification token"
            
            # Mark email as verified
            user.is_verified = True
            user.email_verification_token = None  # Clear token
            user.email_verification_expires_at = None  # Clear expiry
            user.email_verification_attempts = 0  # Reset attempts
            
            db.commit()
            
            logger.info(f"Email verified successfully for user: {user.email}")
            
            return True, "Email verified successfully! You can now login."
            
        except Exception as e:
            logger.error(f"Error verifying email: {e}")
            db.rollback()
            return False, "Internal error verifying email"
    
    async def get_verification_status(self, email: str, db: Session) -> dict:
        """Get verification status for user"""
        try:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                return {"error": "User not found"}
            
            now = datetime.now(timezone.utc)
            can_resend = True
            retry_after = None
            
            # Check if user can resend
            if user.last_verification_attempt:
                time_since_last = (now - user.last_verification_attempt).total_seconds()
                if time_since_last < (self.COOLDOWN_MINUTES * 60):
                    can_resend = False
                    retry_after = int((self.COOLDOWN_MINUTES * 60) - time_since_last)
                elif user.email_verification_attempts >= self.MAX_ATTEMPTS_PER_HOUR:
                    can_resend = False
                    retry_after = int(3600 - time_since_last) if time_since_last < 3600 else 0
            
            return {
                "email": user.email,
                "is_verified": user.is_verified,
                "verification_attempts": user.email_verification_attempts,
                "last_attempt": user.last_verification_attempt,
                "can_resend": can_resend,
                "retry_after": retry_after
            }
            
        except Exception as e:
            logger.error(f"Error getting verification status: {e}")
            return {"error": "Internal error getting verification status"}

# Global instance
email_verification_service = EmailVerificationService()
