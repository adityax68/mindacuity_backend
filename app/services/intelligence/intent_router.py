"""
Intent Router using Semantic Router
Ultra-fast intent classification using embeddings
"""

import logging
from typing import Optional
from semantic_router import Route, SemanticRouter, RouterConfig
from semantic_router.encoders import OpenAIEncoder

from app.services.intelligence.models.conversation_state import IntentTypes

logger = logging.getLogger(__name__)


class IntentRouter:
    """
    Fast intent classification using semantic similarity
    Uses OpenAI embeddings for ~150ms classification
    """
    
    def __init__(self):
        """Initialize semantic router with predefined routes"""
        self.router = self._build_router()
        logger.info("Intent Router initialized with semantic routes")
    
    def _build_router(self) -> SemanticRouter:
        """Build the semantic router with intent routes"""
        
        # Define crisis route (highest priority)
        crisis_route = Route(
            name=IntentTypes.CRISIS,
            utterances=[
                "I want to kill myself",
                "I'm going to hurt myself",
                "I want to die",
                "Life is not worth living",
                "I have a plan to end it all",
                "I can't take this anymore and want to end it",
                "I'm thinking about suicide",
                "I cut myself last night",
                "I want to hurt myself again",
                "Better off dead",
                "No reason to keep living",
                "Planning to overdose",
            ],
        )
        
        # First message / greeting route
        first_message_route = Route(
            name=IntentTypes.FIRST_MESSAGE,
            utterances=[
                "Hello",
                "Hi there",
                "I need help",
                "Can you help me?",
                "I'm feeling anxious",
                "I've been depressed",
                "I'm stressed about work",
                "Having trouble sleeping",
                "Feeling overwhelmed lately",
                "I need to talk to someone",
                "I'm not doing well",
                "Can we talk?",
            ],
        )
        
        # Demographic information responses
        demographic_route = Route(
            name=IntentTypes.DEMOGRAPHIC_RESPONSE,
            utterances=[
                "My name is John",
                "I'm 25 years old",
                "I'm male",
                "I'm female",
                "I prefer not to say",
                "You can call me Sarah",
                "I'm 30",
                "Twenty-five",
                "I'm a woman",
                "I'm a man",
            ],
        )
        
        # Assessment responses (answers to clinical questions)
        assessment_route = Route(
            name=IntentTypes.ASSESSMENT_RESPONSE,
            utterances=[
                "About 2 weeks",
                "For 3 months now",
                "Every day",
                "A few times a week",
                "7 out of 10",
                "Pretty intense",
                "Work stress mainly",
                "When I'm alone",
                "I can't sleep well",
                "It's affecting my work",
                "I've been tired all the time",
                "I get headaches",
                "I haven't tried anything yet",
                "I talk to my friends sometimes",
                "I don't have anyone to talk to",
                "Just started a few days ago",
                "It's been going on for months",
                "Almost never",
                "Constantly",
            ],
        )
        
        # Off-topic route
        off_topic_route = Route(
            name=IntentTypes.OFF_TOPIC,
            utterances=[
                "What's the weather like?",
                "Tell me a joke",
                "Who won the game yesterday?",
                "What should I eat for dinner?",
                "How do I cook pasta?",
                "What's 2+2?",
                "Can you help me with my homework?",
            ],
        )
        
        # Create encoder using OpenAI embeddings
        encoder = OpenAIEncoder(
            name="text-embedding-3-small"
        )
        
        routes = [
            crisis_route,
            first_message_route,
            demographic_route,
            assessment_route,
            off_topic_route,
        ]
        
        # Create and return the semantic router
        return SemanticRouter(encoder=encoder, routes=routes)
    
    def classify(self, message: str) -> str:
        """
        Classify user message intent
        
        Args:
            message: User's message text
        
        Returns:
            Intent type (from IntentTypes)
        """
        try:
            result = self.router(message)
            
            if result and result.name:
                intent = result.name
                logger.info(f"Classified intent: {intent} (score: {result.score:.3f})")
                return intent
            else:
                # No clear match - return unclear
                logger.info("No clear intent match - returning UNCLEAR")
                return IntentTypes.UNCLEAR
        
        except Exception as e:
            logger.error(f"Error in intent classification: {e}")
            # Default to unclear on error
            return IntentTypes.UNCLEAR
    
    def is_crisis_intent(self, message: str) -> bool:
        """
        Quick check if message has crisis intent
        
        Args:
            message: User's message text
        
        Returns:
            True if crisis intent detected
        """
        intent = self.classify(message)
        return intent == IntentTypes.CRISIS
    
    def is_first_message(self, message: str) -> bool:
        """
        Check if this looks like a first message
        
        Args:
            message: User's message text
        
        Returns:
            True if first message intent detected
        """
        intent = self.classify(message)
        return intent == IntentTypes.FIRST_MESSAGE
    
    def is_assessment_response(self, message: str) -> bool:
        """
        Check if message is responding to assessment question
        
        Args:
            message: User's message text
        
        Returns:
            True if assessment response intent detected
        """
        intent = self.classify(message)
        return intent == IntentTypes.ASSESSMENT_RESPONSE
    
    def get_intent_confidence(self, message: str) -> tuple[str, float]:
        """
        Get intent classification with confidence score
        
        Args:
            message: User's message text
        
        Returns:
            Tuple of (intent, confidence_score)
        """
        try:
            result = self.router(message)
            
            if result and result.name:
                return (result.name, result.score if hasattr(result, 'score') else 1.0)
            else:
                return (IntentTypes.UNCLEAR, 0.0)
        
        except Exception as e:
            logger.error(f"Error getting intent confidence: {e}")
            return (IntentTypes.UNCLEAR, 0.0)

