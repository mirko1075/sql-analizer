-- ============================================================================
-- AI Query Analyzer - MySQL Lab Database Data Generation
-- ============================================================================
-- Purpose: Generate realistic test data for slow query detection
-- ============================================================================

USE ecommerce_lab;

-- Disable foreign key checks for faster loading
SET FOREIGN_KEY_CHECKS = 0;
SET UNIQUE_CHECKS = 0;
SET AUTOCOMMIT = 0;

-- ============================================================================
-- Generate Users (100,000 users)
-- ============================================================================
DROP PROCEDURE IF EXISTS generate_users;

DELIMITER $$
CREATE PROCEDURE generate_users()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE batch_size INT DEFAULT 1000;
    DECLARE total_users INT DEFAULT 100000;

    TRUNCATE TABLE users;

    WHILE i <= total_users DO
        INSERT INTO users (
            username, email, first_name, last_name,
            country, city, postal_code, phone,
            date_of_birth, account_status,
            created_at, last_login,
            total_orders, total_spent, loyalty_points,
            preferences
        ) VALUES
        (
            CONCAT('user', i),
            CONCAT('user', i, '@example.com'),
            CONCAT('FirstName', i),
            CONCAT('LastName', i),
            ELT(1 + (i % 20), 'US', 'UK', 'CA', 'AU', 'DE', 'FR', 'ES', 'IT', 'JP', 'CN', 'BR', 'MX', 'IN', 'RU', 'KR', 'SE', 'NO', 'DK', 'FI', 'NL'),
            CONCAT('City', i % 100),
            LPAD(i % 99999, 5, '0'),
            CONCAT('+1-555-', LPAD(i % 10000, 4, '0')),
            DATE_ADD('1950-01-01', INTERVAL (i % 25000) DAY),
            ELT(1 + (i % 10), 'active', 'active', 'active', 'active', 'active', 'active', 'active', 'active', 'suspended', 'deleted'),
            DATE_ADD('2020-01-01', INTERVAL (i % 1460) DAY),
            DATE_ADD('2020-01-01', INTERVAL (i % 1460 + FLOOR(RAND() * 100)) DAY),
            FLOOR(RAND() * 50),
            ROUND(RAND() * 10000, 2),
            FLOOR(RAND() * 5000),
            JSON_OBJECT(
                'newsletter', IF(i % 2 = 0, TRUE, FALSE),
                'sms_alerts', IF(i % 3 = 0, TRUE, FALSE),
                'language', ELT(1 + (i % 5), 'en', 'es', 'fr', 'de', 'ja')
            )
        );

        SET i = i + 1;

        -- Commit in batches
        IF i % batch_size = 0 THEN
            COMMIT;
            SELECT CONCAT('Generated ', i, ' users...') as Progress;
        END IF;
    END WHILE;

    COMMIT;
    SELECT CONCAT('Total users generated: ', total_users) as Complete;
END$$
DELIMITER ;

CALL generate_users();

-- ============================================================================
-- Generate Products (50,000 products)
-- ============================================================================
DROP PROCEDURE IF EXISTS generate_products;

