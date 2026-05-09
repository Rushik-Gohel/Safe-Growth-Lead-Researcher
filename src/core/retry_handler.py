"""Retry logic with exponential backoff and jitter."""

import time
import random
import logging
from typing import Callable, TypeVar, Any, Optional
from functools import wraps
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

from .config import settings

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryHandler:
    """Handler for retry logic with exponential backoff."""
    
    def __init__(
        self,
        max_attempts: Optional[int] = None,
        initial_delay: Optional[int] = None,
        max_delay: int = 60,
        exponential_base: int = 2,
        jitter: bool = True
    ):
        """
        Initialize retry handler.
        
        Args:
            max_attempts: Maximum retry attempts (default from settings)
            initial_delay: Initial delay in seconds (default from settings)
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff
            jitter: Add random jitter to prevent thundering herd
        """
        self.max_attempts = max_attempts or settings.max_retries
        self.initial_delay = initial_delay or settings.retry_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        
        logger.info(
            f"RetryHandler initialized: max_attempts={self.max_attempts}, "
            f"initial_delay={self.initial_delay}s, max_delay={self.max_delay}s"
        )
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given attempt with exponential backoff and jitter.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        # Exponential backoff: initial_delay * (base ^ attempt)
        delay = self.initial_delay * (self.exponential_base ** attempt)
        
        # Cap at max_delay
        delay = min(delay, self.max_delay)
        
        # Add jitter (random value between 0 and delay)
        if self.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay
    
    def execute_with_retry(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any
    ) -> T:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                logger.debug(f"Attempt {attempt + 1}/{self.max_attempts} for {func.__name__}")
                result = func(*args, **kwargs)
                
                if attempt > 0:
                    logger.info(f"Success on attempt {attempt + 1}/{self.max_attempts}")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_attempts - 1:
                    delay = self.calculate_delay(attempt)
                    logger.warning(
                        f"Attempt {attempt + 1}/{self.max_attempts} failed: {str(e)}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {self.max_attempts} attempts failed for {func.__name__}: {str(e)}"
                    )
        
        # All attempts failed
        raise last_exception


def with_retry(
    max_attempts: Optional[int] = None,
    initial_delay: Optional[int] = None,
    retry_on: tuple = (Exception,)
):
    """
    Decorator for adding retry logic to functions using tenacity.
    
    Args:
        max_attempts: Maximum retry attempts
        initial_delay: Initial delay in seconds
        retry_on: Tuple of exception types to retry on
        
    Example:
        @with_retry(max_attempts=3, initial_delay=2)
        def fetch_data():
            # Your code here
            pass
    """
    max_attempts = max_attempts or settings.max_retries
    initial_delay = initial_delay or settings.retry_delay
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(
                multiplier=initial_delay,
                min=initial_delay,
                max=60
            ),
            retry=retry_if_exception_type(retry_on),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.DEBUG)
        )
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# Specific retry decorators for common scenarios
def retry_on_rate_limit(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for retrying on rate limit errors."""
    return with_retry(
        max_attempts=5,
        initial_delay=5,
        retry_on=(Exception,)  # Customize based on specific rate limit exceptions
    )(func)


def retry_on_network_error(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for retrying on network errors."""
    return with_retry(
        max_attempts=3,
        initial_delay=2,
        retry_on=(ConnectionError, TimeoutError)
    )(func)


# Global retry handler instance
retry_handler = RetryHandler()

# Made with Bob
