from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.clinical_assessments import AssessmentType, QuestionResponse, SeverityLevel

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None  # Optional for Google OAuth users
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=1, max_length=72, description="Password must be between 1 and 72 characters")
    role: Optional[str] = "user"  # NEW: Add role field
    # NEW: User profile fields
    age: int = Field(..., ge=1, le=120, description="Age must be between 1 and 120")
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None

# NEW: Google OAuth schemas
class GoogleOAuthRequest(BaseModel):
    google_token: str = Field(..., description="Google ID token from frontend")

class GoogleOAuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: "User"
    is_new_user: bool = False

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: int
    role: str  # NEW: Add role field
    privileges: List[str]  # NEW: Add privileges
    is_active: bool
    # NEW: User profile fields
    age: Optional[int] = None  # Optional for Google OAuth users
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    # NEW: Google OAuth fields
    google_id: Optional[str] = None
    auth_provider: str = "local"
    created_at: datetime
    
    class Config:
        from_attributes = True

# NEW: UserResponse for admin endpoints
class UserResponse(BaseModel):
    id: int
    email: str
    username: Optional[str] = None  # Optional for Google OAuth users
    full_name: Optional[str]
    role: str
    privileges: List[str]
    is_active: bool
    # NEW: User profile fields
    age: Optional[int] = None  # Optional for Google OAuth users
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# NEW: Role schemas
class RoleCreate(BaseModel):
    name: str
    description: str

class RoleResponse(BaseModel):
    id: int
    name: str
    description: str
    is_active: bool
    privileges: List[str]
    
    class Config:
        from_attributes = True

# NEW: Privilege schemas
class PrivilegeResponse(BaseModel):
    id: int
    name: str
    description: str
    category: str
    is_active: bool
    
    class Config:
        from_attributes = True

# NEW: User role update
class UserRoleUpdate(BaseModel):
    role: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    user: User

class TokenData(BaseModel):
    email: Optional[str] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenRevokeRequest(BaseModel):
    refresh_token: str

class TokenStatusResponse(BaseModel):
    is_valid: bool
    expires_at: Optional[datetime] = None
    user_id: Optional[int] = None

# New Test System Schemas
class TestDefinitionResponse(BaseModel):
    id: int
    test_code: str
    test_name: str
    test_category: str
    description: Optional[str]
    total_questions: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class TestQuestionOptionResponse(BaseModel):
    id: int
    option_text: str
    option_value: int
    weight: float
    display_order: int
    
    class Config:
        from_attributes = True

class TestQuestionResponse(BaseModel):
    id: int
    question_number: int
    question_text: str
    is_reverse_scored: bool
    options: List[TestQuestionOptionResponse]
    
    class Config:
        from_attributes = True

class TestScoringRangeResponse(BaseModel):
    id: int
    min_score: int
    max_score: int
    severity_level: str
    severity_label: str
    interpretation: str
    recommendations: Optional[str]
    color_code: Optional[str]
    priority: int
    
    class Config:
        from_attributes = True

class TestDetailsResponse(BaseModel):
    test_definition: TestDefinitionResponse
    questions: List[TestQuestionResponse]
    scoring_ranges: List[TestScoringRangeResponse]
    
    class Config:
        from_attributes = True

class TestAssessmentRequest(BaseModel):
    responses: List[Dict[str, Any]]  # [{"question_id": 1, "option_id": 2}, ...]

