"""
Optimized Session Chat Service with Multi-Agent Orchestration
Uses Redis caching, modular agents, and optimized API call patterns
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.models import Conversation
from app.schemas import SessionChatMessageRequest, SessionChatResponse
from app.services.subscription_service import SubscriptionService
from app.services.optimized_message_store import OptimizedMessageHistoryStore
from app.services.conversation_state_manager import conversation_state_manager
from app.services.assessment_trigger import assessment_trigger
from app.services.agents import orchestrator_agent, diagnostic_agent, assessment_agent
from app.services.prompts import prompt_manager
from app.services.redis_client import redis_client

logger = logging.getLogger(__name__)


class OptimizedSessionChatService:
    """
    Optimized chat service with multi-agent architecture
    
    Features:
    - Redis-based caching for state and messages
    - Multi-agent orchestration (Orchestrator -> Specialist)
    - Optimized 2 API calls per message (instead of 3)
    - Error handling with retry logic
    - Message length validation
    - Off-topic detection
    - Crisis detection
    """
    
    MAX_MESSAGE_LENGTH = 400
    
    def __init__(self):
        self.subscription_service = SubscriptionService()
        self.state_manager = conversation_state_manager
        self.redis = redis_client
    
    async def process_chat_message(
        self,
        db: Session,
        session_identifier: str,
        chat_request: SessionChatMessageRequest
    ) -> SessionChatResponse:
        """
        Process chat message with multi-agent orchestration
        
        Flow:
        1. Check usage limits
        2. Validate message length
        3. Get state and context from Redis
        4. Orchestrator: Classify + generate empathy (1 API call)
        5. Handle special cases (crisis, off-topic)
        6. Specialist: Generate question or assessment (1 API call)
        7. Update state and cache
        8. Return response
        
        Total: 2 API calls for normal flow
        """
        try:
            # 1. Check usage limit
            usage_info = self.subscription_service.check_usage_limit(
                db, session_identifier, allow_orphaned_reuse=False
            )
            
            if not usage_info["can_send"]:
                return self._create_subscription_required_response(
                    session_identifier, usage_info
                )
            
            # 2. Validate message length
            if len(chat_request.message) > self.MAX_MESSAGE_LENGTH:
                return SessionChatResponse(
                    message=f"Message too long. Please keep responses under {self.MAX_MESSAGE_LENGTH} characters.",
                    conversation_id=session_identifier,
                    requires_subscription=False,
                    messages_used=usage_info["messages_used"],
                    message_limit=usage_info["message_limit"],
                    plan_type=usage_info["plan_type"]
                )
            
            # 3. Get conversation context
            conversation = self.subscription_service.create_or_get_conversation(db, session_identifier)
            message_store = OptimizedMessageHistoryStore(db)
            state = self.state_manager.get_state(session_identifier)
            
            # Get recent context from Redis (fast!)
            context = message_store.get_context_for_llm(session_identifier, max_messages=6)
            state_summary = self.state_manager.get_state_summary(session_identifier)
            
            # 4. ORCHESTRATOR CALL (API Call #1)
            # Classifies intent, detects emotion, checks crisis, generates empathy
            orchestrator_result = await orchestrator_agent.classify_and_respond(
                user_message=chat_request.message,
                session_id=session_identifier,
                conversation_context=context,
                state_summary=state_summary
            )
            
            if not orchestrator_result["success"]:
                return self._create_error_response(
                    session_identifier, 
                    orchestrator_result["error"],
                    usage_info
                )
            
            classification = orchestrator_result["classification"]
            
            # Save user message immediately
            message_store.add_user_message(session_identifier, chat_request.message)
            
            # 5. Handle special cases (no additional API calls)
            
            # Crisis check
            if classification["is_crisis"]:
                response_message = prompt_manager.CRISIS_RESPONSE
                message_store.add_assistant_message(session_identifier, response_message)
                self.state_manager.set_risk_level(session_identifier, "crisis")
                self.state_manager.set_phase(session_identifier, "complete")
                
                return self._create_success_response(
                    session_identifier, response_message, usage_info
                )
            
            # Off-topic check
            if classification["is_off_topic"]:
                off_topic_count = self.state_manager.increment_off_topic_count(session_identifier)
                
                redirect_message = prompt_manager.get_off_topic_response(classification["intent"])
                message_store.add_assistant_message(session_identifier, redirect_message)
                
                # If too many off-topic messages, end conversation
                if off_topic_count >= 3:
                    self.state_manager.set_phase(session_identifier, "complete")
                
                return self._create_success_response(
                    session_identifier, redirect_message, usage_info
                )
            
            # 6. Update state with orchestrator insights
            if classification["condition_hypothesis"]:
                self.state_manager.set_condition_hypothesis(
                    session_identifier,
                    classification["condition_hypothesis"]
                )
            
            if classification["sentiment"]:
                self.state_manager.set_sentiment(
                    session_identifier,
                    classification["sentiment"]
                )
            
            if classification["risk_level"]:
                self.state_manager.set_risk_level(
                    session_identifier,
                    classification["risk_level"]
                )
            
            # 7. Route to appropriate specialist based on phase and progress
            
            # Check if this is first message
            if state.phase == "initial" and state.questions_asked == 0:
                # First interaction - use greeting + empathy
                response_message = self._build_initial_response(classification)
                message_store.add_assistant_message(session_identifier, response_message)
                self.state_manager.set_phase(session_identifier, "gathering")
                
                return self._create_success_response(
                    session_identifier, response_message, usage_info
                )
            
            # Check if we need demographics (ask all at once)
            if state.phase == "gathering" and self._need_demographics(state, classification):
                # Check if demographics are completely empty
                if not state.demographics or len(state.demographics) == 0:
                    # Ask for all demographics in one message
                    demographic_question = prompt_manager.get_demographic_question("all")
                    response_message = self._build_response_with_empathy(
                        classification["empathy_response"],
                        demographic_question
                    )
                    message_store.add_assistant_message(session_identifier, response_message)
                    
                    return self._create_success_response(
                        session_identifier, response_message, usage_info
                    )
            
            # Check if we're answering a demographic question (asked all at once)
            if self._is_demographic_response(message_store, session_identifier, state):
                # Parse all demographics from one response
                self._save_all_demographics_from_response(session_identifier, chat_request.message, state)
                
                # Done with demographics, start diagnostic questions
                next_dimension = assessment_trigger.get_next_dimension_needed(session_identifier)
                condition = state.condition_hypothesis[0] if state.condition_hypothesis else "general"
                
                question_result = await diagnostic_agent.generate_question(
                    session_id=session_identifier,
                    condition=condition,
                    dimension_needed=next_dimension,
                    context={"phase": "starting_diagnostics"}
                )
                
                if question_result["success"]:
                    response_message = self._build_response_with_empathy(
                        classification["empathy_response"],
                        question_result["question"]
                    )
                else:
                    # Fallback if GPT fails
                    response_message = self._build_response_with_empathy(
                        classification["empathy_response"],
                        "How long have you been experiencing these feelings? Days, weeks, or months?"
                    )
                
                message_store.add_assistant_message(session_identifier, response_message)
                return self._create_success_response(
                    session_identifier, response_message, usage_info
                )
            
            # Check if we should trigger assessment
            should_assess, reason = assessment_trigger.should_trigger_assessment(session_identifier)
            
            if should_assess:
                # ASSESSMENT CALL (API Call #2)
                assessment_result = await self._generate_assessment(
                    session_identifier, state, classification
                )
                
                response_message = self._build_response_with_empathy(
                    classification["empathy_response"],
                    assessment_result
                )
                message_store.add_assistant_message(session_identifier, response_message)
                self.state_manager.set_phase(session_identifier, "complete")
                
                return self._create_success_response(
                    session_identifier, response_message, usage_info
                )
            
            # 8. Continue diagnostic questioning (API Call #2)
            # Track the answer
            if classification["intent"] == "answering_question":
                # Extract dimension from last question context
                last_message = message_store.get_last_message(session_identifier)
                if last_message and last_message["role"] == "assistant":
                    # Infer dimension from previous question
                    dimension = self._infer_dimension_from_context(state)
                    if dimension:
                        assessment_trigger.mark_dimension_answered(
                            session_identifier,
                            dimension,
                            chat_request.message
                        )
            
            # Generate next diagnostic question
            next_dimension = assessment_trigger.get_next_dimension_needed(session_identifier)
            condition = state.condition_hypothesis[0] if state.condition_hypothesis else "general"
            
            question_result = await diagnostic_agent.generate_question(
                session_id=session_identifier,
                condition=condition,
                dimension_needed=next_dimension,
                context={
                    "last_answer": chat_request.message,
                    "questions_asked": state.questions_asked,
                    "answers_collected": state.answers_collected
                }
            )
            
            if question_result["success"]:
                response_message = self._build_response_with_empathy(
                    classification["empathy_response"],
                    question_result["question"]
                )
            else:
                # Fallback question
                response_message = self._build_response_with_empathy(
                    classification["empathy_response"],
                    "Could you tell me more about how this is affecting your daily life?"
                )
            
            # Save assistant response
            message_store.add_assistant_message(session_identifier, response_message)
            
            # 9. Increment usage and return
            self.subscription_service.increment_usage(db, session_identifier)
            updated_usage = self.subscription_service.check_usage_limit(
                db, session_identifier, allow_orphaned_reuse=False
            )
            
            return self._create_success_response(
                session_identifier, response_message, updated_usage
            )
            
        except Exception as e:
            logger.error(f"Error processing chat message for {session_identifier}: {e}")
            
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")
            
            current_usage = self.subscription_service.check_usage_limit(
                db, session_identifier, allow_orphaned_reuse=False
            )
            
            return SessionChatResponse(
                message="I'm sorry, I encountered an error. Please try again.",
                conversation_id=session_identifier,
                requires_subscription=False,
                messages_used=current_usage.get("messages_used", 0),
                message_limit=current_usage.get("message_limit", None),
                plan_type=current_usage.get("plan_type", "free")
            )
    
    def _build_initial_response(self, classification: Dict[str, Any]) -> str:
        """Build initial greeting response"""
        empathy = classification.get("empathy_response", "")
        
        # Use greeting + empathy
        greeting = prompt_manager.INITIAL_GREETING
        
        if empathy:
            return f"{greeting}\n\n{empathy}"
        
        return greeting
    
    def _build_response_with_empathy(self, empathy: str, main_content: str) -> str:
        """Combine empathy with main response"""
        if empathy and empathy.strip():
            return f"{empathy}\n\n{main_content}"
        return main_content
    
    def _need_demographics(self, state, classification) -> bool:
        """Check if we need to collect demographics"""
        # Only collect if sentiment is negative and not yet collected
        if state.demographics:
            return False
        
        sentiment = classification.get("sentiment", {})
        valence = sentiment.get("valence", 0)
        
        # Negative sentiment (valence < -0.3)
        return valence < -0.3 and state.questions_asked < 3
    
    
    def _is_demographic_response(self, message_store, session_id: str, state) -> bool:
        """Check if user is responding to a demographic question"""
        # Get the last assistant message to see what was asked
        last_message = message_store.get_last_message(session_id)
        
        if not last_message or last_message["role"] != "assistant":
            return False
        
        last_content = last_message["content"].lower()
        
        # Check if last message was asking for demographics (all at once)
        demographic_indicators = [
            "share your name, age, and gender",  # Our new combined question
            "name, age, and gender",
            "your name",
            "preferred name", 
            "what is your age",
            "your age",
            "your gender"
        ]
        
        # Check if we're in demographic collection phase
        is_asking_demographic = any(indicator in last_content for indicator in demographic_indicators)
        
        # Also check if demographics are incomplete
        demographics_incomplete = not state.demographics or len(state.demographics) < 3
        
        return is_asking_demographic and demographics_incomplete
    
    def _save_all_demographics_from_response(self, session_id: str, message: str, state):
        """
        Parse all demographics (name, age, gender) from a single response
        Example: "I'm Aditya, 25, male" or "Aditya, 25 years old, male"
        """
        import re
        
        demographics = {}
        message_lower = message.lower()
        
        # Extract age (look for numbers)
        age_patterns = [
            r'\b(\d{1,3})\s*(?:years?\s*old|yrs?|y\.?o\.?)?\b',  # "25 years old", "25 yrs", "25"
            r'\bage[:\s]+(\d{1,3})\b',  # "age: 25"
            r'\b(\d{1,3})\b'  # Any number
        ]
        
        for pattern in age_patterns:
            age_match = re.search(pattern, message_lower)
            if age_match:
                age = int(age_match.group(1))
                if 1 <= age <= 120:
                    demographics["age"] = age
                    break
        
        # Extract gender
        if any(word in message_lower for word in ["male", "man", "boy", " m "]):
            demographics["gender"] = "male"
        elif any(word in message_lower for word in ["female", "woman", "girl", " f "]):
            demographics["gender"] = "female"
        elif any(word in message_lower for word in ["non-binary", "nonbinary", "enby", "nb"]):
            demographics["gender"] = "non-binary"
        elif any(word in message_lower for word in ["prefer not", "skip", "pass"]):
            demographics["gender"] = "prefer_not_to_say"
        
        # Extract name (more sophisticated)
        # Remove age and gender words to isolate name
        name_message = message
        if "age" in demographics:
            name_message = re.sub(r'\d{1,3}\s*(?:years?\s*old|yrs?|y\.?o\.?)?', '', name_message, flags=re.IGNORECASE)
        
        # Remove common phrases
        for phrase in ["i'm", "i am", "my name is", "call me", "male", "female", "man", "woman"]:
            name_message = name_message.lower().replace(phrase, "")
        
        # Clean up and extract first word/name
        name_parts = name_message.strip().split()
        if name_parts:
            # Get first meaningful word (not gender/age related)
            for part in name_parts:
                clean_part = re.sub(r'[^\w]', '', part).strip()
                if clean_part and len(clean_part) > 1 and not clean_part.isdigit():
                    demographics["name"] = clean_part.capitalize()
                    break
        
        # Fallback if name not found
        if "name" not in demographics:
            # Use first word from original message
            first_word = message.strip().split()[0] if message.strip() else "there"
            demographics["name"] = first_word.capitalize()
        
        # Save all demographics
        if demographics:
            self.state_manager.set_demographics(session_id, demographics)
            logger.info(f"Saved demographics for {session_id}: {demographics}")
        else:
            logger.warning(f"Could not parse demographics from: {message}")
    
    def _infer_dimension_from_context(self, state) -> str:
        """Infer which dimension was being asked about"""
        # Get next dimension needed
        return assessment_trigger.get_next_dimension_needed(state.session_id)
    
    async def _generate_assessment(
        self,
        session_id: str,
        state,
        classification: Dict[str, Any]
    ) -> str:
        """Generate final assessment report"""
        condition = state.condition_hypothesis[0] if state.condition_hypothesis else "general stress"
        
        assessment_result = await assessment_agent.generate_assessment(
            session_id=session_id,
            condition=condition,
            answers=state.answers_collected,
            demographics=state.demographics,
            risk_level=state.risk_level
        )
        
        if assessment_result["success"]:
            return assessment_result["report"]
        else:
            # Fallback assessment
            return """**ASSESSMENT SUMMARY:**

