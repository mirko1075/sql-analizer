"""
DBPower AI Analyzer - Main Application.

Standalone microservice for SQL query analysis using AI models.
Supports both cloud models (OpenAI) and on-premise models (Ollama).
"""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from config import get_config
from analyzer.factory import get_analyzer
from api.routes import router


# Configure logging
def setup_logging(log_level: str):
    """Configure application logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    Args:
        app: FastAPI application instance
    """
    # Startup
    config = get_config()
    setup_logging(config.log_level)

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Starting DBPower AI Analyzer Service")
    logger.info("=" * 60)
    logger.info(f"Service: {config.service_name}")
    logger.info(f"Host: {config.host}:{config.port}")
    logger.info(f"Model Provider: {config.model.provider.value}")
    logger.info(f"Model Name: {config.model.model_name}")
    logger.info(f"Authentication: {'Enabled' if config.require_authentication else 'Disabled'}")
    logger.info("=" * 60)

    # Initialize analyzer
    try:
        analyzer = get_analyzer(config.model)
        logger.info("✓ Analyzer initialized successfully")

        # Health check for local models
        if config.model.provider.value == "ollama":
            if hasattr(analyzer, 'check_health'):
                if analyzer.check_health():
                    logger.info("✓ Local model health check passed")
                else:
                    logger.warning("⚠ Local model health check failed - service may not work correctly")
    except Exception as e:
        logger.error(f"✗ Failed to initialize analyzer: {e}")
        logger.error("Service will start but analysis requests will fail")

    logger.info("Service is ready to accept requests")

    yield

    # Shutdown
    logger.info("Shutting down DBPower AI Analyzer Service")


# Create FastAPI application
app = FastAPI(
    title="DBPower AI Analyzer",
    description="SQL query performance analysis using AI models",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
config = get_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["analyzer"])


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to API docs."""
    return RedirectResponse(url="/docs")


@app.get("/version")
async def version():
    """Get service version information."""
    return {
        "service": "dbpower-ai-analyzer",
        "version": "1.0.0",
        "model_provider": config.model.provider.value,
        "model_name": config.model.model_name
    }


if __name__ == "__main__":
    import uvicorn

    config = get_config()

    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        workers=config.workers,
        log_level=config.log_level.lower(),
        access_log=True
    )
