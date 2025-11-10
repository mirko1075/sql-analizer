"""
Slow Queries API Routes.
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel

from db.models import SlowQuery, get_db
from services.collector import get_all_queries, get_pending_queries
from core.logger import setup_logger
from core.config import settings

logger = setup_logger(__name__, settings.log_level)

router = APIRouter(prefix="/api/v1/slow-queries", tags=["slow-queries"])


class StatusUpdate(BaseModel):
    """Request body for status update."""
    status: str  # pending, analyzed, archived, resolved


@router.get("")
async def list_slow_queries(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    analyzed: Optional[bool] = None,
    status: Optional[str] = Query(None, regex="^(pending|analyzed|archived|resolved)$"),
    query_text: Optional[str] = Query(None, description="Search in SQL query text"),
    database: Optional[str] = Query(None, description="Filter by database name"),
    priority: Optional[str] = Query(None, regex="^(low|medium|high|critical)$", description="Filter by priority"),
    min_query_time: Optional[float] = Query(None, ge=0, description="Minimum query time in seconds"),
    max_query_time: Optional[float] = Query(None, ge=0, description="Maximum query time in seconds"),
    min_rows_examined: Optional[int] = Query(None, ge=0, description="Minimum rows examined"),
    max_rows_examined: Optional[int] = Query(None, ge=0, description="Maximum rows examined")
) -> Dict[str, Any]:
    """
    List all collected slow queries with pagination and filtering.
    
    Query Parameters:
        skip: Number of records to skip (default: 0)
        limit: Number of records to return (default: 50, max: 500)
        analyzed: Filter by analyzed status (optional, deprecated - use status instead)
        status: Filter by status: pending, analyzed, archived, resolved (optional)
        query_text: Search in SQL query text (case-insensitive, partial match)
        database: Filter by database name (exact match)
        priority: Filter by priority: low, medium, high, critical (based on query_time)
        min_query_time: Minimum query execution time in seconds
        max_query_time: Maximum query execution time in seconds
        min_rows_examined: Minimum number of rows examined
        max_rows_examined: Maximum number of rows examined
    
    Returns:
        Dictionary with queries list and pagination info
    """
    try:
        db = next(get_db())
        
        # Build query
        query = db.query(SlowQuery)
        
        # Status filter (preferred)
        if status:
            query = query.filter(SlowQuery.status == status)
        # Backward compatibility with analyzed filter
        elif analyzed is not None:
            query = query.filter(SlowQuery.analyzed == analyzed)
        # Default: show only pending and analyzed (not archived/resolved)
        else:
            query = query.filter(SlowQuery.status.in_(['pending', 'analyzed']))
        
        # SQL text search filter
        if query_text:
            query = query.filter(SlowQuery.sql_text.ilike(f"%{query_text}%"))
        
        # Database filter
        if database:
            query = query.filter(SlowQuery.database_name == database)
        
        # Query time range filters
        if min_query_time is not None:
            query = query.filter(SlowQuery.query_time >= min_query_time)
        if max_query_time is not None:
            query = query.filter(SlowQuery.query_time <= max_query_time)
        
        # Rows examined range filters
        if min_rows_examined is not None:
            query = query.filter(SlowQuery.rows_examined >= min_rows_examined)
        if max_rows_examined is not None:
            query = query.filter(SlowQuery.rows_examined <= max_rows_examined)
        
        # Priority filter (based on query_time thresholds)
        if priority:
            if priority == "critical":
                query = query.filter(SlowQuery.query_time > 5.0)
            elif priority == "high":
                query = query.filter(SlowQuery.query_time > 2.0, SlowQuery.query_time <= 5.0)
            elif priority == "medium":
                query = query.filter(SlowQuery.query_time > 1.0, SlowQuery.query_time <= 2.0)
            elif priority == "low":
                query = query.filter(SlowQuery.query_time <= 1.0)
        
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
                "status": q.status,
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
            "status": slow_query.status,
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


@router.patch("/{query_id}/status")
async def update_query_status(
    query_id: int,
    status_update: StatusUpdate
) -> Dict[str, Any]:
    """
    Update the status of a slow query.
    
    Path Parameters:
        query_id: ID of the slow query
    
    Request Body:
        status: New status (pending, analyzed, archived, resolved)
    
    Returns:
        Updated query information
    """
    try:
        # Validate status
        valid_statuses = ['pending', 'analyzed', 'archived', 'resolved']
        if status_update.status not in valid_statuses:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        db = next(get_db())
        
        slow_query = db.query(SlowQuery).filter(SlowQuery.id == query_id).first()
        
        if not slow_query:
            raise HTTPException(status_code=404, detail=f"Query with ID {query_id} not found")
        
        # Update status
        old_status = slow_query.status
        slow_query.status = status_update.status
        
        # Also update analyzed flag for backward compatibility
        if status_update.status == 'analyzed':
            slow_query.analyzed = True
        
        db.commit()
        
        logger.info(f"Query {query_id} status updated: {old_status} -> {status_update.status}")
        
        return {
            "id": slow_query.id,
            "old_status": old_status,
            "new_status": slow_query.status,
            "message": f"Query status updated to {slow_query.status}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating query status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{query_id}/archive")
async def archive_query(query_id: int) -> Dict[str, Any]:
    """
    Quick endpoint to archive a query (mark as not interesting).
    
    Path Parameters:
        query_id: ID of the slow query
    
    Returns:
        Confirmation message
    """
    return await update_query_status(query_id, StatusUpdate(status='archived'))


@router.post("/{query_id}/resolve")
async def resolve_query(query_id: int) -> Dict[str, Any]:
    """
    Quick endpoint to resolve a query (mark as fixed/acknowledged).

    Path Parameters:
        query_id: ID of the slow query

    Returns:
        Confirmation message
    """
    return await update_query_status(query_id, StatusUpdate(status='resolved'))


@router.post("/cleanup/agent-queries")
async def cleanup_agent_queries() -> Dict[str, Any]:
    """
    Clean up queries from the monitoring agent (EXPLAIN, DESCRIBE, SHOW, etc.).
    This removes queries that are part of the analysis process, not actual application queries.

    Returns:
        Count of deleted queries
    """
    try:
        db = next(get_db())

        # Patterns to match agent queries
        agent_patterns = [
            'EXPLAIN%',
            'DESCRIBE%',
            'DESC %',
            'SHOW INDEX%',
            'SHOW TABLE STATUS%',
            'SHOW FULL PROCESSLIST%',
            'SHOW TABLES%',
            'SHOW DATABASES%',
            '%FROM mysql.slow_log%',
            '%mysql.slow_log%',
            'SELECT SLEEP%'
        ]

        deleted_count = 0
        for pattern in agent_patterns:
            queries_to_delete = db.query(SlowQuery).filter(SlowQuery.sql_text.like(pattern)).all()
            for query in queries_to_delete:
                # Also delete associated analysis results
                if query.analysis_result_id:
                    from db.models import AnalysisResult
                    analysis = db.query(AnalysisResult).filter(AnalysisResult.id == query.analysis_result_id).first()
                    if analysis:
                        db.delete(analysis)
                db.delete(query)
                deleted_count += 1

        db.commit()

        logger.info(f"🧹 Cleaned up {deleted_count} agent queries from database")

        return {
            "deleted": deleted_count,
            "message": f"Removed {deleted_count} agent/monitoring queries from database"
        }

    except Exception as e:
        logger.error(f"Error cleaning up agent queries: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
