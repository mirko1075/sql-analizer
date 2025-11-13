#!/bin/bash
# ============================================================================
# AI Query Analyzer - Slow Query Runner
# ============================================================================
# Purpose: Execute slow queries against the MySQL lab database
# Usage: ./run-slow-queries.sh [options]
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Database connection settings
DB_HOST="${MYSQL_HOST:-127.0.0.1}"
DB_PORT="${MYSQL_PORT:-3307}"
DB_USER="${MYSQL_USER:-root}"
DB_PASS="${MYSQL_PASSWORD:-root}"
DB_NAME="ecommerce_lab"

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}============================================================================${NC}"
echo -e "${BLUE}AI Query Analyzer - Slow Query Test Runner${NC}"
echo -e "${BLUE}============================================================================${NC}"
echo ""

# Function to print section headers
print_header() {
    echo -e "\n${YELLOW}>>> $1${NC}\n"
}

# Function to run a single query and report time
run_query() {
    local query_num="$1"
    local description="$2"
    local query="$3"

    echo -e "${GREEN}[SLOW-$(printf '%03d' $query_num)]${NC} $description"

    # Run query and measure time
    start_time=$(date +%s.%N)

    mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" \
        -e "$query" > /dev/null 2>&1

    end_time=$(date +%s.%N)
    duration=$(echo "$end_time - $start_time" | bc)

    echo -e "  ${BLUE}Duration:${NC} ${duration}s"
    echo ""
}

# Check database connection
print_header "Checking Database Connection"
if mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" -e "USE $DB_NAME;" 2>/dev/null; then
    echo -e "${GREEN}✓ Connected to MySQL at $DB_HOST:$DB_PORT${NC}"
else
    echo -e "${RED}✗ Failed to connect to MySQL${NC}"
    echo "Please check your connection settings:"
    echo "  Host: $DB_HOST"
    echo "  Port: $DB_PORT"
    echo "  User: $DB_USER"
    echo "  Database: $DB_NAME"
    exit 1
fi

# Verify slow query log is enabled
print_header "Verifying Slow Query Log Settings"
mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" \
    -e "SHOW VARIABLES LIKE 'slow_query_log%'; SHOW VARIABLES LIKE 'long_query_time';"

# Run test queries
print_header "Running Slow Query Tests"
echo "This will execute 27 intentionally slow queries..."
echo "Expected total runtime: 3-10 minutes depending on server performance"
echo ""
read -p "Press Enter to continue or Ctrl+C to cancel..."
echo ""

# Category 1: Full Table Scans
print_header "CATEGORY 1: Full Table Scans"

run_query 1 "Email lookup without index" \
    "SELECT user_id, username, email FROM users WHERE email = 'user50000@example.com';"

run_query 2 "Country filter without index" \
    "SELECT COUNT(*) as user_count, country FROM users WHERE country IN ('US', 'UK', 'CA') GROUP BY country;"

run_query 3 "Product category scan without index" \
    "SELECT product_id, product_name, price FROM products WHERE category_id = 25 ORDER BY price DESC LIMIT 20;"

run_query 4 "Date range scan without index" \
    "SELECT user_id, username, created_at FROM users WHERE created_at >= '2022-01-01' AND created_at < '2023-01-01' LIMIT 100;"

# Category 2: Missing Composite Indexes
print_header "CATEGORY 2: Missing Composite Indexes"

run_query 5 "User order history (wrong index)" \
    "SELECT o.order_id, o.order_date, o.total_amount FROM orders o WHERE o.user_id = 12345 ORDER BY o.order_date DESC LIMIT 50;"

run_query 6 "Product category with price sorting" \
    "SELECT p.product_id, p.product_name, p.price FROM products p WHERE p.category_id = 15 AND p.price BETWEEN 50 AND 200 ORDER BY p.price ASC;"

run_query 7 "Product reviews with date sorting" \
    "SELECT r.review_id, r.rating, r.created_at FROM reviews r WHERE r.product_id = 1234 ORDER BY r.created_at DESC LIMIT 10;"

# Category 3: Inefficient Joins
print_header "CATEGORY 3: Inefficient JOINs"

