"""
Query Analyzer - Combines rule-based analysis with AI suggestions.
Gathers comprehensive information: EXPLAIN, schema, indexes, statistics, locks.
"""
import mysql.connector
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from core.config import settings
from core.logger import setup_logger
from db.models import SlowQuery, AnalysisResult, get_db
from services.ai_llama_client import analyze_with_llama

logger = setup_logger(__name__, settings.log_level)


def get_mysql_connection(use_monitoring_user: bool = False):
    """
    Get MySQL connection with error handling.
    
    Args:
        use_monitoring_user: If True, uses dbpower_monitor user instead of configured user
    """
    try:
        if use_monitoring_user:
            # Use dedicated monitoring user for EXPLAIN and analysis
            params = {
                "host": settings.mysql_host,
                "port": settings.mysql_port,
                "user": settings.dbpower_user,
                "password": settings.dbpower_password,
            }
            if settings.mysql_db:
                params["database"] = settings.mysql_db
            return mysql.connector.connect(**params)
        else:
            return mysql.connector.connect(**settings.get_mysql_dict())
    except Exception as e:
        logger.error(f"Failed to connect to MySQL: {e}")
        return None


def extract_table_names(sql: str) -> List[str]:
    """Extract table names from SQL query."""
    tables = []
    # Simple regex for FROM and JOIN clauses
    patterns = [
        r"from\s+`?(\w+)`?",
        r"join\s+`?(\w+)`?",
        r"update\s+`?(\w+)`?",
        r"into\s+`?(\w+)`?"
    ]
    sql_lower = sql.lower()
    for pattern in patterns:
        matches = re.findall(pattern, sql_lower)
        tables.extend(matches)
    return list(set(tables))


def get_table_schema(table_name: str) -> Optional[Dict[str, Any]]:
    """
    Get table schema information including columns and their data types.
    """
    conn = get_mysql_connection(use_monitoring_user=True)
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get column information
        cursor.execute(f"DESCRIBE {table_name}")
        columns = cursor.fetchall()
        
        # Get table statistics
        cursor.execute(f"SHOW TABLE STATUS LIKE '{table_name}'")
        table_stats = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return {
            "columns": columns,
            "rows": table_stats.get('Rows', 0) if table_stats else 0,
            "avg_row_length": table_stats.get('Avg_row_length', 0) if table_stats else 0,
            "data_length": table_stats.get('Data_length', 0) if table_stats else 0,
            "index_length": table_stats.get('Index_length', 0) if table_stats else 0,
            "engine": table_stats.get('Engine', 'N/A') if table_stats else 'N/A'
        }
    except Exception as e:
        logger.warning(f"Could not get schema for table {table_name}: {e}")
        return None


def get_table_indexes(table_name: str) -> List[Dict[str, Any]]:
    """
    Get indexes on a table with cardinality information.
    """
    conn = get_mysql_connection(use_monitoring_user=True)
    if not conn:
        return []
    
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"SHOW INDEX FROM {table_name}")
        indexes = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Group by index name and calculate cardinality
        index_info = {}
        for idx in indexes:
            key_name = idx['Key_name']
            if key_name not in index_info:
                index_info[key_name] = {
                    "name": key_name,
                    "unique": idx['Non_unique'] == 0,
                    "columns": [],
                    "cardinality": idx.get('Cardinality', 0),
                    "type": idx.get('Index_type', 'BTREE')
                }
            index_info[key_name]["columns"].append(idx['Column_name'])
        
        return list(index_info.values())
    except Exception as e:
        logger.warning(f"Could not get indexes for table {table_name}: {e}")
        return []


