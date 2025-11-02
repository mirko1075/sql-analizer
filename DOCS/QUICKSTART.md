# Multi-Database Monitoring - Quick Start Guide

## What Was Implemented

The complete multi-database monitoring system with:
- ✅ **Collector Management**: Track on-premise agents collecting slow queries
- ✅ **Agent Token Authentication**: Secure per-database authentication
- ✅ **Visibility Scopes**: TEAM_ONLY, ORG_WIDE, USER_ONLY access control
- ✅ **Unified Ingestion**: Single endpoint for all database types
- ✅ **Legacy Data Migration**: Automatic backfill of historical data
- ✅ **15 Endpoints Updated**: Full visibility filtering applied

## Quick Start (3 Steps)

### Step 1: Run Database Migrations

**Option A: Using the migration script (easiest)**
```bash
# Set your database password
export DB_PASSWORD='your_password'

# Run migrations
./run_migrations.sh
```

**Option B: Manual execution**
```bash
# Connect to internal PostgreSQL (port 5440)
psql -h localhost -p 5440 -U aiquery_user -d aiquery

# Run migrations
\i backend/db/migrations/004_add_collectors_visibility.sql
\i backend/db/migrations/005_backfill_legacy_connections.sql
```

### Step 2: Start the Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Step 3: Test in Browser

1. **Login** to the application
2. **Navigate to Database Connections** (`/database-connections` or similar)
3. **Verify**: You should now see your database connections (no more "0 DBs shown")
4. **Create a new connection** to test the full flow
5. **Copy the agent token** from the connection details

## What Changed

### New API Endpoints

**Collector Management:**
- `POST /api/v1/collectors/register` - Register collector with agent token
- `POST /api/v1/collectors/ingest/slow-queries` - Ingest slow queries
- `GET /api/v1/collectors` - List collectors
- `POST /api/v1/collectors/{id}/heartbeat` - Update collector status

**Database Connections:**
- `POST /api/v1/database-connections/{id}/rotate-token` - Rotate agent token
- `GET /api/v1/database-connections/{id}/agent-token` - Get full agent token

### Updated Behavior

**All read endpoints now enforce visibility filtering:**
- Slow queries filtered by visible database connections
- Stats aggregated only from accessible databases
- Legacy data automatically migrated to synthetic connections

## Database Schema Changes

### New Tables
- `collectors` - Track collector agents
- `collector_databases` - Many-to-many collector<->database links

### Extended Tables
- `database_connections` - Added: `agent_token`, `visibility_scope`, `owner_user_id`, `is_legacy`, `organization_id`
- `slow_queries_raw` - Added: `database_connection_id`, `organization_id`
- `query_metrics_daily` - Added: `database_connection_id`, `organization_id`
- `query_fingerprint_metrics` - Added: `database_connection_id`, `organization_id`

## Testing Checklist

### 1. Database Connections
- [ ] List connections shows existing connections
- [ ] Create new connection succeeds
- [ ] Agent token is generated and visible (masked)
- [ ] Connection shows correct visibility scope
- [ ] Rotate token endpoint works

### 2. Visibility Filtering
- [ ] User only sees connections from their teams
- [ ] TEAM_ONLY connections only visible to team members
- [ ] Slow queries filtered by visible connections
- [ ] Stats show correct filtered data

### 3. Collector Registration
```bash
# Test collector registration
curl -X POST http://localhost:8000/api/v1/collectors/register \
  -H "Content-Type: application/json" \
  -d '{
    "agent_token": "agt_YOUR_TOKEN_HERE",
    "hostname": "test-collector-01",
    "version": "1.0.0"
  }'
```

### 4. Slow Query Ingestion
```bash
# Test ingestion endpoint
curl -X POST http://localhost:8000/api/v1/collectors/ingest/slow-queries \
  -H "Content-Type: application/json" \
  -d '{
    "agent_token": "agt_YOUR_TOKEN_HERE",
    "queries": [{
      "fingerprint": "SELECT * FROM users WHERE id = ?",
      "full_sql": "SELECT * FROM users WHERE id = 123",
      "duration_ms": 1250.5,
      "rows_examined": 10000,
      "rows_returned": 1,
      "captured_at": "2025-11-02T10:30:00Z"
    }]
  }'
```

