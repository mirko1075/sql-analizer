"""
Multi-tenant Queries API Routes for Phase 6.
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import hashlib

from db.models_multitenant import SlowQuery, User, UserRole, Collector, get_db
from middleware.auth import get_current_user, get_collector_from_api_key
from utils.rule_analyzer import analyze_query_rules

router = APIRouter(prefix="/api/v1/queries", tags=["Queries"])


class BulkQueryRequest(BaseModel):
    """Request model for bulk query insertion."""
    queries: List[Dict[str, Any]] = Field(..., description="List of query data dictionaries")


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
    Includes automatic rule-based analysis with suggestions.
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

    # Perform automatic rule-based analysis
    analysis = analyze_query_rules(
        sql=slow_query.sql_text,
        query_time=slow_query.query_time,
        rows_examined=slow_query.rows_examined or 0,
        rows_sent=slow_query.rows_sent or 0
    )

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
        "identity_id": slow_query.identity_id,
        # Add rule-based analysis
        "analysis": {
            "id": f"rule_based_{query_id}",
            "slow_query_id": query_id,
            "problem": analysis["problem"],
            "root_cause": analysis["root_cause"],
            "suggestions": analysis["suggestions"],
            "improvement_level": analysis["improvement_level"],
            "estimated_speedup": analysis["estimated_speedup"],
            "analyzer_version": analysis["analyzer_version"],
            "analysis_method": "rule_based",
            "confidence_score": analysis["confidence_score"],
            "analyzed_at": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat()
        }
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


@router.post("/bulk")
async def create_queries_bulk(
    request: BulkQueryRequest,
    collector: Collector = Depends(get_collector_from_api_key),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Bulk insert slow queries from a collector agent.
    Requires collector API key authentication.
    """
    created_count = 0
    skipped_count = 0
    errors = []

    for query_data in request.queries:
        try:
            # Extract fields from query data
            sql_text = query_data.get("sql_text", "")
            if not sql_text:
                skipped_count += 1
                continue

            # Generate SQL fingerprint (hash)
            sql_fingerprint = hashlib.md5(sql_text.encode()).hexdigest()[:32]

            # Parse start_time
            start_time_str = query_data.get("start_time")
            start_time = None
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str)
                except:
                    start_time = datetime.utcnow()

            # Create SlowQuery object
            slow_query = SlowQuery(
                sql_fingerprint=sql_fingerprint,
                sql_text=sql_text,
                query_time=float(query_data.get("query_time", 0)),
                lock_time=float(query_data.get("lock_time", 0)),
                rows_sent=int(query_data.get("rows_sent", 0)),
                rows_examined=int(query_data.get("rows_examined", 0)),
                database_name=query_data.get("db") or query_data.get("database_name", "unknown"),
                user_host=query_data.get("user_host", "unknown"),
                start_time=start_time or datetime.utcnow(),
                collected_at=datetime.utcnow(),
                organization_id=collector.organization_id,
                team_id=collector.team_id,
                identity_id=None  # Collector doesn't have identity
            )

            db.add(slow_query)
            created_count += 1

        except Exception as e:
            errors.append({"query": query_data.get("sql_text", "")[:50], "error": str(e)})
            skipped_count += 1

    # Commit all at once
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save queries: {str(e)}")

    return {
        "status": "success",
        "count": created_count,
        "skipped": skipped_count,
        "errors": errors[:10]  # Limit errors to first 10
    }
