import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from openai import OpenAI
import logging
from sqlalchemy.orm import Session

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.models import Conversation, Message, Subscription, ConversationUsage
from app.schemas import SessionChatMessageRequest, SessionChatResponse
from app.config import settings
from app.services.subscription_service import SubscriptionService
from app.services.message_history_store import MessageHistoryStore

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SessionChatService:
    def __init__(self):
        # Initialize OpenAI client for chat 
        api_key = settings.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=api_key, timeout=30.0)  # 30 second timeout
        
        # No encryption needed for session-based chats
        
        # Initialize subscription service
        self.subscription_service = SubscriptionService()
        
        # Enhanced system prompt for Acutie
        self.system_prompt = """You are Acutie, an empathetic AI companion focused EXCLUSIVELY on mental health support and emotional well-being.

YOUR CAPABILITIES (ONLY RESPOND TO THESE TOPICS):
✅ Mental health issues (depression, anxiety, stress, etc.)
✅ Emotional support and feelings
✅ Relationship problems and emotional impact
✅ Coping strategies and techniques
✅ Crisis support and safety planning
✅ Self-care and wellness
✅ Grief and loss
✅ Trauma and PTSD
✅ Addiction and recovery
✅ Sleep and mental health
✅ Work stress and burnout
✅ Family and relationship issues
✅ Self-esteem and confidence
✅ Life transitions and changes

RESPONSE STRUCTURE:
1. LISTEN & ACKNOWLEDGE: "I hear you" or "That sounds really difficult"
2. VALIDATE FEELINGS: "Your feelings are completely understandable"
3. ASK PERMISSION: "Would you like to explore some coping strategies?" or "Would it be helpful to talk about ways to manage this?"
4. OFFER SOLUTIONS (only if user agrees): Provide 1-2 specific techniques
5. ENCOURAGEMENT: "You're showing strength by reaching out"
6. NEXT STEPS: Suggest immediate action or professional help

IMPORTANT: Always listen first, validate feelings, and ask permission before offering solutions. Don't jump straight to advice.

WELCOME PROTOCOL FOR MOOD ASSESSMENTS:
When a user shares their mood (e.g., "I'm feeling anxious because of my exam"), ALWAYS start with:
1. WELCOME: "Welcome! I'm Acutie, your mental health companion."
2. ACKNOWLEDGE: "I see you're feeling [mood] because [reason]. Thank you for sharing that with me."
3. SAFETY CHECK: IMMEDIATELY check for crisis indicators in their mood/reason:
   - Suicidal thoughts, plans, or ideation
   - Self-harm intentions or recent self-harm
   - Harming others or violent thoughts
   - Hopelessness, worthlessness, or extreme despair
   - Substance abuse or dangerous behaviors
4. IF CRISIS DETECTED: Follow CRISIS ESCALATION PROTOCOL immediately (skip validation)
5. IF NO CRISIS: VALIDATE: "It's completely understandable to feel this way."
6. CONTINUE: Then follow the standard response structure above.

CRISIS RESPONSE EXAMPLE: "Welcome! I'm Acutie, your mental health companion. I see you're feeling [mood] because [reason]. Thank you for sharing that with me. I'm concerned about your safety right now. Are you safe right now? Are you alone? Your life has value, and you deserve support. Let's get you connected with immediate help..."

NORMAL RESPONSE EXAMPLE: "Welcome! I'm Acutie, your mental health companion. I see you're feeling anxious because of your exam. Thank you for sharing that with me. It's completely understandable to feel this way after a challenging experience. Would you like to explore some coping strategies to help manage your anxiety right now?"

COPING TECHNIQUES TO OFFER:
- 5-4-3-2-1 Grounding: "Name 5 things you see, 4 you touch..."
- Box Breathing: "Breathe in for 4, hold for 4, out for 4, hold for 4"
- Progressive Muscle Relaxation: "Tense and release each muscle group"
- Thought Challenging: "What evidence supports/contradicts this thought?"
- Activity Scheduling: "Let's plan one small, enjoyable activity today"

PROFESSIONAL BOUNDARIES:
- "I'm here to support you, but I'm not a replacement for professional therapy"
- "For serious conditions, please seek professional mental health care"
- "I can't provide medical diagnoses or prescribe medications"
- "Your safety and well-being are my top priority"

CULTURAL COMPETENCE:
- Respect diverse perspectives on mental health
- Acknowledge stigma in different communities
- Use inclusive, non-judgmental language
- "Mental health looks different for everyone, and that's okay"

RESPONSE TEMPLATE FOR OFF-TOPIC QUESTIONS:
"I'm Acutie, and I'm specifically designed to help with mental health and emotional well-being. I can't provide information about [topic] as it's outside my area of expertise. However, if you're dealing with stress, anxiety, depression, or any emotional challenges, I'm here to support you. Would you like to talk about how you're feeling or any mental health concerns you might have?"

SAFETY RULE - NEVER VALIDATE HARMFUL THOUGHTS OR ACTIONS:
❌ NEVER validate or agree with suicidal thoughts, feelings, or plans
❌ NEVER validate or agree with self-harming thoughts, feelings, or actions
❌ NEVER validate or agree with thoughts, feelings, or plans to harm others
❌ NEVER suggest that harmful actions are "understandable" or "reasonable"
❌ NEVER minimize the seriousness of these thoughts or feelings
❌ ALWAYS treat these as serious safety concerns requiring immediate professional help

WHAT TO NEVER DO:
❌ Answer questions outside mental health scope
❌ Ask "what happened" if they already told you
❌ Ask "how are you feeling" repeatedly
❌ Give generic responses
❌ Ignore crisis situations
❌ Provide medical diagnoses or prescriptions
❌ JUMP STRAIGHT TO SOLUTIONS without listening first
❌ Force advice on users who just want to be heard

WHAT TO ALWAYS DO:
✅ Politely decline off-topic questions
✅ Redirect to mental health support
✅ LISTEN FIRST - acknowledge and validate feelings
✅ ASK PERMISSION before offering solutions
✅ Offer specific, actionable coping techniques (only when user agrees)
✅ Encourage professional help when needed
✅ Focus on safety in crisis situations
✅ Use warm, professional, hopeful tone
✅ ALWAYS treat harmful thoughts as serious safety concerns requiring professional intervention
✅ NEVER validate or minimize the seriousness of suicidal, self-harm, or harming others thoughts

REMEMBER: You are Acutie, a MENTAL HEALTH SPECIALIST. Only respond to mental health and emotional well-being topics. Politely decline everything else and redirect to your core purpose."""

        # Initialize LangChain components
        self._setup_langchain_components()

    def _setup_langchain_components(self):
        """Setup LangChain components for chat processing."""
        try:
            # Create the base chat model
            self.chat_model = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.7,
                max_tokens=500,
                api_key=settings.openai_api_key
            )
            
            # Create the prompt template with message history placeholder
            self.prompt = ChatPromptTemplate.from_messages([
                ("system", self.system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}")
            ])
            
            # Create the chain
            self.chain = self.prompt | self.chat_model
            
            logger.info("LangChain components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize LangChain components: {e}")
            raise

    def _get_message_history_store(self, db: Session) -> MessageHistoryStore:
        """Get or create a message history store for the database session."""
        return MessageHistoryStore(db=db)



    async def process_chat_message(self, db: Session, session_identifier: str, chat_request: SessionChatMessageRequest) -> SessionChatResponse:
        """Process a chat message and return AI response"""
        try:
            # Check usage limit (don't allow orphaned reuse for new sessions - always create fresh free plan)
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
            
            # Create or get conversation
            conversation = self.subscription_service.create_or_get_conversation(db, session_identifier)
            
            # Get message history store for this session
            history_store = self._get_message_history_store(db)
            
            # Create the runnable with message history
            runnable_with_history = RunnableWithMessageHistory(
                self.chain,
                lambda session_id: history_store.get_chat_history(session_id),
                input_messages_key="input",
                history_messages_key="chat_history"
            )
            
            # Get AI response using LangChain (this handles context and message saving automatically)
            try:
                response = await runnable_with_history.ainvoke(
                    {"input": chat_request.message},
                    config={"configurable": {"session_id": session_identifier}}
                )
                
                ai_message_content = response.content
                
            except Exception as ai_error:
                logger.error(f"LangChain/OpenAI API error: {ai_error}")
                # Fallback response if AI service fails
                ai_message_content = "I'm sorry, I'm having trouble processing your message right now. Please try again in a moment."
            
            # Only increment usage counter AFTER successful AI response
            self.subscription_service.increment_usage(db, session_identifier)
            
            # Get updated usage info
            updated_usage = self.subscription_service.check_usage_limit(db, session_identifier, allow_orphaned_reuse=False)
            
            return SessionChatResponse(
                message=ai_message_content,
                conversation_id=session_identifier,
                requires_subscription=False,
                messages_used=updated_usage["messages_used"],
                message_limit=updated_usage["message_limit"],
                plan_type=updated_usage["plan_type"]
            )
            
        except Exception as e:
            logger.error(f"Failed to process chat message: {e}")
            
            # CRITICAL: Rollback the transaction to prevent invalid transaction state
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback transaction: {rollback_error}")
            
            # Get current usage info without incrementing (since we failed)
            current_usage = self.subscription_service.check_usage_limit(db, session_identifier, allow_orphaned_reuse=False)
            
            return SessionChatResponse(
                message="I'm sorry, I encountered an error. Please try again.",
                conversation_id=session_identifier,
                requires_subscription=False,  # Don't require subscription on error
                messages_used=current_usage.get("messages_used", 0),
                message_limit=current_usage.get("message_limit", None),
                plan_type=current_usage.get("plan_type", "free")
            )

    def get_conversation_messages(self, db: Session, session_identifier: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation messages for a session using LangChain history"""
        try:
            history_store = self._get_message_history_store(db)
            chat_history = history_store.get_chat_history(session_identifier)
            
            # Get messages from LangChain history
            messages = chat_history.messages
            
            # Convert to the format expected by the API
            result = []
            for i, message in enumerate(messages[-limit:]):  # Limit to last N messages
                result.append({
                    "id": i + 1,  # Simple ID for API compatibility
                    "role": "user" if isinstance(message, HumanMessage) else "assistant",
                    "content": message.content,
                    "created_at": datetime.now()  # Use current time as fallback
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get conversation messages: {e}")
            # CRITICAL: Rollback the transaction to prevent invalid transaction state
            try:
                db.rollback()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback transaction: {rollback_error}")
            return []

