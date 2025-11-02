"""
AI Query Analyzer - FastAPI Backend Application

Main entry point for the FastAPI application.
"""
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.core.config import settings
from backend.core.logger import get_logger
from backend.db.session import check_db_connection, init_db
from backend.api.routes import slow_queries, stats, collectors, analyzer, statistics, auth, database_connections, teams, users, organizations, onboarding
from backend.services.scheduler import start_scheduler, stop_scheduler

logger = get_logger(__name__)

# Application startup timestamp
APP_START_TIME = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.

    Handles startup and shutdown logic.
    """
    # Startup
    logger.info("=" * 60)
    logger.info("AI Query Analyzer Backend Starting...")
    logger.info(f"Environment: {settings.env}")
    logger.info(f"Version: {app.version}")
    logger.info("=" * 60)

    # Initialize database
    try:
        logger.info("Checking database connection...")
        if check_db_connection():
            logger.info("✓ Database connection successful")

            # Initialize tables if needed (creates tables if they don't exist)
            logger.info("Initializing database schema...")
            init_db()
            logger.info("✓ Database schema ready")
        else:
            logger.error("✗ Database connection failed")
            logger.warning("Application starting with database issues")

    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        logger.warning("Application starting with database issues")

    logger.info("=" * 60)
    logger.info("✓ Application startup complete")
    logger.info("=" * 60)

    # Start collector scheduler (5 minute interval)
    try:
        logger.info("Starting collector scheduler...")
        start_scheduler(interval_minutes=5)
        logger.info("✓ Collector scheduler started")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        logger.warning("Application starting without scheduler")

    yield

    # Shutdown
    logger.info("=" * 60)
    logger.info("AI Query Analyzer Backend Shutting Down...")
    logger.info("=" * 60)

    # Stop scheduler
    try:
        logger.info("Stopping collector scheduler...")
        stop_scheduler()
        logger.info("✓ Scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")

    # Close database connections
    try:
        from backend.db.session import close_db_connections
        close_db_connections()
        logger.info("✓ Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")

    logger.info("✓ Shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:80",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        # Add production origins as needed
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    start_time = time.time()

    # Log request
    logger.info(f"→ {request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Log response
    duration = time.time() - start_time
    logger.info(
        f"← {request.method} {request.url.path} "
        f"[{response.status_code}] {duration:.3f}s"
    )

    return response


# Exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "detail": exc.errors(),
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Check the health status of the application"
)
async def health_check():
    """
    Health check endpoint.

    Returns the status of the application and its dependencies.
    """
    uptime = time.time() - APP_START_TIME

    # Check database
    db_status = "healthy" if check_db_connection() else "unhealthy"

    # Check Redis (simple check)
    redis_status = "unknown"
    try:
        import redis
        r = redis.from_url(settings.get_redis_url())
        r.ping()
        redis_status = "healthy"
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        redis_status = "unhealthy"

    # Determine overall status
    if db_status == "healthy" and redis_status == "healthy":
        overall_status = "healthy"
    elif db_status == "unhealthy":
        overall_status = "unhealthy"
    else:
        overall_status = "degraded"

    return {
        "status": overall_status,
        "version": settings.api_version,
        "environment": settings.env,
        "database": {
            "status": db_status,
            "host": settings.internal_db.host,
            "port": settings.internal_db.port,
        },
        "redis": {
            "status": redis_status,
            "host": settings.redis_host,
            "port": settings.redis_port,
        },
        "uptime_seconds": round(uptime, 2),
        "timestamp": datetime.utcnow().isoformat(),
    }


# Root endpoint
@app.get(
    "/",
    tags=["Root"],
    summary="API root",
    description="Get API information"
)
async def root():
    """
    API root endpoint.

    Returns basic information about the API.
    """
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "description": settings.api_description,
        "docs_url": "/docs",
        "health_url": "/health",
        "timestamp": datetime.utcnow().isoformat(),
    }


# Include routers
app.include_router(auth.router, prefix="/api/v1")  # Authentication routes
app.include_router(users.router, prefix="/api/v1")  # User profile management
app.include_router(organizations.router, prefix="/api/v1")  # Organization management
app.include_router(database_connections.router, prefix="/api/v1")  # Database connections management
app.include_router(teams.router, prefix="/api/v1")  # Team management
app.include_router(onboarding.router, prefix="/api/v1")  # Onboarding wizard
app.include_router(slow_queries.router, prefix="/api/v1")
app.include_router(stats.router, prefix="/api/v1")
app.include_router(collectors.router, prefix="/api/v1")
app.include_router(analyzer.router, prefix="/api/v1")
app.include_router(statistics.router, prefix="/api/v1")

# Log registered routes on startup
@app.on_event("startup")
async def log_routes():
    """Log all registered routes."""
    logger.info("Registered routes:")
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = ', '.join(sorted(route.methods))
            logger.info(f"  {methods:10s} {route.path}")


if __name__ == "__main__":
    # This allows running the app directly with `python main.py`
    # For production, use: uvicorn backend.main:app --host 0.0.0.0 --port 8000
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload in development
        log_level="info",
    )
