-- =====================================================
-- DBPower MySQL Monitoring User Setup
-- =====================================================
-- This script creates a dedicated MySQL user for DBPower
-- monitoring and analysis. Queries from this user will be
-- excluded from the slow query collection.
-- =====================================================

-- Step 1: Create the monitoring user
-- Replace 'your_password_here' with a secure password
CREATE USER IF NOT EXISTS 'dbpower_monitor'@'%' IDENTIFIED BY 'dbpower_secure_pass';

-- Step 2: Grant SELECT privileges on all databases
-- Needed for EXPLAIN, SHOW INDEX, DESCRIBE, etc.
GRANT SELECT ON *.* TO 'dbpower_monitor'@'%';

-- Step 3: Grant privileges on mysql.slow_log
-- Needed to read slow query log
GRANT SELECT ON mysql.slow_log TO 'dbpower_monitor'@'%';

-- Step 4: Grant privileges on performance_schema
-- Needed to check locks and query states
GRANT SELECT ON performance_schema.* TO 'dbpower_monitor'@'%';

-- Step 5: Grant SHOW VIEW privilege
-- Needed to analyze views
GRANT SHOW VIEW ON *.* TO 'dbpower_monitor'@'%';

-- Step 6: Grant PROCESS privilege
-- Needed for SHOW PROCESSLIST to check locks
GRANT PROCESS ON *.* TO 'dbpower_monitor'@'%';

-- Apply changes
FLUSH PRIVILEGES;

-- Verify the user was created
SELECT User, Host FROM mysql.user WHERE User = 'dbpower_monitor';

-- Show granted privileges
SHOW GRANTS FOR 'dbpower_monitor'@'%';

-- =====================================================
-- IMPORTANT NOTES:
-- =====================================================
-- 1. Update the password in your .env file:
--    DBPOWER_USER=dbpower_monitor
--
-- 2. This user has READ-ONLY access
--
-- 3. Queries from this user will be automatically
--    excluded from slow query collection
--
-- 4. To drop the user later:
--    DROP USER 'dbpower_monitor'@'%';
-- =====================================================
