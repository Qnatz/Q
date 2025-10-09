# utils/performance_utils.py

import time
import functools
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

def performance_monitor(threshold: float = 5.0):
    """Decorator to log slow function executions"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                if execution_time > threshold:
                    logger.warning(
                        f"SLOW PERFORMANCE: {func.__name__} took {execution_time:.2f}s "
                        f"(threshold: {threshold}s)"
                    )
        return wrapper
    return decorator
