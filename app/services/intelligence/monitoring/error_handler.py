"""
Centralized Error Handling
Provides consistent error handling and logging across the intelligent system
"""

import logging
from typing import Optional, Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)


class ChatbotError(Exception):
    """Base exception for chatbot-related errors"""
    pass


class LLMError(ChatbotError):
    """Error related to LLM API calls"""
    pass


class StateError(ChatbotError):
    """Error related to conversation state management"""
    pass


class RoutingError(ChatbotError):
    """Error related to intent routing"""
    pass


def handle_errors(fallback_message: str = "I'm sorry, I encountered an error. Please try again."):
    """
    Decorator for handling errors gracefully
    
    Args:
        fallback_message: Message to return if error occurs
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except LLMError as e:
                logger.error(f"LLM Error in {func.__name__}: {e}", exc_info=True)
                return fallback_message
            except StateError as e:
                logger.error(f"State Error in {func.__name__}: {e}", exc_info=True)
                return fallback_message
            except RoutingError as e:
                logger.error(f"Routing Error in {func.__name__}: {e}", exc_info=True)
                return fallback_message
            except Exception as e:
                logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
                return fallback_message
        
        return wrapper
    return decorator


def log_and_suppress(error_message: str = "Error suppressed"):
    """
    Decorator that logs errors but doesn't raise them
    Useful for non-critical operations
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Optional[Any]:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(f"{error_message} in {func.__name__}: {e}")
                return None
        
        return wrapper
    return decorator


class ErrorContext:
    """Context manager for error handling with custom logic"""
    
    def __init__(
        self,
        operation_name: str,
        fallback_value: Any = None,
        critical: bool = False,
    ):
        self.operation_name = operation_name
        self.fallback_value = fallback_value
        self.critical = critical
        self.error = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.error = exc_val
            
            if self.critical:
                logger.critical(
                    f"CRITICAL ERROR in {self.operation_name}: {exc_val}",
                    exc_info=True
                )
                return False  # Re-raise
            else:
                logger.error(
                    f"Error in {self.operation_name}: {exc_val}",
                    exc_info=True
                )
                return True  # Suppress exception
        
        return False


def safe_execute(func: Callable, *args, fallback=None, **kwargs) -> Any:
    """
    Safely execute a function with error handling
    
    Args:
        func: Function to execute
        fallback: Value to return if error occurs
        *args, **kwargs: Arguments for the function
    
    Returns:
        Function result or fallback value
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error in {func.__name__}: {e}")
        return fallback



