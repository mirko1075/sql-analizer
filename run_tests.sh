#!/bin/bash

# Run backend tests with pytest
# Usage: ./run_tests.sh [options]
#
# Options:
#   -v, --verbose     Verbose output
#   -c, --coverage    Run with coverage report
#   -f, --file FILE   Run specific test file
#   -k, --keyword KW  Run tests matching keyword
#   -m, --marker MRK  Run tests with specific marker
#   --html            Generate HTML coverage report

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Default options
VERBOSE=""
COVERAGE=""
TEST_FILE=""
KEYWORD=""
MARKER=""
HTML=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE="-vv"
            shift
            ;;
        -c|--coverage)
            COVERAGE="--cov=backend --cov-report=term-missing"
            shift
            ;;
        -f|--file)
            TEST_FILE="$2"
            shift 2
            ;;
        -k|--keyword)
            KEYWORD="-k $2"
            shift 2
            ;;
        -m|--marker)
            MARKER="-m $2"
            shift 2
            ;;
        --html)
            HTML="--cov-report=html"
            COVERAGE="--cov=backend"
            shift
            ;;
        -h|--help)
            echo "Usage: ./run_tests.sh [options]"
            echo ""
            echo "Options:"
            echo "  -v, --verbose      Verbose output"
            echo "  -c, --coverage     Run with coverage report"
            echo "  -f, --file FILE    Run specific test file"
            echo "  -k, --keyword KW   Run tests matching keyword"
            echo "  -m, --marker MRK   Run tests with specific marker"
            echo "  --html             Generate HTML coverage report"
            echo "  -h, --help         Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./run_tests.sh                          # Run all tests"
            echo "  ./run_tests.sh -v                       # Verbose output"
            echo "  ./run_tests.sh -c                       # With coverage"
            echo "  ./run_tests.sh -f test_auth.py          # Run auth tests only"
            echo "  ./run_tests.sh -k registration          # Run registration tests"
            echo "  ./run_tests.sh --html                   # Generate HTML report"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}🧪 Running Backend Test Suite${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo -e "${RED}Error: backend directory not found${NC}"
    echo "Please run this script from the project root"
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${YELLOW}Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest not found${NC}"
    echo "Installing test dependencies..."
    pip install -r backend/requirements.txt
fi

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Build pytest command
PYTEST_CMD="pytest backend/tests $VERBOSE $COVERAGE $TEST_FILE $KEYWORD $MARKER $HTML"

echo -e "${YELLOW}Running: $PYTEST_CMD${NC}"
echo ""

# Run tests
if $PYTEST_CMD; then
    echo ""
    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo -e "${GREEN}================================${NC}"
    
    if [ -n "$HTML" ]; then
        echo ""
        echo -e "${GREEN}📊 Coverage report generated: htmlcov/index.html${NC}"
        echo "Open with: firefox htmlcov/index.html"
    fi
    
    exit 0
else
    echo ""
    echo -e "${RED}================================${NC}"
    echo -e "${RED}❌ Some tests failed${NC}"
    echo -e "${RED}================================${NC}"
    exit 1
fi
