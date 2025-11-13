# AI Query Analyzer - Integration Testing Guide

## Overview

This guide explains how to test the complete AI Query Analyzer system with the MySQL Slow Query Lab Database.

**Date:** 2025-11-13
**Status:** ✅ READY FOR TESTING
**Critical Fix:** Missing `backend.db` module has been implemented

---

## What Was Fixed

### 🔴 Critical Issue Resolved

**Problem:** The `backend/db/` module was completely missing, preventing the application from running.

**Solution:** Implemented complete database layer with:
- ✅ SQLAlchemy ORM models (5 tables)
- ✅ Database session management
- ✅ Connection pooling
- ✅ Schema initialization

**Files Created:**
```
backend/db/
├── __init__.py          # Package exports
├── models.py            # 5 ORM models (296 lines)
└── session.py           # Session management (157 lines)
```

### ✅ System Status

| Component | Status | Details |
|-----------|--------|---------|
| Backend Code | ✅ Complete | 3,649 lines, all imports working |
| Frontend Code | ✅ Complete | 1,895 lines, React + TypeScript |
| Database Layer | ✅ **FIXED** | 5 models implemented |
| API Endpoints | ✅ Functional | 20 endpoints registered |
| Lab Database | ✅ Ready | 4.7M rows, 27 slow queries |
| Test Scripts | ✅ Created | Full integration test |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  AI Query Analyzer System                     │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌─────────────────┐                                          │
│  │   MySQL Lab DB  │  ← Intentionally slow queries            │
│  │  (ecommerce_lab)│                                          │
│  │   4.7M rows     │                                          │
│  │   Port 3307     │                                          │
│  └────────┬────────┘                                          │
│           │                                                    │
│           ↓ [Collector connects]                              │
│  ┌─────────────────┐                                          │
│  │  FastAPI Backend│                                          │
│  │   Port 8000     │                                          │
│  │                 │                                          │
│  │  - Collectors   │ ← MySQL/PostgreSQL collectors            │
│  │  - Analyzer     │ ← Rule-based + AI stub                   │
│  │  - Scheduler    │ ← Every 5 min (collectors)               │
│  │                 │   Every 10 min (analyzer)                │
│  └────────┬────────┘                                          │
│           │                                                    │
│           ↓ [Stores results]                                  │
│  ┌─────────────────────────────────────────────────┐          │
│  │  Internal PostgreSQL    │        Redis          │          │
│  │  (ai_core)              │      (Cache)          │          │
│  │  Port 5440              │      Port 6379        │          │
│  │                         │                        │          │
│  │  5 Tables:              │                        │          │
│  │  - slow_queries_raw     │                        │          │
│  │  - analysis_result      │                        │          │
│  │  - db_metadata          │                        │          │
│  │  - optimization_history │                        │          │
│  │  - schema_version       │                        │          │
│  └─────────────────────────────────────────────────┘          │
└──────────────────────────────────────────────────────────────┘
```

---

## Database Models

### 1. SlowQueryRaw

Stores raw slow query records collected from monitored databases.

**Columns:**
- `id` (UUID) - Primary key
- `source_db_type` - 'mysql' or 'postgresql'
- `source_db_host`, `source_db_name`, `source_db_port`
- `fingerprint` - SHA-256 hash of normalized query
- `full_sql` - Complete SQL statement
- `duration_ms` - Query execution time
- `rows_examined`, `rows_returned` - Performance metrics
- `plan_json`, `plan_text` - EXPLAIN output
- `status` - NEW, ANALYZED, IGNORED, ERROR
- `captured_at`, `created_at`, `updated_at`

**Indexes:**
- `idx_source_db` (source_db_type, source_db_host)
- `idx_fingerprint_db` (fingerprint, source_db_type)
- `idx_status_captured` (status, captured_at)
- `idx_duration` (duration_ms)

### 2. AnalysisResult

Stores query analysis results and optimization suggestions.

**Columns:**
- `id` (UUID) - Primary key
- `slow_query_id` (FK) - References slow_queries_raw
- `problem` - Issue description
- `root_cause` - Why it's slow
- `suggestions` (JSON) - Array of optimization suggestions
- `improvement_level` - LOW, MEDIUM, HIGH, CRITICAL
- `estimated_speedup` - e.g., "10-100x"
- `analyzer_version` - Analyzer version used
- `analysis_method` - rule_based, ai_assisted, hybrid
- `confidence_score` - 0.00 to 1.00
- `analysis_metadata` (JSON) - Additional data
- `analyzed_at`, `created_at`

**Indexes:**
- `idx_improvement_level`
- `idx_analyzed_at`

### 3. DbMetadata

Tracks metadata about monitored databases.

**Columns:**
- Database identification (type, host, name, port)
- Table information
- Column and index definitions (JSON)
- Row count estimates
- Table size

### 4. OptimizationHistory

Tracks applied optimizations and their effectiveness.

**Columns:**
- Optimization details (type, SQL statement)
- Before/after performance metrics
- Effectiveness tracking
- Applied by (user/system)

### 5. SchemaVersion

Database schema version tracking for migrations.

---

## Quick Start (Docker Required)

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- 10GB+ disk space

### Option 1: Automated Integration Test

**One command to test everything:**

```bash
cd /path/to/dbpower-ai-cloud
./test-integration.sh
```

This script:
1. ✅ Starts internal PostgreSQL + Redis
2. ✅ Starts MySQL lab database
3. ✅ Initializes database schema
4. ✅ Waits for lab data to load (5-10 min)
5. ✅ Runs sample slow queries
6. ✅ Tests MySQL collector
7. ✅ Tests query analyzer
8. ✅ Verifies results

**Expected Runtime:** 15-20 minutes (mostly waiting for data to load)

### Option 2: Manual Step-by-Step

#### Step 1: Start Internal Database

```bash
# Start PostgreSQL + Redis for storing results
docker compose -f docker-compose.internal.yml up -d

