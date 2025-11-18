# Validation Guide - STEP 1 & STEP 2

This guide helps you validate the implementation of STEP 1 (Database Lab) and STEP 2 (Internal Database).

## Quick Validation

Run the automated validation script:

```bash
./validate.sh
```

This script will:
- ✅ Check Docker is running
- ✅ Start all lab databases (MySQL, PostgreSQL)
- ✅ Verify data population (200k users, 500k orders in MySQL; 50k users, 150k orders in PostgreSQL)
- ✅ Confirm secondary indexes were removed from orders table
- ✅ Validate slow query logging is enabled
- ✅ Start internal database and Redis
- ✅ Check internal database schema (tables, views, extensions)
- ✅ Test Redis connectivity

## Python Environment Validation (Optional)

For local development without Docker, you can validate the Python environment:

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
cd ..
```

### 2. Run Python Validation

```bash
python3 validate_python.py
```

This script will test:
- ✅ Configuration loading from environment variables
- ✅ Database connection via SQLAlchemy
- ✅ Schema validation (tables, views, extensions)
- ✅ Model instantiation
- ✅ CRUD operations (Create, Read, Update, Delete)
- ✅ Model relationships (SlowQueryRaw ↔ AnalysisResult)

## Manual Validation Steps

### STEP 1: Database Lab

#### MySQL Lab

```bash
# 1. Check MySQL is running
docker ps | grep mysql-lab

# 2. Test connection
docker exec mysql-lab mysql -uroot -proot -e "SELECT 1"

# 3. Check data
docker exec mysql-lab mysql -uroot -proot -e "
  SELECT
    'users' as table_name,
    COUNT(*) as row_count
  FROM labdb.users
  UNION ALL
  SELECT
    'orders' as table_name,
    COUNT(*) as row_count
  FROM labdb.orders;
"

# Expected output:
# users:  ~200,000 rows
# orders: ~500,000 rows

# 4. Verify no secondary indexes on orders
docker exec mysql-lab mysql -uroot -proot -e "
  SHOW INDEXES FROM labdb.orders WHERE Key_name != 'PRIMARY';
"

# Expected: Empty result (no secondary indexes)

# 5. Check slow query log is enabled
docker exec mysql-lab mysql -uroot -proot -e "
  SHOW VARIABLES LIKE 'slow_query_log';
  SHOW VARIABLES LIKE 'long_query_time';
"

# Expected:
# slow_query_log: ON
# long_query_time: 0.5
```

#### PostgreSQL Lab

```bash
# 1. Check PostgreSQL is running
docker ps | grep postgres-lab

# 2. Test connection
docker exec postgres-lab psql -U postgres -c "SELECT 1"

# 3. Check data
docker exec postgres-lab psql -U postgres -d labdb -c "
  SELECT 'users' as table_name, COUNT(*) as row_count FROM users
  UNION ALL
  SELECT 'orders' as table_name, COUNT(*) as row_count FROM orders;
"

# Expected output:
# users:  ~50,000 rows
# orders: ~150,000 rows

# 4. Check pg_stat_statements extension
docker exec postgres-lab psql -U postgres -d labdb -c "
  SELECT * FROM pg_extension WHERE extname = 'pg_stat_statements';
"

# Expected: Extension should be present

# 5. Test a slow query
docker exec postgres-lab psql -U postgres -d labdb -c "
  SELECT * FROM orders WHERE product LIKE '%phone%' LIMIT 10;
"

# Should take a few seconds due to no indexes
```

### STEP 2: Internal Database

#### Internal PostgreSQL

```bash
# 1. Check internal-db is running
docker ps | grep ai-analyzer-internal-db

# 2. Test connection
docker exec ai-analyzer-internal-db pg_isready -U ai_core

# 3. List tables
docker exec ai-analyzer-internal-db psql -U ai_core -d ai_core -c "\dt"

# Expected tables:
# - slow_queries_raw
# - db_metadata
# - analysis_result
# - optimization_history
# - schema_version

# 4. List views
docker exec ai-analyzer-internal-db psql -U ai_core -d ai_core -c "\dv"

# Expected views:
# - query_performance_summary
# - impactful_tables

# 5. Check extensions
docker exec ai-analyzer-internal-db psql -U ai_core -d ai_core -c "
  SELECT extname FROM pg_extension WHERE extname IN ('uuid-ossp', 'plpgsql');
"

# Expected: Both extensions present

# 6. Verify schema version
docker exec ai-analyzer-internal-db psql -U ai_core -d ai_core -c "
  SELECT * FROM schema_version;
"

# Expected: version = 1
```

#### Redis

```bash
# 1. Check Redis is running
docker ps | grep ai-analyzer-redis

# 2. Test connection
docker exec ai-analyzer-redis redis-cli ping

