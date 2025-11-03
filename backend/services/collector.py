"""
MySQL Slow Query Collector.
Reads from mysql.slow_log table and stores in local database.
"""
import mysql.connector
import hashlib
from datetime import datetime
from typing import List, Dict, Any

from backend.core.config import settings
from backend.core.logger import setup_logger
from backend.db.models import SlowQuery, get_db

logger = setup_logger(__name__, settings.log_level)


def generate_fingerprint(sql: str) -> str:
    """
    Generate a fingerprint (hash) for SQL query.
    Used to group similar queries together.
    
    Args:
        sql: SQL query text
    
    Returns:
        MD5 hash of normalized query
    """
    # Simple normalization: lowercase and remove extra spaces
    normalized = ' '.join(sql.lower().split())
    return hashlib.md5(normalized.encode()).hexdigest()


def collect_slow_queries() -> int:
    """
    Collect slow queries from MySQL slow_log table.
    
    Returns:
        Number of new queries collected
    """
    logger.info("Starting slow query collection from MySQL...")
    
    try:
        # Connect to MySQL
        conn = mysql.connector.connect(**settings.get_mysql_dict())
        cursor = conn.cursor(dictionary=True)
        
        # Get the latest collected timestamp from our database
        db = next(get_db())
        last_query = db.query(SlowQuery).order_by(SlowQuery.start_time.desc()).first()
        last_timestamp = last_query.start_time if last_query else datetime(2020, 1, 1)
        
        logger.info(f"Collecting queries since: {last_timestamp}")
        
        # Query slow_log for new entries
        query = """
        SELECT 
            start_time,
            user_host,
            query_time,
            lock_time,
            rows_sent,
            rows_examined,
            db,
            CONVERT(sql_text USING utf8) as sql_text
        FROM mysql.slow_log
        WHERE start_time > %s
        ORDER BY start_time DESC
        LIMIT 100
        """
        
        cursor.execute(query, (last_timestamp,))
        rows = cursor.fetchall()
        
        logger.info(f"Found {len(rows)} new slow queries")
        
        # Store in local database
        collected_count = 0
        for row in rows:
            sql_text = row['sql_text']
            if not sql_text or len(sql_text.strip()) == 0:
                continue
            
            slow_query = SlowQuery(
                sql_text=sql_text,
                sql_fingerprint=generate_fingerprint(sql_text),
                query_time=float(row['query_time']),
                lock_time=float(row['lock_time']) if row['lock_time'] else 0.0,
                rows_sent=int(row['rows_sent']) if row['rows_sent'] else 0,
                rows_examined=int(row['rows_examined']) if row['rows_examined'] else 0,
                database_name=row['db'],
                user_host=row['user_host'],
                start_time=row['start_time'],
                collected_at=datetime.utcnow()
            )
            
            db.add(slow_query)
            collected_count += 1
        
        db.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Successfully collected {collected_count} slow queries")
        return collected_count
        
    except Exception as e:
        logger.error(f"Error collecting slow queries: {e}", exc_info=True)
        return 0


def get_pending_queries(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get slow queries that haven't been analyzed yet.
    
    Args:
        limit: Maximum number of queries to return
    
    Returns:
        List of slow query dictionaries
    """
    db = next(get_db())
    queries = db.query(SlowQuery).filter(SlowQuery.analyzed == False).limit(limit).all()
    
    return [
        {
            "id": q.id,
            "sql_text": q.sql_text,
            "query_time": q.query_time,
            "rows_examined": q.rows_examined,
            "database_name": q.database_name,
            "start_time": q.start_time.isoformat() if q.start_time else None
        }
        for q in queries
    ]


def get_all_queries(limit: int = 50, analyzed_only: bool = False) -> List[Dict[str, Any]]:
    """
    Get all collected queries.
    
    Args:
        limit: Maximum number of queries to return
        analyzed_only: If True, return only analyzed queries
    
    Returns:
        List of slow query dictionaries
    """
    db = next(get_db())
    query = db.query(SlowQuery)
    
    if analyzed_only:
        query = query.filter(SlowQuery.analyzed == True)
    
    queries = query.order_by(SlowQuery.query_time.desc()).limit(limit).all()
    
    return [
        {
            "id": q.id,
            "sql_text": q.sql_text[:200] + "..." if len(q.sql_text) > 200 else q.sql_text,
            "query_time": q.query_time,
            "rows_examined": q.rows_examined,
            "database_name": q.database_name,
            "analyzed": q.analyzed,
            "analysis_result_id": q.analysis_result_id,
            "start_time": q.start_time.isoformat() if q.start_time else None
        }
        for q in queries
    ]
