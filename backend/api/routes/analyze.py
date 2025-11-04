"""
Analysis API Routes.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any

from services.analyzer import analyze_query, get_analysis_result
from services.collector import collect_slow_queries
from core.logger import setup_logger
from core.config import settings

logger = setup_logger(__name__, settings.log_level)

router = APIRouter(prefix="/api/v1/analyze", tags=["analyze"])


@router.post("/collect")
async def trigger_collection() -> Dict[str, Any]:
    """
    Manually trigger slow query collection.
    
    Returns:
        Collection result with number of queries collected
    """
    try:
        result = collect_slow_queries()
        
        return {
            "status": "completed",
            "collected": result.get("collected", 0),
            "message": result.get("message", "Collection completed")
        }
        
    except Exception as e:
        logger.error(f"Error triggering collection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{query_id}")
async def trigger_analysis(query_id: int) -> Dict[str, Any]:
    """
    Trigger analysis for a specific slow query.
    
    Path Parameters:
        query_id: ID of the slow query to analyze
    
    Returns:
        Analysis result or job status
    """
    try:
        # Run analysis asynchronously
        result = await analyze_query(query_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "completed",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering analysis for query {query_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{query_id}")
async def get_analysis(query_id: int) -> Dict[str, Any]:
    """
    Get analysis result for a query.
    
    Path Parameters:
        query_id: ID of the slow query
    
    Returns:
        Analysis result with issues, suggestions, and AI insights
    """
    try:
        result = get_analysis_result(query_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis not found for query {query_id}. Query may not have been analyzed yet."
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis for query {query_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
