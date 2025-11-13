-- Test script to generate REAL slow queries in MySQL for testing
-- Run this in your MySQL database to create real slow queries (not test queries)

-- Create test database and table
CREATE DATABASE IF NOT EXISTS test_app;
USE test_app;

CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255),
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_status (status)
);

-- Insert some data
INSERT INTO users (email, status) VALUES
    ('user1@example.com', 'active'),
    ('user2@example.com', 'active'),
    ('user3@example.com', 'inactive');

-- Generate some real slow queries that will appear in slow_log

-- 1. Query without WHERE clause (full table scan)
SELECT * FROM users;

-- 2. Query with inefficient join
SELECT u1.*, u2.*
FROM users u1
CROSS JOIN users u2
WHERE u1.id < 10;

-- 3. Query with OR conditions
SELECT * FROM users
WHERE status = 'active' OR email LIKE '%example%';

-- 4. Query with function on indexed column
SELECT * FROM users
WHERE LOWER(status) = 'active';

-- 5. Complex aggregation without indexes
SELECT status, COUNT(*), AVG(id)
FROM users
GROUP BY status
ORDER BY COUNT(*) DESC;

-- Notes:
-- - These queries are intentionally inefficient for testing
-- - They will appear in mysql.slow_log if slow_query_log is enabled
-- - Adjust long_query_time if needed: SET GLOBAL long_query_time = 0;
