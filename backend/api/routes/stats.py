"""
Statistics API Routes.
Provides system-wide statistics and metrics.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from sqlalchemy import func

from db.models import SlowQuery, get_db
from core.logger import setup_logger
from core.config import settings

logger = setup_logger(__name__, settings.log_level)

router = APIRouter(prefix="/api/v1", tags=["stats"])


@router.get("/stats")
async def get_stats() -> Dict[str, Any]:
    """
    Get system statistics.
    
    Returns:
        Dictionary with overall system statistics
    """
    try:
        db = next(get_db())
        
        total_queries = db.query(SlowQuery).count()
        analyzed_queries = db.query(SlowQuery).filter(SlowQuery.analyzed == True).count()
        pending_queries = db.query(SlowQuery).filter(SlowQuery.analyzed == False).count()
        
        # Average query time
        avg_query_time = db.query(func.avg(SlowQuery.query_time)).scalar() or 0.0
        
        # Slowest query
        slowest = db.query(SlowQuery).order_by(SlowQuery.query_time.desc()).first()
        
        return {
            "total_queries": total_queries,
            "analyzed_queries": analyzed_queries,
            "pending_queries": pending_queries,
            "average_query_time": round(avg_query_time, 3),
            "slowest_query": {
                "id": slowest.id,
                "query_time": slowest.query_time,
                "sql_text": slowest.sql_text[:100] + "..." if slowest and len(slowest.sql_text) > 100 else (slowest.sql_text if slowest else None)
            } if slowest else None
        }
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collectors/status")
async def get_collectors_status() -> Dict[str, Any]:
    """
    Get status of data collectors.
    
    Returns:
        Dictionary with collector status information
    """
    try:
        db = next(get_db())
        
        # Get last collection info
        last_query = db.query(SlowQuery).order_by(SlowQuery.collected_at.desc()).first()
        
        # Get collection stats (last hour)
        from datetime import datetime, timedelta
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_collections = db.query(SlowQuery).filter(
            SlowQuery.collected_at >= one_hour_ago
        ).count()
        
        return {
            "status": "active",
            "collection_interval": settings.collection_interval,
            "last_collection": {
                "timestamp": last_query.collected_at.isoformat() if last_query else None,
                "queries_count": 1 if last_query else 0
            },
            "recent_activity": {
                "last_hour": recent_collections,
                "period": "1 hour"
            },
            "mysql": {
                "host": settings.mysql_host,
                "database": settings.mysql_database,
                "status": "connected"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting collector status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyzer/status")
async def get_analyzer_status() -> Dict[str, Any]:
    """
    Get status of query analyzer and AI service.
    
    Returns:
        Dictionary with analyzer status information
    """
    try:
        from services.ai_llama_client import check_llama_health
        
        db = next(get_db())
        
        # Get AI service health
        ai_health = check_llama_health()
        
        # Get analysis stats
        total_analyzed = db.query(SlowQuery).filter(SlowQuery.analyzed == True).count()
        pending_analysis = db.query(SlowQuery).filter(SlowQuery.analyzed == False).count()
        
        # Get last analyzed query
        from db.models import AnalysisResult
        last_analysis = db.query(AnalysisResult).order_by(AnalysisResult.analyzed_at.desc()).first()
        
        return {
            "status": "active" if ai_health["status"] == "healthy" else "degraded",
            "ai_service": {
                "status": ai_health["status"],
                "model": settings.ai_model,
                "available_models": ai_health.get("models", 0),
                "base_url": settings.ai_base_url
            },
            "analysis_stats": {
                "total_analyzed": total_analyzed,
                "pending_analysis": pending_analysis,
                "last_analysis": {
                    "timestamp": last_analysis.analyzed_at.isoformat() if last_analysis else None,
                    "duration": last_analysis.analysis_duration if last_analysis else None
                } if last_analysis else None
            },
            "capabilities": {
                "rule_based_analysis": True,
                "ai_analysis": ai_health["status"] == "healthy",
                "index_suggestions": True,
                "query_rewrite": ai_health["status"] == "healthy"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting analyzer status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