# Wait for healthy status
docker compose -f docker-compose.internal.yml ps

# Expected output:
# internal-db  Up (healthy)
# redis        Up (healthy)
```

#### Step 2: Start Lab Database

```bash
cd lab-database

# Start MySQL lab with slow query data
./start-lab.sh start

# Wait for data to load (5-10 minutes)
./start-lab.sh status

# Expected output:
# ✓ Lab database is running
# ✓ MySQL is accepting connections
#
# Data statistics:
# users:          100,000
# products:        50,000
# orders:         500,000
# order_items:  2,000,000+
# reviews:        300,000
# inventory_log: 1,000,000
```

#### Step 3: Configure Environment

```bash
cd ..

# Use lab environment configuration
cp .env.lab .env

# Or set environment variables manually:
export MYSQL_HOST=127.0.0.1
export MYSQL_PORT=3307
export MYSQL_USER=root
export MYSQL_PASSWORD=root
export MYSQL_DB=ecommerce_lab

export INTERNAL_DB_HOST=localhost
export INTERNAL_DB_PORT=5440
export INTERNAL_DB_USER=ai_core
export INTERNAL_DB_PASSWORD=ai_core
export INTERNAL_DB_NAME=ai_core
```

#### Step 4: Initialize Internal Database Schema

```bash
cd backend

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Initialize schema
python3 << 'EOF'
from backend.db.session import init_db, check_db_connection

if check_db_connection():
    print("✓ Database connection successful")
    init_db()
    print("✓ Schema initialized")
else:
    print("✗ Database connection failed")
EOF
```

#### Step 5: Run Slow Queries in Lab Database

```bash
cd ../lab-database

# Run all 27 slow queries (takes 3-10 minutes)
./start-lab.sh test

# Or run just a few manually:
mysql -h 127.0.0.1 -P 3307 -u root -proot ecommerce_lab << 'SQL'
-- Email lookup without index (SLOW-001)
SELECT user_id, username, email FROM users
WHERE email = 'user50000@example.com';

-- Country filter without index (SLOW-002)
SELECT COUNT(*) as user_count, country FROM users
WHERE country IN ('US', 'UK', 'CA')
GROUP BY country;

-- Product category scan (SLOW-003)
SELECT product_id, product_name, price FROM products
WHERE category_id = 25
ORDER BY price DESC
LIMIT 20;
SQL
```

#### Step 6: Test MySQL Collector

```bash
cd ..

# Method 1: Using test script
python3 test_collectors.py

# Method 2: Using API (if backend running)
curl -X POST http://localhost:8000/api/v1/collectors/mysql/collect

# Method 3: Direct Python
python3 << 'EOF'
from backend.services.mysql_collector import MySQLCollector

