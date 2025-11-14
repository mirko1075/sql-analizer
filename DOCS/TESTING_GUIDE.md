# 🧪 AI Query Analyzer - Testing Guide

Complete guide to running performance tests and interpreting results.

## Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Understanding Results](#understanding-results)
- [Finding Tests in Frontend](#finding-tests-in-frontend)
- [Test Categories](#test-categories)
- [Adding Custom Tests](#adding-custom-tests)

---

## Overview

The AI Query Analyzer includes a comprehensive test suite to simulate **30+ common SQL performance problems**. Each test:

- ✅ Executes a deliberately slow query
- ✅ Has a **unique identifier** (e.g., `TEST:SCAN-001`)
- ✅ Is automatically logged by the database
- ✅ Gets collected and analyzed by the backend
- ✅ Appears in the frontend with the test marker
- ✅ Includes expected problems and suggestions

---

## Quick Start

### Prerequisites
Ensure environment is running (see [ENVIRONMENT_GUIDE.md](ENVIRONMENT_GUIDE.md)):
```bash
# Verify services
docker ps | grep -E "mysql-lab|postgres-lab|backend"
```

### Run All Tests
```bash
cd ai-query-lab/tests

# Run all tests (MySQL + PostgreSQL)
./run_tests.sh all

# Wait 5 minutes for collector, then check frontend
open http://localhost:5173
```

### Run Specific Tests
```bash
# MySQL only
./run_tests.sh mysql

# PostgreSQL only
./run_tests.sh postgres

# Specific category
./run_tests.sh mysql SCAN

# Multiple categories
./run_tests.sh postgres INDEX JOIN

# Single test
./run_tests.sh mysql --single SCAN-001
```

---

## Test Structure

### Directory Layout
```
ai-query-lab/tests/
├── mysql/
│   ├── test_categories.py          # Test runner
│   └── categories/
│       ├── _01_full_table_scans.py
│       ├── _02_missing_indexes.py
│       ├── _03_join_problems.py
│       ├── _04_subquery_issues.py
│       ├── _05_aggregation_problems.py
│       ├── _06_function_on_columns.py
│       ├── _07_type_conversions.py
│       └── _08_or_conditions.py
│
├── postgres/
│   └── [same structure as mysql]
│
├── run_tests.sh                    # Master script
└── README_TESTS.md                 # Test catalog
```

### Test Identifier Format

Every test query includes a marker:
```sql
/* TEST:CATEGORY-ID:Description */ SELECT ...
```

**Examples:**
```sql
/* TEST:SCAN-001:Full_Table_Scan_LIKE_Wildcard */
SELECT * FROM orders WHERE product LIKE '%phone%';

/* TEST:INDEX-002:Missing_Index_On_WHERE_Column */
SELECT * FROM orders WHERE status = 'SHIPPED';

/* TEST:JOIN-003:Multiple_LEFT_JOINs_Cascade */
SELECT u.name, o1.product, o2.product
FROM users u
LEFT JOIN orders o1 ON u.id = o1.user_id
LEFT JOIN orders o2 ON u.id = o2.user_id;
```

**Why this format?**
- ✅ Survives SQL fingerprinting
- ✅ Visible in frontend `full_sql` column
- ✅ Searchable and filterable
- ✅ Self-documenting

---

## Running Tests

### Using the Master Script

The master script `run_tests.sh` provides a convenient interface:

```bash
cd ai-query-lab/tests

# All databases, all categories
./run_tests.sh all

# Specific database
./run_tests.sh mysql
./run_tests.sh postgres

# Specific categories
./run_tests.sh mysql SCAN INDEX
./run_tests.sh postgres JOIN SUB

# Single test
./run_tests.sh mysql --single SCAN-001
./run_tests.sh postgres --single JOIN-002
```

### Using Python Directly

For more control, use the Python runners:

```bash
cd ai-query-lab/tests/mysql

# All tests
python3 test_categories.py

# Specific categories
python3 test_categories.py SCAN INDEX

# Single test
python3 test_categories.py --single SCAN-001

# Verbose mode
python3 test_categories.py --verbose
```

### Test Execution Flow

```
1. Test Script Executes Query
   ↓
2. Database Logs Slow Query
   ↓
3. [Wait 5 minutes] or [Force Collection]
   ↓
4. Collector Gathers Slow Queries
   ↓
5. Analyzer Generates Suggestions
   ↓
6. Results Appear in Frontend
```

---

## Understanding Results

### Test Output Example

```
============================================================
MySQL Query Performance Test Suite
============================================================
Database: 127.0.0.1:3307/labdb
Time: 2024-10-31 17:30:00
✓ Connected to MySQL

Category 01: Full Table Scans
Description: Tests that cause database to scan entire tables
Tests: 5 | Severity: HIGH

  ⚠️  SCAN-001: Full_Table_Scan_LIKE_Leading_Wildcard      [2.34s]
  ⚠️  SCAN-002: Full_Table_Scan_LIKE_Double_Wildcard       [1.87s]
  🔴 SCAN-003: Full_Table_Scan_OR_Different_Columns        [3.12s]
  ⚠️  SCAN-004: Full_Table_Scan_NOT_IN_Large_Set           [1.45s]
  ✓  SCAN-005: Full_Table_Scan_No_WHERE_Clause             [0.23s]

============================================================
Test Summary
============================================================
Total tests:      30
Very slow (>2s):  8 (27%)
Slow (>0.5s):     20 (67%)
Fast:             2 (7%)

Top 5 Slowest Queries:
  1. JOIN-005: 4.56s
  2. SCAN-003: 3.12s
  3. AGG-002: 2.89s
  4. SCAN-001: 2.34s
  5. FUNC-001: 2.12s

Next Steps:
  1. Wait 5 minutes for collector to gather slow queries
  2. Or force collection: curl -X POST http://localhost:8000/api/v1/collectors/mysql/collect
  3. Check frontend: http://localhost:5173
  4. Search for 'TEST:' to find test queries
  5. Or search specific test: 'TEST:SCAN-001'
```

### Status Icons
- 🔴 **VERY_SLOW** (>2s): Critical performance issue
- ⚠️  **SLOW** (>0.5s): Performance issue (expected for tests)
- ✓ **OK** (<0.5s): Fast execution
- ✗ **ERROR**: Query failed to execute

---

## Finding Tests in Frontend

### Method 1: Search for All Test Queries

1. Open frontend: http://localhost:5173
2. Go to "Slow Queries" page
3. In search bar, type: **`TEST:`**
4. All test queries will be displayed

### Method 2: Search for Specific Test

1. Open frontend
2. Search for: **`TEST:SCAN-001`**
3. Click on the query to see details

### Method 3: Filter by Category

1. Search for: **`TEST:SCAN`** (all SCAN tests)
2. Search for: **`TEST:INDEX`** (all INDEX tests)
3. Etc.

### What You'll See in Frontend

**Query List View:**
```
Fingerprint: SELECT * FROM orders WHERE product LIKE ? AND status = ?
Database: MySQL
Duration: 2.34s
Last Seen: 2024-10-31 17:30:15
Status: ANALYZED
```

**Query Detail View:**
```
Full SQL (with marker):
/* TEST:SCAN-001:Full_Table_Scan_LIKE_Wildcard */
SELECT * FROM orders WHERE product LIKE '%phone%' AND status = 'PAID'

Analysis:
✗ Problem: Full table scan detected
✗ Root Cause: LIKE with leading wildcard prevents index usage
📝 Suggestions:
  1. [HIGH] Consider full-text index or restructure query
  2. [MEDIUM] Add index on product column
  3. [LOW] Cache frequently accessed patterns

Metrics:
- Rows Examined: 500,000
- Rows Returned: 1,234
- Efficiency Ratio: 0.25% (very inefficient)
- Estimated Speedup: 10-100x with optimization
```

---

## Test Categories

### Overview of Categories

| Category | Code | Tests | Severity | Description |
|----------|------|-------|----------|-------------|
| **Full Table Scans** | SCAN | 5 | HIGH | Queries that scan entire tables |
| **Missing Indexes** | INDEX | 5 | HIGH | Missing or inefficient indexes |
| **JOIN Problems** | JOIN | 5 | HIGH | Inefficient JOIN operations |
| **Subquery Issues** | SUB | 5 | MEDIUM | Problematic subquery patterns |
| **Aggregation Problems** | AGG | 5 | MEDIUM | Inefficient aggregations |
| **Function on Columns** | FUNC | 5 | MEDIUM | Functions preventing index usage |
| **Type Conversions** | TYPE | 4 | MEDIUM | Implicit type conversion issues |
| **OR Conditions** | OR | 4 | MEDIUM | OR conditions invalidating indexes |

### Category Details

#### SCAN: Full Table Scans
Tests where database must scan entire table:
- `SCAN-001`: LIKE with leading wildcard
- `SCAN-002`: LIKE with double wildcard
- `SCAN-003`: OR on different columns
- `SCAN-004`: NOT IN with large set
- `SCAN-005`: No WHERE clause

#### INDEX: Missing Indexes
Tests where missing indexes cause slow queries:
- `INDEX-001`: JOIN without foreign key index
- `INDEX-002`: WHERE without index
- `INDEX-003`: ORDER BY without index
- `INDEX-004`: GROUP BY without covering index
- `INDEX-005`: Composite index wrong order

#### JOIN: JOIN Problems
Tests with inefficient JOIN operations:
- `JOIN-001`: JOIN without indexes
- `JOIN-002`: Cartesian product (missing ON)
- `JOIN-003`: Multiple LEFT JOINs cascade
- `JOIN-004`: Self-join inefficient
- `JOIN-005`: JOIN with complex aggregation

#### SUB: Subquery Issues
Tests with problematic subqueries:
- `SUB-001`: Subquery in SELECT (N+1)
- `SUB-002`: Correlated subquery in WHERE
- `SUB-003`: IN with large subquery
- `SUB-004`: NOT IN vs NOT EXISTS
- `SUB-005`: Subquery instead of JOIN

#### AGG: Aggregation Problems
Tests with inefficient aggregations:
- `AGG-001`: COUNT(*) without WHERE
- `AGG-002`: GROUP BY without index
- `AGG-003`: HAVING instead of WHERE
- `AGG-004`: DISTINCT unnecessary
- `AGG-005`: Multiple aggregations

#### FUNC: Function on Columns
Tests where functions prevent index usage:
- `FUNC-001`: YEAR/EXTRACT on date column
- `FUNC-002`: UPPER on string column
- `FUNC-003`: Math operation on indexed column
- `FUNC-004`: CONCAT in WHERE
- `FUNC-005`: DATE_FORMAT/TO_CHAR in WHERE

#### TYPE: Type Conversions
Tests with implicit type conversions:
- `TYPE-001`: String comparison with number
- `TYPE-002`: Type mismatch in JOIN
- `TYPE-003`: Date as string comparison
- `TYPE-004`: LIKE on numeric column

#### OR: OR Conditions
Tests where OR conditions hurt performance:
- `OR-001`: OR on different columns
- `OR-002`: OR instead of UNION
- `OR-003`: OR instead of IN
- `OR-004`: OR with function calls

For complete test catalog, see [tests/README_TESTS.md](ai-query-lab/tests/README_TESTS.md)

---

## Forcing Collection and Analysis

By default, the collector runs every **5 minutes**. To see results immediately:

```bash
# Force MySQL collection
curl -X POST http://localhost:8000/api/v1/collectors/mysql/collect

# Force PostgreSQL collection
curl -X POST http://localhost:8000/api/v1/collectors/postgres/collect

# Force analysis of collected queries
curl -X POST http://localhost:8000/api/v1/analyzer/analyze

# Check results
curl http://localhost:8000/api/v1/slow-queries | jq
```

---

## Adding Custom Tests

### Step 1: Add Test Case to Category

Edit a category file (e.g., `mysql/categories/_01_full_table_scans.py`):

```python
TEST_CASES = [
    # ... existing tests ...
    {
        'id': 'SCAN-006',
        'name': 'My_Custom_Test',
        'description': 'Description of what this tests',
        'sql': "/* TEST:SCAN-006:My_Custom_Test */ SELECT * FROM orders WHERE custom_condition",
        'expected_problem': 'Expected problem description',
        'expected_suggestion': 'Expected optimization suggestion'
    }
]
```

### Step 2: Run Your Test

```bash
cd ai-query-lab/tests
./run_tests.sh mysql --single SCAN-006
```

### Step 3: Verify in Frontend

Search for `TEST:SCAN-006` in the frontend.

---

## Troubleshooting

### Tests Run But Don't Appear in Frontend

**Possible causes:**
1. Collector hasn't run yet
2. Queries weren't slow enough to be logged
3. Test query syntax error

**Solutions:**
```bash
# 1. Force collection
curl -X POST http://localhost:8000/api/v1/collectors/mysql/collect

# 2. Check if query was logged in database
docker exec -it mysql-lab mysql -uroot -proot -e "SELECT COUNT(*) FROM mysql.slow_log WHERE sql_text LIKE '%TEST:%'"

# 3. Run test in verbose mode
cd ai-query-lab/tests/mysql
python3 test_categories.py --single SCAN-001 --verbose
```

### Python Import Errors

```bash
# Install dependencies
pip install mysql-connector-python psycopg2-binary python-dotenv

# Or use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Database Connection Errors

```bash
# Check lab databases are running
docker ps | grep -E "mysql-lab|postgres-lab"

# Restart if needed
cd ai-query-lab
docker compose restart mysql-lab postgres-lab
```

---

## Best Practices

### Running Tests

1. **Start with category tests** before running all tests
2. **Force collection** after tests for immediate results
3. **Document** any custom tests you add
4. **Use descriptive markers** in TEST:ID format

### Analyzing Results

1. **Focus on VERY_SLOW** (>2s) tests first
2. **Compare** expected vs actual analysis
3. **Verify** suggested optimizations are correct
4. **Track** which patterns the AI analyzer handles well

### Custom Testing

1. **Follow naming convention**: `CATEGORY-###`
2. **Include marker** in SQL: `/* TEST:ID:Description */`
3. **Document** in category file
4. **Test** both MySQL and PostgreSQL if applicable

---

## Next Steps

- 📊 Explore test results in frontend: http://localhost:5173
- 📚 Read test catalog: [tests/README_TESTS.md](ai-query-lab/tests/README_TESTS.md)
- ⚙️  Customize tests for your use case
- 🔍 Analyze AI suggestions accuracy
- 📈 Track improvements over time

---

## Support

- 🐛 Report test issues: [GitHub Issues](https://github.com/your-repo/issues)
- 📚 More documentation: [README.md](README.md) | [ENVIRONMENT_GUIDE.md](ENVIRONMENT_GUIDE.md)
- 💡 Suggest new test cases: Create an issue with the `test-suggestion` label