run_query 8 "Order with items (product lookup)" \
    "SELECT o.order_id, oi.product_id, oi.quantity FROM orders o JOIN order_items oi ON o.order_id = oi.order_id WHERE o.order_date >= '2023-01-01' LIMIT 1000;"

run_query 9 "User with recent orders and items" \
    "SELECT u.user_id, COUNT(o.order_id) as orders FROM users u LEFT JOIN orders o ON u.user_id = o.user_id WHERE u.country = 'US' GROUP BY u.user_id LIMIT 100;"

run_query 10 "Product performance report" \
    "SELECT p.product_id, COUNT(oi.order_item_id) as sales FROM products p LEFT JOIN order_items oi ON p.product_id = oi.product_id GROUP BY p.product_id LIMIT 50;"

# Category 4: Subquery Problems
print_header "CATEGORY 4: Subquery Problems"

run_query 11 "Correlated subquery for user stats" \
    "SELECT u.user_id, (SELECT COUNT(*) FROM orders WHERE user_id = u.user_id) as orders FROM users u WHERE u.country = 'US' LIMIT 100;"

run_query 12 "IN subquery without index" \
    "SELECT p.product_id, p.product_name FROM products p WHERE p.product_id IN (SELECT DISTINCT product_id FROM order_items LIMIT 1000);"

run_query 13 "NOT EXISTS with poor index" \
    "SELECT p.product_id, p.product_name FROM products p WHERE NOT EXISTS (SELECT 1 FROM reviews r WHERE r.product_id = p.product_id) LIMIT 100;"

# Category 5: Aggregation Issues
print_header "CATEGORY 5: Aggregation Issues"

run_query 14 "Large aggregation without index" \
    "SELECT product_id, COUNT(*) as transactions FROM inventory_log WHERE created_at >= '2023-01-01' GROUP BY product_id LIMIT 100;"

run_query 15 "Complex aggregation" \
    "SELECT search_term, COUNT(*) as searches FROM search_log GROUP BY search_term HAVING searches > 10 LIMIT 20;"

run_query 16 "Daily order aggregation" \
    "SELECT DATE(order_date) as day, COUNT(*) as orders FROM orders GROUP BY day LIMIT 100;"

# Category 6-12: Additional tests
print_header "CATEGORY 6-12: Additional Performance Tests"

run_query 17 "Leading wildcard search" \
    "SELECT product_id, product_name FROM products WHERE product_name LIKE '%laptop%' LIMIT 50;"

run_query 18 "Email domain search" \
    "SELECT user_id, email FROM users WHERE email LIKE '%@gmail.com' LIMIT 100;"

run_query 19 "Sort without index (filesort)" \
    "SELECT user_id, username, total_spent FROM users WHERE total_spent > 1000 ORDER BY total_spent DESC LIMIT 100;"

run_query 20 "Multi-column sort" \
    "SELECT user_id, country, total_spent FROM users ORDER BY country ASC, total_spent DESC LIMIT 100;"

run_query 21 "Distinct without index" \
    "SELECT DISTINCT product_id FROM inventory_log WHERE change_type = 'sale' LIMIT 1000;"

run_query 22 "Count distinct" \
    "SELECT DATE(searched_at) as day, COUNT(DISTINCT user_id) FROM search_log GROUP BY day LIMIT 30;"

run_query 23 "OR condition prevents index" \
    "SELECT user_id, username FROM users WHERE total_spent > 5000 OR loyalty_points > 2000 LIMIT 100;"

run_query 24 "Function on indexed column" \
    "SELECT user_id, created_at FROM users WHERE YEAR(created_at) = 2023 LIMIT 100;"

run_query 25 "Group by non-indexed column" \
    "SELECT status, COUNT(*) FROM orders WHERE order_date >= '2023-01-01' GROUP BY status;"

# Summary
print_header "Test Complete!"
echo -e "${GREEN}✓ All 25 slow queries executed${NC}"
echo ""
echo "Next steps:"
echo "  1. Check the slow query log:"
echo "     mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASS -e \"SELECT * FROM mysql.slow_log ORDER BY start_time DESC LIMIT 10;\""
echo ""
echo "  2. Run the AI Query Analyzer collectors to capture these queries"
echo ""
echo "  3. View analysis results in the dashboard"
echo ""
echo -e "${BLUE}============================================================================${NC}"
