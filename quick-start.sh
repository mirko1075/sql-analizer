#!/bin/bash
# =============================================================================
# AI Query Analyzer - Quick Start Guide
# =============================================================================
# This script helps you get the complete system running step-by-step
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

print_header() {
    echo -e "\n${BLUE}=======================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=======================================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

print_step() {
    echo -e "\n${CYAN}▶ $1${NC}\n"
}

# =============================================================================
# Welcome
# =============================================================================
print_header "AI Query Analyzer - Quick Start"

echo "This script will guide you through starting the complete system:"
echo "  1. Internal PostgreSQL database"
echo "  2. Redis cache"
echo "  3. MySQL lab database (with slow queries)"
echo "  4. Initialize schema"
echo "  5. Verify integration"
echo ""
echo "Prerequisites:"
echo "  • Docker and Docker Compose installed"
echo "  • Python 3.11+ with pip"
echo "  • MySQL client (for testing)"
echo ""

read -p "Press Enter to continue..."

# =============================================================================
# Step 1: Check Prerequisites
# =============================================================================
print_header "Step 1: Checking Prerequisites"

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    echo "Install from: https://docs.docker.com/get-docker/"
    exit 1
fi
print_success "Docker is installed"

# Check Docker Compose
if ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not available"
    exit 1
fi
print_success "Docker Compose is available"

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
print_success "Python $PYTHON_VERSION is installed"

# Check MySQL client
if ! command -v mysql &> /dev/null; then
    print_warning "MySQL client is not installed (optional for manual testing)"
else
    print_success "MySQL client is installed"
fi

# =============================================================================
# Step 2: Install Python Dependencies
# =============================================================================
print_header "Step 2: Installing Python Dependencies"

print_step "Installing backend dependencies..."
pip install -q -r backend/requirements.txt
print_success "Backend dependencies installed"

# =============================================================================
# Step 3: Start Internal Database
# =============================================================================
print_header "Step 3: Starting Internal Database (PostgreSQL + Redis)"

print_step "Starting internal-db and redis containers..."
docker compose -f docker-compose.internal.yml up -d

print_info "Waiting for databases to be ready (10 seconds)..."
sleep 10

# Check health
if docker compose -f docker-compose.internal.yml ps | grep -q "healthy"; then
    print_success "Internal database is ready"
else
    print_warning "Waiting a bit longer..."
    sleep 10
    if docker compose -f docker-compose.internal.yml ps | grep -q "healthy"; then
        print_success "Internal database is ready"
    else
        print_error "Internal database is not healthy - check logs"
        docker compose -f docker-compose.internal.yml logs --tail=20
        exit 1
    fi
fi

# =============================================================================
# Step 4: Initialize Internal Database Schema
# =============================================================================
print_header "Step 4: Initializing Database Schema"

print_step "Loading environment from .env.lab..."
export $(cat .env.lab | grep -v '#' | xargs)

print_step "Initializing schema via Python..."
PYTHONPATH=$SCRIPT_DIR python3 << 'EOF'
from backend.db.session import init_db, check_db_connection

print("Checking database connection...")
if check_db_connection():
    print("✓ Database connection successful")
    print("Initializing schema...")
    init_db()
    print("✓ Schema initialized")
else:
    print("✗ Database connection failed")
    exit(1)
EOF

print_success "Database schema initialized"

# =============================================================================
# Step 5: Start MySQL Lab Database
# =============================================================================
print_header "Step 5: Starting MySQL Lab Database"

cd lab-database

print_step "Starting MySQL lab database..."
./start-lab.sh start

print_info "MySQL container started - it will take 5-10 minutes to fully initialize"
print_info "The container needs to:"
print_info "  • Start MySQL server (30 seconds)"
print_info "  • Run schema creation (30 seconds)"
print_info "  • Generate 4.7 million rows of data (5-10 minutes)"

cd ..

# =============================================================================
# Step 6: Wait for MySQL to Be Ready
# =============================================================================
print_header "Step 6: Waiting for MySQL to Initialize"

print_info "Checking MySQL initialization status..."
print_info "This may take several minutes - please be patient"
echo ""

# Wait for MySQL to accept connections
max_attempts=60
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if mysql -h 127.0.0.1 -P 3307 -u root -proot -e "SELECT 1;" &>/dev/null; then
        print_success "MySQL is accepting connections!"
        break
    fi

    echo -n "."
    sleep 5
    attempt=$((attempt + 1))
done
echo ""

if [ $attempt -eq $max_attempts ]; then
    print_error "MySQL did not start within expected time"
    print_info "Check logs: docker logs mysql-lab-slowquery"
    exit 1
fi

# Wait for data to be loaded
print_info "Waiting for data to be loaded (checking user count)..."
row_count=0
max_data_attempts=60
attempt=0

while [ $row_count -lt 100000 ] && [ $attempt -lt $max_data_attempts ]; do
    row_count=$(mysql -h 127.0.0.1 -P 3307 -u root -proot ecommerce_lab \
        -N -e "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")

    if [ "$row_count" -lt 100000 ]; then
        printf "\r  Users loaded: %s / 100,000" "$row_count"
        sleep 10
        attempt=$((attempt + 1))
    fi
done
echo ""

if [ "$row_count" -ge 100000 ]; then
    print_success "Data fully loaded: $row_count users"
else
    print_warning "Data partially loaded: $row_count users"
    print_info "You can continue - data is still loading in the background"
fi

# =============================================================================
# Step 7: Run Some Slow Queries
# =============================================================================
print_header "Step 7: Running Sample Slow Queries"

print_step "Executing 5 slow queries to populate the slow query log..."

mysql -h 127.0.0.1 -P 3307 -u root -proot ecommerce_lab << 'SQL'
-- SLOW-001: Email lookup without index
SELECT user_id, username, email FROM users WHERE email = 'user50000@example.com';

-- SLOW-002: Country filter
SELECT COUNT(*) as user_count, country FROM users WHERE country IN ('US', 'UK', 'CA') GROUP BY country;

-- SLOW-003: Product category scan
SELECT product_id, product_name, price FROM products WHERE category_id = 25 ORDER BY price DESC LIMIT 20;

-- SLOW-004: Date range
SELECT user_id, username, created_at FROM users WHERE created_at >= '2022-01-01' AND created_at < '2023-01-01' LIMIT 100;

-- SLOW-005: User order history
SELECT o.order_id, o.order_date, o.total_amount FROM orders o WHERE o.user_id = 12345 ORDER BY o.order_date DESC LIMIT 50;
SQL

print_success "Slow queries executed"

# =============================================================================
# Step 8: Run Integration Verification
# =============================================================================
print_header "Step 8: Running Integration Verification"

print_step "Running Python integration test..."
python3 verify-integration.py

# =============================================================================
# Summary
# =============================================================================
print_header "Quick Start Complete!"

echo -e "${GREEN}All systems are running!${NC}"
echo ""
echo "Database connections:"
echo "  • Internal DB: localhost:5440 (PostgreSQL)"
echo "  • Redis: localhost:6379"
echo "  • Lab MySQL: localhost:3307"
echo ""
echo "Next steps:"
echo ""
echo "  1. Start the API server:"
echo "     uvicorn backend.main:app --reload"
echo ""
echo "  2. View API documentation:"
echo "     http://localhost:8000/docs"
echo ""
echo "  3. Test API endpoints:"
echo "     curl http://localhost:8000/api/v1/slow-queries"
echo "     curl http://localhost:8000/api/v1/analyzer/status"
echo ""
echo "  4. Run more slow queries:"
echo "     cd lab-database && ./start-lab.sh test"
echo ""
echo "  5. Monitor collector (in Python):"
echo "     python3 -c 'from backend.services.mysql_collector import MySQLCollector; \\"
echo "                 c = MySQLCollector(); c.connect(); print(c.fetch_slow_queries())'"
echo ""
echo "  6. Stop everything when done:"
echo "     docker compose -f docker-compose.internal.yml down"
echo "     cd lab-database && ./start-lab.sh stop"
echo ""

print_info "For troubleshooting, see:"
echo "  • lab-database/CONNECTION_TROUBLESHOOTING.md"
echo "  • ./lab-database/troubleshoot-connection.sh"
echo "  • INTEGRATION_TESTING_GUIDE.md"
echo ""
