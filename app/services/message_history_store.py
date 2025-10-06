"""
Message History Store for LangChain integration.
This manages multiple DatabaseChatMessageHistory instances for different sessions.
"""

import logging
from typing import Dict, Optional
from sqlalchemy.orm import Session
from langchain_core.chat_history import BaseChatMessageHistory

from app.services.database_chat_history import DatabaseChatMessageHistory

logger = logging.getLogger(__name__)


class MessageHistoryStore:
    """
    Store for managing multiple chat message histories.
    Each session gets its own DatabaseChatMessageHistory instance.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the message history store.
        
        Args:
            db: Database session
        """
        self.db = db
        self._histories: Dict[str, DatabaseChatMessageHistory] = {}
    
    def get_chat_history(self, session_identifier: str) -> BaseChatMessageHistory:
        """
        Get or create a chat history for the given session.
        
        Args:
            session_identifier: The session ID to get history for
            
        Returns:
            DatabaseChatMessageHistory instance for the session
        """
        if session_identifier not in self._histories:
            self._histories[session_identifier] = DatabaseChatMessageHistory(
                session_identifier=session_identifier,
                db=self.db
            )
            logger.debug(f"Created new chat history for session {session_identifier}")
        
        return self._histories[session_identifier]
    
    def clear_session_history(self, session_identifier: str) -> None:
        """
        Clear the chat history for a specific session.
        
        Args:
            session_identifier: The session ID to clear
        """
        if session_identifier in self._histories:
            self._histories[session_identifier].clear()
            del self._histories[session_identifier]
            logger.info(f"Cleared and removed history for session {session_identifier}")
    
    def get_session_info(self, session_identifier: str) -> Dict:
        """
        Get information about a session's chat history.
        
        Args:
            session_identifier: The session ID to get info for
            
        Returns:
            Dictionary with session information
        """
        history = self.get_chat_history(session_identifier)
        return {
            "session_identifier": session_identifier,
            "message_count": history.get_message_count(),
            "has_messages": history.get_message_count() > 0
        }
    
    def cleanup_old_histories(self, max_age_hours: int = 24) -> None:
        """
        Clean up old chat histories from memory (not database).
        This is useful for memory management.
        
        Args:
            max_age_hours: Maximum age of histories to keep in memory
        """
        # This is a simple implementation - in production you might want
        # to track creation times and clean up based on actual age
        logger.info(f"Cleaning up old chat histories (keeping last {max_age_hours} hours)")
        # For now, we'll just log - you can implement actual cleanup logic here

