"""
Slow Queries API Routes.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from datetime import datetime

from db.models import SlowQuery, get_db
from services.collector import get_all_queries, get_pending_queries
from core.logger import setup_logger
from core.config import settings

logger = setup_logger(__name__, settings.log_level)

router = APIRouter(prefix="/api/v1/slow-queries", tags=["slow-queries"])


@router.get("")
async def list_slow_queries(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    analyzed: Optional[bool] = None
) -> Dict[str, Any]:
    """
    List all collected slow queries with pagination.
    
    Query Parameters:
        skip: Number of records to skip (default: 0)
        limit: Number of records to return (default: 50, max: 500)
        analyzed: Filter by analyzed status (optional)
    
    Returns:
        Dictionary with queries list and pagination info
    """
    try:
        db = next(get_db())
        
        # Build query
        query = db.query(SlowQuery)
        
        if analyzed is not None:
            query = query.filter(SlowQuery.analyzed == analyzed)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        queries = query.order_by(SlowQuery.collected_at.desc()).offset(skip).limit(limit).all()
        
        # Format response
        queries_data = []
        for q in queries:
            queries_data.append({
                "id": q.id,
                "sql_fingerprint": q.sql_fingerprint,
                "sql_text": q.sql_text[:200] + "..." if len(q.sql_text) > 200 else q.sql_text,  # Truncate for list view
                "query_time": q.query_time,
                "rows_examined": q.rows_examined,
                "rows_sent": q.rows_sent,
                "database_name": q.database_name,
                "analyzed": q.analyzed,
                "detected_at": q.collected_at.isoformat() if q.collected_at else None
            })
        
        return {
            "queries": queries_data,
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": (skip + limit) < total
        }
        
    except Exception as e:
        logger.error(f"Error listing slow queries: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{query_id}")
async def get_slow_query(query_id: int) -> Dict[str, Any]:
    """
    Get details of a specific slow query.
    
    Path Parameters:
        query_id: ID of the slow query
    
    Returns:
        Slow query details with full SQL text
    """
    try:
        db = next(get_db())
        
        slow_query = db.query(SlowQuery).filter(SlowQuery.id == query_id).first()
        
        if not slow_query:
            raise HTTPException(status_code=404, detail=f"Query with ID {query_id} not found")
        
        return {
            "id": slow_query.id,
            "sql_fingerprint": slow_query.sql_fingerprint,
            "sql_text": slow_query.sql_text,
            "query_time": slow_query.query_time,
            "lock_time": slow_query.lock_time,
            "rows_examined": slow_query.rows_examined,
            "rows_sent": slow_query.rows_sent,
            "database_name": slow_query.database_name,
            "user_host": slow_query.user_host,
            "analyzed": slow_query.analyzed,
            "analysis_result_id": slow_query.analysis_result_id,
            "detected_at": slow_query.collected_at.isoformat() if slow_query.collected_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting slow query {query_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_summary_stats() -> Dict[str, Any]:
    """
    Get summary statistics for slow queries.
    
    Returns:
        Dictionary with various statistics
    """
    try:
        db = next(get_db())
        
        total_queries = db.query(SlowQuery).count()
        analyzed_queries = db.query(SlowQuery).filter(SlowQuery.analyzed == True).count()
        pending_queries = db.query(SlowQuery).filter(SlowQuery.analyzed == False).count()
        
        # Average query time
        from sqlalchemy import func
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
        logger.error(f"Error getting summary stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
