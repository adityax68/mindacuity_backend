"""
Email utility functions for common email operations
"""
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services.email_service import EmailService
from app.database import get_db

logger = logging.getLogger(__name__)

class EmailUtils:
    """Utility class for common email operations"""
    
    def __init__(self):
        self.email_service = EmailService()
    
    async def send_welcome_email(
        self,
        user_email: str,
        user_name: str,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Send welcome email to new user"""
        try:
            subject = "Welcome to Health App!"
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50;">Welcome to Health App!</h1>
                <p>Hello {user_name},</p>
                <p>Thank you for joining Health App! We're excited to have you on board.</p>
                <p>Your account has been successfully created and you can now access all our features.</p>
                <p>If you have any questions, feel free to reach out to our support team.</p>
                <br>
                <p>Best regards,<br>The Health App Team</p>
            </body>
            </html>
            """
            
            text_content = f"""
            Welcome to Health App!
            
            Hello {user_name},
            
            Thank you for joining Health App! We're excited to have you on board.
            
            Your account has been successfully created and you can now access all our features.
            
            If you have any questions, feel free to reach out to our support team.
            
            Best regards,
            The Health App Team
            """
            
            result = await self.email_service.send_email(
                to_emails=[user_email],
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                template_name="welcome_email",
                template_data={"user_name": user_name, "app_name": "Health App"},
                db=db
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending welcome email: {e}")
            return {"status": "failed", "error_message": str(e)}
    
    async def send_password_reset_email(
        self,
        user_email: str,
        reset_token: str,
        user_name: str,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Send password reset email"""
        try:
            # In production, you'd use your actual domain
            reset_url = f"https://yourdomain.com/reset-password?token={reset_token}"
            
            subject = "Reset Your Password - Health App"
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50;">Password Reset Request</h1>
                <p>Hello {user_name},</p>
                <p>We received a request to reset your password for your Health App account.</p>
                <p>Click the button below to reset your password:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" style="background-color: #3498db; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Reset Password</a>
                </div>
                <p>If the button doesn't work, copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #3498db;">{reset_url}</p>
                <p><strong>This link will expire in 1 hour.</strong></p>
                <p>If you didn't request this password reset, please ignore this email.</p>
                <br>
                <p>Best regards,<br>The Health App Team</p>
            </body>
            </html>
            """
            
            text_content = f"""
            Password Reset Request
            
            Hello {user_name},
            
            We received a request to reset your password for your Health App account.
            
            Click the link below to reset your password:
            {reset_url}
            
            This link will expire in 1 hour.
            
            If you didn't request this password reset, please ignore this email.
            
            Best regards,
            The Health App Team
            """
            
            result = await self.email_service.send_email(
                to_emails=[user_email],
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                template_name="password_reset",
                template_data={"user_name": user_name, "reset_url": reset_url},
                db=db
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending password reset email: {e}")
            return {"status": "failed", "error_message": str(e)}
    
    async def send_employee_access_notification(
        self,
        hr_email: str,
        employee_name: str,
        employee_email: str,
        employee_code: str,
        org_name: str,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Send notification to HR about employee access request"""
        try:
            subject = f"Employee Access Request - {employee_name}"
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50;">Employee Access Request</h1>
                <p>Hello HR Team,</p>
                <p>A new employee has requested access to Health App:</p>
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Employee Name:</strong> {employee_name}</p>
                    <p><strong>Employee Email:</strong> {employee_email}</p>
                    <p><strong>Employee Code:</strong> {employee_code}</p>
                    <p><strong>Organization:</strong> {org_name}</p>
                </div>
                <p>Please review and approve this request in the admin panel.</p>
                <br>
                <p>Best regards,<br>The Health App Team</p>
            </body>
            </html>
            """
            
            text_content = f"""
            Employee Access Request
            
            Hello HR Team,
            
            A new employee has requested access to Health App:
            
            Employee Name: {employee_name}
            Employee Email: {employee_email}
            Employee Code: {employee_code}
            Organization: {org_name}
            
            Please review and approve this request in the admin panel.
            
            Best regards,
            The Health App Team
            """
            
            result = await self.email_service.send_email(
                to_emails=[hr_email],
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                template_name="employee_access_request",
                template_data={
                    "employee_name": employee_name,
                    "employee_email": employee_email,
                    "employee_code": employee_code,
                    "org_name": org_name
                },
                db=db
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending employee access notification: {e}")
            return {"status": "failed", "error_message": str(e)}
    
    async def send_subscription_confirmation(
        self,
        user_email: str,
        user_name: str,
        plan_type: str,
        access_code: str,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Send subscription confirmation email"""
        try:
            subject = f"Subscription Confirmed - {plan_type.title()} Plan"
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #2c3e50;">Subscription Confirmed!</h1>
                <p>Hello {user_name},</p>
                <p>Your subscription to the <strong>{plan_type.title()}</strong> plan has been confirmed.</p>
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Plan:</strong> {plan_type.title()}</p>
                    <p><strong>Access Code:</strong> {access_code}</p>
                </div>
                <p>You can now access all the features included in your plan.</p>
                <p>If you have any questions, feel free to contact our support team.</p>
                <br>
                <p>Best regards,<br>The Health App Team</p>
            </body>
            </html>
            """
            
            text_content = f"""
            Subscription Confirmed!
            
            Hello {user_name},
            
            Your subscription to the {plan_type.title()} plan has been confirmed.
            
            Plan: {plan_type.title()}
            Access Code: {access_code}
            
            You can now access all the features included in your plan.
            
            If you have any questions, feel free to contact our support team.
            
            Best regards,
            The Health App Team
            """
            
            result = await self.email_service.send_email(
                to_emails=[user_email],
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                template_name="subscription_confirmation",
                template_data={
                    "user_name": user_name,
                    "plan_type": plan_type,
                    "access_code": access_code
                },
                db=db
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending subscription confirmation: {e}")
            return {"status": "failed", "error_message": str(e)}
    
    async def send_crisis_alert(
        self,
        support_emails: List[str],
        user_identifier: str,
        session_id: str,
        risk_level: str,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Send crisis alert to support team"""
        try:
            subject = f"URGENT: Crisis Alert - {risk_level} Risk Detected"
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h1 style="color: #e74c3c;">🚨 CRISIS ALERT 🚨</h1>
                <p><strong>Risk Level:</strong> {risk_level.upper()}</p>
                <div style="background-color: #fdf2f2; border: 2px solid #e74c3c; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>User Identifier:</strong> {user_identifier}</p>
                    <p><strong>Session ID:</strong> {session_id}</p>
                    <p><strong>Timestamp:</strong> {self._get_current_timestamp()}</p>
                </div>
                <p><strong>Action Required:</strong> Please review this case immediately and provide appropriate support.</p>
                <p>This alert was triggered by our AI system detecting potential crisis indicators.</p>
                <br>
                <p>Best regards,<br>Health App Crisis Detection System</p>
            </body>
            </html>
            """
            
            text_content = f"""
            CRISIS ALERT
            
            Risk Level: {risk_level.upper()}
            
            User Identifier: {user_identifier}
            Session ID: {session_id}
            Timestamp: {self._get_current_timestamp()}
            
            Action Required: Please review this case immediately and provide appropriate support.
            
            This alert was triggered by our AI system detecting potential crisis indicators.
            
            Best regards,
            Health App Crisis Detection System
            """
            
            result = await self.email_service.send_email(
                to_emails=support_emails,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                template_name="crisis_alert",
                template_data={
                    "user_identifier": user_identifier,
                    "session_id": session_id,
                    "risk_level": risk_level
                },
                db=db
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending crisis alert: {e}")
            return {"status": "failed", "error_message": str(e)}
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp as string"""
        from datetime import datetime
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

# Global instance for easy import
email_utils = EmailUtils()
