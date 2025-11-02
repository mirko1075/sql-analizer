# Migration Guide: Multi-Database Monitoring with Collectors

This guide explains how to apply the new database schema changes to enable multi-database monitoring with collectors and visibility scopes.

## Overview

The following changes have been implemented:

1. **Collectors Tracking**: New `collectors` and `collector_databases` tables to track agent instances
2. **Agent Tokens**: Each database connection now has a unique `agent_token` for authentication
3. **Visibility Scopes**: Database connections support three visibility levels:
   - `TEAM_ONLY`: Only team members can see (default)
   - `ORG_WIDE`: All organization members can see
   - `USER_ONLY`: Only the owner can see
4. **Organization Links**: All data tables now link to both `team_id` and `organization_id`
5. **Database Connection Links**: SlowQueryRaw, QueryMetricsDaily, and QueryFingerprintMetrics now link to `database_connection_id`

## Why You See "0 DBs"

If you're seeing "0 DBs" when logging in, it's because:

1. The new database columns haven't been added yet
2. Existing database connections need to be migrated
3. The visibility filtering requires the new fields to be populated

## Solution: Run Migrations

### Step 1: Check Current Schema Version

```bash
# Connect to your database
docker exec -it sql-analyzer-db psql -U postgres -d ai_query_analyzer

# Check current schema version
SELECT version, description, applied_at FROM schema_version ORDER BY version;

# You should see version 2 (auth and multi-tenancy)
# Exit psql
\q
```

### Step 2: Run Migration 004 (Add Collectors and Visibility)

```bash
cd /home/msiddi/development/sql-analizer

# Run migration 004
python3 -c "
from pathlib import Path
from backend.db.session import SessionLocal
from backend.core.logger import get_logger

logger = get_logger(__name__)
db = SessionLocal()

try:
    migration_file = Path('backend/db/migrations/004_add_collectors_visibility.sql')
    with open(migration_file, 'r') as f:
        sql = f.read()

    logger.info('Running migration 004: Add collectors and visibility support')
    db.execute(sql)
    db.commit()
    logger.info('✓ Migration 004 completed successfully!')
except Exception as e:
    db.rollback()
    logger.error(f'✗ Migration 004 failed: {e}')
    raise
finally:
    db.close()
"
```

### Step 3: Run Migration 005 (Backfill Legacy Connections)

```bash
# Run migration 005
python3 -c "
from pathlib import Path
from backend.db.session import SessionLocal
from backend.core.logger import get_logger

logger = get_logger(__name__)
db = SessionLocal()

try:
    migration_file = Path('backend/db/migrations/005_backfill_legacy_connections.sql')
    with open(migration_file, 'r') as f:
        sql = f.read()

    logger.info('Running migration 005: Backfill legacy database connections')
    db.execute(sql)
    db.commit()
    logger.info('✓ Migration 005 completed successfully!')
except Exception as e:
    db.rollback()
    logger.error(f'✗ Migration 005 failed: {e}')
    raise
finally:
    db.close()
"
```

### Step 4: Restart the Backend

```bash
# Restart the backend to pick up the new model changes
docker-compose restart backend

# Or if running locally:
# Kill the backend process and restart it
```

### Step 5: Verify

```bash
# Check schema version again
docker exec -it sql-analyzer-db psql -U postgres -d ai_query_analyzer -c \
  "SELECT version, description, applied_at FROM schema_version ORDER BY version;"

# You should now see versions 1, 2, 4, and 5

# Check database connections
docker exec -it sql-analyzer-db psql -U postgres -d ai_query_analyzer -c \
  "SELECT id, name, team_id, visibility_scope, is_legacy, agent_token IS NOT NULL as has_token
   FROM database_connections;"

# All connections should have:
# - visibility_scope = 'TEAM_ONLY'
# - has_token = true
# - is_legacy = true (for migrated data) or false (for new connections)
```

### Step 6: Test in Browser

1. Log out and log back in
2. Navigate to Database Connections page
3. You should now see your database connections!

## What Was Fixed

