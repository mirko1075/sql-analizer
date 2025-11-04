-- ===================================================================
-- Test 7: Large Table Date Range Query (Partitioning Needed)
-- ===================================================================
-- Issue: Scanning millions of analytics events without partitioning
-- Expected: Very slow, full table scan
-- Fix: Partition table by event_timestamp (monthly or yearly)
-- ===================================================================

USE dbpower_test;

-- Query recent analytics (still scans entire table)
SELECT * FROM analytics_events 
WHERE event_timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY event_timestamp DESC
LIMIT 1000;

-- Aggregate query on large table
SELECT 
    event_type,
    DATE(event_timestamp) as event_date,
    COUNT(*) as event_count
FROM analytics_events
WHERE event_timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY event_type, DATE(event_timestamp)
ORDER BY event_date DESC;

-- Query old data (should be archived/partitioned)
SELECT COUNT(*) FROM analytics_events
WHERE event_timestamp < DATE_SUB(NOW(), INTERVAL 1 YEAR);
