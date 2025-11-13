#!/usr/bin/env python3
"""
DBPower AI Cloud - Collector Agent

Standalone agent that monitors external databases and collects slow queries.
Communicates with the backend API via REST.
"""
import asyncio
import os
import sys
import time
import logging
import argparse
from datetime import datetime
from typing import Optional, Dict, Any
import json

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("collector_agent")


class CollectorAgent:
    """
    Standalone collector agent that monitors a database and reports to backend.
    """

    def __init__(
        self,
        collector_id: int,
        api_key: str,
        backend_url: str,
        db_type: str,
        db_config: Dict[str, Any],
        heartbeat_interval: int = 30,
        collection_interval: int = 300
    ):
        """
        Initialize collector agent.

        Args:
            collector_id: Collector ID from backend
            api_key: API key for authentication
            backend_url: Backend API URL (e.g., http://localhost:8000)
            db_type: Database type (mysql or postgres)
            db_config: Database connection configuration
            heartbeat_interval: Heartbeat interval in seconds (default: 30)
            collection_interval: Collection interval in seconds (default: 300 = 5 minutes)
        """
        self.collector_id = collector_id
        self.api_key = api_key
        self.backend_url = backend_url.rstrip('/')
        self.db_type = db_type
        self.db_config = db_config
        self.heartbeat_interval = heartbeat_interval
        self.collection_interval = collection_interval

        # State
        self.is_running = False
        self.is_collecting = False
        self.last_collection_time = 0
        self.stats = {
            "queries_collected": 0,
            "errors_count": 0,
            "uptime_seconds": 0,
            "last_error": None
        }
        self.start_time = time.time()

        # HTTP session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Database connection (lazy init)
        self.db_connection = None

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with API key."""
        return {
            "X-Collector-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    def send_heartbeat(self) -> Optional[list]:
        """
        Send heartbeat to backend.

        Returns:
            List of pending commands, or None if heartbeat failed
        """
        try:
            # Update stats
            self.stats["uptime_seconds"] = int(time.time() - self.start_time)

            url = f"{self.backend_url}/api/v1/collectors/{self.collector_id}/heartbeat"
            response = self.session.post(
                url,
                headers=self._get_headers(),
                json={
                    "stats": self.stats,
                    "error": self.stats.get("last_error")
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                commands = data.get("commands", [])
                if commands:
                    logger.info(f"Received {len(commands)} pending commands")
                return commands
            else:
                logger.error(f"Heartbeat failed: HTTP {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}")
            self.stats["errors_count"] += 1
            self.stats["last_error"] = str(e)
            return None

    def execute_command(self, command: Dict[str, Any]):
        """
        Execute a command from the backend.

        Args:
            command: Command dictionary with 'id', 'command', and 'params'
        """
        command_id = command["id"]
        command_type = command["command"]
        params = command.get("params", {})

        logger.info(f"Executing command: {command_type} (ID: {command_id})")

        success = False
        result = {}

        try:
            if command_type == "start":
                self.is_collecting = True
                success = True
                result["message"] = "Collection started"

            elif command_type == "stop":
                self.is_collecting = False
                success = True
                result["message"] = "Collection stopped"

            elif command_type == "collect":
                # Trigger immediate collection
                count = self.collect_slow_queries()
                success = True
                result["queries_collected"] = count

            elif command_type == "update_config":
                # Update configuration
                if "db_config" in params:
                    self.db_config.update(params["db_config"])
                    self.db_connection = None  # Reset connection
                    success = True
                    result["message"] = "Configuration updated"

            else:
                logger.warning(f"Unknown command type: {command_type}")
                result["error"] = f"Unknown command: {command_type}"

        except Exception as e:
            logger.error(f"Error executing command {command_type}: {e}", exc_info=True)
            result["error"] = str(e)

        # Report execution result
        self.report_command_execution(command_id, success, result)

    def report_command_execution(self, command_id: int, success: bool, result: Dict[str, Any]):
        """Report command execution result to backend."""
        try:
            url = f"{self.backend_url}/api/v1/collectors/{self.collector_id}/commands/{command_id}/execute"
            response = self.session.post(
                url,
                headers=self._get_headers(),
                json={
                    "command_id": command_id,
                    "success": success,
                    "result": result
                },
                timeout=10
            )

            if response.status_code != 200:
                logger.error(f"Failed to report command execution: HTTP {response.status_code}")

        except Exception as e:
            logger.error(f"Error reporting command execution: {e}")

    def collect_slow_queries(self) -> int:
        """
        Collect slow queries from the database.

        Returns:
            Number of queries collected
        """
        logger.info("Starting slow query collection...")

        try:
            if self.db_type == "mysql":
                return self._collect_mysql_queries()
            elif self.db_type == "postgres":
                return self._collect_postgres_queries()
            else:
                raise ValueError(f"Unsupported database type: {self.db_type}")

        except Exception as e:
            logger.error(f"Error collecting slow queries: {e}", exc_info=True)
            self.stats["errors_count"] += 1
            self.stats["last_error"] = str(e)
            return 0

    def _collect_mysql_queries(self) -> int:
        """Collect slow queries from MySQL slow_log table."""
        try:
            import mysql.connector

            # Connect to MySQL
            if not self.db_connection:
                self.db_connection = mysql.connector.connect(
                    host=self.db_config.get("host", "localhost"),
                    port=self.db_config.get("port", 3306),
                    user=self.db_config.get("user"),
                    password=self.db_config.get("password"),
                    database="mysql",  # slow_log is in mysql database
                    use_pure=True,  # Use pure Python implementation to avoid SSL compatibility issues
                    ssl_disabled=True  # Disable SSL for local development
                )
                logger.info(f"Connected to MySQL at {self.db_config.get('host')}")

            cursor = self.db_connection.cursor(dictionary=True)

            # Get slow queries from last collection interval
            lookback_seconds = self.collection_interval + 60  # Add buffer
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
                WHERE start_time >= NOW() - INTERVAL %s SECOND
                  AND sql_text NOT LIKE %s
                  AND sql_text NOT LIKE %s
                ORDER BY start_time DESC
                LIMIT 100
            """

            cursor.execute(query, (lookback_seconds, '%slow_log%', '%SLEEP%'))
            queries = cursor.fetchall()
            cursor.close()

            if not queries:
                logger.info("No new slow queries found")
                return 0

            # Convert non-JSON-serializable objects for JSON serialization
            from datetime import datetime, timedelta
            for query_data in queries:
                # Iterate through all fields and convert as needed
                for key, value in list(query_data.items()):
                    if isinstance(value, datetime):
                        # Convert datetime to ISO format string
                        query_data[key] = value.isoformat()
                    elif isinstance(value, timedelta):
                        # Convert timedelta to seconds (float)
                        query_data[key] = value.total_seconds()
                    elif isinstance(value, bytes):
                        # Convert bytes to string
                        query_data[key] = value.decode('utf-8', errors='replace')

            # Send queries to backend
            count = self._send_queries_to_backend(queries)
            self.stats["queries_collected"] += count
            self.last_collection_time = time.time()

            logger.info(f"Collected {count} MySQL slow queries")
            return count

        except Exception as e:
            logger.error(f"Error collecting MySQL queries: {e}", exc_info=True)
            self.db_connection = None  # Reset connection on error
            raise

    def _collect_postgres_queries(self) -> int:
        """Collect slow queries from PostgreSQL pg_stat_statements."""
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor

            # Connect to PostgreSQL
            if not self.db_connection:
                self.db_connection = psycopg2.connect(
                    host=self.db_config.get("host", "localhost"),
                    port=self.db_config.get("port", 5432),
                    user=self.db_config.get("user"),
                    password=self.db_config.get("password"),
                    database=self.db_config.get("database", "postgres")
                )
                logger.info(f"Connected to PostgreSQL at {self.db_config.get('host')}")

            cursor = self.db_connection.cursor(cursor_factory=RealDictCursor)

            # Get slow queries from pg_stat_statements
            min_exec_time_ms = self.db_config.get("min_exec_time_ms", 500)
            query = """
                SELECT
                    query,
                    calls,
                    total_exec_time,
                    mean_exec_time,
                    max_exec_time,
                    rows
                FROM pg_stat_statements
                WHERE mean_exec_time > %s
                ORDER BY mean_exec_time DESC
                LIMIT 100
            """

            cursor.execute(query, (min_exec_time_ms,))
            queries = cursor.fetchall()
            cursor.close()

            if not queries:
                logger.info("No new slow queries found")
                return 0

            # Send queries to backend
            count = self._send_queries_to_backend(queries)
            self.stats["queries_collected"] += count
            self.last_collection_time = time.time()

            logger.info(f"Collected {count} PostgreSQL slow queries")
            return count

        except Exception as e:
            logger.error(f"Error collecting PostgreSQL queries: {e}", exc_info=True)
            self.db_connection = None  # Reset connection on error
            raise

    def _send_queries_to_backend(self, queries: list) -> int:
        """
        Send collected queries to backend API.

        Args:
            queries: List of query dictionaries

        Returns:
            Number of queries successfully sent
        """
        try:
            url = f"{self.backend_url}/api/v1/queries/bulk"
            response = self.session.post(
                url,
                headers=self._get_headers(),
                json={"queries": queries},
                timeout=30
            )

            if response.status_code in [200, 201]:
                data = response.json()
                return data.get("count", len(queries))
            else:
                logger.error(f"Failed to send queries: HTTP {response.status_code} - {response.text}")
                return 0

        except Exception as e:
            logger.error(f"Error sending queries to backend: {e}")
            return 0

    async def run(self):
        """Main agent loop."""
        logger.info(f"Starting Collector Agent (ID: {self.collector_id})")
        logger.info(f"Backend: {self.backend_url}")
        logger.info(f"Database: {self.db_type} at {self.db_config.get('host')}")
        logger.info(f"Heartbeat interval: {self.heartbeat_interval}s")
        logger.info(f"Collection interval: {self.collection_interval}s")

        self.is_running = True
        self.is_collecting = True  # Auto-collect by default

        last_heartbeat = 0
        last_collection = 0

        while self.is_running:
            try:
                current_time = time.time()

                # Send heartbeat
                if current_time - last_heartbeat >= self.heartbeat_interval:
                    commands = self.send_heartbeat()
                    last_heartbeat = current_time

                    # Execute pending commands
                    if commands:
                        for command in commands:
                            self.execute_command(command)

                # Automatic collection
                if self.is_collecting and current_time - last_collection >= self.collection_interval:
                    self.collect_slow_queries()
                    last_collection = current_time

                # Sleep briefly
                await asyncio.sleep(1)

            except KeyboardInterrupt:
                logger.info("Shutting down...")
                self.is_running = False
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(5)

        # Cleanup
        if self.db_connection:
            try:
                self.db_connection.close()
            except:
                pass

        logger.info("Collector Agent stopped")

    def stop(self):
        """Stop the agent."""
        self.is_running = False


