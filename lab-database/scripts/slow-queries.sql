-- ============================================================================
-- AI Query Analyzer - Slow Query Test Suite
-- ============================================================================
-- Purpose: Collection of intentionally slow queries for testing the analyzer
-- Each query demonstrates a specific performance issue
-- ============================================================================

USE ecommerce_lab;

-- ============================================================================
-- CATEGORY 1: FULL TABLE SCANS
-- ============================================================================

-- SLOW-001: Email lookup without index
-- Issue: Full table scan on 100K users
-- Expected: 500ms - 2s
-- Fix: CREATE INDEX idx_email ON users(email)
SELECT user_id, username, email, country, total_spent
FROM users
WHERE email = 'user50000@example.com';

-- SLOW-002: Country filter without index
-- Issue: Full table scan with string comparison
-- Expected: 800ms - 3s
-- Fix: CREATE INDEX idx_country ON users(country)
SELECT COUNT(*) as user_count, country
FROM users
WHERE country IN ('US', 'UK', 'CA', 'DE', 'FR')
GROUP BY country;

-- SLOW-003: Product category scan without index
-- Issue: Full table scan on 50K products
-- Expected: 600ms - 2s
-- Fix: CREATE INDEX idx_category ON products(category_id)
SELECT product_id, product_name, price, stock_quantity
FROM products
WHERE category_id = 25
ORDER BY price DESC
LIMIT 20;

-- SLOW-004: Date range scan without index
-- Issue: Full table scan with date comparison
-- Expected: 1s - 4s
-- Fix: CREATE INDEX idx_created_at ON users(created_at)
SELECT user_id, username, email, created_at
FROM users
WHERE created_at >= '2022-01-01'
  AND created_at < '2023-01-01'
ORDER BY created_at DESC;

-- ============================================================================
-- CATEGORY 2: MISSING COMPOSITE INDEXES
-- ============================================================================

-- SLOW-005: User order history (wrong index)
-- Issue: Has index on user_id but not on (user_id, order_date)
-- Expected: 1s - 3s
-- Fix: CREATE INDEX idx_user_date ON orders(user_id, order_date)
SELECT o.order_id, o.order_number, o.order_date, o.total_amount, o.status
FROM orders o
WHERE o.user_id = 12345
ORDER BY o.order_date DESC
LIMIT 50;

-- SLOW-006: Product category with price sorting
-- Issue: No composite index on (category_id, price)
-- Expected: 2s - 5s
-- Fix: CREATE INDEX idx_category_price ON products(category_id, price)
SELECT p.product_id, p.product_name, p.price, p.rating_avg
FROM products p
WHERE p.category_id = 15
  AND p.price BETWEEN 50 AND 200
  AND p.is_active = TRUE
ORDER BY p.price ASC;

-- SLOW-007: Product reviews with date sorting
-- Issue: No composite index on (product_id, created_at)
-- Expected: 1.5s - 4s
-- Fix: CREATE INDEX idx_product_date ON reviews(product_id, created_at)
SELECT r.review_id, r.user_id, r.rating, r.title, r.created_at
FROM reviews r
WHERE r.product_id = 1234
ORDER BY r.created_at DESC
LIMIT 10;

-- ============================================================================
-- CATEGORY 3: INEFFICIENT JOINS
-- ============================================================================

-- SLOW-008: Order with items (product lookup)
-- Issue: No index on order_items.product_id
-- Expected: 3s - 8s
-- Fix: CREATE INDEX idx_product ON order_items(product_id)
SELECT
    o.order_id,
    o.order_number,
    o.order_date,
    oi.product_id,
    p.product_name,
    oi.quantity,
    oi.line_total
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p ON oi.product_id = p.product_id
WHERE o.order_date >= '2023-01-01'
LIMIT 1000;

-- SLOW-009: User with recent orders and items
-- Issue: Multiple table joins without proper indexes
-- Expected: 4s - 10s
-- Fix: Multiple indexes needed
SELECT
    u.user_id,
    u.username,
    u.email,
    COUNT(DISTINCT o.order_id) as order_count,
    COUNT(oi.order_item_id) as item_count,
    SUM(oi.line_total) as total_spent
FROM users u
LEFT JOIN orders o ON u.user_id = o.user_id AND o.order_date >= '2023-01-01'
LEFT JOIN order_items oi ON o.order_id = oi.order_id
WHERE u.country = 'US'
GROUP BY u.user_id, u.username, u.email
HAVING order_count > 0
LIMIT 100;

-- SLOW-010: Product performance report
-- Issue: Complex join with no indexes on order_items.product_id
-- Expected: 5s - 15s
-- Fix: CREATE INDEX idx_product_created ON order_items(product_id, created_at)
SELECT
    p.product_id,
    p.product_name,
    p.category_id,
    COUNT(oi.order_item_id) as times_ordered,
    SUM(oi.quantity) as total_quantity_sold,
    SUM(oi.line_total) as total_revenue,
    AVG(oi.unit_price) as avg_selling_price
