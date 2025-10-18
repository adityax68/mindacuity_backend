"""
Custom Chat Message History implementation for session-based conversations.
This integrates LangChain's ChatMessageHistory with our existing database schema.
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.messages.utils import get_buffer_string

from app.models import Message

logger = logging.getLogger(__name__)


class DatabaseChatMessageHistory(BaseChatMessageHistory):
    """
    Custom chat message history that stores messages in our existing database.
    Each instance is tied to a specific session_identifier.
    """
    
    def __init__(self, session_identifier: str, db: Session):
        """
        Initialize chat history for a specific session.
        
        Args:
            session_identifier: The session ID to track messages for
            db: Database session
        """
        self.session_identifier = session_identifier
        self.db = db
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the database for this session."""
        try:
            # Convert LangChain message to our database format
            role = "user" if isinstance(message, HumanMessage) else "assistant"
            content = message.content
            
            # Handle GPT-5 Responses API format (list of response items)
            if isinstance(content, list):
                # Extract text content from GPT-5 response items
                text_content = ""
                for item in content:
                    if item.get('type') == 'text':
                        text_content += item.get('text', '')
                
                # If no text content found, use fallback
                if not text_content:
                    text_content = "I understand you're going through a difficult time. Can you tell me more about what specific symptoms or concerns you're experiencing right now?"
                
                content = text_content
                logger.info(f"🔧 GPT-5 CONTENT CONVERTED - Session: {self.session_identifier}, Length: {len(content)}")
            
            # Create and save message (no encryption)
            db_message = Message(
                session_identifier=self.session_identifier,
                role=role,
                content=content,
                encrypted_content=None  # No encryption for session-based chats
            )
            
            self.db.add(db_message)
            self.db.commit()
            self.db.refresh(db_message)
            
            logger.debug(f"Added {role} message to session {self.session_identifier}")
            
        except Exception as e:
            logger.error(f"Failed to add message to database: {e}")
            self.db.rollback()
            raise
    
    def clear(self) -> None:
        """Clear all messages for this session."""
        try:
            self.db.query(Message).filter(
                Message.session_identifier == self.session_identifier
            ).delete()
            self.db.commit()
            logger.info(f"Cleared all messages for session {self.session_identifier}")
        except Exception as e:
            logger.error(f"Failed to clear messages: {e}")
            self.db.rollback()
            raise
    
    @property
    def messages(self) -> List[BaseMessage]:
        """Get all messages for this session as LangChain BaseMessage objects."""
        try:
            # Query messages from database
            db_messages = self.db.query(Message).filter(
                Message.session_identifier == self.session_identifier
            ).order_by(Message.created_at.asc()).all()
            
            # Convert to LangChain messages (no decryption needed)
            langchain_messages = []
            for db_message in db_messages:
                # Use content directly (no encryption for session-based chats)
                content = db_message.content
                
                # Convert to appropriate LangChain message type
                if db_message.role == "user":
                    langchain_messages.append(HumanMessage(content=content))
                elif db_message.role == "assistant":
                    langchain_messages.append(AIMessage(content=content))
                elif db_message.role == "system":
                    langchain_messages.append(SystemMessage(content=content))
            
            return langchain_messages
            
        except Exception as e:
            logger.error(f"Failed to retrieve messages: {e}")
            return []
    
    def get_messages_as_string(self, human_prefix: str = "Human", ai_prefix: str = "AI") -> str:
        """Get messages as a formatted string (useful for debugging)."""
        return get_buffer_string(self.messages, human_prefix=human_prefix, ai_prefix=ai_prefix)
    
    def get_message_count(self) -> int:
        """Get the number of messages in this session."""
        try:
            return self.db.query(Message).filter(
                Message.session_identifier == self.session_identifier
            ).count()
        except Exception as e:
            logger.error(f"Failed to get message count: {e}")
            return 0
    
    def get_latest_messages(self, limit: int = 10) -> List[BaseMessage]:
        """Get the latest N messages for this session."""
        try:
            db_messages = self.db.query(Message).filter(
                Message.session_identifier == self.session_identifier
            ).order_by(Message.created_at.desc()).limit(limit).all()
            
            # Reverse to get chronological order
            db_messages.reverse()
            
            # Convert to LangChain messages (no decryption needed)
            langchain_messages = []
            for db_message in db_messages:
                # Use content directly (no encryption for session-based chats)
                content = db_message.content
                
                if db_message.role == "user":
                    langchain_messages.append(HumanMessage(content=content))
                elif db_message.role == "assistant":
                    langchain_messages.append(AIMessage(content=content))
                elif db_message.role == "system":
                    langchain_messages.append(SystemMessage(content=content))
            
            return langchain_messages
            
        except Exception as e:
            logger.error(f"Failed to get latest messages: {e}")
            return []

