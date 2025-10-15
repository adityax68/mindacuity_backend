"""
Diagnostic Agent (OpenAI GPT-4/5)
Generates dynamic, context-aware diagnostic questions
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


class DiagnosticAgent:
    """
    Diagnostic Agent using OpenAI GPT
    Generates contextual diagnostic questions based on condition and progress
    """
    
    MODEL_NAME = "gpt-5"
    MAX_TOKENS = 150
    TEMPERATURE = 0.7
    
    def __init__(self):
        """Initialize OpenAI client"""
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")
        
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=30.0  # 30 second timeout
        )
        self.system_prompt = prompt_manager.DIAGNOSTIC_SYSTEM_PROMPT
    
    async def generate_question(
        self,
        session_id: str,
        condition: str,
        dimension_needed: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate diagnostic question based on condition and needed dimension
        
        Args:
            session_id: Session identifier
            condition: Primary condition (anxiety, depression, stress)
            dimension_needed: Dimension to explore (duration, frequency, intensity, etc.)
            context: Additional context (last answer, state)
            
        Returns:
            Dict with question and metadata
        """
        try:
            # Try pre-written question first (faster, no API call)
            pre_written = prompt_manager.get_condition_question(condition, dimension_needed)
            if pre_written and not context:
                # Use pre-written for first-time questions without specific context
                return {
                    "success": True,
                    "question": pre_written,
                    "dimension": dimension_needed,
                    "source": "pre_written",
                    "usage": {
                        "input_tokens": 0,
                        "output_tokens": 0,
                        "latency_ms": 0
                    }
                }
            
            # Generate dynamic question with AI
            return await self._generate_dynamic_question(
                session_id=session_id,
                condition=condition,
                dimension_needed=dimension_needed,
                context=context
            )
            
        except Exception as e:
            logger.error(f"Diagnostic agent error for session {session_id}: {e}")
            return {
                "success": False,
                "error": "Question generation failed",
                "backend_details": {"error": str(e)}
            }
    
    async def _generate_dynamic_question(
        self,
        session_id: str,
        condition: str,
        dimension_needed: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate dynamic question using GPT
        """
        try:
            # Build contextual prompt
            user_prompt = self._build_question_prompt(
                condition=condition,
                dimension=dimension_needed,
                context=context
            )
            
            # Log request
            interaction_logger.log_request(
                model_name=self.MODEL_NAME,
                session_id=session_id,
                prompt_preview=f"Generate {dimension_needed} question for {condition}",
                prompt_tokens=len(user_prompt) // 4,
                temperature=self.TEMPERATURE,
                max_tokens=self.MAX_TOKENS
            )
            
            start_time = datetime.utcnow()
            
            # Make API call with error handling
            async def api_call():
                response = await self.client.chat.completions.create(
                    model=self.MODEL_NAME,
                    max_completion_tokens=self.MAX_TOKENS,  # GPT-5 uses max_completion_tokens
                    temperature=self.TEMPERATURE,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                return response
            
            result = await error_handler.call_with_retry(
                model_func=api_call,
                model_name=self.MODEL_NAME,
                session_id=session_id,
                operation="question_generation"
            )
            
            if not result["success"]:
                # Fallback to pre-written question
                fallback = prompt_manager.get_condition_question(condition, dimension_needed)
                if fallback:
                    return {
                        "success": True,
                        "question": fallback,
                        "dimension": dimension_needed,
                        "source": "fallback",
                        "error_details": result
                    }
                
                return result
            
            response = result["data"]
            
            # Calculate latency
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Log response
            interaction_logger.log_response(
                model_name=self.MODEL_NAME,
                session_id=session_id,
                completion_tokens=response.usage.completion_tokens,
                latency_ms=latency,
                cost_estimate=error_handler.calculate_cost(
                    self.MODEL_NAME,
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens
                )
            )
            
            # Extract question
            question = response.choices[0].message.content.strip()
            
            # Clean up common artifacts
            question = self._clean_question(question)
            
            return {
                "success": True,
                "question": question,
                "dimension": dimension_needed,
                "source": "generated",
                "usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens,
                    "latency_ms": latency
                }
            }
            
        except Exception as e:
            logger.error(f"Dynamic question generation error: {e}")
            
            # Fallback to pre-written
            fallback = prompt_manager.get_condition_question(condition, dimension_needed)
            if fallback:
                return {
                    "success": True,
                    "question": fallback,
                    "dimension": dimension_needed,
                    "source": "fallback_on_error"
                }
            
            return {
                "success": False,
                "error": "Question generation failed",
                "backend_details": {"error": str(e)}
            }
    
    def _build_question_prompt(
        self,
        condition: str,
        dimension: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build prompt for question generation
        """
        prompt_parts = [f"Generate ONE diagnostic question for {condition}."]
        prompt_parts.append(f"Information needed: {dimension}")
        
        if context:
            if "last_answer" in context:
                prompt_parts.append(f"\nUser's last answer: {context['last_answer']}")
            
            if "questions_asked" in context:
                prompt_parts.append(f"Questions already asked: {context['questions_asked']}")
            
            if "answers_collected" in context:
                answered = ", ".join(context["answers_collected"].keys())
                prompt_parts.append(f"Dimensions already explored: {answered}")
        
        prompt_parts.append(
            f"\nGenerate a natural, conversational question about {dimension}. "
            "Ask ONLY the question, no labels or formatting."
        )
        
        return "\n".join(prompt_parts)
    
    def _clean_question(self, question: str) -> str:
        """
        Clean up generated question
        Remove common artifacts and formatting issues
        """
        # Remove common prefixes
        prefixes_to_remove = [
            "Question:",
            "Here's the question:",
            "**Question:**",
            f"**{self.MODEL_NAME}:**"
        ]
        
        for prefix in prefixes_to_remove:
            if question.startswith(prefix):
                question = question[len(prefix):].strip()
        
        # Remove markdown formatting
        question = question.replace("**", "").replace("*", "")
        
        # Remove quotes
        if question.startswith('"') and question.endswith('"'):
            question = question[1:-1]
        if question.startswith("'") and question.endswith("'"):
            question = question[1:-1]
        
        # Ensure ends with question mark
        if not question.endswith("?"):
            question += "?"
        
        return question.strip()
    
    def get_followup_question(
        self,
        session_id: str,
        user_answer: str,
        original_dimension: str
    ) -> str:
        """
        Generate a quick follow-up question for clarification
        (Synchronous, uses pre-written templates)
        
        Args:
            session_id: Session identifier
            user_answer: User's previous answer
            original_dimension: What we were asking about
            
        Returns:
            Follow-up question string
        """
        answer_lower = user_answer.lower()
        
        # Check if answer is too vague
        vague_indicators = ["maybe", "i don't know", "not sure", "unclear", "kind of", "sort of"]
        
        if any(indicator in answer_lower for indicator in vague_indicators):
            clarification_questions = {
                "duration": "Could you give me an approximate timeframe? For example, a few days, weeks, or months?",
                "frequency": "Would you say it happens more often than not, or just occasionally?",
                "intensity": "If you had to choose a number between 1 and 10, what would it be?",
                "triggers": "Think about the last time it happened - what was going on?",
                "daily_impact": "Has it affected your sleep, work, or relationships in any way?",
                "physical_symptoms": "Have you noticed any changes in how your body feels?",
                "coping": "Have you tried anything at all, even small things?",
                "support_system": "Is there anyone you feel comfortable talking to about how you're feeling?"
            }
            return clarification_questions.get(
                original_dimension,
                "Could you tell me a bit more about that?"
            )
        
        # Answer seems clear, continue to next dimension
        return None


# Global instance
diagnostic_agent = DiagnosticAgent()

