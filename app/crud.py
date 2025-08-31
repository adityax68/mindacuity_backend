from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import List, Optional
from app.models import User, ClinicalAssessment, Organisation, Employee, Complaint
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
            hashed_password=hashed_password,
            role=getattr(user, 'role', 'user')  # NEW: Add role field with default
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        """Get list of users with pagination."""
        return db.query(User).offset(skip).limit(limit).all()

    @staticmethod
    def update_user_role(db: Session, user_id: int, new_role: str) -> Optional[User]:
        """Update user's role."""
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.role = new_role
            db.commit()
            db.refresh(user)
        return user



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

class OrganisationCRUD:
    """CRUD operations for Organisation model."""
    
    @staticmethod
    def generate_org_id(db: Session) -> str:
        """Generate a unique organisation ID like ORG001, ORG002, etc."""
        # Get the count of existing organisations
        count = db.query(func.count(Organisation.id)).scalar()
        return f"ORG{count + 1:03d}"
    
    @staticmethod
    def create_organisation(db: Session, org_name: str, hr_email: str) -> Organisation:
        """Create a new organisation with auto-generated org_id."""
        
        # Generate unique org_id
        org_id = OrganisationCRUD.generate_org_id(db)
        
        # Create organisation
        db_organisation = Organisation(
            org_id=org_id,
            org_name=org_name,
            hr_email=hr_email
        )
        db.add(db_organisation)
        db.commit()
        db.refresh(db_organisation)
        return db_organisation
    
    @staticmethod
    def get_organisation_by_id(db: Session, org_id: str) -> Optional[Organisation]:
        """Get organisation by org_id."""
        return db.query(Organisation).filter(Organisation.org_id == org_id).first()
    
    @staticmethod
    def get_organisation_by_email(db: Session, hr_email: str) -> Optional[Organisation]:
        """Get organisation by HR email."""
        return db.query(Organisation).filter(Organisation.hr_email == hr_email).first()
    
    @staticmethod
    def get_all_organisations(db: Session, skip: int = 0, limit: int = 100) -> List[Organisation]:
        """Get list of all organisations with pagination."""
        return db.query(Organisation).offset(skip).limit(limit).all()

class EmployeeCRUD:
    """CRUD operations for Employee model."""
    
    @staticmethod
    def generate_employee_code(db: Session) -> str:
        """Generate a unique employee code like EMP001, EMP002, etc."""
        # Get the count of existing employees
        count = db.query(func.count(Employee.id)).scalar()
        return f"EMP{count + 1:03d}"
    
    @staticmethod
    def create_employee(db: Session, user_id: int, employee_code: str, org_id: str, hr_email: str, full_name: str, email: str) -> Employee:
        """Create a new employee record."""
        db_employee = Employee(
            user_id=user_id,
            employee_code=employee_code,
            org_id=org_id,
            hr_email=hr_email,
            full_name=full_name,
            email=email
        )
        db.add(db_employee)
        db.commit()
        db.refresh(db_employee)
        return db_employee
    
    @staticmethod
    def get_employee_by_user_id(db: Session, user_id: int) -> Optional[Employee]:
        """Get employee by user ID."""
        return db.query(Employee).filter(Employee.user_id == user_id).first()
    
    @staticmethod
    def get_employees_by_hr_email(db: Session, hr_email: str) -> List[Employee]:
        """Get all employees managed by a specific HR."""
        return db.query(Employee).filter(Employee.hr_email == hr_email, Employee.is_active == True).all()
    
    @staticmethod
    def get_employees_by_org_id(db: Session, org_id: str) -> List[Employee]:
        """Get all employees in a specific organization."""
        return db.query(Employee).filter(Employee.org_id == org_id, Employee.is_active == True).all()
    
    @staticmethod
    def get_employee_by_code(db: Session, employee_code: str) -> Optional[Employee]:
        """Get employee by employee code."""
        return db.query(Employee).filter(Employee.employee_code == employee_code).first()
    
    @staticmethod
    def get_employee_by_id(db: Session, employee_id: int) -> Optional[Employee]:
        """Get employee by ID."""
        return db.query(Employee).filter(Employee.id == employee_id).first()
    
    @staticmethod
    def update_employee_status(db: Session, employee_id: int, is_active: bool) -> Optional[Employee]:
        """Update employee status (active/inactive)."""
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if employee:
            employee.is_active = is_active
            db.commit()
            db.refresh(employee)
            return employee
        return None

class ComplaintCRUD:
    """CRUD operations for Complaint model."""
    
    @staticmethod
    def create_complaint(db: Session, user_id: int, employee_id: Optional[int], complaint_text: str) -> Complaint:
        """Create a new complaint."""
        db_complaint = Complaint(
            user_id=user_id,
            employee_id=employee_id,
            complaint_text=complaint_text
        )
        db.add(db_complaint)
        db.commit()
        db.refresh(db_complaint)
        return db_complaint
    
    @staticmethod
    def get_user_complaints(db: Session, user_id: int) -> List[Complaint]:
        """Get all complaints for a specific user."""
        return db.query(Complaint).filter(Complaint.user_id == user_id).order_by(desc(Complaint.created_at)).all()
    
    @staticmethod
    def get_employee_complaints(db: Session, employee_id: int) -> List[Complaint]:
        """Get all complaints for a specific employee."""
        return db.query(Complaint).filter(Complaint.employee_id == employee_id).order_by(desc(Complaint.created_at)).all()
    
    @staticmethod
    def get_all_complaints_for_hr(db: Session, hr_email: str) -> List[Complaint]:
        """Get all complaints for HR to manage (both identified and anonymous)."""
        # Get complaints from employees managed by this HR
        from app.models import Employee
        employee_ids = [emp.id for emp in db.query(Employee).filter(Employee.hr_email == hr_email).all()]
        
        # Get complaints that either have employee_id in the managed list OR are anonymous (employee_id is None)
        complaints = db.query(Complaint).filter(
            or_(
                Complaint.employee_id.in_(employee_ids),
                Complaint.employee_id.is_(None)
            )
        ).order_by(desc(Complaint.created_at)).all()
        
        return complaints
    
    @staticmethod
    def get_complaint_by_id(db: Session, complaint_id: int) -> Optional[Complaint]:
        """Get complaint by ID."""
        return db.query(Complaint).filter(Complaint.id == complaint_id).first()
    
    @staticmethod
    def update_complaint_status(db: Session, complaint_id: int, status: str, hr_notes: Optional[str] = None) -> Optional[Complaint]:
        """Update complaint status and HR notes."""
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if complaint:
            complaint.status = status
            if hr_notes is not None:
                complaint.hr_notes = hr_notes
            db.commit()
            db.refresh(complaint)
            return complaint
        return None