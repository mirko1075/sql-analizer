# DBPower - Troubleshooting Guide

## 🔍 Problem: No Slow Queries Being Collected

### Symptoms
- Dashboard shows 0 queries
- Collection API returns `"collected": 0`
- MySQL has slow queries but DBPower doesn't see them

### Root Cause
MySQL is logging to **FILE** instead of **TABLE**.

### Solution

**Step 1: Check current configuration**
```bash
mysql -h 127.0.0.1 -P 3306 -u root -padmin -e "SHOW VARIABLES LIKE 'log_output';"
```

If output shows `FILE`, you need to change it to `TABLE`.

**Step 2: Apply configuration**
```bash
mysql -h 127.0.0.1 -P 3306 -u root -padmin < backend/scripts/configure_mysql_slow_log.sql
```

Or manually:
```sql
SET GLOBAL log_output = 'TABLE';
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 0.3;
```

**Step 3: Verify**
```bash
mysql -h 127.0.0.1 -P 3306 -u root -padmin -e "SHOW VARIABLES LIKE 'log_output';"
```

Should show: `TABLE`

**Step 4: Test with a slow query**
```bash
mysql -h 127.0.0.1 -P 3306 -u root -padmin -e "SELECT SLEEP(0.5);"
```

**Step 5: Collect**
```bash
curl -X POST http://localhost:8000/api/v1/analyze/collect
```

Should return: `"collected": 1`

---

## ⚙️ Make Configuration Persistent

**For Docker MySQL:**

Add to your `docker-compose.yml`:
```yaml
mysql-lab:
  image: mysql:8.0
  command: >
    --slow_query_log=1
    --log_output=TABLE
    --long_query_time=0.3
    --log_queries_not_using_indexes=ON
```

**For MySQL Config File:**

Edit `/etc/mysql/my.cnf`:
```ini
[mysqld]
slow_query_log = 1
log_output = TABLE
long_query_time = 0.3
log_queries_not_using_indexes = ON
```

Then restart MySQL:
```bash
sudo systemctl restart mysql
```

---

## 🔍 Problem: Queries Collected But Not Visible

### Check if dbpower_monitor is filtering them out

```bash
mysql -h 127.0.0.1 -P 3306 -u root -padmin -e \
  "SELECT user_host, COUNT(*) FROM mysql.slow_log GROUP BY user_host;"
```

If you see `dbpower_monitor@%`, those queries are correctly filtered out.

---

## 🔍 Problem: Collection Returns 0 Even With Slow Queries

### Check timestamp filtering

DBPower only collects queries **newer** than the last collected one.

**Check last collected timestamp:**
```bash
docker exec dbpower-backend python -c \
  "from db.models import SlowQuery, get_db; \
   db = next(get_db()); \
   lq = db.query(SlowQuery).order_by(SlowQuery.start_time.desc()).first(); \
   print(f'Last: {lq.start_time if lq else None}')"
```

**Check MySQL slow_log:**
```bash
mysql -h 127.0.0.1 -P 3306 -u root -padmin -e \
  "SELECT MAX(start_time) FROM mysql.slow_log;"
```

If MySQL timestamp is older, no new queries will be collected.

**Solution:** Execute a new slow query or clean the database:
```bash
docker exec dbpower-backend python scripts/quick_cleanup.py
```

---

## 🔍 Problem: Collection Fails with Error

### Check MySQL connectivity

```bash
mysql -h 127.0.0.1 -P 3306 -u root -padmin -e "SELECT 1;"
```

### Check backend logs

```bash
docker compose logs backend --tail 50
```

Look for errors like:
- `Access denied`
- `Unknown MySQL server host`
- `Connection refused`

### Verify .env configuration

```bash
cat .env | grep MYSQL
```

Should show:
```
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=admin
```

---

## 🔍 Problem: Analysis Fails

### Check if query exists

```bash
curl http://localhost:8000/api/v1/slow-queries?limit=10 | jq '.queries[] | {id, sql_text}'
```

### Try analyzing a specific query

```bash
curl -X POST http://localhost:8000/api/v1/analyze/1
```

### Check analyzer logs

```bash
docker compose logs backend | grep analyzer
```

---

## 🔍 Problem: Frontend Shows Errors

### Check API connectivity

```bash
curl http://localhost:8000/health
```

Should return:
```json
{"status": "healthy", ...}
```

### Check CORS

Frontend at `http://localhost:3000` should be able to call backend at `http://localhost:8000`.

Since both use `network_mode: host`, this should work automatically.

### Check browser console

Open Developer Tools (F12) and look for:
- Network errors (404, 500)
- CORS errors
- JavaScript errors

---

## 📊 Useful Diagnostic Commands

**Check system status:**
```bash
curl http://localhost:8000/api/v1/stats | jq
```

**Check collector status:**
```bash
curl http://localhost:8000/api/v1/collectors/status | jq
```

**Check analyzer status:**
```bash
curl http://localhost:8000/api/v1/analyzer/status | jq
```

**View recent slow queries:**
```bash
curl "http://localhost:8000/api/v1/slow-queries?limit=5" | jq
```

**Check Docker containers:**
```bash
docker compose ps
```

**Check MySQL slow_log table:**
```bash
mysql -h 127.0.0.1 -P 3306 -u root -padmin -e \
  "SELECT COUNT(*), MAX(start_time) FROM mysql.slow_log;"
```
