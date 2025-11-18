#!/usr/bin/env python3
"""
AI Query Analyzer - Integration Verification Script
====================================================
This script verifies the complete integration without requiring Docker CLI.
Run this after starting the databases to verify everything works.

Usage:
    python3 verify-integration.py [--skip-collector] [--skip-analyzer]
"""

import os
import sys
import time
import argparse
from pathlib import Path
from typing import Optional, Tuple

# Add project root to path
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

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


def print_header(msg: str):
    print(f"\n{Colors.BLUE}{'=' * 70}{Colors.NC}")
    print(f"{Colors.BLUE}{msg}{Colors.NC}")
    print(f"{Colors.BLUE}{'=' * 70}{Colors.NC}\n")


def print_success(msg: str):
    print(f"{Colors.GREEN}✓ {msg}{Colors.NC}")


def print_error(msg: str):
    print(f"{Colors.RED}✗ {msg}{Colors.NC}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.NC}")


def print_info(msg: str):
    print(f"{Colors.CYAN}ℹ {msg}{Colors.NC}")


def test_internal_db_connection() -> Tuple[bool, Optional[str]]:
    """Test connection to internal PostgreSQL database"""
    try:
        from backend.db.session import check_db_connection, get_db_context
        from backend.db.models import Base

        print_info("Testing internal database connection...")

        if check_db_connection():
            print_success("Connected to internal PostgreSQL database")

            # Check if schema exists
            with get_db_context() as db:
                from sqlalchemy import inspect
                inspector = inspect(db.bind)
                tables = inspector.get_table_names()

                if tables:
                    print_success(f"Schema initialized ({len(tables)} tables found)")
                    print(f"  Tables: {', '.join(tables[:5])}" +
                          (f", ... ({len(tables) - 5} more)" if len(tables) > 5 else ""))
                else:
                    print_warning("Schema not initialized - run init_db()")
                    return False, "Schema not initialized"

            return True, None
        else:
            return False, "Connection failed"
    except Exception as e:
        return False, str(e)


def test_mysql_lab_connection() -> Tuple[bool, Optional[str]]:
    """Test connection to MySQL lab database"""
    try:
        import pymysql

        print_info("Testing MySQL lab database connection...")

        config = {
            'host': os.getenv('MYSQL_HOST', '127.0.0.1'),
            'port': int(os.getenv('MYSQL_PORT', '3307')),
            'user': os.getenv('MYSQL_USER', 'root'),
            'password': os.getenv('MYSQL_PASSWORD', 'root'),
            'database': os.getenv('MYSQL_DB', 'ecommerce_lab'),
        }

        conn = pymysql.connect(**config, connect_timeout=5)
        cursor = conn.cursor()

        # Check database
        cursor.execute("SELECT DATABASE()")
        db_name = cursor.fetchone()[0]
        print_success(f"Connected to MySQL database: {db_name}")

        # Check tables
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        print_success(f"Found {len(tables)} tables")
        print(f"  Tables: {', '.join(tables[:5])}" +
              (f", ... ({len(tables) - 5} more)" if len(tables) > 5 else ""))

        # Check data
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM products")
        product_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]

        print_success("Data loaded:")
        print(f"  Users: {user_count:,}")
        print(f"  Products: {product_count:,}")
        print(f"  Orders: {order_count:,}")

        if user_count == 0:
            print_warning("No data loaded yet - database may still be initializing")
            return False, "Data still loading"
        elif user_count < 100000:
            print_warning(f"Data partially loaded ({user_count:,}/100,000 users)")
            return False, "Data still loading"

        # Check slow query log status
        cursor.execute("SHOW VARIABLES LIKE 'slow_query_log'")
        result = cursor.fetchone()
        if result and result[1] == 'ON':
            print_success("Slow query log is enabled")

            cursor.execute("SHOW VARIABLES LIKE 'slow_query_log_file'")
            log_file = cursor.fetchone()[1]
            print(f"  Log file: {log_file}")
        else:
            print_warning("Slow query log is disabled")

        cursor.close()
        conn.close()

        return True, None

    except Exception as e:
        return False, str(e)