## Troubleshooting

### Issue: "0 DBs shown" still appears
**Solution**: Run the migrations. Migration 005 creates legacy connections for historical data.

### Issue: "Could not validate credentials"
**Solution**: Check that JWT_SECRET is set in your .env file and restart the backend.

### Issue: Agent token not visible
**Solution**: Use the `/agent-token` endpoint to retrieve the full token for collector configuration.

### Issue: Queries not appearing after ingestion
**Check**:
1. Agent token is correct
2. Database connection is active (`is_active=true`)
3. Check logs for ingestion errors
4. Verify visibility scope allows user to see the connection

## Next Steps (Optional)

### Update Existing Collectors
If you have existing collector services (mysql_collector.py, postgres_collector.py), update them to use the new ingestion endpoint:

**Old flow**: Direct database inserts
**New flow**: POST to `/api/v1/collectors/ingest/slow-queries`

See [backend/api/routes/collectors.py](backend/api/routes/collectors.py:150) for the ingestion endpoint implementation.

### Configure Collector Agents
1. Get agent token from database connection UI
2. Update collector YAML config:
   ```yaml
   databases:
     - name: production-mysql
       agent_token: agt_1234567890abcdef...
       host: db.prod.example.com
       port: 3306
   ```
3. Start/restart collector agents

## Architecture Overview

```
┌─────────────┐
│   Frontend  │
└──────┬──────┘
       │ HTTP + JWT (user auth)
       ▼
┌─────────────────────────────────────┐
│         FastAPI Backend            │
│  ┌──────────────────────────────┐  │
│  │ Visibility Filtering Layer   │  │
│  │ (get_visible_connection_ids) │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │  API Routes (15 endpoints)   │  │
│  │  - slow_queries.py           │  │
│  │  - stats.py                  │  │
│  │  - statistics.py             │  │
│  │  - collectors.py (NEW)       │  │
│  │  - database_connections.py   │  │
│  └──────────────────────────────┘  │
└──────────┬──────────────────────────┘
           │
           ▼
  ┌─────────────────┐
  │   PostgreSQL    │
  │   (port 5440)   │
  │                 │
  │ - collectors    │
  │ - database_     │
  │   connections   │
  │ - slow_queries_ │
  │   raw           │
  └─────────────────┘
           ▲
           │ agent_token auth
           │
    ┌──────┴──────┐
    │  Collector  │
    │   Agents    │
    │ (on-premise)│
    └─────────────┘
```

## File Reference

**Created Files:**
- `backend/db/migrations/004_add_collectors_visibility.sql` - Schema changes
- `backend/db/migrations/005_backfill_legacy_connections.sql` - Data migration
- `backend/core/visibility.py` - Visibility filtering logic
- `backend/api/schemas/collectors.py` - Collector request/response schemas
- `MIGRATION_GUIDE.md` - Detailed migration instructions
- `run_migrations.sh` - Migration execution script
- `QUICKSTART.md` - This file

**Modified Files:**
- `backend/db/models.py` - Extended models
- `backend/core/dependencies.py` - Added visibility dependencies
- `backend/api/routes/collectors.py` - Complete rewrite
- `backend/api/routes/database_connections.py` - Visibility + token management
- `backend/api/routes/slow_queries.py` - Visibility filtering (5 endpoints)
- `backend/api/routes/stats.py` - Visibility filtering (7 endpoints)
- `backend/api/routes/statistics.py` - Visibility filtering (3 endpoints)
- `backend/api/schemas/database_connections.py` - Added new fields

## Support

For issues or questions:
1. Check the logs: `backend/logs/` or console output
2. Review [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for detailed steps
3. Verify migrations completed successfully
4. Check database connection settings in `.env`

---

**Implementation Status**: ✅ Complete and ready for testing
**Database Migrations**: ⏳ Required before use
**Backend Compatibility**: ✅ All changes backward compatible with proper migration
