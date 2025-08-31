from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import get_current_active_user
from app.crud import ComplaintCRUD, EmployeeCRUD
from app.schemas import User, Complaint, ComplaintCreate, ComplaintUpdate
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
    db: Session = Depends(get_db)
):
    """
    Resolve a complaint (HR only).
    Only accessible to users with 'hr' role.
    """
    try:
        # Check if user has HR role
        if current_user.role != "hr":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. HR role required."
            )
        
        # Get complaint
        complaint = ComplaintCRUD.get_complaint_by_id(db, complaint_id)
        if not complaint:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Complaint not found"
            )
        
        # Get employee and verify HR has access
        employee = EmployeeCRUD.get_employee_by_id(db, complaint.employee_id)
        if not employee or employee.hr_email != current_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only manage complaints from your employees."
            )
        
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
    db: Session = Depends(get_db)
):
    """
    Get all complaints for HR to manage (both identified and anonymous).
    Only accessible to users with 'hr' role.
    """
    try:
        # Check if user has HR role
        if current_user.role != "hr":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. HR role required."
            )
        
        # Get all complaints for this HR
        complaints = ComplaintCRUD.get_all_complaints_for_hr(db, current_user.email)
        
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