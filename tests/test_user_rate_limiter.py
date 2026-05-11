"""Tests for per-user rate limiting."""

import pytest
import time
from src.core.user_rate_limiter import UserRateLimiter


def test_user_rate_limiter_basic():
    """Test basic rate limiting functionality."""
    limiter = UserRateLimiter(
        requests_per_minute=3,
        requests_per_hour=10
    )
    
    user_id = "test_user_1"
    
    # First 3 requests should succeed
    for i in range(3):
        can_proceed, error = limiter.check_rate_limit(user_id)
        assert can_proceed, f"Request {i+1} should succeed"
        assert error is None
        limiter.record_request(user_id)
    
    # 4th request should fail (minute limit)
    can_proceed, error = limiter.check_rate_limit(user_id)
    assert not can_proceed, "4th request should fail"
    assert error is not None
    assert "wait" in error.lower()


def test_user_rate_limiter_multiple_users():
    """Test that different users have independent limits."""
    limiter = UserRateLimiter(
        requests_per_minute=2,
        requests_per_hour=5
    )
    
    user1 = "user_1"
    user2 = "user_2"
    
    # User 1 makes 2 requests
    for _ in range(2):
        can_proceed, _ = limiter.check_rate_limit(user1)
        assert can_proceed
        limiter.record_request(user1)
    
    # User 1 is now blocked
    can_proceed, error = limiter.check_rate_limit(user1)
    assert not can_proceed
    
    # User 2 should still be able to make requests
    can_proceed, error = limiter.check_rate_limit(user2)
    assert can_proceed
    limiter.record_request(user2)


def test_user_rate_limiter_sliding_window():
    """Test that sliding window works correctly."""
    limiter = UserRateLimiter(
        requests_per_minute=2,
        requests_per_hour=10,
        window_seconds=2  # 2 second window for testing
    )
    
    user_id = "test_user_sliding"
    
    # Make 2 requests
    for _ in range(2):
        can_proceed, _ = limiter.check_rate_limit(user_id)
        assert can_proceed
        limiter.record_request(user_id)
    
    # Should be blocked
    can_proceed, _ = limiter.check_rate_limit(user_id)
    assert not can_proceed
    
    # Wait for window to expire
    time.sleep(2.5)
    
    # Should be able to make requests again
    can_proceed, error = limiter.check_rate_limit(user_id)
    assert can_proceed, f"Should be able to proceed after window expires: {error}"


def test_user_rate_limiter_hour_limit():
    """Test hourly rate limit."""
    limiter = UserRateLimiter(
        requests_per_minute=100,  # High minute limit
        requests_per_hour=5       # Low hour limit
    )
    
    user_id = "test_user_hour"
    
    # Make 5 requests (should all succeed)
    for i in range(5):
        can_proceed, _ = limiter.check_rate_limit(user_id)
        assert can_proceed, f"Request {i+1} should succeed"
        limiter.record_request(user_id)
    
    # 6th request should fail (hour limit)
    can_proceed, error = limiter.check_rate_limit(user_id)
    assert not can_proceed, "6th request should fail due to hour limit"
    assert error is not None
    assert "hour" in error.lower() or "minute" in error.lower()


def test_user_stats():
    """Test getting user statistics."""
    limiter = UserRateLimiter(
        requests_per_minute=5,
        requests_per_hour=20
    )
    
    user_id = "test_user_stats"
    
    # Make 3 requests
    for _ in range(3):
        limiter.record_request(user_id)
    
    stats = limiter.get_user_stats(user_id)
    
    assert stats["requests_this_minute"] == 3
    assert stats["requests_this_hour"] == 3
    assert stats["minute_limit"] == 5
    assert stats["hour_limit"] == 20


def test_global_stats():
    """Test getting global statistics."""
    limiter = UserRateLimiter(
        requests_per_minute=5,
        requests_per_hour=20
    )
    
    # Multiple users make requests
    for i in range(3):
        user_id = f"user_{i}"
        limiter.record_request(user_id)
    
    stats = limiter.get_global_stats()
    
    assert stats["total_users"] >= 3
    assert stats["active_users_minute"] >= 3


def test_reset():
    """Test resetting rate limiter."""
    limiter = UserRateLimiter(
        requests_per_minute=2,
        requests_per_hour=5
    )
    
    user_id = "test_user_reset"
    
    # Make requests until blocked
    for _ in range(2):
        limiter.record_request(user_id)
    
    can_proceed, _ = limiter.check_rate_limit(user_id)
    assert not can_proceed
    
    # Reset
    limiter.reset()
    
    # Should be able to make requests again
    can_proceed, error = limiter.check_rate_limit(user_id)
    assert can_proceed, f"Should be able to proceed after reset: {error}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob
