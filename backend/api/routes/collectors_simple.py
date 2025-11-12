"""
Simple collectors routes for Phase 6.
Provides stub endpoints for collectors functionality.
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any

from db.models_multitenant import User
from middleware.auth import get_current_user

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
    current_user: User = Depends(get_current_user)
) -> Dict[str, str]:
    """Trigger MySQL collection (stub)."""
    return {
        "status": "not_implemented",
        "message": "MySQL collector not yet implemented in multi-tenant version"
    }


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
