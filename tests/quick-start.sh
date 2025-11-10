#!/bin/bash
# ===================================================================
# DBPower Test Suite - Quick Start
# ===================================================================
# One command to setup and run all tests
# ===================================================================

set -e

echo "========================================"
echo "DBPower Test Suite - Quick Start"
echo "========================================"
echo ""
echo "This will:"
echo "  1. Create test database"
echo "  2. Generate ~700K rows of test data"
echo "  3. Run all performance tests"
echo "  4. Trigger DBPower collection"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Setup
echo ""
echo "🚀 Setting up test environment..."
./setup-test-env.sh

# Run tests
echo ""
echo "🚀 Running all tests..."
./run-all-tests.sh

# Trigger collection
echo ""
echo "🚀 Triggering DBPower collection..."
sleep 2
curl -X POST http://localhost:8000/api/v1/analyze/collect

echo ""
echo "========================================"
echo "✅ Quick start completed!"
echo "========================================"
echo ""
echo "Open: http://localhost:3000"
echo ""
