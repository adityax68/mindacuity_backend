from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field

class SeverityLevel(str, Enum):
    MINIMAL = "minimal"
    MILD = "mild"
    MODERATE = "moderate"
    MODERATELY_SEVERE = "moderately_severe"
    SEVERE = "severe"
    LOW = "low"
    HIGH = "high"

class AssessmentType(str, Enum):
    PHQ9 = "phq9"
    GAD7 = "gad7"
    PSS10 = "pss10"

class QuestionResponse(BaseModel):
    question_id: int
    response: int = Field(ge=0, le=4, description="Response score (0-4)")

class ClinicalAssessment(BaseModel):
    assessment_type: AssessmentType
    responses: List[QuestionResponse]
    total_score: Optional[int] = None
    severity_level: Optional[SeverityLevel] = None
    interpretation: Optional[str] = None

class ClinicalAssessmentEngine:
    """
    Clinical assessment engine using validated scales:
    - PHQ-9 (Patient Health Questionnaire-9) for depression
    - GAD-7 (Generalized Anxiety Disorder-7) for anxiety
    - PSS-10 (Perceived Stress Scale-10) for stress
    """
    
    def __init__(self):
        # PHQ-9 Questions for Depression
        self.phq9_questions = [
            "Little interest or pleasure in doing things",
            "Feeling down, depressed, or hopeless",
            "Trouble falling or staying asleep, or sleeping too much",
            "Feeling tired or having little energy",
            "Poor appetite or overeating",
            "Feeling bad about yourself - or that you are a failure or have let yourself or your family down",
            "Trouble concentrating on things, such as reading the newspaper or watching television",
            "Moving or speaking slowly enough that other people could have noticed. Or the opposite - being so fidgety or restless that you have been moving around a lot more than usual",
            "Thoughts that you would be better off dead or of hurting yourself in some way"
        ]
        
        # GAD-7 Questions for Anxiety
        self.gad7_questions = [
            "Feeling nervous, anxious, or on edge",
            "Not being able to stop or control worrying",
            "Worrying too much about different things",
            "Trouble relaxing",
            "Being so restless that it's hard to sit still",
            "Becoming easily annoyed or irritable",
            "Feeling afraid as if something awful might happen"
        ]
        
        # PSS-10 Questions for Stress
        self.pss10_questions = [
            "In the last month, how often have you been upset because of something that happened unexpectedly?",
            "In the last month, how often have you felt that you were unable to control the important things in your life?",
            "In the last month, how often have you felt nervous and stressed?",
            "In the last month, how often have you felt confident about your ability to handle your personal problems?",
            "In the last month, how often have you felt that things were going your way?",
            "In the last month, how often have you found that you could not cope with all the things that you had to do?",
            "In the last month, how often have you been able to control irritations in your life?",
            "In the last month, how often have you felt that you were on top of things?",
            "In the last month, how often have you been angered because of things that happened that were outside of your control?",
            "In the last month, how often have you felt difficulties were piling up so high that you could not overcome them?"
        ]
        
        # PSS-10 reverse scoring questions (4, 5, 7, 8) - these are scored in reverse
        self.pss10_reverse_questions = {4, 5, 7, 8}
    
    def get_questions(self, assessment_type: AssessmentType) -> List[str]:
        """Get questions for a specific assessment type."""
        if assessment_type == AssessmentType.PHQ9:
            return self.phq9_questions
        elif assessment_type == AssessmentType.GAD7:
            return self.gad7_questions
        elif assessment_type == AssessmentType.PSS10:
            return self.pss10_questions
        else:
            raise ValueError(f"Unknown assessment type: {assessment_type}")
    
    def calculate_phq9_score(self, responses: List[QuestionResponse]) -> Dict:
        """Calculate PHQ-9 depression score and severity."""
        if len(responses) != 9:
            raise ValueError("PHQ-9 requires exactly 9 responses")
        
        total_score = sum(response.response for response in responses)
        
        # Determine severity level
        if total_score <= 4:
            severity = SeverityLevel.MINIMAL
            interpretation = "Minimal depression - No treatment needed"
        elif total_score <= 9:
            severity = SeverityLevel.MILD
            interpretation = "Mild depression - Watchful waiting; repeat PHQ-9"
        elif total_score <= 14:
            severity = SeverityLevel.MODERATE
            interpretation = "Moderate depression - Treatment plan, counseling, follow-up"
        elif total_score <= 19:
            severity = SeverityLevel.MODERATELY_SEVERE
            interpretation = "Moderately severe depression - Active treatment with medication and/or therapy"
        else:
            severity = SeverityLevel.SEVERE
            interpretation = "Severe depression - Immediate treatment, medication and therapy"
        
        return {
            "total_score": total_score,
            "severity_level": severity,
            "interpretation": interpretation,
            "max_score": 27,
            "assessment_type": "PHQ-9"
        }
    
    def calculate_gad7_score(self, responses: List[QuestionResponse]) -> Dict:
        """Calculate GAD-7 anxiety score and severity."""
        if len(responses) != 7:
            raise ValueError("GAD-7 requires exactly 7 responses")
        
        total_score = sum(response.response for response in responses)
        
        # Determine severity level
        if total_score <= 4:
            severity = SeverityLevel.MINIMAL
            interpretation = "Minimal anxiety - No treatment needed"
        elif total_score <= 9:
            severity = SeverityLevel.MILD
            interpretation = "Mild anxiety - Watchful waiting; repeat GAD-7"
        elif total_score <= 14:
            severity = SeverityLevel.MODERATE
            interpretation = "Moderate anxiety - Treatment plan, counseling, follow-up"
        else:
            severity = SeverityLevel.SEVERE
            interpretation = "Severe anxiety - Active treatment with medication and/or therapy"
        
        return {
            "total_score": total_score,
            "severity_level": severity,
            "interpretation": interpretation,
            "max_score": 21,
            "assessment_type": "GAD-7"
        }
    
    def calculate_pss10_score(self, responses: List[QuestionResponse]) -> Dict:
        """Calculate PSS-10 stress score and severity."""
        if len(responses) != 10:
            raise ValueError("PSS-10 requires exactly 10 responses")
        
        total_score = 0
        
        for i, response in enumerate(responses):
            # PSS-10 uses 0-4 scale, but questions 4, 5, 7, 8 are reverse scored
            if i + 1 in self.pss10_reverse_questions:
                # Reverse scoring: 0→4, 1→3, 2→2, 3→1, 4→0
                score = 4 - response.response
            else:
                score = response.response
            
            total_score += score
        
        # Determine severity level
        if total_score <= 13:
            severity = SeverityLevel.LOW
            interpretation = "Low stress - Good stress management"
        elif total_score <= 26:
            severity = SeverityLevel.MODERATE
            interpretation = "Moderate stress - Consider stress management techniques"
        else:
            severity = SeverityLevel.HIGH
            interpretation = "High stress - Consider professional help for stress management"
        
        return {
            "total_score": total_score,
            "severity_level": severity,
            "interpretation": interpretation,
            "max_score": 40,
            "assessment_type": "PSS-10"
        }
    
    def assess(self, assessment_type: AssessmentType, responses: List[QuestionResponse]) -> Dict:
        """Perform clinical assessment based on type and responses."""
        if assessment_type == AssessmentType.PHQ9:
            return self.calculate_phq9_score(responses)
        elif assessment_type == AssessmentType.GAD7:
            return self.calculate_gad7_score(responses)
        elif assessment_type == AssessmentType.PSS10:
            return self.calculate_pss10_score(responses)
        else:
            raise ValueError(f"Unknown assessment type: {assessment_type}")
    
    def get_assessment_summary(self, assessments: List[Dict]) -> Dict:
        """Generate summary from multiple clinical assessments."""
        summary = {
            "total_assessments": len(assessments),
            "assessments": assessments,
            "overall_risk_level": "low",
            "recommendations": []
        }
        
        # Determine overall risk level
        high_risk_count = 0
        moderate_risk_count = 0
        
        for assessment in assessments:
            severity = assessment.get("severity_level")
            if severity in [SeverityLevel.SEVERE, SeverityLevel.MODERATELY_SEVERE, SeverityLevel.HIGH]:
                high_risk_count += 1
            elif severity in [SeverityLevel.MODERATE]:
                moderate_risk_count += 1
        
        if high_risk_count > 0:
            summary["overall_risk_level"] = "high"
            summary["recommendations"].append("Immediate professional consultation recommended")
        elif moderate_risk_count > 0:
            summary["overall_risk_level"] = "medium"
            summary["recommendations"].append("Consider professional consultation")
        else:
            summary["recommendations"].append("Continue monitoring mental health")
        
        return summary

# Global instance
clinical_engine = ClinicalAssessmentEngine() 