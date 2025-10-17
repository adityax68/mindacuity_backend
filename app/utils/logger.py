import logging
import time
import json
from datetime import datetime
from typing import Any, Dict, Optional
from functools import wraps
import traceback

# Configure structured logging
class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Create formatter for structured logs
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def perf(self, operation: str, duration_ms: float, **kwargs):
        """Log performance metrics"""
        log_data = {
            "type": "PERF",
            "operation": operation,
            "duration_ms": round(duration_ms, 2),
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        self.logger.info(f"PERF | {json.dumps(log_data)}")
    
    def error(self, operation: str, error: Exception, **kwargs):
        """Log errors with context"""
        log_data = {
            "type": "ERROR",
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        self.logger.error(f"ERROR | {json.dumps(log_data)}")
    
    def info(self, message: str, **kwargs):
        """Log info messages"""
        log_data = {
            "type": "INFO",
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        self.logger.info(f"INFO | {json.dumps(log_data)}")
    
    def warn(self, message: str, **kwargs):
        """Log warning messages"""
        log_data = {
            "type": "WARN",
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        self.logger.warning(f"WARN | {json.dumps(log_data)}")

# Create logger instances
chat_logger = StructuredLogger("CHAT_SERVICE")
assessment_logger = StructuredLogger("ASSESSMENT_SERVICE")
session_logger = StructuredLogger("SESSION_SERVICE")
api_logger = StructuredLogger("API_SERVICE")

def log_performance(operation: str):
    """Decorator to log performance of functions"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                chat_logger.perf(
                    operation=operation,
                    duration_ms=duration_ms,
                    function=func.__name__,
                    status="success"
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                chat_logger.error(
                    operation=operation,
                    error=e,
                    duration_ms=duration_ms,
                    function=func.__name__,
                    status="error"
                )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                chat_logger.perf(
                    operation=operation,
                    duration_ms=duration_ms,
                    function=func.__name__,
                    status="success"
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                chat_logger.error(
                    operation=operation,
                    error=e,
                    duration_ms=duration_ms,
                    function=func.__name__,
                    status="error"
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def log_api_performance(operation: str):
    """Decorator specifically for API endpoints"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                api_logger.perf(
                    operation=operation,
                    duration_ms=duration_ms,
                    endpoint=func.__name__,
                    status="success"
                )
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                api_logger.error(
                    operation=operation,
                    error=e,
                    duration_ms=duration_ms,
                    endpoint=func.__name__,
                    status="error"
                )
                raise
        return wrapper
    return decorator

# Import asyncio for the decorator
import asyncio
