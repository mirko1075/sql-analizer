#!/bin/bash
# Check slow queries on local MySQL
# Usage: ./check_local_slow_queries.sh

set -e

# MySQL Connection Settings
MYSQL_HOST="127.0.0.1"
MYSQL_PORT="3306"
MYSQL_USER="root"
MYSQL_PASS="admin"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  MySQL Slow Query Log Checker${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check MySQL connection
echo -e "${YELLOW}Testing MySQL connection...${NC}"
if ! mysql -h "$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASS" -e "SELECT 1;" 2>/dev/null; then
    echo -e "${RED}✗ Cannot connect to MySQL${NC}"
    echo "Please check:"
    echo "  - MySQL is running"
    echo "  - Host: $MYSQL_HOST"
    echo "  - Port: $MYSQL_PORT"
    echo "  - User: $MYSQL_USER"
    echo "  - Password: $MYSQL_PASS"
    exit 1
fi
echo -e "${GREEN}✓ Connected to MySQL${NC}\n"

# Check slow query log configuration
echo -e "${YELLOW}Checking slow query log configuration...${NC}"
mysql -h "$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASS" -e "
SELECT 
    @@global.slow_query_log as 'Slow Query Log',
    @@global.long_query_time as 'Long Query Time (sec)',
    @@global.log_output as 'Log Output'
" 2>/dev/null

# Check if slow query log is enabled
SLOW_LOG_ENABLED=$(mysql -h "$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASS" -sN -e "SELECT @@global.slow_query_log;" 2>/dev/null)

if [ "$SLOW_LOG_ENABLED" != "1" ]; then
    echo -e "\n${RED}⚠ Slow query log is DISABLED${NC}"
    echo -e "\nTo enable it, run:"
    echo -e "${YELLOW}SET GLOBAL slow_query_log = 'ON';${NC}"
    echo -e "${YELLOW}SET GLOBAL long_query_time = 0.3;${NC}"
    echo -e "${YELLOW}SET GLOBAL log_output = 'TABLE';${NC}"
    echo -e "\nThen reconnect to MySQL and run this script again."
    exit 0
fi

# Check log output
LOG_OUTPUT=$(mysql -h "$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASS" -sN -e "SELECT @@global.log_output;" 2>/dev/null)

if [[ "$LOG_OUTPUT" != *"TABLE"* ]]; then
    echo -e "\n${RED}⚠ Log output is not set to TABLE${NC}"
    echo -e "Current: $LOG_OUTPUT"
    echo -e "\nTo fix, run:"
    echo -e "${YELLOW}SET GLOBAL log_output = 'TABLE';${NC}"
    exit 0
fi

echo -e "${GREEN}✓ Slow query log is properly configured${NC}\n"

# Count slow queries
echo -e "${YELLOW}Counting slow queries...${NC}"
SLOW_COUNT=$(mysql -h "$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASS" -sN -e "SELECT COUNT(*) FROM mysql.slow_log;" 2>/dev/null)
echo -e "Total slow queries logged: ${GREEN}${SLOW_COUNT}${NC}\n"

if [ "$SLOW_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}No slow queries found yet.${NC}"
    echo -e "\nTo generate a test slow query, run:"
    echo -e "${BLUE}mysql -h 127.0.0.1 -P3306 -uroot -padmin -e \"SELECT SLEEP(1);\"${NC}"
    exit 0
fi

# Show latest slow queries (CONVERTED from HEX)
echo -e "${YELLOW}Latest slow queries:${NC}\n"
mysql -h "$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASS" -e "
SELECT
    start_time,
    ROUND(query_time, 4) as query_time_sec,
    lock_time,
    rows_sent,
    rows_examined,
    db as database_name,
    CONVERT(sql_text USING utf8) as query_text
FROM mysql.slow_log
ORDER BY start_time DESC
LIMIT 10;
" 2>/dev/null

# Show statistics by database
echo -e "\n${YELLOW}Slow queries by database:${NC}"
mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASS" -e "
SELECT
    COALESCE(db, 'No DB Selected') as database_name,
    COUNT(*) as query_count,
    ROUND(AVG(query_time), 4) as avg_time_sec,
    ROUND(MAX(query_time), 4) as max_time_sec
FROM mysql.slow_log
GROUP BY db
ORDER BY query_count DESC;
" 2>/dev/null

# Show slowest queries (aggregated)
echo -e "\n${YELLOW}Top 5 slowest query patterns:${NC}"
mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASS" -e "
SELECT
    COUNT(*) as executions,
    ROUND(AVG(query_time), 4) as avg_time_sec,
    ROUND(MAX(query_time), 4) as max_time_sec,
    db as database_name,
    LEFT(CONVERT(sql_text USING utf8), 100) as query_preview
FROM mysql.slow_log
GROUP BY db, LEFT(sql_text, 100)
ORDER BY max_time_sec DESC
LIMIT 5;
" 2>/dev/null

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Slow query check completed${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Show useful commands
echo -e "Useful commands:"
echo -e "  ${BLUE}Clear log:${NC}     mysql -h127.0.0.1 -P3306 -uroot -padmin -e \"TRUNCATE TABLE mysql.slow_log;\""
echo -e "  ${BLUE}Disable log:${NC}   mysql -h127.0.0.1 -P3306 -uroot -padmin -e \"SET GLOBAL slow_query_log = 'OFF';\""
echo -e "  ${BLUE}Test query:${NC}    mysql -h127.0.0.1 -P3306 -uroot -padmin -e \"SELECT SLEEP(1);\""