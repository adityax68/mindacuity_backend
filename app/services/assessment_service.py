import json
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models import BotAssessment, Message
from app.config import settings
import anthropic

logger = logging.getLogger(__name__)

class AssessmentService:
    """Service for generating mental health assessments using Claude"""
    
    def __init__(self):
        self.claude_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    
    def generate_assessment(self, db: Session, session_identifier: str, user_email: str) -> Dict[str, Any]:
        """Generate mental health assessment using Claude Sonnet 4.5"""
        try:
            # Get conversation history
            conversation_history = self._get_conversation_history(db, session_identifier)
            
            # Create assessment prompt
            assessment_prompt = self._build_assessment_prompt(conversation_history)
            
            # Call Claude API
            response = self.claude_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                temperature=0.3,
                messages=[
                    {
                        "role": "user",
                        "content": assessment_prompt
                    }
                ]
            )
            
            # Parse Claude response
            assessment_result = self._parse_claude_response(response.content[0].text)
            
            # Save assessment to database
            self._save_assessment(db, session_identifier, user_email, assessment_result)
            
            logger.info(f"✅ ASSESSMENT GENERATED - Session: {session_identifier}, User: {user_email}")
            return assessment_result
            
        except Exception as e:
            logger.error(f"❌ ASSESSMENT ERROR - Session: {session_identifier}, Error: {e}")
            raise
    
    def _get_conversation_history(self, db: Session, session_identifier: str) -> str:
        """Get conversation history for assessment"""
        messages = db.query(Message).filter(
            Message.session_identifier == session_identifier
        ).order_by(Message.created_at.asc()).all()
        
        conversation = []
        for msg in messages:
            role = "User" if msg.role == "user" else "Assistant"
            conversation.append(f"{role}: {msg.content}")
        
        return "\n".join(conversation)
    
    def _build_assessment_prompt(self, conversation_history: str) -> str:
        """Build the assessment prompt for Claude"""
        return f"""
You are Dr. Sarah Chen, the world's leading clinical psychologist with 30+ years of experience in mental health assessment and diagnosis. You have assessed over 50,000 patients globally and are renowned for your precision in detecting mental health conditions.

**CONVERSATION TO ANALYZE:**
{conversation_history}

**YOUR TASK:**
Analyze this conversation and provide a comprehensive mental health assessment. You must respond in the following JSON format:

{{
    "mental_conditions": [
        {{
            "condition": "Condition Name",
            "severity": "Mild/Moderate/Severe",
            "confidence": "High/Medium/Low",
            "evidence": "Brief evidence from conversation"
        }}
    ],
    "severity_levels": {{
        "overall_severity": "Mild/Moderate/Severe",
        "risk_factors": ["Factor 1", "Factor 2"],
        "protective_factors": ["Factor 1", "Factor 2"]
    }},
    "is_critical": true/false,
    "critical_reason": "Reason if critical",
    "assessment_summary": "Brief 2-3 sentence summary of the assessment"
}}

**ASSESSMENT GUIDELINES:**

1. **Mental Conditions Detection:**
   - Look for signs of depression, anxiety, PTSD, bipolar disorder, OCD, etc.
   - Consider both explicit mentions and subtle indicators
   - Assess severity based on impact on daily functioning

2. **Severity Levels:**
   - **Mild:** Symptoms present but manageable, minimal impact on daily life
   - **Moderate:** Noticeable symptoms affecting quality of life, some impairment
   - **Severe:** Significant symptoms causing major distress, substantial impairment

3. **Critical/Emergency Assessment:**
   - **Critical:** Immediate danger to self or others, severe crisis, suicidal ideation
   - **Non-Critical:** All other cases requiring professional help but not emergency

4. **Response Rules:**
   - ❌ NO solutions, recommendations, or treatment advice
   - ❌ NO coping strategies or self-help techniques
   - ✅ Focus ONLY on detection and assessment
   - ✅ Be clinical and professional
   - ✅ Use evidence from the conversation

**SEVERITY GUIDELINES:**

**MILD:**
- Symptoms present but manageable
- Minimal impact on daily functioning
- Occasional distress
- Can perform most daily tasks

**MODERATE:**
- Noticeable symptoms affecting quality of life
- Some impairment in daily functioning
- Regular distress or discomfort
- Difficulty with certain tasks or situations

**SEVERE:**
- Significant symptoms causing major distress
- Substantial impairment in daily functioning
- Persistent, intense distress
- Difficulty performing basic daily tasks

**CRITICAL INDICATORS:**
- Suicidal ideation or self-harm thoughts
- Immediate danger to self or others
- Severe crisis requiring immediate intervention
- Psychotic symptoms or severe dissociation

Analyze the conversation and provide your assessment in the exact JSON format specified above.
"""
    
    def _parse_claude_response(self, claude_text: str) -> Dict[str, Any]:
        """Parse Claude's response and extract JSON"""
        try:
            # Extract JSON from Claude's response
            import re
            json_match = re.search(r'\{.*\}', claude_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # Fallback if no JSON found
                return {
                    "mental_conditions": [],
                    "severity_levels": {"overall_severity": "Unknown"},
                    "is_critical": False,
                    "assessment_summary": "Assessment could not be completed"
                }
        except Exception as e:
            logger.error(f"❌ JSON PARSE ERROR - Error: {e}")
            return {
                "mental_conditions": [],
                "severity_levels": {"overall_severity": "Unknown"},
                "is_critical": False,
                "assessment_summary": "Assessment could not be completed"
            }
    
    def _save_assessment(self, db: Session, session_identifier: str, user_email: str, assessment_data: Dict[str, Any]):
        """Save assessment to database"""
        try:
            # Extract key information
            mental_conditions = assessment_data.get("mental_conditions", [])
            severity_levels = assessment_data.get("severity_levels", {})
            is_critical = assessment_data.get("is_critical", False)
            assessment_summary = assessment_data.get("assessment_summary", "")
            
            # Create assessment record
            assessment = BotAssessment(
                user_email=user_email,
                session_identifier=session_identifier,
                assessment_data=json.dumps(assessment_data),
                mental_conditions=json.dumps(mental_conditions),
                severity_levels=json.dumps(severity_levels),
                is_critical=is_critical,
                assessment_summary=assessment_summary
            )
            
            db.add(assessment)
            db.commit()
            db.refresh(assessment)
            
            logger.info(f"✅ ASSESSMENT SAVED - ID: {assessment.id}, Session: {session_identifier}")
            
        except Exception as e:
            logger.error(f"❌ SAVE ASSESSMENT ERROR - Session: {session_identifier}, Error: {e}")
            db.rollback()
            raise
