#!/usr/bin/env python3
"""
Test script for collector services.

Tests MySQL and PostgreSQL collectors independently to verify they work correctly.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.core.logger import get_logger
from backend.services.mysql_collector import MySQLCollector
from backend.services.postgres_collector import PostgreSQLCollector

logger = get_logger(__name__)

print("=" * 60)
print("Collector Service Test")
print("=" * 60)

# Test MySQL Collector
print("\n[1/2] Testing MySQL Collector...")
print("-" * 60)
try:
    mysql_collector = MySQLCollector()

    # Test connection
    if not mysql_collector.connect():
        print("✗ Failed to connect to MySQL")
    else:
        print("✓ Connected to MySQL")

        # Test fetching slow queries
        queries = mysql_collector.fetch_slow_queries(limit=5)
        print(f"✓ Fetched {len(queries)} slow queries from MySQL")

        if queries:
            sample = queries[0]
            print(f"\n  Sample query:")
            print(f"    SQL: {sample['sql_text'][:80]}...")
            print(f"    Duration: {sample['query_time']}")
            print(f"    Rows examined: {sample['rows_examined']}")
            print(f"    Rows sent: {sample['rows_sent']}")

            # Test EXPLAIN generation
            print("\n  Testing EXPLAIN generation...")
            plan = mysql_collector.generate_explain(sample['sql_text'])
            if plan:
                print(f"  ✓ EXPLAIN plan generated successfully")
            else:
                print(f"  ⚠ EXPLAIN plan could not be generated (query may not be SELECT)")

        mysql_collector.disconnect()

except Exception as e:
    print(f"✗ MySQL collector test failed: {e}")
    import traceback
    traceback.print_exc()

# Test PostgreSQL Collector
print("\n[2/2] Testing PostgreSQL Collector...")
print("-" * 60)
try:
    pg_collector = PostgreSQLCollector()

    # Test connection
    if not pg_collector.connect():
        print("✗ Failed to connect to PostgreSQL")
    else:
        print("✓ Connected to PostgreSQL")

        # Test fetching slow queries
        queries = pg_collector.fetch_slow_queries(min_duration_ms=500, limit=5)
        print(f"✓ Fetched {len(queries)} slow queries from PostgreSQL")

        if queries:
            sample = queries[0]
            print(f"\n  Sample query:")
            print(f"    SQL: {sample['query'][:80]}...")
            print(f"    Mean duration: {sample['mean_exec_time']:.2f}ms")
            print(f"    Total calls: {sample['calls']}")
            print(f"    Rows: {sample['rows']}")

            # Test EXPLAIN generation
            print("\n  Testing EXPLAIN generation...")
            plan = pg_collector.generate_explain(sample['query'])
            if plan:
                print(f"  ✓ EXPLAIN plan generated successfully")
            else:
                print(f"  ⚠ EXPLAIN plan could not be generated (query may not be SELECT)")

        pg_collector.disconnect()

except Exception as e:
    print(f"✗ PostgreSQL collector test failed: {e}")
    import traceback
    traceback.print_exc()

# Test full collection and storage
print("\n" + "=" * 60)
print("Testing Full Collection and Storage")
print("=" * 60)

print("\n[1/2] MySQL full collection...")
try:
    mysql_collector = MySQLCollector()
    count = mysql_collector.collect_and_store()
    print(f"✓ MySQL: Collected and stored {count} queries")
except Exception as e:
    print(f"✗ MySQL collection failed: {e}")
    import traceback
    traceback.print_exc()

print("\n[2/2] PostgreSQL full collection...")
try:
    pg_collector = PostgreSQLCollector()
    count = pg_collector.collect_and_store(min_duration_ms=500.0)
    print(f"✓ PostgreSQL: Collected and stored {count} queries")
except Exception as e:
    print(f"✗ PostgreSQL collection failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✓ Collector tests completed!")
print("=" * 60)

print("\nTo view collected queries, run:")
print("  docker exec -it ai-analyzer-internal-db psql -U ai_core -d ai_core")
print("  SELECT COUNT(*), source_db_type FROM slow_queries_raw GROUP BY source_db_type;")
