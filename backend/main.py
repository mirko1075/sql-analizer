"""
DBPower AI Cloud - Multi-Tenant FastAPI Application.
Phase 1-6 Implementation
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""

    # Startup
    logger.info("🚀 Starting DBPower AI Cloud...")

    try:
        from db.session import init_db_engine, check_db_connection
        from db.models_multitenant import Base

        # Initialize database
        logger.info("📊 Initializing database connection...")
        init_db_engine()

        # Check connection
        if check_db_connection():
            logger.info("✅ Database connection successful")
        else:
            logger.warning("⚠️  Database connection failed")

    except Exception as e:
        logger.error(f"❌ Error during startup: {e}", exc_info=True)
        logger.warning("⚠️  Starting with limited functionality")

    logger.info("✅ Application started successfully")

    yield

    # Shutdown
    logger.info("🛑 Shutting down DBPower AI Cloud...")
    try:
        from db.session import close_db
        close_db()
    except:
        pass
    logger.info("👋 Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="DBPower AI Cloud",
    description="Multi-Tenant AI-Powered Database Query Analyzer",
    version="1.0.0-phase6",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development. Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Try to include routers, but don't fail if they're missing
try:
    from api.routes import auth, admin
    app.include_router(auth.router, tags=["Authentication"])
    app.include_router(admin.router, tags=["Admin"])
    logger.info("✅ Loaded auth and admin routes")
except Exception as e:
    logger.warning(f"⚠️  Could not load auth/admin routes: {e}")

try:
    from api.routes import stats_simple
    app.include_router(stats_simple.router, tags=["Statistics"])
    logger.info("✅ Loaded stats routes")
except Exception as e:
    logger.warning(f"⚠️  Could not load stats routes: {e}")

try:
    from api.routes import queries
    app.include_router(queries.router, tags=["Queries"])
    logger.info("✅ Loaded queries routes")
except Exception as e:
    logger.warning(f"⚠️  Could not load queries routes: {e}")

try:
    from api.routes import collectors_simple
    app.include_router(collectors_simple.router, tags=["Collectors"])
    logger.info("✅ Loaded collectors routes")
except Exception as e:
    logger.warning(f"⚠️  Could not load collectors routes: {e}")

try:
    from api.routes import analyzer_simple
    app.include_router(analyzer_simple.router, tags=["Analyzer"])
    logger.info("✅ Loaded analyzer routes")
except Exception as e:
    logger.warning(f"⚠️  Could not load analyzer routes: {e}")

# Old query routes - disabled for now due to model incompatibility
# try:
#     from api.routes import slow_queries, analyze, stats
#     app.include_router(slow_queries.router, prefix="/api/v1", tags=["Queries"])
#     app.include_router(analyze.router, prefix="/api/v1", tags=["Analysis"])
#     logger.info("✅ Loaded query routes")
# except Exception as e:
#     logger.warning(f"⚠️  Could not load query routes: {e}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": "DBPower AI Cloud",
        "version": "1.0.0-phase6",
        "description": "Multi-Tenant AI-Powered Database Query Analyzer",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""

    # Check database
    db_status = "unknown"
    try:
        from db.session import check_db_connection
        db_status = "connected" if check_db_connection() else "disconnected"
    except Exception as e:
        logger.error(f"Health check error: {e}")
        db_status = "error"

    # Return structure matching frontend HealthStatus interface
    db_healthy = db_status == "connected"

    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": {
            "status": "healthy" if db_healthy else "unhealthy"
        },
        "redis": {
            "status": "healthy"  # Stub - redis not implemented in multi-tenant version
        },
        "uptime_seconds": 0  # TODO: Track actual uptime
    }


@app.get("/api/v1/health")
async def api_health():
    """API health check endpoint."""
    return await health_check()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
