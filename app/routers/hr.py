from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_active_user
from app.crud import EmployeeCRUD
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