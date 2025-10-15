"""
Conversation State Models for LangGraph State Machine
Defines the state that flows through the conversation orchestrator
"""

from typing import Dict, Any, List, Optional, TypedDict
from langchain_core.messages import BaseMessage
from datetime import datetime


class ConversationState(TypedDict):
    """
    The state that flows through the entire conversation.
    This is updated at each node in the state machine.
    """
    # Session identification
    session_id: str
    
    # Message history (LangChain format)
    messages: List[BaseMessage]
    
    # Current conversation stage
    current_stage: str  # greeting | assessment | diagnosis | crisis | completed
    
    # User demographic information
    user_info: Dict[str, Any]  # name, age, gender
    
    # Collected symptoms and responses
    symptoms: Dict[str, Any]  # duration, frequency, intensity, triggers, impact, etc.
    
    # Question tracking
    question_count: int
    questions_asked: List[str]  # Topics already covered
    
    # Crisis detection
    is_crisis: bool
    crisis_confidence: float
    
    # Assessment metadata
    detected_conditions: List[str]  # anxiety, depression, stress, etc.
    sentiment: str  # positive, neutral, negative
    
    # Control flags
    ready_for_diagnosis: bool
    needs_demographics: bool
    
    # Timestamps
    conversation_started: Optional[datetime]
    last_updated: Optional[datetime]


class AssessmentData(TypedDict):
    """Structured assessment data extracted from conversation"""
    duration: Optional[str]  # "2 weeks", "3 months"
    frequency: Optional[str]  # "daily", "weekly"
    intensity: Optional[int]  # 1-10 scale
    triggers: Optional[List[str]]  # List of triggers
    impact_areas: Optional[List[str]]  # sleep, work, relationships, etc.
    physical_symptoms: Optional[List[str]]  # fatigue, headaches, etc.
    coping_mechanisms: Optional[List[str]]  # What they've tried
    support_system: Optional[str]  # Yes/No/Limited


class DiagnosisResult(TypedDict):
    """Structured diagnosis output"""
    primary_conditions: List[str]
    severity_levels: Dict[str, str]  # condition -> mild/moderate/severe
    key_findings: Dict[str, Any]
    recommendations: str
    raw_assessment: str  # Full formatted text


# Stage definitions
class ConversationStages:
    CLASSIFY_INTENT = "classify_intent"
    CRISIS_CHECK = "crisis_check"
    GREETING = "greeting"
    COLLECT_DEMOGRAPHICS = "collect_demographics"
    ASSESSMENT = "assessment"
    DIAGNOSIS = "diagnosis"
    COMPLETED = "completed"
    ERROR = "error"


# Intent types for routing
class IntentTypes:
    CRISIS = "crisis"
    FIRST_MESSAGE = "first_message"
    DEMOGRAPHIC_RESPONSE = "demographic_response"
    ASSESSMENT_RESPONSE = "assessment_response"
    READY_FOR_DIAGNOSIS = "ready_for_diagnosis"
    OFF_TOPIC = "off_topic"
    UNCLEAR = "unclear"


