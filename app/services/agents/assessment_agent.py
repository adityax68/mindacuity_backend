"""
Assessment Agent (OpenAI GPT-4/5)
Generates comprehensive mental health assessment reports
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from openai import AsyncOpenAI

from app.config import settings
from app.services.prompts import prompt_manager
from app.services.model_error_handler import error_handler, ModelInteractionLogger

logger = logging.getLogger(__name__)
interaction_logger = ModelInteractionLogger()


class AssessmentAgent:
    """
    Assessment Agent using OpenAI GPT
    Synthesizes diagnostic data into comprehensive clinical assessment
    """
    
    MODEL_NAME = "gpt-5"
    MAX_TOKENS = 3000  # INCREASED: GPT-5 needs more tokens for comprehensive reports
    TEMPERATURE = 1.0  # GPT-5 only supports default temperature of 1.0
    
    def __init__(self):
        """Initialize OpenAI client"""
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=30.0  # 30 second timeout
        )
        self.system_prompt = prompt_manager.ASSESSMENT_SYSTEM_PROMPT
    
    async def generate_assessment(
        self,
        session_id: str,
        condition: str,
        answers: Dict[str, Any],
        demographics: Optional[Dict[str, Any]] = None,
        risk_level: str = "moderate"
    ) -> Dict[str, Any]:
        """
        Generate comprehensive assessment report
        
        Args:
            session_id: Session identifier
            condition: Primary condition identified (anxiety, depression, stress)
            answers: Dictionary of all diagnostic answers
            demographics: Optional demographic information
            risk_level: Assessed risk level
            
        Returns:
            Dict with assessment report and metadata
        """
        try:
            # Build assessment prompt
            user_prompt = prompt_manager.get_assessment_prompt(
                condition=condition,
                answers=answers,
                demographics=demographics,
                risk_level=risk_level
            )
            
            # Log request
            interaction_logger.log_request(
                model_name=self.MODEL_NAME,
                session_id=session_id,
                prompt_preview=f"Generate assessment for {condition}",
                prompt_tokens=len(user_prompt) // 4,
                temperature=self.TEMPERATURE,
                max_tokens=self.MAX_TOKENS
            )
            
            start_time = datetime.utcnow()
            
            # Make API call with error handling
            async def api_call():
                # GPT-5 uses responses endpoint, not chat/completions
                response = await self.client.responses.create(
                    model=self.MODEL_NAME,
                    input=f"{self.system_prompt}\n\n{user_prompt}",
                    reasoning={"effort": "low"},
                    text={"verbosity": "medium"}
                )
                return response
            
            result = await error_handler.call_with_retry(
                model_func=api_call,
                model_name=self.MODEL_NAME,
                session_id=session_id,
                operation="assessment_generation"
            )
            
            if not result["success"]:
                # Return structured error
                return {
                    "success": False,
                    "error": result["user_message"],
                    "backend_details": result["backend_details"]
                }
            
            response = result["data"]
            
            # Calculate latency
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Log response (GPT-5 responses endpoint doesn't have usage info)
            interaction_logger.log_response(
                model_name=self.MODEL_NAME,
                session_id=session_id,
                completion_tokens=len(assessment_report) // 4,  # Rough estimate
                latency_ms=latency,
                cost_estimate=0.05  # Rough estimate for GPT-5 assessment
            )
            
            # Extract assessment report (GPT-5 responses endpoint format)
            assessment_report = response.output_text if hasattr(response, 'output_text') else str(response)
            assessment_report = assessment_report.strip()
            
            # Parse structured information from report
            structured_data = self._extract_structured_data(assessment_report, condition, answers)
            
            return {
                "success": True,
                "report": assessment_report,
                "structured": structured_data,
                "usage": {
                    "input_tokens": len(user_prompt) // 4,  # Rough estimate
                    "output_tokens": len(assessment_report) // 4,  # Rough estimate
                    "latency_ms": latency
                }
            }
            
        except Exception as e:
            logger.error(f"Assessment generation error for session {session_id}: {e}")
            return {
                "success": False,
                "error": "Assessment generation failed",
                "backend_details": {"error": str(e)}
            }
    
    def _extract_structured_data(
        self,
        report: str,
        condition: str,
        answers: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract structured data from assessment report
        For API consumers who need structured data
        """
        try:
            # Extract severity level from report
            severity = "moderate"  # Default
            report_lower = report.lower()
            
            if "**mild**" in report_lower or "severity: mild" in report_lower:
                severity = "mild"
            elif "**severe**" in report_lower or "severity: severe" in report_lower:
                severity = "severe"
            elif "**moderate**" in report_lower or "severity: moderate" in report_lower:
                severity = "moderate"
            
            # Extract recommendation type
            recommendation = "consult_professional"
            if "immediate" in report_lower or "urgent" in report_lower:
                recommendation = "immediate_intervention"
            elif "self-monitoring" in report_lower or "lifestyle" in report_lower:
                recommendation = "self_monitoring"
            
            # Build structured output
            return {
                "primary_condition": condition,
                "severity": severity,
                "recommendation": recommendation,
                "dimensions_assessed": list(answers.keys()),
                "assessment_completeness": len(answers) / 8.0,  # Assuming 8 ideal dimensions
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error extracting structured data: {e}")
            return {
                "primary_condition": condition,
                "severity": "moderate",
                "recommendation": "consult_professional",
                "error": "Failed to parse structured data"
            }
    
    async def generate_brief_summary(
        self,
        session_id: str,
        condition: str,
        severity: str,
        key_symptoms: list
    ) -> str:
        """
        Generate a brief 2-3 sentence summary (for UI previews)
        
        Args:
            session_id: Session identifier
            condition: Condition identified
            severity: Severity level
            key_symptoms: List of key symptoms
            
        Returns:
            Brief summary string
        """
        try:
            symptoms_text = ", ".join(key_symptoms[:3])
            
            prompt = f"""Generate a brief 2-3 sentence summary of this assessment:

Condition: {condition}
Severity: {severity}
Key symptoms: {symptoms_text}

Provide a compassionate, clear summary for the user."""
            
            async def api_call():
                # GPT-5 uses responses endpoint, not chat/completions
                response = await self.client.responses.create(
                    model=self.MODEL_NAME,
                    input=prompt,
                    reasoning={"effort": "minimal"},
                    text={"verbosity": "low"}
                )
                return response
            
            result = await error_handler.call_with_retry(
                model_func=api_call,
                model_name=self.MODEL_NAME,
                session_id=session_id,
                operation="summary_generation"
            )
            
            if result["success"]:
                response = result["data"]
                # GPT-5 responses endpoint format
                summary = response.output_text if hasattr(response, 'output_text') else str(response)
                return summary.strip()
            else:
                # Fallback summary
                return f"Based on your responses, you're experiencing {severity} {condition}. Professional consultation is recommended."
                
        except Exception as e:
            logger.error(f"Brief summary generation error: {e}")
            return f"Assessment complete for {condition}. Please see full report above."
    
    def validate_assessment_readiness(self, answers: Dict[str, Any]) -> Dict[str, bool]:
        """
        Validate if enough information is present for quality assessment
        
        Args:
            answers: Collected answers
            
        Returns:
            Dict with validation results
        """
        required_dimensions = ["duration", "frequency", "intensity"]
        recommended_dimensions = ["daily_impact", "triggers", "physical_symptoms"]
        
        has_required = all(dim in answers for dim in required_dimensions)
        recommended_count = sum(1 for dim in recommended_dimensions if dim in answers)
        
        return {
            "has_required": has_required,
            "recommended_coverage": recommended_count / len(recommended_dimensions),
            "is_ready": has_required and recommended_count >= 2,
            "missing_critical": [d for d in required_dimensions if d not in answers],
            "total_dimensions": len(answers)
        }


# Global instance
assessment_agent = AssessmentAgent()

