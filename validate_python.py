#!/usr/bin/env python3
"""
Python validation script for STEP 2.

Tests database models, connections, and basic operations.
"""
import sys
import os
from datetime import datetime
from decimal import Decimal

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from backend.core.config import settings
    from backend.core.logger import get_logger
    from backend.db.models import SlowQueryRaw, DbMetadata, AnalysisResult
    from backend.db.session import (
        check_db_connection,
        get_db_context,
        engine,
    )
    from sqlalchemy import text
except ImportError as e:
    print(f"❌ Failed to import backend modules: {e}")
    print("\nPlease install dependencies:")
    print("  cd backend && pip install -r requirements.txt")
    sys.exit(1)

logger = get_logger(__name__)


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def print_header(text: str):
    """Print section header."""
    print(f"\n{Colors.YELLOW}==== {text} ===={Colors.NC}")


def print_status(success: bool, message: str):
    """Print status message with color."""
    symbol = "✓" if success else "✗"
    color = Colors.GREEN if success else Colors.RED
    print(f"{color}{symbol} {message}{Colors.NC}")


def test_config():
    """Test configuration loading."""
    print_header("Configuration Test")

    try:
        print(f"Environment: {settings.env}")
        print(f"Log Level: {settings.log_level}")
        print(f"Internal DB: {settings.internal_db.host}:{settings.internal_db.port}")
        print(f"MySQL Lab: {settings.mysql_lab.host}:{settings.mysql_lab.port}")
        print(f"PostgreSQL Lab: {settings.postgres_lab.host}:{settings.postgres_lab.port}")
        print(f"Redis: {settings.redis_host}:{settings.redis_port}")
        print_status(True, "Configuration loaded successfully")
        return True
    except Exception as e:
        print_status(False, f"Configuration loading failed: {e}")
        return False


def test_db_connection():
    """Test database connection."""
    print_header("Database Connection Test")

    try:
        result = check_db_connection()
        print_status(result, "Database connection" + (" successful" if result else " failed"))
        return result
    except Exception as e:
        print_status(False, f"Database connection test failed: {e}")
        return False


def test_schema():
    """Test that database schema is properly initialized."""
    print_header("Database Schema Test")

    try:
        with get_db_context() as db:
            # Check if tables exist
            result = db.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))

            tables = [row[0] for row in result]

            expected_tables = [
                'slow_queries_raw',
                'db_metadata',
                'analysis_result',
                'optimization_history',
                'schema_version'
            ]

            print(f"\nFound tables: {', '.join(tables)}")

            all_present = all(table in tables for table in expected_tables)
            print_status(all_present, f"All expected tables present: {all_present}")

            # Check views
            result = db.execute(text("""
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = 'public'
            """))

            views = [row[0] for row in result]
            print(f"Found views: {', '.join(views)}")

            expected_views = ['query_performance_summary', 'impactful_tables']
            all_views_present = all(view in views for view in expected_views)
            print_status(all_views_present, f"All expected views present: {all_views_present}")

            return all_present and all_views_present

    except Exception as e:
        print_status(False, f"Schema test failed: {e}")
        return False


def test_models():
    """Test SQLAlchemy models."""
    print_header("SQLAlchemy Models Test")

    try:
        # Test creating a SlowQueryRaw instance
        slow_query = SlowQueryRaw(
            source_db_type='mysql',
            source_db_host='localhost',
            source_db_name='test_db',
            fingerprint='SELECT * FROM users WHERE id = ?',
            full_sql='SELECT * FROM users WHERE id = 123',
            sql_hash='abc123',
            duration_ms=Decimal('1234.56'),
            rows_examined=10000,
            rows_returned=1,
            plan_json={'query_block': {'table': {'table_name': 'users'}}},
            plan_text='EXPLAIN output here',
            status='NEW'
        )

        print(f"Created SlowQueryRaw instance: {slow_query}")
        print_status(True, "SlowQueryRaw model instantiation successful")

        # Test DbMetadata
        db_meta = DbMetadata(
            source_db_type='postgres',
            source_db_host='localhost',
            source_db_name='test_db',
            tables=[{'name': 'users', 'row_count': 1000}],
            indexes=[{'table': 'users', 'name': 'idx_email'}],
        )

        print(f"Created DbMetadata instance: {db_meta}")
        print_status(True, "DbMetadata model instantiation successful")

        return True

    except Exception as e:
        print_status(False, f"Models test failed: {e}")
        return False


