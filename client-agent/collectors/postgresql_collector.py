"""
PostgreSQL slow query collector.
Collects slow queries from pg_stat_statements extension.
"""
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2 import Error
import logging

from .base import BaseCollector, SlowQuery


logger = logging.getLogger(__name__)


class PostgreSQLCollector(BaseCollector):
    """
    PostgreSQL slow query collector.

    Uses pg_stat_statements extension to collect slow queries.
    Requires pg_stat_statements to be installed and configured.
    """

    def connect(self) -> bool:
        """
        Connect to PostgreSQL database.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.connection = psycopg2.connect(
                host=self.config['host'],
                port=self.config.get('port', 5432),
                user=self.config['user'],
                password=self.config['password'],
                database=self.config.get('database', 'postgres'),
                sslmode='require' if self.config.get('ssl', False) else 'prefer',
            )

            logger.info(
                f"Connected to PostgreSQL: {self.config['host']}:{self.config.get('port', 5432)}"
            )
            return True

        except Error as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            return False

    def disconnect(self):
        """Disconnect from PostgreSQL database."""
        if self.connection and not self.connection.closed:
            self.connection.close()
            logger.info("Disconnected from PostgreSQL")

    def is_connected(self) -> bool:
        """
        Check if connected to PostgreSQL.

        Returns:
            True if connected, False otherwise
        """
        return self.connection is not None and not self.connection.closed

    def test_connection(self) -> bool:
        """
        Test PostgreSQL connection.

        Returns:
            True if connection is working, False otherwise
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True
        except Error as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def get_database_version(self) -> Optional[str]:
        """
        Get PostgreSQL version string.

        Returns:
            PostgreSQL version or None if unavailable
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            cursor.close()
            return version
        except Error as e:
            logger.error(f"Failed to get PostgreSQL version: {e}")
            return None

    def check_pg_stat_statements_enabled(self) -> bool:
        """
        Check if pg_stat_statements extension is enabled.

        Returns:
            True if pg_stat_statements is enabled, False otherwise
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                )
            """)
            enabled = cursor.fetchone()[0]
            cursor.close()

            if not enabled:
                logger.warning("pg_stat_statements extension is not enabled")

            return enabled

        except Error as e:
            logger.error(f"Failed to check pg_stat_statements: {e}")
            return False

    def collect_slow_queries(
        self,
        threshold: float = 1.0,
        limit: int = 100
    ) -> List[SlowQuery]:
        """
        Collect slow queries from pg_stat_statements.

        Args:
            threshold: Minimum query time in seconds (mean_exec_time)
            limit: Maximum number of queries to collect

        Returns:
            List of SlowQuery objects
        """
        if not self.is_connected():
            logger.error("Not connected to PostgreSQL")
            return []

        # Check if pg_stat_statements is enabled
        if not self.check_pg_stat_statements_enabled():
            logger.error("pg_stat_statements extension is not enabled")
            return []

        queries = []

        try:
            cursor = self.connection.cursor()

            # Query pg_stat_statements
            # Convert milliseconds to seconds
            sql = """
                SELECT
                    query,
                    mean_exec_time / 1000 as query_time,
                    calls,
                    rows,
                    (blk_read_time + blk_write_time) / 1000 as lock_time
                FROM pg_stat_statements
                WHERE mean_exec_time >= %s * 1000
                  AND query NOT LIKE '%%pg_stat_statements%%'
                ORDER BY mean_exec_time DESC
                LIMIT %s
            """

            cursor.execute(sql, (threshold, limit))
            rows = cursor.fetchall()

            for row in rows:
                query = SlowQuery(
                    sql_text=row[0],
                    sql_fingerprint='',  # Will be generated in __post_init__
                    query_time=float(row[1]),
                    lock_time=float(row[4]) if row[4] else 0.0,
                    rows_sent=int(row[3]) if row[3] else 0,
                    rows_examined=int(row[3]) if row[3] else 0,  # PostgreSQL doesn't track examined separately
                    database_name=self.config.get('database'),
                    user_host=None,  # Not available in pg_stat_statements
                    start_time=None,  # Not available in pg_stat_statements
                )
                queries.append(query)

            cursor.close()

            logger.info(f"Collected {len(queries)} slow queries from PostgreSQL")

        except Error as e:
            logger.error(f"Failed to collect slow queries: {e}")

        return queries

    def get_pg_stat_statements_config(self) -> Dict[str, Any]:
        """
        Get pg_stat_statements configuration.

        Returns:
            Dictionary with pg_stat_statements configuration
        """
        config = {
            'pg_stat_statements.max': None,
            'pg_stat_statements.track': None,
            'pg_stat_statements.track_utility': None,
        }

        try:
            cursor = self.connection.cursor()

            settings = [
                'pg_stat_statements.max',
                'pg_stat_statements.track',
                'pg_stat_statements.track_utility',
            ]

            for setting in settings:
                cursor.execute(
                    "SELECT current_setting(%s, true)",
                    (setting,)
                )
                result = cursor.fetchone()
                if result:
                    config[setting] = result[0]

            cursor.close()

        except Error as e:
            logger.error(f"Failed to get pg_stat_statements configuration: {e}")

        return config

    def reset_pg_stat_statements(self) -> bool:
        """
        Reset pg_stat_statements (clear all statistics).

        Warning: This will delete all query statistics!

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT pg_stat_statements_reset()")
            self.connection.commit()
            cursor.close()
            logger.info("Reset pg_stat_statements")
            return True

        except Error as e:
            logger.error(f"Failed to reset pg_stat_statements: {e}")
            return False
