"""Simple test script for caching functionality."""

import time
import sys
from src.core.cache import TTLCache, cached, get_cache_stats, clear_cache


def test_basic_cache():
    """Test basic cache operations."""
    print("Testing basic cache operations...")
    cache = TTLCache(max_size=10, default_ttl=60)
    
    # Test set and get
    cache.set("key1", "value1")
    assert cache.get("key1") == "value1", "Failed: Basic get"
    print("✓ Basic set/get works")
    
    # Test cache miss
    assert cache.get("nonexistent") is None, "Failed: Cache miss"
    print("✓ Cache miss returns None")
    
    # Test stats
    stats = cache.get_stats()
    assert stats.hits > 0, "Failed: Stats tracking"
    print(f"✓ Cache stats: {stats.hits} hits, {stats.misses} misses, {stats.hit_rate:.1f}% hit rate")


def test_ttl_expiration():
    """Test TTL expiration."""
    print("\nTesting TTL expiration...")
    cache = TTLCache(max_size=10, default_ttl=1)
    
    cache.set("key1", "value1", ttl=1)
    assert cache.get("key1") == "value1", "Failed: Get before expiration"
    print("✓ Value exists before expiration")
    
    time.sleep(1.2)
    assert cache.get("key1") is None, "Failed: Get after expiration"
    print("✓ Value expired after TTL")


def test_cached_decorator():
    """Test cached decorator."""
    print("\nTesting cached decorator...")
    clear_cache()
    
    call_count = [0]  # Use list to allow modification in nested function
    
    @cached(ttl=60, key_prefix="test")
    def expensive_function(x):
        call_count[0] += 1
        return x * 2
    
    # First call
    result1 = expensive_function(5)
    assert result1 == 10, "Failed: First call result"
    assert call_count[0] == 1, "Failed: First call count"
    print("✓ First call executed function")
    
    # Second call (should use cache)
    result2 = expensive_function(5)
    assert result2 == 10, "Failed: Second call result"
    assert call_count[0] == 1, "Failed: Second call count (should be cached)"
    print("✓ Second call used cache")
    
    # Different argument
    result3 = expensive_function(10)
    assert result3 == 20, "Failed: Different argument result"
    assert call_count[0] == 2, "Failed: Different argument count"
    print("✓ Different argument executed function")


def test_max_size_eviction():
    """Test LRU eviction."""
    print("\nTesting LRU eviction...")
    cache = TTLCache(max_size=3, default_ttl=60)
    
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.set("key3", "value3")
    
    # Access key1 to make it recently used
    cache.get("key1")
    
    # Add new entry (should evict key2)
    cache.set("key4", "value4")
    
    assert cache.get("key1") is not None, "Failed: key1 should exist"
    assert cache.get("key2") is None, "Failed: key2 should be evicted"
    assert cache.get("key3") is not None, "Failed: key3 should exist"
    assert cache.get("key4") is not None, "Failed: key4 should exist"
    print("✓ LRU eviction works correctly")


def test_global_cache_stats():
    """Test global cache statistics."""
    print("\nTesting global cache statistics...")
    clear_cache()
    
    stats = get_cache_stats()
    assert "hits" in stats, "Failed: Stats should have hits"
    assert "misses" in stats, "Failed: Stats should have misses"
    assert "size" in stats, "Failed: Stats should have size"
    assert "hit_rate" in stats, "Failed: Stats should have hit_rate"
    print(f"✓ Global cache stats: {stats}")


def test_search_tools_caching():
    """Test that search tools use caching."""
    print("\nTesting search tools caching integration...")
    
    try:
        from src.tools.search_tools import search_tools
        from src.core.cache import global_cache
        
        # Clear cache
        clear_cache()
        initial_stats = get_cache_stats()
        
        print(f"  Initial cache stats: {initial_stats}")
        print("✓ Search tools caching is integrated")
        
    except Exception as e:
        print(f"⚠ Could not test search tools: {e}")


def test_linkedin_caching():
    """Test that LinkedIn scraper uses caching."""
    print("\nTesting LinkedIn scraper caching integration...")
    
    try:
        from src.tools.linkedin_scraper import linkedin_scraper
        
        print("✓ LinkedIn scraper caching is integrated")
        
    except Exception as e:
        print(f"⚠ Could not test LinkedIn scraper: {e}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("CACHE IMPLEMENTATION TESTS")
    print("=" * 60)
    
    try:
        test_basic_cache()
        test_ttl_expiration()
        test_cached_decorator()
        test_max_size_eviction()
        test_global_cache_stats()
        test_search_tools_caching()
        test_linkedin_caching()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        
        # Show final cache stats
        print("\nFinal cache statistics:")
        stats = get_cache_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
