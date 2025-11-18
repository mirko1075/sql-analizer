#!/bin/bash
# =============================================================================
# AI Query Analyzer - Complete Integration Test
# =============================================================================
# This script tests the complete flow:
# 1. Start internal database (PostgreSQL)
# 2. Start lab database (MySQL with slow queries)
# 3. Initialize schema
# 4. Run slow queries
# 5. Test collector
# 6. Test analyzer
# 7. Verify results
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

print_header() {
    echo -e "\n${BLUE}========================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# =============================================================================
# Step 1: Start Internal Database
# =============================================================================
print_header "Step 1: Starting Internal Database (PostgreSQL + Redis)"

print_info "Starting internal-db and redis..."
docker compose -f docker-compose.internal.yml up -d

print_info "Waiting for databases to be ready..."
sleep 10

# Check internal database
if docker compose -f docker-compose.internal.yml ps | grep -q "healthy"; then
    print_success "Internal database is ready"
else
    print_warning "Waiting longer for internal database..."
    sleep 10
fi

# =============================================================================
# Step 2: Start Lab Database
# =============================================================================
print_header "Step 2: Starting MySQL Lab Database"

cd lab-database
print_info "Starting MySQL lab database..."
./start-lab.sh start

cd ..

# =============================================================================
# Step 3: Initialize Internal Database Schema
# =============================================================================
print_header "Step 3: Initializing Database Schema"

print_info "Loading environment..."
export $(cat .env.lab | grep -v '#' | xargs)

print_info "Initializing schema via Python..."
PYTHONPATH=$SCRIPT_DIR python3 << 'EOF'
from backend.db.session import init_db, check_db_connection
from backend.core.logger import get_logger

logger = get_logger(__name__)

print("Checking database connection...")
if check_db_connection():
    print("✓ Database connection successful")
    print("Initializing schema...")
    init_db()
    print("✓ Schema initialized")
else:
    print("✗ Database connection failed")
    exit(1)
EOF

print_success "Database schema initialized"

# =============================================================================
# Step 4: Wait for Lab Database Data
# =============================================================================
print_header "Step 4: Waiting for Lab Database to Load Data"

print_info "Checking if data is loaded..."
row_count=0
max_attempts=30
attempt=0

while [ $row_count -lt 1000 ] && [ $attempt -lt $max_attempts ]; do
    row_count=$(mysql -h 127.0.0.1 -P 3307 -u root -proot ecommerce_lab \
        -N -e "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")

    if [ "$row_count" -lt 1000 ]; then
        echo -n "."
        sleep 10
        attempt=$((attempt + 1))
    fi
done
echo ""

if [ "$row_count" -gt 1000 ]; then
    print_success "Lab database has $row_count users loaded"
else
    print_warning "Lab database still loading data ($row_count users so far)"
    print_info "You can continue and come back to run slow queries later"
fi

# =============================================================================
# Step 5: Run Slow Queries
# =============================================================================
print_header "Step 5: Running Slow Queries (Subset)"

print_info "Running first 5 slow queries to populate slow query log..."
cd lab-database

mysql -h 127.0.0.1 -P 3307 -u root -proot ecommerce_lab << 'SQL'
-- SLOW-001: Email lookup without index
SELECT user_id, username, email FROM users WHERE email = 'user50000@example.com';

-- SLOW-002: Country filter
SELECT COUNT(*) as user_count, country FROM users WHERE country IN ('US', 'UK', 'CA') GROUP BY country;

-- SLOW-003: Product category scan
SELECT product_id, product_name, price FROM products WHERE category_id = 25 ORDER BY price DESC LIMIT 20;

-- SLOW-004: Date range
SELECT user_id, username, created_at FROM users WHERE created_at >= '2022-01-01' AND created_at < '2023-01-01' LIMIT 100;

-- SLOW-005: User order history
SELECT o.order_id, o.order_date, o.total_amount FROM orders o WHERE o.user_id = 12345 ORDER BY o.order_date DESC LIMIT 50;
SQL

cd ..

print_success "Slow queries executed"

# =============================================================================
# Step 6: Test MySQL Collector
# =============================================================================
print_header "Step 6: Testing MySQL Collector"

print_info "Running collector test..."
PYTHONPATH=$SCRIPT_DIR python3 << 'EOF'
import os
os.environ.update({k: v for k, v in [line.split('=', 1) for line in open('.env.lab').read().strip().split('\n') if '=' in line and not line.startswith('#')]})

from backend.services.mysql_collector import MySQLCollector
from backend.core.logger import get_logger

logger = get_logger(__name__)

print("\n" + "="*60)
print("MySQL Collector Test")
print("="*60 + "\n")

try:
    collector = MySQLCollector()

    # Test connection
    if collector.connect():
        print("✓ Connected to MySQL lab database")

        # Fetch slow queries
        queries = collector.fetch_slow_queries(limit=10)
        print(f"✓ Found {len(queries)} slow queries in log")

        if queries:
            print("\nSample query:")
            print(f"  SQL: {queries[0]['sql_text'][:80]}...")
            print(f"  Duration: {queries[0]['query_time']}s")
            print(f"  Rows examined: {queries[0]['rows_examined']}")

        # Test full collection
        print("\nRunning full collection and storage...")
        count = collector.collect_and_store()
        print(f"✓ Collected and stored {count} queries")

        collector.disconnect()
    else:
        print("✗ Failed to connect to MySQL")
        exit(1)

except Exception as e:
    print(f"✗ Collector test failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "="*60)
print("✓ Collector test complete!")
print("="*60)
EOF

print_success "Collector test completed"

# =============================================================================
# Step 7: Test Analyzer
# =============================================================================
print_header "Step 7: Testing Query Analyzer"

print_info "Running analyzer test..."
PYTHONPATH=$SCRIPT_DIR python3 << 'EOF'
import os
os.environ.update({k: v for k, v in [line.split('=', 1) for line in open('.env.lab').read().strip().split('\n') if '=' in line and not line.startswith('#')]})

from backend.services.analyzer import QueryAnalyzer
from backend.db.session import get_db_context
from backend.db.models import SlowQueryRaw, AnalysisResult
from backend.core.logger import get_logger

logger = get_logger(__name__)

print("\n" + "="*60)
print("Query Analyzer Test")
print("="*60 + "\n")

try:
    # Check for pending queries
    with get_db_context() as db:
        pending_count = db.query(SlowQueryRaw).filter(
            SlowQueryRaw.status == 'NEW'
        ).count()

        print(f"Found {pending_count} pending queries to analyze")

    if pending_count > 0:
        # Run analyzer
        analyzer = QueryAnalyzer()
        count = analyzer.analyze_all_pending(limit=10)
        print(f"✓ Analyzed {count} queries")

        # Show results
        with get_db_context() as db:
            analyses = db.query(AnalysisResult).limit(5).all()

            if analyses:
                print("\nSample analyses:")
                for analysis in analyses:
                    print(f"\n  Problem: {analysis.problem}")
                    print(f"  Improvement Level: {analysis.improvement_level.value}")
                    print(f"  Estimated Speedup: {analysis.estimated_speedup}")
                    print(f"  Confidence: {float(analysis.confidence_score):.2f}")
                    print(f"  Suggestions: {len(analysis.suggestions)} recommendations")
    else:
        print("⚠ No pending queries to analyze")

except Exception as e:
    print(f"✗ Analyzer test failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n" + "="*60)
print("✓ Analyzer test complete!")
print("="*60)
EOF

print_success "Analyzer test completed"

# =============================================================================
# Step 8: Verify Results
# =============================================================================
print_header "Step 8: Verifying Results"

print_info "Querying database for results..."
PYTHONPATH=$SCRIPT_DIR python3 << 'EOF'
import os
os.environ.update({k: v for k, v in [line.split('=', 1) for line in open('.env.lab').read().strip().split('\n') if '=' in line and not line.startswith('#')]})

from backend.db.session import get_db_context
from backend.db.models import SlowQueryRaw, AnalysisResult
from sqlalchemy import func

with get_db_context() as db:
    # Query counts
    total_queries = db.query(func.count(SlowQueryRaw.id)).scalar()
    analyzed_queries = db.query(func.count(SlowQueryRaw.id)).filter(
        SlowQueryRaw.status == 'ANALYZED'
    ).scalar()

    # Analysis breakdown
    improvement_breakdown = db.query(
        AnalysisResult.improvement_level,
        func.count(AnalysisResult.id)
    ).group_by(AnalysisResult.improvement_level).all()

    print("\nDatabase Statistics:")
    print(f"  Total slow queries collected: {total_queries}")
    print(f"  Queries analyzed: {analyzed_queries}")
    print("\nImprovement Level Breakdown:")
    for level, count in improvement_breakdown:
        print(f"  {level.value}: {count}")
EOF

print_success "Verification complete"

# =============================================================================
# Summary
# =============================================================================
print_header "Integration Test Complete!"

echo -e "${GREEN}All tests passed!${NC}"
echo ""
echo "Next steps:"
echo "  1. View API docs: http://localhost:8000/docs"
echo "  2. Query slow queries: curl http://localhost:8000/api/v1/slow-queries"
echo "  3. Check analyzer status: curl http://localhost:8000/api/v1/analyzer/status"
echo "  4. Run more slow queries: cd lab-database && ./start-lab.sh test"
echo ""
echo "Databases running:"
echo "  - Internal DB: localhost:5440 (PostgreSQL)"
echo "  - Redis: localhost:6379"
echo "  - Lab MySQL: localhost:3307"
echo ""
print_info "To stop all databases:"
echo "  docker compose -f docker-compose.internal.yml down"
echo "  cd lab-database && ./start-lab.sh stop"
echo ""
