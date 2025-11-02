"""
Analyzer management endpoints.

API routes for triggering query analysis and managing the analyzer service.
"""
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, BackgroundTasks

from backend.core.logger import get_logger
from backend.services.analyzer import QueryAnalyzer
from backend.services.scheduler import get_scheduler

logger = get_logger(__name__)

router = APIRouter(
    prefix="/analyzer",
    tags=["Analyzer"],
)


@router.post("/analyze", summary="Trigger analysis of pending queries")
async def analyze_pending_queries(
    background_tasks: BackgroundTasks,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Manually trigger analysis of all pending (NEW) slow queries.

    Args:
        limit: Maximum number of queries to analyze in one batch (default: 50)

    Runs the analysis in the background and returns immediately.
    """
    def run_analysis():
        try:
            logger.info(f"Manual analysis triggered via API (limit={limit})")
            analyzer = QueryAnalyzer()
            count = analyzer.analyze_all_pending(limit=limit)
            scheduler = get_scheduler()
            scheduler.analyzed_count += count
            scheduler.last_analyzer_run = datetime.utcnow()
            logger.info(f"Manual analysis completed: {count} queries analyzed")
        except Exception as e:
            logger.error(f"Manual analysis failed: {e}", exc_info=True)

    background_tasks.add_task(run_analysis)

    return {
        "status": "started",
        "message": f"Analysis started in background (max {limit} queries)",
        "limit": limit
    }


@router.post("/analyze/{query_id}", summary="Analyze specific query")
async def analyze_query(
    query_id: str,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    Manually trigger analysis of a specific slow query by ID.

    Args:
        query_id: UUID of the slow query to analyze

    Returns:
        Analysis status
    """
    def run_analysis():
        try:
            logger.info(f"Manual analysis triggered for query {query_id}")
            analyzer = QueryAnalyzer()
            result_id = analyzer.analyze_query(query_id)
            scheduler = get_scheduler()
            scheduler.analyzed_count += 1 if result_id else 0
            scheduler.last_analyzer_run = datetime.utcnow()
            if result_id:
                logger.info(f"Analysis completed for query {query_id}: {result_id}")
            else:
                logger.warning(f"Analysis failed for query {query_id}")
        except Exception as e:
            logger.error(f"Analysis failed for query {query_id}: {e}", exc_info=True)

    background_tasks.add_task(run_analysis)

    return {
        "status": "started",
        "message": f"Analysis started for query {query_id}",
        "query_id": query_id
    }


@router.get("/status", summary="Get analyzer status")
async def get_analyzer_status() -> Dict[str, Any]:
    """
    Get the status of the analyzer service.

    Returns information about pending queries and analysis statistics.
    """
    try:
        from backend.db.session import get_db_context
        from backend.db.models import SlowQueryRaw, AnalysisResult
        from sqlalchemy import func

        with get_db_context() as db:
            # Count queries by status
            pending_count = db.query(func.count(SlowQueryRaw.id)).filter(
                SlowQueryRaw.status == 'NEW'
            ).scalar()

            analyzed_count = db.query(func.count(SlowQueryRaw.id)).filter(
                SlowQueryRaw.status == 'ANALYZED'
            ).scalar()

            error_count = db.query(func.count(SlowQueryRaw.id)).filter(
                SlowQueryRaw.status == 'ERROR'
            ).scalar()

            # Analysis statistics
            total_analyses = db.query(func.count(AnalysisResult.id)).scalar()

            high_impact = db.query(func.count(AnalysisResult.id)).filter(
                AnalysisResult.improvement_level == 'HIGH'
            ).scalar()

            medium_impact = db.query(func.count(AnalysisResult.id)).filter(
                AnalysisResult.improvement_level == 'MEDIUM'
            ).scalar()

            low_impact = db.query(func.count(AnalysisResult.id)).filter(
                AnalysisResult.improvement_level == 'LOW'
            ).scalar()

            return {
                "queries": {
                    "pending": pending_count,
                    "analyzed": analyzed_count,
                    "error": error_count,
                    "total": pending_count + analyzed_count + error_count
                },
                "analyses": {
                    "total": total_analyses,
                    "high_impact": high_impact,
                    "medium_impact": medium_impact,
                    "low_impact": low_impact
                },
                "analyzer": {
                    "version": "1.0.0",
                    "status": "ready"
                }
            }

    except Exception as e:
        logger.error(f"Failed to get analyzer status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get analyzer status: {str(e)}")
