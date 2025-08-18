from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from app.models import User, ClinicalAssessment
from app.schemas import UserCreate
from app.auth import get_password_hash
from app.clinical_assessments import AssessmentType

class UserCRUD:
    """CRUD operations for User model."""
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[User]:
        """Get user by email address."""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username."""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()
    
    @staticmethod
    def create_user(db: Session, user: UserCreate) -> User:
        """Create a new user."""
        hashed_password = get_password_hash(user.password)
        db_user = User(
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            hashed_password=hashed_password
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get list of users with pagination."""
        return db.query(User).offset(skip).limit(limit).all()



class ClinicalAssessmentCRUD:
    """CRUD operations for ClinicalAssessment model."""
    
    @staticmethod
    def create_clinical_assessment(db: Session, user_id: int, assessment_data: dict) -> ClinicalAssessment:
        """Create a new clinical assessment."""
        db_assessment = ClinicalAssessment(
            user_id=user_id,
            assessment_type=assessment_data["assessment_type"],
            assessment_name=assessment_data["assessment_name"],
            total_score=assessment_data["total_score"],
            max_score=assessment_data["max_score"],
            severity_level=assessment_data["severity_level"],
            interpretation=assessment_data["interpretation"],
            responses=assessment_data["responses"]
        )
        db.add(db_assessment)
        db.commit()
        db.refresh(db_assessment)
        return db_assessment
    
    @staticmethod
    def get_user_clinical_assessments(db: Session, user_id: int, skip: int = 0, limit: int = 50) -> List[ClinicalAssessment]:
        """Get clinical assessments for a specific user with pagination."""
        return db.query(ClinicalAssessment)\
                .filter(ClinicalAssessment.user_id == user_id)\
                .order_by(desc(ClinicalAssessment.created_at))\
                .offset(skip)\
                .limit(limit)\
                .all()
    
    @staticmethod
    def get_clinical_assessment_by_id(db: Session, assessment_id: int) -> Optional[ClinicalAssessment]:
        """Get clinical assessment by ID."""
        return db.query(ClinicalAssessment)\
                .filter(ClinicalAssessment.id == assessment_id)\
                .first()
    
    @staticmethod
    def get_user_clinical_assessment_summary(db: Session, user_id: int) -> dict:
        """Get summary statistics for a user's clinical assessments."""
        assessments = db.query(ClinicalAssessment)\
                       .filter(ClinicalAssessment.user_id == user_id)\
                       .all()
        
        if not assessments:
            return {
                "total_assessments": 0,
                "assessments": [],
                "overall_risk_level": "low",
                "recommendations": ["No clinical assessments found"]
            }
        
        # Convert to dict format for summary
        assessment_dicts = []
        for assessment in assessments:
            assessment_dicts.append({
                "id": assessment.id,
                "assessment_type": assessment.assessment_type,
                "assessment_name": assessment.assessment_name,
                "total_score": assessment.total_score,
                "max_score": assessment.max_score,
                "severity_level": assessment.severity_level,
                "interpretation": assessment.interpretation,
                "created_at": assessment.created_at.isoformat()
            })
        
        # Use clinical engine to generate summary
        from app.clinical_assessments import clinical_engine
        summary = clinical_engine.get_assessment_summary(assessment_dicts)
        
        return summary
    
    @staticmethod
    def delete_clinical_assessment(db: Session, assessment_id: int, user_id: int) -> bool:
        """Delete a clinical assessment (only if it belongs to the user)."""
        assessment = db.query(ClinicalAssessment)\
                      .filter(ClinicalAssessment.id == assessment_id,
                             ClinicalAssessment.user_id == user_id)\
                      .first()
        
        if assessment:
            db.delete(assessment)
            db.commit()
            return True
        return False 