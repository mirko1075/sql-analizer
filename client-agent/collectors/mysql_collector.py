"""
MySQL slow query collector.
Collects slow queries from MySQL slow_log table.
"""
from typing import List, Dict, Any, Optional
import mysql.connector
from mysql.connector import Error
import logging

from .base import BaseCollector, SlowQuery


logger = logging.getLogger(__name__)


class MySQLCollector(BaseCollector):
    """
    MySQL slow query collector.

    Connects to MySQL database and collects slow queries from the slow_log table.
    Requires slow_query_log to be enabled with log_output=TABLE.
    """

    def connect(self) -> bool:
        """
        Connect to MySQL database.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.connection = mysql.connector.connect(
                host=self.config['host'],
                port=self.config.get('port', 3306),
                user=self.config['user'],
                password=self.config['password'],
                database=self.config.get('database', 'mysql'),
                ssl_disabled=not self.config.get('ssl', False),
            )

            logger.info(
                f"Connected to MySQL: {self.config['host']}:{self.config.get('port', 3306)}"
            )
            return True

        except Error as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            return False

    def disconnect(self):
        """Disconnect from MySQL database."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("Disconnected from MySQL")

    def is_connected(self) -> bool:
        """
        Check if connected to MySQL.

        Returns:
            True if connected, False otherwise
        """
        return self.connection is not None and self.connection.is_connected()

    def test_connection(self) -> bool:
        """
        Test MySQL connection.

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
        Get MySQL version string.

        Returns:
            MySQL version or None if unavailable
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            cursor.close()
            return version
        except Error as e:
            logger.error(f"Failed to get MySQL version: {e}")
            return None

    def collect_slow_queries(
        self,
        threshold: float = 1.0,
        limit: int = 100
    ) -> List[SlowQuery]:
        """
        Collect slow queries from MySQL slow_log table.

        Args:
            threshold: Minimum query time in seconds
            limit: Maximum number of queries to collect

        Returns:
            List of SlowQuery objects
        """
        if not self.is_connected():
            logger.error("Not connected to MySQL")
            return []

        queries = []

        try:
            cursor = self.connection.cursor(dictionary=True)

            # Query the slow_log table
            # Note: Requires slow_query_log=1 and log_output=TABLE
            sql = """
                SELECT
                    sql_text,
                    query_time,
                    lock_time,
                    rows_sent,
                    rows_examined,
                    db AS database_name,
                    user_host,
                    start_time
                FROM mysql.slow_log
                WHERE query_time >= %s
                  AND sql_text NOT LIKE 'SELECT%%slow_log%%'
                ORDER BY start_time DESC
                LIMIT %s
            """

            cursor.execute(sql, (threshold, limit))
            rows = cursor.fetchall()

            for row in rows:
                query = SlowQuery(
                    sql_text=row['sql_text'],
                    sql_fingerprint='',  # Will be generated in __post_init__
                    query_time=float(row['query_time']),
                    lock_time=float(row.get('lock_time', 0.0)),
                    rows_sent=int(row.get('rows_sent', 0)),
                    rows_examined=int(row.get('rows_examined', 0)),
                    database_name=row.get('database_name'),
                    user_host=row.get('user_host'),
                    start_time=row.get('start_time'),
                )
                queries.append(query)

            cursor.close()

            logger.info(f"Collected {len(queries)} slow queries from MySQL")

        except Error as e:
            logger.error(f"Failed to collect slow queries: {e}")

        return queries

    def check_slow_log_enabled(self) -> bool:
        """
        Check if MySQL slow query log is enabled.

        Returns:
            True if slow query log is enabled, False otherwise
        """
        try:
            cursor = self.connection.cursor()

            # Check if slow_query_log is enabled
            cursor.execute("SHOW VARIABLES LIKE 'slow_query_log'")
            result = cursor.fetchone()
            slow_log_enabled = result and result[1].upper() == 'ON'

            # Check if log_output includes TABLE
            cursor.execute("SHOW VARIABLES LIKE 'log_output'")
            result = cursor.fetchone()
            log_output = result[1] if result else ''

            cursor.close()

            if not slow_log_enabled:
                logger.warning("MySQL slow_query_log is not enabled")
                return False

            if 'TABLE' not in log_output.upper():
                logger.warning("MySQL log_output does not include TABLE")
                return False

            return True

        except Error as e:
            logger.error(f"Failed to check slow log configuration: {e}")
            return False

    def get_slow_log_config(self) -> Dict[str, Any]:
        """
        Get MySQL slow query log configuration.

        Returns:
            Dictionary with slow log configuration
        """
        config = {
            'slow_query_log': None,
            'slow_query_log_file': None,
            'long_query_time': None,
            'log_output': None,
            'log_queries_not_using_indexes': None,
        }

        try:
            cursor = self.connection.cursor()

            variables = [
                'slow_query_log',
                'slow_query_log_file',
                'long_query_time',
                'log_output',
                'log_queries_not_using_indexes',
            ]

            for var in variables:
                cursor.execute(f"SHOW VARIABLES LIKE '{var}'")
                result = cursor.fetchone()
                if result:
                    config[var] = result[1]

            cursor.close()

        except Error as e:
            logger.error(f"Failed to get slow log configuration: {e}")

        return config

    def clear_slow_log(self) -> bool:
        """
        Clear MySQL slow_log table.

        Warning: This will delete all slow query records!

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("TRUNCATE TABLE mysql.slow_log")
            cursor.close()
            logger.info("Cleared MySQL slow_log table")
            return True

        except Error as e:
            logger.error(f"Failed to clear slow_log table: {e}")
            return False
