# DBPower - Database Management Scripts

## 📁 Scripts Overview

### 1. `cleanup_database.py` - Interactive Cleanup

Full-featured cleanup script with interactive prompts.

**Usage:**
```bash
docker exec dbpower-backend python scripts/cleanup_database.py
```

**Options:**
- Option 1: Clean all data (keeps table structure)
- Option 2: Reset database (drop and recreate tables)
- Option 3: Exit

### 2. `quick_cleanup.py` - Fast Cleanup

Quick cleanup without prompts. **Use with caution!**

**Usage:**
```bash
docker exec dbpower-backend python scripts/quick_cleanup.py
```

Deletes all slow queries and analysis results immediately.

### 3. `create_dbpower_user.sql` - Create Monitoring User

SQL script to create the dedicated `dbpower_monitor` MySQL user.

**Usage:**
```bash
mysql -h 127.0.0.1 -P 3306 -u root -padmin < backend/scripts/create_dbpower_user.sql
```

**What it does:**
- Creates `dbpower_monitor` user
- Grants SELECT on all databases
- Grants PROCESS and SHOW VIEW privileges
- Grants access to `performance_schema` and `mysql.slow_log`

**Important:** Queries from this user are **automatically excluded** from collection!

### 4. `configure_mysql_slow_log.sql` - Configure Slow Query Log

**⚠️ CRITICAL:** MySQL must log to TABLE, not FILE!

**Usage:**
```bash
mysql -h 127.0.0.1 -P 3306 -u root -padmin < backend/scripts/configure_mysql_slow_log.sql
```

**What it does:**
- Sets `log_output = TABLE` (required for DBPower)
- Enables slow query log
- Sets threshold to 0.3 seconds
- Enables logging queries without indexes

**Why this is needed:** DBPower reads from `mysql.slow_log` table, not from log files.

---

## 🔧 Configuration

### Environment Variables (.env)

```properties
# DBPower Monitoring User
DBPOWER_USER=dbpower_monitor
DBPOWER_PASSWORD=dbpower_secure_pass
```

### How Query Filtering Works

The collector automatically filters out queries from the monitoring user:

```sql
-- Collector query
SELECT * FROM mysql.slow_log
WHERE start_time > %s
  AND user_host NOT LIKE 'dbpower_monitor@%'  -- ⬅️ Filters out DBPower queries
```

This prevents DBPower's own analysis queries (EXPLAIN, SHOW INDEX, etc.) from appearing in the slow query list.

---

## 🚀 Quick Start Guide

### First Time Setup

1. **Create the monitoring user:**
   ```bash
   mysql -h 127.0.0.1 -P 3306 -u root -padmin < backend/scripts/create_dbpower_user.sql
   ```

2. **Verify user creation:**
   ```bash
   mysql -h 127.0.0.1 -P 3306 -u root -padmin -e "SHOW GRANTS FOR 'dbpower_monitor'@'%';"
   ```

3. **Clean existing data:**
   ```bash
   docker exec dbpower-backend python scripts/quick_cleanup.py
   ```

4. **Restart backend:**
   ```bash
   docker compose restart backend
   ```

### Daily Operations

**Clean collected data:**
```bash
docker exec dbpower-backend python scripts/quick_cleanup.py
```

**Interactive cleanup with options:**
```bash
docker exec dbpower-backend python scripts/cleanup_database.py
```

**Check slow queries:**
```bash
curl http://localhost:8000/api/v1/slow-queries | jq
```

---

## 🔍 Troubleshooting

### Queries still showing from dbpower_monitor

Check the user_host pattern in slow_log:
```sql
SELECT DISTINCT user_host FROM mysql.slow_log WHERE user_host LIKE '%dbpower%';
```

### Cannot connect with dbpower_monitor user

Verify grants:
```sql
SHOW GRANTS FOR 'dbpower_monitor'@'%';
```

Re-run the setup script if needed.

### Database cleanup fails

Use the interactive script for detailed error messages:
```bash
docker exec -it dbpower-backend python scripts/cleanup_database.py
```

---

## 📊 Monitoring

**Check collection status:**
```bash
curl http://localhost:8000/api/v1/collectors/status | jq
```

**Check analyzer status:**
```bash
curl http://localhost:8000/api/v1/analyzer/status | jq
```

**View statistics:**
```bash
curl http://localhost:8000/api/v1/stats | jq
```

---

## 🛡️ Security Notes

1. **dbpower_monitor has READ-ONLY access**
   - Cannot modify data
   - Cannot create/drop tables
   - Only SELECT, SHOW, and PROCESS privileges

2. **Change default password**
   - Update `DBPOWER_PASSWORD` in `.env`
   - Update password in MySQL:
     ```sql
     ALTER USER 'dbpower_monitor'@'%' IDENTIFIED BY 'your_new_password';
     FLUSH PRIVILEGES;
     ```

3. **Restrict access by host**
   - Current: `'dbpower_monitor'@'%'` (any host)
   - Recommended: `'dbpower_monitor'@'localhost'` or specific IP

---

## 📝 Notes

- All timestamps are in UTC
- Cleanup does NOT affect the MySQL slow_log table itself
- Only affects the DBPower local database (SQLite)
- Collection runs every 60 seconds (configurable via `COLLECTION_INTERVAL`)
