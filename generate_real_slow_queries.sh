#!/bin/bash
# Generate REAL slow queries for testing
# This script generates intentionally inefficient queries on existing databases

echo "🔧 Generating real slow queries for testing..."
echo ""

# MySQL connection
MYSQL_HOST="127.0.0.1"
MYSQL_USER="root"
MYSQL_PASS="admin"

# Ensure slow query log is enabled and configured
mysql -h $MYSQL_HOST -u$MYSQL_USER -p$MYSQL_PASS <<EOF
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 0.1;
SET GLOBAL log_output = 'TABLE';
SELECT "✅ Slow query log configured" as status;
EOF

echo ""
echo "📊 Generating slow queries on existing databases..."
echo ""

# Generate queries on different databases
mysql -h $MYSQL_HOST -u$MYSQL_USER -p$MYSQL_PASS <<EOF

-- Use mychannel_backoffice
USE mychannel_backoffice;

-- Get table names
SELECT "📍 Working on mychannel_backoffice" as status;

-- Generate some slow queries (these will appear in slow_log)
-- Query 1: Full table scan
SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'mychannel_backoffice';

-- Query 2: Complex aggregation
SELECT TABLE_NAME, COUNT(*)
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'mychannel_backoffice'
GROUP BY TABLE_NAME
ORDER BY COUNT(*) DESC;

-- Query 3: Cross join (intentionally slow)
SELECT a.TABLE_NAME, b.COLUMN_NAME
FROM INFORMATION_SCHEMA.TABLES a
CROSS JOIN INFORMATION_SCHEMA.COLUMNS b
WHERE a.TABLE_SCHEMA = 'mychannel_backoffice'
  AND b.TABLE_SCHEMA = 'mychannel_backoffice'
LIMIT 100;

EOF

# Generate more queries on another database
mysql -h $MYSQL_HOST -u$MYSQL_USER -p$MYSQL_PASS <<EOF

USE mysaas;

SELECT "📍 Working on mysaas" as status;

-- More slow queries
SELECT COUNT(DISTINCT TABLE_NAME)
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'mysaas';

SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'mysaas'
ORDER BY ORDINAL_POSITION
LIMIT 200;

EOF

echo ""
echo "✅ Real slow queries generated!"
echo ""
echo "📊 Check slow_log:"
mysql -h $MYSQL_HOST -u$MYSQL_USER -p$MYSQL_PASS -e "SELECT COUNT(*) as total_slow_queries FROM mysql.slow_log WHERE sql_text NOT LIKE '%SLEEP%'"

echo ""
echo "🚀 Now collect queries with:"
echo "   curl -X POST 'http://localhost:8000/api/v1/collectors/mysql/collect?lookback_minutes=10&min_query_time=0.1' -H 'Authorization: Bearer \$TOKEN' | jq"
