-- ===================================================================
-- Test 3: Range Query Without Index
-- ===================================================================
-- Issue: Searching products by price range without index
-- Expected: Full scan on products table
-- Fix: CREATE INDEX idx_price ON products(price);
-- ===================================================================

USE dbpower_test;

SELECT * FROM products WHERE price BETWEEN 100 AND 200;

SELECT * FROM products WHERE price > 500 ORDER BY price;

SELECT AVG(price), category FROM products WHERE price > 100 GROUP BY category;
