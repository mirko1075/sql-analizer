# DBPower Test Suite

Comprehensive SQL performance testing suite to identify common database issues.

## 📋 Test Categories

### 1. **Missing Indexes** (Tests 01-03)
- Email lookup without index
- Country filtering full table scan
- Price range queries

### 2. **Join Performance** (Tests 04-05)
- N+1 query problems
- Joins without foreign key indexes

### 3. **Query Optimization** (Tests 06, 09)
- Correlated subqueries
- SELECT * inefficiency

### 4. **Large Data** (Tests 07, 12)
- Partitioning needs
- Group by without indexes

### 5. **Text Search** (Test 08)
- LIKE queries without FULLTEXT index

### 6. **Sorting** (Test 11)
- ORDER BY without index

### 7. **Concurrency** (Test 10)
- Row-level locking
- Lock contention

---

## 🚀 Quick Start

### One-command setup and run:
```bash
chmod +x *.sh
./quick-start.sh
```

---

## 📖 Step-by-Step Usage

### Step 1: Setup Test Environment
```bash
chmod +x setup-test-env.sh
./setup-test-env.sh
```

This will:
- Create `dbpower_test` database
- Generate ~700K rows of test data
- Takes 5-10 minutes

### Step 2: Run Tests

**Run all tests:**
```bash
chmod +x run-all-tests.sh
./run-all-tests.sh
```

**Run specific test:**
```bash
chmod +x run-test.sh
./run-test.sh 01  # Missing index on email
./run-test.sh 05  # Join without index
./run-test.sh 07  # Partitioning needs
```

### Step 3: Trigger Collection
```bash
curl -X POST http://localhost:8000/api/v1/analyze/collect
```

### Step 4: View Results
```bash
# Via API
curl http://localhost:8000/api/v1/slow-queries | jq

# Via UI
open http://localhost:3000
```

---

## 📁 Test Files

| Test | File | Issue | Fix |
|------|------|-------|-----|
| 01 | `01-missing-index-email.sql` | No index on email | `CREATE INDEX idx_email ON users(email)` |
| 02 | `02-full-table-scan-country.sql` | No index on country | `CREATE INDEX idx_country ON users(country)` |
| 03 | `03-range-query-no-index.sql` | Price range without index | `CREATE INDEX idx_price ON products(price)` |
| 04 | `04-n-plus-one-problem.sql` | Multiple queries per order | Use JOINs |
| 05 | `05-join-without-index.sql` | FK without index | Add FK indexes |
| 06 | `06-correlated-subquery.sql` | Correlated subquery | Use JOINs/window functions |
| 07 | `07-large-table-partitioning.sql` | Large table scans | Partition by date |
| 08 | `08-text-search-no-fulltext.sql` | LIKE with wildcards | Use FULLTEXT index |
| 09 | `09-select-star-inefficiency.sql` | SELECT * overhead | Select specific columns |
| 10 | `10-locking-contention.sql` | Lock contention | Optimize transactions |
| 11 | `11-order-by-no-index.sql` | Sort without index | Index ORDER BY columns |
| 12 | `12-group-by-no-index.sql` | Group without index | Index GROUP BY columns |

---

## 🎯 Expected Results

After running tests, DBPower should detect:

- ✅ Missing indexes on frequently queried columns
- ✅ Full table scans on large tables
- ✅ Inefficient join conditions
- ✅ Correlated subqueries that can be optimized
- ✅ Need for table partitioning
- ✅ Lock contention and blocking queries

---

## 🛠️ Configuration

Edit test scripts if your MySQL credentials differ:

```bash
MYSQL_HOST="127.0.0.1"
MYSQL_PORT="3306"
MYSQL_USER="root"
MYSQL_PASSWORD="admin"
```

---

## 📊 Test Data Size

| Table | Rows | Purpose |
|-------|------|---------|
| users | 50,000 | Index testing |
| products | 5,000 | Range queries |
| orders | 100,000 | Join testing |
| order_items | ~300,000 | N+1 problems |
| product_reviews | 150,000 | FK index testing |
| analytics_events | 500,000 | Partitioning needs |
| product_inventory | 5,000 | Lock contention |

**Total: ~1.1M rows**

---

## 🧹 Cleanup

To remove test database:
```bash
mysql -h 127.0.0.1 -u root -padmin -e "DROP DATABASE IF EXISTS dbpower_test;"
```

To clean DBPower collected data:
```bash
docker exec dbpower-backend python scripts/quick_cleanup.py
```

---

## 🔍 Troubleshooting

### Queries not appearing in slow log?

Check MySQL slow query log settings:
```sql
SHOW VARIABLES LIKE '%slow%';
SHOW VARIABLES LIKE 'log_output';
```

Ensure:
- `slow_query_log = ON`
- `log_output = TABLE`
- `long_query_time = 0.3` (or lower)

### No data generated?

Check Python dependencies:
```bash
pip3 install mysql-connector-python
```

### Permission denied on scripts?

Make executable:
```bash
chmod +x *.sh
```

---

## 📈 Next Steps

1. **Analyze queries** - Use DBPower UI to see AI suggestions
2. **Apply fixes** - Create recommended indexes
3. **Re-run tests** - Verify performance improvements
4. **Compare results** - Check query time improvements

---

## 🎓 Learning Resources

Each test file includes:
- Problem description
- Expected issue
- Recommended fix
- SQL examples

Read the comments in each `.sql` file for detailed explanations.
