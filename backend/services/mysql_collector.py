"""
MySQL slow query collector.

Collects slow queries from MySQL's slow_log table and generates EXPLAIN plans.
"""
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from decimal import Decimal
from uuid import UUID

import mysql.connector
from mysql.connector import Error as MySQLError

from backend.core.config import settings
from backend.core.logger import get_logger
from backend.db.session import get_db_context
from backend.db.models import SlowQueryRaw
from backend.services.fingerprint import fingerprint_query, is_query_safe_to_explain

logger = get_logger(__name__)


class MySQLCollector:
    """
    Collector for MySQL slow queries.

    Connects to MySQL, reads from mysql.slow_log table, and generates
    EXPLAIN plans for slow queries.
    """

    def __init__(
        self,
        database_connection_id: Optional[UUID] = None,
        team_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None
    ):
        """
        Initialize MySQL collector with configuration.

        Args:
            database_connection_id: UUID of the database connection in the system
            team_id: UUID of the team this collector belongs to
            organization_id: UUID of the organization this collector belongs to
        """
        self.config = settings.mysql_lab
        self.connection = None
        self.database_connection_id = database_connection_id
        self.team_id = team_id
        self.organization_id = organization_id

    def connect(self) -> bool:
        """
        Establish connection to MySQL database.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.connection = mysql.connector.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                autocommit=True
            )
            logger.info(f"✓ Connected to MySQL: {self.config.host}:{self.config.port}")
            return True
        except MySQLError as e:
            logger.error(f"✗ MySQL connection failed: {e}")
            return False

    def disconnect(self):
        """Close MySQL connection."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("MySQL connection closed")

    def fetch_slow_queries(self, since: Optional[datetime] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch slow queries from mysql.slow_log table.

        Args:
            since: Only fetch queries after this timestamp (default: last hour)
            limit: Maximum number of queries to fetch

        Returns:
            List of slow query records
        """
        if not self.connection or not self.connection.is_connected():
            logger.error("Not connected to MySQL")
            return []

        try:
            cursor = self.connection.cursor(dictionary=True)

            # Build query
            query = """
                SELECT
                    start_time,
                    user_host,
                    query_time,
                    lock_time,
                    rows_sent,
                    rows_examined,
                    db,
                    sql_text
                FROM mysql.slow_log
                WHERE 1=1
            """

            params = []

            if since:
                query += " AND start_time > %s"
                params.append(since)

            query += " ORDER BY start_time DESC LIMIT %s"
            params.append(limit)

            cursor.execute(query, params)
            results = cursor.fetchall()
            cursor.close()

            logger.info(f"Fetched {len(results)} slow queries from MySQL")
            return results

        except MySQLError as e:
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

        if not self.connection or not self.connection.is_connected():
            logger.error("Not connected to MySQL")
            return None

        try:
            cursor = self.connection.cursor()

            # Use EXPLAIN FORMAT=JSON for structured output
            explain_query = f"EXPLAIN FORMAT=JSON {sql}"
            cursor.execute(explain_query)

            result = cursor.fetchone()
            cursor.close()

            if result and result[0]:
                # Parse JSON string
                plan = json.loads(result[0])
                return plan

            return None

        except MySQLError as e:
            logger.warning(f"EXPLAIN failed for query: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse EXPLAIN JSON: {e}")
            return None

    def collect_and_store(self, since: Optional[datetime] = None) -> int:
        """
        Collect slow queries and store them in the internal database.

        Args:
            since: Only collect queries after this timestamp

        Returns:
            Number of queries collected and stored
        """
        if not self.connect():
            return 0

        try:
            # Fetch slow queries
            slow_queries = self.fetch_slow_queries(since=since)

            if not slow_queries:
                logger.info("No new slow queries found")
                return 0

            collected_count = 0

            with get_db_context() as db:
                for query_record in slow_queries:
                    try:
                        sql_text = query_record['sql_text']

                        # Skip if empty
                        if not sql_text or not sql_text.strip():
                            continue

                        # Generate fingerprint
                        fingerprint, sql_hash = fingerprint_query(sql_text)

                        # Check if we already have this exact query execution
                        existing = db.query(SlowQueryRaw).filter(
                            SlowQueryRaw.source_db_type == 'mysql',
                            SlowQueryRaw.source_db_host == self.config.host,
                            SlowQueryRaw.sql_hash == sql_hash,
                            SlowQueryRaw.captured_at == query_record['start_time']
                        ).first()

                        if existing:
                            logger.debug(f"Query already exists, skipping: {sql_hash}")
                            continue

                        # Generate EXPLAIN plan
                        plan_json = self.generate_explain(sql_text)

                        # Convert query_time (timedelta) to milliseconds
                        query_time_ms = query_record['query_time'].total_seconds() * 1000

                        # Create new record
                        slow_query = SlowQueryRaw(
                            database_connection_id=self.database_connection_id,
                            team_id=self.team_id,
                            organization_id=self.organization_id,
                            source_db_type='mysql',
                            source_db_host=self.config.host,
                            source_db_name=query_record['db'] or self.config.database,
                            fingerprint=fingerprint,
                            full_sql=sql_text,
                            sql_hash=sql_hash,
                            duration_ms=Decimal(str(query_time_ms)),
                            rows_examined=query_record['rows_examined'],
                            rows_returned=query_record['rows_sent'],
                            plan_json=plan_json,
                            plan_text=None,  # Could store text format if needed
                            captured_at=query_record['start_time'],
                            status='NEW'
                        )

                        db.add(slow_query)
                        collected_count += 1

                    except Exception as e:
                        logger.error(f"Error processing query: {e}")
                        continue

                db.commit()

            logger.info(f"✓ Collected and stored {collected_count} slow queries from MySQL")
            return collected_count

        finally:
            self.disconnect()


# Example usage
if __name__ == "__main__":
    collector = MySQLCollector()
    count = collector.collect_and_store()
    print(f"Collected {count} slow queries")
