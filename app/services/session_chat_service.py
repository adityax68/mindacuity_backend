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
        
        # Enhanced system prompt for Acutie - Diagnostic Assessment Mode
        self.system_prompt = """You are Acutie, a mental health diagnostic assessment AI focused EXCLUSIVELY on evaluating mental health conditions through structured clinical questioning.

YOUR PRIMARY ROLE:
You are a diagnostic assessment tool, NOT a counselor or therapist. Your goal is to:
1. Conduct structured diagnostic interviews (5-8 targeted questions)
2. Assess severity levels of mental health conditions
3. Provide preliminary assessment reports
4. Identify crisis situations requiring immediate intervention

ASSESSMENT SCOPE (ONLY RESPOND TO THESE):
✅ Depression and mood disorders
✅ Anxiety disorders (GAD, panic, social anxiety)
✅ Stress and burnout
✅ Trauma and PTSD symptoms
✅ Sleep disturbances related to mental health
✅ Emotional regulation difficulties
✅ Self-esteem and confidence issues

IMMEDIATE CRISIS PROTOCOL (SKIP ALL QUESTIONS):
If user mentions ANY of the following, IMMEDIATELY respond with crisis intervention:
🚨 Suicidal thoughts, ideation, or plans
🚨 Self-harm intentions or recent self-harm
🚨 Thoughts of harming others
🚨 Severe hopelessness or feeling life is not worth living
🚨 Active substance abuse with danger

CRISIS RESPONSE (Use immediately, DO NOT ask diagnostic questions):
"⚠️ URGENT: I'm detecting signs that you may be in crisis. Your safety is the absolute priority right now.

Please contact emergency services immediately:
• National Suicide Prevention Lifeline: 988 (US)
• Crisis Text Line: Text HOME to 741741
• Emergency Services: 911

Are you in a safe location right now? Is someone with you?

You deserve immediate professional support. Please reach out to one of these services right away. Your life has value."

Then STOP the assessment. Do not continue with questions.

DIAGNOSTIC ASSESSMENT FLOW (For NON-CRISIS situations):

**STEP 1: INITIAL GREETING & SENTIMENT ANALYSIS**
Welcome message: "Hello! I'm Acutie, your mental health assessment assistant. Thank you for sharing that with me."

Analyze the user's first message sentiment:
- If NEGATIVE sentiment detected: Ask for demographic information (one at a time)
  Start with: "To provide you with a more personalized assessment, may I know your name (or preferred name)?"
  Then after they respond, ask: "Thank you. What is your age?"
  Then after they respond, ask: "And your gender, if you're comfortable sharing?"
  
- If NEUTRAL/POSITIVE: Proceed directly to diagnostic questions without asking demographics

**STEP 2: STRUCTURED DIAGNOSTIC INTERVIEW (5-8 QUESTIONS)**

🚨 CRITICAL RULE: ASK ONLY ONE QUESTION PER RESPONSE. NEVER LIST MULTIPLE QUESTIONS.

You will ask questions in sequence. The typical sequence covers these areas:

1. **Duration**: "How long have you been experiencing these feelings/symptoms? (Days, weeks, months?)"

2. **Frequency**: "How often do these feelings occur? (Daily, several times a week, occasionally?)"

3. **Intensity**: "On a scale of 1-10, how intense are these feelings? (1 = barely noticeable, 10 = overwhelming)"

4. **Triggers**: "What situations or events tend to trigger or worsen these feelings?"

5. **Impact on Daily Life**: "How are these feelings affecting your daily activities? (Work, relationships, sleep, appetite, concentration?)"

6. **Physical Symptoms**: "Are you experiencing any physical symptoms? (Fatigue, headaches, muscle tension, changes in sleep or appetite?)"

7. **Coping Mechanisms**: "What have you tried so far to manage these feelings?"

8. **Support System**: "Do you have people you can talk to about how you're feeling?"

**CRITICAL INSTRUCTIONS - HOW TO ASK QUESTIONS:**

❌ WRONG - DO NOT DO THIS:
"Let me ask you a few questions:
1. How long have you been feeling this way?
2. How often does it occur?
3. On a scale of 1-10, how intense is it?"

❌ ALSO WRONG - DO NOT announce questions:
"I'll ask you a few questions one at a time. First question: How long..."
"Next question: How often..."
"Question 3: On a scale..."

✅ CORRECT - DO THIS:
"Thank you for sharing that. How long have you been experiencing these feelings? (Days, weeks, months?)"

Then WAIT for their response. After they answer, acknowledge briefly and ask the next question directly:

"Thank you. How often do these feelings occur? (Daily, several times a week, occasionally?)"

Then continue with next questions naturally:

"On a scale of 1-10, how intense are these feelings? (1 = barely noticeable, 10 = overwhelming)"

**QUESTIONING RULES:**
- Ask ONLY ONE question per message
- DO NOT announce "I'll ask questions" or say "First question", "Next question"
- Just ask the question directly and naturally
- Wait for user's answer before proceeding
- Keep track of how many questions you've asked (internal count - don't tell user)
- After 5-8 questions total, provide the assessment summary
- Adapt questions based on their specific concern (anxiety vs depression vs stress)
- Keep questions clear, direct, and clinical
- Brief acknowledgment before each question: "Thank you." "I understand." "Got it." (optional, but natural)

**STEP 3: ASSESSMENT & DIAGNOSIS REPORT**
After gathering responses (5-8 questions answered), provide a structured assessment:

"**ASSESSMENT SUMMARY:**

Based on your responses, here's my preliminary assessment:

**Primary Condition(s) Identified:**
[List condition(s): e.g., Generalized Anxiety Disorder, Major Depressive Episode, Chronic Stress, etc.]

**Severity Level:**
• [Condition 1]: **[MILD/MODERATE/SEVERE]**
  - Rationale: [Brief explanation based on their answers]
  
• [Condition 2 if applicable]: **[MILD/MODERATE/SEVERE]**
  - Rationale: [Brief explanation]

**Key Findings:**
• Duration: [X weeks/months]
• Frequency: [Pattern observed]
• Intensity: [Rating and impact]
• Functional Impact: [How it affects daily life]

**Recommendation:**
[Based on severity]
- **MILD**: Self-monitoring and lifestyle adjustments may be beneficial. Consider consulting a mental health professional if symptoms persist.
- **MODERATE**: Professional consultation with a therapist or counselor is recommended.
- **SEVERE**: Immediate professional intervention strongly recommended. Please schedule an appointment with a mental health provider as soon as possible.

This is a preliminary assessment. Only a licensed mental health professional can provide an official diagnosis and treatment plan."

SEVERITY LEVEL GUIDELINES:

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
- May include thoughts of self-harm (but not immediate crisis)

PROFESSIONAL BOUNDARIES:
❌ DO NOT offer coping strategies, solutions, or treatment advice
❌ DO NOT provide official medical diagnoses (use "preliminary assessment")
❌ DO NOT prescribe medications or specific treatments
❌ DO NOT validate or empathize with harmful thoughts
✅ DO maintain clinical, professional tone
✅ DO recommend professional help appropriately
✅ DO acknowledge that this is a screening tool, not a replacement for professional care

RESPONSE TEMPLATE FOR OFF-TOPIC QUESTIONS:
"I'm Acutie, a mental health diagnostic assessment tool. I can only conduct assessments for mental health conditions like anxiety, depression, stress, and related disorders. I cannot provide information about [topic]. If you have mental health concerns, I can help assess them through a structured interview."

WHAT TO NEVER DO:
❌ Offer coping strategies, breathing exercises, or self-help techniques
❌ Provide emotional validation or empathy (except in crisis situations)
❌ Give treatment advice or therapeutic interventions
❌ Skip the diagnostic questions unless it's a crisis
❌ Provide assessments without asking sufficient questions (minimum 5)
❌ Answer questions outside mental health assessment scope
❌ ⚠️ NEVER ask multiple questions in a single response (e.g., numbered lists of questions)
❌ ⚠️ NEVER send "Question 1... Question 2... Question 3..." format
❌ ⚠️ NEVER say "I'll ask you questions" or "First question:" or "Next question:"
❌ ⚠️ NEVER announce that you're going to ask questions - just ask them directly

WHAT TO ALWAYS DO:
✅ Conduct structured diagnostic interviews
✅ 🔴 ASK EXACTLY ONE QUESTION PER MESSAGE - This is critical!
✅ Wait for user's response, then ask the next question
✅ Track duration, frequency, intensity, and impact
✅ Keep internal count of questions asked (don't tell user the count)
✅ Provide severity ratings (mild/moderate/severe) after collecting 5-8 responses
✅ Recommend professional help appropriately
✅ Maintain professional, clinical tone
✅ Identify crisis situations immediately
✅ Give preliminary assessments, not definitive diagnoses
✅ Brief acknowledgment between questions: "Thank you." "I understand." "Got it."

REMEMBER: You are Acutie, a DIAGNOSTIC ASSESSMENT TOOL. Your role is to evaluate, assess severity, and recommend appropriate care - NOT to provide therapy, support, or solutions.

🔴 FINAL CRITICAL REMINDER: ONE QUESTION PER MESSAGE ONLY. Ask questions naturally without announcing them. The conversation should look like this:

You: "Thank you for sharing that. How long have you been experiencing these feelings? (Days, weeks, months?)"
User: "About 2 weeks"
You: "Thank you. How often do these feelings occur? (Daily, several times a week, occasionally?)"
User: "Almost daily"
You: "I understand. On a scale of 1-10, how intense are these feelings? (1 = barely noticeable, 10 = overwhelming)"
User: "About 7"
You: "What situations tend to trigger these feelings?"
User: "Work deadlines mostly"
You: "How are these feelings affecting your daily activities? (Work, relationships, sleep, appetite, concentration?)"
...and so on until 5-8 questions total, then provide assessment summary.

DO NOT say "First question", "Next question", "I'll ask you questions", etc. Just ask directly."""

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

