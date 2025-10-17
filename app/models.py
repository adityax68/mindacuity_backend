from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, JSON, ForeignKey, Table, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

# Many-to-many relationship for user privileges
user_privileges = Table(
    'user_privileges',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('privilege_id', Integer, ForeignKey('privileges.id'), primary_key=True)
)

# Many-to-many relationship for role privileges
role_privileges = Table(
    'role_privileges',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('privilege_id', Integer, ForeignKey('privileges.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)  # Always required
    username = Column(String, unique=True, index=True, nullable=True)  # Optional for Google OAuth
    hashed_password = Column(String, nullable=True)  # Optional for Google OAuth
    full_name = Column(String, nullable=True)  # Optional for Google OAuth
    
    # NEW: User profile fields
    age = Column(Integer, nullable=True)  # Optional for Google OAuth
    country = Column(String, nullable=True)  # Optional
    state = Column(String, nullable=True)  # Optional
    city = Column(String, nullable=True)  # Optional
    pincode = Column(String, nullable=True)  # Optional
    
    # NEW: Google OAuth fields
    google_id = Column(String, unique=True, index=True, nullable=True)
    auth_provider = Column(String, default="local")  # "local" or "google"
    
    # NEW: Role system
    role = Column(String, default="user")  # "user" or "admin"
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # NEW: Email verification fields
    email_verification_token = Column(String, nullable=True, index=True)
    email_verification_expires_at = Column(DateTime(timezone=True), nullable=True)
    email_verification_attempts = Column(Integer, default=0)
    last_verification_attempt = Column(DateTime(timezone=True), nullable=True)
    
    # NEW: Password reset fields
    password_reset_token = Column(String, nullable=True, index=True)
    password_reset_expires_at = Column(DateTime(timezone=True), nullable=True)
    password_reset_attempts = Column(Integer, default=0)
    last_reset_attempt = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # NEW: Relationships
    privileges = relationship("Privilege", secondary=user_privileges, back_populates="users")
    assessments = relationship("ClinicalAssessment", back_populates="user")
    rate_limits = relationship("RateLimit", back_populates="user")
    employee = relationship("Employee", back_populates="user", uselist=False)
    complaints = relationship("Complaint", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    chat_attachments = relationship("ChatAttachment", back_populates="user")

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # "user", "admin", "therapist", etc.
    description = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Privilege(Base):
    __tablename__ = "privileges"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # "read_users", "write_assessments", etc.
    description = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    users = relationship("User", secondary=user_privileges, back_populates="privileges")
    roles = relationship("Role", secondary=role_privileges, back_populates="privileges")

class ClinicalAssessment(Base):
    __tablename__ = "clinical_assessments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assessment_type = Column(String, nullable=False)  # "anxiety", "depression", "general", etc.
    score = Column(Float, nullable=False)
    severity = Column(String, nullable=False)  # "mild", "moderate", "severe"
    recommendations = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="assessments")

class RateLimit(Base):
    __tablename__ = "rate_limits"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    endpoint = Column(String, nullable=False)
    requests_count = Column(Integer, default=0)
    window_start = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="rate_limits")

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    employee_id = Column(String, unique=True, index=True, nullable=False)
    department = Column(String, nullable=True)
    position = Column(String, nullable=True)
    hire_date = Column(DateTime(timezone=True), nullable=True)
    salary = Column(Numeric(10, 2), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="employee")

class Complaint(Base):
    __tablename__ = "complaints"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, default="pending")  # "pending", "in_progress", "resolved", "closed"
    priority = Column(String, default="medium")  # "low", "medium", "high", "urgent"
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolution = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="complaints", foreign_keys=[user_id])
    assigned_user = relationship("User", foreign_keys=[assigned_to])

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

class ChatAttachment(Base):
    __tablename__ = "chat_attachments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="chat_attachments")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    session_identifier = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_identifier = Column(String(255), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=True)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subscription_token = Column(String(255), unique=True, index=True, nullable=False)
    access_code = Column(String(255), unique=True, index=True, nullable=False)
    plan_type = Column(String(50), nullable=False)  # "free", "premium", "enterprise"
    message_limit = Column(Integer, nullable=True)
    price = Column(Numeric(10, 2), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")

class UserFreeService(Base):
    __tablename__ = "user_free_services"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    access_code = Column(String(255), unique=True, index=True, nullable=False)
    message_limit = Column(Integer, default=10)
    messages_used = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User")

class AssessmentReport(Base):
    __tablename__ = "assessment_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    session_identifier = Column(String(255), nullable=False, index=True)
    conditions = Column(JSON, nullable=False)  # Array of conditions
    symptoms = Column(JSON, nullable=False)   # Array of key symptoms
    severity_level = Column(String(50), nullable=False)  # mild/moderate/severe
    report_content = Column(Text, nullable=False)
    conversation_quality = Column(String(50), nullable=True)  # excellent/good/fair/limited
    risk_factors = Column(JSON, nullable=True)  # Array of risk factors
    protective_factors = Column(JSON, nullable=True)  # Array of protective factors
    urgency_level = Column(String(50), nullable=True)  # low/moderate/high/critical
    recommendations = Column(JSON, nullable=True)  # Array of recommendations
    limitations = Column(Text, nullable=True)  # Assessment limitations
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", foreign_keys=[session_identifier], primaryjoin="AssessmentReport.session_identifier == Conversation.session_identifier")

class TestDefinition(Base):
    __tablename__ = "test_definitions"
    
    id = Column(Integer, primary_key=True, index=True)
    test_code = Column(String(50), unique=True, nullable=False)
    test_name = Column(String(100), nullable=False)
    test_category = Column(String(50), nullable=False)
    description = Column(Text)
    total_questions = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TestQuestion(Base):
    __tablename__ = "test_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("test_definitions.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_order = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TestQuestionOption(Base):
    __tablename__ = "test_question_options"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("test_questions.id"), nullable=False)
    option_text = Column(String(500), nullable=False)
    option_value = Column(Integer, nullable=False)
    option_order = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TestScoringRange(Base):
    __tablename__ = "test_scoring_ranges"
    
    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("test_definitions.id"), nullable=False)
    min_score = Column(Integer, nullable=False)
    max_score = Column(Integer, nullable=False)
    severity_level = Column(String(50), nullable=False)
    interpretation = Column(Text, nullable=False)
    recommendations = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Organisation(Base):
    __tablename__ = "organisations"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(String(5), unique=True, index=True, nullable=False)
    org_name = Column(String, nullable=False)
    hr_email = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ConversationUsage(Base):
    __tablename__ = "conversation_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    session_identifier = Column(String(255), nullable=False, index=True)
    messages_used = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Research(Base):
    __tablename__ = "researches"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    author = Column(String, nullable=False)
    published_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EmailLog(Base):
    __tablename__ = "email_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    email = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    status = Column(String, nullable=False)  # sent, failed, bounced
    sent_at = Column(DateTime(timezone=True), server_default=func.now())

class EmailUnsubscribe(Base):
    __tablename__ = "email_unsubscribes"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EmailTemplate(Base):
    __tablename__ = "email_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String, unique=True, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EmailBounce(Base):
    __tablename__ = "email_bounces"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)
    bounce_type = Column(String, nullable=False)
    bounce_subtype = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EmailComplaint(Base):
    __tablename__ = "email_complaints"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)
    complaint_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
