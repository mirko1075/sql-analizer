# MySQL Lab Database - Connection Troubleshooting Guide

## Quick Diagnosis

Your error: `Lost connection to MySQL server at 'reading initial communication packet'`

**Most Likely Cause:** MySQL is still initializing (container just started 28 seconds ago)

---

## Solution 1: Wait for Initialization (Most Common)

MySQL containers take 2-5 minutes to fully initialize, especially with our large data generation scripts.

```bash
# Watch the logs to see when it's ready
docker logs -f mysql-lab-slowquery

# Look for this message appearing TWICE:
# "ready for connections"
# First appearance = MySQL server started
# Second appearance = Initialization scripts completed
```

**Then try connecting again:**
```bash
mysql -h 127.0.0.1 -P 3307 -u root -proot
```

---

## Solution 2: Check Container Health

```bash
# Run the diagnostic script
cd lab-database
./troubleshoot-connection.sh
```

Or manually check:

```bash
# Test from INSIDE the container (should work)
docker exec mysql-lab-slowquery mysql -uroot -proot -e "SELECT 1;"

# If this works, the problem is with external connectivity
```

---

## Solution 3: Fix Common Issues

### Issue A: Container Still Initializing

**Symptoms:**
- Container shows "healthy" but can't connect
- Just started less than 2 minutes ago

**Solution:**
```bash
# Wait and check logs
docker logs mysql-lab-slowquery 2>&1 | grep "ready for connections"

# Should see TWO occurrences:
# [Server] /usr/sbin/mysqld: ready for connections. Version: '8.0.x'
# (appears again after init scripts)
```

### Issue B: MySQL Not Binding to 0.0.0.0

**Symptoms:**
- Connection works from inside container
- Fails from host with "Lost connection"

**Solution:**
```bash
# Check bind address
docker exec mysql-lab-slowquery mysql -uroot -proot \
  -e "SHOW VARIABLES LIKE 'bind_address';"

# If it shows 127.0.0.1, restart with proper config:
cd lab-database
docker compose down
docker compose up -d
```

### Issue C: Port Already in Use

**Symptoms:**
- Container won't start properly
- Port conflict errors

**Solution:**
```bash
# Check what's using port 3307
sudo lsof -i :3307
# or
sudo netstat -tuln | grep 3307

# If something else is using it, either:
# 1. Stop that service
# 2. Or change port in docker-compose.yml:
#    ports:
#      - "3308:3306"  # Use 3308 instead
```

### Issue D: Docker Networking Issue

**Symptoms:**
- Container healthy and MySQL ready
- Connection from inside works
- Connection from host fails

**Solution:**
```bash
# Check Docker network
docker inspect mysql-lab-slowquery | grep -A 10 "Networks"

# Recreate container with host network mode:
cd lab-database
docker compose down

# Edit docker-compose.yml, add:
# network_mode: host

# Then restart:
docker compose up -d
```

---

## Quick Fix Commands

### Option 1: Complete Restart

```bash
cd lab-database

# Stop and remove
docker compose down -v

# Start fresh
docker compose up -d

# Wait 2-3 minutes, then check logs
docker logs -f mysql-lab-slowquery

# Wait for: "ready for connections" (appears twice)
```

### Option 2: Check if Just Need to Wait

```bash
# Check if initialization is still running
docker exec mysql-lab-slowquery ps aux | grep mysql

# Check log file size (growing = still initializing)
docker exec mysql-lab-slowquery ls -lh /var/lib/mysql/

# Check if stored procedures are running
docker exec mysql-lab-slowquery mysql -uroot -proot \
  -e "SHOW PROCESSLIST;"
```

---

## Testing Connection Step-by-Step

### Step 1: Test from Inside Container

```bash
docker exec -it mysql-lab-slowquery mysql -uroot -proot

# Once inside MySQL:
mysql> SHOW DATABASES;
mysql> USE ecommerce_lab;
mysql> SELECT COUNT(*) FROM users;
mysql> exit
```

**If this works:** MySQL is fine, issue is with external access.

**If this fails:** MySQL is still initializing or has an error.

### Step 2: Test from Host with Correct Syntax

```bash
# WRONG (lowercase -p for password):
mysql -h 127.0.0.1 -p 3307 -u root
# This tries to connect to port 3306 with password "3307"

# CORRECT (uppercase -P for port):
mysql -h 127.0.0.1 -P 3307 -u root -proot

# Or with password prompt:
mysql -h 127.0.0.1 -P 3307 -u root -p
# Then enter: root
```

### Step 3: Verify Database and Data

```bash
# Check database exists
mysql -h 127.0.0.1 -P 3307 -u root -proot \
  -e "SHOW DATABASES LIKE 'ecommerce_lab';"

# Check if data is loaded
mysql -h 127.0.0.1 -P 3307 -u root -proot ecommerce_lab \
  -e "SELECT COUNT(*) FROM users;"

# Expected: 100,000
# If 0: Data is still loading (wait 5-10 minutes)
```

---

## Monitoring Data Load Progress

The stored procedures generate 4.7 million rows, which takes 5-10 minutes:

```bash
# Watch the progress
watch -n 5 'docker exec mysql-lab-slowquery mysql -uroot -proot ecommerce_lab -e "
SELECT
  (SELECT COUNT(*) FROM users) as users,
  (SELECT COUNT(*) FROM products) as products,
  (SELECT COUNT(*) FROM orders) as orders,
  (SELECT COUNT(*) FROM order_items) as items;
"'

# Target numbers:
# users: 100,000
# products: 50,000
# orders: 500,000
# order_items: 2,000,000+
```

---

## Understanding the "healthy" Status

Docker's healthcheck for MySQL is:
```yaml
healthcheck:
  test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-uroot", "-proot"]
```

**This only checks if MySQL responds to ping, NOT if:**
- Initialization scripts finished
- Data is loaded
- External connections work

So "healthy" status can appear while data is still loading.

---

## Recommended Approach

**Run these commands in order:**

```bash
# 1. Go to lab directory
cd ~/Documents/personal/dbpower-ai-cloud/lab-database

# 2. Check container logs
docker logs mysql-lab-slowquery 2>&1 | tail -50

# 3. Look for "ready for connections" - should appear TWICE
# If you only see it once, wait 2-3 more minutes

# 4. Once you see it twice, test connection
mysql -h 127.0.0.1 -P 3307 -u root -proot -e "SELECT 'Success!' as status;"

# 5. Check if data is loaded
mysql -h 127.0.0.1 -P 3307 -u root -proot ecommerce_lab \
  -e "SELECT COUNT(*) as users FROM users;"

# 6. If users = 0, wait for data loading
docker logs mysql-lab-slowquery | grep "users generated"

# 7. Once data is loaded, run slow queries
cd scripts
./run-slow-queries.sh
```

---

## Still Not Working?

If none of the above works, provide me with:

```bash
# Run and share output:
docker logs mysql-lab-slowquery 2>&1 | tail -100
docker inspect mysql-lab-slowquery | grep -A 20 "Config"
netstat -tuln | grep 3307
```

---

## Alternative: Use Docker Exec for Now

If external connection keeps failing, you can run queries directly via docker exec:

```bash
# Run slow queries through docker exec
docker exec mysql-lab-slowquery mysql -uroot -proot ecommerce_lab << 'SQL'
SELECT user_id, username, email FROM users WHERE email = 'user50000@example.com';
SELECT COUNT(*) FROM users WHERE country = 'US';
SQL
```

---

**Most Likely:** Just wait 2-3 more minutes for initialization to complete! 😊
