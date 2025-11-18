#!/usr/bin/env python3
"""
Test MySQL Collector
====================
This script tests the MySQL slow query collector in isolation.

Prerequisites:
- MySQL lab database running on localhost:3307
- Internal database running on localhost:5440
- Environment loaded from .env.lab

Usage:
    python3 test-collectors.py [--limit N] [--no-store]
"""

import os
import sys
import argparse
from pathlib import Path

# Setup paths
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

# Load environment
env_file = SCRIPT_DIR / '.env.lab'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

from backend.services.mysql_collector import MySQLCollector
from backend.db.session import get_db_context
from backend.db.models import SlowQueryRaw
from backend.core.logger import get_logger

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Test MySQL collector')
    parser.add_argument('--limit', type=int, default=10,
                        help='Number of queries to fetch (default: 10)')
    parser.add_argument('--no-store', action='store_true',
                        help='Do not store queries in database')
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("MySQL Collector Test")
    print("=" * 70 + "\n")

    try:
        # Create collector
        collector = MySQLCollector()

        # Test connection
        print("Connecting to MySQL lab database...")
        if collector.connect():
            print("✓ Connected successfully")
        else:
            print("✗ Failed to connect")
            sys.exit(1)

        # Test slow query log status
        print("\nChecking slow query log configuration...")
        cursor = collector.connection.cursor()

        cursor.execute("SHOW VARIABLES LIKE 'slow_query_log'")
        result = cursor.fetchone()
        slow_log_enabled = result[1] if result else 'OFF'
        print(f"  Slow query log: {slow_log_enabled}")

        if slow_log_enabled == 'OFF':
            print("  ⚠ Slow query log is disabled!")
            print("  Enable it by restarting the lab database")

        cursor.execute("SHOW VARIABLES LIKE 'long_query_time'")
        result = cursor.fetchone()
        long_query_time = result[1] if result else 'unknown'
        print(f"  Long query time: {long_query_time}s")

        cursor.execute("SHOW VARIABLES LIKE 'slow_query_log_file'")
        result = cursor.fetchone()
        log_file = result[1] if result else 'unknown'
        print(f"  Log file: {log_file}")

        cursor.close()

        # Fetch slow queries
        print(f"\nFetching up to {args.limit} slow queries...")
        queries = collector.fetch_slow_queries(limit=args.limit)

        if not queries:
            print("✗ No slow queries found in log")
            print("\nTroubleshooting:")
            print("  1. Run some slow queries:")
            print("     cd lab-database && ./start-lab.sh test")
            print("  2. Check if log file exists and has content")
            print("  3. Verify slow_query_log is enabled")
            collector.disconnect()
            sys.exit(1)

        print(f"✓ Found {len(queries)} slow queries")

        # Display sample queries
        print("\nSample queries:")
        for i, query in enumerate(queries[:3], 1):
            print(f"\n{i}. Query:")
            print(f"   SQL: {query['sql_text'][:80]}{'...' if len(query['sql_text']) > 80 else ''}")
            print(f"   Duration: {query['query_time']:.3f}s")
            print(f"   Rows examined: {query['rows_examined']:,}")
            print(f"   Rows sent: {query['rows_sent']:,}")
            print(f"   Database: {query['db_name']}")

        # Store queries if requested
        if not args.no_store:
            print(f"\nStoring queries in internal database...")
            stored_count = collector.collect_and_store()
            print(f"✓ Stored {stored_count} queries")

            # Verify storage
            with get_db_context() as db:
                total = db.query(SlowQueryRaw).count()
                new_count = db.query(SlowQueryRaw).filter(
                    SlowQueryRaw.status == 'NEW'
                ).count()
                analyzed_count = db.query(SlowQueryRaw).filter(
                    SlowQueryRaw.status == 'ANALYZED'
                ).count()

                print(f"\nDatabase statistics:")
                print(f"  Total queries: {total}")
                print(f"  New (pending analysis): {new_count}")
                print(f"  Analyzed: {analyzed_count}")

        # Disconnect
        collector.disconnect()
        print("\n" + "=" * 70)
        print("✓ Collector test complete!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
