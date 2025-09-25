from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_active_user
from app.crud import EmployeeCRUD, ClinicalAssessmentCRUD, ComplaintCRUD, OrganisationCRUD
from app.schemas import User, Employee, BulkEmployeeResponse
from typing import List
import logging
import csv
import io

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hr", tags=["hr"])

@router.get("/employees", response_model=List[Employee])
async def get_hr_employees(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get all employees managed by the current HR user.
    Only accessible to users with 'hr' role.
    """
    try:
        # Check if user has HR role
        if current_user.role != "hr":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. HR role required."
            )
        
        # Get employees managed by this HR
        employees = EmployeeCRUD.get_employees_by_hr_email(db, current_user.email)
        
        logger.info(f"HR {current_user.email} fetched {len(employees)} employees")
        
        return employees
    
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching HR employees: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )

@router.put("/employees/{employee_id}/status")
async def update_employee_status(
    employee_id: int,
    is_active: bool,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update employee status (active/inactive).
    Only accessible to users with 'hr' role.
    """
    try:
        # Check if user has HR role
        if current_user.role != "hr":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. HR role required."
            )
        
        # Get employee and verify HR has access
        employee = EmployeeCRUD.get_employee_by_id(db, employee_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        # Verify HR manages this employee
        if employee.hr_email != current_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only manage your own employees."
            )
        
        # Update employee status
        updated_employee = EmployeeCRUD.update_employee_status(db, employee_id, is_active)
        
        logger.info(f"HR {current_user.email} updated employee {employee_id} status to {is_active}")
        
        return {"message": f"Employee status updated to {'active' if is_active else 'inactive'}", "employee": updated_employee}
    
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
    except Exception as e:
        logger.error(f"Unexpected error updating employee status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )

@router.get("/employees/{employee_id}/assessments")
async def get_employee_assessments(
    employee_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get assessment history for a specific employee.
    Only accessible to users with 'hr' role.
    """
    try:
        # Check if user has HR role
        if current_user.role != "hr":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. HR role required."
            )
        
        # Get employee and verify HR has access
        employee = EmployeeCRUD.get_employee_by_id(db, employee_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        # Verify HR manages this employee
        if employee.hr_email != current_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only access your own employees' assessments."
            )
        
        # Get assessment history for the employee
        assessments = ClinicalAssessmentCRUD.get_user_clinical_assessments(db, employee.user_id, skip=0, limit=100)
        
        logger.info(f"HR {current_user.email} fetched {len(assessments)} assessments for employee {employee_id}")
        
        return assessments
    
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching employee assessments: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )

@router.get("/employees/{employee_id}/complaints")
async def get_employee_complaints(
    employee_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get complaints for a specific employee.
    Only accessible to users with 'hr' role.
    """
    try:
        # Check if user has HR role
        if current_user.role != "hr":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. HR role required."
            )
        
        # Get employee and verify HR has access
        employee = EmployeeCRUD.get_employee_by_id(db, employee_id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee not found"
            )
        
        # Verify HR manages this employee
        if employee.hr_email != current_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only access complaints from your own employees."
            )
        
        # Get complaints for the employee
        complaints = ComplaintCRUD.get_employee_complaints(db, employee_id)
        
        logger.info(f"HR {current_user.email} fetched {len(complaints)} complaints for employee {employee_id}")
        
        return complaints
    
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching employee complaints: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )

@router.post("/bulk-employee-access", response_model=BulkEmployeeResponse)
async def bulk_employee_access(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Bulk create employees from CSV file.
    Only accessible to users with 'hr' role.
    
    CSV format should include:
    - email (REQUIRED)
    - employee_code (REQUIRED)
    - full_name (REQUIRED)
    - age (optional, defaults to 25)
    - department (optional)
    - position (optional)
    - hire_date (optional)
    - country (optional)
    - state (optional)
    - city (optional)
    - pincode (optional)
    """
    try:
        # Check if user has HR role
        if current_user.role != "hr":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. HR role required."
            )
        
        # Get organization for this HR
        organisation = OrganisationCRUD.get_organisation_by_email(db, current_user.email)
        if not organisation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found for this HR user."
            )
        
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only CSV files are allowed."
            )
        
        # Read and parse CSV file
        content = await file.read()
        try:
            csv_content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file encoding. Please use UTF-8 encoding."
            )
        
        # Parse CSV
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        employees_data = list(csv_reader)
        
        if not employees_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV file is empty or has no valid data."
            )
        
        # Validate CSV headers
        required_headers = ['email', 'employee_code', 'full_name']
        csv_headers = csv_reader.fieldnames or []
        missing_headers = [header for header in required_headers if header not in csv_headers]
        
        if missing_headers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required CSV headers: {', '.join(missing_headers)}"
            )
        
        logger.info(f"HR {current_user.email} uploading {len(employees_data)} employees for org {organisation.org_id}")
        
        # Process bulk employee creation
        result = EmployeeCRUD.bulk_create_employees(
            db=db,
            employees_data=employees_data,
            org_id=organisation.org_id,
            hr_email=current_user.email
        )
        
        # Create summary message
        summary = f"Processed {result['total_processed']} employees. {result['successful']} successful, {result['failed']} failed."
        
        logger.info(f"Bulk employee creation completed: {summary}")
        
        return BulkEmployeeResponse(
            total_processed=result['total_processed'],
            successful=result['successful'],
            failed=result['failed'],
            results=result['results'],
            summary=summary
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
    except Exception as e:
        logger.error(f"Unexpected error during bulk employee creation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        ) 