DELIMITER $$
CREATE PROCEDURE generate_products()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE batch_size INT DEFAULT 1000;
    DECLARE total_products INT DEFAULT 50000;

    TRUNCATE TABLE products;

    WHILE i <= total_products DO
        INSERT INTO products (
            sku, product_name, description, category_id,
            brand, price, cost, stock_quantity,
            weight_kg, is_active, created_at,
            rating_avg, review_count, dimensions, tags
        ) VALUES
        (
            CONCAT('SKU-', LPAD(i, 8, '0')),
            CONCAT('Product ', i, ' - ',
                ELT(1 + (i % 10), 'Premium', 'Basic', 'Deluxe', 'Standard', 'Pro', 'Lite', 'Plus', 'Max', 'Ultra', 'Super')),
            CONCAT('This is a detailed description for product ', i, '. ',
                'Features include high quality, durability, and excellent value. ',
                'Perfect for everyday use. Manufactured with care.'),
            1 + (i % 50),  -- 50 different categories
            CONCAT('Brand', 1 + (i % 100)),  -- 100 different brands
            ROUND(9.99 + (RAND() * 990), 2),
            ROUND(5.00 + (RAND() * 400), 2),
            FLOOR(RAND() * 1000),
            ROUND(0.1 + (RAND() * 50), 2),
            IF(i % 20 = 0, FALSE, TRUE),
            DATE_ADD('2018-01-01', INTERVAL (i % 2190) DAY),
            ROUND(1 + (RAND() * 4), 2),
            FLOOR(RAND() * 500),
            JSON_OBJECT(
                'length_cm', ROUND(10 + RAND() * 100, 1),
                'width_cm', ROUND(10 + RAND() * 100, 1),
                'height_cm', ROUND(5 + RAND() * 50, 1)
            ),
            JSON_ARRAY(
                ELT(1 + (i % 5), 'electronics', 'clothing', 'home', 'sports', 'toys'),
                ELT(1 + (i % 3), 'bestseller', 'new', 'sale')
            )
        );

        SET i = i + 1;

        IF i % batch_size = 0 THEN
            COMMIT;
            SELECT CONCAT('Generated ', i, ' products...') as Progress;
        END IF;
    END WHILE;

    COMMIT;
    SELECT CONCAT('Total products generated: ', total_products) as Complete;
END$$
DELIMITER ;

CALL generate_products();

-- ============================================================================
-- Generate Orders (500,000 orders)
-- ============================================================================
DROP PROCEDURE IF EXISTS generate_orders;

DELIMITER $$
CREATE PROCEDURE generate_orders()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE batch_size INT DEFAULT 1000;
    DECLARE total_orders INT DEFAULT 500000;
    DECLARE random_user BIGINT;
    DECLARE random_subtotal DECIMAL(12,2);

    TRUNCATE TABLE orders;

    WHILE i <= total_orders DO
        SET random_user = 1 + FLOOR(RAND() * 100000);
        SET random_subtotal = ROUND(50 + (RAND() * 1950), 2);

        INSERT INTO orders (
            user_id, order_number, order_date, status,
            payment_method, payment_status,
            shipping_address, billing_address,
            subtotal, tax_amount, shipping_cost, discount_amount, total_amount,
            notes
        ) VALUES
        (
            random_user,
            CONCAT('ORD-', YEAR(DATE_ADD('2020-01-01', INTERVAL (i % 1460) DAY)), '-', LPAD(i, 10, '0')),
            DATE_ADD('2020-01-01', INTERVAL (i % 1460) DAY) + INTERVAL FLOOR(RAND() * 86400) SECOND,
            ELT(1 + (i % 10), 'pending', 'processing', 'processing', 'shipped', 'shipped', 'shipped', 'delivered', 'delivered', 'delivered', 'cancelled'),
            ELT(1 + (i % 4), 'credit_card', 'paypal', 'bank_transfer', 'cash_on_delivery'),
            ELT(1 + (i % 8), 'pending', 'paid', 'paid', 'paid', 'paid', 'paid', 'paid', 'refunded'),
            JSON_OBJECT(
                'street', CONCAT(FLOOR(RAND() * 9999), ' Main St'),
                'city', CONCAT('City', i % 100),
                'postal_code', LPAD(i % 99999, 5, '0'),
                'country', ELT(1 + (i % 5), 'US', 'UK', 'CA', 'AU', 'DE')
            ),
            JSON_OBJECT(
                'street', CONCAT(FLOOR(RAND() * 9999), ' Billing Ave'),
                'city', CONCAT('City', i % 100),
                'postal_code', LPAD(i % 99999, 5, '0'),
                'country', ELT(1 + (i % 5), 'US', 'UK', 'CA', 'AU', 'DE')
            ),
            random_subtotal,
            ROUND(random_subtotal * 0.08, 2),
            ROUND(5 + (RAND() * 20), 2),
            ROUND(RAND() * 50, 2),
            ROUND(random_subtotal * 1.08 + 5 + (RAND() * 20) - (RAND() * 50), 2),
            IF(i % 10 = 0, CONCAT('Customer note for order ', i), NULL)
        );

        SET i = i + 1;

        IF i % batch_size = 0 THEN
            COMMIT;
            SELECT CONCAT('Generated ', i, ' orders...') as Progress;
        END IF;
    END WHILE;

    COMMIT;
    SELECT CONCAT('Total orders generated: ', total_orders) as Complete;