Based on our conversation, I've gathered important information about what you're experiencing. However, I encountered an issue generating the full report.

**Recommendation:**
Please consult with a licensed mental health professional who can provide a comprehensive evaluation and appropriate support.

This preliminary assessment is not a substitute for professional diagnosis and care."""
    
    def _create_success_response(
        self,
        session_id: str,
        message: str,
        usage_info: Dict[str, Any]
    ) -> SessionChatResponse:
        """Create successful response"""
        return SessionChatResponse(
            message=message,
            conversation_id=session_id,
            requires_subscription=False,
            messages_used=usage_info["messages_used"],
            message_limit=usage_info["message_limit"],
            plan_type=usage_info["plan_type"]
        )
    
    def _create_subscription_required_response(
        self,
        session_id: str,
        usage_info: Dict[str, Any]
    ) -> SessionChatResponse:
        """Create subscription required response"""
        if usage_info.get("plan_type") == "free" and usage_info["messages_used"] >= usage_info["message_limit"]:
            message = "You've reached your free message limit. Please subscribe to continue chatting."
        else:
            message = f"Unable to process message: {usage_info.get('error', 'Unknown error')}"
        
        return SessionChatResponse(
            message=message,
            conversation_id=session_id,
            requires_subscription=True,
            messages_used=usage_info["messages_used"],
            message_limit=usage_info["message_limit"],
            plan_type=usage_info["plan_type"]
        )
    
    def _create_error_response(
        self,
        session_id: str,
        error_message: str,
        usage_info: Dict[str, Any]
    ) -> SessionChatResponse:
        """Create error response"""
        return SessionChatResponse(
            message=error_message,
            conversation_id=session_id,
            requires_subscription=False,
            messages_used=usage_info["messages_used"],
            message_limit=usage_info["message_limit"],
            plan_type=usage_info["plan_type"]
        )
    
    def get_conversation_messages(
        self,
        db: Session,
        session_identifier: str,
        limit: int = 50
    ) -> list:
        """Get conversation messages from Redis/DB"""
        try:
            message_store = OptimizedMessageHistoryStore(db)
            return message_store.get_messages(session_identifier, limit=limit)
        except Exception as e:
            logger.error(f"Error getting conversation messages: {e}")
            try:
                db.rollback()
            except:
                pass
            return []

