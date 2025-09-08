from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.auth import get_current_active_user
from app.crud import ClinicalAssessmentCRUD, TestCRUD
from app.clinical_assessments import clinical_engine, AssessmentType
from app.schemas import (
    ClinicalAssessmentRequest, 
    ClinicalAssessmentResponse, 
    ClinicalAssessmentSummary,
    QuestionsResponse,
    ComprehensiveAssessmentRequest,
    ComprehensiveAssessmentResponse,
    TestAssessmentResponse,
    User
)

router = APIRouter(prefix="/clinical", tags=["clinical assessments"])

@router.get("/questions/{assessment_type}", response_model=QuestionsResponse)
def get_assessment_questions(assessment_type: AssessmentType):
    """
    Get questions for a specific clinical assessment type.
    
    - **assessment_type**: Type of assessment (phq9, gad7, pss10)
    
    Returns the questions and response options for the specified assessment.
    """
    questions = clinical_engine.get_questions(assessment_type)
    
    # Define response options based on assessment type
    if assessment_type == AssessmentType.PSS10:
        response_options = [
            "Never",
            "Almost never", 
            "Sometimes",
            "Fairly often",
            "Very often"
        ]
    else:  # PHQ-9 and GAD-7
        response_options = [
            "Not at all",
            "Several days",
            "More than half the days",
            "Nearly every day"
        ]
    
    return QuestionsResponse(
        assessment_type=assessment_type,
        questions=questions,
        response_options=response_options
    )

