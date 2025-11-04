# 🧪 DBPower Test Suite - Quick Reference

## 🚀 Quick Start (One Command)

```bash
cd tests
./quick-start.sh
```

This will:
1. Create test database (dbpower_test)
2. Generate ~1.1M rows of test data
3. Run all 12 performance tests
4. Trigger DBPower collection

**Time**: ~15 minutes total

---

## 📋 Test Categories

| # | Category | Tests | Issues Detected |
|---|----------|-------|-----------------|
| 1 | Missing Indexes | 01-03 | Full table scans, slow lookups |
| 2 | Join Performance | 04-05 | N+1 queries, missing FK indexes |
| 3 | Subqueries | 06 | Correlated subqueries |
| 4 | Large Tables | 07 | Partitioning needs |
| 5 | Text Search | 08 | LIKE without FULLTEXT |
| 6 | SELECT * | 09 | Unnecessary column fetching |
| 7 | Locking | 10 | Row-level contention |
| 8 | Sorting | 11 | ORDER BY without index |
| 9 | Grouping | 12 | GROUP BY without index |

---

## 🎯 Individual Test Commands

```bash
# Setup (first time only)
./setup-test-env.sh

# Run specific test
./run-test.sh 01    # Missing index on email
./run-test.sh 05    # Join without FK index
./run-test.sh 07    # Partitioning needs

# Run all tests
./run-all-tests.sh

# Collect results
curl -X POST http://localhost:8000/api/v1/analyze/collect

# View queries
curl http://localhost:8000/api/v1/slow-queries | jq
```

---

## 📊 Expected Database Size

```
users:             50,000 rows
products:           5,000 rows  
orders:           100,000 rows
order_items:      ~300,000 rows
product_reviews:  150,000 rows
analytics_events: 500,000 rows
product_inventory: 5,000 rows
────────────────────────────────
Total:            ~1.1M rows
```

---

## 🔧 Configuration

Edit scripts if your MySQL settings differ:

```bash
MYSQL_HOST="127.0.0.1"
MYSQL_PORT="3306"
MYSQL_USER="root"
MYSQL_PASSWORD="admin"
```

---

## 🧹 Cleanup

```bash
# Remove test database
mysql -h 127.0.0.1 -u root -padmin -e "DROP DATABASE dbpower_test;"

# Clear DBPower collected data
docker exec dbpower-backend python scripts/quick_cleanup.py
```

---

## 🎓 Learn More

- Full documentation: `tests/README.md`
- Query status management: `backend/docs/QUERY_STATUS_MANAGEMENT.md`
- Test SQL files: `tests/*.sql` (with detailed comments)
