"""
Collector management endpoints.

API routes for manually triggering collection and checking scheduler status.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any

from core.logger import setup_logger
from services.mysql_collector import MySQLCollector
from services.postgres_collector import PostgreSQLCollector
from services.scheduler import get_scheduler

logger = setup_logger(__name__)

router = APIRouter(
    prefix="/collectors",
    tags=["Collectors"],
)


@router.post("/mysql/collect", summary="Trigger MySQL collection")
async def collect_mysql(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Manually trigger MySQL slow query collection.

    Runs the collection in the background and returns immediately.
    """
    def run_collection():
        try:
            logger.info("Manual MySQL collection triggered via API")
            collector = MySQLCollector()
            count = collector.collect_and_store()
            logger.info(f"Manual MySQL collection completed: {count} queries")
        except Exception as e:
            logger.error(f"Manual MySQL collection failed: {e}", exc_info=True)

    background_tasks.add_task(run_collection)

    return {
        "status": "started",
        "message": "MySQL collection started in background",
        "collector": "mysql"
    }


@router.post("/postgres/collect", summary="Trigger PostgreSQL collection")
async def collect_postgres(
    background_tasks: BackgroundTasks,
    min_duration_ms: float = 500.0
) -> Dict[str, Any]:
    """
    Manually trigger PostgreSQL slow query collection.

    Args:
        min_duration_ms: Minimum query duration in milliseconds (default: 500ms)

    Runs the collection in the background and returns immediately.
    """
    def run_collection():
        try:
            logger.info(f"Manual PostgreSQL collection triggered via API (min_duration={min_duration_ms}ms)")
            collector = PostgreSQLCollector()
            count = collector.collect_and_store(min_duration_ms=min_duration_ms)
            logger.info(f"Manual PostgreSQL collection completed: {count} queries")
        except Exception as e:
            logger.error(f"Manual PostgreSQL collection failed: {e}", exc_info=True)

    background_tasks.add_task(run_collection)

    return {
        "status": "started",
        "message": "PostgreSQL collection started in background",
        "collector": "postgres",
        "min_duration_ms": min_duration_ms
    }


@router.get("/status", summary="Get scheduler status")
async def get_scheduler_status() -> Dict[str, Any]:
    """
    Get the status of the collector scheduler.

    Returns information about scheduled jobs and last collection times.
    """
    try:
        scheduler = get_scheduler()
        status = scheduler.get_status()
        return status
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get scheduler status: {str(e)}")


@router.post("/scheduler/start", summary="Start scheduler")
async def start_scheduler(interval_minutes: int = 5) -> Dict[str, Any]:
    """
    Start the collector scheduler.

    Args:
        interval_minutes: Collection interval in minutes (default: 5)
    """
    try:
        scheduler = get_scheduler()
        if scheduler.is_running:
            return {
                "status": "already_running",
                "message": "Scheduler is already running"
            }

        scheduler.start(interval_minutes=interval_minutes)
        return {
            "status": "started",
            "message": f"Scheduler started with {interval_minutes} minute interval",
            "interval_minutes": interval_minutes
        }
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start scheduler: {str(e)}")


@router.post("/scheduler/stop", summary="Stop scheduler")
async def stop_scheduler() -> Dict[str, Any]:
    """
    Stop the collector scheduler.
    """
    try:
        scheduler = get_scheduler()
        if not scheduler.is_running:
            return {
                "status": "not_running",
                "message": "Scheduler is not running"
            }

        scheduler.stop()
        return {
            "status": "stopped",
            "message": "Scheduler stopped successfully"
        }
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to stop scheduler: {str(e)}")
