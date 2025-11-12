"""
Multi-tenant Queries API Routes for Phase 6.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Any, Optional
from datetime import datetime

from db.models_multitenant import SlowQuery, User, UserRole, get_db
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/queries", tags=["Queries"])


@router.get("")
async def list_queries(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Number of records to return"),
    database: Optional[str] = Query(None, description="Filter by database name"),
    min_query_time: Optional[float] = Query(None, ge=0, description="Minimum query time in seconds"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    List all slow queries with pagination and filtering.
    Filters by organization for non-super-admin users.
    """
    # Build query
    query = db.query(SlowQuery)

    # Filter by organization for non-super-admin users
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.filter(SlowQuery.organization_id == current_user.organization_id)

    # Apply filters
    if database:
        query = query.filter(SlowQuery.database_name == database)

    if min_query_time is not None:
        query = query.filter(SlowQuery.query_time >= min_query_time)

    # Get total count
    total = query.count()

    # Apply pagination
    queries = query.order_by(desc(SlowQuery.start_time)).offset(skip).limit(limit).all()

    # Format response
    queries_data = []
    for q in queries:
        # Determine severity based on query time
        if q.query_time > 10:
            severity = "HIGH"
        elif q.query_time > 5:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        queries_data.append({
            "id": q.id,
            "sql_fingerprint": q.sql_fingerprint,
            "sql_text": q.sql_text[:200] + "..." if len(q.sql_text) > 200 else q.sql_text,
            "query_time": round(q.query_time, 3),
            "lock_time": round(q.lock_time, 3) if q.lock_time else 0,
            "rows_examined": q.rows_examined,
            "rows_sent": q.rows_sent,
            "database_name": q.database_name,
            "user_host": q.user_host,
            "start_time": q.start_time.isoformat() if q.start_time else None,
            "collected_at": q.collected_at.isoformat() if q.collected_at else None,
            "severity": severity,
            "organization_id": q.organization_id,
            "team_id": q.team_id
        })

    return {
        "queries": queries_data,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + limit) < total
    }


@router.get("/{query_id}")
async def get_query(
    query_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get details of a specific slow query.
    """
    slow_query = db.query(SlowQuery).filter(SlowQuery.id == query_id).first()

    if not slow_query:
        raise HTTPException(status_code=404, detail=f"Query with ID {query_id} not found")

    # Check access - non-super-admin can only see their org's queries
    if current_user.role != UserRole.SUPER_ADMIN:
        if slow_query.organization_id != current_user.organization_id:
            raise HTTPException(status_code=403, detail="Access denied to this query")

    # Determine severity
    if slow_query.query_time > 10:
        severity = "HIGH"
    elif slow_query.query_time > 5:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    return {
        "id": slow_query.id,
        "sql_fingerprint": slow_query.sql_fingerprint,
        "sql_text": slow_query.sql_text,
        "query_time": round(slow_query.query_time, 3),
        "lock_time": round(slow_query.lock_time, 3) if slow_query.lock_time else 0,
        "rows_examined": slow_query.rows_examined,
        "rows_sent": slow_query.rows_sent,
        "database_name": slow_query.database_name,
        "user_host": slow_query.user_host,
        "start_time": slow_query.start_time.isoformat() if slow_query.start_time else None,
        "collected_at": slow_query.collected_at.isoformat() if slow_query.collected_at else None,
        "severity": severity,
        "organization_id": slow_query.organization_id,
        "team_id": slow_query.team_id,
        "identity_id": slow_query.identity_id
    }


@router.get("/stats/summary")
async def get_query_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get summary statistics for slow queries.
    """
    # Build base query
    query = db.query(SlowQuery)

    # Filter by organization for non-super-admin users
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.filter(SlowQuery.organization_id == current_user.organization_id)

    total_queries = query.count()

    # Average query time
    avg_query_time = db.query(func.avg(SlowQuery.query_time)).scalar() or 0.0

    # Slowest query
    slowest = query.order_by(desc(SlowQuery.query_time)).first()

    # Queries by severity
    high_severity = query.filter(SlowQuery.query_time > 10).count()
    medium_severity = query.filter(SlowQuery.query_time > 5, SlowQuery.query_time <= 10).count()
    low_severity = query.filter(SlowQuery.query_time <= 5).count()

    # Top databases
    from sqlalchemy import distinct
    databases = db.query(
        SlowQuery.database_name,
        func.count(SlowQuery.id).label('count')
    ).group_by(SlowQuery.database_name).order_by(desc('count')).limit(5).all()

    return {
        "total_queries": total_queries,
        "average_query_time": round(avg_query_time, 3),
        "severity_breakdown": {
            "high": high_severity,
            "medium": medium_severity,
            "low": low_severity
        },
        "slowest_query": {
            "id": slowest.id,
            "query_time": round(slowest.query_time, 3),
            "sql_text": slowest.sql_text[:100] + "..." if len(slowest.sql_text) > 100 else slowest.sql_text,
            "database_name": slowest.database_name
        } if slowest else None,
        "top_databases": [
            {"database": db_name, "query_count": count}
            for db_name, count in databases
        ]
    }
