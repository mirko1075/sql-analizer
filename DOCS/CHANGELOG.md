# DBPower SQL Analyzer - Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] - 2025-11-02

### Fixed - Query Visibility & Data Association

#### Problem Identified
Dashboard and Slow Queries page showing 0 records despite collector status showing 12 queries collected (9 MySQL + 3 PostgreSQL). Root cause: orphan queries with `database_connection_id = NULL` were excluded from visibility filtering.

#### Solution Implemented (3-Step Fix)

**STEP 1: Associate Orphan Queries to Database Connections**
- Updated all existing orphan queries in database
- Associated 9 MySQL queries to "MySQL Lab" connection
- Associated 3 PostgreSQL queries to "PostgreSQL Lab" connection
- Queries immediately became visible in dashboard

**STEP 2: Modified Collectors to Include Connection IDs**
- Updated `backend/services/mysql_collector.py`:
  - Added `database_connection_id`, `team_id`, `organization_id` parameters to constructor
  - Modified `collect_and_store()` to save queries with proper associations
- Updated `backend/services/postgres_collector.py`:
  - Added same connection tracking parameters
  - Modified query saving logic to include associations

**STEP 3: Updated Scheduler to Pass Connection IDs**
- Modified `backend/services/scheduler_v2.py`:
  - Scheduler now instantiates collectors with proper connection IDs
  - Passes `database_connection_id`, `team_id`, `organization_id` from DatabaseConnection records
  - Ensures future collected queries are automatically associated

**Files Modified:**
- `backend/services/mysql_collector.py` - Added connection tracking
- `backend/services/postgres_collector.py` - Added connection tracking
- `backend/services/scheduler_v2.py` - Updated collector instantiation

**Database Changes:**
```sql
-- SQL executed to fix orphan queries
UPDATE slow_queries_raw
SET database_connection_id = '98b40357-04dd-49d9-ad39-42736f8fb8da'
WHERE source_db_type = 'mysql' AND database_connection_id IS NULL;
-- Result: 9 rows updated

UPDATE slow_queries_raw
SET database_connection_id = 'cba60cf7-883a-45eb-b35e-697869c45f8c'
WHERE source_db_type = 'postgres' AND database_connection_id IS NULL;
-- Result: 3 rows updated
```

**Verification:**
```bash
# Dashboard stats endpoint now returns correct data
curl http://localhost/api/v1/stats
{
  "total_slow_queries": 12,      # Was 0 before
  "total_analyzed": 12,          # Was 0 before
  "databases_monitored": 2,      # Was 0 before
  "improvement_summary": [
    {"improvement_level": "HIGH", "count": 7},
    {"improvement_level": "LOW", "count": 5}
  ]
}
```

**Impact:**
- ✅ Dashboard now shows real data (12 queries instead of 0)
- ✅ Slow Queries page displays all collected queries
- ✅ Statistics page shows correct database counts
- ✅ Future queries automatically associated correctly
- ✅ Visibility filtering works as intended

---

### Fixed - Password Encryption Key Management

#### Problem
Database connection test failing with "Failed to decrypt password" error. Root cause: backend was generating a new random encryption key on each restart, making previously encrypted passwords undecryptable.

#### Solution
- Added `ENCRYPTION_KEY` environment variable to `docker-compose.yml`
- Fixed encryption key to: `7BHYHtN7_SZKavPg-p-cKBlZN708esKVqmLS9Jk2BIU=`
- Re-encrypted existing database connection passwords

**Files Modified:**
- `docker-compose.yml` - Added ENCRYPTION_KEY environment variable (line 84)

**Security Note:**
- Encryption key should be rotated in production
- Store in secrets manager for production deployments
- Current key sufficient for development environment

---

### Fixed - Frontend/Backend Integration Issues

Fixed 11 frontend/backend integration errors discovered during deployment testing:

1. **Login 405 Error** - Auth endpoints missing `/api/v1` prefix
   - Fixed: `frontend/src/services/auth.service.ts`

2. **Stats Endpoint Error** - Missing `visible_connection_ids` parameter
   - Fixed: `backend/api/routes/stats.py:361-371`

3. **UUID Type Casting** - PostgreSQL query errors
   - Fixed: `backend/api/routes/stats.py:70,273` - Added `CAST(:visible_connection_ids AS uuid[])`

4. **Collectors Status 405** - Wrong route ordering
   - Fixed: `backend/api/routes/collectors.py:324-356` - Added `/status` before `/{collector_id}`

5. **Collectors Status 500** - Wrong column name (`last_heartbeat_at` → `last_heartbeat`)
   - Fixed: `backend/api/routes/collectors.py:347`

