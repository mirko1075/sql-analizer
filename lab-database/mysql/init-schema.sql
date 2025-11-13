-- ============================================================================
-- AI Query Analyzer - MySQL Lab Database
-- ============================================================================
-- Purpose: Intentionally poorly optimized database for testing slow query detection
-- Author: AI Assistant
-- Date: 2025-11-13
-- ============================================================================

-- Enable slow query log
SET GLOBAL slow_query_log = 'ON';
SET GLOBAL long_query_time = 0.5;
SET GLOBAL log_slow_admin_statements = 'ON';
SET GLOBAL log_queries_not_using_indexes = 'ON';

-- Create database
CREATE DATABASE IF NOT EXISTS ecommerce_lab;
USE ecommerce_lab;

-- ============================================================================
-- Table: users
-- ============================================================================
-- Issue: Missing indexes on email, created_at, country
-- Impact: Searches by email, date ranges, and country will be slow
-- ============================================================================
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    user_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(255) NOT NULL,  -- ❌ NO INDEX - will cause slow lookups
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    country VARCHAR(2),  -- ❌ NO INDEX - slow country-based queries
    city VARCHAR(100),
    postal_code VARCHAR(20),
    phone VARCHAR(20),
    date_of_birth DATE,
    account_status ENUM('active', 'suspended', 'deleted') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- ❌ NO INDEX - slow date range queries
    last_login TIMESTAMP NULL,
    total_orders INT DEFAULT 0,
    total_spent DECIMAL(12,2) DEFAULT 0.00,
    loyalty_points INT DEFAULT 0,
    preferences JSON  -- Complex field that can slow queries
) ENGINE=InnoDB;

-- Only primary key index exists (user_id)
-- Missing indexes will cause slow queries on email, country, created_at

-- ============================================================================
-- Table: products
-- ============================================================================
-- Issue: Missing composite index on (category_id, price)
-- Impact: Category browsing with price sorting will be slow
-- ============================================================================
DROP TABLE IF EXISTS products;
CREATE TABLE products (
    product_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    description TEXT,
    category_id INT NOT NULL,  -- ❌ NO INDEX - slow category filtering
    brand VARCHAR(100),
    price DECIMAL(10,2) NOT NULL,  -- ❌ NO INDEX - slow price range queries
    cost DECIMAL(10,2),
    stock_quantity INT DEFAULT 0,
    weight_kg DECIMAL(8,2),
    dimensions JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    rating_avg DECIMAL(3,2) DEFAULT 0.00,
    review_count INT DEFAULT 0,
    tags JSON  -- Complex field
) ENGINE=InnoDB;

-- ❌ Missing composite index: INDEX idx_category_price (category_id, price)

-- ============================================================================
-- Table: orders
-- ============================================================================
-- Issue: Wrong index on user_id (should be composite with order_date)
-- Impact: User order history queries will be slow
-- ============================================================================
DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
    order_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,  -- ❌ WRONG INDEX - should be composite
    order_number VARCHAR(50) UNIQUE NOT NULL,
    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- ❌ NOT INDEXED
    status ENUM('pending', 'processing', 'shipped', 'delivered', 'cancelled') DEFAULT 'pending',
    payment_method VARCHAR(50),
    payment_status ENUM('pending', 'paid', 'refunded', 'failed') DEFAULT 'pending',
    shipping_address JSON,
    billing_address JSON,
    subtotal DECIMAL(12,2) NOT NULL,
    tax_amount DECIMAL(12,2) DEFAULT 0.00,
    shipping_cost DECIMAL(10,2) DEFAULT 0.00,
    discount_amount DECIMAL(10,2) DEFAULT 0.00,
    total_amount DECIMAL(12,2) NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Wrong index: only user_id, should be (user_id, order_date)
CREATE INDEX idx_user ON orders(user_id);
-- ❌ Missing: INDEX idx_user_date (user_id, order_date)
-- ❌ Missing: INDEX idx_order_date (order_date)
-- ❌ Missing: INDEX idx_status (status)