# Expected: PONG

# 3. Check Redis info
docker exec ai-analyzer-redis redis-cli INFO server

# 4. Test basic operations
docker exec ai-analyzer-redis redis-cli SET test_key "Hello"
docker exec ai-analyzer-redis redis-cli GET test_key
docker exec ai-analyzer-redis redis-cli DEL test_key

# Expected: OK, "Hello", (integer) 1
```

## Testing Slow Query Generation

### MySQL Slow Queries

```bash
# Install Python dependencies first (if not already done)
pip install mysql-connector-python python-dotenv

# Run the simulator
python3 ai-query-lab/db/mysql/simulate_slow_queries.py

# In another terminal, check the slow log
docker exec mysql-lab mysql -uroot -proot -e "
  SELECT
    start_time,
    query_time,
    LEFT(sql_text, 80) as sql_preview
  FROM mysql.slow_log
  ORDER BY query_time DESC
  LIMIT 10;
"

# Press Ctrl+C to stop the simulator
```

### PostgreSQL Slow Queries

```bash
# Install Python dependencies first (if not already done)
pip install psycopg2-binary python-dotenv

# Run the simulator
python3 ai-query-lab/db/postgres/simulate_slow_queries.py

# In another terminal, check pg_stat_statements
docker exec postgres-lab psql -U postgres -d labdb -c "
  SELECT
    calls,
    total_exec_time / 1000 as total_time_sec,
    mean_exec_time / 1000 as avg_time_sec,
    LEFT(query, 80) as query_preview
  FROM pg_stat_statements
  WHERE query NOT LIKE '%pg_stat_statements%'
  ORDER BY mean_exec_time DESC
  LIMIT 10;
"

# Press Ctrl+C to stop the simulator
```

## Troubleshooting

### Container won't start

```bash
# Check Docker logs
docker logs mysql-lab
docker logs postgres-lab
docker logs ai-analyzer-internal-db
docker logs ai-analyzer-redis

# Check if ports are already in use
netstat -tuln | grep -E '3307|5433|5440|6379'

# Stop and remove all containers
docker compose down -v
cd ai-query-lab && docker compose down -v && cd ..

# Start fresh
cd ai-query-lab && docker compose up -d && cd ..
docker compose up -d
```

### Database not populated

```bash
# For MySQL - check if init.sql was executed
docker exec mysql-lab ls -la /docker-entrypoint-initdb.d/

# If volume data exists, drop it and recreate
docker compose down -v
cd ai-query-lab && docker compose down -v
rm -rf data/

# Restart
cd ai-query-lab && docker compose up -d && cd ..
docker compose up -d
```

### Python connection fails

```bash
# Make sure internal-db is running
docker ps | grep ai-analyzer-internal-db

# Check environment variables
cat .env

# Test connection manually
docker exec ai-analyzer-internal-db psql -U ai_core -d ai_core -c "SELECT 1"

# If connection works in Docker but not from Python, check host
# Use 'localhost' for local Python, 'internal-db' for Docker Python
```

### Slow queries not appearing

```bash
# For MySQL - verify slow_query_log is enabled
docker exec mysql-lab mysql -uroot -proot -e "
  SET GLOBAL slow_query_log = 'ON';
  SET GLOBAL long_query_time = 0.5;
  SET GLOBAL log_output = 'TABLE';
"

# For PostgreSQL - check configuration
docker exec postgres-lab psql -U postgres -c "
  SHOW log_min_duration_statement;
"

# Should be 500 (milliseconds)
```

## Expected Results Summary

After successful validation, you should have:

✅ **STEP 1 - Database Lab**
- MySQL Lab running on port 3307 with 200k users, 500k orders
- PostgreSQL Lab running on port 5433 with 50k users, 150k orders
- No secondary indexes on orders tables (only PRIMARY KEY)
- Slow query logging enabled on both databases
- Simulation scripts functional

✅ **STEP 2 - Internal Database**
- Internal PostgreSQL running on port 5440
- Redis running on port 6379
- Complete schema with 5 tables, 2 views, triggers
- SQLAlchemy models working
- CRUD operations functional
- Model relationships validated

## Next Steps

Once validation passes:

1. **Test slow query collection** - Run simulators for a few minutes and verify logs are populated
2. **Proceed to STEP 3** - Implement Backend FastAPI routes and services
3. **Connect collector** - STEP 4 will read from slow logs and populate internal-db
4. **Implement analyzer** - STEP 5 will generate optimization suggestions

## Support

If validation fails:
1. Check Docker logs for specific errors
2. Verify all ports are available (not already in use)
3. Ensure Docker has enough resources (4GB RAM minimum recommended)
4. Review environment variables in `.env` file
5. Check network connectivity between containers
