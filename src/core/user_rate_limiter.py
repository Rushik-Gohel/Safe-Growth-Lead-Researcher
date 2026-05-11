"""Per-user rate limiting for public deployment."""

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, Deque, Optional, Tuple
from threading import Lock
import logging

logger = logging.getLogger(__name__)


@dataclass
class UserRequestRecord:
    """Record of a user's request."""
    timestamp: float


class UserRateLimiter:
    """
    Per-user rate limiter to prevent abuse in public deployments.
    Tracks requests per user (by IP or session) with sliding window.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 5,
        requests_per_hour: int = 20,
        window_seconds: int = 60
    ):
        """
        Initialize user rate limiter.
        
        Args:
            requests_per_minute: Max requests per user per minute
            requests_per_hour: Max requests per user per hour
            window_seconds: Sliding window size in seconds
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.window_seconds = window_seconds
        self.hour_window_seconds = 3600
        
        # Track requests per user
        self._user_requests_minute: Dict[str, Deque[UserRequestRecord]] = defaultdict(deque)
        self._user_requests_hour: Dict[str, Deque[UserRequestRecord]] = defaultdict(deque)
        self._lock = Lock()
        
        # Metrics
        self._total_users = 0
        self._blocked_requests = 0
        
        logger.info(
            f"UserRateLimiter initialized: {requests_per_minute} req/min, "
            f"{requests_per_hour} req/hour per user"
        )
    
    def _cleanup_old_requests(
        self,
        user_id: str,
        current_time: float
    ) -> None:
        """Remove requests outside the sliding windows."""
        # Cleanup minute window
        minute_cutoff = current_time - self.window_seconds
        while (self._user_requests_minute[user_id] and 
               self._user_requests_minute[user_id][0].timestamp < minute_cutoff):
            self._user_requests_minute[user_id].popleft()
        
        # Cleanup hour window
        hour_cutoff = current_time - self.hour_window_seconds
        while (self._user_requests_hour[user_id] and 
               self._user_requests_hour[user_id][0].timestamp < hour_cutoff):
            self._user_requests_hour[user_id].popleft()
    
    def check_rate_limit(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user can make a request.
        
        Args:
            user_id: User identifier (IP address or session ID)
            
        Returns:
            Tuple of (can_proceed, error_message)
        """
        with self._lock:
            current_time = time.time()
            self._cleanup_old_requests(user_id, current_time)
            
            # Check minute limit
            minute_requests = len(self._user_requests_minute[user_id])
            if minute_requests >= self.requests_per_minute:
                self._blocked_requests += 1
                oldest_request = self._user_requests_minute[user_id][0]
                wait_time = self.window_seconds - (current_time - oldest_request.timestamp)
                wait_time = max(0, wait_time) + 1
                
                logger.warning(
                    f"User {user_id[:8]}... exceeded minute limit: "
                    f"{minute_requests}/{self.requests_per_minute}"
                )
                return False, f"Rate limit exceeded. Please wait {wait_time:.0f} seconds before trying again."
            
            # Check hour limit
            hour_requests = len(self._user_requests_hour[user_id])
            if hour_requests >= self.requests_per_hour:
                self._blocked_requests += 1
                oldest_request = self._user_requests_hour[user_id][0]
                wait_time = self.hour_window_seconds - (current_time - oldest_request.timestamp)
                wait_minutes = max(0, wait_time) / 60
                
                logger.warning(
                    f"User {user_id[:8]}... exceeded hour limit: "
                    f"{hour_requests}/{self.requests_per_hour}"
                )
                return False, f"Hourly rate limit exceeded. Please wait {wait_minutes:.0f} minutes before trying again."
            
            return True, None
    
    def record_request(self, user_id: str) -> None:
        """
        Record a user's request.
        
        Args:
            user_id: User identifier (IP address or session ID)
        """
        with self._lock:
            current_time = time.time()
            self._cleanup_old_requests(user_id, current_time)
            
            # Track new user
            if not self._user_requests_minute[user_id]:
                self._total_users += 1
            
            # Record request in both windows
            record = UserRequestRecord(timestamp=current_time)
            self._user_requests_minute[user_id].append(record)
            self._user_requests_hour[user_id].append(UserRequestRecord(timestamp=current_time))
            
            logger.debug(
                f"Request recorded for user {user_id[:8]}...: "
                f"minute={len(self._user_requests_minute[user_id])}/{self.requests_per_minute}, "
                f"hour={len(self._user_requests_hour[user_id])}/{self.requests_per_hour}"
            )
    
    def get_user_stats(self, user_id: str) -> Dict[str, int]:
        """Get current stats for a user."""
        with self._lock:
            current_time = time.time()
            self._cleanup_old_requests(user_id, current_time)
            
            return {
                "requests_this_minute": len(self._user_requests_minute[user_id]),
                "requests_this_hour": len(self._user_requests_hour[user_id]),
                "minute_limit": self.requests_per_minute,
                "hour_limit": self.requests_per_hour
            }
    
    def get_global_stats(self) -> Dict[str, int]:
        """Get global statistics."""
        with self._lock:
            return {
                "total_users": self._total_users,
                "blocked_requests": self._blocked_requests,
                "active_users_minute": len([
                    uid for uid, reqs in self._user_requests_minute.items() 
                    if reqs
                ]),
                "active_users_hour": len([
                    uid for uid, reqs in self._user_requests_hour.items() 
                    if reqs
                ])
            }
    
    def reset(self) -> None:
        """Reset all rate limiting data."""
        with self._lock:
            self._user_requests_minute.clear()
            self._user_requests_hour.clear()
            self._total_users = 0
            self._blocked_requests = 0
            logger.info("UserRateLimiter reset")


# Global user rate limiter instance
user_rate_limiter = UserRateLimiter(
    requests_per_minute=5,  # 5 requests per minute per user
    requests_per_hour=20     # 20 requests per hour per user
)


