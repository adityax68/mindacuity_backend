import json
import redis
import logging
import time
from typing import Dict, List, Any, Optional, AsyncGenerator
from sqlalchemy.orm import Session
from openai import OpenAI, AsyncOpenAI
from anthropic import AsyncAnthropic
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import JsonOutputParser

from app.config import settings
from app.models import Message, Conversation, AssessmentReport
from app.services.subscription_service import SubscriptionService
from app.schemas import SessionChatMessageRequest, SessionChatResponse
from app.utils.logger import chat_logger, assessment_logger, session_logger, log_performance

logger = logging.getLogger(__name__)

class EnhancedChatService:
    def __init__(self):
        # Initialize OpenAI client for streaming
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Initialize Anthropic client for assessment
        self.anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        
        # Initialize Redis for session management
        self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        
        # Initialize subscription service
        self.subscription_service = SubscriptionService()
        
        # Enhanced system prompt with Acutie branding
        self.system_prompt = """You are Acutie, a sophisticated mental health companion with extensive experience in psychological assessment and emotional support. You have successfully helped thousands of individuals understand their mental health patterns and conditions.

Your mission is to conduct a comprehensive mental health evaluation through a natural, empathetic conversation within 12 exchanges. Your approach should be:

CONVERSATION STYLE:
- Lead with genuine empathy and understanding
- Ask one focused question per response
- Use warm, professional language that builds trust
- Adapt your communication style to the user's emotional state
- If user goes off-topic, gently redirect: "I understand you're sharing important thoughts. As your mental health companion, I'd like to focus on understanding your emotional wellbeing. Can you tell me about..."
- If user is evasive, acknowledge their feelings: "I sense this might be difficult to discuss. Take your time, and share what feels comfortable."

ASSESSMENT AREAS TO EXPLORE:
1. Emotional patterns and mood fluctuations
2. Sleep quality and energy levels
3. Social relationships and isolation tendencies
4. Work/academic performance and stress levels
5. Physical symptoms related to mental health
6. Coping mechanisms and support systems
7. Life changes or traumatic events
8. Anxiety triggers and panic experiences
9. Self-worth and confidence levels
10. Substance use or self-harm thoughts

CRISIS INTERVENTION:
If user mentions suicidal thoughts, self-harm, or harming others, immediately respond with:
"I'm concerned about your safety. Your life has value and there are people who want to help. Please contact:
- National Suicide Prevention Lifeline: 988
- Crisis Text Line: Text HOME to 741741
- Emergency Services: 911
Are you in a safe place right now? Is someone with you?"

QUESTIONING STRATEGY:
- Start broad, then narrow down based on responses
- Use open-ended questions that encourage detailed responses
- Follow emotional cues and probe deeper when needed
- Balance clinical assessment with human connection
- Vary question types: behavioral, emotional, cognitive, physical

Remember: You're not providing therapy or treatment advice. Your role is assessment and evaluation to help identify potential mental health conditions and their severity levels."""

        # Anthropic assessment prompt
        self.assessment_prompt = """You are a senior clinical psychologist and assessment specialist with expertise in diagnostic evaluation and mental health condition analysis. You have 30+ years of experience in psychological assessment and have reviewed over 25,000 clinical cases.

TASK: Analyze the following conversation between a user and a mental health professional to provide a comprehensive preliminary assessment.

CONVERSATION TO ANALYZE:
{conversation_text}

ASSESSMENT REQUIREMENTS:

1. CONDITION IDENTIFICATION:
   - Identify specific mental health conditions based on DSM-5 criteria
   - Consider comorbidity (multiple conditions)
   - Distinguish between primary and secondary conditions
   - Examples: Generalized Anxiety Disorder, Major Depressive Episode, Panic Disorder, PTSD, Social Anxiety Disorder, Bipolar Disorder, etc.

2. KEY SYMPTOMS ANALYSIS:
   - Identify 2-3 most significant symptoms that strongly indicate the condition(s)
   - Focus on symptoms that meet diagnostic criteria
   - Consider frequency, intensity, and duration of symptoms
   - Include both emotional and physical manifestations

3. SEVERITY ASSESSMENT:
   - MILD: Symptoms present but manageable, minimal functional impairment
   - MODERATE: Noticeable impact on daily life, some functional difficulties
   - SEVERE: Significant distress, substantial functional impairment, may include crisis indicators

4. CONVERSATION QUALITY EVALUATION:
   - Assess user's engagement level and openness
   - Note if user provided sufficient information
   - Identify any resistance, denial, or avoidance patterns
   - Consider cultural, age, or personal factors affecting disclosure

5. CLINICAL INSIGHTS:
   - Risk factors identified
   - Protective factors present
   - Urgency level for professional intervention
   - Specific areas needing further evaluation

PROVIDE YOUR ASSESSMENT IN THIS EXACT JSON FORMAT:

{{
    "conditions": ["Primary Condition", "Secondary Condition if applicable"],
    "symptoms": ["Most significant symptom 1", "Most significant symptom 2", "Most significant symptom 3"],
    "severity_level": "mild|moderate|severe",
    "report_content": "Comprehensive assessment report including condition rationale, symptom analysis, functional impact, and professional recommendations. Include specific examples from the conversation that support your assessment.",
    "conversation_quality": "excellent|good|fair|limited",
    "risk_factors": ["Risk factor 1", "Risk factor 2"],
    "protective_factors": ["Protective factor 1", "Protective factor 2"],
    "urgency_level": "low|moderate|high|critical",
    "recommendations": ["Specific recommendation 1", "Specific recommendation 2"],
    "limitations": "Note any limitations in the assessment due to conversation quality or information gaps"
}}

IMPORTANT GUIDELINES:
- Base assessment strictly on conversation content
- Use clinical terminology appropriately
- Provide evidence-based rationale for each condition identified
- If insufficient information, clearly state limitations
- Maintain professional, compassionate tone
- Include disclaimer about preliminary nature of assessment
- Emphasize need for professional evaluation for official diagnosis

DISCLAIMER TO INCLUDE:
"This is a preliminary assessment based on a brief conversation and should not replace a comprehensive evaluation by a licensed mental health professional. Only a qualified clinician can provide an official diagnosis and treatment plan.""""

    @log_performance("process_chat_message")
    async def process_chat_message(self, db: Session, session_identifier: str, chat_request: SessionChatMessageRequest) -> SessionChatResponse:
        """Process a chat message and return AI response"""
        start_time = time.time()
        try:
            chat_logger.info(
                "Starting chat message processing",
                session_id=session_identifier,
                message_length=len(chat_request.message)
            )
            # Check usage limit (keep existing logic)
            usage_info = self.subscription_service.check_usage_limit(db, session_identifier, allow_orphaned_reuse=False)
            
            if not usage_info["can_send"]:
                if usage_info.get("plan_type") == "free" and usage_info["messages_used"] >= usage_info["message_limit"]:
                    return SessionChatResponse(
                        message="You've reached your free message limit. Please subscribe to continue chatting.",
                        conversation_id=session_identifier,
                        requires_subscription=True,
                        messages_used=usage_info["messages_used"],
                        message_limit=usage_info["message_limit"],
                        plan_type=usage_info["plan_type"]
                    )
                else:
                    return SessionChatResponse(
                        message=f"Unable to process message: {usage_info.get('error', 'Unknown error')}",
                        conversation_id=session_identifier,
                        requires_subscription=True,
                        messages_used=usage_info["messages_used"],
                        message_limit=usage_info.get("message_limit", None),
                        plan_type=usage_info["plan_type"]
                    )
            
            # Create or get conversation (keep existing logic)
            conversation = self.subscription_service.create_or_get_conversation(db, session_identifier)
            
            # Check message count from Redis
            message_count = self.redis_client.get(f"msg_count:{session_identifier}")
            message_count = int(message_count) if message_count else 0
            
            if message_count >= 12:
                return SessionChatResponse(
                    message="Ready to generate assessment. Please click the 'Generate Assessment' button.",
                    conversation_id=session_identifier,
                    requires_subscription=False,
                    messages_used=usage_info["messages_used"],
                    message_limit=usage_info["message_limit"],
                    plan_type=usage_info["plan_type"],
                    assessment_ready=True  # Flag for frontend
                )
            
            # Get conversation history from database
            conversation_history = self._get_conversation_history(db, session_identifier)
            
            # Log conversation history length
            chat_logger.info(
                "Retrieved conversation history",
                session_id=session_identifier,
                history_length=len(conversation_history)
            )
            
            # Use streaming OpenAI call
            openai_start = time.time()
            ai_response = await self._get_streaming_openai_response(chat_request.message, conversation_history)
            openai_duration = (time.time() - openai_start) * 1000
            
            chat_logger.perf(
                operation="openai_response_generation",
                duration_ms=openai_duration,
                session_id=session_identifier,
                response_length=len(ai_response)
            )
            
            # Save messages to database
            self._save_message(db, session_identifier, "user", chat_request.message)
            self._save_message(db, session_identifier, "assistant", ai_response)
            
            # Increment Redis counter
            self.redis_client.incr(f"msg_count:{session_identifier}")
            
            # Increment usage counter
            self.subscription_service.increment_usage(db, session_identifier)
            
            # Get updated usage info
            updated_usage = self.subscription_service.check_usage_limit(db, session_identifier, allow_orphaned_reuse=False)
            
            # Log successful completion
            total_duration = (time.time() - start_time) * 1000
            chat_logger.perf(
                operation="chat_message_complete",
                duration_ms=total_duration,
                session_id=session_identifier,
                messages_used=updated_usage["messages_used"],
                plan_type=updated_usage["plan_type"]
            )
            
            return SessionChatResponse(
                message=ai_response,
                conversation_id=session_identifier,
                requires_subscription=False,
                messages_used=updated_usage["messages_used"],
                message_limit=updated_usage["message_limit"],
                plan_type=updated_usage["plan_type"]
            )
            
        except Exception as e:
            total_duration = (time.time() - start_time) * 1000
            chat_logger.error(
                operation="process_chat_message",
                error=e,
                session_id=session_identifier,
                duration_ms=total_duration
            )
            
            try:
                db.rollback()
            except Exception as rollback_error:
                chat_logger.error(
                    operation="database_rollback",
                    error=rollback_error,
                    session_id=session_identifier
                )
            
            return SessionChatResponse(
                message="I'm sorry, I'm having trouble processing your message right now. Please try again in a moment.",
                conversation_id=session_identifier,
                requires_subscription=False,
                messages_used=0,
                message_limit=0,
                plan_type="none"
            )

    async def get_streaming_response(self, db: Session, session_identifier: str, chat_request: SessionChatMessageRequest) -> AsyncGenerator[str, None]:
        """Stream AI response for better UX"""
        try:
            # Check usage limit
            usage_info = self.subscription_service.check_usage_limit(db, session_identifier, allow_orphaned_reuse=False)
            
            if not usage_info["can_send"]:
                yield "You've reached your message limit. Please subscribe to continue."
                return
            
            # Get conversation history
            conversation_history = self._get_conversation_history(db, session_identifier)
            
            # Stream response from OpenAI
            async for chunk in self._stream_openai_response(chat_request.message, conversation_history):
                yield chunk
            
            # Save messages after streaming is complete
            full_response = await self._get_streaming_openai_response(chat_request.message, conversation_history)
            self._save_message(db, session_identifier, "user", chat_request.message)
            self._save_message(db, session_identifier, "assistant", full_response)
            
            # Increment counters
            self.redis_client.incr(f"msg_count:{session_identifier}")
            self.subscription_service.increment_usage(db, session_identifier)
            
        except Exception as e:
            logger.error(f"Failed to stream response: {e}")
            yield "I'm sorry, I'm having trouble processing your message right now. Please try again in a moment."

    @log_performance("generate_assessment")
    async def generate_assessment(self, db: Session, session_identifier: str) -> Dict[str, Any]:
        """Generate assessment using Anthropic"""
        start_time = time.time()
        try:
            assessment_logger.info(
                "Starting assessment generation",
                session_id=session_identifier
            )
            
            # Get full conversation
            conversation_history = self._get_conversation_history(db, session_identifier)
            
            assessment_logger.info(
                "Retrieved conversation for assessment",
                session_id=session_identifier,
                conversation_length=len(conversation_history)
            )
            
            # Format conversation for Anthropic
            conversation_text = ""
            for msg in conversation_history:
                role = "User" if msg["role"] == "user" else "Acutie"
                conversation_text += f"{role}: {msg['content']}\n\n"
            
            # Generate assessment using Anthropic
            anthropic_start = time.time()
            response = await self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": self.assessment_prompt.format(conversation_text=conversation_text)}]
            )
            anthropic_duration = (time.time() - anthropic_start) * 1000
            
            assessment_logger.perf(
                operation="anthropic_assessment_generation",
                duration_ms=anthropic_duration,
                session_id=session_identifier,
                response_length=len(response.content[0].text)
            )
            
            # Parse JSON response
            assessment_data = json.loads(response.content[0].text)
            
            assessment_logger.info(
                "Assessment data parsed successfully",
                session_id=session_identifier,
                conditions_count=len(assessment_data.get("conditions", [])),
                severity_level=assessment_data.get("severity_level", "unknown")
            )
            
            # Save assessment to database
            db_start = time.time()
            assessment_id = self._save_assessment(db, session_identifier, assessment_data)
            db_duration = (time.time() - db_start) * 1000
            
            assessment_logger.perf(
                operation="assessment_database_save",
                duration_ms=db_duration,
                session_id=session_identifier,
                assessment_id=assessment_id
            )
            
            # Create new session and transfer access code
            session_start = time.time()
            new_session_id = self._create_new_session_with_access_code(db, session_identifier)
            session_duration = (time.time() - session_start) * 1000
            
            session_logger.perf(
                operation="session_transfer",
                duration_ms=session_duration,
                old_session_id=session_identifier,
                new_session_id=new_session_id
            )
            
            # Log total assessment completion
            total_duration = (time.time() - start_time) * 1000
            assessment_logger.perf(
                operation="assessment_complete",
                duration_ms=total_duration,
                session_id=session_identifier,
                assessment_id=assessment_id,
                new_session_id=new_session_id
            )
            
            return {
                "assessment_id": assessment_id,
                "assessment": assessment_data,
                "new_session_id": new_session_id
            }
            
        except Exception as e:
            total_duration = (time.time() - start_time) * 1000
            assessment_logger.error(
                operation="generate_assessment",
                error=e,
                session_id=session_identifier,
                duration_ms=total_duration
            )
            raise

    def _get_conversation_history(self, db: Session, session_identifier: str) -> List[Dict]:
        """Get conversation history from database"""
        messages = db.query(Message).filter(
            Message.session_identifier == session_identifier
        ).order_by(Message.created_at.asc()).all()
        
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    async def _get_streaming_openai_response(self, user_message: str, conversation_history: List[Dict]) -> str:
        """Get streaming response from OpenAI"""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add conversation history (last 10 messages for context)
        for msg in conversation_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        response = await self.openai_client.chat.completions.create(
            model="gpt-5",
            messages=messages,
            temperature=0.7,
            max_tokens=500,
            stream=True
        )
        
        full_response = ""
        async for chunk in response:
            if chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
        
        return full_response

    async def _stream_openai_response(self, user_message: str, conversation_history: List[Dict]) -> AsyncGenerator[str, None]:
        """Stream response from OpenAI"""
        messages = [{"role": "system", "content": self.system_prompt}]
        
        # Add conversation history
        for msg in conversation_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        response = await self.openai_client.chat.completions.create(
            model="gpt-5",
            messages=messages,
            temperature=0.7,
            max_tokens=500,
            stream=True
        )
        
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _save_message(self, db: Session, session_identifier: str, role: str, content: str):
        """Save message to database"""
        message = Message(
            session_identifier=session_identifier,
            role=role,
            content=content
        )
        db.add(message)
        db.commit()

    def _save_assessment(self, db: Session, session_identifier: str, assessment_data: Dict) -> int:
        """Save assessment to database"""
        assessment = AssessmentReport(
            session_identifier=session_identifier,
            conditions=assessment_data.get("conditions", []),
            symptoms=assessment_data.get("symptoms", []),
            severity_level=assessment_data.get("severity_level", "unknown"),
            report_content=assessment_data.get("report_content", ""),
            conversation_quality=assessment_data.get("conversation_quality"),
            risk_factors=assessment_data.get("risk_factors", []),
            protective_factors=assessment_data.get("protective_factors", []),
            urgency_level=assessment_data.get("urgency_level"),
            recommendations=assessment_data.get("recommendations", []),
            limitations=assessment_data.get("limitations")
        )
        
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        
        return assessment.id

    def _create_new_session_with_access_code(self, db: Session, old_session_id: str) -> str:
        """Create new session and transfer access code from old session"""
        try:
            # Get current subscription from old session
            from app.models import ConversationUsage
            usage = db.query(ConversationUsage).filter(
                ConversationUsage.session_identifier == old_session_id
            ).first()
            
            if not usage:
                # Create new session without access code
                new_session_id = self.subscription_service.generate_session_identifier()
                return new_session_id
            
            # Create new session
            new_session_id = self.subscription_service.generate_session_identifier()
            
            # Create new conversation
            new_conversation = Conversation(
                session_identifier=new_session_id,
                title="New Assessment Session"
            )
            db.add(new_conversation)
            
            # Transfer access code to new session
            usage.session_identifier = new_session_id
            usage.messages_used = 0  # Reset message count
            
            db.commit()
            
            # Clear old session data from Redis
            self.redis_client.delete(f"msg_count:{old_session_id}")
            
            return new_session_id
            
        except Exception as e:
            logger.error(f"Failed to create new session: {e}")
            # Fallback: create session without access code
            return self.subscription_service.generate_session_identifier()
