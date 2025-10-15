"""
Performance Metrics and Monitoring
Tracks model usage, latency, costs, and errors
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects and aggregates metrics for monitoring
    Thread-safe singleton for tracking performance
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.metrics = {
            "requests_total": 0,
            "requests_success": 0,
            "requests_failed": 0,
            "crisis_detected": 0,
            "model_calls": defaultdict(int),
            "total_latency_ms": 0.0,
            "errors": defaultdict(int),
            "costs": defaultdict(float),
        }
        self._initialized = True
        logger.info("Metrics Collector initialized")
    
    def record_request(self, success: bool = True):
        """Record a chat request"""
        with self._lock:
            self.metrics["requests_total"] += 1
            if success:
                self.metrics["requests_success"] += 1
            else:
                self.metrics["requests_failed"] += 1
    
    def record_crisis(self):
        """Record crisis detection"""
        with self._lock:
            self.metrics["crisis_detected"] += 1
    
    def record_model_call(self, model_name: str, latency_ms: float):
        """Record model API call"""
        with self._lock:
            self.metrics["model_calls"][model_name] += 1
            self.metrics["total_latency_ms"] += latency_ms
    
    def record_error(self, error_type: str):
        """Record an error"""
        with self._lock:
            self.metrics["errors"][error_type] += 1
    
    def record_cost(self, model_name: str, cost: float):
        """Record cost for a model call"""
        with self._lock:
            self.metrics["costs"][model_name] += cost
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics snapshot"""
        with self._lock:
            return {
                "requests_total": self.metrics["requests_total"],
                "requests_success": self.metrics["requests_success"],
                "requests_failed": self.metrics["requests_failed"],
                "success_rate": (
                    self.metrics["requests_success"] / self.metrics["requests_total"]
                    if self.metrics["requests_total"] > 0 else 0
                ),
                "crisis_detected": self.metrics["crisis_detected"],
                "model_calls": dict(self.metrics["model_calls"]),
                "avg_latency_ms": (
                    self.metrics["total_latency_ms"] / self.metrics["requests_total"]
                    if self.metrics["requests_total"] > 0 else 0
                ),
                "errors": dict(self.metrics["errors"]),
                "total_cost": sum(self.metrics["costs"].values()),
                "cost_by_model": dict(self.metrics["costs"]),
            }
    
    def log_metrics(self):
        """Log current metrics"""
        metrics = self.get_metrics()
        logger.info(f"=== METRICS SNAPSHOT ===")
        logger.info(f"Total Requests: {metrics['requests_total']}")
        logger.info(f"Success Rate: {metrics['success_rate']:.2%}")
        logger.info(f"Crisis Detected: {metrics['crisis_detected']}")
        logger.info(f"Avg Latency: {metrics['avg_latency_ms']:.0f}ms")
        logger.info(f"Total Cost: ${metrics['total_cost']:.4f}")
        logger.info(f"Model Calls: {metrics['model_calls']}")
        if metrics['errors']:
            logger.info(f"Errors: {metrics['errors']}")


# Global metrics collector instance
metrics_collector = MetricsCollector()


class PerformanceTimer:
    """Context manager for timing operations"""
    
    def __init__(self, operation_name: str, model_name: Optional[str] = None):
        self.operation_name = operation_name
        self.model_name = model_name
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        elapsed_ms = (self.end_time - self.start_time) * 1000
        
        if self.model_name:
            metrics_collector.record_model_call(self.model_name, elapsed_ms)
            logger.info(f"{self.operation_name} ({self.model_name}): {elapsed_ms:.0f}ms")
        else:
            logger.info(f"{self.operation_name}: {elapsed_ms:.0f}ms")
        
        if exc_type:
            metrics_collector.record_error(f"{self.operation_name}_error")
        
        return False  # Don't suppress exceptions


def log_conversation_metrics(
    session_id: str,
    message_count: int,
    question_count: int,
    is_crisis: bool,
    stage: str,
):
    """Log conversation-level metrics"""
    logger.info(
        f"Conversation {session_id}: "
        f"Messages={message_count}, "
        f"Questions={question_count}, "
        f"Crisis={is_crisis}, "
        f"Stage={stage}"
    )
    
    if is_crisis:
        metrics_collector.record_crisis()



