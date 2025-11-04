#!/bin/bash
# ===================================================================
# DBPower Test Suite - Setup Script
# ===================================================================
# This script sets up the test database and generates test data
# ===================================================================

set -e

MYSQL_HOST="127.0.0.1"
MYSQL_PORT="3306"
MYSQL_USER="root"
MYSQL_PASSWORD="admin"

echo "========================================"
echo "DBPower Test Suite - Setup"
echo "========================================"

# Check if mysql client is available
if ! command -v mysql &> /dev/null; then
    echo "❌ mysql client not found. Please install mysql-client."
    exit 1
fi

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ python3 not found. Please install Python 3."
    exit 1
fi

# Check if mysql-connector-python is installed
if ! python3 -c "import mysql.connector" &> /dev/null; then
    echo "📦 Installing mysql-connector-python..."
    pip3 install mysql-connector-python
fi

# Step 1: Create test schema
echo ""
echo "📊 Step 1: Creating test database schema..."
mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" < ../data/mysql-lab/test-schema.sql
echo "✅ Schema created"

# Step 2: Generate test data
echo ""
echo "📊 Step 2: Generating test data (this will take 5-10 minutes)..."
python3 ../data/mysql-lab/generate-test-data.py
echo "✅ Test data generated"

# Step 3: Verify setup
echo ""
echo "📊 Step 3: Verifying setup..."
mysql -h "$MYSQL_HOST" -P "$MYSQL_PORT" -u "$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "
USE dbpower_test;
SELECT 'users' as table_name, COUNT(*) as row_count FROM users
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'product_reviews', COUNT(*) FROM product_reviews
UNION ALL SELECT 'analytics_events', COUNT(*) FROM analytics_events
UNION ALL SELECT 'product_inventory', COUNT(*) FROM product_inventory;
"

echo ""
echo "========================================"
echo "✅ Test Environment Ready!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Run all tests:     ./run-all-tests.sh"
echo "  2. Run specific test: ./run-test.sh 01"
echo "  3. View results:      Check slow_log or use DBPower UI"
echo ""
