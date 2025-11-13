"""
MySQL Slow Query Collector for Multi-Tenant Version.
Collects slow queries from MySQL slow_log and stores them in PostgreSQL.
"""
import mysql.connector
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging

from core.config import settings
from db.models_multitenant import SlowQuery, get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class MySQLCollectorMultiTenant:
    """Collects slow queries from MySQL slow_log table."""

    def __init__(self, organization_id: int, team_id: int, identity_id: Optional[int] = None):
        """
        Initialize collector with organization context.

        Args:
            organization_id: Organization ID for multi-tenant isolation
            team_id: Team ID within organization
            identity_id: Optional identity ID for tracking
        """
        self.organization_id = organization_id
        self.team_id = team_id
        self.identity_id = identity_id
        self.mysql_config = settings.get_mysql_dict()

    def get_connection(self):
        """Get MySQL connection with error handling."""
        try:
            return mysql.connector.connect(**self.mysql_config)
        except Exception as e:
            logger.error(f"Failed to connect to MySQL at {settings.mysql_host}:{settings.mysql_port}: {e}")
            return None

    def fingerprint_query(self, sql: str) -> str:
        """
        Generate a fingerprint hash for a SQL query.
        Normalizes the query by replacing literals with placeholders.
        """
        # Simple normalization: replace numbers and strings with ?
        import re
        normalized = sql
        normalized = re.sub(r'\b\d+\b', '?', normalized)  # Replace numbers
        normalized = re.sub(r"'[^']*'", '?', normalized)  # Replace strings
        normalized = re.sub(r'"[^"]*"', '?', normalized)  # Replace double-quoted strings
        normalized = re.sub(r'\s+', ' ', normalized)  # Normalize whitespace
        normalized = normalized.strip().lower()

        # Generate MD5 hash
        return hashlib.md5(normalized.encode()).hexdigest()

    def collect_slow_queries(
        self,
        lookback_minutes: int = 60,
        min_query_time: float = 1.0
    ) -> Dict[str, Any]:
        """
        Collect slow queries from MySQL slow_log.

        Args:
            lookback_minutes: How far back to look for queries (default: 60 minutes)
            min_query_time: Minimum query time in seconds (default: 1.0s)

        Returns:
            Dictionary with collection results
        """
        conn = self.get_connection()
        if not conn:
            return {
                "success": False,
                "error": "Could not connect to MySQL",
                "queries_collected": 0
            }

        try:
            cursor = conn.cursor(dictionary=True)

            # Calculate lookback timestamp
            lookback_time = datetime.utcnow() - timedelta(minutes=lookback_minutes)

            # Query slow_log table
            # MySQL slow_log structure: start_time, user_host, query_time, lock_time,
            # rows_sent, rows_examined, db, sql_text
            # Note: query_time is TIME type - we'll filter by time in Python to handle fractional seconds
            # Exclude monitoring/test/metadata queries (only REAL application queries)
            query = """
                SELECT
                    start_time,
                    user_host,
                    query_time,
                    lock_time,
                    rows_sent,
                    rows_examined,
                    db as database_name,
                    sql_text
                FROM mysql.slow_log
                WHERE start_time >= %s
                  AND sql_text NOT LIKE CONCAT('%%%%', 'slow_log', '%%%%')
                  AND sql_text NOT LIKE CONCAT('%%%%', 'SLEEP', '%%%%')
                  AND sql_text NOT LIKE CONCAT('%%%%', 'test query', '%%%%')
                  AND sql_text NOT LIKE CONCAT('%%%%', 'monitoring', '%%%%')
                  AND sql_text NOT LIKE CONCAT('%%%%', 'INFORMATION_SCHEMA', '%%%%')
                  AND sql_text NOT LIKE CONCAT('%%%%', 'information_schema', '%%%%')
                  AND sql_text NOT LIKE CONCAT('%%%%', 'PERFORMANCE_SCHEMA', '%%%%')
                  AND sql_text NOT LIKE CONCAT('%%%%', 'performance_schema', '%%%%')
                  AND sql_text NOT LIKE 'SHOW%'
                  AND sql_text NOT LIKE 'EXPLAIN%'
                ORDER BY start_time DESC
                LIMIT 1000
            """

            lookback_str = lookback_time.strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"Collecting queries since: {lookback_str} (lookback: {lookback_minutes} min, min_time: {min_query_time}s)")

            cursor.execute(query, (lookback_str,))
            rows = cursor.fetchall()

            logger.info(f"Found {len(rows)} rows in MySQL slow_log")

            cursor.close()
            conn.close()

            # Store queries in PostgreSQL
            db = next(get_db())
            queries_collected = 0
            queries_skipped = 0

            for row in rows:
                try:
                    # Convert query_time from timedelta to float (seconds)
                    query_time_seconds = row['query_time'].total_seconds() if isinstance(row['query_time'], timedelta) else float(row['query_time'])
                    lock_time_seconds = row['lock_time'].total_seconds() if isinstance(row['lock_time'], timedelta) else float(row['lock_time'])

                    # Filter by minimum query time (done in Python to handle fractional seconds correctly)
                    if query_time_seconds < min_query_time:
                        continue

                    # Get SQL text and decode if bytes
                    sql_text = row['sql_text']
                    if isinstance(sql_text, bytes):
                        sql_text = sql_text.decode('utf-8', errors='replace')

                    # Generate fingerprint
                    fingerprint = self.fingerprint_query(sql_text)

                    # Check if query already exists (by fingerprint and start_time)
                    existing = db.query(SlowQuery).filter(
                        SlowQuery.sql_fingerprint == fingerprint,
                        SlowQuery.start_time == row['start_time'],
                        SlowQuery.organization_id == self.organization_id
                    ).first()

                    if existing:
                        queries_skipped += 1
                        continue

                    # Create new slow query record
                    slow_query = SlowQuery(
                        sql_fingerprint=fingerprint,
                        sql_text=sql_text,
                        query_time=query_time_seconds,
                        lock_time=lock_time_seconds,
                        rows_examined=row['rows_examined'] or 0,
                        rows_sent=row['rows_sent'] or 0,
                        database_name=row['database_name'] or 'unknown',
                        user_host=row['user_host'] or 'unknown',
                        start_time=row['start_time'],
                        collected_at=datetime.utcnow(),
                        organization_id=self.organization_id,
                        team_id=self.team_id,
                        identity_id=self.identity_id
                    )

                    db.add(slow_query)
                    queries_collected += 1

                except Exception as e:
                    logger.error(f"Error processing query: {e}")
                    continue

            # Commit all changes
            db.commit()

            logger.info(
                f"MySQL collection complete: {queries_collected} collected, "
                f"{queries_skipped} skipped (duplicates)"
            )

            return {
                "success": True,
                "queries_collected": queries_collected,
                "queries_skipped": queries_skipped,
                "lookback_minutes": lookback_minutes,
                "min_query_time": min_query_time,
                "organization_id": self.organization_id,
                "team_id": self.team_id
            }

        except Exception as e:
            logger.error(f"Error collecting MySQL slow queries: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "queries_collected": 0
            }


