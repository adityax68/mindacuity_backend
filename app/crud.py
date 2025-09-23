from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from typing import List, Optional, Dict, Any
from app.models import User, ClinicalAssessment, Organisation, Employee, Complaint, TestDefinition, TestQuestion, TestQuestionOption, TestScoringRange, Research
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
            role=getattr(user, 'role', 'user'),  # NEW: Add role field with default
            age=user.age,  # NEW: Add age field
            country=getattr(user, 'country', None),  # NEW: Add optional profile fields
            state=getattr(user, 'state', None),
            city=getattr(user, 'city', None),
            pincode=getattr(user, 'pincode', None)
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
        # Get org_id and hr_email from employee record if employee_id is provided
        org_id = None
        hr_email = None
        
        if employee_id:
            employee = EmployeeCRUD.get_employee_by_id(db, employee_id)
            if employee:
                org_id = employee.org_id
                hr_email = employee.hr_email
        
        db_complaint = Complaint(
            user_id=user_id,
            employee_id=employee_id,
            org_id=org_id,
            hr_email=hr_email,
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
    def get_all_complaints_for_hr(db: Session, hr_user_id: int, hr_email: str = None) -> List[Complaint]:
        """Get all complaints for HR to manage (both identified and anonymous)."""
        from app.models import Employee
        
        # Try organization-based filtering first
        hr_employee = EmployeeCRUD.get_employee_by_user_id(db, hr_user_id)
        if hr_employee and hr_employee.org_id:
            # Query complaints directly using org_id field
            complaints = db.query(Complaint).filter(
                or_(
                    Complaint.org_id == hr_employee.org_id,
                    Complaint.employee_id.is_(None)  # Anonymous complaints
                )
            ).order_by(desc(Complaint.created_at)).all()
            
            return complaints
        
        # Fallback to HR email-based filtering if organization-based doesn't work
        if hr_email:
            # Query complaints directly using hr_email field
            complaints = db.query(Complaint).filter(
                or_(
                    Complaint.hr_email == hr_email,
                    Complaint.employee_id.is_(None)  # Anonymous complaints
                )
            ).order_by(desc(Complaint.created_at)).all()
            
            return complaints
        
        return []
    
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

class TestCRUD:
    """CRUD operations for Test system."""
    
    @staticmethod
    def get_test_definitions(db: Session, category: str = None) -> List[TestDefinition]:
        """Get all test definitions, optionally filtered by category."""
        query = db.query(TestDefinition).filter(TestDefinition.is_active == True)
        if category:
            query = query.filter(TestDefinition.test_category == category)
        return query.order_by(TestDefinition.test_name).all()
    
    @staticmethod
    def get_test_definition_by_code(db: Session, test_code: str) -> Optional[TestDefinition]:
        """Get test definition by test code."""
        return db.query(TestDefinition).filter(TestDefinition.test_code == test_code).first()
    
    @staticmethod
    def get_test_definition_by_id(db: Session, test_definition_id: int) -> Optional[TestDefinition]:
        """Get test definition by ID."""
        return db.query(TestDefinition).filter(TestDefinition.id == test_definition_id).first()
    
    @staticmethod
    def get_test_questions(db: Session, test_definition_id: int) -> List[TestQuestion]:
        """Get all questions for a test definition."""
        return db.query(TestQuestion).filter(
            TestQuestion.test_definition_id == test_definition_id
        ).order_by(TestQuestion.question_number).all()
    
    @staticmethod
    def get_test_question_options(db: Session, test_definition_id: int) -> List[TestQuestionOption]:
        """Get all question options for a test definition."""
        return db.query(TestQuestionOption).filter(
            TestQuestionOption.test_definition_id == test_definition_id
        ).order_by(TestQuestionOption.question_id, TestQuestionOption.display_order).all()
    
    @staticmethod
    def get_test_scoring_ranges(db: Session, test_definition_id: int) -> List[TestScoringRange]:
        """Get all scoring ranges for a test definition."""
        return db.query(TestScoringRange).filter(
            TestScoringRange.test_definition_id == test_definition_id
        ).order_by(TestScoringRange.priority).all()
    
    @staticmethod
    def get_test_details(db: Session, test_definition_id: int) -> Dict[str, Any]:
        """Get complete test details including questions, options, and scoring ranges.
        
        Optimized to use eager loading to avoid N+1 query problem.
        This single query replaces 10+ separate queries.
        """
        from sqlalchemy.orm import joinedload
        
        # Single optimized query with eager loading
        test_definition = db.query(TestDefinition)\
            .options(
                # Eager load questions with their options
                joinedload(TestDefinition.questions)
                    .joinedload(TestQuestion.options),
                # Eager load scoring ranges
                joinedload(TestDefinition.scoring_ranges)
            )\
            .filter(TestDefinition.id == test_definition_id)\
            .first()
        
        if not test_definition:
            return None
        
        # The relationships are already loaded, no additional queries needed
        return {
            "test_definition": test_definition,
            "questions": test_definition.questions,
            "scoring_ranges": test_definition.scoring_ranges
        }
    
    @staticmethod
    def get_test_categories(db: Session) -> List[str]:
        """Get all unique test categories."""
        categories = db.query(TestDefinition.test_category).filter(
            TestDefinition.is_active == True
        ).distinct().all()
        return [cat[0] for cat in categories]
    
    @staticmethod
    def calculate_test_score(db: Session, test_definition_id: int, responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate test score and determine severity level."""
        # Get test questions and options
        questions = TestCRUD.get_test_questions(db, test_definition_id)
        scoring_ranges = TestCRUD.get_test_scoring_ranges(db, test_definition_id)
        
        # Calculate total score and max possible score
        total_score = 0
        max_possible_score = 0
        
        for response in responses:
            question_id = response.get("question_id")
            option_id = response.get("option_id")
            
            # Find the question
            question = next((q for q in questions if q.id == question_id), None)
            if not question:
                continue
            
            # Find the option
            option = db.query(TestQuestionOption).filter(
                TestQuestionOption.id == option_id,
                TestQuestionOption.question_id == question_id
            ).first()
            if not option:
                continue
            
            # Calculate score (consider reverse scoring)
            if question.is_reverse_scored:
                # For reverse scored questions, we need to reverse the option value
                # Assuming options are 0-4, reverse would be 4-0
                max_option_value = max([opt.option_value for opt in question.options])
                score = max_option_value - option.option_value
                # For max score calculation, use the highest possible score
                max_question_score = max_option_value * float(option.weight)
            else:
                score = option.option_value
                # For max score calculation, use the highest option value
                max_question_score = max([opt.option_value for opt in question.options]) * float(option.weight)
            
            total_score += score * float(option.weight)
            max_possible_score += max_question_score
        
        # Find appropriate severity range
        severity_range = None
        for range_obj in scoring_ranges:
            if range_obj.min_score <= total_score <= range_obj.max_score:
                severity_range = range_obj
                break
        
        if not severity_range:
            # Default to first range if no match found
            severity_range = scoring_ranges[0] if scoring_ranges else None
        
        return {
            "calculated_score": int(total_score),
            "max_score": int(max_possible_score),
            "severity_level": severity_range.severity_level if severity_range else "unknown",
            "severity_label": severity_range.severity_label if severity_range else "Unknown",
            "interpretation": severity_range.interpretation if severity_range else "Unable to interpret score",
            "recommendations": severity_range.recommendations if severity_range else None,
            "color_code": severity_range.color_code if severity_range else "#6B7280"
        }
    
    @staticmethod
    def create_test_assessment(
        db: Session,
        user_id: int,
        test_definition_id: int,
        responses: List[Dict[str, Any]],
        calculated_score: int,
        max_score: int,
        severity_level: str,
        severity_label: str,
        interpretation: str,
        recommendations: Optional[str],
        color_code: Optional[str]
    ) -> ClinicalAssessment:
        """Create a new test assessment."""
        # Get test definition for additional info
        test_definition = db.query(TestDefinition).filter(TestDefinition.id == test_definition_id).first()
        
        db_assessment = ClinicalAssessment(
            user_id=user_id,
            test_definition_id=test_definition_id,
            test_category=test_definition.test_category,
            raw_responses=responses,
            calculated_score=calculated_score,
            severity_level=severity_level,
            severity_label=severity_label,
            # Legacy fields for backward compatibility
            assessment_type=test_definition.test_code,
            assessment_name=test_definition.test_name,
            total_score=calculated_score,
            max_score=max_score,
            interpretation=interpretation,
            responses=responses  # Keep for backward compatibility
        )
        db.add(db_assessment)
        db.commit()
        db.refresh(db_assessment)
        return db_assessment
    
    @staticmethod
    def get_user_test_assessments(db: Session, user_id: int, skip: int = 0, limit: int = 50) -> List[ClinicalAssessment]:
        """Get test assessments for a specific user with pagination."""
        return db.query(ClinicalAssessment).filter(
            ClinicalAssessment.user_id == user_id,
            ClinicalAssessment.test_definition_id.isnot(None)  # Only new test assessments
        ).order_by(desc(ClinicalAssessment.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_test_assessment_by_id(db: Session, assessment_id: int) -> Optional[ClinicalAssessment]:
        """Get test assessment by ID."""
        return db.query(ClinicalAssessment).filter(
            ClinicalAssessment.id == assessment_id,
            ClinicalAssessment.test_definition_id.isnot(None)
        ).first()

class ResearchCRUD:
    """CRUD operations for Research model."""
    
    @staticmethod
    def create_research(db: Session, title: str, description: str, thumbnail_url: str, source_url: str) -> Research:
        """Create a new research entry."""
        db_research = Research(
            title=title,
            description=description,
            thumbnail_url=thumbnail_url,
            source_url=source_url
        )
        db.add(db_research)
        db.commit()
        db.refresh(db_research)
        return db_research
    
    @staticmethod
    def get_research_by_id(db: Session, research_id: int) -> Optional[Research]:
        """Get research by ID."""
        return db.query(Research).filter(Research.id == research_id).first()
    
    @staticmethod
    def get_researches(db: Session, skip: int = 0, limit: int = 10, active_only: bool = True) -> List[Research]:
        """Get list of researches with pagination."""
        query = db.query(Research)
        if active_only:
            query = query.filter(Research.is_active == True)
        return query.order_by(desc(Research.created_at)).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_researches_count(db: Session, active_only: bool = True) -> int:
        """Get total count of researches."""
        query = db.query(Research)
        if active_only:
            query = query.filter(Research.is_active == True)
        return query.count()
    
    @staticmethod
    def update_research(db: Session, research_id: int, **kwargs) -> Optional[Research]:
        """Update research by ID."""
        db_research = db.query(Research).filter(Research.id == research_id).first()
        if not db_research:
            return None
        
        for key, value in kwargs.items():
            if hasattr(db_research, key):
                setattr(db_research, key, value)
        
        db.commit()
        db.refresh(db_research)
        return db_research
    
    @staticmethod
    def delete_research(db: Session, research_id: int) -> bool:
        """Delete research by ID (soft delete by setting is_active to False)."""
        db_research = db.query(Research).filter(Research.id == research_id).first()
        if not db_research:
            return False
        
        db_research.is_active = False
        db.commit()
        return True