6. **Collectors Jobs Undefined** - Frontend expected different response structure
   - Fixed: `backend/api/routes/collectors.py:324-389` - Restructured response with jobs array

7. **Organizations .map Error** - Backend returns wrapped response
   - Fixed: `frontend/src/services/organization.service.ts:16` - Extract `.organizations`

8. **Teams .map Error** - Same wrapper issue
   - Fixed: `frontend/src/services/team.service.ts:16,71` - Extract `.teams` and `.members`

9. **Databases .map Error** - Same wrapper issue
   - Fixed: `frontend/src/services/database.service.ts:16` - Extract `.connections`

10. **Container Cache** - Frontend not using new build
    - Fixed: Used `docker compose up -d --force-recreate frontend`

11. **Browser Cache** - Old JavaScript files cached
    - Fixed: Hard refresh (Ctrl+Shift+R) required

**Files Modified:**
- `frontend/src/services/auth.service.ts` - API prefix
- `frontend/src/services/organization.service.ts` - Response unwrapping
- `frontend/src/services/team.service.ts` - Response unwrapping
- `frontend/src/services/database.service.ts` - Response unwrapping
- `backend/api/routes/stats.py` - Parameter and type fixes
- `backend/api/routes/collectors.py` - Route ordering and response structure

---

## [1.1.0] - 2025-10-31

### Added - Multi-Database Monitoring with Collectors

**Major Feature:** Complete multi-tenant database monitoring infrastructure.

#### Database Schema Changes

**Migration 004: Add Collectors and Visibility Support**
- Added `collectors` table to track agent instances
- Added `collector_databases` junction table for collector-to-database mapping
- Added `agent_token` column to `database_connections` (unique authentication token)
- Added `agent_token_created_at` timestamp
- Added `visibility_scope` enum: `TEAM_ONLY`, `ORG_WIDE`, `USER_ONLY`
- Added `owner_user_id` for connection ownership tracking
- Added `is_legacy` flag to distinguish legacy connections
- Added `organization_id` to all data tables for org-wide isolation
- Added `database_connection_id` to `slow_queries_raw`, `query_metrics_daily`, `query_fingerprint_metrics`

**Migration 005: Backfill Legacy Connections**
- Automatic detection and flagging of legacy database connections
- Default visibility scope set to `TEAM_ONLY`
- Auto-generation of agent tokens for existing connections

#### New API Endpoints

**Collector Management:**
- `POST /api/v1/collectors/register` - Register collector with agent_token (no JWT required)
- `POST /api/v1/collectors/ingest/slow-queries` - Unified ingestion endpoint (no JWT required)
- `POST /api/v1/collectors/{id}/heartbeat` - Collector heartbeat (requires JWT)
- `GET /api/v1/collectors` - List collectors for current team
- `GET /api/v1/collectors/status` - Get collector status and statistics
- `GET /api/v1/collectors/{id}` - Get specific collector details
- `POST /api/v1/collectors/{id}/deactivate` - Deactivate collector (OWNER/ADMIN only)

**Agent Token Management:**
- `POST /api/v1/database-connections/{id}/rotate-token` - Rotate agent token (OWNER/ADMIN only)
- `GET /api/v1/database-connections/{id}/agent-token` - Retrieve full agent token (OWNER/ADMIN only)

#### Backend Services

**Team Collector Scheduler** (`backend/services/scheduler_v2.py`)
- Multi-tenant slow query collection
- Auto-discovery of active DatabaseConnection records
- Per-connection collection with appropriate collectors
- Team and organization isolation
- Automatic heartbeat updates

**Visibility System** (`backend/core/visibility.py`)
- Helper functions for visibility filtering:
  - `get_user_team_ids()` - Get all teams user belongs to
  - `get_user_organization_ids()` - Get all orgs user belongs to
  - `get_visible_database_connections()` - Filter connections by visibility
  - `get_visible_database_connection_ids()` - Optimized ID-only filter

**Dependencies** (`backend/core/dependencies.py`)
- FastAPI dependency injection helpers
- `get_current_team()` - Team context from header
- `get_visible_database_connections()` - Filtered connections
- `get_visible_database_connection_ids()` - Filtered connection IDs

#### Security Model