def get_mysql_databases() -> Dict[str, Any]:
    """
    Get list of available databases from MySQL server.
    Excludes system databases.

    Returns:
        Dictionary with database list
    """
    try:
        conn = mysql.connector.connect(**settings.get_mysql_dict())
        cursor = conn.cursor()

        # Get all databases
        cursor.execute("SHOW DATABASES")
        rows = cursor.fetchall()
        all_databases = [str(row[0]) for row in rows]

        # Exclude system databases
        system_databases = {'mysql', 'information_schema', 'performance_schema', 'sys'}
        user_databases = [db for db in all_databases if db not in system_databases]

        cursor.close()
        conn.close()

        return {
            "success": True,
            "databases": user_databases,
            "total_databases": len(user_databases),
            "excluded_system_dbs": list(system_databases)
        }

    except Exception as e:
        logger.error(f"Failed to get MySQL databases: {e}")
        return {
            "success": False,
            "error": str(e),
            "databases": []
        }


def test_mysql_connection() -> Dict[str, Any]:
    """
    Test MySQL connection and slow_log table accessibility.

    Returns:
        Dictionary with connection test results
    """
    try:
        conn = mysql.connector.connect(**settings.get_mysql_dict())
        cursor = conn.cursor()

        # Test query
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]

        # Check slow_log table
        cursor.execute("SELECT COUNT(*) FROM mysql.slow_log")
        slow_log_count = cursor.fetchone()[0]

        # Check if slow_log is enabled
        cursor.execute("SHOW VARIABLES LIKE 'slow_query_log'")
        slow_log_enabled = cursor.fetchone()

        cursor.close()
        conn.close()

        return {
            "success": True,
            "mysql_version": version,
            "host": settings.mysql_host,
            "port": settings.mysql_port,
            "slow_log_count": slow_log_count,
            "slow_log_enabled": slow_log_enabled[1] if slow_log_enabled else 'unknown',
            "message": f"Successfully connected to MySQL {version}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "host": settings.mysql_host,
            "port": settings.mysql_port,
            "message": f"Failed to connect: {str(e)}"
        }
