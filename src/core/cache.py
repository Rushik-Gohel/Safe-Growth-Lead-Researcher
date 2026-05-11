"""Centralized caching module with TTL support and statistics."""

import time
import hashlib
import logging
from typing import Any, Optional, Callable, Dict
from dataclasses import dataclass, field
from functools import wraps
from threading import Lock

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with TTL support."""
    
    value: Any
    timestamp: float
    ttl: int
    hits: int = 0
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() - self.timestamp > self.ttl
    
    def get_age(self) -> float:
        """Get age of cache entry in seconds."""
        return time.time() - self.timestamp


@dataclass
class CacheStats:
    """Cache statistics."""
    
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "size": self.size,
            "hit_rate": f"{self.hit_rate:.2f}%"
        }


class TTLCache:
    """
    Thread-safe cache with Time-To-Live (TTL) support.
    
    Features:
    - Automatic expiration based on TTL
    - LRU eviction when max size is reached
    - Thread-safe operations
    - Cache statistics tracking
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize TTL cache.
        
        Args:
            max_size: Maximum number of entries
            default_ttl: Default TTL in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = Lock()
        self._stats = CacheStats()
        
        logger.info(f"TTLCache initialized: max_size={max_size}, default_ttl={default_ttl}s")
    
    def _generate_key(self, *args, **kwargs) -> str:
        """
        Generate cache key from arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Cache key string
        """
        # Create a string representation of arguments
        key_parts = [str(arg) for arg in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_str = "|".join(key_parts)
        
        # Hash for consistent key length
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _evict_expired(self) -> None:
        """Remove expired entries."""
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
            self._stats.evictions += 1
        
        if expired_keys:
            logger.debug(f"Evicted {len(expired_keys)} expired entries")
    
    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._cache:
            return
        
        # Find entry with oldest timestamp and lowest hits
        lru_key = min(
            self._cache.keys(),
            key=lambda k: (self._cache[k].hits, self._cache[k].timestamp)
        )
        
        del self._cache[lru_key]
        self._stats.evictions += 1
        logger.debug(f"Evicted LRU entry: {lru_key}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats.misses += 1
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._stats.misses += 1
                self._stats.evictions += 1
                return None
            
            entry.hits += 1
            self._stats.hits += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if None)
        """
        with self._lock:
            # Evict expired entries first
            self._evict_expired()
            
            # Evict LRU if at max size
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_lru()
            
            # Store entry
            self._cache[key] = CacheEntry(
                value=value,
                timestamp=time.time(),
                ttl=ttl or self.default_ttl
            )
            
            self._stats.size = len(self._cache)
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._stats.size = 0
            logger.info("Cache cleared")
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            self._stats.size = len(self._cache)
            return self._stats
    
    def get_entry_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a cache entry.
        
        Args:
            key: Cache key
            
        Returns:
            Entry information or None
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            
            return {
                "age": entry.get_age(),
                "ttl": entry.ttl,
                "hits": entry.hits,
                "expired": entry.is_expired()
            }


def cached(ttl: Optional[int] = None, key_prefix: str = ""):
    """
    Decorator for caching function results with TTL.
    
    Args:
        ttl: Time-to-live in seconds (uses default if None)
        key_prefix: Prefix for cache keys
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Skip caching if disabled
            if not settings.enable_caching:
                logger.debug(f"Caching disabled, executing {func.__name__} without cache")
                return func(*args, **kwargs)
            
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{global_cache._generate_key(*args, **kwargs)}"
            
            # Try to get from cache
            cached_value = global_cache.get(cache_key)
            if cached_value is not None:
                logger.info(f"✓ Cache HIT: {func.__name__} (key: {cache_key[:50]}...)")
                return cached_value
            
            # Execute function
            logger.info(f"✗ Cache MISS: {func.__name__} - executing function")
            result = func(*args, **kwargs)
            
            # Store in cache
            global_cache.set(cache_key, result, ttl=ttl or settings.cache_ttl)
            logger.info(f"✓ Cached result for {func.__name__} (TTL: {ttl or settings.cache_ttl}s)")
            
            return result
        
        return wrapper
    return decorator


# Global cache instance
global_cache = TTLCache(
    max_size=settings.cache_max_size,
    default_ttl=settings.cache_ttl
)


def get_cache_stats() -> Dict[str, Any]:
    """
    Get global cache statistics.
    
    Returns:
        Cache statistics dictionary
    """
    return global_cache.get_stats().to_dict()


def clear_cache() -> None:
    """Clear global cache."""
    global_cache.clear()