collector = MySQLCollector()
if collector.connect():
    count = collector.collect_and_store()
    print(f"✓ Collected {count} slow queries")
    collector.disconnect()
EOF
```

**Expected Output:**
```
MySQL Collector Test
============================================================

✓ Connected to MySQL lab database
✓ Found 5 slow queries in log

Sample query:
  SQL: SELECT user_id, username, email FROM users WHERE email = ?...
  Duration: 1.23s
  Rows examined: 100000

✓ Collected and stored 5 queries
```

#### Step 7: Test Query Analyzer

```bash
# Method 1: Using test script
python3 test_analyzer.py

# Method 2: Using API (if backend running)
curl -X POST http://localhost:8000/api/v1/analyzer/analyze

# Method 3: Direct Python
python3 << 'EOF'
from backend.services.analyzer import QueryAnalyzer

analyzer = QueryAnalyzer()
count = analyzer.analyze_all_pending(limit=10)
print(f"✓ Analyzed {count} queries")
EOF
```

**Expected Output:**
```
Query Analyzer Test
============================================================

Found 5 pending queries to analyze
✓ Analyzed 5 queries

Sample analyses:

  Problem: Full table scan detected
  Improvement Level: HIGH
  Estimated Speedup: 10-100x
  Confidence: 0.90
  Suggestions: 1 recommendations
```

#### Step 8: Verify Results

```bash
# Query the internal database
python3 << 'EOF'
from backend.db.session import get_db_context
from backend.db.models import SlowQueryRaw, AnalysisResult
from sqlalchemy import func

with get_db_context() as db:
    total = db.query(func.count(SlowQueryRaw.id)).scalar()
    analyzed = db.query(func.count(SlowQueryRaw.id)).filter(
        SlowQueryRaw.status == 'ANALYZED'
    ).scalar()

    breakdown = db.query(
        AnalysisResult.improvement_level,
        func.count(AnalysisResult.id)
    ).group_by(AnalysisResult.improvement_level).all()

    print(f"\nTotal slow queries: {total}")
    print(f"Analyzed: {analyzed}")
    print("\nImprovement breakdown:")
    for level, count in breakdown:
        print(f"  {level.value}: {count}")
EOF
```

**Expected Output:**
```
Total slow queries: 5
Analyzed: 5

Improvement breakdown:
  HIGH: 3
  MEDIUM: 1
  LOW: 1
```

---

## Testing Without Docker

If Docker is not available, you can still test parts of the system:

### Test Backend Imports and Configuration

```bash
cd backend

# Test all imports work
python3 << 'EOF'
from backend.db import models, session
from backend.services import mysql_collector, analyzer
from backend.api.routes import slow_queries, stats

print("✓ All imports successful")
print(f"✓ Database models: {len(models.Base.metadata.tables)}")
EOF
```

### Test API Endpoint Structure

```bash
python3 test_server.py
```

**Expected Output:**
```
✓ All modules imported successfully
✓ FastAPI app created
✓ 20+ API endpoints registered
⚠ Database connection failed (expected - no Docker)
```

---

## API Testing

### Start Backend Server

```bash
cd backend

# Method 1: Direct Python
python3 main.py

# Method 2: With uvicorn
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Test Endpoints

```bash
# Health check
curl http://localhost:8000/health

# List slow queries
curl http://localhost:8000/api/v1/slow-queries

# Get statistics
curl http://localhost:8000/api/v1/stats

# Trigger collection
curl -X POST http://localhost:8000/api/v1/collectors/mysql/collect

# Trigger analysis
curl -X POST http://localhost:8000/api/v1/analyzer/analyze

# Get collector status
curl http://localhost:8000/api/v1/collectors/status

# Get analyzer status
curl http://localhost:8000/api/v1/analyzer/status

# View API docs
open http://localhost:8000/docs
```

---

## Expected Results

### Slow Query Collection

**SLOW-001: Email Lookup**
```json
{
  "fingerprint": "select user_id username email from users where email = ?",
  "duration_ms": 1234.56,
  "rows_examined": 100000,
  "rows_returned": 1,
  "status": "NEW"
}
```

### Analysis Result

