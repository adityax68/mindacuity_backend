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
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    
    # NEW: User profile fields
    age = Column(Integer, nullable=False)  # Mandatory field
    country = Column(String, nullable=True)  # Optional
    state = Column(String, nullable=True)  # Optional
    city = Column(String, nullable=True)  # Optional
    pincode = Column(String, nullable=True)  # Optional
    
    # NEW: Role system
    role = Column(String, default="user")  # "user" or "admin"
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # NEW: Relationships
    privileges = relationship("Privilege", secondary=user_privileges, back_populates="users")
    assessments = relationship("ClinicalAssessment", back_populates="user")
    rate_limits = relationship("RateLimit", back_populates="user")
    employee = relationship("Employee", back_populates="user", uselist=False)
    complaints = relationship("Complaint", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # "user", "admin", "therapist", etc.
    description = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # NEW: Many-to-many with privileges
    privileges = relationship("Privilege", secondary=role_privileges, back_populates="roles")

class Privilege(Base):
    __tablename__ = "privileges"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # e.g., "create_assessment", "read_users"
    description = Column(String)
    category = Column(String)  # e.g., "assessment", "user_management", "system"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # NEW: Relationships
    users = relationship("User", secondary=user_privileges, back_populates="privileges")
    roles = relationship("Role", secondary=role_privileges, back_populates="privileges")

# New Test Schema Models
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
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    questions = relationship("TestQuestion", back_populates="test_definition", cascade="all, delete-orphan")
    scoring_ranges = relationship("TestScoringRange", back_populates="test_definition", cascade="all, delete-orphan")
    assessments = relationship("ClinicalAssessment", back_populates="test_definition")

class TestQuestion(Base):
    __tablename__ = "test_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    test_definition_id = Column(Integer, ForeignKey("test_definitions.id"), nullable=False)
    question_number = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    is_reverse_scored = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    test_definition = relationship("TestDefinition", back_populates="questions")
    options = relationship("TestQuestionOption", back_populates="question", cascade="all, delete-orphan")

class TestQuestionOption(Base):
    __tablename__ = "test_question_options"
    
    id = Column(Integer, primary_key=True, index=True)
    test_definition_id = Column(Integer, ForeignKey("test_definitions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("test_questions.id"), nullable=False)
    option_text = Column(String(200), nullable=False)
    option_value = Column(Integer, nullable=False)
    weight = Column(Numeric(3,2), default=1.0)
    display_order = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    test_definition = relationship("TestDefinition")
    question = relationship("TestQuestion", back_populates="options")

class TestScoringRange(Base):
    __tablename__ = "test_scoring_ranges"
    
    id = Column(Integer, primary_key=True, index=True)
    test_definition_id = Column(Integer, ForeignKey("test_definitions.id"), nullable=False)
    min_score = Column(Integer, nullable=False)
    max_score = Column(Integer, nullable=False)
    severity_level = Column(String(50), nullable=False)
    severity_label = Column(String(100), nullable=False)
    interpretation = Column(Text, nullable=False)
    recommendations = Column(Text)
    color_code = Column(String(7))
    priority = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    test_definition = relationship("TestDefinition", back_populates="scoring_ranges")

class ClinicalAssessment(Base):
    __tablename__ = "clinical_assessments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Legacy fields (keeping for backward compatibility)
    assessment_type = Column(String, nullable=True)  # phq9, gad7, pss10
    total_score = Column(Integer, nullable=True)
    severity_level = Column(String, nullable=True)  # minimal, mild, moderate, etc.
    interpretation = Column(Text, nullable=True)
    responses = Column(JSON, nullable=True)  # Store question responses as JSON
    max_score = Column(Integer, nullable=True)
    assessment_name = Column(String, nullable=True)  # PHQ-9, GAD-7, PSS-10 
    
    # New fields for test system
    test_definition_id = Column(Integer, ForeignKey("test_definitions.id"), nullable=True)
    test_category = Column(String(50), nullable=True)
    raw_responses = Column(JSON, nullable=True)  # Store actual option selections
    calculated_score = Column(Integer, nullable=True)  # Final calculated score
    severity_label = Column(String(100), nullable=True)  # Human-readable severity
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="assessments")
    test_definition = relationship("TestDefinition", back_populates="assessments")


class Complaint(Base):
    __tablename__ = "complaints"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)  # Optional for anonymous complaints
    org_id = Column(String, nullable=True)  # Organization ID for efficient querying
    hr_email = Column(String, nullable=True)  # HR email for efficient querying
    complaint_text = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, resolved
    hr_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="complaints")
    employee = relationship("Employee", back_populates="complaints")



class RateLimit(Base):
    __tablename__ = "rate_limits"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message_count = Column(Integer, default=0)
    window_start = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    user = relationship("User", back_populates="rate_limits")

class Organisation(Base):
    __tablename__ = "organisations"
    
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(String, unique=True, index=True, nullable=False)  # Unique identifier like ORG001
    org_name = Column(String, nullable=False)
    hr_email = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    employee_code = Column(String, unique=True, index=True, nullable=False)  # EMP001, EMP002, etc.
    org_id = Column(String, nullable=False)
    hr_email = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    department = Column(String)  # Optional: IT, HR, Sales, etc.
    position = Column(String)    # Optional: Manager, Developer, etc.
    hire_date = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship
    user = relationship("User", back_populates="employee")
    complaints = relationship("Complaint", back_populates="employee")

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship
    user = relationship("User", back_populates="refresh_tokens")

# NEW: Session-based chat models for anonymous conversations

class Conversation(Base):
    __tablename__ = "conversations_new"
    
    id = Column(Integer, primary_key=True, index=True)
    session_identifier = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(255), default="New Conversation")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    messages = relationship("Message", back_populates="conversation")
    usage_records = relationship("ConversationUsage", back_populates="conversation")

class Message(Base):
    __tablename__ = "messages_new"
    
    id = Column(Integer, primary_key=True, index=True)
    session_identifier = Column(String(255), ForeignKey("conversations_new.session_identifier"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    encrypted_content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    subscription_token = Column(String(255), unique=True, nullable=False, index=True)
    access_code = Column(String(20), unique=True, nullable=False, index=True)
    plan_type = Column(String(20), nullable=False)  # "free", "basic", "premium"
    message_limit = Column(Integer, nullable=True)  # NULL for unlimited
    price = Column(Numeric(10, 2), default=0.00)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    usage_records = relationship("ConversationUsage", back_populates="subscription")

class ConversationUsage(Base):
    __tablename__ = "conversation_usage"
    
    id = Column(Integer, primary_key=True, index=True)
    session_identifier = Column(String(255), ForeignKey("conversations_new.session_identifier"), nullable=False)
    subscription_token = Column(String(255), ForeignKey("subscriptions.subscription_token"), nullable=False)
    messages_used = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="usage_records")
    subscription = relationship("Subscription", back_populates="usage_records")