def test_crud_operations():
    """Test basic CRUD operations."""
    print_header("CRUD Operations Test")

    try:
        with get_db_context() as db:
            # Create
            test_query = SlowQueryRaw(
                source_db_type='mysql',
                source_db_host='test-host',
                source_db_name='test_db',
                fingerprint='SELECT * FROM test WHERE id = ?',
                full_sql='SELECT * FROM test WHERE id = 1',
                sql_hash='test_hash_' + datetime.now().strftime('%Y%m%d%H%M%S'),
                duration_ms=Decimal('500.00'),
                rows_examined=100,
                rows_returned=1,
                status='NEW'
            )

            db.add(test_query)
            db.commit()
            db.refresh(test_query)

            query_id = test_query.id
            print(f"Created test query with ID: {query_id}")
            print_status(True, "CREATE operation successful")

            # Read
            retrieved_query = db.query(SlowQueryRaw).filter_by(id=query_id).first()
            if retrieved_query and retrieved_query.fingerprint == test_query.fingerprint:
                print_status(True, "READ operation successful")
            else:
                print_status(False, "READ operation failed")
                return False

            # Update
            retrieved_query.status = 'ANALYZED'
            db.commit()

            updated_query = db.query(SlowQueryRaw).filter_by(id=query_id).first()
            if updated_query.status == 'ANALYZED':
                print_status(True, "UPDATE operation successful")
            else:
                print_status(False, "UPDATE operation failed")
                return False

            # Delete
            db.delete(updated_query)
            db.commit()

            deleted_query = db.query(SlowQueryRaw).filter_by(id=query_id).first()
            if deleted_query is None:
                print_status(True, "DELETE operation successful")
            else:
                print_status(False, "DELETE operation failed")
                return False

            return True

    except Exception as e:
        print_status(False, f"CRUD operations test failed: {e}")
        return False


def test_relationships():
    """Test model relationships."""
    print_header("Model Relationships Test")

    try:
        with get_db_context() as db:
            # Create a slow query
            slow_query = SlowQueryRaw(
                source_db_type='mysql',
                source_db_host='test-host',
                source_db_name='test_db',
                fingerprint='SELECT * FROM users WHERE email = ?',
                full_sql='SELECT * FROM users WHERE email = "test@example.com"',
                sql_hash='rel_test_' + datetime.now().strftime('%Y%m%d%H%M%S'),
                duration_ms=Decimal('1500.00'),
                rows_examined=50000,
                rows_returned=1,
                status='NEW'
            )

            db.add(slow_query)
            db.commit()
            db.refresh(slow_query)

            # Create an analysis result for this query
            analysis = AnalysisResult(
                slow_query_id=slow_query.id,
                problem="Missing index on email column",
                root_cause="Full table scan required due to no index",
                suggestions=[
                    {
                        "type": "INDEX",
                        "priority": "HIGH",
                        "sql": "CREATE INDEX idx_users_email ON users(email)",
                        "description": "Add index on email column"
                    }
                ],
                improvement_level='HIGH',
                estimated_speedup='50x',
                analyzer_version='1.0.0',
                analysis_method='rule_based',
                confidence_score=Decimal('0.95')
            )

            db.add(analysis)
            db.commit()

            # Test relationship
            db.refresh(slow_query)
            if slow_query.analysis and slow_query.analysis.problem == analysis.problem:
                print_status(True, "One-to-one relationship (SlowQueryRaw -> AnalysisResult) works")
            else:
                print_status(False, "Relationship test failed")
                return False

            # Cleanup
            db.delete(analysis)
            db.delete(slow_query)
            db.commit()

            return True

    except Exception as e:
        print_status(False, f"Relationships test failed: {e}")
        return False


def main():
    """Run all validation tests."""
    print(f"{Colors.BLUE}{'='*50}{Colors.NC}")
    print(f"{Colors.BLUE}  Python Validation Tests{Colors.NC}")
    print(f"{Colors.BLUE}{'='*50}{Colors.NC}")

    results = {
        "Configuration": test_config(),
        "Database Connection": test_db_connection(),
        "Database Schema": test_schema(),
        "SQLAlchemy Models": test_models(),
        "CRUD Operations": test_crud_operations(),
        "Model Relationships": test_relationships(),
    }

    # Summary
    print_header("Test Summary")
    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        print_status(result, test_name)

    print(f"\n{Colors.BLUE}{'='*50}{Colors.NC}")
    if passed == total:
        print(f"{Colors.GREEN}✓ All tests passed ({passed}/{total}){Colors.NC}")
        return 0
    else:
        print(f"{Colors.RED}✗ Some tests failed ({passed}/{total}){Colors.NC}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
