"""
API routes for statistics and analytics.

Provides endpoints for aggregate statistics and insights.
"""
from typing import List
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, text, desc

from backend.db.session import get_db
from backend.db.models import SlowQueryRaw, AnalysisResult, DbMetadata
from backend.api.schemas.stats import (
    TableImpactSchema,
    DatabaseStatsSchema,
    GlobalStatsResponse,
    ImprovementSummarySchema,
    QueryTrendSchema,
)
from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get(
    "/top-tables",
    response_model=List[TableImpactSchema],
    summary="Get top impacted tables",
    description="Retrieve tables that appear most frequently in slow queries"
)
async def get_top_tables(
    limit: int = Query(10, ge=1, le=50, description="Number of tables to return"),
    source_db_type: str = Query(None, description="Filter by database type"),
    db: Session = Depends(get_db)
):
    """
    Get tables that appear most frequently in slow query execution plans.

    This helps identify which tables are bottlenecks in the system.
    """
    try:
        # Use the impactful_tables view
        query = text("""
            SELECT
                source_db_type,
                source_db_host,
                table_name,
                query_count,
                avg_duration_ms,
                distinct_queries
            FROM impactful_tables
            WHERE 1=1
                AND (:db_type IS NULL OR source_db_type = :db_type)
            ORDER BY query_count DESC
            LIMIT :limit
        """)

        result = db.execute(
            query,
            {"db_type": source_db_type, "limit": limit}
        ).fetchall()

        return [
            TableImpactSchema(
                source_db_type=row[0],
                source_db_host=row[1],
                table_name=row[2],
                query_count=row[3],
                avg_duration_ms=float(row[4]),
                distinct_queries=row[5]
            )
            for row in result
        ]

    except Exception as e:
        logger.error(f"Error getting top tables: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/database/{db_type}/{db_host}",
    response_model=DatabaseStatsSchema,
    summary="Get database statistics",
    description="Get statistics for a specific database"
)
async def get_database_stats(
    db_type: str,
    db_host: str,
    db: Session = Depends(get_db)
):
    """
    Get aggregate statistics for a specific database.

    Includes:
    - Total slow queries count
    - Analyzed vs pending queries
    - Average execution time
    - High-impact queries count
    """
    try:
        # Get basic counts
        total_count = db.query(func.count(SlowQueryRaw.id)).filter(
            SlowQueryRaw.source_db_type == db_type,
            SlowQueryRaw.source_db_host == db_host
        ).scalar() or 0

        analyzed_count = db.query(func.count(SlowQueryRaw.id)).filter(
            SlowQueryRaw.source_db_type == db_type,
            SlowQueryRaw.source_db_host == db_host,
            SlowQueryRaw.status == 'ANALYZED'
        ).scalar() or 0

        pending_count = db.query(func.count(SlowQueryRaw.id)).filter(
            SlowQueryRaw.source_db_type == db_type,
            SlowQueryRaw.source_db_host == db_host,
            SlowQueryRaw.status == 'NEW'
        ).scalar() or 0

        avg_duration = db.query(func.avg(SlowQueryRaw.duration_ms)).filter(
            SlowQueryRaw.source_db_type == db_type,
            SlowQueryRaw.source_db_host == db_host
        ).scalar() or 0

        # Count high-impact queries
        high_impact_count = db.query(func.count(AnalysisResult.id)).join(
            SlowQueryRaw, AnalysisResult.slow_query_id == SlowQueryRaw.id
        ).filter(
            SlowQueryRaw.source_db_type == db_type,
            SlowQueryRaw.source_db_host == db_host,
            AnalysisResult.improvement_level.in_(['HIGH', 'CRITICAL'])
        ).scalar() or 0

        return DatabaseStatsSchema(
            source_db_type=db_type,
            source_db_host=db_host,
            total_slow_queries=total_count,
            analyzed_queries=analyzed_count,
            pending_queries=pending_count,
            avg_duration_ms=float(avg_duration),
            high_impact_count=high_impact_count
        )

    except Exception as e:
        logger.error(f"Error getting database stats for {db_type}:{db_host}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/global",
    response_model=GlobalStatsResponse,
    summary="Get global statistics",
    description="Get overall statistics across all monitored databases"
)
async def get_global_stats(
    db: Session = Depends(get_db)
):
    """
    Get global statistics across all monitored databases.

    Includes:
    - Total queries and analysis status
    - Number of databases monitored
    - Top impacted tables
    - Improvement potential summary
    - Recent query trends
    """
    try:
        # Total queries
        total_queries = db.query(func.count(SlowQueryRaw.id)).scalar() or 0

        # Analyzed queries
        analyzed_count = db.query(func.count(SlowQueryRaw.id)).filter(
            SlowQueryRaw.status == 'ANALYZED'
        ).scalar() or 0

        # Pending queries
        pending_count = db.query(func.count(SlowQueryRaw.id)).filter(
            SlowQueryRaw.status == 'NEW'
        ).scalar() or 0

        # Number of unique databases
        databases_count = db.query(
            func.count(func.distinct(SlowQueryRaw.source_db_host))
        ).scalar() or 0

        # Top tables (limit to 5 for global view)
        top_tables_query = text("""
            SELECT
                source_db_type,
                source_db_host,
                table_name,
                query_count,
                avg_duration_ms,
                distinct_queries
            FROM impactful_tables
            ORDER BY query_count DESC
            LIMIT 5
        """)
        top_tables_result = db.execute(top_tables_query).fetchall()
        top_tables = [
            TableImpactSchema(
                source_db_type=row[0],
                source_db_host=row[1],
                table_name=row[2],
                query_count=row[3],
                avg_duration_ms=float(row[4]),
                distinct_queries=row[5]
            )
            for row in top_tables_result
        ]

        # Improvement summary
        improvement_summary_query = db.query(
            AnalysisResult.improvement_level,
            func.count(AnalysisResult.id).label('count')
        ).group_by(AnalysisResult.improvement_level).all()

        improvement_summary = [
            ImprovementSummarySchema(
                improvement_level=level or 'UNKNOWN',
                count=count
            )
            for level, count in improvement_summary_query
        ]

        # Recent trend (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        trend_query = db.query(
            func.date(SlowQueryRaw.captured_at).label('date'),
            func.count(SlowQueryRaw.id).label('query_count'),
            func.avg(SlowQueryRaw.duration_ms).label('avg_duration_ms'),
            func.max(SlowQueryRaw.duration_ms).label('max_duration_ms')
        ).filter(
            SlowQueryRaw.captured_at >= seven_days_ago
        ).group_by(func.date(SlowQueryRaw.captured_at)).order_by('date').all()

        recent_trend = [
            QueryTrendSchema(
                date=str(row.date),
                query_count=row.query_count,
                avg_duration_ms=float(row.avg_duration_ms),
                max_duration_ms=float(row.max_duration_ms)
            )
            for row in trend_query
        ]

        return GlobalStatsResponse(
            total_slow_queries=total_queries,
            total_analyzed=analyzed_count,
            total_pending=pending_count,
            databases_monitored=databases_count,
            top_tables=top_tables,
            improvement_summary=improvement_summary,
            recent_trend=recent_trend
        )

    except Exception as e:
        logger.error(f"Error getting global stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/databases",
    summary="List monitored databases",
    description="Get list of all databases being monitored"
)
async def list_monitored_databases(
    db: Session = Depends(get_db)
):
    """
    Get a list of all databases that have slow queries recorded.
    """
    try:
        databases = db.query(
            SlowQueryRaw.source_db_type,
            SlowQueryRaw.source_db_host,
            SlowQueryRaw.source_db_name,
            func.count(SlowQueryRaw.id).label('query_count'),
            func.max(SlowQueryRaw.captured_at).label('last_seen')
        ).group_by(
            SlowQueryRaw.source_db_type,
            SlowQueryRaw.source_db_host,
            SlowQueryRaw.source_db_name
        ).all()

        return [
            {
                "db_type": db_type,
                "host": host,
                "database": db_name,
                "slow_queries_count": count,
                "last_seen": last_seen.isoformat() if last_seen else None
            }
            for db_type, host, db_name, count, last_seen in databases
        ]

    except Exception as e:
        logger.error(f"Error listing databases: {e}")
        raise HTTPException(status_code=500, detail=str(e))