def load_config(config_file: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    with open(config_file, 'r') as f:
        return json.load(f)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='DBPower AI Cloud - Collector Agent')
    parser.add_argument('--config', required=True, help='Configuration file path (JSON)')
    parser.add_argument('--collector-id', type=int, help='Collector ID (overrides config)')
    parser.add_argument('--api-key', help='API key (overrides config)')
    parser.add_argument('--backend-url', help='Backend URL (overrides config)')

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Override with command line arguments
    if args.collector_id:
        config['collector_id'] = args.collector_id
    if args.api_key:
        config['api_key'] = args.api_key
    if args.backend_url:
        config['backend_url'] = args.backend_url

    # Validate required fields
    required_fields = ['collector_id', 'api_key', 'backend_url', 'db_type', 'db_config']
    for field in required_fields:
        if field not in config:
            logger.error(f"Missing required field in configuration: {field}")
            sys.exit(1)

    # Create and run agent
    agent = CollectorAgent(
        collector_id=config['collector_id'],
        api_key=config['api_key'],
        backend_url=config['backend_url'],
        db_type=config['db_type'],
        db_config=config['db_config'],
        heartbeat_interval=config.get('heartbeat_interval', 30),
        collection_interval=config.get('collection_interval', 300)
    )

    # Run agent
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
