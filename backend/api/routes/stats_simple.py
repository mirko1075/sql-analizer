"""
Simple stats routes for Phase 6 admin panel.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Any

from db.models_multitenant import get_db, SlowQuery, Organization, Team, User, UserRole
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/v1/stats", tags=["Statistics"])


@router.get("/dashboard")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get dashboard statistics.

    Returns:
        Dashboard statistics including counts and summaries
    """
    # Count organizations
    org_count = db.query(func.count(Organization.id)).scalar() or 0

    # Count teams
    team_count = db.query(func.count(Team.id)).scalar() or 0

    # Count users
    user_count = db.query(func.count(User.id)).scalar() or 0

    # Count slow queries
    query_count = db.query(func.count(SlowQuery.id)).scalar() or 0

    # Filter by organization if not super admin
    if current_user.role != UserRole.SUPER_ADMIN:
        org_id = current_user.organization_id
        if org_id:
            query_count = db.query(func.count(SlowQuery.id)).filter(
                SlowQuery.organization_id == org_id
            ).scalar() or 0

    # Get recent queries (last 5)
    recent_queries_query = db.query(SlowQuery)
    if current_user.role != UserRole.SUPER_ADMIN:
        recent_queries_query = recent_queries_query.filter(
            SlowQuery.organization_id == current_user.organization_id
        )

    recent_queries = recent_queries_query.order_by(SlowQuery.start_time.desc()).limit(5).all()

    recent_queries_data = [
        {
            "id": q.id,
            "sql_text": q.sql_text[:100] + "..." if len(q.sql_text) > 100 else q.sql_text,
            "query_time": round(q.query_time, 2),
            "database_name": q.database_name,
            "start_time": q.start_time.isoformat() if q.start_time else None
        }
        for q in recent_queries
    ]

    return {
        "organizations": org_count,
        "teams": team_count,
        "users": user_count,
        "slow_queries": query_count,
        "recent_queries": recent_queries_data,
        "alerts": []  # TODO: Add alerts based on query severity
    }


@router.get("/summary")
async def get_stats_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get quick stats summary."""
    return {
        "total_queries_analyzed": db.query(func.count(SlowQuery.id)).scalar() or 0,
        "active_organizations": db.query(func.count(Organization.id)).scalar() or 0,
        "active_users": db.query(func.count(User.id)).scalar() or 0,
    }


@router.get("/top-slow-queries")
async def get_top_slow_queries(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get top slowest queries."""
    query = db.query(SlowQuery)

    # Filter by organization if not super admin
    if current_user.role != UserRole.SUPER_ADMIN:
        query = query.filter(SlowQuery.organization_id == current_user.organization_id)

    queries = query.order_by(SlowQuery.query_time.desc()).limit(limit).all()

    queries_data = [
        {
            "id": q.id,
            "sql_text": q.sql_text[:100] + "..." if len(q.sql_text) > 100 else q.sql_text,
            "query_time": round(q.query_time, 2),
            "database_name": q.database_name,
            "start_time": q.start_time.isoformat() if q.start_time else None,
            "rows_examined": q.rows_examined
        }
        for q in queries
    ]

    return {"queries": queries_data}


@router.get("/unanalyzed-queries")
async def get_unanalyzed_queries(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get unanalyzed queries (stub - analysis not implemented yet)."""
    # For now, return empty list since analysis is not implemented
    return {"queries": []}
