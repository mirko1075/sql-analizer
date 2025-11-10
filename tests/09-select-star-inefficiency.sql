-- ===================================================================
-- Test 9: SELECT * Without Covering Index
-- ===================================================================
-- Issue: Fetching all columns when only few are needed
-- Expected: Slower than necessary, more I/O
-- Fix: Use covering indexes or select only needed columns
-- ===================================================================

USE dbpower_test;

-- BAD: SELECT * when only few columns needed
SELECT * FROM orders 
WHERE order_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
ORDER BY order_date DESC;

-- BETTER: Select only needed columns (can use covering index)
SELECT id, user_id, order_date, total_amount, status
FROM orders
WHERE order_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
ORDER BY order_date DESC;

-- BAD: Fetching large TEXT columns unnecessarily
SELECT * FROM product_reviews 
WHERE rating = 5
LIMIT 1000;
