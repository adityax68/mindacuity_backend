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
    
    # NEW: Role system
    role = Column(String, default="user")  # "user" or "admin"
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # NEW: Relationships
    privileges = relationship("Privilege", secondary=user_privileges, back_populates="users")
    assessments = relationship("ClinicalAssessment", back_populates="user")
    chat_conversations = relationship("ChatConversation", back_populates="user")
    chat_messages = relationship("ChatMessage", back_populates="user")
    rate_limits = relationship("RateLimit", back_populates="user")
    employee = relationship("Employee", back_populates="user", uselist=False)
    complaints = relationship("Complaint", back_populates="user")

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

class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="chat_conversations")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")

class Complaint(Base):
    __tablename__ = "complaints"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)  # Optional for anonymous complaints
    complaint_text = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, resolved
    hr_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="complaints")
    employee = relationship("Employee", back_populates="complaints")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("chat_conversations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)  # Encrypted message content
    encrypted_content = Column(Text, nullable=False)  # Actually encrypted content
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("ChatConversation", back_populates="messages")
    user = relationship("User", back_populates="chat_messages")

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