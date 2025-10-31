#!/bin/bash

# AI Query Analyzer - Startup Script
# This script helps you start the entire application stack

set -e

echo "=================================================="
echo "AI Query Analyzer - Startup Script"
echo "=================================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Function to show usage
usage() {
    echo "Usage: ./start.sh [MODE]"
    echo ""
    echo "Modes:"
    echo "  dev       Start in development mode (default)"
    echo "  prod      Start in production mode"
    echo "  lab       Start only lab databases (MySQL + PostgreSQL)"
    echo "  stop      Stop all services"
    echo "  clean     Stop all services and remove volumes"
    echo "  logs      Show logs from all services"
    echo ""
    echo "Examples:"
    echo "  ./start.sh dev        # Start in development mode"
    echo "  ./start.sh prod       # Start in production mode"
    echo "  ./start.sh stop       # Stop all services"
    echo ""
    exit 1
}

# Parse command line arguments
MODE="${1:-dev}"

case "$MODE" in
    dev)
        echo "🚀 Starting AI Query Analyzer in DEVELOPMENT mode..."
        echo ""

        # Start lab databases first
        echo "📊 Starting lab databases (MySQL + PostgreSQL)..."
        cd ai-query-lab
        docker-compose up -d
        cd ..

        # Wait a bit for lab databases to be ready
        echo "⏳ Waiting for lab databases to initialize (30 seconds)..."
        sleep 30

        # Start main application
        echo "🔧 Starting main application services..."
        docker-compose up -d

        echo ""
        echo "✅ All services started successfully!"
        echo ""
        echo "📋 Access Points:"
        echo "  - Frontend:  http://localhost:3000"
        echo "  - Backend:   http://localhost:8000"
        echo "  - API Docs:  http://localhost:8000/docs"
        echo "  - MySQL Lab: localhost:3307"
        echo "  - PG Lab:    localhost:5433"
        echo ""
        echo "📊 View logs:"
        echo "  docker-compose logs -f [service-name]"
        echo ""
        echo "🛑 Stop services:"
        echo "  ./start.sh stop"
        ;;

    prod)
        echo "🚀 Starting AI Query Analyzer in PRODUCTION mode..."
        echo ""

        # Check if .env.prod exists
        if [ ! -f .env.prod ]; then
            echo "⚠️  Warning: .env.prod not found. Creating from template..."
            cp .env.prod.example .env.prod
            echo "❗ Please edit .env.prod with your production values before continuing."
            echo "   Press Ctrl+C to cancel, or Enter to continue with defaults..."
            read
        fi

        # Start lab databases first
        echo "📊 Starting lab databases (MySQL + PostgreSQL)..."
        cd ai-query-lab
        docker-compose up -d
        cd ..

        # Wait for lab databases
        echo "⏳ Waiting for lab databases to initialize (30 seconds)..."
        sleep 30

        # Start main application in production mode
        echo "🔧 Starting main application services (production)..."
        docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

        echo ""
        echo "✅ All services started successfully in PRODUCTION mode!"
        echo ""
        echo "📋 Access Points:"
        echo "  - Frontend:  http://localhost:80"
        echo "  - Backend:   http://localhost:8000"
        echo "  - API Docs:  http://localhost:8000/docs"
        echo ""
        echo "🛑 Stop services:"
        echo "  docker-compose -f docker-compose.prod.yml down"
        ;;

    lab)
        echo "📊 Starting ONLY lab databases..."
        cd ai-query-lab
        docker-compose up -d
        cd ..

        echo ""
        echo "✅ Lab databases started!"
        echo "  - MySQL:     localhost:3307 (user: root, password: root)"
        echo "  - PostgreSQL: localhost:5433 (user: postgres, password: postgres)"
        ;;

    stop)
        echo "🛑 Stopping all services..."

        # Stop main application
        echo "  Stopping main application..."
        docker-compose down

        # Stop lab databases
        echo "  Stopping lab databases..."
        cd ai-query-lab
        docker-compose down
        cd ..

        echo ""
        echo "✅ All services stopped!"
        ;;

    clean)
        echo "🧹 Cleaning up all services and volumes..."
        echo "⚠️  WARNING: This will delete all data!"
        echo "Press Ctrl+C to cancel, or Enter to continue..."
        read

        # Stop and remove everything
        docker-compose down -v
        cd ai-query-lab
        docker-compose down -v
        cd ..

        # Remove data directories
        echo "  Removing data directories..."
        rm -rf data/internal-db/* data/redis/*

        echo ""
        echo "✅ Cleanup complete!"
        ;;

    logs)
        echo "📋 Showing logs (press Ctrl+C to exit)..."
        docker-compose logs -f
        ;;

    *)
        echo "❌ Error: Unknown mode '$MODE'"
        echo ""
        usage
        ;;
esac
