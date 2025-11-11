-- ===================================================================
-- Test 5: Join Without Foreign Key Index
-- ===================================================================
-- Issue: Joining product_reviews with products/users (no FK indexes)
-- Expected: Very slow join performance
-- Fix: CREATE INDEX idx_product_id ON product_reviews(product_id);
--      CREATE INDEX idx_user_id ON product_reviews(user_id);
-- ===================================================================

USE dbpower_test;

-- Join reviews with products (slow - no index on product_reviews.product_id)
SELECT p.product_name, pr.rating, pr.review_text
FROM products p
JOIN product_reviews pr ON p.id = pr.product_id
WHERE p.category = 'Electronics'
LIMIT 100;

-- Join reviews with users (slow - no index on product_reviews.user_id)
SELECT u.username, pr.rating, pr.review_text
FROM users u
JOIN product_reviews pr ON u.id = pr.user_id
WHERE u.country = 'USA'
LIMIT 100;

-- Three-way join (very slow)
SELECT p.product_name, u.username, pr.rating, pr.review_text
FROM product_reviews pr
JOIN products p ON pr.product_id = p.id
JOIN users u ON pr.user_id = u.id
WHERE pr.rating >= 4
ORDER BY pr.created_at DESC
LIMIT 100;
