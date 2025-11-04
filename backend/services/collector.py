"""
MySQL Slow Query Collector.
Reads from mysql.slow_log table and stores in local database.
"""
import mysql.connector
import hashlib
from datetime import datetime
from typing import List, Dict, Any

from core.config import settings
from core.logger import setup_logger
from db.models import SlowQuery, get_db

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


def collect_slow_queries() -> Dict[str, Any]:
    """
    Collect slow queries from MySQL slow_log table.
    
    Returns:
        Dictionary with collection result
    """
    collection_start = datetime.utcnow()
    logger.info("🔍 Starting slow query collection from MySQL...")
    
    try:
        # Connect to MySQL
        logger.info(f"📡 DB Poll | Connecting to MySQL at {settings.mysql_host}:{settings.mysql_port}")
        conn = mysql.connector.connect(**settings.get_mysql_dict())
        cursor = conn.cursor(dictionary=True)
        
        # Get the latest collected timestamp from our database
        db = next(get_db())
        last_query = db.query(SlowQuery).order_by(SlowQuery.start_time.desc()).first()
        last_timestamp = last_query.start_time if last_query else datetime(2020, 1, 1)
        
        logger.info(f"📅 Collecting queries since: {last_timestamp}")
        
        # Query slow_log for new entries, excluding DBPower monitoring user, SLEEP queries, and self-referencing queries
        # We collect application queries but exclude the collector's own queries to slow_log
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
          AND user_host NOT LIKE %s
          AND sql_text NOT LIKE 'SELECT SLEEP%%'
          AND sql_text NOT LIKE '%%FROM mysql.slow_log%%'
          AND sql_text NOT LIKE '%%mysql.slow_log%%'
        ORDER BY query_time DESC
        LIMIT 100
        """
        
        # Filter pattern for DBPower user (matches user_host like 'dbpower_monitor@%')
        dbpower_filter = f"{settings.dbpower_user}@%"
        
        logger.info(f"📊 DB Poll | Query: SELECT FROM mysql.slow_log WHERE start_time > {last_timestamp} AND user_host NOT LIKE '{dbpower_filter}' AND sql_text NOT LIKE 'SELECT SLEEP%' AND sql_text NOT LIKE '%FROM mysql.slow_log%' ORDER BY query_time DESC LIMIT 100")
        logger.info(f"🔍 Executing query with parameters: last_timestamp={last_timestamp}, dbpower_filter={dbpower_filter}")
        cursor.execute(query, (last_timestamp, dbpower_filter))
        rows = cursor.fetchall()
        
        poll_duration = (datetime.utcnow() - collection_start).total_seconds()
        logger.info(f"✅ DB Poll Complete | Found: {len(rows)} queries | Duration: {poll_duration:.3f}s")
        
        if len(rows) == 0:
            logger.info(f"⚠️  No rows returned. Testing if any queries exist in slow_log...")
            cursor.execute("SELECT COUNT(*) as cnt FROM mysql.slow_log")
            total_rows = cursor.fetchone()
            logger.info(f"   Total rows in slow_log: {total_rows['cnt'] if total_rows else 0}")
        
        # Store in local database
        collected_count = 0
        skipped_duplicates = 0
        
        for row in rows:
            sql_text = row['sql_text']
            if not sql_text or len(sql_text.strip()) == 0:
                continue
            
            # Convert timedelta to float seconds
            query_time_seconds = row['query_time'].total_seconds() if hasattr(row['query_time'], 'total_seconds') else float(row['query_time'])
            lock_time_seconds = row['lock_time'].total_seconds() if (row['lock_time'] and hasattr(row['lock_time'], 'total_seconds')) else (float(row['lock_time']) if row['lock_time'] else 0.0)
            
            fingerprint = generate_fingerprint(sql_text)
            
            # Check if this query already exists (same fingerprint and start_time)
            existing = db.query(SlowQuery).filter(
                SlowQuery.sql_fingerprint == fingerprint,
                SlowQuery.start_time == row['start_time']
            ).first()
            
            if existing:
                skipped_duplicates += 1
                logger.debug(f"Skipping duplicate query: {fingerprint[:8]}... at {row['start_time']}")
                continue
            
            slow_query = SlowQuery(
                sql_text=sql_text,
                sql_fingerprint=fingerprint,
                query_time=query_time_seconds,
                lock_time=lock_time_seconds,
                rows_sent=int(row['rows_sent']) if row['rows_sent'] else 0,
                rows_examined=int(row['rows_examined']) if row['rows_examined'] else 0,
                database_name=row['db'],
                user_host=row['user_host'],
                start_time=row['start_time'],
                collected_at=datetime.utcnow(),
                status='pending'  # New queries start as pending
            )
            
            db.add(slow_query)
            collected_count += 1
        
        db.commit()
        cursor.close()
        conn.close()
        
        total_duration = (datetime.utcnow() - collection_start).total_seconds()
        logger.info(
            f"✅ Collection Complete | "
            f"Collected: {collected_count} | "
            f"Skipped: {skipped_duplicates} | "
            f"Total Duration: {total_duration:.3f}s"
        )
        return {
            "collected": collected_count,
            "skipped_duplicates": skipped_duplicates,
            "message": f"Successfully collected {collected_count} slow queries"
        }
        
    except Exception as e:
        logger.error(f"Error collecting slow queries: {e}", exc_info=True)
        return {
            "collected": 0,
            "message": f"Error: {str(e)}"
        }


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