END$$
DELIMITER ;

CALL generate_orders();

-- ============================================================================
-- Generate Order Items (2,000,000 items - avg 4 items per order)
-- ============================================================================
DROP PROCEDURE IF EXISTS generate_order_items;

DELIMITER $$
CREATE PROCEDURE generate_order_items()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE j INT DEFAULT 1;
    DECLARE batch_size INT DEFAULT 1000;
    DECLARE total_orders INT DEFAULT 500000;
    DECLARE items_per_order INT;
    DECLARE random_product BIGINT;
    DECLARE random_price DECIMAL(10,2);

    TRUNCATE TABLE order_items;

    WHILE i <= total_orders DO
        -- Each order gets 1-8 items
        SET items_per_order = 1 + FLOOR(RAND() * 8);
        SET j = 1;

        WHILE j <= items_per_order DO
            SET random_product = 1 + FLOOR(RAND() * 50000);
            SET random_price = ROUND(9.99 + (RAND() * 490), 2);

            INSERT INTO order_items (
                order_id, product_id, quantity, unit_price,
                discount_percent, line_total
            ) VALUES
            (
                i,
                random_product,
                1 + FLOOR(RAND() * 5),
                random_price,
                IF(RAND() > 0.7, ROUND(RAND() * 30, 2), 0),
                ROUND(random_price * (1 + FLOOR(RAND() * 5)) * (1 - IF(RAND() > 0.7, RAND() * 0.3, 0)), 2)
            );

            SET j = j + 1;
        END WHILE;

        SET i = i + 1;

        IF i % batch_size = 0 THEN
            COMMIT;
            SELECT CONCAT('Generated order items for ', i, ' orders...') as Progress;
        END IF;
    END WHILE;

    COMMIT;
    SELECT 'Order items generation complete' as Complete;
END$$
DELIMITER ;

CALL generate_order_items();

-- ============================================================================
-- Generate Reviews (300,000 reviews)
-- ============================================================================
DROP PROCEDURE IF EXISTS generate_reviews;

DELIMITER $$
CREATE PROCEDURE generate_reviews()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE batch_size INT DEFAULT 1000;
    DECLARE total_reviews INT DEFAULT 300000;

    TRUNCATE TABLE reviews;

    WHILE i <= total_reviews DO
        INSERT INTO reviews (
            product_id, user_id, rating, title, review_text,
            is_verified_purchase, helpful_count, created_at
        ) VALUES
        (
            1 + FLOOR(RAND() * 50000),
            1 + FLOOR(RAND() * 100000),
            1 + FLOOR(RAND() * 5),
            CONCAT('Review title ', i),
            CONCAT('This is review number ', i, '. ',
                ELT(1 + (i % 5),
                    'Great product! Highly recommend.',
                    'Good value for money. Works as expected.',
                    'Average quality. Could be better.',
                    'Not satisfied with this purchase.',
                    'Excellent! Exceeded my expectations.')),
            IF(RAND() > 0.3, TRUE, FALSE),
            FLOOR(RAND() * 100),
            DATE_ADD('2020-01-01', INTERVAL (i % 1460) DAY)
        );

        SET i = i + 1;

        IF i % batch_size = 0 THEN
            COMMIT;
            SELECT CONCAT('Generated ', i, ' reviews...') as Progress;
        END IF;
    END WHILE;

    COMMIT;
    SELECT CONCAT('Total reviews generated: ', total_reviews) as Complete;
END$$
DELIMITER ;

CALL generate_reviews();

-- ============================================================================
-- Generate Inventory Log (1,000,000 entries)
-- ============================================================================
DROP PROCEDURE IF EXISTS generate_inventory_log;

