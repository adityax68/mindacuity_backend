import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from openai import OpenAI
import logging
from cryptography.fernet import Fernet
from sqlalchemy.orm import Session
from app.models import ChatConversation, ChatMessage, RateLimit, User
from app.schemas import ChatMessageRequest, ChatResponse
from app.config import settings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        # Initialize OpenAI client for chat 
        api_key = settings.openai_api_key
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=api_key)
        
        # Initialize encryption key
        encryption_key = settings.encryption_key
        if not encryption_key:
            # Generate a new key if not provided (for development)
            encryption_key = Fernet.generate_key()
            logger.warning("ENCRYPTION_KEY not found, using generated key. Set this in production!")
        else:
            # Ensure the key is in bytes format
            encryption_key = encryption_key.encode()
        
        self.cipher = Fernet(encryption_key)
        
        # Rate limiting configuration
        self.max_messages_per_minute = 100
        
        # Enhanced system prompt for Acutie
        self.system_prompt = """You are Acutie, an empathetic AI companion focused EXCLUSIVELY on mental health support and emotional well-being.

YOUR CAPABILITIES (ONLY RESPOND TO THESE TOPICS):
✅ Mental health issues (depression, anxiety, stress, etc.)
✅ Emotional support and feelings
✅ Relationship problems and emotional impact
✅ Work/life stress and burnout
✅ Sleep problems and mental health
✅ Self-harm and suicidal thoughts (CRISIS HANDLING)
✅ Coping strategies and mental wellness
✅ Trauma and emotional healing
✅ Self-esteem and confidence issues
✅ Grief and loss
✅ Addiction and mental health
✅ Panic attacks and anxiety disorders
✅ Mood disorders and emotional regulation

TOPICS OUTSIDE YOUR SCOPE (POLITELY DECLINE):
❌ Politics, politicians, current events
❌ General knowledge questions
❌ Technical or academic topics
❌ Entertainment, movies, sports
❌ Business or financial advice
❌ Travel or lifestyle tips
❌ Historical facts or trivia
❌ Scientific explanations (unless mental health related)
❌ Any topic not related to mental health or emotional well-being

CRISIS ESCALATION PROTOCOL:
- IMMEDIATE: "Are you safe right now? Are you alone?"
- URGENT: Provide crisis hotlines (988, local numbers)
- GROUNDING: "Let's do a quick grounding exercise: Name 5 things you can see..."
- REFERRAL: "This is serious and you deserve professional support"
- FOLLOW-UP: Check safety in next response
- SAFETY FIRST: Never validate harmful thoughts - always treat as serious safety concerns

RESPONSE STRUCTURE:
1. LISTEN & ACKNOWLEDGE: "I hear you" or "That sounds really difficult"
2. VALIDATE FEELINGS: "Your feelings are completely understandable"
3. ASK PERMISSION: "Would you like to explore some coping strategies?" or "Would it be helpful to talk about ways to manage this?"
4. OFFER SOLUTIONS (only if user agrees): Provide 1-2 specific techniques
5. ENCOURAGEMENT: "You're showing strength by reaching out"
6. NEXT STEPS: Suggest immediate action or professional help

IMPORTANT: Always listen first, validate feelings, and ask permission before offering solutions. Don't jump straight to advice.

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

EXAMPLE CONVERSATION FLOWS:

MENTAL HEALTH TOPIC:
User: "I had a breakup today, I feel suicidal"
Bot: "I'm deeply concerned about your safety. Breakups are incredibly painful, and I hear how much you're hurting right now. First, are you safe right now? Are you alone? Your feelings of pain and sadness are completely understandable given what you're going through, but I want to be very clear that suicidal thoughts are serious and require immediate professional help. These thoughts are not a solution and you deserve support to get through this difficult time. Would you like to try a quick grounding exercise together to help you feel more present? We can name 5 things you can see around you right now..."

OFF-TOPIC QUESTION:
User: "Who is Rahul Gandhi?"
Bot: "I'm Acutie, and I'm specifically designed to help with mental health and emotional well-being. I can't provide information about politics or politicians as it's outside my area of expertise. However, if you're dealing with stress, anxiety, depression, or any emotional challenges, I'm here to support you. Would you like to talk about how you're feeling or any mental health concerns you might have?"

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

    def _encrypt_message(self, message: str) -> str:
        """Encrypt a message using Fernet"""
        try:
            encrypted = self.cipher.encrypt(message.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Failed to encrypt message: {e}")
            # Fallback: hash the message if encryption fails
            return hashlib.sha256(message.encode()).hexdigest()

    def _decrypt_message(self, encrypted_message: str) -> str:
        """Decrypt a message using Fernet"""
        try:
            decrypted = self.cipher.decrypt(encrypted_message.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Failed to decrypt message: {e}")
            return "[Message could not be decrypted]"

    def _check_rate_limit(self, db: Session, user_id: int) -> bool:
        """Check if user has exceeded rate limit"""
        try:
            now = datetime.utcnow()
            window_start = now - timedelta(minutes=1)
            
            # Get current rate limit record
            rate_limit = db.query(RateLimit).filter(
                RateLimit.user_id == user_id,
                RateLimit.window_start >= window_start
            ).first()
            
            if not rate_limit:
                # Create new rate limit record
                rate_limit = RateLimit(
                    user_id=user_id,
                    message_count=1,
                    window_start=now
                )
                db.add(rate_limit)
                db.commit()
                return True
            
            if rate_limit.message_count >= self.max_messages_per_minute:
                return False
            
            # Increment message count
            rate_limit.message_count += 1
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Allow message if rate limiting fails
            return True

    def _get_conversation_context(self, db: Session, conversation_id: int, max_messages: int = 10) -> List[Dict[str, str]]:
        """Get recent conversation context for OpenAI"""
        try:
            messages = db.query(ChatMessage).filter(
                ChatMessage.conversation_id == conversation_id
            ).order_by(ChatMessage.created_at.desc()).limit(max_messages).all()
            
            # Reverse to get chronological order
            messages.reverse()
            
            context = []
            for msg in messages:
                content = self._decrypt_message(msg.encrypted_content)
                context.append({
                    "role": msg.role,
                    "content": content
                })
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to get conversation context: {e}")
            return []

    def _create_or_get_conversation(self, db: Session, user_id: int, conversation_id: Optional[int] = None) -> ChatConversation:
        """Create new conversation or get existing one"""
        if conversation_id:
            conversation = db.query(ChatConversation).filter(
                ChatConversation.id == conversation_id,
                ChatConversation.user_id == user_id
            ).first()
            
            if not conversation:
                raise ValueError("Conversation not found or access denied")
            
            return conversation
        
        # Create new conversation
        conversation = ChatConversation(
            user_id=user_id,
            title="New Chat"
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        
        return conversation

    def _generate_title_from_message(self, message: str) -> str:
        """Generate a title for the conversation based on first message"""
        try:
            # Use OpenAI to generate a short, relevant title
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are Acutie. Generate a short, 3-5 word title for this conversation that reflects the emotional topic. Only return the title, nothing else."},
                    {"role": "user", "content": message}
                ],
                max_tokens=20,
                temperature=0.7
            )
            
            title = response.choices[0].message.content.strip()
            # Clean up the title
            title = title.replace('"', '').replace("'", "")
            if len(title) > 50:
                title = title[:47] + "..."
            
            return title
            
        except Exception as e:
            logger.error(f"Failed to generate title: {e}")
            # Fallback title
            words = message.split()[:3]
            return " ".join(words) + "..." if len(words) == 3 else message[:30] + "..."

    async def process_chat_message(self, db: Session, user_id: int, chat_request: ChatMessageRequest) -> ChatResponse:
        """Process a chat message and return AI response"""
        try:
            # Check rate limit
            if not self._check_rate_limit(db, user_id):
                raise ValueError(f"Rate limit exceeded. Maximum {self.max_messages_per_minute} messages per minute.")
            
            # Get or create conversation
            conversation = self._create_or_get_conversation(db, user_id, chat_request.conversation_id)
            
            # Store user message
            user_message = ChatMessage(
                conversation_id=conversation.id,
                user_id=user_id,
                role="user",
                content=chat_request.message,  # Store plain text for search
                encrypted_content=self._encrypt_message(chat_request.message)
            )
            db.add(user_message)
            db.commit()
            db.refresh(user_message)
            
            # Generate title for new conversations
            if not conversation.title:
                try:
                    title = self._generate_title_from_message(chat_request.message)
                    conversation.title = title
                    db.commit()
                except Exception as e:
                    logger.error(f"Failed to update conversation title: {e}")
            
            # Get conversation context
            context = self._get_conversation_context(db, conversation.id)
            
            # Prepare messages for OpenAI
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(context)
            
            # Get AI response
            ai_response = await self._get_ai_response(messages)
            
            # Store AI response
            ai_message = ChatMessage(
                conversation_id=conversation.id,
                user_id=user_id,
                role="assistant",
                content=ai_response,
                encrypted_content=self._encrypt_message(ai_response)
            )
            db.add(ai_message)
            db.commit()
            db.refresh(ai_message)
            
            # Update conversation timestamp
            conversation.updated_at = datetime.utcnow()
            db.commit()
            
            return ChatResponse(
                conversation_id=conversation.id,
                assistant_message=ai_response,
                message_id=ai_message.id
            )
            
        except Exception as e:
            logger.error(f"Failed to process chat message: {e}")
            raise

    async def _get_ai_response(self, messages: List[Dict[str, str]]) -> str:
        """Get response from OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error details: {str(e)}")
            
            # Fallback response - more appropriate for crisis situations
            if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                return "I'm experiencing high demand right now, but I want to make sure you're safe. If you're having thoughts of harming yourself, please call a crisis hotline immediately. I'll be back to help you soon."
            elif "timeout" in str(e).lower():
                return "I'm taking longer than usual to respond, but I want to make sure you're safe. If you're having thoughts of harming yourself, please call a crisis hotline immediately. I'm here to help once the connection is restored."
            else:
                return "I'm experiencing a technical issue right now, but I want to make sure you're safe. If you're having thoughts of harming yourself, please call a crisis hotline immediately. I'm here to help once the connection is restored."

    def get_user_conversations(self, db: Session, user_id: int) -> List[ChatConversation]:
        """Get all conversations for a user"""
        try:
            conversations = db.query(ChatConversation).filter(
                ChatConversation.user_id == user_id
            ).order_by(ChatConversation.updated_at.desc()).all()
            
            return conversations
            
        except Exception as e:
            logger.error(f"Failed to get user conversations: {e}")
            return []

    def get_conversation_messages(self, db: Session, conversation_id: int, user_id: int) -> List[ChatMessage]:
        """Get all messages for a conversation"""
        try:
            # Verify user owns this conversation
            conversation = db.query(ChatConversation).filter(
                ChatConversation.id == conversation_id,
                ChatConversation.user_id == user_id
            ).first()
            
            if not conversation:
                raise ValueError("Conversation not found or access denied")
            
            messages = db.query(ChatMessage).filter(
                ChatMessage.conversation_id == conversation_id
            ).order_by(ChatMessage.created_at.asc()).all()
            
            # Decrypt messages
            for message in messages:
                message.content = self._decrypt_message(message.encrypted_content)
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get conversation messages: {e}")
            return [] 