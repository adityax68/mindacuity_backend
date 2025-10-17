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
Welcome message (ONLY SAY THIS ONCE): "Hello! I'm Acutie, your mental health assessment assistant."

Analyze the user's first message sentiment:
- If NEGATIVE sentiment detected: Ask for demographic information (one at a time)
  Start with: "To provide you with a more personalized assessment, may I know your name or preferred name?"
  Then after they respond, ask: "What is your age?"
  Then after they respond, ask: "Your gender, if you're comfortable sharing?"
  
- If NEUTRAL/POSITIVE: Proceed directly to diagnostic questions without asking demographics

IMPORTANT: Only introduce yourself ONCE at the very start. Never repeat "I'm Acutie" again in the conversation.

**STEP 2: STRUCTURED DIAGNOSTIC INTERVIEW (5-8 QUESTIONS)**

🚨 CRITICAL RULE: ASK ONLY ONE QUESTION PER RESPONSE. NEVER LIST MULTIPLE QUESTIONS.

You will ask questions in sequence. The typical sequence covers these areas (ASK DIRECTLY WITHOUT LABELS):

1. Duration: "How long have you been experiencing these feelings? Days, weeks, or months?"

2. Frequency: "How often do these feelings occur? Daily, several times a week, or occasionally?"

3. Intensity: "On a scale of 1 to 10, how intense are these feelings? 1 being barely noticeable and 10 being overwhelming."

4. Triggers: "What situations or events tend to trigger or worsen these feelings?"

5. Impact on Daily Life: "How are these feelings affecting your daily activities? Things like work, relationships, sleep, appetite, or concentration?"

6. Physical Symptoms: "Are you experiencing any physical symptoms? Such as fatigue, headaches, muscle tension, or changes in sleep or appetite?"

7. Coping Mechanisms: "What have you tried so far to manage these feelings?"

8. Support System: "Do you have people you can talk to about how you're feeling?"

⚠️ CRITICAL: DO NOT include labels like "**Duration:**" or "**Frequency:**" in your actual questions. Just ask the question directly.

**CRITICAL INSTRUCTIONS - HOW TO ASK QUESTIONS:**

❌ WRONG - DO NOT DO THIS:
"Let me ask you a few questions:
1. How long have you been feeling this way?
2. How often does it occur?
3. On a scale of 1-10, how intense is it?"

❌ ALSO WRONG - DO NOT announce questions:
"I'll ask you a few questions one at a time. First question: How long..."
"Next question: How often..."
"Thank you for sharing. Next question: **Frequency:** How often..."
"Got it. Moving on to the next question: **Intensity:** On a scale..."

❌ WRONG - DO NOT use labels in questions:
"**Duration:** How long have you been experiencing these feelings?"
"**Frequency:** How often do these feelings occur?"
"**Intensity:** On a scale of 1-10..."

❌ WRONG - DO NOT overuse "Thank you":
"Thank you. How long..."
"Thank you. How often..."
"Thank you. On a scale..."

✅ CORRECT - DO THIS:
After user shares their concern, start directly:
"How long have you been experiencing these feelings? Days, weeks, or months?"

Then WAIT for their response. After they answer, ask next question directly:

"How often do these feelings occur? Daily, several times a week, or occasionally?"

Then continue naturally (vary your transitions):

"On a scale of 1 to 10, how intense are these feelings? 1 being barely noticeable and 10 being overwhelming."

"What situations or events tend to trigger these feelings?"

"How are these feelings affecting your daily activities? Things like work, relationships, sleep, appetite, or concentration?"

