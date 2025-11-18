# MySQL Slow Query Lab Database

## Overview

This is an intentionally **poorly optimized** MySQL database designed for testing slow query detection and analysis tools. It simulates a real-world e-commerce application with realistic data volumes but with missing or incorrect indexes that cause performance issues.

## Purpose

- **Test slow query detection systems**
- **Demonstrate query optimization opportunities**
- **Train AI models on realistic slow query patterns**
- **Educational tool for database performance tuning**

## Database Schema

### E-commerce Database (11 tables)

```
ecommerce_lab/
├── users (100,000 rows)
│   ├── ❌ Missing index on email
│   ├── ❌ Missing index on country
│   └── ❌ Missing index on created_at
├── products (50,000 rows)
│   ├── ❌ Missing composite index (category_id, price)
│   └── ❌ Missing index on category_id
├── orders (500,000 rows)
│   ├── ⚠️  Wrong index: only user_id (should be user_id, order_date)
│   ├── ❌ Missing index on order_date
│   └── ❌ Missing index on status
├── order_items (2,000,000 rows)
│   └── ❌ Missing index on product_id
├── reviews (300,000 rows)
│   ├── ⚠️  Wrong index: only product_id (should be product_id, created_at)
│   └── ❌ Missing index on rating
├── inventory_log (1,000,000 rows)
│   └── ❌ NO indexes except primary key
├── customer_sessions (200,000 rows)
│   ├── ❌ Missing index on user_id
│   └── ❌ Missing index on session_start
├── search_log (500,000 rows)
│   └── ❌ NO indexes for analytics
├── wishlists (100,000+ rows)
│   ├── ⚠️  Wrong index: only user_id
│   └── ❌ Missing composite unique index (user_id, product_id)
├── cart_items (50,000+ rows)
│   └── ❌ Missing index on product_id
└── promotions (1,000+ rows)
    └── ❌ Missing index on date ranges
```

## Data Volumes

| Table | Rows | Purpose |
|-------|------|---------|
| `users` | 100,000 | Customer accounts |
| `products` | 50,000 | Product catalog |
| `orders` | 500,000 | Order history |
| `order_items` | 2,000,000+ | Line items (avg 4 per order) |
| `reviews` | 300,000 | Product reviews |
| `inventory_log` | 1,000,000 | Inventory transactions |
| `customer_sessions` | 200,000 | User sessions |
| `search_log` | 500,000 | Search queries |
| `wishlists` | Variable | Saved items |
| `cart_items` | Variable | Shopping carts |
| `promotions` | 1,000+ | Discount codes |

**Total Rows: ~4.7 million**

## Quick Start

### 1. Start the Database

```bash
cd lab-database
docker compose up -d
```

**Wait for initialization** (~5-10 minutes):
- Schema creation
- Data generation (stored procedures)
- Index creation (minimal, intentionally)

### 2. Verify Database is Ready

```bash
# Check container status
docker compose ps

# Check logs
docker compose logs -f mysql-lab

# Wait for: "ready for connections" message
```

### 3. Connect to Database

```bash
# Using mysql client
mysql -h 127.0.0.1 -P 3307 -u root -proot ecommerce_lab

# Using Docker exec
docker exec -it mysql-lab-slowquery mysql -uroot -proot ecommerce_lab
```

### 4. Verify Data Loaded

```sql
-- Check row counts
SELECT 'users' as table_name, COUNT(*) as rows FROM users
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'reviews', COUNT(*) FROM reviews
UNION ALL SELECT 'inventory_log', COUNT(*) FROM inventory_log;

-- Expected output:
-- users:          100,000
-- products:        50,000
-- orders:         500,000
-- order_items:  2,000,000+
-- reviews:        300,000
-- inventory_log: 1,000,000
```

### 5. Run Slow Query Tests

```bash
cd scripts
chmod +x run-slow-queries.sh
./run-slow-queries.sh
```

This will execute **27 different slow queries** covering:
- Full table scans
- Missing indexes
- Inefficient JOINs
- Subquery problems
- Aggregation issues
- LIKE queries
- Sorting issues
- And more...

## Slow Query Categories

### Category 1: Full Table Scans (4 queries)
- Email lookup without index
- Country filter without index
- Product category scan
- Date range queries

### Category 2: Missing Composite Indexes (3 queries)
- User order history (wrong index)
- Product category with price sorting
- Product reviews with date sorting

### Category 3: Inefficient JOINs (3 queries)
- Order with items (product lookup)
- User with recent orders
- Product performance report

### Category 4: Subquery Problems (3 queries)
- Correlated subqueries
- IN subquery without index
- NOT EXISTS queries

### Category 5: Aggregation Issues (3 queries)
- Large aggregations without index
- Complex multi-table aggregations
- Daily statistics

