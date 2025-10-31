#!/bin/bash
# Validation script for STEP 1 and STEP 2
# Tests database lab and internal database setup

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  AI Query Analyzer - Validation Script${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
        return 1
    fi
}

# Function to print section header
print_header() {
    echo -e "\n${YELLOW}==== $1 ====${NC}"
}

# Track overall status
OVERALL_STATUS=0

#############################################
# STEP 1: Database Lab Validation
#############################################
print_header "STEP 1: Database Lab Validation"

# 1.1 Check if Docker is running
echo -e "\n${BLUE}1.1 Checking Docker...${NC}"
if ! docker info > /dev/null 2>&1; then
    print_status 1 "Docker is not running"
    echo "Please start Docker and try again"
    exit 1
fi
print_status 0 "Docker is running"

# 1.2 Start lab databases
echo -e "\n${BLUE}1.2 Starting lab databases...${NC}"
cd ai-query-lab
docker compose up -d
cd ..

# Wait for databases to be ready
echo "Waiting 20 seconds for databases to initialize..."
sleep 20

# 1.3 Check MySQL lab
echo -e "\n${BLUE}1.3 Validating MySQL Lab...${NC}"

# Check container is running
if docker ps | grep -q mysql-lab; then
    print_status 0 "MySQL container is running"
else
    print_status 1 "MySQL container is not running"
    OVERALL_STATUS=1
fi

# Check connection
if docker exec mysql-lab mysql -uroot -proot -e "SELECT 1" > /dev/null 2>&1; then
    print_status 0 "MySQL connection successful"
else
    print_status 1 "MySQL connection failed"
    OVERALL_STATUS=1
fi

# Check database and tables exist
MYSQL_TABLES=$(docker exec mysql-lab mysql -uroot -proot -e "USE labdb; SHOW TABLES;" 2>/dev/null | grep -c "orders\|users" || echo "0")
if [ "$MYSQL_TABLES" -eq 2 ]; then
    print_status 0 "MySQL tables (users, orders) exist"
else
    print_status 1 "MySQL tables are missing"
    OVERALL_STATUS=1
fi

# Check data is populated
MYSQL_USER_COUNT=$(docker exec mysql-lab mysql -uroot -proot -e "SELECT COUNT(*) FROM labdb.users;" -sN 2>/dev/null || echo "0")
MYSQL_ORDER_COUNT=$(docker exec mysql-lab mysql -uroot -proot -e "SELECT COUNT(*) FROM labdb.orders;" -sN 2>/dev/null || echo "0")

if [ "$MYSQL_USER_COUNT" -gt 100000 ]; then
    print_status 0 "MySQL users table populated (${MYSQL_USER_COUNT} rows)"
else
    print_status 1 "MySQL users table has insufficient data (${MYSQL_USER_COUNT} rows, expected ~200k)"
    OVERALL_STATUS=1
fi

if [ "$MYSQL_ORDER_COUNT" -gt 300000 ]; then
    print_status 0 "MySQL orders table populated (${MYSQL_ORDER_COUNT} rows)"
else
    print_status 1 "MySQL orders table has insufficient data (${MYSQL_ORDER_COUNT} rows, expected ~500k)"
    OVERALL_STATUS=1
fi

# Check that secondary indexes were removed (only PRIMARY KEY should exist)
MYSQL_INDEXES=$(docker exec mysql-lab mysql -uroot -proot -e "SHOW INDEXES FROM labdb.orders WHERE Key_name != 'PRIMARY';" -sN 2>/dev/null | wc -l)
if [ "$MYSQL_INDEXES" -eq 0 ]; then
    print_status 0 "MySQL orders table has no secondary indexes (as intended)"
else
    print_status 1 "MySQL orders table has ${MYSQL_INDEXES} secondary indexes (should be 0)"
    OVERALL_STATUS=1
fi

# Check slow query log is enabled
SLOW_LOG_ENABLED=$(docker exec mysql-lab mysql -uroot -proot -e "SHOW VARIABLES LIKE 'slow_query_log';" -sN 2>/dev/null | awk '{print $2}')
if [ "$SLOW_LOG_ENABLED" = "ON" ]; then
    print_status 0 "MySQL slow query log is enabled"
