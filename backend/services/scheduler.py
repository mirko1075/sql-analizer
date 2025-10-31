"""
Scheduler for periodic collection of slow queries.

Uses APScheduler to run collectors at regular intervals.
"""
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.core.config import settings
from backend.core.logger import get_logger
from backend.services.mysql_collector import MySQLCollector
from backend.services.postgres_collector import PostgreSQLCollector
from backend.services.analyzer import QueryAnalyzer

logger = get_logger(__name__)


class CollectorScheduler:
    """
    Scheduler for running collectors periodically.

    Manages background jobs that collect slow queries from MySQL and PostgreSQL.
    """

    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self.last_mysql_run: Optional[datetime] = None
        self.last_postgres_run: Optional[datetime] = None
        self.last_analyzer_run: Optional[datetime] = None
        self.mysql_collected_count = 0
        self.postgres_collected_count = 0
        self.analyzed_count = 0

    def collect_mysql_queries(self):
        """Job to collect MySQL slow queries."""
        try:
            logger.info("Starting MySQL slow query collection...")
            collector = MySQLCollector()
            count = collector.collect_and_store()
            self.mysql_collected_count += count
            self.last_mysql_run = datetime.utcnow()
            logger.info(f"✓ MySQL collection completed: {count} queries collected")
        except Exception as e:
            logger.error(f"✗ MySQL collection failed: {e}", exc_info=True)

    def collect_postgres_queries(self):
        """Job to collect PostgreSQL slow queries."""
        try:
            logger.info("Starting PostgreSQL slow query collection...")
            collector = PostgreSQLCollector()
            count = collector.collect_and_store(min_duration_ms=500.0)
            self.postgres_collected_count += count
            self.last_postgres_run = datetime.utcnow()
            logger.info(f"✓ PostgreSQL collection completed: {count} queries collected")
        except Exception as e:
            logger.error(f"✗ PostgreSQL collection failed: {e}", exc_info=True)

    def analyze_pending_queries(self):
        """Job to analyze pending slow queries."""
        try:
            logger.info("Starting pending query analysis...")
            analyzer = QueryAnalyzer()
            count = analyzer.analyze_all_pending(limit=50)
            self.analyzed_count += count
            self.last_analyzer_run = datetime.utcnow()
            logger.info(f"✓ Query analysis completed: {count} queries analyzed")
        except Exception as e:
            logger.error(f"✗ Query analysis failed: {e}", exc_info=True)

    def start(self, interval_minutes: int = 5):
        """
        Start the scheduler.

        Args:
            interval_minutes: Collection interval in minutes (default: 5)
        """
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        logger.info("=" * 60)
        logger.info("Starting Collector Scheduler")
        logger.info(f"Collection interval: {interval_minutes} minutes")
        logger.info("=" * 60)

        # Add MySQL collection job
        self.scheduler.add_job(
            func=self.collect_mysql_queries,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id='mysql_collector',
            name='MySQL Slow Query Collector',
            replace_existing=True,
            max_instances=1,  # Prevent overlapping runs
        )

        # Add PostgreSQL collection job
        self.scheduler.add_job(
            func=self.collect_postgres_queries,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id='postgres_collector',
            name='PostgreSQL Slow Query Collector',
            replace_existing=True,
            max_instances=1,  # Prevent overlapping runs
        )

        # Add Analyzer job (runs at double the interval)
        analyzer_interval = interval_minutes * 2
        self.scheduler.add_job(
            func=self.analyze_pending_queries,
            trigger=IntervalTrigger(minutes=analyzer_interval),
            id='query_analyzer',
            name='Query Analyzer',
            replace_existing=True,
            max_instances=1,  # Prevent overlapping runs
        )

        # Start scheduler
        self.scheduler.start()
        self.is_running = True

        logger.info("✓ Scheduler started successfully")
        logger.info(f"  MySQL collector: every {interval_minutes} minutes")
        logger.info(f"  PostgreSQL collector: every {interval_minutes} minutes")
        logger.info(f"  Query analyzer: every {analyzer_interval} minutes")

        # Run once immediately
        logger.info("Running initial collection and analysis...")
        self.collect_mysql_queries()
        self.collect_postgres_queries()
        self.analyze_pending_queries()

    def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return

        logger.info("Stopping Collector Scheduler...")
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

        return {
            'is_running': self.is_running,
            'jobs': jobs,
            'mysql_last_run': self.last_mysql_run.isoformat() if self.last_mysql_run else None,
            'postgres_last_run': self.last_postgres_run.isoformat() if self.last_postgres_run else None,
            'analyzer_last_run': self.last_analyzer_run.isoformat() if self.last_analyzer_run else None,
            'mysql_total_collected': self.mysql_collected_count,
            'postgres_total_collected': self.postgres_collected_count,
            'total_analyzed': self.analyzed_count,
        }


# Global scheduler instance
_scheduler: Optional[CollectorScheduler] = None


def get_scheduler() -> CollectorScheduler:
    """
    Get the global scheduler instance.

    Returns:
        CollectorScheduler instance
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = CollectorScheduler()
    return _scheduler


def start_scheduler(interval_minutes: int = 5):
    """
    Start the global scheduler.

    Args:
        interval_minutes: Collection interval in minutes
    """
    scheduler = get_scheduler()
    scheduler.start(interval_minutes=interval_minutes)


def stop_scheduler():
    """Stop the global scheduler."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.stop()
        _scheduler = None


# Example usage
if __name__ == "__main__":
    import time

    scheduler = CollectorScheduler()
    scheduler.start(interval_minutes=1)

    try:
        # Keep running
        while True:
            time.sleep(10)
            status = scheduler.get_status()
            print(f"\nScheduler Status: {status}")
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        scheduler.stop()
