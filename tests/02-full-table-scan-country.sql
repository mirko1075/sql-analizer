-- ===================================================================
-- Test 2: Full Table Scan on WHERE Condition
-- ===================================================================
-- Issue: Filtering by country without index
-- Expected: Full table scan on 50k users
-- Fix: CREATE INDEX idx_country ON users(country);
-- ===================================================================

USE dbpower_test;

SELECT * FROM users WHERE country = 'USA';

SELECT * FROM users WHERE country = 'USA' AND account_status = 'active';

SELECT COUNT(*), country FROM users GROUP BY country;
