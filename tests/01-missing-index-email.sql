-- ===================================================================
-- Test 1: Missing Index on Email Lookup
-- ===================================================================
-- Issue: Full table scan on users table (no index on email)
-- Expected: Should trigger slow query log
-- Fix: CREATE INDEX idx_email ON users(email);
-- ===================================================================

USE dbpower_test;

SELECT * FROM users WHERE email = 'test12345@example.com';

SELECT * FROM users WHERE email LIKE '%@gmail.com';

SELECT COUNT(*) FROM users WHERE email LIKE 'a%';
