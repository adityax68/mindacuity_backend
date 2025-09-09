from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_active_user, require_privilege
from app.crud import ComplaintCRUD, EmployeeCRUD
from app.schemas import User, Complaint, ComplaintCreate, ComplaintUpdate
from app.services.role_service import RoleService, get_role_service
from typing import List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/complaints", tags=["complaints"])

@router.post("/", response_model=Complaint, status_code=status.HTTP_201_CREATED)
async def create_complaint(
    complaint: ComplaintCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new complaint.
    Only accessible to authenticated users.
    """
    try:
        # Check if user is an employee
        if current_user.role != "employee":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only employees can create complaints"
            )
        
        # Get employee record for the current user
        employee = EmployeeCRUD.get_employee_by_user_id(db, current_user.id)
        if not employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee record not found"
            )
        
        # Create complaint with optional employee_id based on user choice
        employee_id = employee.id if complaint.share_employee_id else None
        
        db_complaint = ComplaintCRUD.create_complaint(
            db=db,
            user_id=current_user.id,
            employee_id=employee_id,
            complaint_text=complaint.complaint_text
        )
        
        logger.info(f"Employee {current_user.email} created complaint {db_complaint.id}")
        
        return db_complaint
    
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating complaint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )

@router.get("/my-complaints", response_model=List[Complaint])
async def get_my_complaints(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's complaints.
    Only accessible to authenticated users.
    """
    try:
        complaints = ComplaintCRUD.get_user_complaints(db, current_user.id)
        return complaints
    
    except Exception as e:
        logger.error(f"Unexpected error fetching complaints: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )

@router.put("/{complaint_id}/resolve")
async def resolve_complaint(
    complaint_id: int,
    complaint_update: ComplaintUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """
    Resolve a complaint (HR only).
    Only accessible to users with 'manage_complaints' privilege.
    """
    try:
        # Check if user has manage_complaints privilege
        has_privilege = await role_service.user_has_privilege(current_user.id, "manage_complaints")
        if not has_privilege:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. HR privilege required to manage complaints."
            )
        
        # Get complaint
        complaint = ComplaintCRUD.get_complaint_by_id(db, complaint_id)
        if not complaint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Complaint not found"
            )
        
        # Verify HR has access to this complaint
        # HR can manage complaints from their organization (both identified and anonymous)
        if complaint.employee_id is not None:
            # For identified complaints, check access using the stored org_id and hr_email
            hr_employee = EmployeeCRUD.get_employee_by_user_id(db, current_user.id)
            has_access = False
            
            if hr_employee and hr_employee.org_id and complaint.org_id:
                # Check if both HR and complaint are in the same organization
                has_access = (hr_employee.org_id == complaint.org_id)
            elif complaint.hr_email:
                # Fallback to HR email-based access
                has_access = (complaint.hr_email == current_user.email)
            
            if not has_access:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied. You can only manage complaints from your organization or managed employees."
                )
        # For anonymous complaints (employee_id is None), any HR with manage_complaints privilege can resolve them
        
        # Update complaint status
        updated_complaint = ComplaintCRUD.update_complaint_status(
            db=db,
            complaint_id=complaint_id,
            status=complaint_update.status,
            hr_notes=complaint_update.hr_notes
        )
        
        logger.info(f"HR {current_user.email} resolved complaint {complaint_id}")
        
        return {"message": "Complaint updated successfully", "complaint": updated_complaint}
    
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
    except Exception as e:
        logger.error(f"Unexpected error resolving complaint: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        )

@router.get("/hr/all-complaints")
async def get_hr_complaints(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    role_service: RoleService = Depends(get_role_service)
):
    """
    Get all complaints for HR to manage (both identified and anonymous).
    Only accessible to users with 'manage_complaints' privilege.
    """
    try:
        # Check if user has manage_complaints privilege
        has_privilege = await role_service.user_has_privilege(current_user.id, "manage_complaints")
        if not has_privilege:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. HR privilege required to manage complaints."
            )
        
        # Get all complaints for this HR (try organization-based first, fallback to email-based)
        complaints = ComplaintCRUD.get_all_complaints_for_hr(db, current_user.id, current_user.email)
        
        logger.info(f"HR {current_user.email} fetched {len(complaints)} complaints")
        
        return complaints
    
    except HTTPException:
        # Re-raise HTTP exceptions as they are already properly formatted
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching HR complaints: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again."
        ) 