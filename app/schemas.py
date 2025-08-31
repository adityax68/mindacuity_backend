from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.clinical_assessments import AssessmentType, QuestionResponse, SeverityLevel

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    role: Optional[str] = "user"  # NEW: Add role field

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: int
    role: str  # NEW: Add role field
    privileges: List[str]  # NEW: Add privileges
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# NEW: UserResponse for admin endpoints
class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    role: str
    privileges: List[str]
    is_active: bool
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
    token_type: str
    user: User

class TokenData(BaseModel):
    email: Optional[str] = None

# Clinical Assessment schemas
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

# Chat schemas
class ChatMessageRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None

class ChatMessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatConversationResponse(BaseModel):
    id: int
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse]
    
    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    conversation_id: int
    assistant_message: str
    message_id: int

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