class TestAssessmentResponse(BaseModel):
    id: int
    user_id: int
    test_definition_id: int
    test_code: str
    test_name: str
    test_category: str
    calculated_score: int
    max_score: int
    severity_level: str
    severity_label: str
    interpretation: str
    recommendations: Optional[str]
    color_code: Optional[str]
    raw_responses: List[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True

# Clinical Assessment schemas (legacy)
class ClinicalAssessmentRequest(BaseModel):
    assessment_type: AssessmentType
    responses: List[QuestionResponse]

class ComprehensiveAssessmentRequest(BaseModel):
    responses: List[Dict[str, Any]]  # Simplified format for comprehensive assessment

class ComprehensiveAssessmentResponse(BaseModel):
    id: int
    user_id: int
    assessment_type: str
    assessment_name: str
    total_score: int
    max_score: int
    severity_level: str
    interpretation: str
    responses: List[Dict[str, Any]]
    created_at: datetime
    depression: Dict[str, Any]
    anxiety: Dict[str, Any]
    stress: Dict[str, Any]
    
    class Config:
        from_attributes = True

class ClinicalAssessmentResponse(BaseModel):
    id: int
    user_id: int
    assessment_type: str
    assessment_name: str
    total_score: int
    max_score: int
    severity_level: str
    interpretation: str
    responses: List[Dict]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ClinicalAssessmentSummary(BaseModel):
    total_assessments: int
    assessments: List[Dict]
    overall_risk_level: str
    recommendations: List[str]

class QuestionsResponse(BaseModel):
    assessment_type: AssessmentType
    questions: List[str]
    response_options: List[str]


# NEW: Session-based chat schemas

class SessionChatMessageRequest(BaseModel):
    message: str
    session_identifier: str

class SessionChatResponse(BaseModel):
    message: str
    conversation_id: str  # session_identifier
    requires_subscription: bool = False
    messages_used: int = 0
    message_limit: Optional[int] = None
    plan_type: str = "free"

class SubscriptionRequest(BaseModel):
    plan_type: str = Field(..., description="free, basic, or premium")

class SubscriptionResponse(BaseModel):
    subscription_token: str
    access_code: str
    plan_type: str
    message_limit: Optional[int]
    price: float
    expires_at: Optional[datetime] = None

class AccessCodeRequest(BaseModel):
    access_code: str

class AccessCodeResponse(BaseModel):
    success: bool
    message: str
    subscription_token: Optional[str] = None
    plan_type: Optional[str] = None
    message_limit: Optional[int] = None

class SessionMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class SessionConversationResponse(BaseModel):
    session_identifier: str
    title: str
    created_at: datetime
    messages: List[SessionMessageResponse]
    usage_info: Dict[str, Any]
    
    class Config:
        from_attributes = True

# Organisation schemas
class OrganisationCreate(BaseModel):
    org_name: str = Field(..., min_length=1, max_length=255)
    hr_email: EmailStr

class OrganisationResponse(BaseModel):
    id: int
    org_id: str
    org_name: str
    hr_email: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class EmployeeCreate(BaseModel):
    employee_code: str
    org_id: str
    hr_email: str

class Employee(EmployeeCreate):
    id: int
    user_id: int
    full_name: str
    email: str
    department: Optional[str] = None
    position: Optional[str] = None
    hire_date: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Complaint schemas
class ComplaintCreate(BaseModel):
    complaint_text: str
    share_employee_id: bool = True  # Default to sharing employee ID

class ComplaintUpdate(BaseModel):
    status: str
    hr_notes: Optional[str] = None

class Complaint(BaseModel):
    id: int
    user_id: int
    employee_id: Optional[int] = None  # Optional for anonymous complaints
    complaint_text: str
    status: str
    hr_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Research schemas
class ResearchCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    source_url: str = Field(..., min_length=1, max_length=500)
    thumbnail_url: str = Field(..., min_length=1, max_length=500)

class ResearchUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    source_url: Optional[str] = Field(None, min_length=1, max_length=500)
    thumbnail_url: Optional[str] = Field(None, min_length=1, max_length=500)
    is_active: Optional[bool] = None

class Research(BaseModel):
    id: int
    title: str
    description: str
    thumbnail_url: str
    source_url: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ResearchListResponse(BaseModel):
    researches: List[Research]
    total: int
    page: int
    per_page: int
    total_pages: int

# Bulk Employee Access schemas
class BulkEmployeeData(BaseModel):
    email: str  # REQUIRED
    employee_code: str  # REQUIRED
    full_name: str  # REQUIRED
    age: int = Field(default=25, ge=1, le=120, description="Age must be between 1 and 120")  # REQUIRED with default
    department: Optional[str] = None
    position: Optional[str] = None
    hire_date: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None

class BulkEmployeeResult(BaseModel):
    email: str
    employee_code: str
    status: str  # "success" or "failed"
    message: str
    user_id: Optional[int] = None
    employee_id: Optional[int] = None

class BulkEmployeeResponse(BaseModel):
    total_processed: int
    successful: int
    failed: int
    results: List[BulkEmployeeResult]
    summary: str

# Email Verification Schemas

class EmailVerificationRequest(BaseModel):
    """Schema for email verification request"""
    token: str = Field(..., min_length=1, description="Email verification token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "abc123def456ghi789"
            }
        }

