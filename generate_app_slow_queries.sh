#!/bin/bash
# Generate REAL slow queries on APPLICATION TABLES (not metadata)
# This creates slow queries that would actually appear in a production application

echo "🔧 Generating REAL application slow queries..."
echo ""

MYSQL_HOST="127.0.0.1"
MYSQL_USER="root"
MYSQL_PASS="admin"

# Ensure slow query log is enabled
mysql -h $MYSQL_HOST -u$MYSQL_USER -p$MYSQL_PASS <<EOF 2>/dev/null
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 0.1;
SET GLOBAL log_output = 'TABLE';
EOF

echo "✅ Slow query log configured"
echo ""

# First, find tables in mychannel_backoffice
echo "📊 Discovering tables in mychannel_backoffice..."
TABLES=$(mysql -h $MYSQL_HOST -u$MYSQL_USER -p$MYSQL_PASS -N -e "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'mychannel_backoffice' AND TABLE_TYPE = 'BASE TABLE' LIMIT 5" 2>/dev/null)

echo "Found tables: $TABLES"
echo ""

# Get first table name
FIRST_TABLE=$(echo "$TABLES" | head -n 1)

if [ -z "$FIRST_TABLE" ]; then
    echo "❌ No tables found in mychannel_backoffice"
    echo "Creating test table..."

    mysql -h $MYSQL_HOST -u$MYSQL_USER -p$MYSQL_PASS mychannel_backoffice <<EOF 2>/dev/null
    CREATE TABLE IF NOT EXISTS test_users (
        id INT PRIMARY KEY AUTO_INCREMENT,
        email VARCHAR(255),
        name VARCHAR(255),
        status VARCHAR(50),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_status (status)
    );

    INSERT INTO test_users (email, name, status) VALUES
        ('user1@test.com', 'User 1', 'active'),
        ('user2@test.com', 'User 2', 'inactive'),
        ('user3@test.com', 'User 3', 'active'),
        ('user4@test.com', 'User 4', 'pending'),
        ('user5@test.com', 'User 5', 'active');
EOF
    FIRST_TABLE="test_users"
    echo "✅ Created test_users table"
fi

echo ""
echo "🚀 Generating slow queries on real application tables..."
echo ""

# Generate REAL application slow queries
mysql -h $MYSQL_HOST -u$MYSQL_USER -p$MYSQL_PASS mychannel_backoffice <<EOF 2>/dev/null

-- Query 1: SELECT * without WHERE (bad practice)
SELECT * FROM $FIRST_TABLE LIMIT 100;

-- Query 2: Query with OR conditions
SELECT * FROM $FIRST_TABLE WHERE id = 1 OR id = 2 OR id = 3;

-- Query 3: LIKE with leading wildcard
SELECT * FROM $FIRST_TABLE WHERE email LIKE '%@test.com' LIMIT 50;

-- Query 4: Complex subquery
SELECT * FROM $FIRST_TABLE WHERE id IN (SELECT id FROM $FIRST_TABLE WHERE id > 0) LIMIT 20;

-- Query 5: ORDER BY without index
SELECT * FROM $FIRST_TABLE ORDER BY email DESC LIMIT 10;

EOF

echo "✅ Generated 5 real application slow queries on table: $FIRST_TABLE"
echo ""

# Generate on another database if available
echo "📊 Generating queries on mysaas database..."

mysql -h $MYSQL_HOST -u$MYSQL_USER -p$MYSQL_PASS mysaas <<EOF 2>/dev/null

-- Create test table if not exists
CREATE TABLE IF NOT EXISTS test_products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255),
    price DECIMAL(10,2),
    category VARCHAR(100),
    stock INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT IGNORE INTO test_products (id, name, price, category, stock) VALUES
    (1, 'Product A', 99.99, 'Electronics', 100),
    (2, 'Product B', 49.99, 'Books', 50),
    (3, 'Product C', 199.99, 'Electronics', 25);

-- Real application queries
SELECT * FROM test_products WHERE price > 0 ORDER BY price DESC;
SELECT * FROM test_products WHERE category = 'Electronics' OR category = 'Books';
SELECT COUNT(*), AVG(price), category FROM test_products GROUP BY category;

EOF

echo "✅ Generated queries on mysaas database"
echo ""
echo "📊 Total slow queries in log:"
mysql -h $MYSQL_HOST -u$MYSQL_USER -p$MYSQL_PASS -N -e "SELECT COUNT(*) FROM mysql.slow_log WHERE sql_text NOT LIKE '%SLEEP%' AND sql_text NOT LIKE '%INFORMATION_SCHEMA%' AND sql_text NOT LIKE '%information_schema%'" 2>/dev/null

echo ""
echo "🎯 Now collect with:"
echo "   curl -X POST 'http://localhost:8000/api/v1/collectors/mysql/collect?lookback_minutes=10&min_query_time=0.1' \\"
echo "        -H 'Authorization: Bearer \$TOKEN' | jq"
