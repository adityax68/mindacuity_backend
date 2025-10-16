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
        from datetime import datetime
        
        request_start = datetime.utcnow()
        logger.info(f"[PERF] === Starting request for session {session_identifier} ===")
        
        try:
            # 1. Check usage limit
            step_start = datetime.utcnow()
            usage_info = self.subscription_service.check_usage_limit(
                db, session_identifier, allow_orphaned_reuse=False
            )
            logger.info(f"[PERF] Usage check took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
            
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
            step_start = datetime.utcnow()
            conversation = self.subscription_service.create_or_get_conversation(db, session_identifier)
            logger.info(f"[PERF] DB conversation lookup took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
            
            step_start = datetime.utcnow()
            message_store = OptimizedMessageHistoryStore(db)
            state = self.state_manager.get_state(session_identifier)
            
            # Get recent context from Redis (fast!)
            context = message_store.get_context_for_llm(session_identifier, max_messages=6)
            
            # Build state summary from existing state (no extra Redis call!)
            state_summary = {
                "phase": state.phase,
                "questions_asked": state.questions_asked,
                "dimensions_answered": len(state.dimensions_answered),
                "condition_hypothesis": state.condition_hypothesis,
                "risk_level": state.risk_level,
                "has_demographics": bool(state.demographics)
            }
            logger.info(f"[PERF] Redis state/context fetch took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
            
            # 4. ORCHESTRATOR CALL (API Call #1)
            # Classifies intent, detects emotion, checks crisis, generates empathy
            step_start = datetime.utcnow()
            logger.info(f"[PERF] Calling Orchestrator agent...")
            orchestrator_result = await orchestrator_agent.classify_and_respond(
                user_message=chat_request.message,
                session_id=session_identifier,
                conversation_context=context,
                state_summary=state_summary
            )
            logger.info(f"[PERF] Orchestrator TOTAL (including retries) took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
            
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
                
                # INCREMENT USAGE BEFORE RETURNING!
                self.subscription_service.increment_usage(db, session_identifier)
                usage_info["messages_used"] = usage_info.get("messages_used", 0) + 1
                if usage_info.get("message_limit"):
                    usage_info["can_send"] = usage_info["messages_used"] < usage_info["message_limit"]
                
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
                
                # INCREMENT USAGE BEFORE RETURNING!
                self.subscription_service.increment_usage(db, session_identifier)
                usage_info["messages_used"] = usage_info.get("messages_used", 0) + 1
                if usage_info.get("message_limit"):
                    usage_info["can_send"] = usage_info["messages_used"] < usage_info["message_limit"]
                
                return self._create_success_response(
                    session_identifier, redirect_message, usage_info
                )
            
            # 6. Update state with orchestrator insights (BATCHED for performance)
            state_updates = {}
            if classification["condition_hypothesis"]:
                state_updates["condition_hypothesis"] = classification["condition_hypothesis"]
            
            if classification["sentiment"]:
                state_updates["sentiment"] = classification["sentiment"]
            
            if classification["risk_level"]:
                state_updates["risk_level"] = classification["risk_level"]
            
            # Single Redis get+save instead of 3 separate cycles!
            if state_updates:
                step_start = datetime.utcnow()
                self.state_manager.update_state(session_identifier, state_updates)
                logger.info(f"[PERF] Batched state update took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
            
            # 7. Route to appropriate specialist based on phase and progress
            
            # Check if this is first message
            if state.phase == "initial" and state.questions_asked == 0:
                # First interaction - just use greeting (orchestrator empathy might be redundant)
                response_message = prompt_manager.INITIAL_GREETING
                message_store.add_assistant_message(session_identifier, response_message)
                self.state_manager.set_phase(session_identifier, "gathering")
                
                # INCREMENT USAGE BEFORE RETURNING!
                self.subscription_service.increment_usage(db, session_identifier)
                usage_info["messages_used"] = usage_info.get("messages_used", 0) + 1
                if usage_info.get("message_limit"):
                    usage_info["can_send"] = usage_info["messages_used"] < usage_info["message_limit"]
                
                return self._create_success_response(
                    session_identifier, response_message, usage_info
                )
            
            # IMPORTANT: Check if user is RESPONDING to demographics FIRST
            # (Before checking if we need to ask - to avoid asking when they just answered!)
            logger.info(f"[DEBUG] STEP 1: Check if responding to demographics - demographics: {state.demographics}, phase: {state.phase}")
            is_demo_response = self._is_demographic_response(message_store, session_identifier, state)
            logger.info(f"[DEBUG] Is demographic response: {is_demo_response}")
            
            if is_demo_response:
                # Parse all demographics from one response
                logger.info(f"[DEBUG] Parsing demographics from: '{chat_request.message}'")
                self._save_all_demographics_from_response(session_identifier, chat_request.message, state)
                
                # Refresh state to confirm demographics were saved
                state = self.state_manager.get_state(session_identifier)
                logger.info(f"[DEBUG] After saving demographics: {state.demographics}")
                
                # Done with demographics, start diagnostic questions
                next_dimension = assessment_trigger.get_next_dimension_needed(session_identifier)
                condition = state.condition_hypothesis[0] if state.condition_hypothesis else "general"
                
                step_start = datetime.utcnow()
                logger.info(f"[PERF] Calling Diagnostic agent after demographics for dimension: {next_dimension}...")
                question_result = await diagnostic_agent.generate_question(
                    session_id=session_identifier,
                    condition=condition,
                    dimension_needed=next_dimension,
                    context={"phase": "starting_diagnostics"}
                )
                logger.info(f"[PERF] Diagnostic agent took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
                
                if question_result["success"]:
                    empathy = classification.get("empathy_response", "")
                    question = question_result["question"]
                    logger.info(f"[DEBUG] Building response - empathy: '{empathy}', question: '{question}'")
                    response_message = self._build_response_with_empathy(empathy, question)
                else:
                    # Fallback if GPT fails
                    logger.warning(f"Diagnostic agent failed after demographics, using fallback. Error: {question_result.get('error')}")
                    fallback_question = "How long have you been experiencing these feelings? Days, weeks, or months?"
                    # Use empathy if available, otherwise just the question
                    empathy = classification.get("empathy_response", "")
                    if empathy and empathy.strip() and empathy.strip() != "?":
                        response_message = f"{empathy}\n\n{fallback_question}"
                    else:
                        response_message = fallback_question
                    logger.info(f"[DEBUG] Using fallback response: '{response_message}'")
                
                message_store.add_assistant_message(session_identifier, response_message)
                
                # INCREMENT USAGE BEFORE RETURNING!
                self.subscription_service.increment_usage(db, session_identifier)
                usage_info["messages_used"] = usage_info.get("messages_used", 0) + 1
                if usage_info.get("message_limit"):
                    usage_info["can_send"] = usage_info["messages_used"] < usage_info["message_limit"]
                
                return self._create_success_response(
                    session_identifier, response_message, usage_info
                )
            
            # Now check if we NEED to ask for demographics (only if user didn't just provide them)
            logger.info(f"[DEBUG] STEP 2: Check if we need to ask for demographics - demographics: {state.demographics}")
            need_demo = self._need_demographics(state, classification)
            logger.info(f"[DEBUG] Need demographics: {need_demo}, sentiment: {classification.get('sentiment')}")
            
            if state.phase == "gathering" and need_demo:
                # Check if demographics are completely empty
                if not state.demographics or len(state.demographics) == 0:
                    logger.info(f"[DEBUG] Asking for demographics (empty check passed)")
                    # Ask for all demographics in one message
                    demographic_question = prompt_manager.get_demographic_question("all")
                    response_message = self._build_response_with_empathy(
                        classification["empathy_response"],
                        demographic_question
                    )
                    message_store.add_assistant_message(session_identifier, response_message)
                    
                    # INCREMENT USAGE BEFORE RETURNING!
                    self.subscription_service.increment_usage(db, session_identifier)
                    usage_info["messages_used"] = usage_info.get("messages_used", 0) + 1
                    if usage_info.get("message_limit"):
                        usage_info["can_send"] = usage_info["messages_used"] < usage_info["message_limit"]
                    
                    return self._create_success_response(
                        session_identifier, response_message, usage_info
                    )
                else:
                    logger.info(f"[DEBUG] Demographics exist but need_demographics returned True: {state.demographics}")
            
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
                
                # INCREMENT USAGE BEFORE RETURNING!
                self.subscription_service.increment_usage(db, session_identifier)
                usage_info["messages_used"] = usage_info.get("messages_used", 0) + 1
                if usage_info.get("message_limit"):
                    usage_info["can_send"] = usage_info["messages_used"] < usage_info["message_limit"]
                
                return self._create_success_response(
                    session_identifier, response_message, usage_info
                )
            
            # 8. Continue diagnostic questioning (API Call #2)
            # Track the answer for ALL responses during diagnostic phase
            if state.phase == "gathering":
                # Extract dimension from last question context
                last_assistant_message = message_store.get_last_assistant_message(session_identifier)
                if last_assistant_message:
                    # Infer dimension from previous question
                    dimension = self._infer_dimension_from_context(state)
                    if dimension:
                        logger.info(f"[DEBUG] Marking dimension '{dimension}' as answered for session {session_identifier}")
                        assessment_trigger.mark_dimension_answered(
                            session_identifier,
                            dimension,
                            chat_request.message
                        )
                        # Refresh state after marking dimension
                        state = self.state_manager.get_state(session_identifier)
                        logger.info(f"[DEBUG] After marking dimension - questions_asked: {state.questions_asked}, dimensions_answered: {state.dimensions_answered}")
            
            # Check if we should trigger assessment now
            should_trigger, trigger_reason = assessment_trigger.should_trigger_assessment(session_identifier)
            logger.info(f"[DEBUG] Assessment trigger check: should_trigger={should_trigger}, reason={trigger_reason}")
            
            if should_trigger:
                logger.info(f"[DEBUG] Triggering assessment for session {session_identifier}")
                # Generate assessment
                step_start = datetime.utcnow()
                assessment_result = await assessment_agent.generate_assessment(
                    session_id=session_identifier,
                    condition=state.condition_hypothesis[0] if state.condition_hypothesis else "general stress",
                    answers=state.answers_collected,
                    demographics=state.demographics,
                    risk_level=state.risk_level
                )
                logger.info(f"[PERF] Assessment generation took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
                
                if assessment_result["success"]:
                    response_message = assessment_result["report"]
                    message_store.add_assistant_message(session_identifier, response_message)
                    
                    # Mark session as complete
                    self.state_manager.set_phase(session_identifier, "complete")
                    
                    # INCREMENT USAGE BEFORE RETURNING!
                    self.subscription_service.increment_usage(db, session_identifier)
                    usage_info["messages_used"] = usage_info.get("messages_used", 0) + 1
                    if usage_info.get("message_limit"):
                        usage_info["can_send"] = usage_info["messages_used"] < usage_info["message_limit"]
                    
                    return self._create_success_response(
                        session_identifier, response_message, usage_info
                    )
                else:
                    logger.error(f"Assessment generation failed: {assessment_result.get('error')}")
                    # Fallback response when assessment fails
                    response_message = "I apologize, but I'm having trouble generating your assessment right now. Let me ask you a few more questions to better understand your situation."
                    message_store.add_assistant_message(session_identifier, response_message)
                    
                    # INCREMENT USAGE FOR FALLBACK RESPONSE
                    self.subscription_service.increment_usage(db, session_identifier)
                    usage_info["messages_used"] = usage_info.get("messages_used", 0) + 1
                    if usage_info.get("message_limit"):
                        usage_info["can_send"] = usage_info["messages_used"] < usage_info["message_limit"]
                    
                    return self._create_success_response(
                        session_identifier, response_message, usage_info
                    )
            
            # Generate next diagnostic question
            next_dimension = assessment_trigger.get_next_dimension_needed(session_identifier)
            condition = state.condition_hypothesis[0] if state.condition_hypothesis else "general"
            
            step_start = datetime.utcnow()
            logger.info(f"[PERF] Calling Diagnostic agent for dimension: {next_dimension}...")
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
            logger.info(f"[PERF] Diagnostic agent took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
            
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
            step_start = datetime.utcnow()
            message_store.add_assistant_message(session_identifier, response_message)
            logger.info(f"[PERF] Save assistant message took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
            
            # 9. Increment usage and return (cached, no extra DB query)
            step_start = datetime.utcnow()
            self.subscription_service.increment_usage(db, session_identifier)
            
            # Update usage info locally (no DB query needed!)
            usage_info["messages_used"] = usage_info.get("messages_used", 0) + 1
            if usage_info.get("message_limit"):
                usage_info["can_send"] = usage_info["messages_used"] < usage_info["message_limit"]
            
            logger.info(f"[PERF] DB usage increment took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
            
            total_duration = (datetime.utcnow() - request_start).total_seconds()
            logger.info(f"[PERF] === REQUEST COMPLETED in {total_duration:.3f}s for session {session_identifier} ===")
            
            return self._create_success_response(
                session_identifier, response_message, usage_info
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
        logger.info(f"[DEBUG] _is_demographic_response called for session {session_id}")
        
        # Get the last ASSISTANT message to see what was asked
        # (Not just last message, which could be the user's message we just added!)
        last_assistant_message = message_store.get_last_assistant_message(session_id)
        
        if not last_assistant_message:
            logger.info(f"[DEBUG] No last assistant message found, returning False")
            return False
        
        last_content = last_assistant_message["content"].lower()
        logger.info(f"[DEBUG] Last assistant message: '{last_content[:150]}...'")
        
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
        logger.info(f"[DEBUG] is_asking_demographic: {is_asking_demographic}")
        
        # Also check if demographics are incomplete
        demographics_incomplete = not state.demographics or len(state.demographics) < 3
        logger.info(f"[DEBUG] demographics_incomplete: {demographics_incomplete}, current demographics: {state.demographics}")
        
        result = is_asking_demographic and demographics_incomplete
        logger.info(f"[DEBUG] _is_demographic_response returning: {result}")
        return result
    
    def _save_all_demographics_from_response(self, session_id: str, message: str, state):
        """
        Parse all demographics (name, age, gender) from a single response
        Example: "I'm Aditya, 25, male" or "Aditya, 25 years old, male"
        """
        import re
        
        logger.info(f"[DEBUG] _save_all_demographics_from_response called with message: '{message}'")
        
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
                    logger.info(f"[DEBUG] Extracted age: {age}")
                    break
        
        # Extract gender
        if any(word in message_lower for word in ["male", "man", "boy", " m "]):
            demographics["gender"] = "male"
            logger.info(f"[DEBUG] Extracted gender: male")
        elif any(word in message_lower for word in ["female", "woman", "girl", " f "]):
            demographics["gender"] = "female"
            logger.info(f"[DEBUG] Extracted gender: female")
        elif any(word in message_lower for word in ["non-binary", "nonbinary", "enby", "nb"]):
            demographics["gender"] = "non-binary"
            logger.info(f"[DEBUG] Extracted gender: non-binary")
        elif any(word in message_lower for word in ["prefer not", "skip", "pass"]):
            demographics["gender"] = "prefer_not_to_say"
            logger.info(f"[DEBUG] Extracted gender: prefer_not_to_say")
        
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
                    logger.info(f"[DEBUG] Extracted name: {demographics['name']}")
                    break
        
        # Fallback if name not found
        if "name" not in demographics:
            # Use first word from original message
            first_word = message.strip().split()[0] if message.strip() else "there"
            demographics["name"] = first_word.capitalize()
            logger.info(f"[DEBUG] Using fallback name: {demographics['name']}")
        
        # Save all demographics
        logger.info(f"[DEBUG] About to save demographics: {demographics}")
        if demographics:
            result = self.state_manager.set_demographics(session_id, demographics)
            logger.info(f"[DEBUG] state_manager.set_demographics returned: {result}")
            logger.info(f"[SUCCESS] Saved demographics for {session_id}: {demographics}")
        else:
            logger.warning(f"[WARNING] Could not parse demographics from: {message}")
    
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
        """Get conversation messages from Redis/DB with proper format"""
        try:
            message_store = OptimizedMessageHistoryStore(db)
            messages = message_store.get_messages(session_identifier, limit=limit)
            
            # Add id field and convert created_at to datetime for API response
            formatted_messages = []
            for idx, msg in enumerate(messages):
                formatted_msg = {
                    "id": idx + 1,  # Sequential ID for API
                    "role": msg.get("role", "assistant"),
                    "content": msg.get("content", ""),
                    "created_at": msg.get("created_at", datetime.utcnow().isoformat())
                }
                # Convert ISO string to datetime if needed
                if isinstance(formatted_msg["created_at"], str):
                    try:
                        formatted_msg["created_at"] = datetime.fromisoformat(formatted_msg["created_at"])
                    except:
                        formatted_msg["created_at"] = datetime.utcnow()
                
                formatted_messages.append(formatted_msg)
            
            return formatted_messages
            
        except Exception as e:
            logger.error(f"Error getting conversation messages: {e}")
            try:
                db.rollback()
            except:
                pass
            return []

    async def process_chat_message_stream(
        self,
        db: Session,
        session_identifier: str,
        chat_request: SessionChatMessageRequest
    ):
        """
        Process chat message with streaming response
        Yields empathy response immediately, then question/report when ready
        """
        try:
            request_start = datetime.utcnow()
            logger.info(f"[PERF] === Starting STREAMING request for session {session_identifier} ===")
            
            # 1. Usage check (same as before)
            step_start = datetime.utcnow()
            usage_info = self.subscription_service.check_usage_limit(db, session_identifier)
            logger.info(f"[PERF] Usage check took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
            
            if not usage_info.get("can_send", False):
                yield {
                    'type': 'error',
                    'message': 'Message limit reached. Please upgrade your plan.',
                    'usage_info': usage_info
                }
                return
            
            # 2. Get conversation and state (same as before)
            step_start = datetime.utcnow()
            conversation = db.query(Conversation).filter(
                Conversation.session_identifier == session_identifier
            ).first()
            logger.info(f"[PERF] DB conversation lookup took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
            
            step_start = datetime.utcnow()
            state = self.state_manager.get_state(session_identifier)
            message_store = OptimizedMessageHistoryStore(db)
            logger.info(f"[PERF] Redis state/context fetch took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
            
            # 3. Save user message
            message_store.add_user_message(session_identifier, chat_request.message)
            
            # 4. Call Orchestrator (Claude) - FAST RESPONSE
            step_start = datetime.utcnow()
            logger.info(f"[PERF] Calling Orchestrator agent...")
            
            # Build state summary from existing state (no extra Redis call!)
            state_summary = {
                "phase": state.phase,
                "questions_asked": state.questions_asked,
                "dimensions_answered": len(state.dimensions_answered),
                "has_demographics": bool(state.demographics)
            }
            
            classification = await orchestrator_agent.classify_and_respond(
                user_message=chat_request.message,
                session_id=session_identifier,
                conversation_context=message_store.get_context_for_llm(session_identifier),
                state_summary=state_summary
            )
            logger.info(f"[PERF] Orchestrator took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
            
            # 5. STREAM EMPATHY RESPONSE IMMEDIATELY
            empathy_response = classification.get("empathy_response", "")
            if empathy_response:
                yield {
                    'type': 'empathy',
                    'content': empathy_response,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            # 6. Update state (batched)
            step_start = datetime.utcnow()
            state_updates = {
                "last_activity": datetime.utcnow().isoformat(),
                "last_user_message": chat_request.message,
                "questions_asked": state.questions_asked,
                "answers_collected": state.answers_collected,
                "condition_hypothesis": state.condition_hypothesis,
                "risk_level": classification.get("risk_level", "low")
            }
            self.state_manager.update_state(session_identifier, state_updates)
            logger.info(f"[PERF] Batched state update took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
            
            # 7. Handle different conversation phases
            if classification.get("intent") == "crisis":
                # Crisis response - immediate
                crisis_response = "I'm concerned about your safety. Please contact emergency services immediately: 988 (Suicide & Crisis Lifeline) or 911. You're not alone, and there are people who want to help."
                message_store.add_assistant_message(session_identifier, crisis_response)
                self.state_manager.set_phase(session_identifier, "complete")
                self.subscription_service.increment_usage(db, session_identifier)
                
                yield {
                    'type': 'crisis',
                    'content': crisis_response,
                    'timestamp': datetime.utcnow().isoformat()
                }
                return
                
            elif classification.get("intent") == "off_topic":
                # Off-topic response - immediate
                off_topic_response = "I'm specialized in mental health assessments and can only help with concerns related to anxiety, depression, stress, and similar conditions. If you're experiencing any mental health challenges, I'm here to help assess them."
                message_store.add_assistant_message(session_identifier, off_topic_response)
                self.subscription_service.increment_usage(db, session_identifier)
                
                yield {
                    'type': 'off_topic',
                    'content': off_topic_response,
                    'timestamp': datetime.utcnow().isoformat()
                }
                return
            
            # 8. Handle demographics and assessment logic
            if state.phase == "greeting":
                # First message - send initial greeting
                initial_greeting = prompt_manager.INITIAL_GREETING
                message_store.add_assistant_message(session_identifier, initial_greeting)
                self.state_manager.set_phase(session_identifier, "demographics")
                self.subscription_service.increment_usage(db, session_identifier)
                
                yield {
                    'type': 'greeting',
                    'content': initial_greeting,
                    'timestamp': datetime.utcnow().isoformat()
                }
                return
            
            # Check if user is responding to demographics
            if self._is_demographic_response(message_store, session_identifier, state):
                # Parse all demographics from one response
                logger.info(f"[DEBUG] Parsing demographics from: '{chat_request.message}'")
                self._save_all_demographics_from_response(session_identifier, chat_request.message, state)
                
                # Refresh state to confirm demographics were saved
                state = self.state_manager.get_state(session_identifier)
                logger.info(f"[DEBUG] After saving demographics: {state.demographics}")
                
                # Done with demographics, start diagnostic questions
                self.state_manager.set_phase(session_identifier, "gathering")
                
                # Send acknowledgment and start diagnostic questions
                ack_response = f"Thank you for sharing that, {state.demographics.get('name', 'there')}."
                message_store.add_assistant_message(session_identifier, ack_response)
                self.subscription_service.increment_usage(db, session_identifier)
                
                yield {
                    'type': 'demographics_ack',
                    'content': ack_response,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Continue to diagnostic questions below
            
            # Check if we still need demographics
            if self._need_demographics(state, classification):
                demo_question = "To provide you with a more personalized assessment, I'd like to know a bit about you. Could you share your name, age, and gender (if you're comfortable)?"
                message_store.add_assistant_message(session_identifier, demo_question)
                self.subscription_service.increment_usage(db, session_identifier)
                
                yield {
                    'type': 'demographics_question',
                    'content': demo_question,
                    'timestamp': datetime.utcnow().isoformat()
                }
                return
            
            # 9. Check if we should trigger assessment
            should_assess, reason = assessment_trigger.should_trigger_assessment(session_identifier)
            
            if should_assess:
                # ASSESSMENT PHASE - Generate comprehensive report
                logger.info(f"[DEBUG] Triggering assessment for session {session_identifier}")
                
                # Mark dimension as answered if this was a response
                if state.phase == "gathering":
                    dimension = self._infer_dimension_from_context(state)
                    if dimension:
                        assessment_trigger.mark_dimension_answered(session_identifier, dimension, chat_request.message)
                
                # Generate assessment (this takes time)
                step_start = datetime.utcnow()
                assessment_result = await assessment_agent.generate_assessment(
                    session_id=session_identifier,
                    condition=state.condition_hypothesis[0] if state.condition_hypothesis else "general stress",
                    answers=state.answers_collected,
                    demographics=state.demographics,
                    risk_level=state.risk_level
                )
                logger.info(f"[PERF] Assessment generation took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
                
                if assessment_result["success"]:
                    response_message = assessment_result["report"]
                    message_store.add_assistant_message(session_identifier, response_message)
                    self.state_manager.set_phase(session_identifier, "complete")
                    
                    # INCREMENT USAGE
                    self.subscription_service.increment_usage(db, session_identifier)
                    usage_info["messages_used"] = usage_info.get("messages_used", 0) + 1
                    if usage_info.get("message_limit"):
                        usage_info["can_send"] = usage_info["messages_used"] < usage_info["message_limit"]
                    
                    yield {
                        'type': 'assessment',
                        'content': response_message,
                        'timestamp': datetime.utcnow().isoformat(),
                        'usage_info': usage_info
                    }
                    return
                else:
                    # Assessment failed - fallback
                    fallback_response = "I apologize, but I'm having trouble generating your assessment right now. Let me ask you a few more questions to better understand your situation."
                    message_store.add_assistant_message(session_identifier, fallback_response)
                    self.subscription_service.increment_usage(db, session_identifier)
                    
                    yield {
                        'type': 'assessment_error',
                        'content': fallback_response,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    return
            
            # 10. Generate next diagnostic question (this takes time)
            next_dimension = assessment_trigger.get_next_dimension_needed(session_identifier)
            condition = state.condition_hypothesis[0] if state.condition_hypothesis else "general"
            
            step_start = datetime.utcnow()
            logger.info(f"[PERF] Calling Diagnostic agent for dimension: {next_dimension}...")
            
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
            logger.info(f"[PERF] Diagnostic agent took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
            
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
            step_start = datetime.utcnow()
            message_store.add_assistant_message(session_identifier, response_message)
            logger.info(f"[PERF] Save assistant message took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
            
            # Mark dimension as answered
            if state.phase == "gathering":
                assessment_trigger.mark_dimension_answered(session_identifier, next_dimension, chat_request.message)
            
            # Increment usage
            step_start = datetime.utcnow()
            self.subscription_service.increment_usage(db, session_identifier)
            usage_info["messages_used"] = usage_info.get("messages_used", 0) + 1
            if usage_info.get("message_limit"):
                usage_info["can_send"] = usage_info["messages_used"] < usage_info["message_limit"]
            logger.info(f"[PERF] DB usage increment took {(datetime.utcnow() - step_start).total_seconds():.3f}s")
            
            total_duration = (datetime.utcnow() - request_start).total_seconds()
            logger.info(f"[PERF] === STREAMING REQUEST COMPLETED in {total_duration:.3f}s for session {session_identifier} ===")
            
            # STREAM THE FINAL QUESTION
            yield {
                'type': 'question',
                'content': response_message,
                'timestamp': datetime.utcnow().isoformat(),
                'usage_info': usage_info
            }
            
        except Exception as e:
            logger.error(f"Error processing streaming chat message for {session_identifier}: {e}")
            yield {
                'type': 'error',
                'message': f"Failed to process message: {str(e)}",
                'timestamp': datetime.utcnow().isoformat()
            }