else
    print_status 1 "MySQL slow query log is not enabled"
    OVERALL_STATUS=1
fi

# 1.4 Check PostgreSQL lab
echo -e "\n${BLUE}1.4 Validating PostgreSQL Lab...${NC}"

# Check container is running
if docker ps | grep -q postgres-lab; then
    print_status 0 "PostgreSQL container is running"
else
    print_status 1 "PostgreSQL container is not running"
    OVERALL_STATUS=1
fi

# Check connection
if docker exec postgres-lab psql -U postgres -c "SELECT 1" > /dev/null 2>&1; then
    print_status 0 "PostgreSQL connection successful"
else
    print_status 1 "PostgreSQL connection failed"
    OVERALL_STATUS=1
fi

# Check tables exist
PG_TABLES=$(docker exec postgres-lab psql -U postgres -d labdb -c "\dt" 2>/dev/null | grep -c "orders\|users" || echo "0")
if [ "$PG_TABLES" -eq 2 ]; then
    print_status 0 "PostgreSQL tables (users, orders) exist"
else
    print_status 1 "PostgreSQL tables are missing"
    OVERALL_STATUS=1
fi

# Check data is populated
PG_USER_COUNT=$(docker exec postgres-lab psql -U postgres -d labdb -tAc "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
PG_ORDER_COUNT=$(docker exec postgres-lab psql -U postgres -d labdb -tAc "SELECT COUNT(*) FROM orders;" 2>/dev/null || echo "0")

if [ "$PG_USER_COUNT" -gt 30000 ]; then
    print_status 0 "PostgreSQL users table populated (${PG_USER_COUNT} rows)"
else
    print_status 1 "PostgreSQL users table has insufficient data (${PG_USER_COUNT} rows, expected ~50k)"
    OVERALL_STATUS=1
fi

if [ "$PG_ORDER_COUNT" -gt 100000 ]; then
    print_status 0 "PostgreSQL orders table populated (${PG_ORDER_COUNT} rows)"
else
    print_status 1 "PostgreSQL orders table has insufficient data (${PG_ORDER_COUNT} rows, expected ~150k)"
    OVERALL_STATUS=1
fi

# Check pg_stat_statements extension
PG_EXTENSION=$(docker exec postgres-lab psql -U postgres -d labdb -tAc "SELECT COUNT(*) FROM pg_extension WHERE extname='pg_stat_statements';" 2>/dev/null || echo "0")
if [ "$PG_EXTENSION" -eq 1 ]; then
    print_status 0 "pg_stat_statements extension is installed"
else
    print_status 1 "pg_stat_statements extension is missing"
    OVERALL_STATUS=1
fi

#############################################
# STEP 2: Internal Database Validation
#############################################
print_header "STEP 2: Internal Database Validation"

# 2.1 Start internal services
echo -e "\n${BLUE}2.1 Starting internal services...${NC}"
docker compose up -d internal-db redis

echo "Waiting 15 seconds for internal database to initialize..."
sleep 15

# 2.2 Check internal-db
echo -e "\n${BLUE}2.2 Validating Internal PostgreSQL...${NC}"

# Check container is running
if docker ps | grep -q ai-analyzer-internal-db; then
    print_status 0 "Internal DB container is running"
else
    print_status 1 "Internal DB container is not running"
    OVERALL_STATUS=1
fi

# Check connection
if docker exec ai-analyzer-internal-db pg_isready -U ai_core > /dev/null 2>&1; then
    print_status 0 "Internal DB is ready"
else
    print_status 1 "Internal DB is not ready"
    OVERALL_STATUS=1
fi

# Check if schema tables exist
INTERNAL_TABLES=$(docker exec ai-analyzer-internal-db psql -U ai_core -d ai_core -c "\dt" 2>/dev/null | grep -c "slow_queries_raw\|analysis_result\|db_metadata" || echo "0")
if [ "$INTERNAL_TABLES" -ge 3 ]; then
    print_status 0 "Internal DB schema tables created (found $INTERNAL_TABLES tables)"
else
    print_status 1 "Internal DB schema tables missing (found $INTERNAL_TABLES tables, expected at least 3)"
    OVERALL_STATUS=1
fi

# Check uuid-ossp extension
UUID_EXTENSION=$(docker exec ai-analyzer-internal-db psql -U ai_core -d ai_core -tAc "SELECT COUNT(*) FROM pg_extension WHERE extname='uuid-ossp';" 2>/dev/null || echo "0")
if [ "$UUID_EXTENSION" -eq 1 ]; then
    print_status 0 "uuid-ossp extension is installed"
else
    print_status 1 "uuid-ossp extension is missing"
    OVERALL_STATUS=1
fi

# Check views exist
VIEWS_COUNT=$(docker exec ai-analyzer-internal-db psql -U ai_core -d ai_core -c "\dv" 2>/dev/null | grep -c "query_performance_summary\|impactful_tables" || echo "0")
if [ "$VIEWS_COUNT" -ge 2 ]; then
    print_status 0 "Database views created"
else
    print_status 1 "Database views missing"
    OVERALL_STATUS=1
fi

# 2.3 Check Redis
echo -e "\n${BLUE}2.3 Validating Redis...${NC}"

# Check container is running
if docker ps | grep -q ai-analyzer-redis; then
    print_status 0 "Redis container is running"
else
    print_status 1 "Redis container is not running"
    OVERALL_STATUS=1
fi

# Check Redis is responding
if docker exec ai-analyzer-redis redis-cli ping 2>/dev/null | grep -q PONG; then
    print_status 0 "Redis is responding"
else
    print_status 1 "Redis is not responding"
    OVERALL_STATUS=1
fi

#############################################
# Python Environment Validation (Optional)
#############################################
print_header "STEP 2b: Python Environment (Optional)"

echo -e "\n${BLUE}2.4 Checking Python environment...${NC}"

# Check if Python 3 is available
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_status 0 "Python is available: $PYTHON_VERSION"

    # Check if requirements can be imported (if installed)
    echo -e "\n${BLUE}2.5 Testing Python imports...${NC}"

    if python3 -c "import sys; sys.path.insert(0, '$(pwd)'); from backend.core.config import settings; print(f'Config loaded: env={settings.env}')" 2>/dev/null; then
        print_status 0 "Python backend modules can be imported"

        # Test database connection from Python
        echo -e "\n${BLUE}2.6 Testing Python DB connection...${NC}"
        if python3 -c "import sys; sys.path.insert(0, '$(pwd)'); from backend.db.session import check_db_connection; check_db_connection()" 2>/dev/null; then
            print_status 0 "Python can connect to internal database"
        else
            print_status 1 "Python cannot connect to internal database (dependencies may not be installed)"
            echo "  Tip: cd backend && pip install -r requirements.txt"
        fi
    else
        print_status 1 "Python backend modules cannot be imported (dependencies not installed)"
        echo "  This is optional for Docker-only deployment"
        echo "  To test locally: cd backend && pip install -r requirements.txt"
    fi
else
    print_status 1 "Python 3 is not available"
    echo "  This is optional if running only in Docker"
fi

#############################################
# Summary
#############################################
print_header "Validation Summary"

echo -e "\n${BLUE}Container Status:${NC}"
docker compose ps

echo -e "\n${BLUE}Port Mappings:${NC}"
echo "  MySQL Lab:       localhost:3307"
echo "  PostgreSQL Lab:  localhost:5433"
echo "  Internal DB:     localhost:5440"
echo "  Redis:           localhost:6379"

if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}  ✓ All validations passed!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo -e "\n${YELLOW}Next steps:${NC}"
    echo "  1. Test slow query simulation:"
    echo "     python3 ai-query-lab/db/mysql/simulate_slow_queries.py"
    echo "     python3 ai-query-lab/db/postgres/simulate_slow_queries.py"
    echo ""
    echo "  2. Check slow query logs:"
    echo "     docker exec mysql-lab mysql -uroot -proot -e \"SELECT COUNT(*) FROM mysql.slow_log;\""
    echo ""
    echo "  3. Ready to proceed with STEP 3 (Backend FastAPI)"
else
    echo -e "\n${RED}========================================${NC}"
    echo -e "${RED}  ✗ Some validations failed${NC}"
    echo -e "${RED}========================================${NC}"
    echo -e "\n${YELLOW}Please check the errors above and fix them before proceeding.${NC}"
    exit 1
fi
