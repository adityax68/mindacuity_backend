"""
Optimized Message History Store with Redis Caching
Two-tier caching: Redis (hot) + PostgreSQL (cold storage)
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from app.models import Message
from app.services.redis_client import redis_client
from app.database import SessionLocal  # NEW: Import session factory

logger = logging.getLogger(__name__)

# Shared thread pool for DB writes (non-blocking)
_db_write_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="db_write")


class OptimizedMessageHistoryStore:
    """
    Two-tier message storage:
    1. Redis: Hot cache (last 20 messages) - sub-millisecond access
    2. PostgreSQL: Cold storage (all messages) - persistent
    
    Write strategy: Dual-write (Redis immediate, DB async)
    Read strategy: Redis-first, fallback to DB
    """
    
    CONTEXT_WINDOW_SIZE = 20  # Keep last 20 messages in Redis
    CONTEXT_TTL = 3600  # 1 hour
    
    def __init__(self, db: Session):
        self.db = db
        self.redis = redis_client
    
    def get_messages(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent messages with Redis-first strategy
        
        Args:
            session_id: Session identifier
            limit: Max number of messages to retrieve
            
        Returns:
            List of messages in format [{"role": "user", "content": "..."}]
        """
        try:
            cache_key = f"context:{session_id}"
            
            # Try Redis first (sub-millisecond)
            cached_messages = self.redis.lrange(cache_key, 0, limit - 1, deserialize=True)
            
            if cached_messages:
                logger.debug(f"Cache HIT for session {session_id} - Redis")
                # Messages are stored newest first, reverse for chronological order
                return list(reversed(cached_messages))
            
            # Cache miss - fetch from database
            logger.debug(f"Cache MISS for session {session_id} - querying DB")
            db_messages = self.db.query(Message).filter(
                Message.session_identifier == session_id
            ).order_by(Message.created_at.desc()).limit(limit).all()
            
            if not db_messages:
                return []
            
            # Populate Redis cache for next time
            messages_list = []
            for msg in db_messages:
                message_dict = {
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None
                }
                messages_list.append(message_dict)
                self.redis.rpush(cache_key, message_dict)
            
            # Set expiry
            self.redis.expire(cache_key, self.CONTEXT_TTL)
            
            # Return in chronological order
            return list(reversed(messages_list))
            
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {e}")
            return []
    
    def get_langchain_messages(self, session_id: str, limit: int = 10) -> List[BaseMessage]:
        """
        Get messages as LangChain BaseMessage objects
        
        Returns:
            List of HumanMessage and AIMessage objects
        """
        try:
            messages = self.get_messages(session_id, limit)
            
            langchain_messages = []
            for msg in messages:
                if msg["role"] == "user":
                    langchain_messages.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    langchain_messages.append(AIMessage(content=msg["content"]))
            
            return langchain_messages
            
        except Exception as e:
            logger.error(f"Error converting messages to LangChain format: {e}")
            return []
    
    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """
        Add message with dual-write strategy
        
        1. Write to Redis immediately (for next request)
        2. Write to PostgreSQL asynchronously (fire-and-forget)
        
        Args:
            session_id: Session identifier
            role: "user" or "assistant"
            content: Message content
            
        Returns:
            True if Redis write successful
        """
        try:
            cache_key = f"context:{session_id}"
            
            # Prepare message
            message_dict = {
                "role": role,
                "content": content,
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Write to Redis immediately (left push = newest first)
            self.redis.lpush(cache_key, message_dict)
            
            # Trim to keep only recent messages
            self.redis.ltrim(cache_key, 0, self.CONTEXT_WINDOW_SIZE - 1)
            
            # Set/refresh expiry
            self.redis.expire(cache_key, self.CONTEXT_TTL)
            
            # Write to PostgreSQL in thread pool (truly non-blocking)
            # Note: We pass data, NOT the session (sessions aren't thread-safe)
            loop = asyncio.get_event_loop()
            loop.run_in_executor(
                _db_write_executor,
                self._save_to_db_sync,
                session_id, role, content
            )
            
            logger.debug(f"Added {role} message to session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding message for session {session_id}: {e}")
            return False
    
    @staticmethod
    def _save_to_db_sync(session_id: str, role: str, content: str):
        """
        Synchronous database write (runs in thread pool, doesn't block event loop)
        Creates its OWN session (thread-safe!)
        """
        db = None
        try:
            # Create a NEW session for this thread (SQLAlchemy sessions aren't thread-safe!)
            db = SessionLocal()
            
            message = Message(
                session_identifier=session_id,
                role=role,
                content=content,
                created_at=datetime.utcnow()
            )
            db.add(message)
            db.commit()
            logger.debug(f"[PERF] DB write completed for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to save message to DB for session {session_id}: {e}")
            if db:
                try:
                    db.rollback()
                except Exception as rollback_error:
                    logger.error(f"Failed to rollback: {rollback_error}")
        finally:
            # Always close the session we created
            if db:
                try:
                    db.close()
                except Exception as close_error:
                    logger.error(f"Failed to close DB session: {close_error}")
    
    def add_user_message(self, session_id: str, content: str) -> bool:
        """Convenience method to add user message"""
        return self.add_message(session_id, "user", content)
    
    def add_assistant_message(self, session_id: str, content: str) -> bool:
        """Convenience method to add assistant message"""
        return self.add_message(session_id, "assistant", content)
    
    def get_message_count(self, session_id: str) -> int:
        """
        Get total message count (from Redis if available, else DB)
        """
        try:
            cache_key = f"context:{session_id}"
            
            # Try Redis first
            count = self.redis.llen(cache_key)
            if count > 0:
                return count
            
            # Fallback to DB
            return self.db.query(Message).filter(
                Message.session_identifier == session_id
            ).count()
            
        except Exception as e:
            logger.error(f"Error getting message count for session {session_id}: {e}")
            return 0
    
    def get_last_message(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent message
        """
        try:
            cache_key = f"context:{session_id}"
            
            # Get first item from list (newest)
            messages = self.redis.lrange(cache_key, 0, 0, deserialize=True)
            if messages:
                return messages[0]
            
            # Fallback to DB
            db_message = self.db.query(Message).filter(
                Message.session_identifier == session_id
            ).order_by(Message.created_at.desc()).first()
            
            if db_message:
                return {
                    "role": db_message.role,
                    "content": db_message.content,
                    "created_at": db_message.created_at.isoformat() if db_message.created_at else None
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting last message for session {session_id}: {e}")
            return None
    
    def get_last_assistant_message(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent ASSISTANT message (for checking what was last asked)
        """
        try:
            cache_key = f"context:{session_id}"
            
            # Get recent messages from Redis
            messages = self.redis.lrange(cache_key, 0, 10, deserialize=True)  # Check last 10
            logger.info(f"[DEBUG] get_last_assistant_message: Found {len(messages) if messages else 0} messages in Redis for session {session_id}")
            
            if messages:
                # Log all messages for debugging
                for i, msg in enumerate(messages):
                    logger.info(f"[DEBUG] Message {i}: role={msg.get('role')}, content_preview={msg.get('content', '')[:50]}...")
                
                # Find first assistant message
                for msg in messages:
                    if msg.get("role") == "assistant":
                        logger.info(f"[DEBUG] Found assistant message in Redis: '{msg.get('content', '')[:100]}...'")
                        return msg
            
            # Fallback to DB
            logger.info(f"[DEBUG] No assistant message in Redis, checking DB...")
            db_message = self.db.query(Message).filter(
                Message.session_identifier == session_id,
                Message.role == "assistant"
            ).order_by(Message.created_at.desc()).first()
            
            if db_message:
                logger.info(f"[DEBUG] Found assistant message in DB: '{db_message.content[:100]}...'")
                return {
                    "role": db_message.role,
                    "content": db_message.content,
                    "created_at": db_message.created_at.isoformat() if db_message.created_at else None
                }
            
            logger.info(f"[DEBUG] No assistant message found anywhere for session {session_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting last assistant message for session {session_id}: {e}")
            return None
    
    def clear_messages(self, session_id: str) -> bool:
        """
        Clear all messages for a session (Redis only, DB persists)
        """
        try:
            cache_key = f"context:{session_id}"
            self.redis.delete(cache_key)
            logger.info(f"Cleared message cache for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing messages for session {session_id}: {e}")
            return False
    
    def warm_cache(self, session_id: str, limit: int = 20):
        """
        Pre-populate Redis cache from database
        Useful when resuming a conversation
        """
        try:
            cache_key = f"context:{session_id}"
            
            # Check if cache exists
            if self.redis.exists(cache_key):
                logger.debug(f"Cache already warm for session {session_id}")
                return
            
            # Fetch from DB
            db_messages = self.db.query(Message).filter(
                Message.session_identifier == session_id
            ).order_by(Message.created_at.desc()).limit(limit).all()
            
            if not db_messages:
                return
            
            # Populate Redis (newest first)
            for msg in db_messages:
                message_dict = {
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None
                }
                self.redis.rpush(cache_key, message_dict)
            
            # Set expiry
            self.redis.expire(cache_key, self.CONTEXT_TTL)
            
            logger.info(f"Warmed cache for session {session_id} with {len(db_messages)} messages")
            
        except Exception as e:
            logger.error(f"Error warming cache for session {session_id}: {e}")
    
    def get_context_for_llm(self, session_id: str, max_messages: int = 6) -> List[Dict[str, str]]:
        """
        Get optimized context for LLM calls
        Returns last N exchanges (user + assistant pairs)
        
        Args:
            session_id: Session identifier
            max_messages: Maximum messages to include (default 6 = 3 exchanges)
            
        Returns:
            List of messages in format for LLM context
        """
        try:
            messages = self.get_messages(session_id, limit=max_messages)
            
            # Format for LLM
            context = []
            for msg in messages:
                context.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting context for LLM: {e}")
            return []


class OptimizedChatMessageHistory(BaseChatMessageHistory):
    """
    LangChain-compatible chat history with Redis optimization
    Drop-in replacement for DatabaseChatMessageHistory
    """
    
    def __init__(self, session_id: str, db: Session):
        self.session_id = session_id
        self.db = db
        self.store = OptimizedMessageHistoryStore(db)
    
    def add_message(self, message: BaseMessage) -> None:
        """Add a message to the store"""
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        self.store.add_message(self.session_id, role, message.content)
    
    def clear(self) -> None:
        """Clear message history"""
        self.store.clear_messages(self.session_id)
    
    @property
    def messages(self) -> List[BaseMessage]:
        """Get all messages as LangChain objects"""
        return self.store.get_langchain_messages(self.session_id)


# Factory function for LangChain integration
def get_optimized_message_history(session_id: str, db: Session) -> OptimizedChatMessageHistory:
    """
    Factory function to create optimized message history
    Compatible with LangChain's RunnableWithMessageHistory
    """
    return OptimizedChatMessageHistory(session_id, db)

