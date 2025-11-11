-- ===================================================================
-- Test 10: Row-Level Locking and Contention
-- ===================================================================
-- Issue: Concurrent updates causing locks and potential deadlocks
-- Expected: Lock wait timeouts, slow updates
-- Fix: Optimize transaction scope, use proper isolation levels
-- ===================================================================

USE dbpower_test;

-- Simulate inventory update with lock
START TRANSACTION;
SELECT * FROM product_inventory WHERE product_id = 100 FOR UPDATE;
-- (Long processing time here would block other transactions)
UPDATE product_inventory 
SET available_quantity = available_quantity - 5,
    reserved_quantity = reserved_quantity + 5
WHERE product_id = 100;
COMMIT;

-- Multiple concurrent updates (run this simultaneously from multiple connections)
UPDATE product_inventory 
SET available_quantity = available_quantity - 1
WHERE product_id IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10);

-- Lock contention on high-traffic table
INSERT INTO user_sessions (user_id, session_token, ip_address) 
VALUES (FLOOR(RAND() * 50000) + 1, UUID(), '192.168.1.1');
