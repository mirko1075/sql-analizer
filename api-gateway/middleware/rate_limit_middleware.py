"""
Rate limiting middleware for FastAPI.
"""
import logging
from typing import Callable, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting requests.

    Supports:
    - Per-organization rate limiting
    - Per-IP rate limiting
    - Proper HTTP 429 responses
    - Retry-After headers
    """

    def __init__(self, app, rate_limiter: Optional[RateLimiter] = None):
        """
        Initialize middleware.

        Args:
            app: FastAPI application
            rate_limiter: RateLimiter instance (can be None initially)
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response (429 if rate limited, otherwise forwarded response)
        """
        # Skip rate limiting if rate_limiter not initialized yet
        if self.rate_limiter is None:
            return await call_next(request)

        # Extract organization ID from request state (set by auth middleware)
        organization_id = getattr(request.state, 'organization_id', None)

        # Extract IP address
        ip_address = request.client.host if request.client else None

        # Check rate limit
        is_allowed, retry_after = self.rate_limiter.check_rate_limit(
            organization_id=organization_id,
            ip_address=ip_address
        )

        if not is_allowed:
            # Rate limit exceeded
            logger.warning(
                f"Rate limit exceeded - org: {organization_id}, IP: {ip_address}"
            )

            headers = {}
            if retry_after is not None:
                headers['Retry-After'] = str(retry_after)
                headers['X-RateLimit-Reset'] = str(retry_after)

            # Get current stats for headers
            stats = self.rate_limiter.get_stats(
                organization_id=organization_id,
                ip_address=ip_address
            )

            if stats.get('organization'):
                headers['X-RateLimit-Limit'] = str(stats['organization']['limit'])
                headers['X-RateLimit-Remaining'] = str(stats['organization']['remaining'])

            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Please retry after {retry_after} seconds.",
                    "retry_after": retry_after
                },
                headers=headers
            )

        # Request allowed - add rate limit headers to response
        response = await call_next(request)

        # Add rate limit info headers
        stats = self.rate_limiter.get_stats(
            organization_id=organization_id,
            ip_address=ip_address
        )

        if stats.get('organization'):
            response.headers['X-RateLimit-Limit'] = str(stats['organization']['limit'])
            response.headers['X-RateLimit-Remaining'] = str(stats['organization']['remaining'])

        return response
