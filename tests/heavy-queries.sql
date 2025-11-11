-- ===================================================================
-- Heavy Query Tests on Existing labdb Database
-- ===================================================================
-- These queries will generate slow query log entries
-- ===================================================================

USE labdb;

-- Test 1: Full table scan with LIKE wildcard
-- Issue: Leading wildcard prevents index usage
SELECT * FROM users WHERE email LIKE '%gmail.com' LIMIT 100;

-- Test 2: Complex JOIN without proper indexes
-- Issue: No index on user_id in orders table
SELECT u.full_name, u.email, COUNT(o.id) as order_count, SUM(o.total_amount) as total_spent
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
GROUP BY u.id, u.full_name, u.email
HAVING total_spent > 1000
ORDER BY total_spent DESC;

-- Test 3: Correlated subquery
-- Issue: Subquery executes for each row
SELECT u.*, 
       (SELECT COUNT(*) FROM orders WHERE user_id = u.id) as order_count,
       (SELECT SUM(total_amount) FROM orders WHERE user_id = u.id) as total_spent
FROM users u
WHERE u.country = 'USA'
LIMIT 1000;

-- Test 4: Full table scan with OR conditions
-- Issue: OR conditions prevent index usage
SELECT * FROM users WHERE country = 'USA' OR country = 'UK' OR country = 'Canada';

-- Test 5: Range query without index
-- Issue: No index on price column
SELECT * FROM products WHERE price BETWEEN 50 AND 100;

-- Test 6: ORDER BY without index
-- Issue: No index on order_date
SELECT * FROM orders 
WHERE status = 'completed'
ORDER BY order_date DESC 
LIMIT 1000;

-- Test 7: Multiple JOINs with aggregation
-- Issue: Complex query with multiple table scans
SELECT 
    u.country,
    COUNT(DISTINCT u.id) as user_count,
    COUNT(o.id) as order_count,
    AVG(o.total_amount) as avg_order_value,
    SUM(o.total_amount) as total_revenue
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE o.order_date >= DATE_SUB(NOW(), INTERVAL 6 MONTH)
GROUP BY u.country
HAVING order_count > 10
ORDER BY total_revenue DESC;

-- Test 8: DISTINCT with JOIN (inefficient)
-- Issue: DISTINCT after JOIN is expensive
SELECT DISTINCT u.country, u.city
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE o.status IN ('completed', 'shipped');

-- Test 9: Self-join for analytics
-- Issue: Expensive self-join operation
SELECT u1.country, COUNT(DISTINCT u2.id) as referred_users
FROM users u1
LEFT JOIN users u2 ON u1.city = u2.city AND u1.id != u2.id
WHERE u1.country IN ('USA', 'UK', 'Germany')
GROUP BY u1.country;

-- Test 10: Large OFFSET pagination
-- Issue: MySQL has to scan all skipped rows
SELECT * FROM orders 
ORDER BY id 
LIMIT 100 OFFSET 45000;

-- Test 11: Function on indexed column (if any)
-- Issue: Functions prevent index usage
SELECT * FROM users WHERE LOWER(email) LIKE '%test%';

-- Test 12: Complex WHERE with multiple conditions
-- Issue: No covering index for this query pattern
SELECT u.*, o.order_date, o.total_amount
FROM users u
JOIN orders o ON u.id = o.user_id
WHERE u.country = 'USA'
  AND o.status = 'completed'
  AND o.order_date >= '2024-01-01'
  AND o.total_amount > 500
ORDER BY o.order_date DESC
LIMIT 500;

-- Test 13: Aggregation without index
-- Issue: GROUP BY on non-indexed column
SELECT status, COUNT(*) as count, AVG(total_amount) as avg_amount
FROM orders
GROUP BY status;

-- Test 14: NOT IN with subquery (slow)
-- Issue: NOT IN is less efficient than LEFT JOIN
SELECT * FROM users 
WHERE id NOT IN (SELECT DISTINCT user_id FROM orders WHERE status = 'cancelled')
LIMIT 1000;

-- Test 15: Multiple aggregations on large dataset
-- Issue: Full table scan with multiple calculations
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_orders,
    COUNT(DISTINCT user_id) as unique_users,
    SUM(total_amount) as revenue,
    AVG(total_amount) as avg_order,
    MIN(total_amount) as min_order,
    MAX(total_amount) as max_order
FROM orders
GROUP BY DATE(created_at)
ORDER BY date DESC;