-- ============================================================================
-- Table: order_items
-- ============================================================================
-- Issue: No index on product_id, will cause slow product sales reports
-- Impact: Product analytics will be extremely slow
-- ============================================================================
DROP TABLE IF EXISTS order_items;
CREATE TABLE order_items (
    order_item_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,  -- ❌ NO INDEX - slow product reports
    quantity INT NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    discount_percent DECIMAL(5,2) DEFAULT 0.00,
    line_total DECIMAL(12,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Only has index on order_id
CREATE INDEX idx_order ON order_items(order_id);
-- ❌ Missing: INDEX idx_product (product_id)
-- ❌ Missing: INDEX idx_created_at (created_at) for time-based analytics

-- ============================================================================
-- Table: reviews
-- ============================================================================
-- Issue: Missing composite index on (product_id, created_at)
-- Impact: Product review sorting by date will be slow
-- ============================================================================
DROP TABLE IF EXISTS reviews;
CREATE TABLE reviews (
    review_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id BIGINT NOT NULL,  -- ❌ WRONG INDEX
    user_id BIGINT NOT NULL,
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title VARCHAR(200),
    review_text TEXT,
    is_verified_purchase BOOLEAN DEFAULT FALSE,
    helpful_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- ❌ NOT INDEXED
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Wrong index: only product_id
CREATE INDEX idx_product ON reviews(product_id);
-- ❌ Missing: INDEX idx_product_date (product_id, created_at)
-- ❌ Missing: INDEX idx_rating (rating)
-- ❌ Missing: INDEX idx_user (user_id)

-- ============================================================================
-- Table: inventory_log
-- ============================================================================
-- Issue: No indexes at all except primary key
-- Impact: Inventory history queries will be extremely slow
-- ============================================================================
DROP TABLE IF EXISTS inventory_log;
CREATE TABLE inventory_log (
    log_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    product_id BIGINT NOT NULL,  -- ❌ NO INDEX
    change_type ENUM('purchase', 'sale', 'adjustment', 'return') NOT NULL,
    quantity_change INT NOT NULL,
    quantity_before INT NOT NULL,
    quantity_after INT NOT NULL,
    reference_id BIGINT,  -- order_id or purchase_id
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- ❌ NO INDEX
    created_by VARCHAR(100)
) ENGINE=InnoDB;

-- ❌ NO INDEXES AT ALL - will cause full table scans

-- ============================================================================
-- Table: customer_sessions
-- ============================================================================
-- Issue: No index on user_id or session_start
-- Impact: User activity tracking will be slow
-- ============================================================================
DROP TABLE IF EXISTS customer_sessions;
CREATE TABLE customer_sessions (
    session_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT,  -- ❌ NO INDEX - can be NULL for guests
    session_token VARCHAR(255) UNIQUE NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- ❌ NO INDEX
    session_end TIMESTAMP NULL,
    page_views INT DEFAULT 0,
    actions_taken JSON,
    cart_data JSON
) ENGINE=InnoDB;

-- ❌ Missing: INDEX idx_user (user_id)
-- ❌ Missing: INDEX idx_start (session_start)

-- ============================================================================
-- Table: search_log
-- ============================================================================
-- Issue: No indexes for analytics
-- Impact: Search analytics will be very slow
-- ============================================================================
DROP TABLE IF EXISTS search_log;
CREATE TABLE search_log (
    search_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT,  -- ❌ NO INDEX
    search_term VARCHAR(255) NOT NULL,  -- ❌ NO INDEX
    filters_applied JSON,
    results_count INT,
    clicked_product_id BIGINT,  -- ❌ NO INDEX
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- ❌ NO INDEX
    session_id BIGINT
) ENGINE=InnoDB;

-- ❌ NO INDEXES - search analytics will crawl

-- ============================================================================
-- Table: wishlists
-- ============================================================================
-- Issue: Missing composite index on (user_id, product_id)
-- Impact: Wishlist checks will be slow
-- ============================================================================
DROP TABLE IF EXISTS wishlists;
CREATE TABLE wishlists (
    wishlist_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,  -- ❌ WRONG INDEX
    product_id BIGINT NOT NULL,  -- ❌ NO INDEX
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes VARCHAR(500)
) ENGINE=InnoDB;

CREATE INDEX idx_user ON wishlists(user_id);
-- ❌ Missing: UNIQUE INDEX idx_user_product (user_id, product_id)
-- ❌ Missing: INDEX idx_product (product_id)

-- ============================================================================
-- Table: cart_items
-- ============================================================================
-- Issue: No index on product_id
-- Impact: Cart analytics by product will be slow
-- ============================================================================
DROP TABLE IF EXISTS cart_items;
CREATE TABLE cart_items (
    cart_item_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,  -- ❌ NO INDEX
    quantity INT NOT NULL DEFAULT 1,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE INDEX idx_user ON cart_items(user_id);
-- ❌ Missing: INDEX idx_product (product_id)

-- ============================================================================
-- Table: promotions
-- ============================================================================
-- Issue: No index on date ranges
-- Impact: Active promotion queries will be slow
-- ============================================================================
DROP TABLE IF EXISTS promotions;
CREATE TABLE promotions (
    promotion_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    promo_code VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    discount_type ENUM('percentage', 'fixed_amount') NOT NULL,
    discount_value DECIMAL(10,2) NOT NULL,
    min_purchase_amount DECIMAL(10,2),
    max_discount_amount DECIMAL(10,2),
    start_date TIMESTAMP NOT NULL,  -- ❌ NO INDEX
    end_date TIMESTAMP NOT NULL,  -- ❌ NO INDEX
    usage_limit INT,
    times_used INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ❌ Missing: INDEX idx_dates (start_date, end_date)
-- ❌ Missing: INDEX idx_active (is_active, start_date, end_date)

-- ============================================================================
-- Summary of Performance Issues Created
-- ============================================================================
--
-- 1. users table: Missing indexes on email, country, created_at
-- 2. products table: Missing composite index on (category_id, price)
-- 3. orders table: Wrong index (should be composite with order_date)
-- 4. order_items table: Missing index on product_id
-- 5. reviews table: Wrong index structure for common queries
-- 6. inventory_log table: NO indexes except primary key
-- 7. customer_sessions table: Missing indexes on user_id and session_start
-- 8. search_log table: NO indexes for analytics
-- 9. wishlists table: Missing unique composite index
-- 10. cart_items table: Missing product_id index
-- 11. promotions table: Missing date range indexes
--
-- These issues will generate the following types of slow queries:
-- - Full table scans
-- - Missing index usage
-- - Inefficient JOINs
-- - Slow aggregations
-- - Poor sorting performance
-- - Inefficient WHERE clauses
--
-- ============================================================================

-- Create a view for reporting (intentionally slow)
CREATE OR REPLACE VIEW slow_user_order_summary AS
SELECT
    u.user_id,
    u.username,
    u.email,
    u.country,
    COUNT(o.order_id) as total_orders,
    SUM(o.total_amount) as total_spent,
    AVG(o.total_amount) as avg_order_value,
    MAX(o.order_date) as last_order_date,
    (SELECT COUNT(*) FROM reviews r WHERE r.user_id = u.user_id) as review_count
FROM users u
LEFT JOIN orders o ON u.user_id = o.user_id
GROUP BY u.user_id, u.username, u.email, u.country;
-- This view will be slow due to correlated subquery and missing indexes

-- Show database structure
SELECT 'Database schema created successfully!' as Status;
SELECT 'Tables created with intentional performance issues' as Note;
SELECT 'Ready for slow query testing' as Ready;
