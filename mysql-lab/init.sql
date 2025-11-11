-- DBPower Base - MySQL Demo Database
-- Creates sample tables with intentionally missing indexes for testing

USE labdb;

-- Users table (no index on email - will cause slow queries)
DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    city VARCHAR(100),
    country VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Orders table (no index on user_id or status - will cause slow queries)
DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    product_name VARCHAR(255),
    total_amount DECIMAL(10, 2),
    status VARCHAR(50),
    order_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table (no index on category)
DROP TABLE IF EXISTS products;
CREATE TABLE products (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    price DECIMAL(10, 2),
    stock_quantity INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert 10,000 users
DROP PROCEDURE IF EXISTS insert_demo_users;
DELIMITER //
CREATE PROCEDURE insert_demo_users()
BEGIN
    DECLARE i INT DEFAULT 1;
    WHILE i <= 10000 DO
        INSERT INTO users (email, full_name, city, country)
        VALUES (
            CONCAT('user', i, '@example.com'),
            CONCAT('User ', i, ' Test'),
            ELT(FLOOR(1 + RAND() * 10), 'New York', 'London', 'Paris', 'Tokyo', 'Sydney', 'Toronto', 'Berlin', 'Madrid', 'Rome', 'Amsterdam'),
            ELT(FLOOR(1 + RAND() * 5), 'USA', 'UK', 'France', 'Japan', 'Australia')
        );
        SET i = i + 1;
    END WHILE;
END //
DELIMITER ;

CALL insert_demo_users();
DROP PROCEDURE insert_demo_users;

-- Insert 50,000 orders
DROP PROCEDURE IF EXISTS insert_demo_orders;
DELIMITER //
CREATE PROCEDURE insert_demo_orders()
BEGIN
    DECLARE i INT DEFAULT 1;
    WHILE i <= 50000 DO
        INSERT INTO orders (user_id, product_name, total_amount, status, order_date)
        VALUES (
            FLOOR(1 + RAND() * 10000),
            CONCAT('Product ', FLOOR(1 + RAND() * 100)),
            ROUND(10 + RAND() * 500, 2),
            ELT(FLOOR(1 + RAND() * 5), 'pending', 'processing', 'shipped', 'delivered', 'cancelled'),
            DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND() * 365) DAY)
        );
        SET i = i + 1;
    END WHILE;
END //
DELIMITER ;

CALL insert_demo_orders();
DROP PROCEDURE insert_demo_orders;

-- Insert 1,000 products
DROP PROCEDURE IF EXISTS insert_demo_products;
DELIMITER //
CREATE PROCEDURE insert_demo_products()
BEGIN
    DECLARE i INT DEFAULT 1;
    WHILE i <= 1000 DO
        INSERT INTO products (name, category, price, stock_quantity)
        VALUES (
            CONCAT('Product ', i),
            ELT(FLOOR(1 + RAND() * 5), 'Electronics', 'Clothing', 'Books', 'Home', 'Sports'),
            ROUND(10 + RAND() * 990, 2),
            FLOOR(RAND() * 500)
        );
        SET i = i + 1;
    END WHILE;
END //
DELIMITER ;

CALL insert_demo_products();
DROP PROCEDURE insert_demo_products;

-- Show table statistics
SELECT 'Users' AS table_name, COUNT(*) AS row_count FROM users
UNION ALL
SELECT 'Orders', COUNT(*) FROM orders
UNION ALL
SELECT 'Products', COUNT(*) FROM products;

SELECT '✅ Demo data loaded successfully!' AS status;
