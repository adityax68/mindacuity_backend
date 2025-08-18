from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, JSON
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ClinicalAssessment(Base):
    __tablename__ = "clinical_assessments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    assessment_type = Column(String, nullable=False)  # phq9, gad7, pss10
    total_score = Column(Integer, nullable=False)
    severity_level = Column(String, nullable=False)  # minimal, mild, moderate, etc.
    interpretation = Column(Text, nullable=False)
    responses = Column(JSON, nullable=False)  # Store question responses as JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Additional metadata
    max_score = Column(Integer, nullable=False)
    assessment_name = Column(String, nullable=False)  # PHQ-9, GAD-7, PSS-10 