def test_collector(run_collection: bool = True) -> Tuple[bool, Optional[str]]:
    """Test MySQL collector"""
    try:
        from backend.services.mysql_collector import MySQLCollector
        from backend.db.session import get_db_context
        from backend.db.models import SlowQueryRaw

        print_info("Testing MySQL collector...")

        collector = MySQLCollector()

        # Test connection
        if not collector.connect():
            return False, "Collector failed to connect to MySQL"

        print_success("Collector connected to MySQL")

        # Fetch slow queries
        queries = collector.fetch_slow_queries(limit=5)
        print_success(f"Found {len(queries)} slow queries in log")

        if queries:
            sample = queries[0]
            print(f"\n  Sample query:")
            print(f"    SQL: {sample['sql_text'][:70]}...")
            print(f"    Duration: {sample['query_time']:.3f}s")
            print(f"    Rows examined: {sample['rows_examined']:,}")

        # Run collection if requested
        if run_collection and queries:
            print_info("Running collection and storage...")
            count = collector.collect_and_store()
            print_success(f"Collected and stored {count} queries")

            # Verify storage
            with get_db_context() as db:
                total = db.query(SlowQueryRaw).count()
                print_success(f"Total queries in database: {total}")

        collector.disconnect()
        return True, None

    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, str(e)


def test_analyzer(run_analysis: bool = True) -> Tuple[bool, Optional[str]]:
    """Test query analyzer"""
    try:
        from backend.services.analyzer import QueryAnalyzer
        from backend.db.session import get_db_context
        from backend.db.models import SlowQueryRaw, AnalysisResult

        print_info("Testing query analyzer...")

        # Check for pending queries
        with get_db_context() as db:
            pending_count = db.query(SlowQueryRaw).filter(
                SlowQueryRaw.status == 'NEW'
            ).count()

            total_count = db.query(SlowQueryRaw).count()

            print_success(f"Found {pending_count} pending queries (of {total_count} total)")

        if pending_count == 0:
            print_warning("No pending queries to analyze")
            if total_count == 0:
                return False, "No queries in database - run collector first"
            else:
                print_info("All queries already analyzed")
                return True, None

        # Run analyzer if requested
        if run_analysis:
            print_info(f"Analyzing up to 10 pending queries...")

            analyzer = QueryAnalyzer()
            analyzed_count = analyzer.analyze_all_pending(limit=10)

            print_success(f"Analyzed {analyzed_count} queries")

            # Show sample results
            with get_db_context() as db:
                analyses = db.query(AnalysisResult).limit(3).all()

                if analyses:
                    print(f"\n  Sample analyses:")
                    for i, analysis in enumerate(analyses, 1):
                        print(f"\n  {i}. Problem: {analysis.problem}")
                        print(f"     Improvement: {analysis.improvement_level.value}")
                        print(f"     Speedup: {analysis.estimated_speedup}")
                        print(f"     Confidence: {float(analysis.confidence_score):.2f}")

        return True, None

    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, str(e)


