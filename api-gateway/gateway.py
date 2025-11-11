"""
DBPower API Gateway - Main Application.

Centralized routing, authentication, and rate limiting for all DBPower services.
"""
import logging
import sys
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from config import get_config
from core.rate_limiter import RateLimiter
from core.proxy import ProxyClient
from middleware.auth_middleware import AuthMiddleware
from middleware.rate_limit_middleware import RateLimitMiddleware
from middleware.logging_middleware import LoggingMiddleware


# Configure logging
def setup_logging(log_level: str):
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


# Global instances
rate_limiter: Optional[RateLimiter] = None
proxy_client: Optional[ProxyClient] = None
redis_client: Optional[redis.Redis] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    Args:
        app: FastAPI application instance
    """
    global rate_limiter, proxy_client, redis_client

    # Startup
    config = get_config()
    setup_logging(config.log_level)

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Starting DBPower API Gateway")
    logger.info("=" * 60)
    logger.info(f"Service: {config.service_name}")
    logger.info(f"Host: {config.host}:{config.port}")
    logger.info(f"Backend: {config.backend_url}")
    logger.info(f"AI Analyzer: {config.ai_analyzer_url}")
    logger.info(f"Authentication: {'Enabled' if config.require_authentication else 'Disabled'}")
    logger.info(f"Rate Limiting: {config.rate_limit.requests_per_minute} req/min")
    logger.info("=" * 60)

    # Initialize Redis
    if config.redis_enabled and REDIS_AVAILABLE:
        try:
            redis_client = redis.from_url(config.redis_url)
            redis_client.ping()
            logger.info("✓ Redis connected successfully")
        except Exception as e:
            logger.warning(f"⚠ Redis connection failed: {e}")
            logger.warning("⚠ Falling back to in-memory rate limiting")
            redis_client = None
    else:
        if not REDIS_AVAILABLE:
            logger.warning("⚠ Redis library not installed")
        logger.warning("⚠ Using in-memory rate limiting (not suitable for production)")
        redis_client = None

    # Initialize rate limiter
    rate_limiter = RateLimiter(redis_client, config.rate_limit)
    logger.info("✓ Rate limiter initialized")

    # Initialize proxy client
    proxy_client = ProxyClient(timeout=30)
    logger.info("✓ Proxy client initialized")

    logger.info("API Gateway is ready to accept requests")

    yield

    # Shutdown
    logger.info("Shutting down DBPower API Gateway")

    if proxy_client:
        await proxy_client.close()

    if redis_client:
        redis_client.close()


# Create FastAPI application
app = FastAPI(
    title="DBPower API Gateway",
    description="Centralized routing, authentication, and rate limiting for DBPower services",
    version="1.0.0",
    lifespan=lifespan
)

# Get configuration
config = get_config()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=config.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware (order matters!)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware, rate_limiter=rate_limiter)
app.add_middleware(AuthMiddleware)


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Service status
    """
    status = {
        "status": "healthy",
        "service": config.service_name,
        "version": "1.0.0",
        "backend": config.backend_url,
        "ai_analyzer": config.ai_analyzer_url,
        "redis": redis_client is not None
    }

    # Check backend health
    try:
        if proxy_client:
            response = await proxy_client.client.get(
                f"{config.backend_url}/health",
                timeout=5
            )
            status["backend_healthy"] = response.status_code == 200
    except Exception:
        status["backend_healthy"] = False

    # Check AI analyzer health
    try:
        if proxy_client:
            response = await proxy_client.client.get(
                f"{config.ai_analyzer_url}/api/v1/health",
                timeout=5
            )
            status["ai_analyzer_healthy"] = response.status_code == 200
    except Exception:
        status["ai_analyzer_healthy"] = False

    return status


# Rate limit info endpoint
@app.get("/rate-limit/info")
async def rate_limit_info(request: Request):
    """
    Get rate limit information for current user/organization.

    Returns:
        Rate limit statistics
    """
    org_id = getattr(request.state, 'organization_id', None)
    ip = request.client.host if request.client else None

    stats = rate_limiter.get_stats(
        organization_id=org_id,
        ip_address=ip
    )

    return stats


# Backend service proxy routes
@app.api_route("/api/v1/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_backend(request: Request, path: str):
    """
    Proxy requests to backend service.

    Args:
        request: Incoming request
        path: API path

    Returns:
        Proxied response from backend
    """
    target_url = f"{config.backend_url}/api/v1/{path}"

    # Add query parameters
    if request.url.query:
        target_url += f"?{request.url.query}"

    return await proxy_client.forward_request(request, target_url)


# AI Analyzer service proxy routes
@app.api_route("/analyzer/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_ai_analyzer(request: Request, path: str):
    """
    Proxy requests to AI Analyzer service.

    Args:
        request: Incoming request
        path: API path

    Returns:
        Proxied response from AI Analyzer
    """
    target_url = f"{config.ai_analyzer_url}/api/v1/{path}"

    # Add query parameters
    if request.url.query:
        target_url += f"?{request.url.query}"

    return await proxy_client.forward_request(request, target_url)


# Admin endpoint for rate limit reset
@app.post("/admin/rate-limit/reset")
async def reset_rate_limits(
    request: Request,
    organization_id: Optional[int] = None,
    ip_address: Optional[str] = None
):
    """
    Reset rate limits (admin only).

    Args:
        request: Request
        organization_id: Organization ID to reset
        ip_address: IP address to reset

    Returns:
        Success message
    """
    # Check if user is admin
    role = getattr(request.state, 'role', None)
    if role not in ['super_admin', 'org_admin']:
        return JSONResponse(
            status_code=403,
            content={"error": "Forbidden", "message": "Admin access required"}
        )

    rate_limiter.reset(
        organization_id=organization_id,
        ip_address=ip_address
    )

    return {"status": "success", "message": "Rate limits reset successfully"}


if __name__ == "__main__":
    import uvicorn

    config = get_config()

    uvicorn.run(
        "gateway:app",
        host=config.host,
        port=config.port,
        workers=config.workers,
        log_level=config.log_level.lower(),
        access_log=True
    )
