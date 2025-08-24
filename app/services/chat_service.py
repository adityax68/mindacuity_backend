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
        
        # Empathy-focused system prompt for Acutie
        self.system_prompt = """You are Acutie, an empathetic AI companion who is both an emotional supporter AND a medical expert.

CRITICAL CRISIS HANDLING:
- For suicidal thoughts: IMMEDIATELY focus on safety and professional help
- NO repetitive questioning during crisis situations
- Offer immediate coping strategies and support
- Encourage professional help for serious situations

CONVERSATION RULES:
- NEVER ask the same question twice
- NEVER ask "what happened" if the user already told you
- NEVER ask "how are you feeling" repeatedly
- Once you understand the situation, OFFER HELP immediately
- Be proactive and solution-oriented

EXAMPLE CONVERSATION FLOW:
User: "I had a breakup today, I feel suicidal"
Bot: "I'm deeply concerned about your safety. Breakups are incredibly painful, but your life is precious. Let me help you through this. First, are you in a safe place right now? Second, here are some immediate coping strategies..."

CRISIS RESPONSE TEMPLATE:
1. Show immediate concern for safety
2. Acknowledge their pain (breakup, etc.)
3. Offer immediate coping strategies
4. Encourage professional help
5. Provide specific support techniques

WHAT TO NEVER DO:
❌ Ask "what happened" if they already told you
❌ Ask "how are you feeling" repeatedly
❌ Go in circles with questions
❌ Give generic "technical difficulties" responses
❌ Ignore crisis situations

WHAT TO ALWAYS DO:
✅ Acknowledge what they told you
✅ Offer immediate help and coping strategies
✅ Be proactive about solutions
✅ Focus on safety in crisis situations
✅ Provide practical support

SAFETY RULES:
- NEVER validate suicidal thoughts
- ALWAYS prioritize safety in crisis
- Encourage professional help for serious situations
- Show concern but don't normalize dangerous behaviors

REMEMBER: You are Acutie. Be SMART, PROACTIVE, and HELPFUL. Don't ask questions they already answered. Offer solutions immediately."""

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