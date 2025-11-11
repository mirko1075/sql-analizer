"""
DBPower Client Agent - Main entry point.

Collects slow queries from customer databases and sends them to SaaS backend.
"""
import os
import sys
import time
import signal
import logging
from typing import Dict, List
from datetime import datetime
import threading

from config import ClientAgentConfig, DatabaseType
from collectors import MySQLCollector, PostgreSQLCollector, BaseCollector
from anonymizer import SQLAnonymizer, AnonymizationLevel
from transport import SaaSClient, SaaSClientError


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ClientAgent:
    """
    DBPower Client Agent.

    Runs on-premise at customer site and:
    1. Collects slow queries from customer databases
    2. Anonymizes sensitive data
    3. Sends data to SaaS backend
    """

    def __init__(self, config: ClientAgentConfig):
        """
        Initialize client agent.

        Args:
            config: Client agent configuration
        """
        self.config = config
        self.running = False
        self.collectors: Dict[str, BaseCollector] = {}
        self.anonymizer = SQLAnonymizer(config.anonymization_level)
        self.saas_client = SaaSClient(
            api_url=config.saas.api_url,
            api_key=config.saas.api_key,
            agent_id=config.agent_id,
            verify_ssl=config.saas.verify_ssl,
            timeout=config.saas.timeout,
            retry_attempts=config.saas.retry_attempts,
            retry_delay=config.saas.retry_delay,
        )

        # Statistics
        self.stats = {
            'started_at': None,
            'collections': 0,
            'queries_collected': 0,
            'queries_sent': 0,
            'queries_anonymized': 0,
            'errors': 0,
            'last_collection_time': None,
        }

    def initialize_collectors(self):
        """Initialize database collectors."""
        logger.info(f"Initializing collectors for {len(self.config.databases)} databases")

        for db_config in self.config.databases:
            collector_id = db_config.id

            try:
                # Create appropriate collector based on database type
                if db_config.type == DatabaseType.MYSQL:
                    collector = MySQLCollector({
                        'host': db_config.host,
                        'port': db_config.port,
                        'user': db_config.user,
                        'password': db_config.password,
                        'database': db_config.database,
                        'ssl': db_config.ssl,
                    })
                elif db_config.type == DatabaseType.POSTGRESQL:
                    collector = PostgreSQLCollector({
                        'host': db_config.host,
                        'port': db_config.port,
                        'user': db_config.user,
                        'password': db_config.password,
                        'database': db_config.database,
                        'ssl': db_config.ssl,
                    })
                else:
                    logger.error(f"Unsupported database type: {db_config.type}")
                    continue

                # Connect to database
                if collector.connect():
                    self.collectors[collector_id] = collector
                    logger.info(f"Connected to database: {collector_id} ({db_config.type})")
                else:
                    logger.error(f"Failed to connect to database: {collector_id}")

            except Exception as e:
                logger.error(f"Failed to initialize collector {collector_id}: {e}")

        logger.info(f"Initialized {len(self.collectors)} collectors")

    def collect_and_send_queries(self):
        """Collect slow queries from all databases and send to SaaS."""
        logger.info("Starting query collection cycle")
        self.stats['collections'] += 1
        self.stats['last_collection_time'] = datetime.utcnow()

        total_collected = 0
        total_sent = 0

        for db_id, collector in self.collectors.items():
            try:
                db_config = next((db for db in self.config.databases if db.id == db_id), None)
                if not db_config:
                    logger.error(f"Database config not found for: {db_id}")
                    continue

                logger.info(f"Collecting from database: {db_id}")

                # Collect slow queries
                queries = collector.collect_slow_queries(
                    threshold=db_config.slow_query_threshold,
                    limit=100
                )

                if not queries:
                    logger.info(f"No slow queries found in {db_id}")
                    continue

                logger.info(f"Collected {len(queries)} slow queries from {db_id}")
                total_collected += len(queries)

                # Anonymize queries
                anonymized_queries = []
                for query in queries:
                    try:
                        anonymized_sql, anon_stats = self.anonymizer.anonymize(query.sql_text)
                        query.sql_text = anonymized_sql
                        anonymized_queries.append(query)
                        self.stats['queries_anonymized'] += 1
                    except Exception as e:
                        logger.error(f"Failed to anonymize query: {e}")
                        continue

                # Send to SaaS
                if anonymized_queries:
                    try:
                        result = self.saas_client.send_slow_queries(
                            queries=anonymized_queries,
                            organization_id=db_config.organization_id or 1,  # Default to 1
                            team_id=db_config.team_id or 1,
                            identity_id=db_config.identity_id or 1,
                        )

                        queries_received = result.get('queries_received', 0)
                        logger.info(f"Successfully sent {queries_received} queries from {db_id}")
                        total_sent += queries_received

                    except SaaSClientError as e:
                        logger.error(f"Failed to send queries from {db_id}: {e}")
                        self.stats['errors'] += 1

            except Exception as e:
                logger.error(f"Error collecting from {db_id}: {e}")
                self.stats['errors'] += 1

        self.stats['queries_collected'] += total_collected
        self.stats['queries_sent'] += total_sent

        logger.info(
            f"Collection cycle complete: collected={total_collected}, sent={total_sent}"
        )

    def run(self):
        """Main run loop."""
        logger.info("Starting DBPower Client Agent")
        logger.info(f"Agent ID: {self.config.agent_id}")
        logger.info(f"SaaS URL: {self.config.saas.api_url}")
        logger.info(f"Anonymization level: {self.config.anonymization_level.value}")

        # Validate configuration
        errors = self.config.validate()
        if errors:
            logger.error("Configuration errors:")
            for error in errors:
                logger.error(f"  - {error}")
            sys.exit(1)

        # Initialize collectors
        self.initialize_collectors()

        if not self.collectors:
            logger.error("No collectors initialized. Exiting.")
            sys.exit(1)

        # Test SaaS connection
        try:
            logger.info("Testing SaaS backend connection...")
            health = self.saas_client.health_check()
            logger.info(f"SaaS backend healthy: {health}")
        except SaaSClientError as e:
            logger.error(f"SaaS backend unreachable: {e}")
            logger.warning("Continuing anyway - will retry on collection")

        self.running = True
        self.stats['started_at'] = datetime.utcnow()

        logger.info("Entering main collection loop")

        # Main collection loop
        while self.running:
            try:
                self.collect_and_send_queries()

                # Wait for next collection interval
                collection_interval = min(
                    [db.collection_interval for db in self.config.databases]
                )
                logger.info(f"Sleeping for {collection_interval}s until next collection")
                time.sleep(collection_interval)

            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break

            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                self.stats['errors'] += 1
                time.sleep(60)  # Wait before retrying

        self.shutdown()

    def shutdown(self):
        """Shutdown agent gracefully."""
        logger.info("Shutting down client agent")
        self.running = False

        # Disconnect all collectors
        for db_id, collector in self.collectors.items():
            try:
                collector.disconnect()
                logger.info(f"Disconnected from: {db_id}")
            except Exception as e:
                logger.error(f"Error disconnecting from {db_id}: {e}")

        # Print final statistics
        uptime = (datetime.utcnow() - self.stats['started_at']).total_seconds() if self.stats['started_at'] else 0
        logger.info("=" * 60)
        logger.info("Final Statistics:")
        logger.info(f"  Uptime: {uptime:.0f}s")
        logger.info(f"  Collections: {self.stats['collections']}")
        logger.info(f"  Queries collected: {self.stats['queries_collected']}")
        logger.info(f"  Queries anonymized: {self.stats['queries_anonymized']}")
        logger.info(f"  Queries sent: {self.stats['queries_sent']}")
        logger.info(f"  Errors: {self.stats['errors']}")
        logger.info("=" * 60)

        logger.info("Client agent stopped")


def main():
    """Main entry point."""
    logger.info("DBPower Client Agent starting...")

    # Load configuration
    config_file = os.getenv('CONFIG_FILE')

    try:
        if config_file:
            logger.info(f"Loading configuration from file: {config_file}")
            config = ClientAgentConfig.from_file(config_file)
        else:
            logger.info("Loading configuration from environment variables")
            config = ClientAgentConfig.from_env()

        # Set log level
        logging.getLogger().setLevel(config.log_level)

    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)

    # Create and run agent
    agent = ClientAgent(config)

    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}")
        agent.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run agent
    agent.run()


if __name__ == "__main__":
    main()
