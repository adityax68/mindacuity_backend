from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.assessment_service import AssessmentService
from app.services.subscription_service import SubscriptionService
from pydantic import BaseModel
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/assessment", tags=["assessment"])

class AssessmentRequest(BaseModel):
    session_identifier: str
    user_email: str

class AssessmentResponse(BaseModel):
    success: bool
    assessment_data: Dict[str, Any]
    message: str

@router.post("/generate", response_model=AssessmentResponse)
async def generate_assessment(
    request: AssessmentRequest,
    db: Session = Depends(get_db)
):
    """Generate mental health assessment using Claude"""
    try:
        logger.info(f"🚀 ASSESSMENT REQUEST - Session: {request.session_identifier}, User: {request.user_email}")
        
        # Check usage limit
        subscription_service = SubscriptionService()
        usage_info = subscription_service.check_usage_limit(db, request.session_identifier)
        
        if not usage_info["can_send"]:
            raise HTTPException(
                status_code=403,
                detail="Usage limit exceeded. Please subscribe to continue."
            )
        
        # Generate assessment
        assessment_service = AssessmentService()
        assessment_data = assessment_service.generate_assessment(
            db, request.session_identifier, request.user_email
        )
        
        logger.info(f"✅ ASSESSMENT COMPLETED - Session: {request.session_identifier}")
        
        return AssessmentResponse(
            success=True,
            assessment_data=assessment_data,
            message="Assessment generated successfully"
        )
        
    except Exception as e:
        logger.error(f"❌ ASSESSMENT ERROR - Session: {request.session_identifier}, Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate assessment: {str(e)}"
        )

@router.get("/history/{user_email}")
async def get_assessment_history(
    user_email: str,
    db: Session = Depends(get_db)
):
    """Get assessment history for a user"""
    try:
        from app.models import BotAssessment
        
        assessments = db.query(BotAssessment).filter(
            BotAssessment.user_email == user_email
        ).order_by(BotAssessment.created_at.desc()).all()
        
        assessment_list = []
        for assessment in assessments:
            assessment_list.append({
                "id": assessment.id,
                "session_identifier": assessment.session_identifier,
                "created_at": assessment.created_at,
                "is_critical": assessment.is_critical,
                "assessment_summary": assessment.assessment_summary,
                "mental_conditions": assessment.mental_conditions,
                "severity_levels": assessment.severity_levels
            })
        
        return {
            "success": True,
            "assessments": assessment_list
        }
        
    except Exception as e:
        logger.error(f"❌ ASSESSMENT HISTORY ERROR - User: {user_email}, Error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get assessment history: {str(e)}"
        )