class EmailVerificationResponse(BaseModel):
    """Schema for email verification response"""
    success: bool
    message: str
    verified: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Email verified successfully! You can now login.",
                "verified": True
            }
        }

class ResendVerificationRequest(BaseModel):
    """Schema for resend verification request"""
    email: EmailStr = Field(..., description="Email address to resend verification to")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }

class ResendVerificationResponse(BaseModel):
    """Schema for resend verification response"""
    success: bool
    message: str
    attempts_remaining: Optional[int] = None
    retry_after: Optional[int] = None  # seconds
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Verification email sent successfully.",
                "attempts_remaining": 2,
                "retry_after": None
            }
        }

class VerificationStatusResponse(BaseModel):
    """Schema for verification status response"""
    email: str
    is_verified: bool
    verification_attempts: int
    last_attempt: Optional[datetime] = None
    can_resend: bool
    retry_after: Optional[int] = None  # seconds
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "is_verified": False,
                "verification_attempts": 1,
                "last_attempt": "2023-01-01T12:00:00Z",
                "can_resend": True,
                "retry_after": None
            }
        }

class SignupResponse(BaseModel):
    """Enhanced signup response with verification info"""
    success: bool
    message: str
    user_id: int
    email: str
    verification_sent: bool
    verification_required: bool = True
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "User created successfully. Please check your email to verify your account.",
                "user_id": 123,
                "email": "user@example.com",
                "verification_sent": True,
                "verification_required": True
            }
        }

class LoginResponse(BaseModel):
    """Enhanced login response with verification status"""
    success: bool
    message: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_type: Optional[str] = None
    user: Optional[dict] = None
    verification_required: bool = False
    can_resend_verification: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "message": "Please verify your email before logging in.",
                "access_token": None,
                "refresh_token": None,
                "token_type": None,
                "user": None,
                "verification_required": True,
                "can_resend_verification": True
            }
        }

# Password Reset Schemas

