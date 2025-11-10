-- ===================================================================
-- Test 4: N+1 Query Problem
-- ===================================================================
-- Issue: Loading orders with items separately (N+1 problem)
-- Expected: Multiple queries or slow single query
-- Fix: Use JOIN to fetch all data in one query
-- ===================================================================

USE dbpower_test;

-- BAD: This would be followed by N queries to get items
SELECT * FROM orders WHERE status = 'pending' LIMIT 100;

-- Then for each order: SELECT * FROM order_items WHERE order_id = ?
-- Simulating N+1:
SELECT oi.* FROM order_items oi WHERE order_id = 1;
SELECT oi.* FROM order_items oi WHERE order_id = 2;
SELECT oi.* FROM order_items oi WHERE order_id = 3;

-- GOOD: Single query with JOIN (but still slow without proper optimization)
SELECT o.*, oi.*, p.product_name 
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
LEFT JOIN products p ON oi.product_id = p.id
WHERE o.status = 'pending'
LIMIT 1000;
