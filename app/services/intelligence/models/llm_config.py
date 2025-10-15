"""
LLM Configuration for Multi-Model System
Defines which models to use for different tasks
"""

import os
from typing import Dict, Any
from enum import Enum


class ModelProvider(Enum):
    """Available LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ModelName(Enum):
    """Specific models to use"""
    # OpenAI models
    GPT_5 = "gpt-5"
    GPT_4O = "gpt-4o"
    GPT_4O_MINI = "gpt-4o-mini"
    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"
    
    # Anthropic models  
    CLAUDE_SONNET_4_5 = "claude-sonnet-4-5-20250929"
    CLAUDE_HAIKU_3_5 = "claude-3-5-haiku-20241022"


class TaskType(Enum):
    """Different task types that require different models"""
    INTENT_CLASSIFICATION = "intent_classification"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    CRISIS_DETECTION = "crisis_detection"
    GREETING_EMPATHETIC = "greeting_empathetic"
    GREETING_NEUTRAL = "greeting_neutral"
    ASSESSMENT_QUESTION = "assessment_question"
    RESPONSE_EXTRACTION = "response_extraction"
    DIAGNOSIS_ANALYSIS = "diagnosis_analysis"
    DIAGNOSIS_FORMATTING = "diagnosis_formatting"


# Model routing configuration
MODEL_ROUTING: Dict[TaskType, Dict[str, Any]] = {
    TaskType.INTENT_CLASSIFICATION: {
        "model": ModelName.TEXT_EMBEDDING_3_SMALL,
        "provider": ModelProvider.OPENAI,
        "temperature": 0.0,  # Not used for embeddings
        "max_tokens": 0,  # Not used for embeddings
        "notes": "Fast semantic search for intent classification"
    },
    
    TaskType.SENTIMENT_ANALYSIS: {
        "model": ModelName.CLAUDE_HAIKU_3_5,
        "provider": ModelProvider.ANTHROPIC,
        "temperature": 0.3,
        "max_tokens": 50,
        "notes": "Fast sentiment detection with better emotional intelligence"
    },
    
    TaskType.CRISIS_DETECTION: {
        "primary_model": ModelName.GPT_5,
        "secondary_model": ModelName.CLAUDE_SONNET_4_5,
        "provider": [ModelProvider.OPENAI, ModelProvider.ANTHROPIC],
        "temperature": 0.3,
        "max_tokens": 800,
        "notes": "Ensemble detection with both models for accuracy"
    },
    
    TaskType.GREETING_EMPATHETIC: {
        "model": ModelName.CLAUDE_SONNET_4_5,
        "provider": ModelProvider.ANTHROPIC,
        "temperature": 0.7,
        "max_tokens": 400,
        "use_cache": True,
        "notes": "Claude excels at warm, empathetic greetings"
    },
    
    TaskType.GREETING_NEUTRAL: {
        "model": ModelName.GPT_4O_MINI,
        "provider": ModelProvider.OPENAI,
        "temperature": 0.7,
        "max_tokens": 300,
        "notes": "Fast greeting for neutral/positive sentiment"
    },
    
    TaskType.ASSESSMENT_QUESTION: {
        "model": ModelName.CLAUDE_SONNET_4_5,
        "provider": ModelProvider.ANTHROPIC,
        "temperature": 0.8,
        "max_tokens": 400,
        "use_cache": True,
        "notes": "Natural, conversational question generation"
    },
    
    TaskType.RESPONSE_EXTRACTION: {
        "model": ModelName.CLAUDE_HAIKU_3_5,
        "provider": ModelProvider.ANTHROPIC,
        "temperature": 0.3,
        "max_tokens": 300,
        "notes": "Fast structured data extraction with excellent JSON formatting"
    },
    
    TaskType.DIAGNOSIS_ANALYSIS: {
        "model": ModelName.GPT_5,
        "provider": ModelProvider.OPENAI,
        "temperature": 0.4,
        "max_tokens": 1000,
        "notes": "Superior reasoning for complex clinical analysis"
    },
    
    TaskType.DIAGNOSIS_FORMATTING: {
        "model": ModelName.CLAUDE_SONNET_4_5,
        "provider": ModelProvider.ANTHROPIC,
        "temperature": 0.6,
        "max_tokens": 1000,
        "use_cache": True,
        "notes": "Natural language formatting with empathy"
    },
}


# Model-specific settings
OPENAI_CONFIG = {
    "api_key": os.getenv("OPENAI_API_KEY"),
    "timeout": 30.0,
    "max_retries": 3,
}

ANTHROPIC_CONFIG = {
    "api_key": os.getenv("ANTHROPIC_API_KEY"),
    "timeout": 30.0,
    "max_retries": 3,
    "default_max_tokens": 500,
}


# Token limits per model (for cost tracking)
TOKEN_COSTS = {
    ModelName.GPT_5: {
        "input": 5.00,  # per 1M tokens (estimated - adjust when official pricing available)
        "output": 15.00,
    },
    ModelName.GPT_4O: {
        "input": 2.50,
        "output": 10.00,
    },
    ModelName.GPT_4O_MINI: {
        "input": 0.150,
        "output": 0.600,
    },
    ModelName.TEXT_EMBEDDING_3_SMALL: {
        "input": 0.020,
        "output": 0.0,
    },
    ModelName.CLAUDE_SONNET_4_5: {
        "input": 3.00,  # With caching: 0.30
        "output": 15.00,
    },
}


def get_model_config(task_type: TaskType) -> Dict[str, Any]:
    """Get model configuration for a specific task"""
    config = MODEL_ROUTING.get(task_type)
    if not config:
        # Fallback to GPT-4o-mini for unknown tasks
        return {
            "model": ModelName.GPT_4O_MINI,
            "provider": ModelProvider.OPENAI,
            "temperature": 0.7,
            "max_tokens": 500,
        }
    return config


def get_api_key(provider: ModelProvider) -> str:
    """Get API key for a provider"""
    if provider == ModelProvider.OPENAI:
        return OPENAI_CONFIG["api_key"]
    elif provider == ModelProvider.ANTHROPIC:
        return ANTHROPIC_CONFIG["api_key"]
    else:
        raise ValueError(f"Unknown provider: {provider}")

