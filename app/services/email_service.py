import boto3
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from botocore.exceptions import ClientError, BotoCoreError
from sqlalchemy.orm import Session
from app.config import settings
from app.models import EmailLog, EmailUnsubscribe
from app.database import get_db

logger = logging.getLogger(__name__)

class EmailService:
    """AWS SES Email Service with production-ready features"""
    
    def __init__(self):
        self.aws_access_key_id = settings.aws_access_key_id
        self.aws_secret_access_key = settings.aws_secret_access_key
        self.aws_region = settings.aws_region
        self.from_email = settings.ses_from_email
        self.from_name = settings.ses_from_name
        self.reply_to = settings.ses_reply_to
        self.configuration_set = settings.ses_configuration_set
        
        if not all([self.aws_access_key_id, self.aws_secret_access_key, self.from_email]):
            raise ValueError("Missing required AWS SES environment variables")
        
        try:
            self.ses_client = boto3.client(
                'ses',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            )
            
            # Verify SES configuration
            self._verify_ses_setup()
            
        except Exception as e:
            logger.error(f"Failed to initialize SES client: {e}")
            raise
    
    def _verify_ses_setup(self):
        """Verify SES configuration and sender email"""
        try:
            # Check if sender email is verified
            response = self.ses_client.get_identity_verification_attributes(
                Identities=[self.from_email]
            )
            
            verification_status = response.get('VerificationAttributes', {}).get(
                self.from_email, {}
            ).get('VerificationStatus')
            
            if verification_status != 'Success':
                logger.warning(f"Sender email {self.from_email} is not verified in SES")
            
            logger.info(f"SES client initialized successfully for region: {self.aws_region}")
            
        except ClientError as e:
            logger.error(f"SES verification failed: {e}")
            raise
    
    async def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        template_name: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Send email via AWS SES with tracking and error handling
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject line
            html_content: HTML email content
            text_content: Plain text email content (optional)
            template_name: Name of the email template (for tracking)
            template_data: Data used in template rendering
            db: Database session for logging
            
        Returns:
            Dict with sending results and message IDs
        """
        try:
            # Validate inputs
            if not to_emails or not subject or not html_content:
                raise ValueError("to_emails, subject, and html_content are required")
            
            # Check for unsubscribed emails
            if db:
                unsubscribed_emails = await self._get_unsubscribed_emails(db, to_emails)
                to_emails = [email for email in to_emails if email not in unsubscribed_emails]
                
                if not to_emails:
                    logger.info("All recipients have unsubscribed, skipping email send")
                    return {"status": "skipped", "reason": "all_unsubscribed"}
            
            # Prepare email message
            message = self._prepare_message(subject, html_content, text_content)
            
            # Prepare send_email parameters
            send_params = {
                'Source': f"{self.from_name} <{self.from_email}>",
                'Destination': {'ToAddresses': to_emails},
                'Message': message,
                'ReplyToAddresses': [self.reply_to] if self.reply_to else [self.from_email]
            }
            
            # Only add ConfigurationSetName if it's set
            if self.configuration_set:
                send_params['ConfigurationSetName'] = self.configuration_set
            
            # Send email
            response = self.ses_client.send_email(**send_params)
            
            message_id = response['MessageId']
            
            # Log email send
            if db:
                await self._log_email_send(
                    db=db,
                    to_emails=to_emails,
                    subject=subject,
                    template_name=template_name,
                    message_id=message_id,
                    status="sent"
                )
            
            logger.info(f"Email sent successfully to {len(to_emails)} recipients. MessageId: {message_id}")
            
            return {
                "status": "success",
                "message_id": message_id,
                "recipients": len(to_emails),
                "to_emails": to_emails
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            logger.error(f"SES ClientError: {error_code} - {error_message}")
            
            # Log failed email
            if db:
                await self._log_email_send(
                    db=db,
                    to_emails=to_emails,
                    subject=subject,
                    template_name=template_name,
                    message_id=None,
                    status="failed",
                    error_message=error_message
                )
            
            return {
                "status": "failed",
                "error_code": error_code,
                "error_message": error_message
            }
            
        except Exception as e:
            logger.error(f"Unexpected error sending email: {e}")
            
            # Log failed email
            if db:
                await self._log_email_send(
                    db=db,
                    to_emails=to_emails,
                    subject=subject,
                    template_name=template_name,
                    message_id=None,
                    status="failed",
                    error_message=str(e)
                )
            
            return {
                "status": "failed",
                "error_message": str(e)
            }
    
    def _prepare_message(self, subject: str, html_content: str, text_content: Optional[str] = None) -> Dict:
        """Prepare email message for SES"""
        message = {
            'Subject': {
                'Data': subject,
                'Charset': 'UTF-8'
            },
            'Body': {
                'Html': {
                    'Data': html_content,
                    'Charset': 'UTF-8'
                }
            }
        }
        
        if text_content:
            message['Body']['Text'] = {
                'Data': text_content,
                'Charset': 'UTF-8'
            }
        
        return message
    
    async def _get_unsubscribed_emails(self, db: Session, emails: List[str]) -> List[str]:
        """Get list of unsubscribed emails"""
        try:
            unsubscribed = db.query(EmailUnsubscribe.email).filter(
                EmailUnsubscribe.email.in_(emails)
            ).all()
            return [email[0] for email in unsubscribed]
        except Exception as e:
            logger.error(f"Error checking unsubscribed emails: {e}")
            return []
    
    async def _log_email_send(
        self,
        db: Session,
        to_emails: List[str],
        subject: str,
        template_name: Optional[str],
        message_id: Optional[str],
        status: str,
        error_message: Optional[str] = None
    ):
        """Log email send attempt to database"""
        try:
            for email in to_emails:
                email_log = EmailLog(
                    recipient_email=email,
                    template_name=template_name or "custom",
                    subject=subject,
                    status=status,
                    message_id=message_id,
                    error_message=error_message,
                    sent_at=datetime.utcnow()
                )
                db.add(email_log)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error logging email send: {e}")
            db.rollback()
    
    async def handle_bounce(self, bounce_data: Dict[str, Any], db: Session):
        """Handle SES bounce notification"""
        try:
            message_id = bounce_data.get('mail', {}).get('messageId')
            bounce_type = bounce_data.get('bounce', {}).get('bounceType')
            bounce_subtype = bounce_data.get('bounce', {}).get('bounceSubType')
            
            # Get bounced email addresses
            bounced_recipients = bounce_data.get('bounce', {}).get('bouncedRecipients', [])
            
            for recipient in bounced_recipients:
                email = recipient.get('emailAddress')
                bounce_reason = recipient.get('diagnosticCode', '')
                
                # Update email log
                email_log = db.query(EmailLog).filter(
                    EmailLog.message_id == message_id,
                    EmailLog.recipient_email == email
                ).first()
                
                if email_log:
                    email_log.status = "bounced"
                    email_log.bounced_at = datetime.utcnow()
                    email_log.bounce_reason = bounce_reason
                    email_log.bounce_type = bounce_type
                    email_log.bounce_subtype = bounce_subtype
                
                # Add to unsubscribe list for permanent bounces
                if bounce_type == 'Permanent':
                    await self._add_to_unsubscribe_list(db, email, f"Permanent bounce: {bounce_reason}")
            
            db.commit()
            logger.info(f"Processed bounce for message {message_id}: {bounce_type}/{bounce_subtype}")
            
        except Exception as e:
            logger.error(f"Error handling bounce: {e}")
            db.rollback()
    
    async def handle_complaint(self, complaint_data: Dict[str, Any], db: Session):
        """Handle SES complaint notification"""
        try:
            message_id = complaint_data.get('mail', {}).get('messageId')
            
            # Get complained email addresses
            complained_recipients = complaint_data.get('complaint', {}).get('complainedRecipients', [])
            
            for recipient in complained_recipients:
                email = recipient.get('emailAddress')
                
                # Update email log
                email_log = db.query(EmailLog).filter(
                    EmailLog.message_id == message_id,
                    EmailLog.recipient_email == email
                ).first()
                
                if email_log:
                    email_log.status = "complained"
                    email_log.complained_at = datetime.utcnow()
                
                # Add to unsubscribe list
                await self._add_to_unsubscribe_list(db, email, "Spam complaint")
            
            db.commit()
            logger.info(f"Processed complaint for message {message_id}")
            
        except Exception as e:
            logger.error(f"Error handling complaint: {e}")
            db.rollback()
    
    async def handle_delivery(self, delivery_data: Dict[str, Any], db: Session):
        """Handle SES delivery notification"""
        try:
            message_id = delivery_data.get('mail', {}).get('messageId')
            
            # Get delivered email addresses
            delivered_recipients = delivery_data.get('delivery', {}).get('recipients', [])
            
            for email in delivered_recipients:
                # Update email log
                email_log = db.query(EmailLog).filter(
                    EmailLog.message_id == message_id,
                    EmailLog.recipient_email == email
                ).first()
                
                if email_log:
                    email_log.status = "delivered"
                    email_log.delivered_at = datetime.utcnow()
            
            db.commit()
            logger.info(f"Processed delivery for message {message_id}")
            
        except Exception as e:
            logger.error(f"Error handling delivery: {e}")
            db.rollback()
    
    async def _add_to_unsubscribe_list(self, db: Session, email: str, reason: str):
        """Add email to unsubscribe list"""
        try:
            # Check if already exists
            existing = db.query(EmailUnsubscribe).filter(
                EmailUnsubscribe.email == email
            ).first()
            
            if not existing:
                unsubscribe = EmailUnsubscribe(
                    email=email,
                    reason=reason,
                    unsubscribed_at=datetime.utcnow()
                )
                db.add(unsubscribe)
                logger.info(f"Added {email} to unsubscribe list: {reason}")
            
        except Exception as e:
            logger.error(f"Error adding to unsubscribe list: {e}")
    
    async def unsubscribe_email(self, email: str, reason: str = "User requested", db: Optional[Session] = None):
        """Manually unsubscribe an email address"""
        if not db:
            db = next(get_db())
        
        try:
            await self._add_to_unsubscribe_list(db, email, reason)
            db.commit()
            return {"status": "success", "message": f"Email {email} unsubscribed successfully"}
            
        except Exception as e:
            logger.error(f"Error unsubscribing email: {e}")
            db.rollback()
            return {"status": "error", "message": str(e)}
    
    async def get_email_stats(self, db: Session, days: int = 30) -> Dict[str, Any]:
        """Get email statistics for the last N days"""
        try:
            since_date = datetime.utcnow() - timedelta(days=days)
            
            # Get basic stats
            total_sent = db.query(EmailLog).filter(
                EmailLog.sent_at >= since_date
            ).count()
            
            total_delivered = db.query(EmailLog).filter(
                EmailLog.delivered_at >= since_date,
                EmailLog.status == "delivered"
            ).count()
            
            total_bounced = db.query(EmailLog).filter(
                EmailLog.bounced_at >= since_date,
                EmailLog.status == "bounced"
            ).count()
            
            total_complained = db.query(EmailLog).filter(
                EmailLog.complained_at >= since_date,
                EmailLog.status == "complained"
            ).count()
            
            # Calculate rates
            delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
            bounce_rate = (total_bounced / total_sent * 100) if total_sent > 0 else 0
            complaint_rate = (total_complained / total_sent * 100) if total_sent > 0 else 0
            
            return {
                "period_days": days,
                "total_sent": total_sent,
                "total_delivered": total_delivered,
                "total_bounced": total_bounced,
                "total_complained": total_complained,
                "delivery_rate": round(delivery_rate, 2),
                "bounce_rate": round(bounce_rate, 2),
                "complaint_rate": round(complaint_rate, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting email stats: {e}")
            return {"error": str(e)}
