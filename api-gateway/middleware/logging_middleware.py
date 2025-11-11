"""
Logging middleware for API Gateway.
"""
import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from config import get_config

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging HTTP requests and responses.

    Logs:
    - Request method, path, and query parameters
    - Response status code and timing
    - User/organization information (if authenticated)
    - Errors and exceptions
    """

    def __init__(self, app):
        """
        Initialize middleware.

        Args:
            app: FastAPI application
        """
        super().__init__(app)
        self.config = get_config()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with logging.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response
        """
        # Skip logging if disabled
        if not self.config.log_requests:
            return await call_next(request)

        start_time = time.time()

        # Extract request info
        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""

        # Extract user info if available (set by auth middleware)
        user_id = getattr(request.state, 'user_id', None)
        org_id = getattr(request.state, 'organization_id', None)

        # Log request
        log_message = f"{method} {path}"
        if query:
            log_message += f"?{query}"
        if org_id:
            log_message += f" | Org: {org_id}"
        if user_id:
            log_message += f" | User: {user_id}"

        logger.info(log_message)

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time
            duration_ms = round(duration * 1000, 2)

            # Log response
            logger.info(
                f"{method} {path} - {response.status_code} ({duration_ms}ms)"
            )

            # Add timing header
            response.headers['X-Response-Time'] = f"{duration_ms}ms"

            return response

        except Exception as e:
            # Log error
            duration = time.time() - start_time
            duration_ms = round(duration * 1000, 2)

            logger.error(
                f"{method} {path} - ERROR: {str(e)} ({duration_ms}ms)",
                exc_info=True
            )

            raise
