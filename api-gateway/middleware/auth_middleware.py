"""
Authentication middleware for FastAPI.
Validates JWT tokens from Phase 1-2 backend.
"""
import logging
from typing import Callable, Optional
import jwt
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config import get_config

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for JWT authentication.

    Validates tokens and extracts user/organization information.
    """

    # Paths that don't require authentication
    PUBLIC_PATHS = [
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register"
    ]

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
        Process request with authentication.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response (401 if unauthorized, otherwise forwarded response)
        """
        # Skip authentication for public paths
        if self._is_public_path(request.url.path):
            return await call_next(request)

        # Skip authentication if disabled
        if not self.config.require_authentication:
            return await call_next(request)

        # Extract token from Authorization header
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return self._unauthorized_response("Missing Authorization header")

        # Parse Bearer token
        parts = auth_header.split()

        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return self._unauthorized_response("Invalid Authorization header format")

        token = parts[1]

        # Validate token
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret_key,
                algorithms=[self.config.jwt_algorithm]
            )

            # Extract user information
            request.state.user_id = payload.get('user_id')
            request.state.organization_id = payload.get('org_id')
            request.state.team_id = payload.get('team_id')
            request.state.identity_id = payload.get('identity_id')
            request.state.role = payload.get('role')

            logger.debug(
                f"Authenticated user {request.state.user_id} "
                f"from org {request.state.organization_id}"
            )

        except jwt.ExpiredSignatureError:
            return self._unauthorized_response("Token has expired")

        except jwt.InvalidTokenError as e:
            return self._unauthorized_response(f"Invalid token: {str(e)}")

        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return self._unauthorized_response("Authentication failed")

        # Continue to next middleware/handler
        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        """
        Check if path is public (doesn't require authentication).

        Args:
            path: Request path

        Returns:
            True if path is public
        """
        for public_path in self.PUBLIC_PATHS:
            if path.startswith(public_path):
                return True
        return False

    def _unauthorized_response(self, message: str) -> JSONResponse:
        """
        Create 401 Unauthorized response.

        Args:
            message: Error message

        Returns:
            JSONResponse with 401 status
        """
        return JSONResponse(
            status_code=401,
            content={
                "error": "Unauthorized",
                "message": message
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