**Agent Authentication:**
- Each database connection has a unique `agent_token` (generated via `secrets.token_urlsafe(32)`)
- Token prefixed with `agt_` for easy identification
- Tokens are one-way (can't derive database credentials from token)
- Token rotation capability for security
- JWT issued to collectors after registration (365-day validity)

**Visibility Scopes:**
- `TEAM_ONLY` (default): Only team members can view
- `ORG_WIDE`: All organization members can view
- `USER_ONLY`: Only the connection owner can view

**Multi-Tenancy:**
- All data isolated by `team_id` and `organization_id`
- Stats and queries filtered by visible connection IDs
- Collectors track which team/org they belong to

#### Files Added
- `backend/db/migrations/004_add_collectors_visibility.sql`
- `backend/db/migrations/005_backfill_legacy_connections.sql`
- `backend/services/scheduler_v2.py`
- `backend/core/visibility.py`
- `backend/api/schemas/collectors.py`
- `DOCS/MIGRATION_GUIDE.md`

#### Files Modified
- `backend/db/models.py` - Added Collector, CollectorDatabase models, updated DatabaseConnection
- `backend/api/routes/collectors.py` - New collector management endpoints
- `backend/api/routes/database_connections.py` - Added token management
- `backend/api/routes/stats.py` - Visibility filtering
- `backend/api/routes/slow_queries.py` - Visibility filtering
- `backend/core/dependencies.py` - Visibility helper dependencies

---

## [1.0.0] - 2025-10-31

### Completed - AI Query Analyzer Core Implementation

Full implementation of slow query monitoring, analysis, and optimization system.

#### Features Implemented

**1. Slow Query Collection**
- MySQL slow query collector using `mysql.slow_log` table
- PostgreSQL slow query collector using `pg_stat_statements` extension
- EXPLAIN plan generation for both database types
- Query fingerprinting and deduplication
- Background scheduled collection (APScheduler)

**Components:**
- `backend/services/mysql_collector.py` - MySQL slow query collection
- `backend/services/postgres_collector.py` - PostgreSQL slow query collection
- `backend/services/fingerprint.py` - Query fingerprinting and normalization
- `backend/services/scheduler.py` - Background collection scheduler

**2. Rule-Based Query Analysis**
- Automated analysis of EXPLAIN plans
- Pattern-based optimization detection
- Severity classification (CRITICAL, HIGH, MEDIUM, LOW)
- Improvement estimation (potential speedup)

**Analyzer Capabilities:**
- Full table scan detection
- Missing index identification
- Filesort operation detection
- High-cost query identification
- Rows examined vs returned ratio analysis

**Component:**
- `backend/services/analyzer.py` - Core analysis engine with MySQL and PostgreSQL plan analysis

**3. AI-Assisted Analysis (Optional)**
- OpenAI GPT-4 integration for deep query analysis
- Database context collection (schemas, indexes, statistics, foreign keys, configuration)
- Contextual recommendations based on actual database state
- JSON-structured analysis output

**Components:**
- `backend/services/ai_analysis.py` - AI analysis orchestration
- `backend/services/ai_stub.py` - OpenAI GPT-4 provider
- `backend/services/db_context_collector.py` - Database metadata collection

**4. Statistics & Trends**
- Database-level aggregated statistics
- Table impact analysis
- Query trend visualization
- Improvement summary by severity level

**Database Views:**
- `impactful_tables` - Tables appearing most in slow queries
- `query_fingerprint_metrics` - Aggregated metrics per query pattern
- `query_metrics_daily` - Daily query performance trends

**Components:**
- `backend/api/routes/stats.py` - Statistics API endpoints
- `backend/db/migrations/003_add_statistics_views.sql` - Database views

**5. Frontend Dashboard**
- Dashboard with key metrics overview
- Slow Queries page with filtering and sorting
- Query detail page with EXPLAIN visualization
- Collectors management page
- Statistics & Trends page

**Components:**
- `frontend/src/pages/Dashboard.tsx` - Main dashboard
- `frontend/src/pages/SlowQueries.tsx` - Query list and filtering
- `frontend/src/pages/QueryDetail.tsx` - Detailed query analysis
- `frontend/src/pages/Collectors.tsx` - Collector management
- `frontend/src/pages/Statistics.tsx` - Trends and analytics

#### Database Schema

**Core Tables:**
- `slow_queries_raw` - Raw slow query data from collectors
- `analysis_results` - Analysis results (heuristic and AI)
- `db_metadata` - Cached database metadata (tables, indexes, stats)

**Tracking Tables:**
- `query_fingerprint_metrics` (view) - Aggregated query pattern metrics
- `query_metrics_daily` (view) - Daily performance trends
- `impactful_tables` (view) - Most-queried tables

#### API Endpoints

**Slow Queries:**
- `GET /api/v1/slow-queries` - List slow queries with filtering
- `GET /api/v1/slow-queries/{id}` - Get query details
- `POST /api/v1/slow-queries/{id}/analyze` - Trigger heuristic analysis
- `POST /api/v1/slow-queries/{id}/analyze-ai` - Trigger AI analysis

**Statistics:**
- `GET /api/v1/stats/global` - Global statistics
- `GET /api/v1/stats/top-tables` - Most impacted tables
- `GET /api/v1/stats/query-trends` - Query performance trends
- `GET /api/v1/stats/databases` - List monitored databases

**Collectors:**
- `POST /api/v1/collectors/mysql/collect` - Trigger MySQL collection
- `POST /api/v1/collectors/postgres/collect` - Trigger PostgreSQL collection
- `GET /api/v1/collectors/status` - Get collector status

#### Configuration

**Environment Variables:**
- `INTERNAL_DB_*` - Internal database connection (PostgreSQL)
- `MYSQL_*` - Target MySQL database connection
- `PG_*` - Target PostgreSQL database connection
- `REDIS_*` - Redis connection for caching
- `AI_PROVIDER` - AI provider selection (openai, stub)
- `AI_API_KEY` - OpenAI API key
- `AI_MODEL` - Model selection (gpt-4, gpt-4o-mini)

#### Testing

**Test Lab Setup:**
- Dedicated test databases (`ai-query-lab`)
- Slow query generators for MySQL and PostgreSQL
- Synthetic data generation (100k customers, 1M orders)
- Complex query patterns for testing

**Test Scripts:**
- `ai-query-lab/db/mysql/generate_heavy_slow_queries.sh` - MySQL load testing
- `ai-query-lab/test_slow_queries.sh` - Integration testing
- `test_collectors.py` - Collector unit tests

#### Documentation

- `DOCS/IMPLEMENTATION_COMPLETE.md` - Implementation summary
- `DOCS/STEP5_REPORT.md` - Analyzer implementation details
- `DOCS/TESTING_GUIDE.md` - Testing procedures
- `DOCS/QUICK_START.md` - Quick start guide
- `DOCS/ENVIRONMENT_GUIDE.md` - Environment setup

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (React)                       │
│  - Dashboard, Slow Queries, Statistics, Collectors       │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/REST
┌────────────────────▼────────────────────────────────────┐
│                Backend (FastAPI)                         │
│  - REST API, Authentication, Analysis Orchestration      │
└─────┬──────────────┬──────────────┬────────────────────┘
      │              │              │
      ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────────┐
│ Internal │  │  Redis   │  │  External    │
│   DB     │  │ (Cache)  │  │  Databases   │
│(Postgres)│  │          │  │(MySQL,       │
│          │  │          │  │ PostgreSQL)  │
└──────────┘  └──────────┘  └──────────────┘
     │                              ▲
     │                              │
     ▼                              │
┌─────────────────┐        ┌───────┴─────────┐
│   Collectors    │────────│   Schedulers    │
│  (Background)   │        │ (APScheduler)   │
└─────────────────┘        └─────────────────┘
```

### Data Flow

1. **Collection:** Schedulers trigger collectors every 5 minutes
2. **Storage:** Collectors save slow queries to `slow_queries_raw`
3. **Analysis:** Analyzer processes queries and saves to `analysis_results`
4. **Frontend:** Dashboard displays analyzed queries with recommendations
5. **AI Enhancement:** Optional AI analysis provides deeper insights

---

## Future Enhancements

### Planned Features
- [ ] Agent container for on-premise deployment
- [ ] Docker Hub distribution for agent
- [ ] Helm chart for Kubernetes deployment
- [ ] Advanced security (mTLS, certificate pinning)
- [ ] Query sanitization for data privacy
- [ ] Multi-database support in single agent
- [ ] Agent health monitoring dashboard

### Under Consideration
- [ ] Real-time query monitoring
- [ ] Alerting system for critical queries
- [ ] Query performance regression detection
- [ ] Automated query optimization suggestions
- [ ] Index recommendation engine
- [ ] Cost estimation for query optimizations

---

## Migration Notes

### From 1.0.0 to 1.1.0
Run migrations 004 and 005 to enable multi-database monitoring:
```bash
docker exec ai-analyzer-backend python -c "
from pathlib import Path
from backend.db.session import SessionLocal

db = SessionLocal()
try:
    for migration in ['004_add_collectors_visibility.sql', '005_backfill_legacy_connections.sql']:
        with open(f'backend/db/migrations/{migration}', 'r') as f:
            db.execute(f.read())
    db.commit()
    print('✓ Migrations completed')
except Exception as e:
    db.rollback()
    print(f'✗ Migration failed: {e}')
    raise
finally:
    db.close()
"
```

### From 1.1.0 to 1.2.0
No database migrations required. Backend restart will apply collector fixes automatically.

---

## Contributors

- **Claude AI Assistant** - Core implementation, architecture, and documentation
- **Mirko Siddi** - Product requirements, testing, and validation

---

## License

Proprietary - All rights reserved

---

## Support

For issues, questions, or feature requests, please contact the development team.
