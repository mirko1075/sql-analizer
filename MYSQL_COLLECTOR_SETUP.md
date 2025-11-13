# MySQL Collector Setup Guide

## ✅ Current Configuration

The MySQL collector is configured and ready to collect slow queries from your MySQL database at `127.0.0.1:3306`.

### Configuration Details
- **Host**: `127.0.0.1` (localhost via host.docker.internal)
- **Port**: `3306`
- **User**: `root`
- **Password**: `admin`
- **Monitoring**: All databases

### Excluded Queries
The collector automatically excludes:
- Test queries with `SLEEP()`
- Queries containing `slow_log` references
- Queries with `test query` or `monitoring` keywords
- `SHOW` and `EXPLAIN` commands
- Other monitoring/diagnostic queries

## 📊 Using the Collector

### 1. Test MySQL Connection

```bash
# Get authentication token
TOKEN=$(curl -s -X POST 'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@dbpower.com","password":"admin123"}' | jq -r '.access_token')

# Test MySQL connection
curl -s 'http://localhost:8000/api/v1/collectors/mysql/test' \
  -H "Authorization: Bearer $TOKEN" | jq
```

Expected output:
```json
{
  "success": true,
  "mysql_version": "8.0.36",
  "host": "host.docker.internal",
  "port": 3306,
  "slow_log_count": 7,
  "slow_log_enabled": "ON",
  "message": "Successfully connected to MySQL 8.0.36"
}
```

### 2. Collect Slow Queries

```bash
# Collect queries from last 24 hours (min 0.5 seconds)
curl -s -X POST 'http://localhost:8000/api/v1/collectors/mysql/collect?lookback_minutes=1440&min_query_time=0.5' \
  -H "Authorization: Bearer $TOKEN" | jq

# Collect queries from last 7 days (min 1 second)
curl -s -X POST 'http://localhost:8000/api/v1/collectors/mysql/collect?lookback_minutes=10080&min_query_time=1.0' \
  -H "Authorization: Bearer $TOKEN" | jq
```

**Parameters:**
- `lookback_minutes`: How far back to look (1-15000 minutes, ~10 days max)
- `min_query_time`: Minimum query time in seconds (0.1-inf seconds)

Expected output:
```json
{
  "status": "success",
  "message": "Collected 15 queries (skipped 3 duplicates)",
  "queries_collected": 15,
  "queries_skipped": 3,
  "lookback_minutes": 1440,
  "min_query_time": 0.5,
  "organization_id": 1,
  "team_id": 1
}
```

### 3. View Collected Queries

```bash
# List all queries
curl -s 'http://localhost:8000/api/v1/queries?limit=20' \
  -H "Authorization: Bearer $TOKEN" | jq

# Get query detail with automatic rule-based analysis
curl -s 'http://localhost:8000/api/v1/queries/1' \
  -H "Authorization: Bearer $TOKEN" | jq
```

## 🧪 Generate Test Slow Queries

If your MySQL slow_log is empty, you can generate real slow queries for testing:

```bash
# Run the test script
mysql -h 127.0.0.1 -u root -padmin < backend/test_generate_slow_queries.sql

# Wait a moment, then collect
curl -s -X POST 'http://localhost:8000/api/v1/collectors/mysql/collect?lookback_minutes=60&min_query_time=0.1' \
  -H "Authorization: Bearer $TOKEN" | jq
```

## 🔧 MySQL Configuration

Ensure MySQL slow query log is enabled:

```sql
-- Check current settings
SHOW VARIABLES LIKE 'slow_query_log';
SHOW VARIABLES LIKE 'long_query_time';

-- Enable slow query log (if needed)
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 0.5;  -- Log queries > 0.5 seconds

-- Use TABLE logging (required for collector)
SET GLOBAL log_output = 'TABLE';
```

## 📝 Frontend Usage

### Query List View
- Shows all collected queries from MySQL slow_log
- Only REAL queries (no fake/demo data)
- Automatically filtered by organization (multi-tenant)

### Query Detail View
- **Automatic Rule-Based Analysis**: Shown immediately when opening query detail
  - 10 heuristic rules checking for common issues
  - Severity levels: LOW, MEDIUM, HIGH, CRITICAL
  - Estimated speedup and improvement suggestions
  - Confidence score: 0.75 (rule-based)

- **AI Analysis**: On-demand only
  - Click "Analyze now" button to trigger AI-powered analysis
  - Higher confidence score
  - More detailed insights

## 🎯 Current State

- ✅ Database is clean (no demo data)
- ✅ MySQL collector configured and working
- ✅ Monitoring queries automatically excluded
- ✅ Rule-based analysis automatic on query detail
- ✅ Multi-tenant isolation enabled
- ✅ Deduplication working (same query + timestamp)

## 🚀 Production Usage

1. Point collector to your production MySQL server
2. Update `docker-compose.yml`:
   ```yaml
   MYSQL_HOST: your-production-mysql-host
   MYSQL_PORT: 3306
   MYSQL_USER: monitoring_user
   MYSQL_PASSWORD: secure_password
   ```
3. Restart backend: `docker compose restart backend`
4. Run collection manually or via scheduler

## 📊 Monitoring

Check collector logs:
```bash
docker logs ai-analyzer-backend --tail 50 | grep -i "mysql\|collecting"
```

View database queries directly:
```bash
docker exec -i ai-analyzer-internal-db psql -U ai_core -d ai_core \
  -c "SELECT id, database_name, query_time, LEFT(sql_text, 60) FROM slow_queries ORDER BY collected_at DESC LIMIT 10;"
```
