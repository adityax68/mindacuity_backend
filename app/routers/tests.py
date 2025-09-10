from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.auth import get_current_active_user
from app.models import User, TestDefinition, TestQuestion, TestQuestionOption, TestScoringRange, ClinicalAssessment
from app.schemas import (
    TestDefinitionResponse, 
    TestDetailsResponse, 
    TestAssessmentRequest, 
    TestAssessmentResponse
)
from app.crud import TestCRUD

router = APIRouter(prefix="/tests", tags=["tests"])

def get_max_score_for_test(test_code: str) -> int:
    """Get max score for a test based on test code."""
    max_scores = {
        'phq9': 27,
        'gad7': 21,
        'pss10': 40
    }
    return max_scores.get(test_code, 100)  # Default to 100 if not found

def convert_to_test_assessment_response(assessment: ClinicalAssessment, test_definition: TestDefinition = None) -> TestAssessmentResponse:
    """Convert ClinicalAssessment to TestAssessmentResponse format."""
    test_code = test_definition.test_code if test_definition else assessment.assessment_type
    max_score = get_max_score_for_test(test_code)
    
    return TestAssessmentResponse(
        id=assessment.id,
        user_id=assessment.user_id,
        test_definition_id=assessment.test_definition_id,
        test_code=test_code,
        test_name=test_definition.test_name if test_definition else assessment.assessment_name,
        test_category=test_definition.test_category if test_definition else assessment.test_category,
        calculated_score=assessment.calculated_score or assessment.total_score,
        max_score=max_score,
        severity_level=assessment.severity_level,
        severity_label=assessment.severity_label,
        interpretation=assessment.interpretation,
        recommendations=getattr(assessment, 'recommendations', None),
        color_code=getattr(assessment, 'color_code', None),
        raw_responses=assessment.raw_responses or assessment.responses,
        created_at=assessment.created_at
    )

@router.get("/definitions", response_model=List[TestDefinitionResponse])
def get_test_definitions(
    category: str = None,
    db: Session = Depends(get_db)
):
    """Get all available test definitions, optionally filtered by category."""
    return TestCRUD.get_test_definitions(db, category=category)

@router.get("/definitions/{test_code}", response_model=TestDetailsResponse)
def get_test_details(
    test_code: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific test including questions and scoring ranges.
    
    Optimized to use single query instead of two separate queries.
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
        .filter(TestDefinition.test_code == test_code)\
        .first()
    
    if not test_definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test with code '{test_code}' not found"
        )
    
    # Return the optimized structure
    return {
        "test_definition": test_definition,
        "questions": test_definition.questions,
        "scoring_ranges": test_definition.scoring_ranges
    }

@router.get("/categories")
def get_test_categories(db: Session = Depends(get_db)):
    """Get all available test categories."""
    return TestCRUD.get_test_categories(db)

@router.post("/assess/{test_code}", response_model=TestAssessmentResponse, status_code=status.HTTP_201_CREATED)
def perform_test_assessment(
    test_code: str,
    assessment: TestAssessmentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Perform a test assessment and get results."""
    # Validate test exists
    test_definition = TestCRUD.get_test_definition_by_code(db, test_code)
    if not test_definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test with code '{test_code}' not found"
        )
    
    if not test_definition.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Test '{test_code}' is not currently active"
        )
    
    # Validate responses
    expected_questions = TestCRUD.get_test_questions(db, test_definition.id)
    if len(assessment.responses) != len(expected_questions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected {len(expected_questions)} responses for {test_code}, got {len(assessment.responses)}"
        )
    
    # Calculate score and get severity
    result = TestCRUD.calculate_test_score(db, test_definition.id, assessment.responses)
    
    # Save assessment
    db_assessment = TestCRUD.create_test_assessment(
        db=db,
        user_id=current_user.id,
        test_definition_id=test_definition.id,
        responses=assessment.responses,
        calculated_score=result["calculated_score"],
        max_score=result["max_score"],
        severity_level=result["severity_level"],
        severity_label=result["severity_label"],
        interpretation=result["interpretation"],
        recommendations=result["recommendations"],
        color_code=result["color_code"]
    )
    
    # Return response in the expected format
    return TestAssessmentResponse(
        id=db_assessment.id,
        user_id=db_assessment.user_id,
        test_definition_id=db_assessment.test_definition_id,
        test_code=test_definition.test_code,
        test_name=test_definition.test_name,
        test_category=test_definition.test_category,
        calculated_score=db_assessment.calculated_score,
        max_score=result["max_score"],
        severity_level=db_assessment.severity_level,
        severity_label=db_assessment.severity_label,
        interpretation=db_assessment.interpretation,
        recommendations=result["recommendations"],
        color_code=result["color_code"],
        raw_responses=db_assessment.raw_responses,
        created_at=db_assessment.created_at
    )

@router.get("/assessments", response_model=List[TestAssessmentResponse])
def get_user_test_assessments(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50
):
    """Get test assessment history for the current user."""
    assessments = TestCRUD.get_user_test_assessments(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    # Convert to proper response format
    result = []
    for assessment in assessments:
        test_definition = TestCRUD.get_test_definition_by_id(db, assessment.test_definition_id)
        result.append(convert_to_test_assessment_response(assessment, test_definition))
    
    return result

@router.get("/assessments/{assessment_id}", response_model=TestAssessmentResponse)
def get_test_assessment(
    assessment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific test assessment by ID."""
    assessment = TestCRUD.get_test_assessment_by_id(db, assessment_id)
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found"
        )
    
    # Check if user owns this assessment
    if assessment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this assessment"
        )
    
    # Convert to proper response format
    test_definition = TestCRUD.get_test_definition_by_id(db, assessment.test_definition_id)
    return convert_to_test_assessment_response(assessment, test_definition)
