# Testing Quick Reference

This guide provides a quick reference for all available testing and troubleshooting tools.

## Quick Start (Complete Setup)

If you're starting fresh, use this one command to set everything up:

```bash
./quick-start.sh
```

This will:
- ✓ Start internal PostgreSQL + Redis
- ✓ Initialize database schema
- ✓ Start MySQL lab database
- ✓ Wait for data to load
- ✓ Run sample slow queries
- ✓ Verify integration

**Time required:** 10-15 minutes (mostly waiting for data generation)

---

## Individual Test Scripts

### 1. Integration Verification

**Test the complete system end-to-end:**

```bash
python3 verify-integration.py
```

**Options:**
```bash
# Skip collector test
python3 verify-integration.py --skip-collector

# Skip analyzer test
python3 verify-integration.py --skip-analyzer

# Test but don't collect queries
python3 verify-integration.py --no-collection

# Test but don't analyze queries
python3 verify-integration.py --no-analysis
```

**What it tests:**
- Internal PostgreSQL connection
- MySQL lab database connection and data
- Collector functionality
- Analyzer functionality
- Database statistics

---

### 2. Collector Test

**Test only the MySQL collector:**

```bash
python3 test-collectors.py
```

**Options:**
```bash
# Fetch up to 20 queries
python3 test-collectors.py --limit 20

# Test but don't store in database
python3 test-collectors.py --no-store
```

**What it tests:**
- MySQL connection
- Slow query log configuration
- Fetching slow queries from log
- Storing queries in internal database

---

### 3. Analyzer Test

**Test only the query analyzer:**

```bash
python3 test-analyzer.py
```

**Options:**
```bash
# Analyze up to 20 queries
python3 test-analyzer.py --limit 20

# Just show stats, don't analyze
python3 test-analyzer.py --no-analyze
```

**What it tests:**
- Pending query count
- Analysis execution
- Analysis results and breakdowns
- Suggestion generation

---

### 4. Original Integration Test (Bash)

**Complete integration test with all components:**

```bash
./test-integration.sh
```

This is the original comprehensive bash script that:
- Starts both databases
- Initializes schema
- Waits for data loading
- Runs slow queries
- Tests collector
- Tests analyzer
- Shows results

**Time required:** 10-15 minutes

---

## Troubleshooting Tools

### MySQL Connection Issues

**Run the diagnostic script:**

```bash
cd lab-database
./troubleshoot-connection.sh
```

This checks:
- Container status
- MySQL initialization progress
- Connection from inside container
- Connection from host
- Database and data status
- Bind address configuration
- Port binding

**Manual checks:**

```bash
# Check container logs
docker logs mysql-lab-slowquery

# Look for "ready for connections" (should appear TWICE)
docker logs mysql-lab-slowquery 2>&1 | grep "ready for connections"

# Test connection from inside container
docker exec mysql-lab-slowquery mysql -uroot -proot -e "SELECT 1;"

# Test from host (correct syntax)
mysql -h 127.0.0.1 -P 3307 -u root -proot -e "SELECT 1;"

# Check data loading progress
mysql -h 127.0.0.1 -P 3307 -u root -proot ecommerce_lab \
  -e "SELECT COUNT(*) FROM users;"
```

**Common Issues:**

| Issue | Cause | Solution |
|-------|-------|----------|
| "Lost connection" error | MySQL still initializing | Wait 2-5 minutes, check logs |
| Container shows "healthy" but can't connect | Initialization scripts running | Wait for "ready for connections" (2x) |
| "Can't connect to port 3306" | Wrong command syntax | Use `-P 3307` (uppercase P) not `-p 3307` |
| No slow queries found | Log not enabled or empty | Run `./start-lab.sh test` |
| Data count = 0 | Still loading | Wait 5-10 minutes for stored procedures |

**Full troubleshooting guide:**

```bash
# Read the comprehensive guide
cat lab-database/CONNECTION_TROUBLESHOOTING.md

# Or view it online
less lab-database/CONNECTION_TROUBLESHOOTING.md
```

---

## Database Management

### Start Databases

```bash
# Internal database (PostgreSQL + Redis)
docker compose -f docker-compose.internal.yml up -d

# Lab database (MySQL)
cd lab-database && ./start-lab.sh start
```

### Stop Databases

```bash
# Stop internal database
docker compose -f docker-compose.internal.yml down

# Stop lab database
cd lab-database && ./start-lab.sh stop
```

### Check Database Status

```bash
# Check all containers
docker ps

# Check internal database health
docker compose -f docker-compose.internal.yml ps

# Check lab database logs
docker logs mysql-lab-slowquery

# Check data loading progress
watch -n 5 'mysql -h 127.0.0.1 -P 3307 -u root -proot ecommerce_lab \
  -e "SELECT COUNT(*) FROM users;"'
```

---

## Running Slow Queries

### Run All 27 Test Queries

```bash
cd lab-database
./start-lab.sh test
```

### Run Specific Queries

```bash
# Run queries from the SQL file
mysql -h 127.0.0.1 -P 3307 -u root -proot ecommerce_lab < scripts/slow-queries.sql

# Run a single query
mysql -h 127.0.0.1 -P 3307 -u root -proot ecommerce_lab \
  -e "SELECT * FROM users WHERE email = 'user50000@example.com';"
```

---

## API Testing

### Start API Server

```bash
# Make sure environment is loaded
export $(cat .env.lab | grep -v '#' | xargs)

# Start server
uvicorn backend.main:app --reload
```

