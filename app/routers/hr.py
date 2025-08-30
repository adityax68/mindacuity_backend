from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_active_user
from app.crud import EmployeeCRUD
from app.schemas import User, Employee, HREmployeeListResponse, HREmployeeListData, EmployeeListItem, PaginationInfo
from app.models import Organisation
from typing import List, Optional
import logging
import math


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
        
        # Get employees managed by this HR (ORIGINAL WORKING LOGIC)
        try:
            employees = EmployeeCRUD.get_employees_by_hr_email(db, current_user.email)
            logger.info(f"HR {current_user.email} fetched {len(employees)} employees")
        except Exception as e:
            logger.error(f"Error fetching employees by HR email: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )
        
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

@router.get("/employees/dashboard", response_model=HREmployeeListResponse)
async def get_hr_employees_dashboard(
    search: Optional[str] = Query(None, description="Search term for employee_code or email"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: Optional[int] = Query(10, ge=1, description="Number of employees per page"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get employees for HR dashboard with search and pagination.
    Only accessible to users with 'hr' role.
    """
    try:
        # Check if user has HR role
        if current_user.role != "hr":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. HR role required."
            )
        
        # Get the org_id from the user's employee record (same logic as dashboard)
        user_employee = db.query(Employee).filter(Employee.user_id == current_user.id).first()
        if not user_employee:
            # Fallback: Try to find organization by HR email (original logic)
            organisation = db.query(Organisation).filter(Organisation.hr_email == current_user.email).first()
            if not organisation:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. User is not associated with any organization."
                )
            org_id = organisation.org_id
        else:
            org_id = user_employee.org_id
        
        # Get employees with search and pagination
        try:
            employees, total_count = EmployeeCRUD.get_employees_for_hr_dashboard(
                db=db,
                org_id=org_id,
                search=search or "",
                page=page,
                limit=limit if limit and limit > 0 else None
            )
            logger.info(f"Successfully fetched {len(employees)} employees, total count: {total_count}")
        except Exception as e:
            logger.error(f"Error in CRUD method: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error while fetching employees"
            )
        
        # Calculate pagination info
        if limit and limit > 0:
            total_pages = math.ceil(total_count / limit) if total_count > 0 else 0
            employees_per_page = limit
        else:
            total_pages = 1 if total_count > 0 else 0
            employees_per_page = total_count
        
        # Convert to response format
        employee_list = [
            EmployeeListItem(
                id=emp.id,
                full_name=emp.full_name,
                email=emp.email,
                employee_code=emp.employee_code,
                user_id=emp.user_id,
                is_active=emp.is_active
            )
            for emp in employees
        ]
        
        pagination_info = PaginationInfo(
            current_page=page,
            total_pages=total_pages,
            total_employees=total_count,
            employees_per_page=employees_per_page
        )
        
        logger.info(f"HR {current_user.email} fetched {len(employees)} employees (page {page}, search: '{search}')")
        
        return HREmployeeListResponse(
            success=True,
            data=HREmployeeListData(
                employees=employee_list,
                pagination=pagination_info
            )
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching HR employees dashboard: {e}", exc_info=True)
        # Log more details about the error
        logger.error(f"User ID: {current_user.id}, Role: {current_user.role}, Email: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        ) 