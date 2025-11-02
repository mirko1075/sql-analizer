#!/usr/bin/env python3
"""
DBPower Collector Agent

On-premise agent that collects slow queries from MySQL and PostgreSQL databases
and sends them to the DBPower SaaS backend.
"""
import os
import sys
import time
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests
import mysql.connector
import psycopg2


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('dbpower-agent')


class DBPowerAgent:
    """
    Collector agent that monitors databases and sends slow queries to DBPower backend.
    """

    def __init__(self):
        """Initialize the agent with environment variables."""
        self.api_url = os.getenv('DBPOWER_API_URL', 'http://localhost:8000/api/v1')
        self.agent_token = os.getenv('DBPOWER_AGENT_TOKEN')
        self.collector_id = os.getenv('COLLECTOR_ID')  # Optional
        self.collection_interval = int(os.getenv('COLLECTION_INTERVAL_SECONDS', '300'))  # 5 minutes default
        self.heartbeat_interval = int(os.getenv('HEARTBEAT_INTERVAL_SECONDS', '60'))  # 1 minute default

        if not self.agent_token:
            logger.error("DBPOWER_AGENT_TOKEN environment variable is required")
            sys.exit(1)

        self.databases = []
        self.last_collection_time = {}  # Track last collection time per database
        self.last_heartbeat_time = None

        logger.info(f"DBPower Agent initialized")
        logger.info(f"API URL: {self.api_url}")
        logger.info(f"Collection interval: {self.collection_interval}s")
        logger.info(f"Heartbeat interval: {self.heartbeat_interval}s")

    def fetch_config(self) -> bool:
        """
        Fetch database configuration from the backend.

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Fetching database configuration from backend...")
            response = requests.get(
                f"{self.api_url}/collectors/config",
                params={'agent_token': self.agent_token},
                timeout=30
            )

            if response.status_code == 401:
                logger.error("Invalid agent token. Please check your DBPOWER_AGENT_TOKEN.")
                return False

            response.raise_for_status()
            config = response.json()

            self.databases = config.get('databases', [])
            logger.info(f"Configuration fetched successfully: {len(self.databases)} database(s) to monitor")

            for db in self.databases:
                logger.info(f"  - {db['name']} ({db['db_type']}://{db['host']}:{db['port']}/{db['database_name']})")

            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch configuration: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error fetching configuration: {e}")
            return False

    def send_heartbeat(self) -> bool:
        """
        Send heartbeat to the backend.

        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.api_url}/collectors/heartbeat",
                params={'agent_token': self.agent_token},
                json={
                    'status': 'ACTIVE',
                    'metrics': {
                        'databases_monitored': len(self.databases),
                        'uptime_seconds': int(time.time())
                    }
                },
                timeout=10
            )

            response.raise_for_status()
            self.last_heartbeat_time = datetime.utcnow()
            logger.debug("Heartbeat sent successfully")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send heartbeat: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending heartbeat: {e}")
            return False

    def collect_mysql_slow_queries(self, db_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Collect slow queries from MySQL database.

        Args:
            db_config: Database configuration

        Returns:
            List of slow query records
        """
        queries = []
        conn = None

        try:
            logger.debug(f"Connecting to MySQL: {db_config['host']}:{db_config['port']}")

            # Connect to MySQL
            conn = mysql.connector.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database_name'],
                user=db_config['username'],
                password=db_config['password'],
                connect_timeout=10
            )

            cursor = conn.cursor(dictionary=True)

            # Get slow queries from performance_schema
            # Note: This requires MySQL performance_schema to be enabled
            query = """
                SELECT
                    DIGEST_TEXT as query_text,
                    COUNT_STAR as exec_count,
                    AVG_TIMER_WAIT / 1000000000 as avg_duration_ms,
                    MAX_TIMER_WAIT / 1000000000 as max_duration_ms,
                    SUM_ROWS_EXAMINED as rows_examined,
                    SUM_ROWS_SENT as rows_returned
                FROM performance_schema.events_statements_summary_by_digest
                WHERE DIGEST_TEXT IS NOT NULL
                  AND AVG_TIMER_WAIT > 1000000000  -- Queries slower than 1 second
                ORDER BY AVG_TIMER_WAIT DESC
                LIMIT 50
            """

            cursor.execute(query)
            results = cursor.fetchall()

            for row in results:
                # Create fingerprint (hash of normalized query)
                fingerprint = row['query_text'] or ''
                sql_hash = hashlib.sha256(fingerprint.encode()).hexdigest()

                queries.append({
                    'fingerprint': fingerprint,
                    'full_sql': fingerprint,  # In this case, they're the same
                    'duration_ms': float(row['avg_duration_ms'] or 0),
                    'rows_examined': int(row['rows_examined'] or 0),
                    'rows_returned': int(row['rows_returned'] or 0),
                    'captured_at': datetime.utcnow().isoformat() + 'Z',
                    'plan_json': None,
                    'plan_text': None
                })

            cursor.close()
            logger.info(f"Collected {len(queries)} slow queries from MySQL: {db_config['name']}")

        except mysql.connector.Error as e:
            logger.error(f"MySQL error collecting from {db_config['name']}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error collecting from MySQL {db_config['name']}: {e}")
        finally:
            if conn and conn.is_connected():
                conn.close()

        return queries

    def collect_postgres_slow_queries(self, db_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Collect slow queries from PostgreSQL database.

        Args:
            db_config: Database configuration

        Returns:
            List of slow query records
        """
        queries = []
        conn = None

        try:
            logger.debug(f"Connecting to PostgreSQL: {db_config['host']}:{db_config['port']}")

            # Connect to PostgreSQL
            conn_string = (
                f"host={db_config['host']} "
                f"port={db_config['port']} "
                f"dbname={db_config['database_name']} "
                f"user={db_config['username']} "
                f"password={db_config['password']} "
                f"connect_timeout=10"
            )

            if db_config.get('ssl_enabled'):
                conn_string += " sslmode=require"

            conn = psycopg2.connect(conn_string)
            cursor = conn.cursor()

            # Get slow queries from pg_stat_statements
            # Note: This requires pg_stat_statements extension to be enabled
            query = """
                SELECT
                    query,
                    calls as exec_count,
                    mean_exec_time as avg_duration_ms,
                    max_exec_time as max_duration_ms,
                    rows as rows_returned
                FROM pg_stat_statements
                WHERE mean_exec_time > 1000  -- Queries slower than 1 second
                  AND query NOT LIKE '%pg_stat_statements%'
                ORDER BY mean_exec_time DESC
                LIMIT 50
            """

            cursor.execute(query)
            results = cursor.fetchall()

            for row in results:
                # Create fingerprint (hash of normalized query)
                query_text = row[0] or ''
                fingerprint = query_text
                sql_hash = hashlib.sha256(fingerprint.encode()).hexdigest()

                queries.append({
                    'fingerprint': fingerprint,
                    'full_sql': query_text,
                    'duration_ms': float(row[2] or 0),
                    'rows_examined': None,  # PostgreSQL doesn't expose this easily
                    'rows_returned': int(row[4] or 0),
                    'captured_at': datetime.utcnow().isoformat() + 'Z',
                    'plan_json': None,
                    'plan_text': None
                })

            cursor.close()
            logger.info(f"Collected {len(queries)} slow queries from PostgreSQL: {db_config['name']}")

        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error collecting from {db_config['name']}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error collecting from PostgreSQL {db_config['name']}: {e}")
        finally:
            if conn:
                conn.close()

        return queries

    def collect_slow_queries(self, db_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Collect slow queries from a database based on its type.

        Args:
            db_config: Database configuration

        Returns:
            List of slow query records
        """
        db_type = db_config['db_type'].lower()

        if db_type == 'mysql':
            return self.collect_mysql_slow_queries(db_config)
        elif db_type in ['postgres', 'postgresql']:
            return self.collect_postgres_slow_queries(db_config)
        else:
            logger.warning(f"Unsupported database type: {db_type}")
            return []

    def send_slow_queries(self, queries: List[Dict[str, Any]]) -> bool:
        """
        Send collected slow queries to the backend.

        Args:
            queries: List of slow query records

        Returns:
            True if successful, False otherwise
        """
        if not queries:
            return True

        try:
            response = requests.post(
                f"{self.api_url}/collectors/ingest/slow-queries",
                json={
                    'agent_token': self.agent_token,
                    'queries': queries,
                    'metadata': {
                        'collector_version': '1.0.0',
                        'collection_time': datetime.utcnow().isoformat() + 'Z'
                    }
                },
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            logger.info(
                f"Sent {result.get('queries_received', 0)} queries to backend: "
                f"{result.get('queries_stored', 0)} stored, "
                f"{result.get('queries_skipped', 0)} skipped"
            )

            if result.get('errors'):
                for error in result['errors']:
                    logger.warning(f"Backend error: {error}")

            return result.get('success', False)

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send slow queries: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending slow queries: {e}")
            return False

    def run_collection_cycle(self):
        """Run a single collection cycle for all databases."""
        logger.info("Starting collection cycle...")

        for db_config in self.databases:
            db_id = db_config['id']
            db_name = db_config['name']

            try:
                # Collect slow queries
                queries = self.collect_slow_queries(db_config)

                # Send to backend
                if queries:
                    self.send_slow_queries(queries)
                else:
                    logger.info(f"No slow queries found for {db_name}")

                # Update last collection time
                self.last_collection_time[db_id] = datetime.utcnow()

            except Exception as e:
                logger.error(f"Error in collection cycle for {db_name}: {e}")

        logger.info("Collection cycle completed")

    def run(self):
        """Main agent loop."""
        logger.info("=" * 60)
        logger.info("DBPower Collector Agent Starting")
        logger.info("=" * 60)

        # Initial configuration fetch
        if not self.fetch_config():
            logger.error("Failed to fetch initial configuration. Retrying in 60 seconds...")
            time.sleep(60)
            if not self.fetch_config():
                logger.error("Still unable to fetch configuration. Exiting.")
                sys.exit(1)

        # Initial heartbeat
        self.send_heartbeat()

        logger.info("Agent is now running. Press Ctrl+C to stop.")
        logger.info("=" * 60)

        last_collection = time.time()
        last_heartbeat = time.time()
        last_config_refresh = time.time()

        try:
            while True:
                current_time = time.time()

                # Refresh configuration every 5 minutes
                if current_time - last_config_refresh >= 300:
                    self.fetch_config()
                    last_config_refresh = current_time

                # Send heartbeat
                if current_time - last_heartbeat >= self.heartbeat_interval:
                    self.send_heartbeat()
                    last_heartbeat = current_time

                # Run collection cycle
                if current_time - last_collection >= self.collection_interval:
                    self.run_collection_cycle()
                    last_collection = current_time

                # Sleep for a short time to avoid busy-waiting
                time.sleep(10)

        except KeyboardInterrupt:
            logger.info("\nShutting down agent...")
            logger.info("Goodbye!")
        except Exception as e:
            logger.error(f"Fatal error in main loop: {e}", exc_info=True)
            sys.exit(1)


if __name__ == '__main__':
    agent = DBPowerAgent()
    agent.run()