class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request"""
    email: EmailStr = Field(..., description="Email address to send password reset link")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }

class ForgotPasswordResponse(BaseModel):
    """Schema for forgot password response"""
    success: bool
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Password reset link has been sent to your email."
            }
        }

class ResetPasswordRequest(BaseModel):
    """Schema for reset password request"""
    token: str = Field(..., min_length=1, description="Password reset token")
    new_password: str = Field(..., min_length=1, max_length=72, description="New password (1-72 characters)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "abc123def456ghi789",
                "new_password": "newSecurePassword123"
            }
        }

class ResetPasswordResponse(BaseModel):
    """Schema for reset password response"""
    success: bool
    message: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Password has been reset successfully. You can now login with your new password."
            }
        }

# Email System Schemas

from enum import Enum

class EmailStatus(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    COMPLAINED = "complained"
    FAILED = "failed"

class BounceType(str, Enum):
    PERMANENT = "Permanent"
    TRANSIENT = "Transient"

class EmailSendRequest(BaseModel):
    """Schema for sending emails"""
    to_emails: List[EmailStr] = Field(..., min_items=1, max_items=50, description="List of recipient email addresses")
    subject: str = Field(..., min_length=1, max_length=255, description="Email subject line")
    html_content: str = Field(..., min_length=1, description="HTML email content")
    text_content: Optional[str] = Field(None, description="Plain text email content")
    template_name: Optional[str] = Field(None, max_length=100, description="Name of the email template")
    template_data: Optional[Dict[str, Any]] = Field(None, description="Data for template rendering")
    
    class Config:
        json_schema_extra = {
            "example": {
                "to_emails": ["user@example.com"],
                "subject": "Welcome to Health App",
                "html_content": "<h1>Welcome!</h1><p>Thank you for joining us.</p>",
                "text_content": "Welcome! Thank you for joining us.",
                "template_name": "welcome_email",
                "template_data": {"user_name": "John Doe", "app_name": "Health App"}
            }
        }

class EmailSendResponse(BaseModel):
    """Schema for email send response"""
    status: str = Field(..., description="Status of the email send operation")
    message_id: Optional[str] = Field(None, description="SES message ID")
    recipients: Optional[int] = Field(None, description="Number of recipients")
    to_emails: Optional[List[str]] = Field(None, description="List of recipient emails")
    error_code: Optional[str] = Field(None, description="Error code if failed")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message_id": "0000014a-f4d4-4f4e-8f4e-123456789abc-000000",
                "recipients": 1,
                "to_emails": ["user@example.com"]
            }
        }

class EmailLogResponse(BaseModel):
    """Schema for email log response"""
    id: int
    recipient_email: str
    template_name: str
    subject: str
    status: EmailStatus
    message_id: Optional[str]
    sent_at: datetime
    delivered_at: Optional[datetime]
    bounced_at: Optional[datetime]
    complained_at: Optional[datetime]
    bounce_type: Optional[str]
    bounce_subtype: Optional[str]
    bounce_reason: Optional[str]
    error_message: Optional[str]
    template_data: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class EmailUnsubscribeRequest(BaseModel):
    """Schema for unsubscribe request"""
    email: EmailStr = Field(..., description="Email address to unsubscribe")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for unsubscribing")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "reason": "Too many emails"
            }
        }

class EmailUnsubscribeResponse(BaseModel):
    """Schema for unsubscribe response"""
    status: str = Field(..., description="Status of the unsubscribe operation")
    message: str = Field(..., description="Response message")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Email user@example.com unsubscribed successfully"
            }
        }

class EmailUnsubscribeList(BaseModel):
    """Schema for unsubscribe list item"""
    id: int
    email: str
    reason: Optional[str]
    source: Optional[str]
    unsubscribed_at: datetime
    
    class Config:
        from_attributes = True

class EmailTemplateCreate(BaseModel):
    """Schema for creating email templates"""
    name: str = Field(..., min_length=1, max_length=100, description="Template name")
    subject_template: str = Field(..., min_length=1, description="Subject template")
    html_template: str = Field(..., min_length=1, description="HTML template")
    text_template: Optional[str] = Field(None, description="Plain text template")
    description: Optional[str] = Field(None, max_length=500, description="Template description")
    category: Optional[str] = Field(None, max_length=50, description="Template category")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "welcome_email",
                "subject_template": "Welcome to {{app_name}}, {{user_name}}!",
                "html_template": "<h1>Welcome {{user_name}}!</h1><p>Thank you for joining {{app_name}}.</p>",
                "text_template": "Welcome {{user_name}}! Thank you for joining {{app_name}}.",
                "description": "Welcome email for new users",
                "category": "auth"
            }
        }

class EmailTemplateUpdate(BaseModel):
    """Schema for updating email templates"""
    subject_template: Optional[str] = Field(None, min_length=1, description="Subject template")
    html_template: Optional[str] = Field(None, min_length=1, description="HTML template")
    text_template: Optional[str] = Field(None, description="Plain text template")
    description: Optional[str] = Field(None, max_length=500, description="Template description")
    category: Optional[str] = Field(None, max_length=50, description="Template category")
    is_active: Optional[bool] = Field(None, description="Whether template is active")
    
    class Config:
        json_schema_extra = {
            "example": {
                "subject_template": "Welcome to {{app_name}}, {{user_name}}!",
                "html_template": "<h1>Welcome {{user_name}}!</h1><p>Thank you for joining {{app_name}}.</p>",
                "description": "Updated welcome email for new users"
            }
        }

class EmailTemplateResponse(BaseModel):
    """Schema for email template response"""
    id: int
    name: str
    version: int
    subject_template: str
    html_template: str
    text_template: Optional[str]
    description: Optional[str]
    category: Optional[str]
    is_active: bool
    usage_count: int
    last_used_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class EmailBounceResponse(BaseModel):
    """Schema for email bounce response"""
    id: int
    email: str
    message_id: Optional[str]
    bounce_type: str
    bounce_subtype: str
    bounce_reason: Optional[str]
    diagnostic_code: Optional[str]
    notification_timestamp: Optional[datetime]
    feedback_id: Optional[str]
    is_processed: bool
    processed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class EmailComplaintResponse(BaseModel):
    """Schema for email complaint response"""
    id: int
    email: str
    message_id: Optional[str]
    complaint_type: Optional[str]
    complaint_reason: Optional[str]
    notification_timestamp: Optional[datetime]
    feedback_id: Optional[str]
    is_processed: bool
    processed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class EmailStatsResponse(BaseModel):
    """Schema for email statistics response"""
    period_days: int
    total_sent: int
    total_delivered: int
    total_bounced: int
    total_complained: int
    delivery_rate: float
    bounce_rate: float
    complaint_rate: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "period_days": 30,
                "total_sent": 1000,
                "total_delivered": 950,
                "total_bounced": 30,
                "total_complained": 5,
                "delivery_rate": 95.0,
                "bounce_rate": 3.0,
                "complaint_rate": 0.5
            }
        }

class SESNotificationRequest(BaseModel):
    """Schema for SES notification webhook"""
    notificationType: str = Field(..., description="Type of notification (Bounce, Complaint, Delivery)")
    mail: Dict[str, Any] = Field(..., description="Mail object from SES")
    bounce: Optional[Dict[str, Any]] = Field(None, description="Bounce data")
    complaint: Optional[Dict[str, Any]] = Field(None, description="Complaint data")
    delivery: Optional[Dict[str, Any]] = Field(None, description="Delivery data")
    
    class Config:
        json_schema_extra = {
            "example": {
                "notificationType": "Bounce",
                "mail": {
                    "messageId": "0000014a-f4d4-4f4e-8f4e-123456789abc-000000",
                    "timestamp": "2023-01-01T00:00:00.000Z",
                    "source": "sender@example.com",
                    "sourceArn": "arn:aws:ses:us-east-1:123456789012:identity/sender@example.com",
                    "sourceIp": "127.0.0.1",
                    "callerIdentity": "123456789012",
                    "sendingAccountId": "123456789012"
                },
                "bounce": {
                    "bounceType": "Permanent",
                    "bounceSubType": "General",
                    "bouncedRecipients": [
                        {
                            "emailAddress": "recipient@example.com",
                            "action": "failed",
                            "status": "5.1.1",
                            "diagnosticCode": "smtp; 550 5.1.1 User unknown"
                        }
                    ],
                    "timestamp": "2023-01-01T00:00:00.000Z",
                    "feedbackId": "0000014a-f4d4-4f4e-8f4e-123456789abc-000000"
                }
            }
        }

class EmailListRequest(BaseModel):
    """Schema for email list requests with pagination"""
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(50, ge=1, le=100, description="Number of items per page")
    status: Optional[EmailStatus] = Field(None, description="Filter by email status")
    template_name: Optional[str] = Field(None, description="Filter by template name")
    recipient_email: Optional[str] = Field(None, description="Filter by recipient email")
    
    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "limit": 50,
                "status": "delivered",
                "template_name": "welcome_email"
            }
        }

class EmailListResponse(BaseModel):
    """Schema for paginated email list response"""
    items: List[EmailLogResponse]
    total: int
    page: int
    limit: int
    pages: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "items": [],
                "total": 100,
                "page": 1,
                "limit": 50,
                "pages": 2
            }
        }