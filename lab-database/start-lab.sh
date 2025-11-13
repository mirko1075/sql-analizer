#!/bin/bash
# ============================================================================
# AI Query Analyzer - Quick Lab Start Script
# ============================================================================
# Purpose: One-command lab database setup and testing
# Usage: ./start-lab.sh [command]
# Commands:
#   start    - Start the lab database
#   stop     - Stop the lab database
#   restart  - Restart the lab database
#   status   - Check lab database status
#   test     - Run slow query tests
#   logs     - View database logs
#   connect  - Connect to MySQL shell
#   reset    - Reset database (WARNING: deletes all data)
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Database connection settings
DB_HOST="127.0.0.1"
DB_PORT="3307"
DB_USER="root"
DB_PASS="root"
DB_NAME="ecommerce_lab"
CONTAINER_NAME="mysql-lab-slowquery"

# Functions
print_header() {
    echo -e "\n${BLUE}===========================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===========================================================================${NC}\n"
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
    echo -e "${BLUE}ℹ $1${NC}"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        echo "Please install Docker first: https://docs.docker.com/get-docker/"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker is not running"
        echo "Please start Docker and try again"
        exit 1
    fi

    print_success "Docker is running"
}

start_lab() {
    print_header "Starting MySQL Slow Query Lab"

    check_docker

    print_info "Starting MySQL container..."
    docker compose up -d

    echo ""
    print_info "Waiting for MySQL to be ready..."

    # Wait for healthy status (max 120 seconds)
    timeout=120
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if docker compose ps | grep -q "healthy"; then
            print_success "MySQL is ready!"
            break
        fi

        if [ $((elapsed % 10)) -eq 0 ]; then
            echo -n "."
        fi

        sleep 2
        elapsed=$((elapsed + 2))
    done
    echo ""

    if [ $elapsed -ge $timeout ]; then
        print_warning "MySQL took longer than expected to start"
        print_info "Check logs with: ./start-lab.sh logs"
    fi

    # Check if data is loaded
    print_info "Checking data..."
    sleep 2

    row_count=$(mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASS $DB_NAME \
        -N -e "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")

    if [ "$row_count" -gt "0" ]; then
        print_success "Database initialized with data ($row_count users)"
    else
        print_warning "Database is initializing... this may take 5-10 minutes"
        print_info "Monitor progress: docker compose logs -f mysql-lab"
    fi

    echo ""
    print_header "Lab Database Ready!"
    echo "Connection info:"
    echo "  Host: $DB_HOST"
    echo "  Port: $DB_PORT"
    echo "  User: $DB_USER"
    echo "  Password: $DB_PASS"
    echo "  Database: $DB_NAME"
    echo ""
    echo "Next steps:"
    echo "  1. Wait for data to load (if not ready)"
    echo "  2. Run tests: ./start-lab.sh test"
    echo "  3. Connect: ./start-lab.sh connect"
    echo ""
}

stop_lab() {
    print_header "Stopping MySQL Slow Query Lab"

    docker compose stop

    print_success "Lab database stopped"
    print_info "Data is preserved. Use './start-lab.sh start' to resume"
}

restart_lab() {
    print_header "Restarting MySQL Slow Query Lab"

    docker compose restart

    print_info "Waiting for MySQL to be ready..."
    sleep 10

    print_success "Lab database restarted"
}

status_lab() {
    print_header "MySQL Slow Query Lab Status"

    echo "Container status:"
    docker compose ps

    echo ""

    if docker compose ps | grep -q "Up"; then
        print_success "Lab database is running"

        # Try to connect
        if mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASS -e "USE $DB_NAME;" 2>/dev/null; then
            print_success "MySQL is accepting connections"

            # Get row counts
            echo ""
            echo "Data statistics:"
            mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASS $DB_NAME <<EOF
SELECT 'users' as table_name, COUNT(*) as rows FROM users
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'reviews', COUNT(*) FROM reviews
UNION ALL SELECT 'inventory_log', COUNT(*) FROM inventory_log;
EOF
        else
            print_warning "MySQL is not accepting connections yet"
        fi
    else
        print_warning "Lab database is not running"
        print_info "Start with: ./start-lab.sh start"
    fi
}

test_lab() {
    print_header "Running Slow Query Tests"

    # Check if database is running
    if ! docker compose ps | grep -q "Up"; then
        print_error "Lab database is not running"
        print_info "Start with: ./start-lab.sh start"
        exit 1
    fi

    # Check if data is loaded
    row_count=$(mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASS $DB_NAME \
        -N -e "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")

    if [ "$row_count" -eq "0" ]; then
        print_error "Database is not initialized yet"
        print_info "Wait for initialization to complete (check logs)"
        exit 1
    fi

    # Run slow query tests
    if [ -f "scripts/run-slow-queries.sh" ]; then
        cd scripts
        ./run-slow-queries.sh
    else
        print_error "Test script not found: scripts/run-slow-queries.sh"
        exit 1
    fi
}

logs_lab() {
    print_header "MySQL Lab Database Logs"

    docker compose logs -f --tail=100 mysql-lab
}

connect_lab() {
    print_header "Connecting to MySQL Lab Database"

    if ! docker compose ps | grep -q "Up"; then
        print_error "Lab database is not running"
        print_info "Start with: ./start-lab.sh start"
        exit 1
    fi

    print_info "Connecting to MySQL..."
    echo "Use 'exit' or Ctrl+D to disconnect"
    echo ""

    mysql -h $DB_HOST -P $DB_PORT -u $DB_USER -p$DB_PASS $DB_NAME
}

reset_lab() {
    print_header "Reset MySQL Lab Database"

    print_warning "This will DELETE all data and reinitialize the database!"
    read -p "Are you sure? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        print_info "Reset cancelled"
        exit 0
    fi

    print_info "Stopping and removing containers..."
    docker compose down -v

    print_info "Starting fresh database..."
    docker compose up -d

    print_success "Database reset initiated"
    print_warning "Initialization will take 5-10 minutes"
    print_info "Monitor progress: ./start-lab.sh logs"
}

show_help() {
    echo "MySQL Slow Query Lab - Management Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  start    - Start the lab database"
    echo "  stop     - Stop the lab database"
    echo "  restart  - Restart the lab database"
    echo "  status   - Check lab database status"
    echo "  test     - Run slow query tests"
    echo "  logs     - View database logs"
    echo "  connect  - Connect to MySQL shell"
    echo "  reset    - Reset database (WARNING: deletes all data)"
    echo "  help     - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start        # Start the lab"
    echo "  $0 test         # Run slow query tests"
    echo "  $0 connect      # Open MySQL shell"
    echo ""
}

# Main command handler
case "${1:-help}" in
    start)
        start_lab
        ;;
    stop)
        stop_lab
        ;;
    restart)
        restart_lab
        ;;
    status)
        status_lab
        ;;
    test)
        test_lab
        ;;
    logs)
        logs_lab
        ;;
    connect)
        connect_lab
        ;;
    reset)
        reset_lab
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