**For SLOW-001:**
```json
{
  "problem": "Full table scan detected",
  "root_cause": "Query performs full table scan on users table (100K rows). No index on email column causes every row to be examined.",
  "improvement_level": "HIGH",
  "estimated_speedup": "10-100x",
  "confidence_score": 0.90,
  "suggestions": [
    {
      "type": "INDEX",
      "priority": "HIGH",
      "description": "Create index on email column",
      "sql": "CREATE INDEX idx_email ON users(email);",
      "estimated_impact": "100-400x improvement"
    }
  ]
}
```

### Performance Improvements

| Query | Before | After Index | Improvement |
|-------|--------|-------------|-------------|
| SLOW-001 | 1.2s | 5ms | 240x |
| SLOW-002 | 800ms | 10ms | 80x |
| SLOW-003 | 1.5s | 15ms | 100x |
| SLOW-008 | 5s | 100ms | 50x |
| SLOW-014 | 20s | 200ms | 100x |

---

## Troubleshooting

### Backend Won't Start

**Error:** `ModuleNotFoundError: No module named 'backend.db'`

**Solution:**
```bash
# Check if files exist
ls -la backend/db/

# Files should exist:
# __init__.py
# models.py
# session.py

# If missing, pull latest code:
git pull origin claude/analyze-and-test-app-01GJS2d5iRRq1nonQZLAWTLn
```

### Database Connection Failed

**Error:** `Connection refused` on port 5440

**Solution:**
```bash
# Start internal database
docker compose -f docker-compose.internal.yml up -d

# Wait for healthy status
docker compose -f docker-compose.internal.yml ps

# Check logs
docker compose -f docker-compose.internal.yml logs internal-db
```

### Lab Database Not Loading Data

**Issue:** `users` table has 0 rows

**Solution:**
```bash
cd lab-database

# Check container logs
docker compose logs mysql-lab | tail -100

# Look for "ready for connections" message
# Data loading takes 5-10 minutes via stored procedures

# Check progress
mysql -h 127.0.0.1 -P 3307 -u root -proot ecommerce_lab \
  -e "SELECT COUNT(*) FROM users;"
```

### Collector Not Finding Slow Queries

**Issue:** Collector returns 0 queries

**Solution:**
```bash
# 1. Verify slow query log is enabled
mysql -h 127.0.0.1 -P 3307 -u root -proot -e \
  "SHOW VARIABLES LIKE 'slow_query_log%';"

# Should show: ON

# 2. Check slow query log
mysql -h 127.0.0.1 -P 3307 -u root -proot -e \
  "SELECT COUNT(*) FROM mysql.slow_log;"

# 3. Run some slow queries first
cd lab-database
./start-lab.sh test
```

---

## File Summary

### Created/Fixed Files

| File | Type | Purpose |
|------|------|---------|
| `backend/db/__init__.py` | Python | Database package exports |
| `backend/db/models.py` | Python | 5 SQLAlchemy ORM models |
| `backend/db/session.py` | Python | Session management |
| `.env.lab` | Config | Lab environment variables |
| `docker-compose.internal.yml` | Docker | Internal DB + Redis |
| `test-integration.sh` | Bash | Full integration test |
| `lab-database/` | Directory | Complete lab database |
| `COMPREHENSIVE_TEST_REPORT.md` | Doc | Analysis report |
| `INTEGRATION_TESTING_GUIDE.md` | Doc | This file |

---

## Next Steps

1. **Test with Docker**
   - Run `./test-integration.sh`
   - Verify all components work together

2. **Frontend Testing**
   - Start backend: `cd backend && python3 main.py`
   - Start frontend: `cd frontend && npm run dev`
   - Access: `http://localhost:3000`

3. **Production Deployment**
   - Implement authentication (JWT)
   - Add unit tests (pytest)
   - Configure HTTPS
   - Set up monitoring
   - Performance optimization

4. **AI Integration**
   - Replace AI stub with real OpenAI/Anthropic API
   - Fine-tune prompts
   - Implement learning loop

---

## Support

For issues:
1. Check `COMPREHENSIVE_TEST_REPORT.md` for known issues
2. Review `lab-database/README.md` for lab database help
3. Check Docker logs: `docker compose logs`

---

**Created:** 2025-11-13
**Version:** 1.0.0
**Status:** ✅ Ready for Testing
**Branch:** `claude/analyze-and-test-app-01GJS2d5iRRq1nonQZLAWTLn`