### Test Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Get slow queries
curl http://localhost:8000/api/v1/slow-queries | jq

# Get analyzer status
curl http://localhost:8000/api/v1/analyzer/status | jq

# Get specific query
curl http://localhost:8000/api/v1/slow-queries/{query_id} | jq

# Trigger collection (manual)
curl -X POST http://localhost:8000/api/v1/collector/run | jq

# Trigger analysis (manual)
curl -X POST http://localhost:8000/api/v1/analyzer/analyze | jq
```

### View API Documentation

Open in browser:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Development Workflow

### Typical Development Flow

```bash
# 1. Start databases (first time)
./quick-start.sh

# 2. Make code changes
vim backend/services/analyzer.py

# 3. Test changes
python3 test-analyzer.py

# 4. Run integration test
python3 verify-integration.py

# 5. Start API server
uvicorn backend.main:app --reload

# 6. Test API
curl http://localhost:8000/api/v1/analyzer/status | jq
```

### Running Tests After Changes

```bash
# If you changed the collector
python3 test-collectors.py

# If you changed the analyzer
python3 test-analyzer.py

# If you changed database models
# 1. Drop and recreate schema
PYTHONPATH=. python3 -c "from backend.db.session import engine; \
  from backend.db.models import Base; \
  Base.metadata.drop_all(engine); \
  Base.metadata.create_all(engine)"

# 2. Run integration test
python3 verify-integration.py

# If you changed API endpoints
# 1. Start server
uvicorn backend.main:app --reload

# 2. Test in browser
# http://localhost:8000/docs
```

---

## Monitoring Data Loading

### Watch Data Load Progress

```bash
# Watch user count (refreshes every 5 seconds)
watch -n 5 'mysql -h 127.0.0.1 -P 3307 -u root -proot ecommerce_lab \
  -e "SELECT COUNT(*) FROM users;"'

# Watch all table counts
watch -n 5 'mysql -h 127.0.0.1 -P 3307 -u root -proot ecommerce_lab \
  -e "SELECT
    (SELECT COUNT(*) FROM users) as users,
    (SELECT COUNT(*) FROM products) as products,
    (SELECT COUNT(*) FROM orders) as orders,
    (SELECT COUNT(*) FROM order_items) as items;"'
```

### Expected Data Volumes

| Table | Expected Count | Load Time |
|-------|---------------|-----------|
| users | 100,000 | 1-2 min |
| products | 50,000 | 1 min |
| categories | 50 | < 1 sec |
| orders | 500,000 | 3-5 min |
| order_items | 2,000,000+ | 5-10 min |
| reviews | 300,000 | 2-3 min |
| inventory_log | 1,000,000 | 5-7 min |

**Total:** ~4.7 million rows, 5-10 minutes to load completely

---

## Environment Files

### .env.lab

Main configuration for lab environment:

```bash
# Internal Database
INTERNAL_DB_HOST=localhost
INTERNAL_DB_PORT=5440
INTERNAL_DB_USER=ai_core
INTERNAL_DB_PASSWORD=ai_core
INTERNAL_DB_NAME=ai_core

# MySQL Lab Database
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3307
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DB=ecommerce_lab

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
```

### Loading Environment

```bash
# In bash
export $(cat .env.lab | grep -v '#' | xargs)

# In Python (automatically loaded by test scripts)
# See test-collectors.py or test-analyzer.py for example
```

---

## Summary of All Scripts

| Script | Purpose | Time | Prerequisites |
|--------|---------|------|---------------|
| `quick-start.sh` | Complete setup from scratch | 10-15 min | Docker, Python |
| `verify-integration.py` | Test all components | 30 sec | DBs running |
| `test-collectors.py` | Test collector only | 10 sec | MySQL running |
| `test-analyzer.py` | Test analyzer only | 10 sec | Queries collected |
| `test-integration.sh` | Full bash integration test | 10-15 min | Docker, Python |
| `troubleshoot-connection.sh` | Diagnose MySQL issues | 30 sec | Docker |

---

## Getting Help

### Documentation

- **Integration Testing:** `INTEGRATION_TESTING_GUIDE.md`
- **Troubleshooting:** `lab-database/CONNECTION_TROUBLESHOOTING.md`
- **Application Analysis:** `COMPREHENSIVE_TEST_REPORT.md`
- **This Guide:** `TESTING_QUICKREF.md`

### Check Logs

```bash
# Internal database logs
docker compose -f docker-compose.internal.yml logs internal-db

# Redis logs
docker compose -f docker-compose.internal.yml logs redis

# MySQL logs (full)
docker logs mysql-lab-slowquery

# MySQL logs (last 50 lines)
docker logs mysql-lab-slowquery 2>&1 | tail -50

# API server logs (if running)
# Check your terminal where uvicorn is running
```

### Common Commands Cheat Sheet

```bash
# Status check
docker ps
docker compose -f docker-compose.internal.yml ps

# Database connections
mysql -h 127.0.0.1 -P 3307 -u root -proot ecommerce_lab
docker exec -it ai-analyzer-internal-db psql -U ai_core -d ai_core

# Quick tests
python3 -c "from backend.db.session import check_db_connection; print(check_db_connection())"
mysql -h 127.0.0.1 -P 3307 -u root -proot -e "SELECT 1;"

# Restart everything
docker compose -f docker-compose.internal.yml restart
cd lab-database && ./start-lab.sh restart

# Clean slate
docker compose -f docker-compose.internal.yml down -v
cd lab-database && ./start-lab.sh stop
docker volume prune -f
```

---

**Last Updated:** 2025-11-13
