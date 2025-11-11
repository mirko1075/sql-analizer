-- ===================================================================
-- Test 8: Text Search Without FULLTEXT Index
-- ===================================================================
-- Issue: LIKE queries with wildcards on text columns
-- Expected: Full table scan, very slow
-- Fix: CREATE FULLTEXT INDEX idx_search_query ON search_logs(search_query);
--      Then use: MATCH(search_query) AGAINST('keyword' IN BOOLEAN MODE)
-- ===================================================================

USE dbpower_test;

-- BAD: Leading wildcard - cannot use index
SELECT * FROM search_logs 
WHERE search_query LIKE '%product%'
ORDER BY search_timestamp DESC
LIMIT 100;

-- BAD: Case-insensitive search
SELECT * FROM search_logs 
WHERE LOWER(search_query) LIKE '%electronics%'
LIMIT 100;

-- Multiple LIKE conditions (very slow)
SELECT * FROM search_logs
WHERE search_query LIKE '%phone%' 
   OR search_query LIKE '%laptop%'
   OR search_query LIKE '%tablet%'
LIMIT 100;
