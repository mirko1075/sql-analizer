#!/bin/bash
# ===================================================================
# DBPower Test Suite - Run Single Test
# ===================================================================
# Usage: ./run-test.sh <test_number>
# Example: ./run-test.sh 01
# ===================================================================

MYSQL_HOST="127.0.0.1"
MYSQL_PORT="3306"
MYSQL_USER="root"
MYSQL_PASSWORD="admin"
MYSQL_DB="dbpower_test"

if [ -z "$1" ]; then
    echo "Usage: $0 <test_number>"
    echo "Example: $0 01"
    echo ""
    echo "Available tests:"
    ls -1 [0-9][0-9]-*.sql | sed 's/.sql//'
    exit 1
fi

TEST_NUM="$1"
TEST_FILE="${TEST_NUM}-*.sql"

# Find matching test file
MATCHED_FILE=$(ls ${TEST_FILE} 2>/dev/null | head -n 1)

if [ -z "$MATCHED_FILE" ]; then
    echo "❌ Test file not found: ${TEST_FILE}"
    exit 1
fi

echo "========================================"
echo "Running Test: $MATCHED_FILE"
echo "========================================"
echo ""

# Show test description (first 5 comment lines)
head -n 10 "$MATCHED_FILE" | grep "^--"

echo ""
echo "Executing queries..."
echo "----------------------------------------"

# Run the test
mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DB" < "$MATCHED_FILE"

echo ""
echo "✅ Test completed"
echo ""
echo "📊 Check results:"
echo "  1. Via DBPower UI: http://localhost:3000"
echo "  2. Via API: curl http://localhost:8000/api/v1/slow-queries"
echo "  3. Trigger collection: curl -X POST http://localhost:8000/api/v1/analyze/collect"
echo ""
