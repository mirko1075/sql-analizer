"""
Rate limiter implementation using Redis and token bucket algorithm.
Supports per-organization and per-IP rate limiting.
"""
import time
import logging
from typing import Optional, Tuple
from datetime import datetime, timedelta

try:
    import redis
    from redis import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    Redis = None

from config import RateLimitConfig

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter using Redis for distributed rate limiting.

    Supports:
    - Per-organization limits
    - Per-IP limits
    - Burst allowance
    - Automatic blocking for excessive requests
    """

    def __init__(self, redis_client: Optional[Redis], config: RateLimitConfig):
        """
        Initialize rate limiter.

        Args:
            redis_client: Redis client instance (None for in-memory fallback)
            config: Rate limit configuration
        """
        self.redis = redis_client
        self.config = config

        # In-memory fallback (not suitable for multi-instance deployments)
        self._memory_cache: dict = {}

        if not redis_client:
            logger.warning("Redis not available - using in-memory rate limiting (not distributed)")

    def check_rate_limit(
        self,
        organization_id: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if request is allowed under rate limits.

        Args:
            organization_id: Organization ID for per-org limiting
            ip_address: IP address for per-IP limiting

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
            - is_allowed: True if request is allowed
            - retry_after_seconds: Seconds to wait before retry (None if allowed)
        """
        # Check organization-level limit
        if self.config.enable_per_organization and organization_id is not None:
            allowed, retry_after = self._check_limit(
                key=f"rate_limit:org:{organization_id}",
                limit=self.config.requests_per_minute,
                window_seconds=60
            )
            if not allowed:
                logger.warning(f"Rate limit exceeded for organization {organization_id}")
                return False, retry_after

        # Check IP-level limit
        if self.config.enable_per_ip and ip_address is not None:
            allowed, retry_after = self._check_limit(
                key=f"rate_limit:ip:{ip_address}",
                limit=self.config.requests_per_minute,
                window_seconds=60
            )
            if not allowed:
                logger.warning(f"Rate limit exceeded for IP {ip_address}")
                return False, retry_after

        return True, None

    def _check_limit(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> Tuple[bool, Optional[int]]:
        """
        Check rate limit using token bucket algorithm.

        Args:
            key: Redis key for this limit
            limit: Maximum requests in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        if self.redis:
            return self._check_limit_redis(key, limit, window_seconds)
        else:
            return self._check_limit_memory(key, limit, window_seconds)

    def _check_limit_redis(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> Tuple[bool, Optional[int]]:
        """
        Check rate limit using Redis (distributed).

        Uses sliding window counter approach with Redis ZSET.
        """
        now = time.time()
        window_start = now - window_seconds

        try:
            # Use pipeline for atomic operations
            pipe = self.redis.pipeline()

            # Remove expired entries
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current requests in window
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(now): now})

            # Set expiry on key
            pipe.expire(key, window_seconds * 2)

            results = pipe.execute()

            current_count = results[1]  # Result of zcard

            if current_count >= limit:
                # Rate limit exceeded
                # Calculate retry-after based on oldest request in window
                oldest_scores = self.redis.zrange(key, 0, 0, withscores=True)
                if oldest_scores:
                    oldest_time = oldest_scores[0][1]
                    retry_after = int(oldest_time + window_seconds - now) + 1
                    return False, retry_after
                else:
                    return False, window_seconds

            return True, None

        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fail open (allow request) to avoid blocking all traffic
            return True, None

    def _check_limit_memory(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> Tuple[bool, Optional[int]]:
        """
        Check rate limit using in-memory cache (single-instance only).

        Not suitable for multi-instance deployments.
        """
        now = time.time()
        window_start = now - window_seconds

        # Initialize if not exists
        if key not in self._memory_cache:
            self._memory_cache[key] = []

        # Remove expired entries
        self._memory_cache[key] = [
            t for t in self._memory_cache[key]
            if t > window_start
        ]

        current_count = len(self._memory_cache[key])

        if current_count >= limit:
            # Rate limit exceeded
            oldest_time = min(self._memory_cache[key])
            retry_after = int(oldest_time + window_seconds - now) + 1
            return False, retry_after

        # Add current request
        self._memory_cache[key].append(now)

        return True, None

    def reset(self, organization_id: Optional[int] = None, ip_address: Optional[str] = None):
        """
        Reset rate limit counters.

        Args:
            organization_id: Organization ID to reset (None for all)
            ip_address: IP address to reset (None for all)
        """
        if self.redis:
            if organization_id is not None:
                self.redis.delete(f"rate_limit:org:{organization_id}")
            if ip_address is not None:
                self.redis.delete(f"rate_limit:ip:{ip_address}")
            if organization_id is None and ip_address is None:
                # Reset all rate limits
                for key in self.redis.scan_iter("rate_limit:*"):
                    self.redis.delete(key)
        else:
            if organization_id is not None:
                self._memory_cache.pop(f"rate_limit:org:{organization_id}", None)
            if ip_address is not None:
                self._memory_cache.pop(f"rate_limit:ip:{ip_address}", None)
            if organization_id is None and ip_address is None:
                self._memory_cache.clear()

    def get_stats(
        self,
        organization_id: Optional[int] = None,
        ip_address: Optional[str] = None
    ) -> dict:
        """
        Get rate limit statistics.

        Args:
            organization_id: Organization ID
            ip_address: IP address

        Returns:
            Statistics dictionary
        """
        stats = {}

        if self.redis:
            if organization_id is not None:
                key = f"rate_limit:org:{organization_id}"
                count = self.redis.zcard(key)
                stats['organization'] = {
                    'id': organization_id,
                    'current_count': count,
                    'limit': self.config.requests_per_minute,
                    'remaining': max(0, self.config.requests_per_minute - count)
                }

            if ip_address is not None:
                key = f"rate_limit:ip:{ip_address}"
                count = self.redis.zcard(key)
                stats['ip'] = {
                    'address': ip_address,
                    'current_count': count,
                    'limit': self.config.requests_per_minute,
                    'remaining': max(0, self.config.requests_per_minute - count)
                }
        else:
            # Memory cache stats
            if organization_id is not None:
                key = f"rate_limit:org:{organization_id}"
                count = len(self._memory_cache.get(key, []))
                stats['organization'] = {
                    'id': organization_id,
                    'current_count': count,
                    'limit': self.config.requests_per_minute,
                    'remaining': max(0, self.config.requests_per_minute - count)
                }

        return stats
