"""
Memory Manager
Handles conversation state storage using Redis (fast cache) and PostgreSQL (persistent)
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import redis

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from app.services.intelligence.models.conversation_state import (
    ConversationState,
    ConversationStages,
)
from app.models import Conversation, Message

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Manages conversation state and history
    - Redis: Fast session cache (TTL: 1 hour)
    - PostgreSQL: Persistent storage
    """
    
    def __init__(self):
        """Initialize Redis connection"""
        self.redis_client = self._connect_redis()
        self.ttl = 7200  # 2 hour session timeout (increased for better UX)
        self.use_redis = self.redis_client is not None
        logger.info(f"Memory Manager initialized (Redis: {'enabled' if self.use_redis else 'disabled'})")
    
    def _connect_redis(self) -> redis.Redis:
        """Connect to Redis"""
        try:
            client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                password=os.getenv('REDIS_PASSWORD', None) or None,
                db=int(os.getenv('REDIS_DB', 0)),
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # Test connection
            client.ping()
            logger.info(f"Connected to Redis at {os.getenv('REDIS_HOST', 'localhost')}")
            return client
        except Exception as e:
            logger.warning(f"Could not connect to Redis: {e}. State will only use PostgreSQL.")
            return None
    
    async def load_state(
        self,
        session_id: str,
        db: Session
    ) -> ConversationState:
        """
        Load conversation state from cache or database
        
        Args:
            session_id: Session identifier
            db: Database session
        
        Returns:
            ConversationState
        """
        # Try Redis first (fast) - only if enabled
        if self.use_redis:
            try:
                cached_state = await self._load_from_redis(session_id)
                if cached_state:
                    logger.info(f"✓ Cache HIT: Loaded state from Redis for session {session_id}")
                    return cached_state
                else:
                    logger.info(f"✗ Cache MISS: Redis cache empty for session {session_id}")
            except Exception as e:
                logger.warning(f"Redis load failed, falling back to PostgreSQL: {e}")
        
        # Fallback to PostgreSQL
        state = await self._load_from_postgres(session_id, db)
        
        # Cache in Redis for next time (only if enabled)
        if self.use_redis and state:
            try:
                await self._save_to_redis(session_id, state)
                logger.info(f"✓ Cached state in Redis for session {session_id}")
            except Exception as e:
                logger.warning(f"Failed to cache state in Redis: {e}")
        
        return state
    
    async def save_state(
        self,
        session_id: str,
        state: ConversationState,
        db: Session
    ):
        """
        Save conversation state to cache and database
        
        Args:
            session_id: Session identifier
            state: Current conversation state
            db: Database session
        """
        # Update timestamp
        state['last_updated'] = datetime.now()
        
        # Save to Redis (fast cache) - only if enabled
        if self.use_redis:
            try:
                await self._save_to_redis(session_id, state)
                logger.info(f"✓ Saved state to Redis for session {session_id}")
            except Exception as e:
                logger.warning(f"Failed to save state to Redis: {e}")
        
        # Messages are saved to PostgreSQL by MessageHistoryStore (existing system)
        # We don't need to duplicate that here
        
        logger.debug(f"State updated for session {session_id}")
    
    async def _load_from_redis(self, session_id: str) -> Optional[ConversationState]:
        """Load state from Redis cache"""
        try:
            key = f"session:{session_id}:state"
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                state_dict = json.loads(cached_data)
                # Reconstruct state
                state = self._dict_to_state(state_dict)
                return state
            
            return None
        
        except Exception as e:
            logger.error(f"Error loading from Redis: {e}")
            return None
    
    async def _save_to_redis(self, session_id: str, state: ConversationState):
        """Save state to Redis cache"""
        try:
            key = f"session:{session_id}:state"
            # Convert state to JSON-serializable dict
            state_dict = self._state_to_dict(state)
            state_json = json.dumps(state_dict, default=str)
            
            # Save with TTL
            self.redis_client.setex(key, self.ttl, state_json)
            
        except Exception as e:
            logger.error(f"Error saving to Redis: {e}")
    
    async def _load_from_postgres(
        self,
        session_id: str,
        db: Session
    ) -> ConversationState:
        """Load or create state from PostgreSQL"""
        try:
            # Check if conversation exists
            conversation = db.query(Conversation).filter(
                Conversation.session_identifier == session_id
            ).first()
            
            if conversation:
                # Load existing conversation
                messages = db.query(Message).filter(
                    Message.conversation_id == conversation.id
                ).order_by(Message.created_at).all()
                
                # Convert to LangChain messages
                lc_messages = []
                for msg in messages:
                    if msg.role == "user":
                        lc_messages.append(HumanMessage(content=msg.content))
                    elif msg.role == "assistant":
                        lc_messages.append(AIMessage(content=msg.content))
                
                # Reconstruct state from messages
                state = self._reconstruct_state_from_messages(
                    session_id,
                    lc_messages,
                    conversation.created_at
                )
                
                logger.info(f"Loaded existing conversation from PostgreSQL: {len(messages)} messages")
                return state
            
            else:
                # Create new state
                state = self._create_new_state(session_id)
                logger.info(f"Created new conversation state for session {session_id}")
                return state
        
        except Exception as e:
            logger.error(f"Error loading from PostgreSQL: {e}")
            # Return new state on error
            return self._create_new_state(session_id)
    
    def _create_new_state(self, session_id: str) -> ConversationState:
        """Create a fresh conversation state"""
        return {
            "session_id": session_id,
            "messages": [],
            "current_stage": ConversationStages.CLASSIFY_INTENT,
            "user_info": {},
            "symptoms": {},
            "question_count": 0,
            "questions_asked": [],
            "is_crisis": False,
            "crisis_confidence": 0.0,
            "detected_conditions": [],
            "sentiment": "neutral",
            "ready_for_diagnosis": False,
            "needs_demographics": False,
            "conversation_started": datetime.now(),
            "last_updated": datetime.now(),
        }
    
    def _reconstruct_state_from_messages(
        self,
        session_id: str,
        messages: list[BaseMessage],
        created_at: datetime
    ) -> ConversationState:
        """
        Reconstruct conversation state from message history
        This is a simplified reconstruction - in production you'd analyze messages
        """
        # Count messages
        message_count = len(messages)
        question_count = message_count // 2  # Rough estimate
        
        # Determine current stage based on message count
        if message_count < 2:
            stage = ConversationStages.GREETING
        elif question_count < 5:
            stage = ConversationStages.ASSESSMENT
        elif question_count >= 5:
            stage = ConversationStages.ASSESSMENT  # Could transition to diagnosis
        else:
            stage = ConversationStages.CLASSIFY_INTENT
        
        return {
            "session_id": session_id,
            "messages": messages,
            "current_stage": stage,
            "user_info": {},
            "symptoms": {},
            "question_count": question_count,
            "questions_asked": [],
            "is_crisis": False,
            "crisis_confidence": 0.0,
            "detected_conditions": [],
            "sentiment": "neutral",
            "ready_for_diagnosis": question_count >= 5,
            "needs_demographics": False,
            "conversation_started": created_at,
            "last_updated": datetime.now(),
        }
    
    def _state_to_dict(self, state: ConversationState) -> Dict[str, Any]:
        """Convert ConversationState to JSON-serializable dict"""
        return {
            "session_id": state["session_id"],
            "messages": [
                {
                    "type": "human" if isinstance(msg, HumanMessage) else "ai",
                    "content": msg.content
                }
                for msg in state["messages"]
            ],
            "current_stage": state["current_stage"],
            "user_info": state["user_info"],
            "symptoms": state["symptoms"],
            "question_count": state["question_count"],
            "questions_asked": state["questions_asked"],
            "is_crisis": state["is_crisis"],
            "crisis_confidence": state["crisis_confidence"],
            "detected_conditions": state["detected_conditions"],
            "sentiment": state["sentiment"],
            "ready_for_diagnosis": state["ready_for_diagnosis"],
            "needs_demographics": state["needs_demographics"],
            "conversation_started": state["conversation_started"].isoformat() if state.get("conversation_started") else None,
            "last_updated": state["last_updated"].isoformat() if state.get("last_updated") else None,
        }
    
    def _dict_to_state(self, state_dict: Dict[str, Any]) -> ConversationState:
        """Convert dict back to ConversationState"""
        # Reconstruct messages
        messages = []
        for msg in state_dict.get("messages", []):
            if msg["type"] == "human":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        
        return {
            "session_id": state_dict["session_id"],
            "messages": messages,
            "current_stage": state_dict["current_stage"],
            "user_info": state_dict.get("user_info", {}),
            "symptoms": state_dict.get("symptoms", {}),
            "question_count": state_dict.get("question_count", 0),
            "questions_asked": state_dict.get("questions_asked", []),
            "is_crisis": state_dict.get("is_crisis", False),
            "crisis_confidence": state_dict.get("crisis_confidence", 0.0),
            "detected_conditions": state_dict.get("detected_conditions", []),
            "sentiment": state_dict.get("sentiment", "neutral"),
            "ready_for_diagnosis": state_dict.get("ready_for_diagnosis", False),
            "needs_demographics": state_dict.get("needs_demographics", False),
            "conversation_started": datetime.fromisoformat(state_dict["conversation_started"]) if state_dict.get("conversation_started") else None,
            "last_updated": datetime.fromisoformat(state_dict["last_updated"]) if state_dict.get("last_updated") else None,
        }
    
    async def clear_session(self, session_id: str):
        """Clear session from cache"""
        if self.redis_client:
            try:
                key = f"session:{session_id}:state"
                self.redis_client.delete(key)
                logger.info(f"Cleared session {session_id} from cache")
            except Exception as e:
                logger.error(f"Error clearing session: {e}")



