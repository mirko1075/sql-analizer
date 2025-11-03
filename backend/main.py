"""
DBPower Base LLaMA Edition - FastAPI Application.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager

from core.config import settings
from core.logger import setup_logger
from db.models import init_db
from services.collector import collect_slow_queries
from services.ai_llama_client import ensure_model_loaded, check_llama_health
from api.routes import slow_queries, analyze, stats

logger = setup_logger(__name__, settings.log_level)


# Background task for periodic collection
async def periodic_collector():
    """Run slow query collection periodically."""
    while True:
        try:
            logger.info("Running periodic slow query collection...")
            result = collect_slow_queries()
            logger.info(f"Collection completed: {result.get('collected', 0)} queries collected")
        except Exception as e:
            logger.error(f"Error in periodic collection: {e}", exc_info=True)
        
        # Wait for configured interval (default: 5 minutes)
        await asyncio.sleep(settings.collection_interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    
    # Startup
    logger.info("🚀 Starting DBPower Base LLaMA Edition...")
    
    # Initialize database
    logger.info("📊 Initializing SQLite database...")
    init_db()
    
    # Check LLaMA service health
    logger.info("🧠 Checking AI (LLaMA) service health...")
    health = check_llama_health()
    if health["status"] == "healthy":
        logger.info(f"✅ AI service is healthy - {health['models']} models available")
        
        # Ensure model is loaded
        logger.info(f"🔄 Ensuring model '{settings.ai_model}' is loaded...")
        ensure_model_loaded()
        logger.info("✅ Model ready for analysis")
    else:
        logger.warning(f"⚠️  AI service not ready: {health['message']}")
        logger.warning("Analysis will be limited to rule-based checks only")
    
    # Start background collection task
    logger.info(f"⏱️  Starting periodic collection (every {settings.collection_interval}s)...")
    collection_task = asyncio.create_task(periodic_collector())
    
    logger.info("✅ Application started successfully")
    logger.info(f"📡 API available at http://0.0.0.0:{settings.api_port}")
    logger.info(f"🔍 Monitoring MySQL at {settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down DBPower Base...")
    collection_task.cancel()
    try:
        await collection_task
    except asyncio.CancelledError:
        pass
    logger.info("👋 Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="DBPower Base LLaMA Edition",
    description="AI-Powered MySQL Query Analyzer with Local LLaMA Model",
    version="1.0.0",
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

# Include routers
app.include_router(slow_queries.router)
app.include_router(analyze.router)
app.include_router(stats.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app": "DBPower Base LLaMA Edition",
        "version": "1.0.0",
        "description": "AI-Powered MySQL Query Analyzer with Local LLaMA Model",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    
    # Check AI service
    ai_health = check_llama_health()
    
    return {
        "status": "healthy",
        "mysql": {
            "host": settings.mysql_host,
            "database": settings.mysql_database,
            "status": "connected"
        },
        "ai": {
            "service": ai_health["status"],
            "model": settings.ai_model,
            "available_models": ai_health.get("models", 0)
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
