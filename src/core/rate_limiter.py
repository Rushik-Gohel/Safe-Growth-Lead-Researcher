"""Token and request rate limiting with sliding window algorithm."""

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional
from threading import Lock
import logging

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimitMetrics:
    """Metrics for rate limiting dashboard."""
    
    current_rpm: int = 0
    current_tpm: int = 0
    max_rpm: int = field(default_factory=lambda: settings.gemini_rpm)
    max_tpm: int = field(default_factory=lambda: settings.gemini_tpm)
    total_requests: int = 0
    total_tokens: int = 0
    requests_blocked: int = 0
    last_request_time: Optional[float] = None
    
    @property
    def rpm_percentage(self) -> float:
        """Calculate RPM usage percentage."""
        return (self.current_rpm / self.max_rpm * 100) if self.max_rpm > 0 else 0
    
    @property
    def tpm_percentage(self) -> float:
        """Calculate TPM usage percentage."""
        return (self.current_tpm / self.max_tpm * 100) if self.max_tpm > 0 else 0
    
    @property
    def is_near_limit(self) -> bool:
        """Check if approaching rate limits (>80%)."""
        return self.rpm_percentage > 80 or self.tpm_percentage > 80


@dataclass
class RequestRecord:
    """Record of a single request for sliding window."""
    
    timestamp: float
    tokens: int


class TokenGovernor:
    """
    Rate limiter using sliding window algorithm for RPM and TPM tracking.
    Thread-safe implementation for concurrent requests.
    """
    
    def __init__(
        self,
        rpm_limit: Optional[int] = None,
        tpm_limit: Optional[int] = None,
        window_seconds: int = 60
    ):
        """
        Initialize the token governor.
        
        Args:
            rpm_limit: Requests per minute limit (default from settings)
            tpm_limit: Tokens per minute limit (default from settings)
            window_seconds: Sliding window size in seconds
        """
        self.rpm_limit = rpm_limit or settings.gemini_rpm
        self.tpm_limit = tpm_limit or settings.gemini_tpm
        self.window_seconds = window_seconds
        
        # Sliding window storage
        self._requests: Deque[RequestRecord] = deque()
        self._lock = Lock()
        
        # Metrics
        self._metrics = RateLimitMetrics(
            max_rpm=self.rpm_limit,
            max_tpm=self.tpm_limit
        )
        
        logger.info(
            f"TokenGovernor initialized: RPM={self.rpm_limit}, "
            f"TPM={self.tpm_limit}, Window={self.window_seconds}s"
        )
    
    def _cleanup_old_requests(self, current_time: float) -> None:
        """Remove requests outside the sliding window."""
        cutoff_time = current_time - self.window_seconds
        
        while self._requests and self._requests[0].timestamp < cutoff_time:
            self._requests.popleft()
    
    def _calculate_current_usage(self) -> tuple[int, int]:
        """Calculate current RPM and TPM from sliding window."""
        current_rpm = len(self._requests)
        current_tpm = sum(req.tokens for req in self._requests)
        return current_rpm, current_tpm
    
    def check_rate_limit(self, estimated_tokens: int = 1000) -> tuple[bool, Optional[float]]:
        """
        Check if request can proceed without exceeding rate limits.
        
        Args:
            estimated_tokens: Estimated tokens for the request
            
        Returns:
            Tuple of (can_proceed, wait_time_seconds)
        """
        with self._lock:
            current_time = time.time()
            self._cleanup_old_requests(current_time)
            
            current_rpm, current_tpm = self._calculate_current_usage()
            
            # Check if adding this request would exceed limits
            would_exceed_rpm = (current_rpm + 1) > self.rpm_limit
            would_exceed_tpm = (current_tpm + estimated_tokens) > self.tpm_limit
            
            if would_exceed_rpm or would_exceed_tpm:
                # Calculate wait time based on oldest request
                if self._requests:
                    oldest_request = self._requests[0]
                    wait_time = self.window_seconds - (current_time - oldest_request.timestamp)
                    wait_time = max(0, wait_time) + 1  # Add 1 second buffer
                else:
                    wait_time = 1.0
                
                self._metrics.requests_blocked += 1
                logger.warning(
                    f"Rate limit would be exceeded: RPM={current_rpm}/{self.rpm_limit}, "
                    f"TPM={current_tpm}/{self.tpm_limit}. Wait {wait_time:.1f}s"
                )
                return False, wait_time
            
            return True, None
    
    def record_request(self, tokens_used: int) -> None:
        """
        Record a completed request for rate limiting.
        
        Args:
            tokens_used: Number of tokens consumed by the request
        """
        with self._lock:
            current_time = time.time()
            self._cleanup_old_requests(current_time)
            
            # Add new request
            self._requests.append(RequestRecord(
                timestamp=current_time,
                tokens=tokens_used
            ))
            
            # Update metrics
            self._metrics.total_requests += 1
            self._metrics.total_tokens += tokens_used
            self._metrics.last_request_time = current_time
            
            # Update current usage
            self._metrics.current_rpm, self._metrics.current_tpm = self._calculate_current_usage()
            
            logger.debug(
                f"Request recorded: {tokens_used} tokens. "
                f"Current: RPM={self._metrics.current_rpm}/{self.rpm_limit}, "
                f"TPM={self._metrics.current_tpm}/{self.tpm_limit}"
            )
    
    def get_metrics(self) -> RateLimitMetrics:
        """Get current rate limiting metrics."""
        with self._lock:
            current_time = time.time()
            self._cleanup_old_requests(current_time)
            self._metrics.current_rpm, self._metrics.current_tpm = self._calculate_current_usage()
            return self._metrics
    
    def wait_if_needed(self, estimated_tokens: int = 1000) -> float:
        """
        Wait if rate limit would be exceeded.
        
        Args:
            estimated_tokens: Estimated tokens for the request
            
        Returns:
            Time waited in seconds
        """
        can_proceed, wait_time = self.check_rate_limit(estimated_tokens)
        
        if not can_proceed and wait_time:
            logger.info(f"Rate limit reached. Waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
            return wait_time
        
        return 0.0
    
    def reset(self) -> None:
        """Reset all rate limiting data (useful for testing)."""
        with self._lock:
            self._requests.clear()
            self._metrics = RateLimitMetrics(
                max_rpm=self.rpm_limit,
                max_tpm=self.tpm_limit
            )
            logger.info("TokenGovernor reset")


# Global token governor instance
token_governor = TokenGovernor()

# Made with Bob
