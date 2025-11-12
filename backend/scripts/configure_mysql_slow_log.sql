-- =====================================================
-- MySQL Slow Query Log Configuration
-- =====================================================
-- Configures MySQL to log slow queries to TABLE
-- instead of FILE, so DBPower can read them.
-- =====================================================

-- Enable slow query log
SET GLOBAL slow_query_log = 'ON';

-- Set log output to TABLE (required for DBPower)
SET GLOBAL log_output = 'TABLE';

-- Set threshold for slow queries (in seconds)
-- Default: 0.3 seconds
-- Adjust based on your needs:
--   - 0.1 = Very aggressive (log queries > 100ms)
--   - 0.3 = Balanced (log queries > 300ms)
--   - 1.0 = Conservative (log queries > 1 second)
SET GLOBAL long_query_time = 0.3;

-- Optional: Log queries that don't use indexes
-- Useful for finding missing index opportunities
SET GLOBAL log_queries_not_using_indexes = 'ON';

-- Optional: Log administrative statements
-- (ALTER TABLE, CREATE INDEX, etc.)
-- SET GLOBAL log_slow_admin_statements = 'ON';

-- Verify configuration
SELECT 
    @@slow_query_log as slow_log_enabled,
    @@log_output as log_output,
    @@long_query_time as threshold_seconds,
    @@log_queries_not_using_indexes as log_no_indexes;

-- Check current slow queries count
SELECT 
    COUNT(*) as total_slow_queries,
    MIN(start_time) as oldest_query,
    MAX(start_time) as newest_query
FROM mysql.slow_log;

-- =====================================================
-- IMPORTANT: Make Configuration Persistent
-- =====================================================
-- The above changes are RUNTIME only.
-- To make them persistent across MySQL restarts,
-- add these lines to your MySQL configuration file:
--
-- For Docker: Add to docker-compose.yml command:
--   command: >
--     --slow_query_log=1
--     --log_output=TABLE
--     --long_query_time=0.3
--     --log_queries_not_using_indexes=ON
--
-- For MySQL config file (/etc/mysql/my.cnf):
--   [mysqld]
--   slow_query_log = 1
--   log_output = TABLE
--   long_query_time = 0.3
--   log_queries_not_using_indexes = ON
-- =====================================================

-- Optional: Clean old slow queries
-- TRUNCATE TABLE mysql.slow_log;
