"""
API routes for slow query management.

Provides endpoints to list, retrieve, and manage slow queries.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.db.session import get_db
from backend.db.models import SlowQueryRaw, AnalysisResult, User, Team
from backend.api.schemas.slow_query import (
    SlowQuerySummary,
    SlowQueryWithAnalysis,
    SlowQueryListResponse,
    ErrorResponse,
    AIAnalysisResultSchema,
)
from backend.core.logger import get_logger
from backend.core.dependencies import get_current_active_user, get_current_team
from backend.services.ai_analysis import analyze_query_with_ai

logger = get_logger(__name__)

router = APIRouter(prefix="/slow-queries", tags=["Slow Queries"])


@router.get(
    "",
    response_model=SlowQueryListResponse,
    summary="List slow queries",
    description="Retrieve a paginated list of slow queries grouped by fingerprint for the current team"
)
async def list_slow_queries(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    source_db_type: Optional[str] = Query(None, description="Filter by database type"),
    source_db_host: Optional[str] = Query(None, description="Filter by database host"),
    min_duration_ms: Optional[float] = Query(None, description="Minimum query duration in milliseconds"),
    status: Optional[str] = Query(None, description="Filter by status: NEW, ANALYZED, IGNORED, ERROR"),
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team),
    db: Session = Depends(get_db)
):
    """
    Get a list of slow queries grouped by fingerprint.

    Returns aggregated statistics for each unique query pattern including:
    - Execution count
    - Average, min, max execution times
    - Analysis status
    """
    try:
        # Subquery to get the most recent query ID for each fingerprint group
        from sqlalchemy import lateral

        # Build base query using the query_performance_summary view
        query = db.query(
            SlowQueryRaw.fingerprint,
            SlowQueryRaw.source_db_type,
            SlowQueryRaw.source_db_host,
            func.count(SlowQueryRaw.id).label('execution_count'),
            func.avg(SlowQueryRaw.duration_ms).label('avg_duration_ms'),
            func.min(SlowQueryRaw.duration_ms).label('min_duration_ms'),
            func.max(SlowQueryRaw.duration_ms).label('max_duration_ms'),
            func.percentile_cont(0.95).within_group(SlowQueryRaw.duration_ms).label('p95_duration_ms'),
            func.min(SlowQueryRaw.captured_at).label('first_seen'),
            func.max(SlowQueryRaw.captured_at).label('last_seen'),
            func.avg(
                func.nullif(SlowQueryRaw.rows_examined, 0) /
                func.greatest(func.nullif(SlowQueryRaw.rows_returned, 0), 1)
            ).label('avg_efficiency_ratio'),
            func.bool_or(SlowQueryRaw.status == 'ANALYZED').label('has_analysis'),
            func.max(AnalysisResult.improvement_level).label('max_improvement_level')
        ).outerjoin(
            AnalysisResult, SlowQueryRaw.id == AnalysisResult.slow_query_id
        )

        # Filter by team (REQUIRED for multi-tenancy)
        query = query.filter(SlowQueryRaw.team_id == current_team.id)

        # Apply additional filters
        if source_db_type:
            query = query.filter(SlowQueryRaw.source_db_type == source_db_type)

        if source_db_host:
            query = query.filter(SlowQueryRaw.source_db_host == source_db_host)

        if min_duration_ms:
            query = query.having(func.avg(SlowQueryRaw.duration_ms) >= min_duration_ms)

        if status:
            query = query.filter(SlowQueryRaw.status == status)

        # Group by fingerprint and source
        query = query.group_by(
            SlowQueryRaw.fingerprint,
            SlowQueryRaw.source_db_type,
            SlowQueryRaw.source_db_host
        )

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        items = query.order_by(desc('avg_duration_ms')).offset(offset).limit(page_size).all()

        # Convert to response model
        # For each grouped result, get the most recent query ID
        summaries = []
        for item in items:
            # Get the most recent query ID for this fingerprint group
            representative_query = db.query(SlowQueryRaw.id).filter(
                SlowQueryRaw.fingerprint == item.fingerprint,
                SlowQueryRaw.source_db_type == item.source_db_type,
                SlowQueryRaw.source_db_host == item.source_db_host
            ).order_by(desc(SlowQueryRaw.captured_at)).first()

            summaries.append(SlowQuerySummary(
                id=str(representative_query.id) if representative_query else "",
                fingerprint=item.fingerprint,
                source_db_type=item.source_db_type,
                source_db_host=item.source_db_host,
                execution_count=item.execution_count,
                avg_duration_ms=float(item.avg_duration_ms),
                min_duration_ms=float(item.min_duration_ms),
                max_duration_ms=float(item.max_duration_ms),
                p95_duration_ms=float(item.p95_duration_ms) if item.p95_duration_ms else None,
                first_seen=item.first_seen,
                last_seen=item.last_seen,
                avg_efficiency_ratio=float(item.avg_efficiency_ratio) if item.avg_efficiency_ratio else None,
                has_analysis=item.has_analysis,
                max_improvement_level=item.max_improvement_level
            ))

        total_pages = (total + page_size - 1) // page_size

        return SlowQueryListResponse(
            items=summaries,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Error listing slow queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/{query_id}/analyze-ai",
    response_model=AIAnalysisResultSchema,
    summary="Run AI-assisted analysis for a slow query",
)
async def analyze_query_with_ai_endpoint(
    query_id: UUID,
    force: bool = Query(False, description="Re-run AI analysis even if cached"),
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team),
    db: Session = Depends(get_db)
):
    """
    Run AI-powered analysis for a specific slow query and return the generated insights.
    """
    try:
        # Verify the query belongs to the current team
        slow_query = db.query(SlowQueryRaw).filter(
            SlowQueryRaw.id == query_id,
            SlowQueryRaw.team_id == current_team.id
        ).first()

        if not slow_query:
            raise HTTPException(status_code=404, detail=f"Query with ID {query_id} not found")

        result = analyze_query_with_ai(query_id, force=force)
        return AIAnalysisResultSchema.model_validate(result)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("AI analysis failed for query %s: %s", query_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="AI analysis failed") from exc


@router.get(
    "/{query_id}",
    response_model=SlowQueryWithAnalysis,
    summary="Get slow query details",
    description="Retrieve detailed information about a specific slow query including analysis"
)
async def get_slow_query(
    query_id: UUID,
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific slow query.

    Returns:
    - Full SQL query
    - Execution plan (JSON and text)
    - Performance metrics
    - Analysis results (if available)
    - Optimization suggestions
    """
    try:
        # Query slow query with its analysis, filtered by team
        slow_query = db.query(SlowQueryRaw).filter(
            SlowQueryRaw.id == query_id,
            SlowQueryRaw.team_id == current_team.id
        ).first()

        if not slow_query:
            raise HTTPException(status_code=404, detail=f"Query with ID {query_id} not found")

        # Convert to response model (relationships are loaded automatically)
        return SlowQueryWithAnalysis.model_validate(slow_query)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving query {query_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/fingerprint/{fingerprint_hash}",
    response_model=List[SlowQueryWithAnalysis],
    summary="Get queries by fingerprint",
    description="Retrieve all executions of queries matching a specific fingerprint"
)
async def get_queries_by_fingerprint(
    fingerprint_hash: str,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team),
    db: Session = Depends(get_db)
):
    """
    Get all executions of queries matching a fingerprint.

    Useful for analyzing how the same query pattern performs over time.
    """
    try:
        # Filter by fingerprint and team
        queries = db.query(SlowQueryRaw).filter(
            SlowQueryRaw.fingerprint == fingerprint_hash,
            SlowQueryRaw.team_id == current_team.id
        ).order_by(desc(SlowQueryRaw.captured_at)).limit(limit).all()

        if not queries:
            raise HTTPException(status_code=404, detail=f"No queries found with fingerprint: {fingerprint_hash}")

        return [SlowQueryWithAnalysis.model_validate(q) for q in queries]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving queries by fingerprint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/{query_id}",
    summary="Delete slow query",
    description="Delete a slow query record and its analysis"
)
async def delete_slow_query(
    query_id: UUID,
    current_user: User = Depends(get_current_active_user),
    current_team: Team = Depends(get_current_team),
    db: Session = Depends(get_db)
):
    """
    Delete a slow query record.

    This will also cascade delete the associated analysis result.
    """
    try:
        # Verify the query belongs to the current team before deleting
        slow_query = db.query(SlowQueryRaw).filter(
            SlowQueryRaw.id == query_id,
            SlowQueryRaw.team_id == current_team.id
        ).first()

        if not slow_query:
            raise HTTPException(status_code=404, detail=f"Query with ID {query_id} not found")

        db.delete(slow_query)
        db.commit()

        logger.info(f"User {current_user.email} deleted slow query {query_id} from team {current_team.name}")

        return {"message": f"Query {query_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting query {query_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
