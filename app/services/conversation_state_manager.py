"""
Conversation State Manager
Manages conversation state in Redis for fast access and persistence
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from app.services.redis_client import redis_client

logger = logging.getLogger(__name__)


class ConversationState:
    """Data structure for conversation state"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.phase = "initial"  # initial, gathering, assessing, complete
        self.questions_asked = 0
        self.condition_hypothesis = []  # ["anxiety", "depression"]
        self.answers_collected = {}  # {"duration": "2 weeks", "intensity": 7, ...}
        self.dimensions_answered = set()  # {"duration", "frequency", "intensity"}
        self.demographics = {}  # {"age": 25, "name": "Alex", "gender": "female"}
        self.sentiment = None  # {"valence": -0.8, "arousal": 0.6}
        self.risk_level = "low"  # low, moderate, high, crisis
        self.last_update = datetime.utcnow().isoformat()
        self.off_topic_count = 0
        self.empathy_responses_count = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        return {
            "session_id": self.session_id,
            "phase": self.phase,
            "questions_asked": self.questions_asked,
            "condition_hypothesis": self.condition_hypothesis,
            "answers_collected": self.answers_collected,
            "dimensions_answered": list(self.dimensions_answered),
            "demographics": self.demographics,
            "sentiment": self.sentiment,
            "risk_level": self.risk_level,
            "last_update": self.last_update,
            "off_topic_count": self.off_topic_count,
            "empathy_responses_count": self.empathy_responses_count
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ConversationState':
        """Create from dictionary"""
        state = ConversationState(data.get("session_id", ""))
        state.phase = data.get("phase", "initial")
        state.questions_asked = data.get("questions_asked", 0)
        state.condition_hypothesis = data.get("condition_hypothesis", [])
        state.answers_collected = data.get("answers_collected", {})
        state.dimensions_answered = set(data.get("dimensions_answered", []))
        state.demographics = data.get("demographics", {})
        state.sentiment = data.get("sentiment")
        state.risk_level = data.get("risk_level", "low")
        state.last_update = data.get("last_update", datetime.utcnow().isoformat())
        state.off_topic_count = data.get("off_topic_count", 0)
        state.empathy_responses_count = data.get("empathy_responses_count", 0)
        return state


class ConversationStateManager:
    """
    Manages conversation state in Redis
    Provides fast access to current conversation context
    """
    
    STATE_TTL = 86400  # 24 hours
    
    def __init__(self):
        self.redis = redis_client
    
    def get_state(self, session_id: str) -> ConversationState:
        """
        Get conversation state from Redis
        Creates new state if doesn't exist
        """
        try:
            state_key = f"session:{session_id}"
            state_data = self.redis.get(state_key, deserialize=True)
            
            if state_data:
                logger.debug(f"Retrieved state for session {session_id}")
                return ConversationState.from_dict(state_data)
            else:
                logger.debug(f"Creating new state for session {session_id}")
                return ConversationState(session_id)
                
        except Exception as e:
            logger.error(f"Error getting state for session {session_id}: {e}")
            # Return empty state on error
            return ConversationState(session_id)
    
    def save_state(self, state: ConversationState) -> bool:
        """
        Save conversation state to Redis with TTL
        """
        try:
            state_key = f"session:{state.session_id}"
            state.last_update = datetime.utcnow().isoformat()
            
            success = self.redis.set(
                state_key,
                state.to_dict(),
                ex=self.STATE_TTL
            )
            
            if success:
                logger.debug(f"Saved state for session {state.session_id}")
            else:
                logger.error(f"Failed to save state for session {state.session_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving state for session {state.session_id}: {e}")
            return False
    
    def update_state(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update specific fields in state
        """
        try:
            state = self.get_state(session_id)
            
            # Update fields
            for key, value in updates.items():
                if hasattr(state, key):
                    setattr(state, key, value)
            
            return self.save_state(state)
            
        except Exception as e:
            logger.error(f"Error updating state for session {session_id}: {e}")
            return False
    
    def add_answer(self, session_id: str, dimension: str, answer: Any) -> bool:
        """
        Add an answer to a diagnostic dimension
        """
        try:
            state = self.get_state(session_id)
            state.answers_collected[dimension] = answer
            state.dimensions_answered.add(dimension)
            state.questions_asked += 1
            
            # Also track in Redis set for quick queries
            self.redis.sadd(f"dimensions:{session_id}", dimension)
            self.redis.expire(f"dimensions:{session_id}", self.STATE_TTL)
            
            return self.save_state(state)
            
        except Exception as e:
            logger.error(f"Error adding answer for session {session_id}: {e}")
            return False
    
    def get_dimensions_answered(self, session_id: str) -> set:
        """
        Get set of answered dimensions (fast Redis set operation)
        """
        try:
            return self.redis.smembers(f"dimensions:{session_id}")
        except Exception as e:
            logger.error(f"Error getting dimensions for session {session_id}: {e}")
            return set()
    
    def get_dimensions_count(self, session_id: str) -> int:
        """
        Get count of answered dimensions
        """
        try:
            return self.redis.scard(f"dimensions:{session_id}")
        except Exception as e:
            logger.error(f"Error getting dimension count for session {session_id}: {e}")
            return 0
    
    def set_phase(self, session_id: str, phase: str) -> bool:
        """
        Update conversation phase
        """
        return self.update_state(session_id, {"phase": phase})
    
    def set_condition_hypothesis(self, session_id: str, conditions: List[str]) -> bool:
        """
        Set hypothesized conditions
        """
        return self.update_state(session_id, {"condition_hypothesis": conditions})
    
    def set_risk_level(self, session_id: str, risk_level: str) -> bool:
        """
        Set risk level (low, moderate, high, crisis)
        """
        return self.update_state(session_id, {"risk_level": risk_level})
    
    def set_sentiment(self, session_id: str, sentiment: Dict[str, float]) -> bool:
        """
        Set sentiment analysis result
        """
        return self.update_state(session_id, {"sentiment": sentiment})
    
    def set_demographics(self, session_id: str, demographics: Dict[str, Any]) -> bool:
        """
        Set or update demographics
        """
        state = self.get_state(session_id)
        state.demographics.update(demographics)
        return self.save_state(state)
    
    def increment_off_topic_count(self, session_id: str) -> int:
        """
        Increment off-topic message counter
        Returns new count
        """
        try:
            state = self.get_state(session_id)
            state.off_topic_count += 1
            self.save_state(state)
            return state.off_topic_count
        except Exception as e:
            logger.error(f"Error incrementing off-topic count for session {session_id}: {e}")
            return 0
    
    def delete_state(self, session_id: str) -> bool:
        """
        Delete conversation state (cleanup)
        """
        try:
            state_key = f"session:{session_id}"
            dimensions_key = f"dimensions:{session_id}"
            
            self.redis.delete(state_key, dimensions_key)
            logger.info(f"Deleted state for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting state for session {session_id}: {e}")
            return False
    
    def state_exists(self, session_id: str) -> bool:
        """
        Check if state exists in Redis
        """
        try:
            state_key = f"session:{session_id}"
            return self.redis.exists(state_key) > 0
        except Exception as e:
            logger.error(f"Error checking state existence for session {session_id}: {e}")
            return False
    
    def get_questions_asked(self, session_id: str) -> int:
        """
        Get number of questions asked
        """
        try:
            state = self.get_state(session_id)
            return state.questions_asked
        except Exception as e:
            logger.error(f"Error getting question count for session {session_id}: {e}")
            return 0
    
    def should_collect_demographics(self, session_id: str) -> bool:
        """
        Determine if we should collect demographics
        Based on sentiment analysis (negative sentiment = yes)
        """
        try:
            state = self.get_state(session_id)
            
            # Already collected
            if state.demographics:
                return False
            
            # Check sentiment
            if state.sentiment:
                valence = state.sentiment.get("valence", 0)
                # Negative valence means negative sentiment
                return valence < -0.3
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking demographics collection for session {session_id}: {e}")
            return False
    
    def get_state_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get a summary of state for logging/debugging
        """
        try:
            state = self.get_state(session_id)
            return {
                "phase": state.phase,
                "questions_asked": state.questions_asked,
                "dimensions_answered": len(state.dimensions_answered),
                "condition_hypothesis": state.condition_hypothesis,
                "risk_level": state.risk_level,
                "has_demographics": bool(state.demographics)
            }
        except Exception as e:
            logger.error(f"Error getting state summary for session {session_id}: {e}")
            return {}


# Global instance
conversation_state_manager = ConversationStateManager()