@router.post("/assess", response_model=ClinicalAssessmentResponse, status_code=status.HTTP_201_CREATED)
def perform_clinical_assessment(
    assessment: ClinicalAssessmentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Perform a clinical assessment using validated scales.
    
    - **assessment_type**: Type of assessment (phq9, gad7, pss10)
    - **responses**: List of question responses with scores (0-4)
    
    Returns comprehensive clinical assessment results with severity levels and interpretations.
    """
    # Validate responses
    expected_questions = len(clinical_engine.get_questions(assessment.assessment_type))
    if len(assessment.responses) != expected_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected {expected_questions} responses for {assessment.assessment_type}, got {len(assessment.responses)}"
        )
    
    # Validate response scores
    for response in assessment.responses:
        if response.response < 0 or response.response > 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Response scores must be between 0 and 4, got {response.response}"
            )
    
    # Perform clinical assessment
    result = clinical_engine.assess(assessment.assessment_type, assessment.responses)
    
    # Prepare data for database storage
    assessment_data = {
        "assessment_type": assessment.assessment_type.value,
        "assessment_name": result["assessment_type"],
        "total_score": result["total_score"],
        "max_score": result["max_score"],
        "severity_level": result["severity_level"].value,
        "interpretation": result["interpretation"],
        "responses": [{"question_id": r.question_id, "response": r.response} for r in assessment.responses]
    }
    
    # Save to database
    db_assessment = ClinicalAssessmentCRUD.create_clinical_assessment(
        db=db, 
        user_id=current_user.id, 
        assessment_data=assessment_data
    )
    
    return db_assessment

@router.post("/comprehensive", response_model=ComprehensiveAssessmentResponse, status_code=status.HTTP_201_CREATED)
def perform_comprehensive_assessment(
    assessment: ComprehensiveAssessmentRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Perform a comprehensive mental health assessment combining PHQ-9, GAD-7, and PSS-10.
    
    - **responses**: List of question responses with scores (0-4)
    
    Returns comprehensive clinical assessment results with severity levels and interpretations.
    """
    try:
        # Separate responses by category (depression, anxiety, stress)
        depression_responses = []
        anxiety_responses = []
        stress_responses = []
        
        for response in assessment.responses:
            if response.get('category') == 'depression':
                depression_responses.append(response)
            elif response.get('category') == 'anxiety':
                anxiety_responses.append(response)
            elif response.get('category') == 'stress':
                stress_responses.append(response)
        
        # Validate we have the right number of responses
        if len(depression_responses) != 9:  # PHQ-9 has 9 questions
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Expected 9 depression responses, got {len(depression_responses)}"
            )
        if len(anxiety_responses) != 7:  # GAD-7 has 7 questions
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Expected 7 anxiety responses, got {len(anxiety_responses)}"
            )
        if len(stress_responses) != 10:  # PSS-10 has 10 questions
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Expected 10 stress responses, got {len(stress_responses)}"
            )
        
        # Calculate scores
        depression_score = sum(r.get('response', 0) for r in depression_responses)
        anxiety_score = sum(r.get('response', 0) for r in anxiety_responses)
        
        # PSS-10 has reverse scoring for questions 4, 5, 7, 8
        stress_score = 0
        for i, response in enumerate(stress_responses):
            score = response.get('response', 0)
            if i in [3, 4, 6, 7]:  # Questions 4, 5, 7, 8 (0-indexed)
                stress_score += (4 - score)  # Reverse scoring
            else:
                stress_score += score
        
        # Determine severity levels
        def get_depression_severity(score):
            if score <= 4: return 'minimal'
            if score <= 9: return 'mild'
            if score <= 14: return 'moderate'
            if score <= 19: return 'moderately_severe'
            return 'severe'
        
        def get_anxiety_severity(score):
            if score <= 4: return 'minimal'
            if score <= 9: return 'mild'
            if score <= 14: return 'moderate'
            return 'severe'
        
        def get_stress_severity(score):
            if score <= 13: return 'low'
            if score <= 26: return 'moderate'
            return 'high'
        
        # Calculate overall severity
        depression_severity = get_depression_severity(depression_score)
        anxiety_severity = get_anxiety_severity(anxiety_score)
        stress_severity = get_stress_severity(stress_score)
        
        # Determine overall severity (take the highest)
        severity_levels = [depression_severity, anxiety_severity, stress_severity]
        overall_severity = 'severe' if 'severe' in severity_levels else \
                          'moderately_severe' if 'moderately_severe' in severity_levels else \
                          'moderate' if 'moderate' in severity_levels else \
                          'mild' if 'mild' in severity_levels else 'minimal'
        
        # Create interpretation
        interpretation = f"Comprehensive assessment results: Depression score {depression_score}/27 ({depression_severity}), Anxiety score {anxiety_score}/21 ({anxiety_severity}), Stress score {stress_score}/40 ({stress_severity}). Overall severity: {overall_severity}."
        
        # Prepare data for database storage
        assessment_data = {
            "assessment_type": "comprehensive",
            "assessment_name": "Comprehensive Assessment",
            "total_score": depression_score + anxiety_score + stress_score,
            "max_score": 27 + 21 + 40,  # 88 total
            "severity_level": overall_severity,
            "interpretation": interpretation,
            "responses": assessment.responses
        }
        
        # Save to database
        db_assessment = ClinicalAssessmentCRUD.create_clinical_assessment(
            db=db, 
            user_id=current_user.id, 
            assessment_data=assessment_data
        )
        
        # Return the expected format for the frontend
        return {
            "id": db_assessment.id,
            "user_id": db_assessment.user_id,
            "assessment_type": "comprehensive",
            "assessment_name": "Comprehensive Assessment",
            "total_score": depression_score + anxiety_score + stress_score,
            "max_score": 27 + 21 + 40,
            "severity_level": overall_severity,
            "interpretation": interpretation,
            "responses": assessment.responses,
            "created_at": db_assessment.created_at,
            "depression": {
                "score": depression_score,
                "max_score": 27,
                "severity": depression_severity,
                "interpretation": f"Depression score: {depression_score}/27 ({depression_severity})"
            },
            "anxiety": {
                "score": anxiety_score,
                "max_score": 21,
                "severity": anxiety_severity,
                "interpretation": f"Anxiety score: {anxiety_score}/21 ({anxiety_severity})"
            },
            "stress": {
                "score": stress_score,
                "max_score": 40,
                "severity": stress_severity,
                "interpretation": f"Stress score: {stress_score}/40 ({stress_severity})"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing comprehensive assessment: {str(e)}"
        )

@router.get("/my-assessments", response_model=List[ClinicalAssessmentResponse])
def get_my_clinical_assessments(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's clinical assessment history.
    
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (max 100)
    """
    if limit > 100:
        limit = 100
    
    assessments = ClinicalAssessmentCRUD.get_user_clinical_assessments(
        db=db, 
        user_id=current_user.id, 
        skip=skip, 
        limit=limit
    )
    
    return assessments

@router.get("/summary", response_model=ClinicalAssessmentSummary)
def get_clinical_assessment_summary(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for current user's clinical assessments.
    
    Returns aggregated data including severity levels, recommendations, and trends.
    """
    summary = ClinicalAssessmentCRUD.get_user_clinical_assessment_summary(
        db=db, 
        user_id=current_user.id
    )
    
    return ClinicalAssessmentSummary(**summary)

@router.get("/unified-assessments", response_model=List[dict])
def get_unified_assessment_history(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get unified assessment history including both old clinical assessments and new test system results.
    
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (max 100)
    """
    if limit > 100:
        limit = 100
    
    # Get old clinical assessments
    clinical_assessments = ClinicalAssessmentCRUD.get_user_clinical_assessments(
        db=db, 
        user_id=current_user.id, 
        skip=skip, 
        limit=limit
    )
    
    # Get new test assessments using the proper conversion
    from app.routers.tests import convert_to_test_assessment_response
    
    test_assessments_raw = TestCRUD.get_user_test_assessments(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    # Convert test assessments to proper response format
    test_assessments = []
    for assessment in test_assessments_raw:
        test_definition = TestCRUD.get_test_definition_by_id(db, assessment.test_definition_id)
        test_assessments.append(convert_to_test_assessment_response(assessment, test_definition))
    
    # Convert clinical assessments to unified format
    unified_assessments = []
    
    for assessment in clinical_assessments:
        unified_assessments.append({
            "id": assessment.id,
            "user_id": assessment.user_id,
            "type": "clinical",
            "assessment_type": assessment.assessment_type,
            "assessment_name": assessment.assessment_name,
            "test_code": assessment.assessment_type,
            "test_category": assessment.test_category or "clinical",
            "total_score": assessment.total_score,
            "max_score": assessment.max_score,
            "calculated_score": assessment.calculated_score or assessment.total_score,
            "severity_level": assessment.severity_level,
            "severity_label": assessment.severity_label or assessment.severity_level,
            "interpretation": assessment.interpretation,
            "recommendations": getattr(assessment, 'recommendations', None),
            "color_code": getattr(assessment, 'color_code', None),
            "responses": assessment.responses,
            "raw_responses": assessment.raw_responses or assessment.responses,
            "created_at": assessment.created_at
        })
    
    # Convert test assessments to unified format
    for assessment in test_assessments:
        unified_assessments.append({
            "id": assessment.id,
            "user_id": assessment.user_id,
            "type": "test",
            "assessment_type": assessment.test_code,
            "assessment_name": assessment.test_name,
            "test_code": assessment.test_code,
            "test_category": assessment.test_category,
            "total_score": assessment.calculated_score,
            "max_score": assessment.max_score,
            "calculated_score": assessment.calculated_score,
            "severity_level": assessment.severity_level,
            "severity_label": assessment.severity_label,
            "interpretation": assessment.interpretation,
            "recommendations": assessment.recommendations,
            "color_code": assessment.color_code,
            "responses": assessment.raw_responses,
            "raw_responses": assessment.raw_responses,
            "created_at": assessment.created_at
        })
    
    # Sort by created_at descending
    unified_assessments.sort(key=lambda x: x["created_at"], reverse=True)
    
    return unified_assessments

@router.get("/{assessment_id}", response_model=ClinicalAssessmentResponse)
def get_clinical_assessment(
    assessment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific clinical assessment by ID.
    
    - **assessment_id**: ID of the assessment to retrieve
    
    Users can only access their own assessments.
    """
    assessment = ClinicalAssessmentCRUD.get_clinical_assessment_by_id(
        db=db, 
        assessment_id=assessment_id
    )
    
    if not assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical assessment not found"
        )
    
    # Check if assessment belongs to current user
    if assessment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this assessment"
        )
    
    return assessment

@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_clinical_assessment(
    assessment_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Delete a specific clinical assessment.
    
    - **assessment_id**: ID of the assessment to delete
    
    Users can only delete their own assessments.
    """
    success = ClinicalAssessmentCRUD.delete_clinical_assessment(
        db=db, 
        assessment_id=assessment_id, 
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clinical assessment not found or not authorized to delete"
        )

@router.post("/assess-anonymous")
def perform_anonymous_clinical_assessment(assessment: ClinicalAssessmentRequest):
    """
    Perform anonymous clinical assessment (no authentication required, no data stored).
    
    - **assessment_type**: Type of assessment (phq9, gad7, pss10)
    - **responses**: List of question responses with scores (0-4)
    
    Returns assessment results without storing any data.
    """
    # Validate responses
    expected_questions = len(clinical_engine.get_questions(assessment.assessment_type))
    if len(assessment.responses) != expected_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Expected {expected_questions} responses for {assessment.assessment_type}, got {len(assessment.responses)}"
        )
    
    # Validate response scores
    for response in assessment.responses:
        if response.response < 0 or response.response > 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Response scores must be between 0 and 4, got {response.response}"
            )
    
    # Perform clinical assessment
    result = clinical_engine.assess(assessment.assessment_type, assessment.responses)
    
    return {
        "assessment": result,
        "disclaimer": "This is an anonymous assessment. No data is stored. For personalized tracking, please create an account."
    } 