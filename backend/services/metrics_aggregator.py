"""
Metrics Aggregator Service.

Aggregates raw slow query data into daily and fingerprint-based metrics
for efficient statistics and trend analysis.
"""
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional
from decimal import Decimal

from sqlalchemy import func, and_, desc, case
from sqlalchemy.orm import Session

from backend.core.logger import get_logger
from backend.db.session import get_db_context
from backend.db.models import (
    SlowQueryRaw,
    AnalysisResult,
    QueryMetricsDaily,
    QueryFingerprintMetrics
)

logger = get_logger(__name__)


class MetricsAggregator:
    """
    Aggregates slow query metrics for statistics and trend analysis.

    Provides methods to:
    - Aggregate daily metrics for time-series charts
    - Aggregate fingerprint metrics for top queries analysis
    - Update metrics incrementally or in bulk
    """

    def __init__(self):
        """Initialize the metrics aggregator."""
        pass

    def aggregate_daily_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Aggregate metrics by day.

        Args:
            start_date: Start date for aggregation (default: 30 days ago)
            end_date: End date for aggregation (default: today)

        Returns:
            Number of daily metric records created/updated
        """
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Normalize to midnight UTC
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        updated_count = 0

        with get_db_context() as db:
            # Get unique combinations of date + source
            date_sources = db.query(
                func.date_trunc('day', SlowQueryRaw.captured_at).label('metric_date'),
                SlowQueryRaw.source_db_type,
                SlowQueryRaw.source_db_host
            ).filter(
                and_(
                    SlowQueryRaw.captured_at >= start_date,
                    SlowQueryRaw.captured_at <= end_date
                )
            ).group_by(
                func.date_trunc('day', SlowQueryRaw.captured_at),
                SlowQueryRaw.source_db_type,
                SlowQueryRaw.source_db_host
            ).all()

            for metric_date, source_db_type, source_db_host in date_sources:
                try:
                    self._aggregate_single_day(
                        db=db,
                        metric_date=metric_date,
                        source_db_type=source_db_type,
                        source_db_host=source_db_host
                    )
                    updated_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to aggregate metrics for {metric_date.date()} "
                        f"{source_db_type}:{source_db_host}: {e}"
                    )
                    continue

            db.commit()

        logger.info(f"Aggregated metrics for {updated_count} day-source combinations")
        return updated_count

    def _aggregate_single_day(
        self,
        db: Session,
        metric_date: datetime,
        source_db_type: str,
        source_db_host: str
    ) -> None:
        """
        Aggregate metrics for a single day and source.

        Args:
            db: Database session
            metric_date: The date to aggregate (midnight UTC)
            source_db_type: Database type
            source_db_host: Database host
        """
        # Calculate end of day
        end_of_day = metric_date + timedelta(days=1)

        # Aggregate query metrics for this day
        stats = db.query(
            func.count(SlowQueryRaw.id).label('total_queries'),
            func.count(func.distinct(SlowQueryRaw.fingerprint)).label('unique_fingerprints'),
            func.avg(SlowQueryRaw.duration_ms).label('avg_duration_ms'),
            func.min(SlowQueryRaw.duration_ms).label('min_duration_ms'),
            func.max(SlowQueryRaw.duration_ms).label('max_duration_ms'),
            func.percentile_cont(0.50).within_group(SlowQueryRaw.duration_ms).label('p50_duration_ms'),
            func.percentile_cont(0.95).within_group(SlowQueryRaw.duration_ms).label('p95_duration_ms'),
            func.percentile_cont(0.99).within_group(SlowQueryRaw.duration_ms).label('p99_duration_ms'),
            func.avg(SlowQueryRaw.rows_examined).label('avg_rows_examined'),
            func.avg(SlowQueryRaw.rows_returned).label('avg_rows_returned'),
            func.avg(
                func.nullif(SlowQueryRaw.rows_examined, 0) /
                func.greatest(func.nullif(SlowQueryRaw.rows_returned, 0), 1)
            ).label('avg_efficiency_ratio')
        ).filter(
            and_(
                SlowQueryRaw.captured_at >= metric_date,
                SlowQueryRaw.captured_at < end_of_day,
                SlowQueryRaw.source_db_type == source_db_type,
                SlowQueryRaw.source_db_host == source_db_host
            )
        ).one()

        # Count analyzed queries
        analyzed_count = db.query(func.count(SlowQueryRaw.id)).filter(
            and_(
                SlowQueryRaw.captured_at >= metric_date,
                SlowQueryRaw.captured_at < end_of_day,
                SlowQueryRaw.source_db_type == source_db_type,
                SlowQueryRaw.source_db_host == source_db_host,
                SlowQueryRaw.status == 'ANALYZED'
            )
        ).scalar() or 0

        # Count high impact queries
        high_impact_count = db.query(func.count(SlowQueryRaw.id)).join(
            AnalysisResult,
            SlowQueryRaw.id == AnalysisResult.slow_query_id
        ).filter(
            and_(
                SlowQueryRaw.captured_at >= metric_date,
                SlowQueryRaw.captured_at < end_of_day,
                SlowQueryRaw.source_db_type == source_db_type,
                SlowQueryRaw.source_db_host == source_db_host,
                AnalysisResult.improvement_level.in_(['HIGH', 'CRITICAL'])
            )
        ).scalar() or 0

        # Check if record exists
        existing = db.query(QueryMetricsDaily).filter(
            and_(
                QueryMetricsDaily.metric_date == metric_date,
                QueryMetricsDaily.source_db_type == source_db_type,
                QueryMetricsDaily.source_db_host == source_db_host
            )
        ).first()

        if existing:
            # Update existing record
            existing.total_queries = stats.total_queries
            existing.unique_fingerprints = stats.unique_fingerprints
            existing.avg_duration_ms = stats.avg_duration_ms
            existing.min_duration_ms = stats.min_duration_ms
            existing.max_duration_ms = stats.max_duration_ms
            existing.p50_duration_ms = stats.p50_duration_ms
            existing.p95_duration_ms = stats.p95_duration_ms
            existing.p99_duration_ms = stats.p99_duration_ms
            existing.avg_rows_examined = int(stats.avg_rows_examined) if stats.avg_rows_examined else None
            existing.avg_rows_returned = int(stats.avg_rows_returned) if stats.avg_rows_returned else None
            existing.avg_efficiency_ratio = stats.avg_efficiency_ratio
            existing.analyzed_count = analyzed_count
            existing.high_impact_count = high_impact_count
            existing.updated_at = datetime.utcnow()
        else:
            # Create new record
            new_metric = QueryMetricsDaily(
                metric_date=metric_date,
                source_db_type=source_db_type,
                source_db_host=source_db_host,
                total_queries=stats.total_queries,
                unique_fingerprints=stats.unique_fingerprints,
                avg_duration_ms=stats.avg_duration_ms,
                min_duration_ms=stats.min_duration_ms,
                max_duration_ms=stats.max_duration_ms,
                p50_duration_ms=stats.p50_duration_ms,
                p95_duration_ms=stats.p95_duration_ms,
                p99_duration_ms=stats.p99_duration_ms,
                avg_rows_examined=int(stats.avg_rows_examined) if stats.avg_rows_examined else None,
                avg_rows_returned=int(stats.avg_rows_returned) if stats.avg_rows_returned else None,
                avg_efficiency_ratio=stats.avg_efficiency_ratio,
                analyzed_count=analyzed_count,
                high_impact_count=high_impact_count
            )
            db.add(new_metric)

    def aggregate_fingerprint_metrics(self) -> int:
        """
        Aggregate metrics by query fingerprint.

        Calculates cumulative statistics for each unique query pattern.

        Returns:
            Number of fingerprint metric records created/updated
        """
        updated_count = 0

        with get_db_context() as db:
            # Get all unique fingerprint combinations
            fingerprints = db.query(
                SlowQueryRaw.fingerprint,
                SlowQueryRaw.source_db_type,
                SlowQueryRaw.source_db_host
            ).group_by(
                SlowQueryRaw.fingerprint,
                SlowQueryRaw.source_db_type,
                SlowQueryRaw.source_db_host
            ).all()

            for fingerprint, source_db_type, source_db_host in fingerprints:
                try:
                    self._aggregate_single_fingerprint(
                        db=db,
                        fingerprint=fingerprint,
                        source_db_type=source_db_type,
                        source_db_host=source_db_host
                    )
                    updated_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to aggregate fingerprint metrics for "
                        f"{fingerprint[:50]}...: {e}"
                    )
                    continue

            db.commit()

        logger.info(f"Aggregated fingerprint metrics for {updated_count} patterns")
        return updated_count

    def _aggregate_single_fingerprint(
        self,
        db: Session,
        fingerprint: str,
        source_db_type: str,
        source_db_host: str
    ) -> None:
        """
        Aggregate metrics for a single fingerprint.

        Args:
            db: Database session
            fingerprint: Query pattern
            source_db_type: Database type
            source_db_host: Database host
        """
        # Aggregate statistics for this fingerprint
        stats = db.query(
            func.count(SlowQueryRaw.id).label('execution_count'),
            func.min(SlowQueryRaw.captured_at).label('first_seen'),
            func.max(SlowQueryRaw.captured_at).label('last_seen'),
            func.sum(SlowQueryRaw.duration_ms).label('total_duration_ms'),
            func.avg(SlowQueryRaw.duration_ms).label('avg_duration_ms'),
            func.min(SlowQueryRaw.duration_ms).label('min_duration_ms'),
            func.max(SlowQueryRaw.duration_ms).label('max_duration_ms'),
            func.percentile_cont(0.95).within_group(SlowQueryRaw.duration_ms).label('p95_duration_ms'),
            func.avg(SlowQueryRaw.rows_examined).label('avg_rows_examined'),
            func.avg(SlowQueryRaw.rows_returned).label('avg_rows_returned'),
            func.avg(
                func.nullif(SlowQueryRaw.rows_examined, 0) /
                func.greatest(func.nullif(SlowQueryRaw.rows_returned, 0), 1)
            ).label('avg_efficiency_ratio')
        ).filter(
            and_(
                SlowQueryRaw.fingerprint == fingerprint,
                SlowQueryRaw.source_db_type == source_db_type,
                SlowQueryRaw.source_db_host == source_db_host
            )
        ).one()

        # Check if any query with this fingerprint has been analyzed
        has_analysis = db.query(func.count(SlowQueryRaw.id)).filter(
            and_(
                SlowQueryRaw.fingerprint == fingerprint,
                SlowQueryRaw.source_db_type == source_db_type,
                SlowQueryRaw.source_db_host == source_db_host,
                SlowQueryRaw.status == 'ANALYZED'
            )
        ).scalar() > 0

        # Get highest improvement level
        improvement_level_query = db.query(
            AnalysisResult.improvement_level
        ).join(
            SlowQueryRaw,
            AnalysisResult.slow_query_id == SlowQueryRaw.id
        ).filter(
            and_(
                SlowQueryRaw.fingerprint == fingerprint,
                SlowQueryRaw.source_db_type == source_db_type,
                SlowQueryRaw.source_db_host == source_db_host
            )
        ).order_by(
            desc(
                case(
                    (AnalysisResult.improvement_level == 'CRITICAL', 4),
                    (AnalysisResult.improvement_level == 'HIGH', 3),
                    (AnalysisResult.improvement_level == 'MEDIUM', 2),
                    (AnalysisResult.improvement_level == 'LOW', 1),
                    else_=0
                )
            )
        ).first()

        improvement_level = improvement_level_query[0] if improvement_level_query else None

        # Get representative query ID (most recent)
        representative = db.query(SlowQueryRaw.id).filter(
            and_(
                SlowQueryRaw.fingerprint == fingerprint,
                SlowQueryRaw.source_db_type == source_db_type,
                SlowQueryRaw.source_db_host == source_db_host
            )
        ).order_by(desc(SlowQueryRaw.captured_at)).first()

        representative_id = representative[0] if representative else None

        # Check if record exists
        existing = db.query(QueryFingerprintMetrics).filter(
            and_(
                QueryFingerprintMetrics.fingerprint == fingerprint,
                QueryFingerprintMetrics.source_db_type == source_db_type,
                QueryFingerprintMetrics.source_db_host == source_db_host
            )
        ).first()

        if existing:
            # Update existing record
            existing.execution_count = stats.execution_count
            existing.first_seen = stats.first_seen
            existing.last_seen = stats.last_seen
            existing.total_duration_ms = stats.total_duration_ms
            existing.avg_duration_ms = stats.avg_duration_ms
            existing.min_duration_ms = stats.min_duration_ms
            existing.max_duration_ms = stats.max_duration_ms
            existing.p95_duration_ms = stats.p95_duration_ms
            existing.avg_rows_examined = int(stats.avg_rows_examined) if stats.avg_rows_examined else None
            existing.avg_rows_returned = int(stats.avg_rows_returned) if stats.avg_rows_returned else None
            existing.avg_efficiency_ratio = stats.avg_efficiency_ratio
            existing.has_analysis = 1 if has_analysis else 0
            existing.improvement_level = improvement_level
            existing.representative_query_id = representative_id
            existing.updated_at = datetime.utcnow()
        else:
            # Create new record
            new_metric = QueryFingerprintMetrics(
                fingerprint=fingerprint,
                source_db_type=source_db_type,
                source_db_host=source_db_host,
                execution_count=stats.execution_count,
                first_seen=stats.first_seen,
                last_seen=stats.last_seen,
                total_duration_ms=stats.total_duration_ms,
                avg_duration_ms=stats.avg_duration_ms,
                min_duration_ms=stats.min_duration_ms,
                max_duration_ms=stats.max_duration_ms,
                p95_duration_ms=stats.p95_duration_ms,
                avg_rows_examined=int(stats.avg_rows_examined) if stats.avg_rows_examined else None,
                avg_rows_returned=int(stats.avg_rows_returned) if stats.avg_rows_returned else None,
                avg_efficiency_ratio=stats.avg_efficiency_ratio,
                has_analysis=1 if has_analysis else 0,
                improvement_level=improvement_level,
                representative_query_id=representative_id
            )
            db.add(new_metric)

    def aggregate_all(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, int]:
        """
        Run all aggregations.

        Args:
            start_date: Start date for daily aggregation
            end_date: End date for daily aggregation

        Returns:
            Dictionary with counts of records created/updated
        """
        logger.info("Starting full metrics aggregation")

        daily_count = self.aggregate_daily_metrics(start_date, end_date)
        fingerprint_count = self.aggregate_fingerprint_metrics()

        result = {
            'daily_metrics': daily_count,
            'fingerprint_metrics': fingerprint_count
        }

        logger.info(f"Metrics aggregation completed: {result}")
        return result


# Convenience functions
def aggregate_daily_metrics(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> int:
    """Aggregate daily metrics."""
    aggregator = MetricsAggregator()
    return aggregator.aggregate_daily_metrics(start_date, end_date)


def aggregate_fingerprint_metrics() -> int:
    """Aggregate fingerprint metrics."""
    aggregator = MetricsAggregator()
    return aggregator.aggregate_fingerprint_metrics()


def aggregate_all_metrics(start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, int]:
    """Run all metrics aggregations."""
    aggregator = MetricsAggregator()
    return aggregator.aggregate_all(start_date, end_date)


# Example usage
if __name__ == "__main__":
    aggregator = MetricsAggregator()
    result = aggregator.aggregate_all()
    print(f"Aggregation complete: {result}")
