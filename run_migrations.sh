#!/bin/bash
# Migration script for multi-database monitoring implementation
# Runs migrations 004 and 005

set -e  # Exit on error

echo "========================================"
echo "Multi-Database Monitoring - Migrations"
echo "========================================"
echo ""

# Database connection settings (using internal DB on port 5440)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5440}"
DB_NAME="${DB_NAME:-aiquery}"
DB_USER="${DB_USER:-aiquery_user}"

echo "Database connection:"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo ""

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo "Error: psql command not found. Please install PostgreSQL client."
    exit 1
fi

# Test connection
echo "Testing database connection..."
if ! PGPASSWORD="${DB_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &> /dev/null; then
    echo "Error: Cannot connect to database. Please check your credentials."
    echo "Set DB_PASSWORD environment variable if needed: export DB_PASSWORD='your_password'"
    exit 1
fi
echo "✓ Database connection successful"
echo ""

# Run migration 004
echo "========================================"
echo "Running migration 004: Add collectors and visibility"
echo "========================================"
PGPASSWORD="${DB_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f backend/db/migrations/004_add_collectors_visibility.sql
echo "✓ Migration 004 completed"
echo ""

# Run migration 005
echo "========================================"
echo "Running migration 005: Backfill legacy connections"
echo "========================================"
PGPASSWORD="${DB_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f backend/db/migrations/005_backfill_legacy_connections.sql
echo "✓ Migration 005 completed"
echo ""

# Verify tables exist
echo "========================================"
echo "Verifying schema changes..."
echo "========================================"
PGPASSWORD="${DB_PASSWORD}" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT
    'collectors table' as check_name,
    COUNT(*) as row_count
FROM collectors
UNION ALL
SELECT
    'database_connections (with agent_token)' as check_name,
    COUNT(*) as row_count
FROM database_connections
WHERE agent_token IS NOT NULL;
"
echo ""

echo "========================================"
echo "✓ All migrations completed successfully!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Restart your backend server"
echo "2. Test database connections in the UI"
echo "3. Configure collector agents with agent tokens"
echo ""
