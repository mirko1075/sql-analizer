#!/bin/bash
# Test all frontend API endpoints for DBPower AI Cloud

set -e

echo "=================================================="
echo "Testing All Frontend API Endpoints"
echo "=================================================="
echo ""

# Get authentication token
echo "🔑 Getting authentication token..."
TOKEN=$(curl -s 'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@dbpower.com","password":"admin123"}' \
  | jq -r '.access_token')

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "❌ Failed to get authentication token"
  exit 1
fi

echo "✅ Got token: ${TOKEN:0:50}..."
echo ""

# Test counter
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

test_endpoint() {
  local name="$1"
  local method="$2"
  local url="$3"
  local expected_status="${4:-200}"

  TOTAL_TESTS=$((TOTAL_TESTS + 1))
  echo -n "Testing: $name... "

  if [ "$method" = "GET" ]; then
    status=$(curl -s -o /dev/null -w "%{http_code}" "$url" -H "Authorization: Bearer $TOKEN")
  else
    status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$url" -H "Authorization: Bearer $TOKEN" -H "Content-Length: 0")
  fi

  if [ "$status" = "$expected_status" ]; then
    echo "✅ ($status)"
    PASSED_TESTS=$((PASSED_TESTS + 1))
  else
    echo "❌ (expected $expected_status, got $status)"
    FAILED_TESTS=$((FAILED_TESTS + 1))
  fi
}

echo "=================================================="
echo "HEALTH & STATUS ENDPOINTS"
echo "=================================================="
test_endpoint "Health check (public)" "GET" "http://localhost:8000/health"
test_endpoint "API health check" "GET" "http://localhost:8000/api/v1/health"
echo ""

echo "=================================================="
echo "QUERY ENDPOINTS"
echo "=================================================="
test_endpoint "Get queries list" "GET" "http://localhost:8000/api/v1/queries?skip=0&limit=10"
test_endpoint "Get query detail" "GET" "http://localhost:8000/api/v1/queries/3"
echo ""

echo "=================================================="
echo "STATISTICS ENDPOINTS"
echo "=================================================="
test_endpoint "Dashboard stats" "GET" "http://localhost:8000/api/v1/stats/dashboard"
test_endpoint "Top slow queries" "GET" "http://localhost:8000/api/v1/stats/top-slow-queries?limit=10"
test_endpoint "Unanalyzed queries" "GET" "http://localhost:8000/api/v1/stats/unanalyzed-queries?limit=10"
test_endpoint "Query trends" "GET" "http://localhost:8000/api/v1/stats/trends?days=7"
echo ""

echo "=================================================="
echo "COLLECTOR ENDPOINTS"
echo "=================================================="
test_endpoint "Collector status" "GET" "http://localhost:8000/api/v1/collectors/status"
test_endpoint "Trigger MySQL collection" "POST" "http://localhost:8000/api/v1/collectors/mysql/collect"
test_endpoint "Trigger PostgreSQL collection" "POST" "http://localhost:8000/api/v1/collectors/postgres/collect?min_duration_ms=500"
test_endpoint "Start scheduler" "POST" "http://localhost:8000/api/v1/collectors/scheduler/start?interval_minutes=5"
test_endpoint "Stop scheduler" "POST" "http://localhost:8000/api/v1/collectors/scheduler/stop"
echo ""

echo "=================================================="
echo "ANALYZER ENDPOINTS"
echo "=================================================="
test_endpoint "Analyzer status" "GET" "http://localhost:8000/api/v1/analyzer/status"
test_endpoint "Trigger batch analysis" "POST" "http://localhost:8000/api/v1/analyzer/analyze?limit=50"
test_endpoint "Analyze specific query" "POST" "http://localhost:8000/api/v1/analyzer/analyze/3"
echo ""

echo "=================================================="
echo "TEST SUMMARY"
echo "=================================================="
echo "Total tests:  $TOTAL_TESTS"
echo "Passed:       $PASSED_TESTS"
echo "Failed:       $FAILED_TESTS"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
  echo "✅ All tests passed!"
  exit 0
else
  echo "❌ Some tests failed"
  exit 1
fi
