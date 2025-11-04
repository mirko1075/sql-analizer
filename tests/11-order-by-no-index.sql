-- ===================================================================
-- Test 11: Order By Without Index
-- ===================================================================
-- Issue: Sorting large result sets without index on sort column
-- Expected: Filesort, temporary table creation
-- Fix: CREATE INDEX on ORDER BY columns
-- ===================================================================

USE dbpower_test;

-- Sort by unindexed column
SELECT * FROM users 
WHERE account_status = 'active'
ORDER BY last_login DESC
LIMIT 100;

-- Multiple column sort without composite index
SELECT * FROM products
WHERE category = 'Electronics'
ORDER BY price DESC, product_name ASC
LIMIT 50;

-- Large result set with ORDER BY
SELECT o.*, u.username
FROM orders o
JOIN users u ON o.user_id = u.id
ORDER BY o.total_amount DESC
LIMIT 100;
