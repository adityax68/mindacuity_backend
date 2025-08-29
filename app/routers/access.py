from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_active_user
from app.crud import UserCRUD, OrganisationCRUD, EmployeeCRUD
from app.schemas import User, EmployeeCreate
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/access", tags=["access"])

@router.post("/request", response_model=Dict[str, Any])
async def request_access(
    access_type: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Request access for a specific role type.
    
    - **access_type**: Type of access requested ("employee", "hr", "counsellor")
    """
    try:
        logger.info(f"User {current_user.email} requesting {access_type} access")
        
        # Check if user is already an admin
        if current_user.role == "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin users cannot request additional access"
            )
        
        if access_type == "hr":
            # Check if user's email exists in organisation table
            organisation = OrganisationCRUD.get_organisation_by_email(db, current_user.email)
            
            if organisation:
                # Grant HR role
                updated_user = UserCRUD.update_user_role(db, current_user.id, "hr")
                if updated_user:
                    logger.info(f"Successfully granted HR role to user {current_user.email}")
                    return {
                        "success": True,
                        "message": "HR access granted successfully",
                        "new_role": "hr",
                        "organisation": {
                            "org_id": organisation.org_id,
                            "org_name": organisation.org_name
                        }
                    }
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to update user role"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email not found in organisation records. HR access denied."
                )
        
        elif access_type == "employee":
            # For employee access, we need additional data from the request body
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee access requires additional information. Please use the employee request endpoint."
            )
        
        elif access_type == "counsellor":
            # For counsellor access, we can grant a counsellor role
            if current_user.role in ["user", "employee"]:
                updated_user = UserCRUD.update_user_role(db, current_user.id, "counsellor")
                if updated_user:
                    logger.info(f"Successfully granted counsellor role to user {current_user.email}")
                    return {
                        "success": True,
                        "message": "Counsellor access granted successfully",
                        "new_role": "counsellor"
                    }
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to update user role"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User already has elevated access"
                )
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid access type. Must be 'employee', 'hr', or 'counsellor'"
            )
    
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
    except Exception as e:
        logger.error(f"Unexpected error during access request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )

@router.post("/request-employee", response_model=Dict[str, Any])
async def request_employee_access(
    employee_data: EmployeeCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Request employee access with organization details.
    
    - **employee_code**: User's employee code
    - **org_id**: Organization ID
    - **hr_email**: HR email address
    """
    try:
        logger.info(f"User {current_user.email} requesting employee access with org_id: {employee_data.org_id}")
        
        # Check if user is already an admin
        if current_user.role == "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin users cannot request additional access"
            )
        
        # Check if user already has elevated access
        if current_user.role != "user":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has elevated access"
            )
        
        # Validate organization exists
        organisation = OrganisationCRUD.get_organisation_by_id(db, employee_data.org_id)
        if not organisation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Your organization does not exist"
            )
        
        # Validate HR email matches the organization
        if organisation.hr_email != employee_data.hr_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="HR email does not match the organization"
            )
        
        # Check if employee code already exists
        existing_employee = EmployeeCRUD.get_employee_by_code(db, employee_data.employee_code)
        if existing_employee:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Employee code already exists"
            )
        
        # Create employee record
        employee = EmployeeCRUD.create_employee(
            db=db,
            user_id=current_user.id,
            employee_code=employee_data.employee_code,
            org_id=employee_data.org_id,
            hr_email=employee_data.hr_email,
            full_name=current_user.full_name or "",
            email=current_user.email
        )
        
        # Update user role to employee
        updated_user = UserCRUD.update_user_role(db, current_user.id, "employee")
        
        if employee and updated_user:
            logger.info(f"Successfully granted employee access to user {current_user.email}")
            return {
                "success": True,
                "message": "Employee access granted",
                "new_role": "employee",
                "employee": {
                    "employee_code": employee.employee_code,
                    "org_id": employee.org_id,
                    "org_name": organisation.org_name
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create employee record"
            )
    
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
    except Exception as e:
        logger.error(f"Unexpected error during employee access request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        ) 