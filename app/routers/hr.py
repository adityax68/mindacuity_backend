from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_active_user
from app.crud import EmployeeCRUD, ClinicalAssessmentCRUD, ComplaintCRUD
from app.schemas import User, Employee
from typing import List
import logging

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