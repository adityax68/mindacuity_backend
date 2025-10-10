from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
import json

from app.database import get_db
from app.auth import get_current_active_user
from app.models import User, EmailLog, EmailUnsubscribe, EmailTemplate, EmailBounce, EmailComplaint
from app.schemas import (
    EmailSendRequest, EmailSendResponse, EmailLogResponse, EmailUnsubscribeRequest,
    EmailUnsubscribeResponse, EmailUnsubscribeList, EmailTemplateCreate, EmailTemplateUpdate, EmailTemplateResponse,
    EmailBounceResponse, EmailComplaintResponse, EmailStatsResponse, SESNotificationRequest,
    EmailListRequest, EmailListResponse
)
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/email", tags=["email"])

# Initialize email service
email_service = EmailService()

@router.post("/send", response_model=EmailSendResponse)
async def send_email(
    email_request: EmailSendRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Send email via AWS SES
    
    - **to_emails**: List of recipient email addresses
    - **subject**: Email subject line
    - **html_content**: HTML email content
    - **text_content**: Plain text email content (optional)
    - **template_name**: Name of the email template (optional)
    - **template_data**: Data for template rendering (optional)
    """
    try:
        result = await email_service.send_email(
            to_emails=email_request.to_emails,
            subject=email_request.subject,
            html_content=email_request.html_content,
            text_content=email_request.text_content,
            template_name=email_request.template_name,
            template_data=email_request.template_data,
            db=db
        )
        
        return EmailSendResponse(**result)
        
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )

@router.get("/logs", response_model=EmailListResponse)
async def get_email_logs(
    request: EmailListRequest = Depends(),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get email logs with pagination and filtering
    
    - **page**: Page number (default: 1)
    - **limit**: Items per page (default: 50, max: 100)
    - **status**: Filter by email status (optional)
    - **template_name**: Filter by template name (optional)
    - **recipient_email**: Filter by recipient email (optional)
    """
    try:
        # Build query
        query = db.query(EmailLog)
        
        # Apply filters
        if request.status:
            query = query.filter(EmailLog.status == request.status.value)
        
        if request.template_name:
            query = query.filter(EmailLog.template_name == request.template_name)
        
        if request.recipient_email:
            query = query.filter(EmailLog.recipient_email.ilike(f"%{request.recipient_email}%"))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (request.page - 1) * request.limit
        logs = query.order_by(EmailLog.sent_at.desc()).offset(offset).limit(request.limit).all()
        
        # Calculate pages
        pages = (total + request.limit - 1) // request.limit
        
        return EmailListResponse(
            items=[EmailLogResponse.from_orm(log) for log in logs],
            total=total,
            page=request.page,
            limit=request.limit,
            pages=pages
        )
        
    except Exception as e:
        logger.error(f"Error getting email logs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get email logs: {str(e)}"
        )

@router.get("/stats", response_model=EmailStatsResponse)
async def get_email_stats(
    days: int = 30,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get email statistics for the last N days
    
    - **days**: Number of days to look back (default: 30)
    """
    try:
        stats = await email_service.get_email_stats(db, days)
        return EmailStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Error getting email stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get email stats: {str(e)}"
        )

@router.post("/unsubscribe", response_model=EmailUnsubscribeResponse)
async def unsubscribe_email(
    unsubscribe_request: EmailUnsubscribeRequest,
    db: Session = Depends(get_db)
):
    """
    Unsubscribe an email address from all emails
    
    - **email**: Email address to unsubscribe
    - **reason**: Reason for unsubscribing (optional)
    """
    try:
        result = await email_service.unsubscribe_email(
            email=unsubscribe_request.email,
            reason=unsubscribe_request.reason or "User requested",
            db=db
        )
        
        return EmailUnsubscribeResponse(**result)
        
    except Exception as e:
        logger.error(f"Error unsubscribing email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unsubscribe email: {str(e)}"
        )

@router.get("/unsubscribes", response_model=List[EmailUnsubscribeList])
async def get_unsubscribed_emails(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get list of unsubscribed email addresses (Admin only)
    """
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        unsubscribes = db.query(EmailUnsubscribe).order_by(EmailUnsubscribe.unsubscribed_at.desc()).all()
        return unsubscribes
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting unsubscribed emails: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get unsubscribed emails: {str(e)}"
        )

@router.get("/bounces", response_model=List[EmailBounceResponse])
async def get_email_bounces(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get email bounce records (Admin only)
    """
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        bounces = db.query(EmailBounce).order_by(EmailBounce.created_at.desc()).all()
        return [EmailBounceResponse.from_orm(bounce) for bounce in bounces]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting email bounces: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get email bounces: {str(e)}"
        )

@router.get("/complaints", response_model=List[EmailComplaintResponse])
async def get_email_complaints(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get email complaint records (Admin only)
    """
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        complaints = db.query(EmailComplaint).order_by(EmailComplaint.created_at.desc()).all()
        return [EmailComplaintResponse.from_orm(complaint) for complaint in complaints]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting email complaints: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get email complaints: {str(e)}"
        )

@router.post("/ses/webhook")
async def handle_ses_notification(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle SES bounce, complaint, and delivery notifications
    
    This endpoint receives webhooks from AWS SES for:
    - Bounce notifications
    - Complaint notifications  
    - Delivery notifications
    """
    try:
        # Parse the notification
        body = await request.body()
        notification_data = json.loads(body)
        
        notification_type = notification_data.get('notificationType')
        
        logger.info(f"Received SES notification: {notification_type}")
        
        if notification_type == 'Bounce':
            await email_service.handle_bounce(notification_data, db)
            
        elif notification_type == 'Complaint':
            await email_service.handle_complaint(notification_data, db)
            
        elif notification_type == 'Delivery':
            await email_service.handle_delivery(notification_data, db)
            
        else:
            logger.warning(f"Unknown notification type: {notification_type}")
            return JSONResponse(
                status_code=400,
                content={"error": f"Unknown notification type: {notification_type}"}
            )
        
        return JSONResponse(
            status_code=200,
            content={"status": "success", "message": f"Processed {notification_type} notification"}
        )
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in SES notification: {e}")
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid JSON"}
        )
        
    except Exception as e:
        logger.error(f"Error processing SES notification: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to process notification: {str(e)}"}
        )

@router.post("/templates", response_model=EmailTemplateResponse)
async def create_email_template(
    template_data: EmailTemplateCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new email template (Admin only)
    """
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        # Check if template name already exists
        existing = db.query(EmailTemplate).filter(EmailTemplate.name == template_data.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Template with name '{template_data.name}' already exists"
            )
        
        template = EmailTemplate(
            name=template_data.name,
            subject_template=template_data.subject_template,
            html_template=template_data.html_template,
            text_template=template_data.text_template,
            description=template_data.description,
            category=template_data.category
        )
        
        db.add(template)
        db.commit()
        db.refresh(template)
        
        return EmailTemplateResponse.from_orm(template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating email template: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create email template: {str(e)}"
        )

@router.get("/templates", response_model=List[EmailTemplateResponse])
async def get_email_templates(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all email templates
    """
    try:
        templates = db.query(EmailTemplate).order_by(EmailTemplate.name).all()
        return [EmailTemplateResponse.from_orm(template) for template in templates]
        
    except Exception as e:
        logger.error(f"Error getting email templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get email templates: {str(e)}"
        )

@router.put("/templates/{template_name}", response_model=EmailTemplateResponse)
async def update_email_template(
    template_name: str,
    template_data: EmailTemplateUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update an email template (Admin only)
    """
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        template = db.query(EmailTemplate).filter(EmailTemplate.name == template_name).first()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_name}' not found"
            )
        
        # Update fields
        if template_data.subject_template is not None:
            template.subject_template = template_data.subject_template
        if template_data.html_template is not None:
            template.html_template = template_data.html_template
        if template_data.text_template is not None:
            template.text_template = template_data.text_template
        if template_data.description is not None:
            template.description = template_data.description
        if template_data.category is not None:
            template.category = template_data.category
        if template_data.is_active is not None:
            template.is_active = template_data.is_active
        
        # Increment version
        template.version += 1
        
        db.commit()
        db.refresh(template)
        
        return EmailTemplateResponse.from_orm(template)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating email template: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update email template: {str(e)}"
        )

@router.delete("/templates/{template_name}")
async def delete_email_template(
    template_name: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete an email template (Admin only)
    """
    try:
        if current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )
        
        template = db.query(EmailTemplate).filter(EmailTemplate.name == template_name).first()
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_name}' not found"
            )
        
        db.delete(template)
        db.commit()
        
        return {"status": "success", "message": f"Template '{template_name}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting email template: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete email template: {str(e)}"
        )
