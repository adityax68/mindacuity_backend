from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.database import get_db
from app.auth import get_current_user, UnifiedUser
from app.models import User, ClinicalAssessment
from app.schemas import (
    ClinicalAssessmentRequest, ClinicalAssessmentResponse, 
    ComprehensiveAssessmentRequest, ComprehensiveAssessmentResponse,
    ClinicalAssessmentSummary, QuestionsResponse
)
from app.clinical_assessments import clinical_engine, AssessmentType
from app.crud import ClinicalAssessmentCRUD
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/clinical", tags=["clinical_assessments"])

@router.get("/questions/{assessment_type}", response_model=QuestionsResponse)
async def get_assessment_questions(assessment_type: AssessmentType):
    """Get questions for a specific assessment type"""
    try:
        questions = clinical_engine.get_questions(assessment_type)
        
        # Provide response options based on assessment type
        if assessment_type == AssessmentType.PHQ9:
            response_options = ["Not at all", "Several days", "More than half the days", "Nearly every day"]
        elif assessment_type == AssessmentType.GAD7:
            response_options = ["Not at all", "Several days", "More than half the days", "Nearly every day"]
        elif assessment_type == AssessmentType.PSS10:
            response_options = ["Never", "Almost never", "Sometimes", "Fairly often", "Very often"]
        else:
            response_options = ["Not at all", "Several days", "More than half the days", "Nearly every day"]
        
        return QuestionsResponse(
            assessment_type=assessment_type,
            questions=questions,
            response_options=response_options
        )
    except Exception as e:
        logger.error(f"Failed to get questions for {assessment_type}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get assessment questions: {str(e)}"
        )

@router.post("/assess", response_model=ClinicalAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def perform_clinical_assessment(
    assessment: ClinicalAssessmentRequest,
    current_user: UnifiedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Perform a clinical assessment"""
    try:
        # Convert UnifiedUser to user_id for clinical service
        user_id = current_user.id if isinstance(current_user.id, int) else int(current_user.id, 16) % 1000000
        
        # Process the assessment
        result = clinical_engine.process_assessment(assessment.assessment_type, assessment.responses)
        
        # Store the assessment
        db_assessment = await ClinicalAssessmentCRUD.create_clinical_assessment(
            db, user_id, {
                "assessment_type": assessment.assessment_type.value,
                "total_score": result["total_score"],
                "severity_level": result["severity_level"],
                "interpretation": result["interpretation"],
                "responses": assessment.responses,
                "max_score": result["max_score"],
                "assessment_name": result["assessment_name"]
            }
        )
        
        return ClinicalAssessmentResponse(
            id=db_assessment.id,
            assessment_type=db_assessment.assessment_type,
            total_score=db_assessment.total_score,
            severity_level=db_assessment.severity_level,
            interpretation=db_assessment.interpretation,
            responses=db_assessment.responses,
            created_at=db_assessment.created_at,
            max_score=db_assessment.max_score,
            assessment_name=db_assessment.assessment_name
        )
        
    except Exception as e:
        logger.error(f"Failed to perform assessment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform assessment: {str(e)}"
        )

@router.get("/my-assessments", response_model=List[ClinicalAssessmentResponse])
async def get_my_clinical_assessments(
    skip: int = 0,
    limit: int = 50,
    current_user: UnifiedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all clinical assessments for the current user"""
    try:
        # Convert UnifiedUser to user_id for clinical service
        user_id = current_user.id if isinstance(current_user.id, int) else int(current_user.id, 16) % 1000000
        
        assessments = await ClinicalAssessmentCRUD.get_user_clinical_assessments(db, user_id, skip, limit)
        
        return [
            ClinicalAssessmentResponse(
                id=assessment.id,
                assessment_type=assessment.assessment_type,
                total_score=assessment.total_score,
                severity_level=assessment.severity_level,
                interpretation=assessment.interpretation,
                responses=assessment.responses,
                created_at=assessment.created_at,
                max_score=assessment.max_score,
                assessment_name=assessment.assessment_name
            )
            for assessment in assessments
        ]
        
    except Exception as e:
        logger.error(f"Failed to get assessments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get assessments: {str(e)}"
        )

@router.get("/summary", response_model=ClinicalAssessmentSummary)
async def get_assessment_summary(
    current_user: UnifiedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get assessment summary for the current user"""
    try:
        # Convert UnifiedUser to user_id for clinical service
        user_id = current_user.id if isinstance(current_user.id, int) else int(current_user.id, 16) % 1000000
        
        summary = await ClinicalAssessmentCRUD.get_user_clinical_assessment_summary(db, user_id)
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get assessment summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get assessment summary: {str(e)}"
        )

@router.post("/comprehensive", response_model=ComprehensiveAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def perform_comprehensive_assessment(
    assessment: ComprehensiveAssessmentRequest,
    current_user: UnifiedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Perform a comprehensive assessment (all three types)"""
    try:
        # Convert UnifiedUser to user_id for clinical service
        user_id = current_user.id if isinstance(current_user.id, int) else int(current_user.id, 16) % 1000000
        
        # Process comprehensive assessment
        result = clinical_engine.process_comprehensive_assessment(assessment.responses)
        
        # Store the assessment
        db_assessment = await ClinicalAssessmentCRUD.create_clinical_assessment(
            db, user_id, {
                "assessment_type": "comprehensive",
                "total_score": result["total_score"],
                "severity_level": result["severity_level"],
                "interpretation": result["interpretation"],
                "responses": assessment.responses,
                "max_score": result["max_score"],
                "assessment_name": result["assessment_name"]
            }
        )
        
        return ComprehensiveAssessmentResponse(
            id=db_assessment.id,
            total_score=db_assessment.total_score,
            severity_level=db_assessment.severity_level,
            interpretation=db_assessment.interpretation,
            responses=db_assessment.responses,
            created_at=db_assessment.created_at,
            max_score=db_assessment.max_score,
            assessment_name=db_assessment.assessment_name
        )
        
    except Exception as e:
        logger.error(f"Failed to perform comprehensive assessment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to perform comprehensive assessment: {str(e)}"
        )

@router.get("/assessments/{assessment_id}", response_model=ClinicalAssessmentResponse)
async def get_assessment_by_id(
    assessment_id: int,
    current_user: UnifiedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific assessment by ID"""
    try:
        # Convert UnifiedUser to user_id for clinical service
        user_id = current_user.id if isinstance(current_user.id, int) else int(current_user.id, 16) % 1000000
        
        assessment = await ClinicalAssessmentCRUD.get_clinical_assessment_by_id(db, assessment_id)
        
        if not assessment or assessment.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assessment not found or access denied"
            )
        
        return ClinicalAssessmentResponse(
            id=assessment.id,
            assessment_type=assessment.assessment_type,
            total_score=assessment.total_score,
            severity_level=assessment.severity_level,
            interpretation=assessment.interpretation,
            responses=assessment.responses,
            created_at=assessment.created_at,
            max_score=assessment.max_score,
            assessment_name=assessment.assessment_name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get assessment {assessment_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get assessment: {str(e)}"
        ) 