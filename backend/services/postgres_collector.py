"""
PostgreSQL slow query collector.

Collects slow queries from PostgreSQL's pg_stat_statements extension
and generates EXPLAIN plans.
"""
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal

import psycopg2
from psycopg2 import Error as PGError
from psycopg2.extras import RealDictCursor

from core.config import settings
from core.logger import setup_logger
from db.session import get_db_context
from db.models import SlowQueryRaw
from services.fingerprint import fingerprint_query, is_query_safe_to_explain

logger = setup_logger(__name__)


class PostgreSQLCollector:
    """
    Collector for PostgreSQL slow queries.

    Connects to PostgreSQL, reads from pg_stat_statements, and generates
    EXPLAIN plans for slow queries.
    """

    def __init__(self):
        """Initialize PostgreSQL collector with configuration."""
        self.config = settings.postgres_lab
        self.connection = None

    def connect(self) -> bool:
        """
        Establish connection to PostgreSQL database.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.connection = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
            )
            self.connection.autocommit = False
            logger.info(f"✓ Connected to PostgreSQL: {self.config.host}:{self.config.port}")
            return True
        except PGError as e:
            logger.error(f"✗ PostgreSQL connection failed: {e}")
            return False

    def disconnect(self):
        """Close PostgreSQL connection."""
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.info("PostgreSQL connection closed")

    def fetch_slow_queries(
        self,
        min_duration_ms: float = 1000.0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Fetch slow queries from pg_stat_statements.

        Args:
            min_duration_ms: Minimum query duration in milliseconds (default: 1000ms = 1s)
            limit: Maximum number of queries to fetch

        Returns:
            List of slow query records
        """
        if not self.connection or self.connection.closed:
            logger.error("Not connected to PostgreSQL")
            return []

        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)

            # Query pg_stat_statements
            query = """
                SELECT
                    queryid,
                    query,
                    calls,
                    total_exec_time,
                    mean_exec_time,
                    max_exec_time,
                    rows,
                    shared_blks_hit,
                    shared_blks_read,
                    shared_blks_written
                FROM pg_stat_statements
                WHERE mean_exec_time >= %s
                    AND query NOT ILIKE '%%pg_stat_statements%%'
                    AND query NOT ILIKE '%%pg_catalog%%'
                ORDER BY mean_exec_time DESC
                LIMIT %s
            """

            cursor.execute(query, (min_duration_ms, limit))
            results = cursor.fetchall()
            cursor.close()

            logger.info(f"Fetched {len(results)} slow queries from PostgreSQL")
            return results

        except PGError as e:
            logger.error(f"Error fetching slow queries: {e}")
            return []

    def generate_explain(self, sql: str) -> Optional[Dict[str, Any]]:
        """
        Generate EXPLAIN plan for a SQL query.

        Args:
            sql: SQL query to explain

        Returns:
            EXPLAIN plan as JSON dict, or None if failed
        """
        if not is_query_safe_to_explain(sql):
            logger.warning(f"Skipping EXPLAIN for non-SELECT query: {sql[:50]}...")
            return None

        if not self.connection or self.connection.closed:
            logger.error("Not connected to PostgreSQL")
            return None

        try:
            cursor = self.connection.cursor()

            # Use EXPLAIN (FORMAT JSON) for structured output
            # Note: Not using ANALYZE to avoid executing the query
            explain_query = f"EXPLAIN (FORMAT JSON) {sql}"
            cursor.execute(explain_query)

            result = cursor.fetchone()
            cursor.close()

            # Rollback to avoid leaving transaction open
            self.connection.rollback()

            if result and result[0]:
                # PostgreSQL returns EXPLAIN as JSON array
                plan = result[0][0] if isinstance(result[0], list) else result[0]
                return plan

            return None

        except PGError as e:
            logger.warning(f"EXPLAIN failed for query: {e}")
            # Rollback on error
            if self.connection and not self.connection.closed:
                self.connection.rollback()
            return None
        except (json.JSONDecodeError, IndexError) as e:
            logger.error(f"Failed to parse EXPLAIN JSON: {e}")
            return None

    def collect_and_store(
        self,
        min_duration_ms: float = 1000.0,
        limit: int = 100
    ) -> int:
        """
        Collect slow queries and store them in the internal database.

        Args:
            min_duration_ms: Minimum query duration in milliseconds
            limit: Maximum number of queries to collect

        Returns:
            Number of queries collected and stored
        """
        if not self.connect():
            return 0

        try:
            # Fetch slow queries
            slow_queries = self.fetch_slow_queries(
                min_duration_ms=min_duration_ms,
                limit=limit
            )

            if not slow_queries:
                logger.info("No new slow queries found")
                return 0

            collected_count = 0

            with get_db_context() as db:
                for query_record in slow_queries:
                    try:
                        sql_text = query_record['query']

                        # Skip if empty
                        if not sql_text or not sql_text.strip():
                            continue

                        # Generate fingerprint
                        fingerprint, sql_hash = fingerprint_query(sql_text)

                        # Check if we already have this query pattern recently
                        # Note: pg_stat_statements aggregates executions, so we check by fingerprint
                        existing = db.query(SlowQueryRaw).filter(
                            SlowQueryRaw.source_db_type == 'postgres',
                            SlowQueryRaw.source_db_host == self.config.host,
                            SlowQueryRaw.fingerprint == fingerprint
                        ).first()

                        if existing:
                            logger.debug(f"Query pattern already exists, skipping: {sql_hash}")
                            continue

                        # Generate EXPLAIN plan
                        plan_json = self.generate_explain(sql_text)

                        # Create new record
                        slow_query = SlowQueryRaw(
                            source_db_type='postgres',
                            source_db_host=self.config.host,
                            source_db_name=self.config.database,
                            fingerprint=fingerprint,
                            full_sql=sql_text,
                            sql_hash=sql_hash,
                            duration_ms=Decimal(str(query_record['mean_exec_time'])),
                            rows_examined=query_record.get('shared_blks_read', 0) + query_record.get('shared_blks_hit', 0),
                            rows_returned=query_record.get('rows', 0),
                            plan_json=plan_json,
                            plan_text=None,  # Could store text format if needed
                            captured_at=datetime.utcnow(),
                            status='NEW'
                        )

                        db.add(slow_query)
                        collected_count += 1

                    except Exception as e:
                        logger.error(f"Error processing query: {e}")
                        continue

                db.commit()

            logger.info(f"✓ Collected and stored {collected_count} slow queries from PostgreSQL")
            return collected_count

        finally:
            self.disconnect()


# Example usage
if __name__ == "__main__":
    collector = PostgreSQLCollector()
    count = collector.collect_and_store(min_duration_ms=500.0)
    print(f"Collected {count} slow queries")
