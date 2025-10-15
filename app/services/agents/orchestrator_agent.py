"""
Orchestrator Agent (Anthropic Claude)
Classifies intent, detects emotion, assesses risk, and provides empathy
OPTIMIZED: Combines classification + empathy in single API call
"""

import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import anthropic

from app.config import settings
from app.services.prompts import prompt_manager
from app.services.model_error_handler import error_handler, ModelInteractionLogger

logger = logging.getLogger(__name__)
interaction_logger = ModelInteractionLogger()


class OrchestratorAgent:
    """
    Orchestrator Agent using Anthropic Claude
    Handles: classification, emotion detection, crisis check, empathy response
    
    OPTIMIZATION: Single API call combines all orchestration tasks
    """
    
    MODEL_NAME = "claude-sonnet-4-5-20250929"
    MAX_TOKENS = 500
    TEMPERATURE = 0.7
    
    def __init__(self):
        """Initialize Anthropic client"""
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")
        
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.system_prompt = prompt_manager.ORCHESTRATOR_SYSTEM_PROMPT
    
    async def classify_and_respond(
        self,
        user_message: str,
        session_id: str,
        conversation_context: Optional[list] = None,
        state_summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Classify message and generate empathetic response in ONE API call
        
        Args:
            user_message: User's message
            session_id: Session identifier
            conversation_context: Recent conversation history
            state_summary: Current conversation state
            
        Returns:
            Dict with classification and empathy response
        """
        try:
            # Build prompt with context
            user_prompt = self._build_user_prompt(
                user_message=user_message,
                context=conversation_context,
                state=state_summary
            )
            
            # Log request
            interaction_logger.log_request(
                model_name=self.MODEL_NAME,
                session_id=session_id,
                prompt_preview=user_message,
                prompt_tokens=len(user_prompt) // 4,  # Rough estimate
                temperature=self.TEMPERATURE,
                max_tokens=self.MAX_TOKENS
            )
            
            start_time = datetime.utcnow()
            
            # Make API call with error handling
            async def api_call():
                response = self.client.messages.create(
                    model=self.MODEL_NAME,
                    max_tokens=self.MAX_TOKENS,
                    temperature=self.TEMPERATURE,
                    system=self.system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                )
                return response
            
            result = await error_handler.call_with_retry(
                model_func=api_call,
                model_name=self.MODEL_NAME,
                session_id=session_id,
                operation="orchestration"
            )
            
            if not result["success"]:
                # Return error response
                return {
                    "success": False,
                    "error": result["user_message"],
                    "backend_details": result["backend_details"]
                }
            
            response = result["data"]
            
            # Calculate latency
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Log response
            interaction_logger.log_response(
                model_name=self.MODEL_NAME,
                session_id=session_id,
                completion_tokens=response.usage.output_tokens,
                latency_ms=latency,
                cost_estimate=error_handler.calculate_cost(
                    self.MODEL_NAME,
                    response.usage.input_tokens,
                    response.usage.output_tokens
                )
            )
            
            # Parse response
            content = response.content[0].text
            parsed = self._parse_response(content)
            
            return {
                "success": True,
                "classification": parsed,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "latency_ms": latency
                }
            }
            
        except Exception as e:
            logger.error(f"Orchestrator error for session {session_id}: {e}")
            return {
                "success": False,
                "error": "Classification failed",
                "backend_details": {"error": str(e)}
            }
    
    def _build_user_prompt(
        self,
        user_message: str,
        context: Optional[list] = None,
        state: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build user prompt with context and state
        """
        prompt_parts = []
        
        # Add state summary if available
        if state:
            prompt_parts.append(f"""CONVERSATION STATE:
- Phase: {state.get('phase', 'initial')}
- Questions asked: {state.get('questions_asked', 0)}
- Condition hypothesis: {', '.join(state.get('condition_hypothesis', []))}
- Risk level: {state.get('risk_level', 'unknown')}
""")
        
        # Add recent context if available
        if context and len(context) > 0:
            prompt_parts.append("RECENT CONVERSATION:")
            for msg in context[-4:]:  # Last 2 exchanges
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:100]  # Truncate long messages
                prompt_parts.append(f"{role.capitalize()}: {content}")
            prompt_parts.append("")
        
        # Add current user message
        prompt_parts.append(f"USER'S CURRENT MESSAGE:\n{user_message}")
        
        # Add instruction
        prompt_parts.append("\nAnalyze this message and provide classification in JSON format as specified in your system prompt.")
        
        return "\n".join(prompt_parts)
    
    def _parse_response(self, content: str) -> Dict[str, Any]:
        """
        Parse JSON response from Claude
        Handles cases where response might not be perfect JSON
        """
        try:
            # Try to extract JSON from response
            # Look for content between { and }
            start = content.find('{')
            end = content.rfind('}') + 1
            
            if start != -1 and end > start:
                json_str = content[start:end]
                parsed = json.loads(json_str)
                
                # Ensure all required fields exist
                return {
                    "intent": parsed.get("intent", "unknown"),
                    "emotional_state": parsed.get("emotional_state", "neutral"),
                    "condition_hypothesis": parsed.get("condition_hypothesis", []),
                    "risk_level": parsed.get("risk_level", "low"),
                    "is_crisis": parsed.get("is_crisis", False),
                    "is_off_topic": parsed.get("is_off_topic", False),
                    "sentiment": parsed.get("sentiment", {"valence": 0.0, "arousal": 0.0}),
                    "empathy_response": parsed.get("empathy_response", ""),
                    "next_action": parsed.get("next_action", "ask_diagnostic_question"),
                    "reasoning": parsed.get("reasoning", "")
                }
            else:
                logger.warning(f"Could not find JSON in response: {content[:200]}")
                return self._default_classification()
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}. Content: {content[:200]}")
            return self._default_classification()
        except Exception as e:
            logger.error(f"Unexpected parsing error: {e}")
            return self._default_classification()
    
    def _default_classification(self) -> Dict[str, Any]:
        """
        Return default classification when parsing fails
        """
        return {
            "intent": "seeking_assessment",
            "emotional_state": "neutral",
            "condition_hypothesis": ["general"],
            "risk_level": "low",
            "is_crisis": False,
            "is_off_topic": False,
            "sentiment": {"valence": 0.0, "arousal": 0.0},
            "empathy_response": "I understand. Let me help assess what you're experiencing.",
            "next_action": "ask_diagnostic_question",
            "reasoning": "Default classification due to parsing error"
        }
    
    def classify_dimension(self, user_answer: str, expected_dimension: str) -> Optional[str]:
        """
        Quick classification of which dimension an answer addresses
        Used to track progress
        
        Args:
            user_answer: User's answer
            expected_dimension: What we were asking about
            
        Returns:
            Dimension name or None
        """
        # Simple keyword matching (fast, no API call needed)
        answer_lower = user_answer.lower()
        
        DIMENSION_KEYWORDS = {
            "duration": ["week", "month", "day", "year", "ago", "since", "long"],
            "frequency": ["daily", "often", "sometimes", "always", "never", "occasionally", "frequent"],
            "intensity": ["scale", "level", "severe", "mild", "intense", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
            "triggers": ["when", "situation", "event", "cause", "trigger", "because", "after"],
            "daily_impact": ["work", "sleep", "relationship", "eat", "concentrate", "function", "affect"],
            "physical_symptoms": ["headache", "pain", "tired", "fatigue", "tension", "physical", "body"],
            "coping": ["try", "tried", "manage", "cope", "help", "therapy", "medication"],
            "support_system": ["talk", "friend", "family", "support", "people", "someone", "alone"]
        }
        
        # Check if answer contains keywords for expected dimension
        if expected_dimension in DIMENSION_KEYWORDS:
            keywords = DIMENSION_KEYWORDS[expected_dimension]
            if any(keyword in answer_lower for keyword in keywords):
                return expected_dimension
        
        # Check other dimensions
        for dimension, keywords in DIMENSION_KEYWORDS.items():
            if any(keyword in answer_lower for keyword in keywords):
                return dimension
        
        # Default to expected dimension
        return expected_dimension


# Global instance
orchestrator_agent = OrchestratorAgent()

