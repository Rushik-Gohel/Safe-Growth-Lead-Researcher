"""Tests for caching functionality."""

import time
import pytest
from src.core.cache import TTLCache, cached, get_cache_stats, clear_cache, global_cache


class TestTTLCache:
    """Test TTL cache functionality."""
    
    def setup_method(self):
        """Setup test cache."""
        self.cache = TTLCache(max_size=10, default_ttl=2)
    
    def test_basic_set_get(self):
        """Test basic set and get operations."""
        self.cache.set("key1", "value1")
        assert self.cache.get("key1") == "value1"
    
    def test_cache_miss(self):
        """Test cache miss returns None."""
        assert self.cache.get("nonexistent") is None
    
    def test_ttl_expiration(self):
        """Test that entries expire after TTL."""
        self.cache.set("key1", "value1", ttl=1)
        assert self.cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(1.1)
        assert self.cache.get("key1") is None
    
    def test_cache_stats(self):
        """Test cache statistics tracking."""
        # Clear stats
        self.cache._stats.hits = 0
        self.cache._stats.misses = 0
        
        # Set and get
        self.cache.set("key1", "value1")
        self.cache.get("key1")  # Hit
        self.cache.get("key2")  # Miss
        
        stats = self.cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.size == 1
    
    def test_max_size_eviction(self):
        """Test LRU eviction when max size is reached."""
        cache = TTLCache(max_size=3, default_ttl=60)
        
        # Fill cache
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Access key1 to make it more recently used
        cache.get("key1")
        
        # Add new entry, should evict key2 (least recently used)
        cache.set("key4", "value4")
        
        assert cache.get("key1") is not None
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") is not None
        assert cache.get("key4") is not None
    
    def test_clear_cache(self):
        """Test clearing all cache entries."""
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        
        self.cache.clear()
        
        assert self.cache.get("key1") is None
        assert self.cache.get("key2") is None
        assert self.cache.get_stats().size == 0
    
    def test_hit_rate_calculation(self):
        """Test hit rate calculation."""
        self.cache._stats.hits = 0
        self.cache._stats.misses = 0
        
        self.cache.set("key1", "value1")
        
        # 3 hits, 2 misses = 60% hit rate
        self.cache.get("key1")
        self.cache.get("key1")
        self.cache.get("key1")
        self.cache.get("key2")
        self.cache.get("key3")
        
        stats = self.cache.get_stats()
        assert stats.hit_rate == 60.0


class TestCachedDecorator:
    """Test cached decorator functionality."""
    
    def setup_method(self):
        """Setup for each test."""
        clear_cache()
        self.call_count = 0
    
    def test_cached_decorator(self):
        """Test that decorator caches function results."""
        @cached(ttl=60, key_prefix="test")
        def expensive_function(x):
            self.call_count += 1
            return x * 2
        
        # First call - should execute function
        result1 = expensive_function(5)
        assert result1 == 10
        assert self.call_count == 1
        
        # Second call - should use cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert self.call_count == 1  # Not incremented
        
        # Different argument - should execute function
        result3 = expensive_function(10)
        assert result3 == 20
        assert self.call_count == 2
    
    def test_cached_with_kwargs(self):
        """Test caching with keyword arguments."""
        @cached(ttl=60, key_prefix="test")
        def function_with_kwargs(a, b=10):
            self.call_count += 1
            return a + b
        
        # First call
        result1 = function_with_kwargs(5, b=10)
        assert result1 == 15
        assert self.call_count == 1
        
        # Same call - should use cache
        result2 = function_with_kwargs(5, b=10)
        assert result2 == 15
        assert self.call_count == 1
        
        # Different kwargs - should execute
        result3 = function_with_kwargs(5, b=20)
        assert result3 == 25
        assert self.call_count == 2
    
    def test_cache_expiration_in_decorator(self):
        """Test that cached decorator respects TTL."""
        @cached(ttl=1, key_prefix="test")
        def function_with_short_ttl(x):
            self.call_count += 1
            return x * 2
        
        # First call
        result1 = function_with_short_ttl(5)
        assert result1 == 10
        assert self.call_count == 1
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Should execute again after expiration
        result2 = function_with_short_ttl(5)
        assert result2 == 10
        assert self.call_count == 2


class TestGlobalCache:
    """Test global cache instance."""
    
    def setup_method(self):
        """Setup for each test."""
        clear_cache()
    
    def test_get_cache_stats(self):
        """Test getting global cache statistics."""
        stats = get_cache_stats()
        
        assert "hits" in stats
        assert "misses" in stats
        assert "evictions" in stats
        assert "size" in stats
        assert "hit_rate" in stats
    
    def test_clear_cache_function(self):
        """Test clearing global cache."""
        # Add some entries
        global_cache.set("test1", "value1")
        global_cache.set("test2", "value2")
        
        # Clear cache
        clear_cache()
        
        # Verify cleared
        assert global_cache.get("test1") is None
        assert global_cache.get("test2") is None


def test_cache_thread_safety():
    """Test that cache operations are thread-safe."""
    import threading
    
    cache = TTLCache(max_size=100, default_ttl=60)
    errors = []
    
    def worker(thread_id):
        try:
            for i in range(100):
                key = f"key_{thread_id}_{i}"
                cache.set(key, f"value_{i}")
                value = cache.get(key)
                assert value == f"value_{i}" or value is None
        except Exception as e:
            errors.append(e)
    
    # Create multiple threads
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    
    # Start all threads
    for thread in threads:
        thread.start()
    
    # Wait for completion
    for thread in threads:
        thread.join()
    
    # Check for errors
    assert len(errors) == 0, f"Thread safety errors: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