1. **Database Schema**: Added new tables and columns for collectors and visibility
2. **Legacy Data Migration**: Existing connections were migrated with default values:
   - `visibility_scope` = 'TEAM_ONLY'
   - `organization_id` = team's organization
   - `agent_token` = auto-generated secure token
   - `is_legacy` = true (to mark migrated data)

3. **Visibility Filtering**: The `/api/v1/database-connections` endpoint now uses proper visibility filtering
4. **Model Updates**: SQLAlchemy models updated to include new fields and relationships

## Alternative: Clean Migrations (If Issues Occur)

If you encounter issues with migrations, you can:

### Option A: Manual SQL Fix (Quick)

```bash
# Connect to database
docker exec -it sql-analyzer-db psql -U postgres -d ai_query_analyzer

# Run these commands manually:
-- Add new columns to database_connections
ALTER TABLE database_connections
  ADD COLUMN IF NOT EXISTS agent_token VARCHAR(128) UNIQUE,
  ADD COLUMN IF NOT EXISTS agent_token_created_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS visibility_scope VARCHAR(20) DEFAULT 'TEAM_ONLY',
  ADD COLUMN IF NOT EXISTS owner_user_id UUID REFERENCES users(id),
  ADD COLUMN IF NOT EXISTS is_legacy BOOLEAN DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id);

-- Set organization_id based on team
UPDATE database_connections dc
SET organization_id = t.organization_id
FROM teams t
WHERE dc.team_id = t.id AND dc.organization_id IS NULL;

-- Set default visibility
UPDATE database_connections
SET visibility_scope = 'TEAM_ONLY'
WHERE visibility_scope IS NULL;

-- Generate agent tokens (you may need to do this programmatically)
-- For now, set a placeholder
UPDATE database_connections
SET agent_token = 'agt_' || md5(random()::text || clock_timestamp()::text),
    agent_token_created_at = NOW()
WHERE agent_token IS NULL;

-- Commit
\q
```

### Option B: Full Redeployment (Most Thorough)

If you have no production data to preserve:

```bash
# WARNING: This will delete all data!
cd /home/msiddi/development/sql-analizer

# Stop and remove containers
docker-compose down -v

# Remove the database volume
docker volume rm sql-analizer_postgres_data

# Rebuild and start
docker-compose up -d --build

# Run ALL migrations from scratch
python -m backend.run_migration

# Seed initial data
python -m backend.seed_initial_data
```

## Next Steps

After migrations are complete:

1. **Create New Collectors**: Use the new collector registration endpoint
2. **Configure Visibility**: Update database connections to use ORG_WIDE or USER_ONLY scope if needed
3. **Agent Tokens**: Use the agent tokens to configure on-premise collectors
4. **Test Ingestion**: Verify data flows through the new ingestion endpoints

## Troubleshooting

### Issue: "relation does not exist" errors

**Solution**: Make sure you've run all migrations in order (001, 004, 005)

### Issue: Still seeing 0 DBs

**Solution**:
1. Check that your user has team memberships: `SELECT * FROM team_members WHERE user_id = '<your-user-id>';`
2. Check that database connections have team_id set: `SELECT * FROM database_connections;`
3. Check that visibility_scope is set: `SELECT COUNT(*) FROM database_connections WHERE visibility_scope IS NULL;`
4. Check backend logs for visibility filtering errors

### Issue: Migrations fail with constraint violations

**Solution**:
1. Check if migrations were partially applied
2. Use Option A (Manual SQL Fix) to manually add missing columns
3. Or use Option B (Full Redeployment) if no production data exists

## Support

If you encounter issues:
1. Check backend logs: `docker-compose logs backend`
2. Check database logs: `docker-compose logs db`
3. Verify migrations were applied: `SELECT * FROM schema_version;`
4. Test visibility filtering manually with psql queries

## Summary

This migration adds critical multi-database monitoring features:
- ✅ Collector tracking and health monitoring
- ✅ Agent token authentication
- ✅ Visibility scope control (TEAM_ONLY, ORG_WIDE, USER_ONLY)
- ✅ Organization-level filtering
- ✅ Database connection tracking for all metrics

After running these migrations, your system will be ready for multi-database monitoring with proper isolation and security.
