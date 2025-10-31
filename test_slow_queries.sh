#!/bin/bash
# Test script for slow query simulation
# Runs slow queries directly via Docker without Python dependencies

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Slow Query Simulation Test${NC}"
echo -e "${BLUE}========================================${NC}\n"

# MySQL Slow Queries
echo -e "${YELLOW}Testing MySQL Slow Queries...${NC}\n"

echo "Query 1: Full table scan with LIKE (should be slow)"
docker exec mysql-lab mysql -uroot -proot -e "
USE labdb;
SELECT BENCHMARK(1, (
  SELECT COUNT(*) FROM orders WHERE product LIKE '%phone%' AND status='PAID'
));
" 2>&1 | grep -v "Using a password"

echo -e "\nQuery 2: JOIN without index (should be slow)"
docker exec mysql-lab mysql -uroot -proot -e "
USE labdb;
SELECT COUNT(*)
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.country = 'IT' AND o.status = 'SHIPPED';
" 2>&1 | grep -v "Using a password"

echo -e "\nQuery 3: GROUP BY without covering index (should be slow)"
docker exec mysql-lab mysql -uroot -proot -e "
USE labdb;
SELECT country, COUNT(*) as cnt
FROM users
GROUP BY country
ORDER BY cnt DESC;
" 2>&1 | grep -v "Using a password"

echo -e "\n${GREEN}✓ MySQL queries executed${NC}\n"

# Check MySQL slow log
echo -e "${YELLOW}Checking MySQL slow query log...${NC}"
MYSQL_SLOW_COUNT=$(docker exec mysql-lab mysql -uroot -proot -sN -e "SELECT COUNT(*) FROM mysql.slow_log;" 2>&1 | grep -v "Using a password")
echo -e "Slow queries logged in MySQL: ${GREEN}${MYSQL_SLOW_COUNT}${NC}\n"

if [ "$MYSQL_SLOW_COUNT" -gt 0 ]; then
    echo "Latest slow queries:"
    docker exec mysql-lab mysql -uroot -proot -e "
      SELECT
        start_time,
        query_time,
        LEFT(sql_text, 80) as query_preview
      FROM mysql.slow_log
      ORDER BY start_time DESC
      LIMIT 5;
    " 2>&1 | grep -v "Using a password"
fi

# PostgreSQL Slow Queries
echo -e "\n${YELLOW}Testing PostgreSQL Slow Queries...${NC}\n"

echo "Query 1: Full table scan with LIKE (should be slow)"
docker exec postgres-lab psql -U postgres -d labdb -c "
  SELECT COUNT(*) FROM orders WHERE product LIKE '%phone%' AND status='PAID';
" 2>&1

echo -e "\nQuery 2: JOIN without index (should be slow)"
docker exec postgres-lab psql -U postgres -d labdb -c "
  SELECT COUNT(*)
  FROM users u
  JOIN orders o ON u.id = o.user_id
  WHERE u.country = 'IT' AND o.status = 'SHIPPED';
" 2>&1

echo -e "\nQuery 3: Complex aggregation (should be slow)"
docker exec postgres-lab psql -U postgres -d labdb -c "
  SELECT u.country, COUNT(o.id) as order_count, SUM(o.price) as total_revenue
  FROM users u
  LEFT JOIN orders o ON u.id = o.user_id
  WHERE o.status IN ('PAID', 'SHIPPED')
  GROUP BY u.country
  HAVING COUNT(o.id) > 10
  ORDER BY total_revenue DESC
  LIMIT 10;
" 2>&1

echo -e "\n${GREEN}✓ PostgreSQL queries executed${NC}\n"

# Check PostgreSQL stats
echo -e "${YELLOW}Checking PostgreSQL pg_stat_statements...${NC}"
docker exec postgres-lab psql -U postgres -d labdb -c "
  SELECT
    calls,
    ROUND(total_exec_time::numeric / 1000, 2) as total_time_sec,
    ROUND(mean_exec_time::numeric / 1000, 2) as avg_time_sec,
    LEFT(query, 80) as query_preview
  FROM pg_stat_statements
  WHERE query NOT LIKE '%pg_stat_statements%'
    AND query NOT LIKE '%pg_catalog%'
  ORDER BY mean_exec_time DESC
  LIMIT 5;
" 2>&1

echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Slow query test completed${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "\nYou can now:"
echo -e "  1. Check MySQL slow log: docker exec mysql-lab mysql -uroot -proot -e \"SELECT COUNT(*) FROM mysql.slow_log;\""
echo -e "  2. Check PostgreSQL stats: docker exec postgres-lab psql -U postgres -d labdb -c \"SELECT COUNT(*) FROM pg_stat_statements;\""
echo -e "  3. Run continuous simulation with Python scripts (requires dependencies)"