### Category 6-12: Additional Issues
- LIKE queries with leading wildcards
- Sorting large result sets
- DISTINCT on unindexed columns
- OR conditions preventing index usage
- Functions on indexed columns
- GROUP BY on non-indexed columns

## Performance Issues Summary

### 🔴 Critical Issues (High Impact)

1. **inventory_log** - NO indexes at all (1M rows)
   - All queries cause full table scans
   - Expected query time: 5-20 seconds

2. **search_log** - NO analytics indexes (500K rows)
   - Search analytics extremely slow
   - Expected query time: 3-15 seconds

3. **order_items.product_id** - Missing index (2M rows)
   - Product sales reports very slow
   - Expected query time: 5-15 seconds

### 🟡 High Impact Issues

4. **users.email** - Missing index (100K rows)
   - Login queries slow: 500ms - 2s

5. **orders** - Wrong index structure (500K rows)
   - User order history slow: 1-3s

6. **products.category_id** - Missing composite index (50K rows)
   - Product browsing slow: 600ms - 2s

### 🟢 Medium Impact Issues

7. **reviews** - Wrong index for common queries
8. **customer_sessions** - Missing user_id index
9. **wishlists** - Missing composite unique index
10. **promotions** - Missing date range indexes

## Slow Query Log

### View Recent Slow Queries

```sql
-- Check slow query log status
SHOW VARIABLES LIKE 'slow_query%';
SHOW VARIABLES LIKE 'long_query_time';

-- View slow queries from mysql.slow_log table
SELECT
    start_time,
    query_time,
    lock_time,
    rows_sent,
    rows_examined,
    sql_text
FROM mysql.slow_log
ORDER BY start_time DESC
LIMIT 10;

-- Count slow queries by type
SELECT
    LEFT(sql_text, 50) as query_start,
    COUNT(*) as count,
    AVG(query_time) as avg_time,
    MAX(query_time) as max_time
FROM mysql.slow_log
GROUP BY LEFT(sql_text, 50)
ORDER BY count DESC;
```

### View Slow Query Log File

```bash
# Using docker exec
docker exec mysql-lab-slowquery tail -f /var/log/mysql/slow-query.log

# Copy log file to host
docker cp mysql-lab-slowquery:/var/log/mysql/slow-query.log ./slow-query.log
```

## Testing with AI Query Analyzer

### 1. Ensure Lab DB is Running

```bash
docker compose ps
# mysql-lab should be "Up" and "healthy"
```

### 2. Configure Backend Collector

The AI Query Analyzer backend should connect to:
- **Host:** `127.0.0.1` or `host.docker.internal` (from Docker)
- **Port:** `3307`
- **User:** `root`
- **Password:** `root`
- **Database:** `ecommerce_lab`

### 3. Run Slow Queries

```bash
cd scripts
./run-slow-queries.sh
```

### 4. Trigger Collection

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/collectors/mysql/collect

# Or wait for scheduled collection (every 5 minutes)
```

### 5. View Results

```bash
# Check analyzer status
curl http://localhost:8000/api/v1/analyzer/status

# View collected queries
curl http://localhost:8000/api/v1/slow-queries

# Or use the frontend dashboard
open http://localhost:3000
```

## Expected Analysis Results

### Query SLOW-001: Email Lookup

```
Problem: Full table scan detected
Root Cause: Query performs full table scan (access_type: ALL)
Improvement Level: HIGH
Estimated Speedup: 10-100x
Suggestions:
  - CREATE INDEX idx_email ON users(email);
```

### Query SLOW-003: Category Browse

```
Problem: Missing index on filtering column
Root Cause: No index on category_id, requires table scan
Improvement Level: HIGH
Estimated Speedup: 10-100x
Suggestions:
  - CREATE INDEX idx_category_price ON products(category_id, price);
```

### Query SLOW-008: Order with Items

```
Problem: Inefficient JOIN
Root Cause: Missing index on order_items.product_id
Improvement Level: HIGH
Estimated Speedup: 5-20x
Suggestions:
  - CREATE INDEX idx_product ON order_items(product_id);
```

## Optimization Guide

### Fix Critical Issues

```sql
-- Fix inventory_log (CRITICAL)
CREATE INDEX idx_product_date ON inventory_log(product_id, created_at);
CREATE INDEX idx_change_type ON inventory_log(change_type);

-- Fix search_log (CRITICAL)
CREATE INDEX idx_search_term ON search_log(search_term, searched_at);
CREATE INDEX idx_user_searched ON search_log(user_id, searched_at);

-- Fix order_items.product_id (CRITICAL)
CREATE INDEX idx_product ON order_items(product_id);
CREATE INDEX idx_product_created ON order_items(product_id, created_at);
```

### Fix High Impact Issues

```sql
-- Fix users table
CREATE INDEX idx_email ON users(email);
CREATE INDEX idx_country ON users(country);
CREATE INDEX idx_created_at ON users(created_at);
CREATE INDEX idx_total_spent ON users(total_spent);

