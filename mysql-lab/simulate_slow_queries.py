#!/usr/bin/env python3
"""
Simulate Slow Queries - Generate intentionally slow queries for testing.
Run this inside the mysql-lab container or point to mysql-lab:3306.
"""
import mysql.connector
import time
import random
from datetime import datetime

# MySQL connection config
MYSQL_CONFIG = {
    "host": "mysql-lab",
    "port": 3306,
    "user": "root",
    "password": "rootpassword",
    "database": "labdb"
}

# Slow query patterns (intentionally bad queries)
SLOW_QUERIES = [
    # Query 1: SELECT * without WHERE
    "SELECT * FROM users",
    
    # Query 2: SELECT * with ORDER BY (no index)
    "SELECT * FROM users ORDER BY created_at DESC",
    
    # Query 3: LIKE with leading wildcard
    "SELECT * FROM users WHERE email LIKE '%@example.com'",
    
    # Query 4: Join without indexes
    "SELECT u.*, o.* FROM users u JOIN orders o ON u.id = o.user_id WHERE o.status = 'pending'",
    
    # Query 5: Full table scan with calculation
    "SELECT user_id, SUM(total_amount) FROM orders GROUP BY user_id",
    
    # Query 6: IN clause with large list (simulated)
    "SELECT * FROM orders WHERE status IN ('pending', 'processing', 'shipped')",
    
    # Query 7: Multiple joins
    "SELECT u.full_name, COUNT(o.id) FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id",
    
    # Query 8: Complex WHERE without index
    "SELECT * FROM orders WHERE total_amount > 100 AND status = 'delivered' ORDER BY order_date DESC",
    
    # Query 9: LIKE pattern in middle
    "SELECT * FROM products WHERE name LIKE '%Product%'",
    
    # Query 10: Subquery without optimization
    "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders WHERE total_amount > 200)",
]


def run_slow_query(conn, query):
    """Execute a slow query and measure time."""
    try:
        cursor = conn.cursor()
        start = time.time()
        cursor.execute(query)
        rows = cursor.fetchall()
        duration = time.time() - start
        cursor.close()
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Executed: {query[:80]}... ({len(rows)} rows, {duration:.3f}s)")
        return True
    except Exception as e:
        print(f"❌ Error executing query: {e}")
        return False


def main():
    """Main simulation loop."""
    print("🔄 Starting slow query simulation...")
    print(f"📡 Connecting to MySQL at {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}...")
    
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        print("✅ Connected to MySQL")
        print("⏳ Running slow queries (Ctrl+C to stop)...\n")
        
        iteration = 0
        while True:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")
            
            # Run 3-5 random queries each iteration
            num_queries = random.randint(3, 5)
            queries = random.sample(SLOW_QUERIES, num_queries)
            
            for query in queries:
                run_slow_query(conn, query)
                time.sleep(random.uniform(0.5, 2.0))  # Random delay between queries
            
            # Wait before next iteration
            wait_time = random.randint(10, 30)
            print(f"\n⏸️  Waiting {wait_time}s before next iteration...")
            time.sleep(wait_time)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Simulation stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn:
            conn.close()
            print("👋 Disconnected from MySQL")


if __name__ == "__main__":
    main()