def show_summary():
    """Show summary of database contents"""
    try:
        from backend.db.session import get_db_context
        from backend.db.models import SlowQueryRaw, AnalysisResult
        from sqlalchemy import func

        print_info("Querying database statistics...")

        with get_db_context() as db:
            # Query counts
            total_queries = db.query(func.count(SlowQueryRaw.id)).scalar()
            new_queries = db.query(func.count(SlowQueryRaw.id)).filter(
                SlowQueryRaw.status == 'NEW'
            ).scalar()
            analyzed_queries = db.query(func.count(SlowQueryRaw.id)).filter(
                SlowQueryRaw.status == 'ANALYZED'
            ).scalar()

            # Analysis breakdown
            improvement_breakdown = db.query(
                AnalysisResult.improvement_level,
                func.count(AnalysisResult.id)
            ).group_by(AnalysisResult.improvement_level).all()

            print(f"\n  {Colors.CYAN}Database Statistics:{Colors.NC}")
            print(f"    Total slow queries: {total_queries}")
            print(f"    New (pending): {new_queries}")
            print(f"    Analyzed: {analyzed_queries}")

            if improvement_breakdown:
                print(f"\n  {Colors.CYAN}Improvement Level Breakdown:{Colors.NC}")
                for level, count in improvement_breakdown:
                    print(f"    {level.value}: {count}")

            # Show some sample queries
            recent_queries = db.query(SlowQueryRaw).order_by(
                SlowQueryRaw.collected_at.desc()
            ).limit(3).all()

            if recent_queries:
                print(f"\n  {Colors.CYAN}Recent Queries:{Colors.NC}")
                for q in recent_queries:
                    print(f"\n    ID: {q.id}")
                    print(f"    SQL: {q.full_sql[:60]}...")
                    print(f"    Duration: {float(q.duration_ms)}ms")
                    print(f"    Status: {q.status.value}")

    except Exception as e:
        print_error(f"Failed to query statistics: {e}")


def main():
    parser = argparse.ArgumentParser(description='Verify AI Query Analyzer integration')
    parser.add_argument('--skip-collector', action='store_true',
                        help='Skip running the collector')
    parser.add_argument('--skip-analyzer', action='store_true',
                        help='Skip running the analyzer')
    parser.add_argument('--no-collection', action='store_true',
                        help='Test collector but do not collect queries')
    parser.add_argument('--no-analysis', action='store_true',
                        help='Test analyzer but do not analyze queries')
    args = parser.parse_args()

    print_header("AI Query Analyzer - Integration Verification")

    failed_tests = []

    # Test 1: Internal Database
    print_header("Test 1: Internal PostgreSQL Database")
    success, error = test_internal_db_connection()
    if not success:
        print_error(f"Internal database test failed: {error}")
        failed_tests.append(("Internal Database", error))

    # Test 2: MySQL Lab Database
    print_header("Test 2: MySQL Lab Database")
    success, error = test_mysql_lab_connection()
    if not success:
        print_error(f"MySQL lab database test failed: {error}")
        failed_tests.append(("MySQL Lab Database", error))

        if "still loading" in error.lower():
            print_info("\nMySQ initialization tips:")
            print("  • Wait 5-10 minutes for data generation to complete")
            print("  • Check progress: docker logs mysql-lab-slowquery")
            print("  • Look for: 'users generated' in logs")
            print("  • Run: ./lab-database/troubleshoot-connection.sh")

    # Test 3: Collector
    if not args.skip_collector:
        print_header("Test 3: MySQL Collector")
        run_collection = not args.no_collection
        success, error = test_collector(run_collection=run_collection)
        if not success:
            print_error(f"Collector test failed: {error}")
            failed_tests.append(("Collector", error))

    # Test 4: Analyzer
    if not args.skip_analyzer:
        print_header("Test 4: Query Analyzer")
        run_analysis = not args.no_analysis
        success, error = test_analyzer(run_analysis=run_analysis)
        if not success:
            print_error(f"Analyzer test failed: {error}")
            failed_tests.append(("Analyzer", error))

    # Show summary
    print_header("Database Summary")
    show_summary()

    # Final report
    print_header("Verification Results")

    if failed_tests:
        print_error(f"Failed {len(failed_tests)} test(s):")
        for test_name, error in failed_tests:
            print(f"  • {test_name}: {error}")
        print()
        sys.exit(1)
    else:
        print_success("All tests passed!")
        print()
        print(f"{Colors.GREEN}Integration verified successfully!{Colors.NC}")
        print()
        print("Next steps:")
        print("  • Start API server: uvicorn backend.main:app --reload")
        print("  • View API docs: http://localhost:8000/docs")
        print("  • Run more slow queries: cd lab-database && ./start-lab.sh test")
        print()
        sys.exit(0)


if __name__ == '__main__':
    main()
