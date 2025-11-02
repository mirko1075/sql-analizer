"""
Enhanced scheduler for multi-tenant slow query collection.

Uses team-based database connections instead of hardcoded configurations.
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.core.logger import get_logger
from backend.core.security import decrypt_db_password
from backend.db.session import get_db_context
from backend.db.models import DatabaseConnection, SlowQueryRaw, AnalysisResult
from sqlalchemy import func

logger = get_logger(__name__)


class TeamCollectorScheduler:
    """
    Multi-tenant scheduler for collecting slow queries.

    Automatically discovers DatabaseConnection records and runs
    appropriate collectors for each team.
    """

    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self.last_collection_run: Optional[datetime] = None
        self.last_analyzer_run: Optional[datetime] = None
        self.total_collected = 0
        self.total_analyzed = 0

    def collect_from_all_connections(self):
        """
        Job to collect slow queries from all active database connections.

        Iterates through all active DatabaseConnection records and runs
        the appropriate collector for each database type.
        """
        try:
            logger.info("Starting multi-tenant slow query collection...")

            with get_db_context() as db:
                # Get all active database connections
                connections = db.query(DatabaseConnection).filter(
                    DatabaseConnection.is_active == True
                ).all()

                if not connections:
                    logger.warning("No active database connections found")
                    return

                logger.info(f"Found {len(connections)} active database connection(s)")

                total_count = 0

                for conn in connections:
                    try:
                        count = self._collect_from_connection(conn)
                        total_count += count
                        logger.info(
                            f"✓ Collected {count} queries from {conn.db_type}:"
                            f"{conn.host} (team_id: {conn.team_id})"
                        )
                    except Exception as e:
                        logger.error(
                            f"✗ Failed to collect from {conn.db_type}:{conn.host} "
                            f"(team_id: {conn.team_id}): {e}",
                            exc_info=True
                        )

                self.total_collected += total_count
                self.last_collection_run = datetime.utcnow()
                logger.info(
                    f"✓ Multi-tenant collection completed: {total_count} total queries collected"
                )

        except Exception as e:
            logger.error(f"✗ Multi-tenant collection failed: {e}", exc_info=True)

    def _collect_from_connection(self, conn: DatabaseConnection) -> int:
        """
        Collect slow queries from a specific database connection.

        Args:
            conn: DatabaseConnection object

        Returns:
            Number of queries collected
        """
        # Decrypt password
        password = decrypt_db_password(conn.encrypted_password)

        # Import collectors here to avoid circular imports
        if conn.db_type == 'mysql':
            from backend.services.mysql_collector import MySQLCollector
            # Pass connection IDs to collector
            collector = MySQLCollector(
                database_connection_id=conn.id,
                team_id=conn.team_id,
                organization_id=conn.organization_id
            )
            # Override config with connection details
            collector.config.host = conn.host
            collector.config.port = conn.port
            collector.config.database = conn.database_name
            collector.config.user = conn.username
            collector.config.password = password
            count = collector.collect_and_store()

        elif conn.db_type in ['postgres', 'postgresql']:
            from backend.services.postgres_collector import PostgreSQLCollector
            # Pass connection IDs to collector
            collector = PostgreSQLCollector(
                database_connection_id=conn.id,
                team_id=conn.team_id,
                organization_id=conn.organization_id
            )
            # Override config with connection details
            collector.config.host = conn.host
            collector.config.port = conn.port
            collector.config.database = conn.database_name
            collector.config.user = conn.username
            collector.config.password = password
            count = collector.collect_and_store(min_duration_ms=500.0)

        else:
            logger.warning(
                f"Unsupported database type '{conn.db_type}' "
                f"for connection {conn.id}"
            )
            return 0

        # Update last_connected_at on successful collection
        with get_db_context() as db:
            db_conn = db.query(DatabaseConnection).filter(
                DatabaseConnection.id == conn.id
            ).first()
            if db_conn:
                db_conn.last_connected_at = datetime.utcnow()
                db.commit()

        return count

    def analyze_pending_queries(self):
        """
        Job to analyze pending slow queries across all teams.

        Analyzes queries with status='NEW' from all teams.
        """
        try:
            logger.info("Starting multi-tenant pending query analysis...")

            from backend.services.analyzer import QueryAnalyzer
            analyzer = QueryAnalyzer()
            count = analyzer.analyze_all_pending(limit=100)

            self.total_analyzed += count
            self.last_analyzer_run = datetime.utcnow()
            logger.info(f"✓ Query analysis completed: {count} queries analyzed")

        except Exception as e:
            logger.error(f"✗ Query analysis failed: {e}", exc_info=True)

    def start(self, interval_minutes: int = 5):
        """
        Start the multi-tenant scheduler.

        Args:
            interval_minutes: Collection interval in minutes (default: 5)
        """
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        logger.info("=" * 60)
        logger.info("Starting Multi-Tenant Collector Scheduler")
        logger.info(f"Collection interval: {interval_minutes} minutes")
        logger.info("=" * 60)

        # Add collection job (all database types)
        self.scheduler.add_job(
            func=self.collect_from_all_connections,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id='multi_tenant_collector',
            name='Multi-Tenant Slow Query Collector',
            replace_existing=True,
            max_instances=1,
        )

        # Add analyzer job (runs at double the interval)
        analyzer_interval = interval_minutes * 2
        self.scheduler.add_job(
            func=self.analyze_pending_queries,
            trigger=IntervalTrigger(minutes=analyzer_interval),
            id='query_analyzer',
            name='Query Analyzer',
            replace_existing=True,
            max_instances=1,
        )

        # Start scheduler
        self.scheduler.start()
        self.is_running = True

        logger.info("✓ Multi-tenant scheduler started successfully")
        logger.info(f"  Database collector: every {interval_minutes} minutes")
        logger.info(f"  Query analyzer: every {analyzer_interval} minutes")

        # Run once immediately
        logger.info("Running initial collection and analysis...")
        self.collect_from_all_connections()
        self.analyze_pending_queries()

    def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return

        logger.info("Stopping Multi-Tenant Collector Scheduler...")
        self.scheduler.shutdown(wait=True)
        self.is_running = False
        logger.info("✓ Scheduler stopped")

    def get_status(self) -> dict:
        """
        Get scheduler status.

        Returns:
            Dictionary with scheduler status information
        """
        jobs = []
        if self.is_running:
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                })

        # Get stats from database
        with get_db_context() as db:
            total_queries = db.query(func.count(SlowQueryRaw.id)).scalar() or 0
            total_analyses = db.query(func.count(AnalysisResult.id)).scalar() or 0
            analyzer_last_seen = db.query(func.max(AnalysisResult.analyzed_at)).scalar()

            # Get active connections count
            active_connections = db.query(func.count(DatabaseConnection.id)).filter(
                DatabaseConnection.is_active == True
            ).scalar() or 0

        return {
            'is_running': self.is_running,
            'jobs': jobs,
            'last_collection_run': self.last_collection_run.isoformat() if self.last_collection_run else None,
            'last_analyzer_run': (self.last_analyzer_run or analyzer_last_seen).isoformat() if (self.last_analyzer_run or analyzer_last_seen) else None,
            'total_queries_collected': max(self.total_collected, total_queries),
            'total_analyzed': max(self.total_analyzed, total_analyses),
            'active_connections': active_connections,
        }


# Global scheduler instance
_scheduler: Optional[TeamCollectorScheduler] = None


def get_team_scheduler() -> TeamCollectorScheduler:
    """Get the global multi-tenant scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TeamCollectorScheduler()
    return _scheduler


def start_team_scheduler(interval_minutes: int = 5):
    """Start the global multi-tenant scheduler."""
    scheduler = get_team_scheduler()
    scheduler.start(interval_minutes=interval_minutes)


def stop_team_scheduler():
    """Stop the global multi-tenant scheduler."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.stop()
        _scheduler = None
