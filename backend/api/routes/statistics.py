"""
API routes for statistics and trend analysis.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, desc, and_
from sqlalchemy.orm import Session

from backend.api.schemas.statistics import (
    PerformanceTrendsResponse,
    DailyMetricPoint,
    QueryDistributionResponse,
    TopQueryPattern,
    EfficiencyBucket,
    AIInsightsResponse,
    AIInsightQuery,
)
from backend.db.models import QueryMetricsDaily, QueryFingerprintMetrics
from backend.db.session import get_db

router = APIRouter(prefix="/statistics", tags=["Statistics"])


@router.get("/performance-trends", response_model=PerformanceTrendsResponse)
def get_performance_trends(
    days: int = Query(30, ge=1, le=365, description="Number of days to retrieve"),
    source_db_type: Optional[str] = Query(None, description="Filter by database type"),
    source_db_host: Optional[str] = Query(None, description="Filter by database host"),
    db: Session = Depends(get_db),
):
    """
    Get performance trends over time.

    Returns daily aggregated metrics for time-series charts.
    """
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Build query
    query = db.query(QueryMetricsDaily).filter(
        QueryMetricsDaily.metric_date >= start_date
    )

    if source_db_type:
        query = query.filter(QueryMetricsDaily.source_db_type == source_db_type)
    if source_db_host:
        query = query.filter(QueryMetricsDaily.source_db_host == source_db_host)

    metrics = query.order_by(QueryMetricsDaily.metric_date).all()

    # Calculate summary statistics
    if metrics:
        total_queries = sum(m.total_queries for m in metrics)
        avg_duration = sum(float(m.avg_duration_ms or 0) for m in metrics) / len(metrics)
        max_p95 = max((float(m.p95_duration_ms or 0) for m in metrics), default=0)
        total_high_impact = sum(m.high_impact_count for m in metrics)
    else:
        total_queries = 0
        avg_duration = 0
        max_p95 = 0
        total_high_impact = 0

    return PerformanceTrendsResponse(
        metrics=[DailyMetricPoint.model_validate(m) for m in metrics],
        date_range={
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        summary={
            "total_queries": total_queries,
            "avg_duration_ms": round(avg_duration, 2),
            "max_p95_duration_ms": round(max_p95, 2),
            "total_high_impact": total_high_impact,
            "days_covered": len(set(m.metric_date.date() for m in metrics)),
        }
    )


@router.get("/query-distribution", response_model=QueryDistributionResponse)
def get_query_distribution(
    limit: int = Query(10, ge=1, le=50, description="Number of top queries to return"),
    source_db_type: Optional[str] = Query(None, description="Filter by database type"),
    source_db_host: Optional[str] = Query(None, description="Filter by database host"),
    db: Session = Depends(get_db),
):
    """
    Get query distribution statistics.

    Returns top queries by various metrics and efficiency histogram.
    """
    # Base query
    base_query = db.query(QueryFingerprintMetrics)

    if source_db_type:
        base_query = base_query.filter(QueryFingerprintMetrics.source_db_type == source_db_type)
    if source_db_host:
        base_query = base_query.filter(QueryFingerprintMetrics.source_db_host == source_db_host)

    # Top slowest queries (by average duration)
    top_slowest = base_query.order_by(
        desc(QueryFingerprintMetrics.avg_duration_ms)
    ).limit(limit).all()

    # Top most frequent queries (by execution count)
    top_frequent = base_query.order_by(
        desc(QueryFingerprintMetrics.execution_count)
    ).limit(limit).all()

    # Top inefficient queries (by efficiency ratio)
    top_inefficient = base_query.filter(
        QueryFingerprintMetrics.avg_efficiency_ratio.isnot(None)
    ).order_by(
        desc(QueryFingerprintMetrics.avg_efficiency_ratio)
    ).limit(limit).all()

    # Efficiency histogram
    all_ratios = db.query(QueryFingerprintMetrics.avg_efficiency_ratio).filter(
        QueryFingerprintMetrics.avg_efficiency_ratio.isnot(None)
    )
    if source_db_type:
        all_ratios = all_ratios.filter(QueryFingerprintMetrics.source_db_type == source_db_type)
    if source_db_host:
        all_ratios = all_ratios.filter(QueryFingerprintMetrics.source_db_host == source_db_host)

    ratios = [float(r[0]) for r in all_ratios.all()]
    total_ratios = len(ratios)

    histogram = []
    if total_ratios > 0:
        buckets = [
            ("Excellent (≤1)", lambda r: r <= 1),
            ("Good (1-10)", lambda r: 1 < r <= 10),
            ("Fair (10-100)", lambda r: 10 < r <= 100),
            ("Poor (100-1000)", lambda r: 100 < r <= 1000),
            ("Critical (>1000)", lambda r: r > 1000),
        ]

        for label, condition in buckets:
            count = sum(1 for r in ratios if condition(r))
            percentage = (count / total_ratios) * 100
            histogram.append(EfficiencyBucket(
                range_label=label,
                count=count,
                percentage=round(percentage, 2)
            ))

    return QueryDistributionResponse(
        top_slowest=[TopQueryPattern.model_validate(q) for q in top_slowest],
        top_frequent=[TopQueryPattern.model_validate(q) for q in top_frequent],
        top_inefficient=[TopQueryPattern.model_validate(q) for q in top_inefficient],
        efficiency_histogram=histogram,
    )


@router.get("/ai-insights", response_model=AIInsightsResponse)
def get_ai_insights(
    limit: int = Query(10, ge=1, le=50, description="Number of queries to return per category"),
    source_db_type: Optional[str] = Query(None, description="Filter by database type"),
    source_db_host: Optional[str] = Query(None, description="Filter by database host"),
    db: Session = Depends(get_db),
):
    """
    Get AI-driven insights.

    Returns high-priority queries and AI analysis statistics.
    """
    # Base query for queries with AI analysis
    base_query = db.query(QueryFingerprintMetrics).filter(
        QueryFingerprintMetrics.has_analysis == 1
    )

    if source_db_type:
        base_query = base_query.filter(QueryFingerprintMetrics.source_db_type == source_db_type)
    if source_db_host:
        base_query = base_query.filter(QueryFingerprintMetrics.source_db_host == source_db_host)

    # High priority queries (HIGH or CRITICAL improvement level)
    high_priority = base_query.filter(
        QueryFingerprintMetrics.improvement_level.in_(['HIGH', 'CRITICAL'])
    ).order_by(
        desc(QueryFingerprintMetrics.avg_duration_ms)
    ).limit(limit).all()

    # Recently analyzed queries
    recently_analyzed = base_query.order_by(
        desc(QueryFingerprintMetrics.last_seen)
    ).limit(limit).all()

    # Total analyzed count
    total_analyzed = base_query.count()

    # Analysis distribution by improvement level
    distribution_query = base_query.with_entities(
        QueryFingerprintMetrics.improvement_level,
        func.count(QueryFingerprintMetrics.id).label('count')
    ).group_by(
        QueryFingerprintMetrics.improvement_level
    ).all()

    analysis_distribution = {
        level: count for level, count in distribution_query if level
    }

    return AIInsightsResponse(
        high_priority_queries=[AIInsightQuery.model_validate(q) for q in high_priority],
        recently_analyzed=[AIInsightQuery.model_validate(q) for q in recently_analyzed],
        total_analyzed=total_analyzed,
        analysis_distribution=analysis_distribution,
    )