FROM products p
LEFT JOIN order_items oi ON p.product_id = oi.product_id
    AND oi.created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
GROUP BY p.product_id, p.product_name, p.category_id
ORDER BY total_revenue DESC
LIMIT 50;

-- ============================================================================
-- CATEGORY 4: SUBQUERY PROBLEMS
-- ============================================================================

-- SLOW-011: Correlated subquery for user stats
-- Issue: Subquery executes for each row
-- Expected: 10s - 30s
-- Fix: Rewrite as JOIN or use derived table
SELECT
    u.user_id,
    u.username,
    u.email,
    (SELECT COUNT(*) FROM orders WHERE user_id = u.user_id) as order_count,
    (SELECT SUM(total_amount) FROM orders WHERE user_id = u.user_id) as total_spent,
    (SELECT MAX(order_date) FROM orders WHERE user_id = u.user_id) as last_order_date
FROM users u
WHERE u.country = 'US'
  AND u.account_status = 'active'
LIMIT 100;

-- SLOW-012: IN subquery without index
-- Issue: Subquery returns large result set, main query has no index
-- Expected: 5s - 12s
-- Fix: CREATE INDEX idx_product ON order_items(product_id) + rewrite query
SELECT p.product_id, p.product_name, p.price, p.stock_quantity
FROM products p
WHERE p.product_id IN (
    SELECT DISTINCT product_id
    FROM order_items
    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
)
ORDER BY p.price DESC;

-- SLOW-013: NOT EXISTS with poor index
-- Issue: Correlated NOT EXISTS on unindexed column
-- Expected: 8s - 20s
-- Fix: CREATE INDEX idx_product ON reviews(product_id)
SELECT p.product_id, p.product_name, p.price, p.created_at
FROM products p
WHERE p.is_active = TRUE
  AND NOT EXISTS (
      SELECT 1 FROM reviews r WHERE r.product_id = p.product_id
  )
LIMIT 100;

-- ============================================================================
-- CATEGORY 5: AGGREGATION ISSUES
-- ============================================================================

-- SLOW-014: Large aggregation without index
-- Issue: Inventory log has NO indexes
-- Expected: 8s - 25s
-- Fix: CREATE INDEX idx_product_date ON inventory_log(product_id, created_at)
SELECT
    product_id,
    COUNT(*) as transaction_count,
    SUM(quantity_change) as net_change,
    MIN(created_at) as first_transaction,
    MAX(created_at) as last_transaction
FROM inventory_log
WHERE created_at >= '2023-01-01'
GROUP BY product_id
HAVING transaction_count > 10
ORDER BY transaction_count DESC
LIMIT 100;

-- SLOW-015: Complex aggregation with multiple tables
-- Issue: No indexes on search_log
-- Expected: 6s - 15s
-- Fix: CREATE INDEX idx_search_term ON search_log(search_term, searched_at)
SELECT
    search_term,
    COUNT(*) as search_count,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(clicked_product_id) as clicks,
    ROUND(COUNT(clicked_product_id) / COUNT(*) * 100, 2) as click_through_rate
FROM search_log
WHERE searched_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY search_term
HAVING search_count > 10
ORDER BY search_count DESC
LIMIT 20;

-- SLOW-016: Daily order aggregation
-- Issue: No index on order_date
-- Expected: 4s - 10s
-- Fix: CREATE INDEX idx_order_date ON orders(order_date)
SELECT
    DATE(order_date) as order_day,
    COUNT(*) as order_count,
    SUM(total_amount) as daily_revenue,
    AVG(total_amount) as avg_order_value,
    COUNT(DISTINCT user_id) as unique_customers
FROM orders
WHERE order_date >= DATE_SUB(NOW(), INTERVAL 90 DAY)
GROUP BY DATE(order_date)
ORDER BY order_day DESC;

-- ============================================================================
-- CATEGORY 6: LIKE QUERIES WITHOUT INDEX
-- ============================================================================

-- SLOW-017: Leading wildcard search
-- Issue: Cannot use index with leading %
-- Expected: 3s - 8s
-- Fix: Full-text index or search engine
SELECT product_id, product_name, description, price
FROM products
WHERE product_name LIKE '%laptop%'
   OR description LIKE '%laptop%'
LIMIT 50;

-- SLOW-018: Email domain search
-- Issue: Leading wildcard prevents index usage
-- Expected: 2s - 5s
-- Fix: Store domain separately or use full-text search
SELECT user_id, username, email, created_at
FROM users
WHERE email LIKE '%@gmail.com'
LIMIT 100;

-- ============================================================================
-- CATEGORY 7: SORTING LARGE RESULT SETS
-- ============================================================================

