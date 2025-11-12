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

    return {
        "organizations": org_count,
        "teams": team_count,
        "users": user_count,
        "slow_queries": query_count,
        "recent_queries": [],  # TODO: Add recent queries
        "alerts": []  # TODO: Add alerts
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
