"""
Simple collectors routes for Phase 6.
Provides stub endpoints for collectors functionality.
"""
from fastapi import APIRouter, Depends, Query
from typing import Dict, Any

from db.models_multitenant import User
from middleware.auth import get_current_user
from utils.mysql_collector_multitenant import MySQLCollectorMultiTenant, test_mysql_connection

router = APIRouter(prefix="/api/v1/collectors", tags=["Collectors"])


@router.get("/status")
async def get_collector_status(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get collector status (stub implementation).

    Returns mock data since collectors are not yet implemented in Phase 6.
    """
    return {
        "is_running": False,
        "jobs": [],
        "mysql_last_run": None,
        "postgres_last_run": None,
        "analyzer_last_run": None,
        "mysql_total_collected": 0,
        "postgres_total_collected": 0,
        "total_analyzed": 0,
        "message": "Collectors not yet implemented in multi-tenant version"
    }


@router.post("/mysql/collect")
async def trigger_mysql_collection(
    lookback_minutes: int = Query(60, ge=1, le=15000, description="Lookback period in minutes (max ~10 days for testing)"),
    min_query_time: float = Query(1.0, ge=0.1, description="Minimum query time in seconds"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Trigger MySQL slow query collection.

    Collects slow queries from MySQL slow_log table and stores them
    in the multi-tenant database with organization isolation.
    """
    # Create collector with user's organization context
    collector = MySQLCollectorMultiTenant(
        organization_id=current_user.organization_id,
        team_id=current_user.team_id if hasattr(current_user, 'team_id') else 1,
        identity_id=current_user.identity_id if hasattr(current_user, 'identity_id') else None
    )

    # Collect queries
    result = collector.collect_slow_queries(
        lookback_minutes=lookback_minutes,
        min_query_time=min_query_time
    )

    if result["success"]:
        return {
            "status": "success",
            "message": f"Collected {result['queries_collected']} queries (skipped {result['queries_skipped']} duplicates)",
            **result
        }
    else:
        return {
            "status": "error",
            "message": result.get("error", "Unknown error"),
            **result
        }


@router.get("/mysql/test")
async def test_mysql_collector(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Test MySQL connection and slow_log accessibility.

    Returns connection status and MySQL server information.
    """
    return test_mysql_connection()


@router.post("/postgres/collect")
async def trigger_postgres_collection(
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Trigger PostgreSQL collection (stub)."""
    return {
        "status": "not_implemented",
        "message": "PostgreSQL collector not yet implemented in multi-tenant version"
    }


@router.post("/scheduler/start")
async def start_scheduler(
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Start scheduler (stub)."""
    return {
        "status": "not_implemented",
        "message": "Scheduler not yet implemented in multi-tenant version"
    }


@router.post("/scheduler/stop")
async def stop_scheduler(
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Stop scheduler (stub)."""
    return {
        "status": "not_implemented",
        "message": "Scheduler not yet implemented in multi-tenant version"
    }
