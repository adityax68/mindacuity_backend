from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, JSON, ForeignKey, Table, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
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

class ClinicalAssessment(Base):
    __tablename__ = "clinical_assessments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assessment_type = Column(String, nullable=False)  # phq9, gad7, pss10
    total_score = Column(Integer, nullable=False)
    severity_level = Column(String, nullable=False)  # minimal, mild, moderate, etc.
    interpretation = Column(Text, nullable=False)
    responses = Column(JSON, nullable=False)  # Store question responses as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Additional metadata
    max_score = Column(Integer, nullable=False)
    assessment_name = Column(String, nullable=False)  # PHQ-9, GAD-7, PSS-10 
    
    # NEW: Relationship
    user = relationship("User", back_populates="assessments")

class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=True)  # Auto-generated from first message
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    user = relationship("User", back_populates="chat_conversations")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")

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

# New Organization/Employee Models
class Organization(Base):
    __tablename__ = "organisations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_name = Column(String(150), nullable=False)
    hremail = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    employees = relationship("Employee", back_populates="organization", cascade="all, delete-orphan")

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    employee_email = Column(String(150), nullable=False, index=True)
    password_hash = Column(Text, nullable=False)
    name = Column(String(100), nullable=False)
    dob = Column(Date, nullable=True)
    phone_number = Column(String(20), nullable=True)
    joining_date = Column(Date, server_default=func.current_date())
    role = Column(String(20), default="employee")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    organization = relationship("Organization", back_populates="employees") 