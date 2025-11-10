-- ===================================================================
-- Test 6: Correlated Subquery (Slow)
-- ===================================================================
-- Issue: Correlated subquery executed for each row
-- Expected: Very slow query
-- Fix: Use JOIN or window functions instead
-- ===================================================================

USE dbpower_test;

-- BAD: Correlated subquery (runs for each product)
SELECT 
    p.id,
    p.product_name,
    p.price,
    (SELECT AVG(rating) FROM product_reviews pr WHERE pr.product_id = p.id) as avg_rating,
    (SELECT COUNT(*) FROM product_reviews pr WHERE pr.product_id = p.id) as review_count
FROM products p
WHERE p.category = 'Electronics'
LIMIT 100;

-- BAD: Get latest price for each product
SELECT 
    p.id,
    p.product_name,
    p.price,
    (SELECT MAX(changed_at) FROM price_history ph WHERE ph.product_id = p.id) as last_price_change
FROM products p
LIMIT 100;

-- BAD: Subquery in WHERE clause
SELECT * FROM products p
WHERE p.price > (
    SELECT AVG(price) FROM products p2 WHERE p2.category = p.category
);
