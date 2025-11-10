#!/bin/bash
# ===================================================================
# DBPower Test Suite - Run All Tests
# ===================================================================
# Executes all SQL test files sequentially
# ===================================================================

MYSQL_HOST="127.0.0.1"
MYSQL_PORT="3306"
MYSQL_USER="root"
MYSQL_PASSWORD="admin"
MYSQL_DB="dbpower_test"

echo "========================================"
echo "DBPower Test Suite - Running All Tests"
echo "========================================"
echo ""

# Count test files
TOTAL_TESTS=$(ls -1 [0-9][0-9]-*.sql 2>/dev/null | wc -l)

if [ "$TOTAL_TESTS" -eq 0 ]; then
    echo "❌ No test files found"
    exit 1
fi

echo "Found $TOTAL_TESTS test files"
echo ""

# Run each test
COUNTER=0
for TEST_FILE in [0-9][0-9]-*.sql; do
    COUNTER=$((COUNTER + 1))
    
    echo "----------------------------------------"
    echo "Test $COUNTER/$TOTAL_TESTS: $TEST_FILE"
    echo "----------------------------------------"
    
    # Show first description line
    head -n 5 "$TEST_FILE" | grep "^-- Test" | head -n 1
    
    # Run test
    mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DB" < "$TEST_FILE" 2>&1 | head -n 5
    
    echo "✅ Completed"
    echo ""
    
    # Small delay between tests
    sleep 1
done

echo "========================================"
echo "✅ All tests completed!"
echo "========================================"
echo ""
echo "📊 Next steps:"
echo "  1. Trigger collection:"
echo "     curl -X POST http://localhost:8000/api/v1/analyze/collect"
echo ""
echo "  2. View collected queries:"
echo "     curl http://localhost:8000/api/v1/slow-queries | jq"
echo ""
echo "  3. Check stats:"
echo "     curl http://localhost:8000/api/v1/stats | jq"
echo ""
echo "  4. Open UI:"
echo "     http://localhost:3000"
echo ""