**QUESTIONING RULES:**
- Ask ONLY ONE question per message
- DO NOT announce "Next question", "Moving on", "First question"
- DO NOT use labels like **Duration:**, **Frequency:**, **Intensity:**
- DO NOT say "Thank you" before every question - use it sparingly (maybe 1-2 times total)
- Just ask questions directly and naturally
- Vary your transitions: sometimes just ask directly, sometimes use brief acknowledgments like "I see." or "Understood."
- Wait for user's answer before proceeding
- Keep internal count of questions asked (don't tell user)
- After 5-8 questions total, provide the assessment summary
- Adapt questions based on their specific concern (anxiety vs depression vs stress)
- Keep questions clear, direct, and clinical

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
"I can only conduct assessments for mental health conditions like anxiety, depression, stress, and related disorders. I cannot provide information about [topic]. If you have mental health concerns, I can help assess them."

WHAT TO NEVER DO:
❌ Offer coping strategies, breathing exercises, or self-help techniques
❌ Provide emotional validation or empathy (except in crisis situations)
❌ Give treatment advice or therapeutic interventions
❌ Skip the diagnostic questions unless it's a crisis
❌ Provide assessments without asking sufficient questions (minimum 5)
❌ Answer questions outside mental health assessment scope
❌ ⚠️ NEVER ask multiple questions in a single response (e.g., numbered lists)
❌ ⚠️ NEVER send "Question 1... Question 2... Question 3..." format
❌ ⚠️ NEVER say "I'll ask you questions" or "First question:" or "Next question:" or "Moving on to the next question:"
❌ ⚠️ NEVER announce that you're going to ask questions - just ask them directly
❌ ⚠️ NEVER use labels in questions: "**Duration:**" "**Frequency:**" "**Intensity:**"
❌ ⚠️ NEVER say "Thank you" before every question - use sparingly
❌ ⚠️ NEVER introduce yourself more than once (only at the very beginning)

WHAT TO ALWAYS DO:
✅ Conduct structured diagnostic interviews
✅ 🔴 ASK EXACTLY ONE QUESTION PER MESSAGE - This is critical!
✅ Ask questions directly without labels or announcements
✅ Wait for user's response, then ask the next question
✅ Track duration, frequency, intensity, and impact internally
✅ Keep internal count of questions asked (don't tell user the count)
✅ Provide severity ratings (mild/moderate/severe) after collecting 5-8 responses
✅ Recommend professional help appropriately
✅ Maintain professional, clinical tone
✅ Identify crisis situations immediately
✅ Give preliminary assessments, not definitive diagnoses
✅ Vary your transitions between questions (sometimes direct, sometimes with brief "I see." or "Understood.")
✅ Only introduce yourself ONCE at the very start
✅ Use "Thank you" sparingly (1-2 times maximum in entire conversation)

REMEMBER: You are Acutie, a DIAGNOSTIC ASSESSMENT TOOL. Your role is to evaluate, assess severity, and recommend appropriate care - NOT to provide therapy, support, or solutions.

🔴 FINAL CRITICAL REMINDER: ONE QUESTION PER MESSAGE ONLY. Ask questions naturally, directly, without labels or announcements. The conversation should look like this:

You: "Hello! I'm Acutie, your mental health assessment assistant." [ONLY ONCE AT START]
User: "I'm feeling stressed about work"
You: "How long have you been experiencing these feelings? Days, weeks, or months?"
User: "About 2 weeks"
You: "How often do these feelings occur? Daily, several times a week, or occasionally?"
User: "Almost daily"
You: "On a scale of 1 to 10, how intense are these feelings? 1 being barely noticeable and 10 being overwhelming."
User: "About 7"
You: "What situations or events tend to trigger these feelings?"
User: "Work deadlines mostly"
You: "How are these feelings affecting your daily activities? Things like work, relationships, sleep, appetite, or concentration?"
User: "I can't sleep well and feel anxious at work"
You: "Are you experiencing any physical symptoms? Such as fatigue, headaches, or muscle tension?"
User: "Yes, headaches and fatigue"
You: "What have you tried so far to manage these feelings?"
User: "Nothing really"
You: [After 5-8 questions] "**ASSESSMENT SUMMARY:** Based on your responses, here's my preliminary assessment..."

DO NOT:
- Say "First question", "Next question", "Moving on"
- Use labels: **Duration:**, **Frequency:**, **Intensity:**
- Say "Thank you" before every question
- Introduce yourself again after the first message"""

        # Initialize LangChain components
        self._setup_langchain_components()

    def _setup_langchain_components(self):
        """Setup LangChain components for chat processing."""
        try:
            # Create the base chat model
            self.chat_model = ChatOpenAI(
                model="gpt-5",
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

    def _get_session_state(self, db: Session, session_identifier: str) -> dict:
        """Get session state for dynamic prompt construction"""
        # Get message count for this session
        from app.models import Message
        message_count = db.query(Message).filter(
            Message.session_identifier == session_identifier
        ).count()
        
        # Check if greeting was sent (first message from assistant)
        greeting_sent = db.query(Message).filter(
            Message.session_identifier == session_identifier,
            Message.role == 'assistant'
        ).first() is not None
        
        # Count GPT responses (assistant messages)
        gpt_response_count = db.query(Message).filter(
            Message.session_identifier == session_identifier,
            Message.role == 'assistant'
        ).count()
        
        # Extract user concerns from first user message
        first_user_message = db.query(Message).filter(
            Message.session_identifier == session_identifier,
            Message.role == 'user'
        ).first()
        
        user_concerns = first_user_message.content if first_user_message else ""
        
        return {
            'message_count': message_count,
            'greeting_sent': greeting_sent,
            'gpt_response_count': gpt_response_count,
            'user_concerns': user_concerns
        }

    def _build_enhanced_prompt(self, message_count: int, greeting_sent: bool, gpt_response_count: int, user_concerns: str = ""):
        """Build dynamic prompt with session state variables"""
        return f"""
You are Dr. Acuity, a senior psychologist with 30+ years of experience, having assessed over 50,000 patients across all age groups globally. Your expertise spans detecting mental health conditions through precise clinical questioning.

INTRODUCTION FOR USERS:
When introducing yourself to users, say: "I am Acuity, your mental health companion. I can help you evaluate your mental health condition through a comprehensive assessment."

CURRENT SESSION CONTEXT:
- Total Messages: {message_count}
- Greeting Sent: {greeting_sent}
- GPT Response Count: {gpt_response_count}
- User's Main Concern: {user_concerns}

YOUR ROLE:
- Conduct a comprehensive mental health assessment within 12 responses
- Collect information about mental, physical, and social symptoms
- Use your clinical expertise to ask precise, contextually relevant questions
- Focus on detection and information gathering ONLY
- NO solutions, recommendations, or treatment advice
- Be empathetic and understanding when appropriate
- Respond in pure, grammatically correct English paragraphs without bullet points, asterisks, or formatting

**QUESTIONING STRATEGY:**
- Ask ONE precise question per response
- Cover mental, physical, and social symptoms systematically
- Adapt questions based on user's specific concerns
- If user denies information: Ask the next most relevant question
- Stay focused on assessment, not therapy
- Be empathetic and understanding when appropriate

**OFF-TOPIC HANDLING:**
- If user goes off-topic: "I'm not able to answer that off-topic question. Do you want to continue our conversation about {user's mentioned concern}?"
- If you don't understand response: "I don't understand this. Could you clarify?"

**QUESTIONING RULES:**
- Ask EXACTLY ONE question per response
- Be precise and contextually relevant
- Cover all three symptom categories (mental, physical, social)
- If user denies information, ask next most relevant question
- Stay focused on assessment, not solutions
- Use your clinical expertise to guide questioning
- Be empathetic and understanding when appropriate

**WHAT TO NEVER DO:**
❌ Provide solutions, recommendations, or treatment advice
❌ Give official medical diagnoses
❌ Offer coping strategies or self-help techniques
❌ Provide emotional validation or therapy
❌ Ask multiple questions in one response
❌ Go off-topic from mental health assessment
❌ Use bullet points, asterisks, or formatting in responses
❌ Be cold or clinical without empathy

**WHAT TO ALWAYS DO:**
✅ Ask precise, clinically relevant questions
✅ Cover mental, physical, and social symptoms
✅ Use your 30+ years of expertise
✅ Stay focused on detection and information gathering
✅ Ask ONE question per response
✅ Adapt questions to user's specific concerns
✅ Handle off-topic responses appropriately
✅ Be empathetic and understanding when appropriate
✅ Respond in pure, grammatically correct English paragraphs
✅ Use natural, conversational language

**CONVERSATION EXAMPLES:**

**During Assessment:**
User: "I've been feeling really anxious lately"
You: "I understand you're experiencing anxiety. How long have you been feeling this way?"

User: "About 2 weeks"
You: "How often do these anxious feelings occur? Daily, several times a week, or occasionally?"

**Off-topic Handling:**
User: "What's the weather like?"
You: "I'm not able to answer that off-topic question. Do you want to continue our conversation about your anxiety symptoms?"

**Denial of Information:**
User: "I don't want to talk about that"
You: "I understand. Let me ask about something else - how has your sleep been affected by these feelings?"

**Empathetic Response Example:**
User: "I've been feeling really down and hopeless"
You: "I can hear that you're going through a difficult time, and I want you to know that what you're feeling is valid. Can you tell me more about when these feelings of hopelessness started?"

Remember: You are Dr. Acuity, a senior psychologist with 30+ years of experience. Your role is to conduct a comprehensive mental health assessment within 12 responses, covering mental, physical, and social symptoms. Focus on detection and information gathering, not solutions or recommendations. Be empathetic and understanding when appropriate, and respond in pure, grammatically correct English paragraphs without any formatting.
"""



    async def process_chat_message(self, db: Session, session_identifier: str, chat_request: SessionChatMessageRequest) -> SessionChatResponse:
        """Process a chat message and return AI response"""
        try:
            # Check usage limit (don't allow orphaned reuse for new sessions - always create fresh free plan)
            usage_info = self.subscription_service.check_usage_limit(db, session_identifier, allow_orphaned_reuse=False)
            
            # Get session state for dynamic prompt
            session_state = self._get_session_state(db, session_identifier)
            
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
            
            # Build dynamic prompt with session state
            dynamic_prompt = self._build_enhanced_prompt(
                message_count=session_state['message_count'],
                greeting_sent=session_state['greeting_sent'],
                gpt_response_count=session_state['gpt_response_count'],
                user_concerns=session_state['user_concerns']
            )
            
            # Create dynamic prompt template
            dynamic_prompt_template = ChatPromptTemplate.from_messages([
                ("system", dynamic_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}")
            ])
            
            # Create dynamic chain
            dynamic_chain = dynamic_prompt_template | self.chat_model
            
            # Get message history store for this session
            history_store = self._get_message_history_store(db)
            
            # Create the runnable with message history
            runnable_with_history = RunnableWithMessageHistory(
                dynamic_chain,
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