def get_explain_plan(sql: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed EXPLAIN output for a query.
    Returns structured data with all EXPLAIN columns.
    """
    conn = get_mysql_connection(use_monitoring_user=True)
    if not conn:
        return None
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Run EXPLAIN
        cursor.execute(f"EXPLAIN {sql}")
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not rows:
            return None
        
        # Return full EXPLAIN details
        explain_details = []
        for row in rows:
            explain_details.append({
                "id": row.get('id'),
                "select_type": row.get('select_type'),
                "table": row.get('table'),
                "type": row.get('type'),  # Critical: ALL = full table scan
                "possible_keys": row.get('possible_keys'),
                "key": row.get('key'),  # NULL = no index used
                "key_len": row.get('key_len'),
                "ref": row.get('ref'),
                "rows": row.get('rows'),  # Number of rows examined
                "filtered": row.get('filtered'),  # Percentage of rows filtered
                "Extra": row.get('Extra')  # Using filesort, Using temporary, etc.
            })
        
        return {
            "rows": explain_details,
            "has_full_scan": any(r.get('type') == 'ALL' for r in explain_details),
            "uses_index": any(r.get('key') is not None for r in explain_details),
            "using_filesort": any('Using filesort' in str(r.get('Extra', '')) for r in explain_details),
            "using_temporary": any('Using temporary' in str(r.get('Extra', '')) for r in explain_details),
            "total_rows_examined": sum(r.get('rows', 0) for r in explain_details)
        }
        
    except Exception as e:
        logger.warning(f"Could not get EXPLAIN plan: {e}")
        return None


def check_locks_and_contention() -> Dict[str, Any]:
    """
    Check for locks and query contention.
    """
    conn = get_mysql_connection(use_monitoring_user=True)
    if not conn:
        return {"error": "Could not connect to MySQL"}
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get current process list
        cursor.execute("SHOW FULL PROCESSLIST")
        processes = cursor.fetchall()
        
        # Count queries by state
        states = {}
        for proc in processes:
            state = proc.get('State', 'Unknown')
            states[state] = states.get(state, 0) + 1
        
        # Check for locked queries
        locked_queries = [p for p in processes if 'lock' in str(p.get('State', '')).lower()]
        
        cursor.close()
        conn.close()
        
        return {
            "total_connections": len(processes),
            "states": states,
            "locked_queries_count": len(locked_queries),
            "has_contention": len(locked_queries) > 0
        }
    except Exception as e:
        logger.warning(f"Could not check locks: {e}")
        return {"error": str(e)}


def analyze_rules(sql: str, query_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rule-based query analysis.
    Detects common performance issues.
    
    Args:
        sql: SQL query text
        query_info: Query performance metrics
    
    Returns:
        Dictionary with issues and suggestions
    """
    issues = []
    suggested_indexes = []
    priority = "LOW"
    
    sql_lower = sql.lower()
    
    # Rule 1: SELECT *
    if "select *" in sql_lower:
        issues.append({
            "type": "SELECT_STAR",
            "severity": "MEDIUM",
            "message": "Query uses SELECT * which retrieves all columns. Specify only needed columns."
        })
        priority = "MEDIUM"
    
    # Rule 2: Missing WHERE clause
    if "where" not in sql_lower and ("select" in sql_lower or "update" in sql_lower or "delete" in sql_lower):
        issues.append({
            "type": "NO_WHERE_CLAUSE",
            "severity": "HIGH",
            "message": "Query has no WHERE clause. This performs a full table scan."
        })
        priority = "HIGH"
    
    # Rule 3: LIKE with leading wildcard
    if re.search(r"like\s+['\"]%", sql_lower):
        issues.append({
            "type": "LEADING_WILDCARD",
            "severity": "MEDIUM",
            "message": "LIKE pattern starts with wildcard (%). Index cannot be used."
        })
        if priority == "LOW":
            priority = "MEDIUM"
    
    # Rule 4: High rows examined vs rows sent ratio
    rows_examined = query_info.get("rows_examined", 0)
    rows_sent = query_info.get("rows_sent", 0)
    
    if rows_examined > 0 and rows_sent > 0:
        ratio = rows_examined / rows_sent
        if ratio > 100:
            issues.append({
                "type": "HIGH_EXAMINE_RATIO",
                "severity": "CRITICAL",
                "message": f"Query examines {rows_examined} rows but returns only {rows_sent}. Efficiency ratio: {ratio:.1f}:1"
            })
            priority = "CRITICAL"
        elif ratio > 10:
            issues.append({
                "type": "MODERATE_EXAMINE_RATIO",
                "severity": "HIGH",
                "message": f"Query examines {rows_examined} rows but returns only {rows_sent}. Consider adding indexes."
            })
            if priority not in ["CRITICAL"]:
                priority = "HIGH"
    
    # Rule 5: Slow query time
    query_time = query_info.get("query_time", 0)
    if query_time > 2.0:
        issues.append({
            "type": "SLOW_EXECUTION",
            "severity": "HIGH",
            "message": f"Query took {query_time:.2f}s to execute. This is significantly slow."
        })
        if priority == "LOW":
            priority = "HIGH"
    
    # Rule 6: Extract table names for index suggestions
    # Simple regex to find table names after FROM and JOIN
    table_pattern = r"(?:from|join)\s+`?(\w+)`?"
    tables = re.findall(table_pattern, sql_lower)
    
    if tables:
        for table in set(tables):
            # Suggest indexes on columns in WHERE clause
            where_match = re.search(r"where\s+(.+?)(?:order|group|limit|$)", sql_lower, re.DOTALL)
            if where_match:
                where_clause = where_match.group(1)
                # Extract column names (simple approach)
                columns = re.findall(r"(\w+)\s*(?:=|>|<|like|in)", where_clause)
                if columns:
                    for col in set(columns):
                        suggested_indexes.append({
                            "table": table,
                            "column": col,
                            "statement": f"CREATE INDEX idx_{table}_{col} ON {table}({col});"
                        })
    
    return {
        "issues": issues,
        "suggested_indexes": suggested_indexes,
        "priority": priority,
        "rules_checked": 6
    }


def analyze_query(query_id: int) -> Dict[str, Any]:
    """
    Perform comprehensive analysis on a slow query.
    Gathers: EXPLAIN plan, schema info, indexes, statistics, locks, AI analysis.
    
    Args:
        query_id: ID of the slow query to analyze
    
    Returns:
        Complete analysis result dictionary
    """
    start_time = datetime.utcnow()
    
    try:
        # Get the query from database
        db = next(get_db())
        slow_query = db.query(SlowQuery).filter(SlowQuery.id == query_id).first()
        
        if not slow_query:
            return {"error": f"Query with ID {query_id} not found"}
        
        logger.info(f"🔍 Starting comprehensive analysis for query {query_id}...")
        
        # Prepare query context
        query_info = {
            "query_time": slow_query.query_time,
            "rows_examined": slow_query.rows_examined,
            "rows_sent": slow_query.rows_sent,
            "database_name": slow_query.database_name
        }
        
        # ==== STEP 1: EXPLAIN Plan (Execution Plan) ====
        logger.info("📊 Getting EXPLAIN plan...")
        explain_plan = get_explain_plan(slow_query.sql_text)
        
        # ==== STEP 2: Schema and Index Information ====
        logger.info("🗄️  Gathering schema and index information...")
        tables = extract_table_names(slow_query.sql_text)
        schema_info = {}
        for table in tables:
            schema = get_table_schema(table)
            indexes = get_table_indexes(table)
            if schema or indexes:
                schema_info[table] = {
                    "schema": schema,
                    "indexes": indexes,
                    "has_indexes": len(indexes) > 0
                }
        
        # ==== STEP 3: Check for Locks and Contention ====
        logger.info("🔒 Checking for locks and contention...")
        lock_info = check_locks_and_contention()
        
        # ==== STEP 4: Rule-based Analysis ====
        logger.info("📋 Running rule-based analysis...")
        rule_analysis = analyze_rules(slow_query.sql_text, query_info)
        
        # ==== STEP 5: AI Analysis with LLaMA ====
        logger.info("🤖 Running AI analysis with LLaMA...")
        
        # Format EXPLAIN for AI (convert dict to readable string)
        explain_text = None
        if explain_plan and explain_plan.get('rows'):
            explain_text = "EXPLAIN Analysis:\n"
            for row in explain_plan['rows']:
                explain_text += f"  Table: {row['table']}\n"
                explain_text += f"  Type: {row['type']} {'⚠️ FULL TABLE SCAN' if row['type'] == 'ALL' else ''}\n"
                explain_text += f"  Possible Keys: {row['possible_keys'] or 'NONE'}\n"
                explain_text += f"  Key Used: {row['key'] or 'NONE ❌'}\n"
                explain_text += f"  Rows Examined: {row['rows']}\n"
                explain_text += f"  Filtered: {row['filtered']}%\n"
                explain_text += f"  Extra: {row['Extra']}\n"
                explain_text += "  ---\n"
            
            # Add summary
            explain_text += f"\nSummary:\n"
            explain_text += f"  Full Table Scan: {'YES ⚠️' if explain_plan.get('has_full_scan') else 'NO'}\n"
            explain_text += f"  Uses Index: {'YES' if explain_plan.get('uses_index') else 'NO ❌'}\n"
            explain_text += f"  Using Filesort: {'YES ⚠️' if explain_plan.get('using_filesort') else 'NO'}\n"
            explain_text += f"  Using Temporary: {'YES ⚠️' if explain_plan.get('using_temporary') else 'NO'}\n"
            explain_text += f"  Total Rows Examined: {explain_plan.get('total_rows_examined', 0)}\n"
        
        # Add schema context for AI
        context_with_schema = {
            **query_info,
            "tables": schema_info,
            "locks": lock_info
        }
        
        ai_analysis_text = analyze_with_llama(
            sql=slow_query.sql_text,
            explain_plan=explain_text,
            context=context_with_schema
        )
        
        # Calculate analysis duration
        analysis_duration = (datetime.utcnow() - start_time).total_seconds()
        
        # ==== STEP 6: Store Results ====
        logger.info("💾 Storing analysis results...")
        analysis_result = AnalysisResult(
            slow_query_id=query_id,
            issues_found=json.dumps(rule_analysis["issues"]),
            suggested_indexes=json.dumps(rule_analysis["suggested_indexes"]),
            improvement_priority=rule_analysis["priority"],
            ai_analysis=ai_analysis_text,
            ai_suggestions=ai_analysis_text,
            analyzed_at=datetime.utcnow(),
            analysis_duration=analysis_duration
        )
        
        db.add(analysis_result)
        
        # Update slow query as analyzed
        slow_query.analyzed = True
        slow_query.analysis_result_id = analysis_result.id
        
        db.commit()
        
        logger.info(f"✅ Query {query_id} analyzed successfully in {analysis_duration:.2f}s")
        
        return {
            "query_id": query_id,
            "analysis_id": analysis_result.id,
            "execution_plan": explain_plan,
            "schema_info": schema_info,
            "lock_info": lock_info,
            "rule_analysis": rule_analysis,
            "ai_analysis": ai_analysis_text,
            "analysis_duration": analysis_duration,
            "priority": rule_analysis["priority"],
            "summary": {
                "has_full_table_scan": explain_plan.get('has_full_scan', False) if explain_plan else False,
                "uses_index": explain_plan.get('uses_index', False) if explain_plan else False,
                "has_locks": lock_info.get('has_contention', False),
                "total_rows_examined": explain_plan.get('total_rows_examined', 0) if explain_plan else 0,
                "tables_analyzed": len(schema_info)
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error analyzing query {query_id}: {e}", exc_info=True)
        return {"error": str(e)}


def get_analysis_result(query_id: int) -> Optional[Dict[str, Any]]:
    """
    Get analysis result for a query.
    
    Args:
        query_id: ID of the slow query
    
    Returns:
        Analysis result dictionary or None if not found
    """
    try:
        db = next(get_db())
        slow_query = db.query(SlowQuery).filter(SlowQuery.id == query_id).first()
        
        if not slow_query or not slow_query.analyzed:
            return None
        
        analysis = db.query(AnalysisResult).filter(
            AnalysisResult.id == slow_query.analysis_result_id
        ).first()
        
        if not analysis:
            return None
        
        return {
            "query_id": query_id,
            "sql_text": slow_query.sql_text,
            "query_time": slow_query.query_time,
            "rows_examined": slow_query.rows_examined,
            "issues": json.loads(analysis.issues_found) if analysis.issues_found else [],
            "suggested_indexes": json.loads(analysis.suggested_indexes) if analysis.suggested_indexes else [],
            "priority": analysis.improvement_priority,
            "ai_analysis": analysis.ai_analysis,
            "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
            "analysis_duration": analysis.analysis_duration
        }
        
    except Exception as e:
        logger.error(f"Error getting analysis result: {e}")
        return None