-- Fix orders table
CREATE INDEX idx_user_date ON orders(user_id, order_date);
CREATE INDEX idx_order_date ON orders(order_date);
CREATE INDEX idx_status ON orders(status);

-- Fix products table
CREATE INDEX idx_category_price ON products(category_id, price);
CREATE INDEX idx_category ON products(category_id);
```

### Fix Medium Impact Issues

```sql
-- Fix reviews table
DROP INDEX idx_product ON reviews;
CREATE INDEX idx_product_date ON reviews(product_id, created_at);
CREATE INDEX idx_rating ON reviews(rating);
CREATE INDEX idx_user ON reviews(user_id);

-- Fix customer_sessions
CREATE INDEX idx_user ON customer_sessions(user_id);
CREATE INDEX idx_session_start ON customer_sessions(session_start);

-- Fix wishlists
DROP INDEX idx_user ON wishlists;
CREATE UNIQUE INDEX idx_user_product ON wishlists(user_id, product_id);

-- Fix promotions
CREATE INDEX idx_dates ON promotions(start_date, end_date);
CREATE INDEX idx_active ON promotions(is_active, start_date, end_date);
```

## Performance Comparison

### Before Optimization

| Query | Category | Duration | Issue |
|-------|----------|----------|-------|
| SLOW-001 | Email lookup | 1-2s | Full table scan |
| SLOW-003 | Category browse | 600ms-2s | Missing index |
| SLOW-008 | Order items | 3-8s | Missing JOIN index |
| SLOW-014 | Inventory stats | 8-25s | No indexes |
| SLOW-011 | User stats | 10-30s | Correlated subquery |

### After Optimization

| Query | Category | Duration | Improvement |
|-------|----------|----------|-------------|
| SLOW-001 | Email lookup | 5-10ms | 100-400x faster |
| SLOW-003 | Category browse | 10-20ms | 30-200x faster |
| SLOW-008 | Order items | 50-200ms | 15-160x faster |
| SLOW-014 | Inventory stats | 100-500ms | 16-250x faster |
| SLOW-011 | User stats | 200-800ms | 12-150x faster |

## Maintenance

### Reset Database

```bash
# Stop and remove container
docker compose down -v

# Start fresh (will re-initialize)
docker compose up -d
```

### View Logs

```bash
# Container logs
docker compose logs -f mysql-lab

# Slow query log
docker exec mysql-lab-slowquery tail -f /var/log/mysql/slow-query.log
```

### Backup Data

```bash
# Dump database
docker exec mysql-lab-slowquery mysqldump -uroot -proot ecommerce_lab > backup.sql

# Dump slow query log
docker cp mysql-lab-slowquery:/var/log/mysql/slow-query.log ./backup-slowlog.log
```

## Troubleshooting

### Database not starting

```bash
# Check logs
docker compose logs mysql-lab

# Common issues:
# - Port 3307 already in use
# - Insufficient memory (need 1GB+ free)
# - Disk space (need 5GB+ free)
```

### Data not loading

```bash
# Check if initialization completed
docker compose logs mysql-lab | grep "ready for connections"

# If stuck, restart
docker compose restart mysql-lab

# Force reinitialize
docker compose down -v
docker compose up -d
```

### Slow queries not appearing in log

```sql
-- Verify slow query log is enabled
SHOW VARIABLES LIKE 'slow_query_log';
-- Should show: ON

-- Check threshold
SHOW VARIABLES LIKE 'long_query_time';
-- Should show: 0.500000

-- Enable if needed
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 0.5;
```

## Files Structure

```
lab-database/
├── docker-compose.yml          # Docker setup
├── README.md                   # This file
├── mysql/
│   ├── init-schema.sql         # Database schema with poor indexes
│   └── load-data.sql           # Data generation (4.7M rows)
└── scripts/
    ├── slow-queries.sql        # 27 test queries (SQL)
    └── run-slow-queries.sh     # Query runner script
```

## Use Cases

### 1. Testing Slow Query Detection
- Run slow queries
- Verify they appear in slow_log
- Test collector captures them

### 2. Testing Query Analysis
- Collect slow queries
- Run analyzer
- Verify analysis identifies issues correctly

### 3. Training AI Models
- Generate diverse slow query patterns
- Capture EXPLAIN plans
- Use as training data for ML models

### 4. Education & Demos
- Demonstrate query optimization
- Show before/after performance
- Teach indexing strategies

## License

This is a test/demo database. All data is randomly generated.

## Support

For issues or questions, refer to the main AI Query Analyzer documentation.

---

**Created:** 2025-11-13
**Version:** 1.0.0
**Purpose:** Slow Query Testing Lab Environment
