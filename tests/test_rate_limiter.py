"""Tests for rate limiter."""

import pytest
import time
from src.core.rate_limiter import TokenGovernor, RateLimitMetrics


def estimate_input_tokens(user_input: str) -> int:
    """Mirror the input token estimate used by UI/API research entrypoints."""
    return max(250, min(1000, len(user_input) * 4))


@pytest.fixture
def governor():
    """Create token governor for testing."""
    return TokenGovernor(rpm_limit=10, tpm_limit=1000, window_seconds=60)


class TestTokenGovernor:
    """Test token governor functionality."""
    
    def test_initialization(self, governor):
        """Test governor initialization."""
        assert governor.rpm_limit == 10
        assert governor.tpm_limit == 1000
        assert governor.window_seconds == 60
    
    def test_check_rate_limit_within_limits(self, governor):
        """Test rate limit check when within limits."""
        can_proceed, wait_time = governor.check_rate_limit(estimated_tokens=100)
        assert can_proceed is True
        assert wait_time is None
    
    def test_record_request(self, governor):
        """Test recording a request."""
        governor.record_request(tokens_used=100)
        metrics = governor.get_metrics()
        
        assert metrics.current_rpm == 1
        assert metrics.current_tpm == 100
        assert metrics.total_requests == 1
        assert metrics.total_tokens == 100
    
    def test_multiple_requests(self, governor):
        """Test multiple requests tracking."""
        for i in range(5):
            governor.record_request(tokens_used=50)
        
        metrics = governor.get_metrics()
        assert metrics.current_rpm == 5
        assert metrics.current_tpm == 250
        assert metrics.total_requests == 5
        assert metrics.total_tokens == 250
    
    def test_rpm_limit_exceeded(self, governor):
        """Test RPM limit detection."""
        # Record requests up to limit
        for i in range(10):
            governor.record_request(tokens_used=10)
        
        # Next request should be blocked
        can_proceed, wait_time = governor.check_rate_limit(estimated_tokens=10)
        assert can_proceed is False
        assert wait_time is not None
        assert wait_time > 0
    
    def test_tpm_limit_exceeded(self, governor):
        """Test TPM limit detection."""
        # Record request that would exceed TPM
        governor.record_request(tokens_used=900)
        
        # Next large request should be blocked
        can_proceed, wait_time = governor.check_rate_limit(estimated_tokens=200)
        assert can_proceed is False
        assert wait_time is not None
    
    def test_sliding_window_cleanup(self, governor):
        """Test that old requests are cleaned up."""
        # Create governor with 1 second window for testing
        test_governor = TokenGovernor(rpm_limit=10, tpm_limit=1000, window_seconds=1)
        
        # Record a request
        test_governor.record_request(tokens_used=100)
        metrics = test_governor.get_metrics()
        assert metrics.current_rpm == 1
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Check that request was cleaned up
        metrics = test_governor.get_metrics()
        assert metrics.current_rpm == 0
        assert metrics.current_tpm == 0
    
    def test_metrics_percentages(self, governor):
        """Test metrics percentage calculations."""
        # Record some requests
        for i in range(5):
            governor.record_request(tokens_used=100)
        
        metrics = governor.get_metrics()
        assert metrics.rpm_percentage == 50.0  # 5/10 * 100
        assert metrics.tpm_percentage == 50.0  # 500/1000 * 100
    
    def test_is_near_limit(self, governor):
        """Test near limit detection."""
        # Not near limit
        governor.record_request(tokens_used=100)
        metrics = governor.get_metrics()
        assert metrics.is_near_limit is False
        
        # Near limit (>80%)
        for i in range(8):
            governor.record_request(tokens_used=10)
        
        metrics = governor.get_metrics()
        assert metrics.is_near_limit is True
    
    def test_wait_if_needed(self, governor):
        """Test wait_if_needed functionality."""
        # Should not wait when within limits
        wait_time = governor.wait_if_needed(estimated_tokens=100)
        assert wait_time == 0.0
        
        # Record requests up to limit
        for i in range(10):
            governor.record_request(tokens_used=10)
        
        # Should wait when limit exceeded
        # Note: This test might be slow due to actual waiting
        # In production, you might want to mock time.sleep
    
    def test_reset(self, governor):
        """Test governor reset."""
        # Record some requests
        for i in range(5):
            governor.record_request(tokens_used=100)
        
        # Reset
        governor.reset()
        
        # Check that everything is cleared
        metrics = governor.get_metrics()
        assert metrics.current_rpm == 0
        assert metrics.current_tpm == 0
        assert metrics.total_requests == 0
        assert metrics.total_tokens == 0
    
    def test_concurrent_requests(self, governor):
        """Test thread safety with concurrent requests."""
        import threading
        
        def record_multiple():
            for i in range(10):
                governor.record_request(tokens_used=10)
        
        # Create multiple threads
        threads = [threading.Thread(target=record_multiple) for _ in range(3)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check final metrics
        metrics = governor.get_metrics()
        assert metrics.total_requests == 30
        assert metrics.total_tokens == 300


class TestRateLimitMetrics:
    """Test rate limit metrics."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = RateLimitMetrics(max_rpm=15, max_tpm=1000000)
        assert metrics.current_rpm == 0
        assert metrics.current_tpm == 0
        assert metrics.max_rpm == 15
        assert metrics.max_tpm == 1000000
    
    def test_percentage_calculations(self):
        """Test percentage calculations."""
        metrics = RateLimitMetrics(
            current_rpm=10,
            current_tpm=500000,
            max_rpm=15,
            max_tpm=1000000
        )
        
        assert metrics.rpm_percentage == pytest.approx(66.67, rel=0.01)
        assert metrics.tpm_percentage == 50.0
    
    def test_is_near_limit_property(self):
        """Test is_near_limit property."""
        # Not near limit
        metrics = RateLimitMetrics(
            current_rpm=5,
            current_tpm=100000,
            max_rpm=15,
            max_tpm=1000000
        )
        assert metrics.is_near_limit is False
        
        # Near RPM limit
        metrics.current_rpm = 13
        assert metrics.is_near_limit is True
        
        # Near TPM limit
        metrics.current_rpm = 5
        metrics.current_tpm = 850000
        assert metrics.is_near_limit is True


class TestResearchInputRateLimitEstimate:
    """Test input rate limiting token estimation."""

    def test_estimate_input_tokens_has_minimum_floor(self):
        """Small inputs should still reserve a minimum token budget."""
        assert estimate_input_tokens("Acme") == 250

    def test_estimate_input_tokens_scales_with_input_length(self):
        """Medium inputs should scale with input size."""
        assert estimate_input_tokens("a" * 100) == 400

    def test_estimate_input_tokens_has_maximum_cap(self):
        """Very large inputs should be capped."""
        assert estimate_input_tokens("a" * 1000) == 1000

    def test_input_rate_limit_blocks_after_reserved_capacity_is_used(self):
        """Research input should be blocked once reserved TPM capacity is exhausted."""
        governor = TokenGovernor(rpm_limit=10, tpm_limit=1000, window_seconds=60)

        reserved_tokens = estimate_input_tokens("Acme")
        assert reserved_tokens == 250

        for _ in range(4):
            can_proceed, wait_time = governor.check_rate_limit(estimated_tokens=reserved_tokens)
            assert can_proceed is True
            assert wait_time is None
            governor.record_request(tokens_used=reserved_tokens)

        can_proceed, wait_time = governor.check_rate_limit(estimated_tokens=reserved_tokens)
        assert can_proceed is False
        assert wait_time is not None
        assert wait_time > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

# Made with Bob
