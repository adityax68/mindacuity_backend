"""
Model Error Handler with Retry Logic and Detailed Logging
Handles all LLM API errors gracefully with fallbacks
"""

import asyncio
import logging
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Awaitable
from functools import wraps

logger = logging.getLogger(__name__)

# Specialized logger for model interactions
model_logger = logging.getLogger("model_interactions")


class ModelError(Exception):
    """Base class for model errors"""
    pass


class RateLimitError(ModelError):
    """Rate limit exceeded"""
    pass


class TokenLimitError(ModelError):
    """Context length exceeded"""
    pass


class TimeoutError(ModelError):
    """Request timeout"""
    pass


class AuthenticationError(ModelError):
    """Authentication failed"""
    pass


class ModelInteractionLogger:
    """
    Structured logging for all model interactions
    """
    
    @staticmethod
    def log_request(
        model_name: str,
        session_id: str,
        prompt_preview: str,
        prompt_tokens: int,
        temperature: float = 0.7,
        max_tokens: int = 500
    ):
        """Log model request"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "model_request",
            "model": model_name,
            "session_id": session_id,
            "prompt_tokens": prompt_tokens,
            "prompt_preview": prompt_preview[:200],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        model_logger.info(json.dumps(log_entry))
    
    @staticmethod
    def log_response(
        model_name: str,
        session_id: str,
        completion_tokens: int,
        latency_ms: float,
        cost_estimate: float = 0.0
    ):
        """Log model response"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "model_response",
            "model": model_name,
            "session_id": session_id,
            "completion_tokens": completion_tokens,
            "latency_ms": latency_ms,
            "cost_estimate": cost_estimate
        }
        model_logger.info(json.dumps(log_entry))
    
    @staticmethod
    def log_error(
        model_name: str,
        session_id: str,
        error_type: str,
        error_message: str,
        attempt: int = 1,
        will_retry: bool = False
    ):
        """Log model error"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": "model_error",
            "level": "ERROR",
            "model": model_name,
            "session_id": session_id,
            "error_type": error_type,
            "error_message": error_message,
            "attempt": attempt,
            "will_retry": will_retry,
            "stack_trace": traceback.format_exc()
        }
        model_logger.error(json.dumps(log_entry))


class ModelErrorHandler:
    """
    Handles all model errors with graceful degradation and retry logic
    """
    
    USER_FRIENDLY_MESSAGES = {
        "rate_limit": "I'm experiencing high traffic right now. Please try again in a moment.",
        "token_limit": "Our conversation has grown quite long. Let me provide an assessment based on what we've discussed.",
        "timeout": "I'm taking a bit longer to respond. Please try again.",
        "authentication": "I'm having trouble connecting to the service. Please try again later.",
        "unknown": "I encountered an unexpected issue. Please try again."
    }
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """
        Initialize error handler
        
        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff (seconds)
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.interaction_logger = ModelInteractionLogger()
    
    async def call_with_retry(
        self,
        model_func: Callable[[], Awaitable[Any]],
        model_name: str,
        session_id: str,
        operation: str = "inference"
    ) -> Dict[str, Any]:
        """
        Call model function with exponential backoff retry
        
        Args:
            model_func: Async function to call
            model_name: Name of the model (for logging)
            session_id: Session identifier
            operation: Operation description
            
        Returns:
            Dict with "success", "data", "error_type", "user_message", "backend_details"
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                # Call the model
                result = await model_func()
                
                return {
                    "success": True,
                    "data": result,
                    "attempt": attempt
                }
                
            except Exception as e:
                error_type = self._classify_error(e)
                will_retry = attempt < self.max_retries
                
                # Log the error
                self.interaction_logger.log_error(
                    model_name=model_name,
                    session_id=session_id,
                    error_type=error_type,
                    error_message=str(e),
                    attempt=attempt,
                    will_retry=will_retry
                )
                
                # If this is the last attempt or a non-retryable error, return error response
                if not will_retry or error_type in ["authentication", "token_limit"]:
                    return self._create_error_response(
                        error_type=error_type,
                        error=e,
                        attempt=attempt,
                        model_name=model_name,
                        session_id=session_id
                    )
                
                # Calculate backoff delay with jitter
                delay = self.base_delay * (2 ** (attempt - 1))
                delay = delay * (0.5 + 0.5 * (attempt / self.max_retries))  # Add jitter
                
                logger.warning(
                    f"Retry attempt {attempt}/{self.max_retries} for {model_name} "
                    f"after {delay:.1f}s delay. Error: {error_type}"
                )
                
                await asyncio.sleep(delay)
        
        # All retries exhausted
        return {
            "success": False,
            "error_type": "max_retries_exceeded",
            "user_message": self.USER_FRIENDLY_MESSAGES["unknown"],
            "backend_details": {
                "error": "Maximum retry attempts exceeded",
                "attempts": self.max_retries,
                "model": model_name
            }
        }
    
    def _classify_error(self, error: Exception) -> str:
        """
        Classify error type from exception
        """
        error_str = str(error).lower()
        error_class = error.__class__.__name__.lower()
        
        # Rate limit errors
        if "rate" in error_str or "ratelimit" in error_class:
            return "rate_limit"
        
        # Token/context length errors
        if any(x in error_str for x in ["context", "token", "length", "maximum"]):
            return "token_limit"
        
        # Timeout errors
        if "timeout" in error_str or "timeout" in error_class:
            return "timeout"
        
        # Authentication errors
        if any(x in error_str for x in ["auth", "api key", "unauthorized", "forbidden"]):
            return "authentication"
        
        # Connection errors
        if any(x in error_str for x in ["connection", "network", "unreachable"]):
            return "connection"
        
        return "unknown"
    
    def _create_error_response(
        self,
        error_type: str,
        error: Exception,
        attempt: int,
        model_name: str,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Create structured error response
        """
        user_message = self.USER_FRIENDLY_MESSAGES.get(
            error_type,
            self.USER_FRIENDLY_MESSAGES["unknown"]
        )
        
        backend_details = {
            "error_type": error_type,
            "error_class": error.__class__.__name__,
            "error_message": str(error),
            "attempts": attempt,
            "model": model_name,
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add specific details based on error type
        if error_type == "rate_limit":
            retry_after = getattr(error, 'retry_after', None)
            if retry_after:
                backend_details["retry_after_seconds"] = retry_after
        
        elif error_type == "token_limit":
            context_length = getattr(error, 'context_length', None)
            max_length = getattr(error, 'max_length', None)
            if context_length and max_length:
                backend_details["current_tokens"] = context_length
                backend_details["max_tokens"] = max_length
                backend_details["suggestion"] = "compress_history"
        
        return {
            "success": False,
            "error_type": error_type,
            "user_message": user_message,
            "backend_details": backend_details
        }
    
    def calculate_cost(
        self,
        model_name: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate estimated cost for model call
        """
        # Pricing per 1K tokens
        PRICING = {
            "anthropic-claude-sonnet": {"input": 0.003, "output": 0.015},
            "openai-gpt-4": {"input": 0.03, "output": 0.06},
            "openai-gpt-3.5": {"input": 0.0005, "output": 0.0015}
        }
        
        # Normalize model name
        model_key = None
        if "claude" in model_name.lower():
            model_key = "anthropic-claude-sonnet"
        elif "gpt-4" in model_name.lower() or "gpt-5" in model_name.lower():
            model_key = "openai-gpt-4"
        elif "gpt-3.5" in model_name.lower():
            model_key = "openai-gpt-3.5"
        
        if not model_key:
            return 0.0
        
        pricing = PRICING[model_key]
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        
        return round(input_cost + output_cost, 6)


def handle_model_errors(model_name: str, operation: str = "inference"):
    """
    Decorator for automatic error handling and retry
    
    Usage:
        @handle_model_errors(model_name="claude-sonnet", operation="classification")
        async def classify_message(message):
            return await anthropic_client.messages.create(...)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract session_id if available
            session_id = kwargs.get('session_id', 'unknown')
            
            error_handler = ModelErrorHandler()
            
            # Wrap the function call
            async def model_call():
                return await func(*args, **kwargs)
            
            result = await error_handler.call_with_retry(
                model_func=model_call,
                model_name=model_name,
                session_id=session_id,
                operation=operation
            )
            
            if not result["success"]:
                # Log error and raise
                logger.error(f"Model call failed: {result['backend_details']}")
                raise ModelError(result["user_message"])
            
            return result["data"]
        
        return wrapper
    return decorator


# Global error handler instance
error_handler = ModelErrorHandler()

