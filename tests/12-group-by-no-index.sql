-- ===================================================================
-- Test 12: Group By Without Index
-- ===================================================================
-- Issue: Grouping on unindexed columns
-- Expected: Temporary table, filesort
-- Fix: CREATE INDEX on GROUP BY columns
-- ===================================================================

USE dbpower_test;

-- Group by unindexed column
SELECT supplier_id, COUNT(*), AVG(price)
FROM products
GROUP BY supplier_id;

-- Multiple grouping columns
SELECT country, city, COUNT(*) as user_count
FROM users
GROUP BY country, city
ORDER BY user_count DESC;

-- Group with HAVING
SELECT user_id, COUNT(*) as order_count, SUM(total_amount) as total_spent
FROM orders
GROUP BY user_id
HAVING order_count > 5
ORDER BY total_spent DESC;