DELIMITER $$
CREATE PROCEDURE generate_inventory_log()
BEGIN
    DECLARE i INT DEFAULT 1;
    DECLARE batch_size INT DEFAULT 1000;
    DECLARE total_logs INT DEFAULT 1000000;

    TRUNCATE TABLE inventory_log;

    WHILE i <= total_logs DO
        INSERT INTO inventory_log (
            product_id, change_type, quantity_change,
            quantity_before, quantity_after, reference_id, notes, created_at
        ) VALUES
        (
            1 + FLOOR(RAND() * 50000),
            ELT(1 + FLOOR(RAND() * 4), 'purchase', 'sale', 'adjustment', 'return'),
            FLOOR(RAND() * 100) - 50,
            FLOOR(RAND() * 1000),
            FLOOR(RAND() * 1000),
            IF(RAND() > 0.5, FLOOR(RAND() * 500000), NULL),
            IF(RAND() > 0.8, CONCAT('Note for log entry ', i), NULL),
            DATE_ADD('2020-01-01', INTERVAL (i % 1460) DAY)
        );

        SET i = i + 1;

        IF i % batch_size = 0 THEN
            COMMIT;
            SELECT CONCAT('Generated ', i, ' inventory logs...') as Progress;
        END IF;
    END WHILE;

    COMMIT;
    SELECT CONCAT('Total inventory logs generated: ', total_logs) as Complete;
END$$
DELIMITER ;

CALL generate_inventory_log();

-- ============================================================================
-- Generate smaller tables
-- ============================================================================

-- Customer sessions (200,000)
TRUNCATE TABLE customer_sessions;
INSERT INTO customer_sessions (user_id, session_token, ip_address, session_start, page_views)
SELECT
    IF(RAND() > 0.2, 1 + FLOOR(RAND() * 100000), NULL),
    UUID(),
    CONCAT(FLOOR(RAND() * 255), '.', FLOOR(RAND() * 255), '.', FLOOR(RAND() * 255), '.', FLOOR(RAND() * 255)),
    DATE_ADD('2023-01-01', INTERVAL FLOOR(RAND() * 365) DAY),
    1 + FLOOR(RAND() * 50)
FROM
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t1,
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t2,
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t3,
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t4,
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4) t5,
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4) t6,
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4) t7
LIMIT 200000;

COMMIT;
SELECT 'Customer sessions generated' as Status;

-- Search log (500,000)
TRUNCATE TABLE search_log;
INSERT INTO search_log (user_id, search_term, results_count, clicked_product_id, searched_at)
SELECT
    IF(RAND() > 0.3, 1 + FLOOR(RAND() * 100000), NULL),
    ELT(1 + FLOOR(RAND() * 20), 'laptop', 'phone', 'tablet', 'headphones', 'camera',
        'watch', 'shoes', 'shirt', 'dress', 'jeans', 'backpack', 'charger',
        'mouse', 'keyboard', 'monitor', 'desk', 'chair', 'lamp', 'book', 'toy'),
    FLOOR(RAND() * 1000),
    IF(RAND() > 0.5, 1 + FLOOR(RAND() * 50000), NULL),
    DATE_ADD('2023-01-01', INTERVAL FLOOR(RAND() * 365) DAY)
FROM
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t1,
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t2,
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t3,
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t4,
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t5,
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5) t6,
    (SELECT 1 UNION SELECT 2 UNION SELECT 3 UNION SELECT 4) t7
LIMIT 500000;

COMMIT;
SELECT 'Search log generated' as Status;

-- Re-enable checks
SET FOREIGN_KEY_CHECKS = 1;
SET UNIQUE_CHECKS = 1;
SET AUTOCOMMIT = 1;

-- ============================================================================
-- Verify data loaded
-- ============================================================================
SELECT 'Data generation complete!' as Status;
SELECT
    'users' as table_name, COUNT(*) as row_count FROM users
UNION ALL
SELECT 'products', COUNT(*) FROM products
UNION ALL
SELECT 'orders', COUNT(*) FROM orders
UNION ALL
SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL
SELECT 'reviews', COUNT(*) FROM reviews
UNION ALL
SELECT 'inventory_log', COUNT(*) FROM inventory_log
UNION ALL
SELECT 'customer_sessions', COUNT(*) FROM customer_sessions
UNION ALL
SELECT 'search_log', COUNT(*) FROM search_log;