-- SLOW-019: Sort without index (filesort)
-- Issue: No index on total_spent
-- Expected: 2s - 6s
-- Fix: CREATE INDEX idx_total_spent ON users(total_spent)
SELECT user_id, username, email, total_spent, loyalty_points
FROM users
WHERE total_spent > 1000
ORDER BY total_spent DESC
LIMIT 100;

-- SLOW-020: Multi-column sort without composite index
-- Issue: No composite index for sorting
-- Expected: 3s - 8s
-- Fix: CREATE INDEX idx_country_spent ON users(country, total_spent DESC)
SELECT user_id, username, email, country, total_spent
FROM users
WHERE account_status = 'active'
ORDER BY country ASC, total_spent DESC
LIMIT 100;

-- ============================================================================
-- CATEGORY 8: DISTINCT ON LARGE TABLES
-- ============================================================================

-- SLOW-021: Distinct without index
-- Issue: No index on change_type
-- Expected: 5s - 12s
-- Fix: CREATE INDEX idx_change_type ON inventory_log(change_type)
SELECT DISTINCT product_id
FROM inventory_log
WHERE change_type = 'sale'
  AND created_at >= '2023-01-01';

-- SLOW-022: Count distinct without index
-- Issue: No index to optimize DISTINCT
-- Expected: 4s - 10s
-- Fix: CREATE INDEX idx_user_searched ON search_log(user_id, searched_at)
SELECT
    DATE(searched_at) as search_date,
    COUNT(DISTINCT user_id) as unique_users,
    COUNT(*) as total_searches
FROM search_log
WHERE searched_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(searched_at);

-- ============================================================================
-- CATEGORY 9: COMPLEX WHERE CLAUSES
-- ============================================================================

-- SLOW-023: OR condition prevents index usage
-- Issue: OR conditions on different columns
-- Expected: 3s - 7s
-- Fix: Rewrite as UNION or ensure all columns indexed
SELECT user_id, username, email, country, total_spent
FROM users
WHERE total_spent > 5000
   OR loyalty_points > 2000
   OR account_status = 'suspended'
LIMIT 100;

-- SLOW-024: Function on indexed column
-- Issue: YEAR() function prevents index usage
-- Expected: 2s - 5s
-- Fix: Rewrite as: created_at >= '2023-01-01' AND created_at < '2024-01-01'
SELECT user_id, username, email, created_at
FROM users
WHERE YEAR(created_at) = 2023
LIMIT 100;

-- ============================================================================
-- CATEGORY 10: CARTESIAN PRODUCTS AND CROSS JOINS
-- ============================================================================

-- SLOW-025: Implicit cross join
-- Issue: Missing JOIN condition causes cartesian product
-- Expected: 10s - 60s (DANGEROUS!)
-- Fix: Add proper JOIN condition
SELECT u.username, p.product_name
FROM users u, products p
WHERE u.country = 'US'
  AND p.category_id = 1
LIMIT 100;

-- ============================================================================
-- CATEGORY 11: GROUP BY WITHOUT INDEX
-- ============================================================================

-- SLOW-026: Group by non-indexed column
-- Issue: No index on status
-- Expected: 3s - 8s
-- Fix: CREATE INDEX idx_status ON orders(status)
SELECT
    status,
    COUNT(*) as order_count,
    SUM(total_amount) as total_revenue
FROM orders
WHERE order_date >= '2023-01-01'
GROUP BY status;

-- ============================================================================
-- CATEGORY 12: UNION QUERIES
-- ============================================================================

-- SLOW-027: UNION of slow queries
-- Issue: Multiple slow queries combined
-- Expected: 8s - 20s
-- Fix: Optimize individual queries
SELECT 'High Spender' as category, user_id, username, email, total_spent
FROM users
WHERE total_spent > 10000
UNION ALL
SELECT 'Active Reviewer', user_id, username, email, total_spent
FROM users
WHERE user_id IN (
    SELECT user_id FROM reviews GROUP BY user_id HAVING COUNT(*) > 5
);

-- ============================================================================
-- Summary
-- ============================================================================
-- Total slow queries: 27
-- Categories covered:
--   1. Full table scans (4 queries)
--   2. Missing composite indexes (3 queries)
--   3. Inefficient JOINs (3 queries)
--   4. Subquery problems (3 queries)
--   5. Aggregation issues (3 queries)
--   6. LIKE queries (2 queries)
--   7. Sorting issues (2 queries)
--   8. DISTINCT problems (2 queries)
--   9. Complex WHERE (2 queries)
--  10. Cartesian products (1 query)
--  11. GROUP BY issues (1 query)
--  12. UNION queries (1 query)
--
-- Expected behavior:
-- - All queries should appear in mysql.slow_log
-- - Execution times range from 500ms to 60s
-- - Various EXPLAIN plan issues (ALL, filesort, temporary, etc.)
-- ============================================================================
