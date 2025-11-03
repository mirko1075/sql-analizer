"""
Query Analyzer - Combines rule-based analysis with AI suggestions.
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


def get_explain_plan(sql: str) -> Optional[str]:
    """
    Get EXPLAIN output for a query.
    
    Args:
        sql: SQL query text
    
    Returns:
        EXPLAIN plan as formatted string or None if error
    """
    try:
        conn = mysql.connector.connect(**settings.get_mysql_dict())
        cursor = conn.cursor(dictionary=True)
        
        # Run EXPLAIN
        cursor.execute(f"EXPLAIN {sql}")
        rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not rows:
            return None
        
        # Format EXPLAIN output
        explain_text = "EXPLAIN output:\n"
        for row in rows:
            explain_text += f"  Type: {row.get('type', 'N/A')}\n"
            explain_text += f"  Possible Keys: {row.get('possible_keys', 'NONE')}\n"
            explain_text += f"  Key: {row.get('key', 'NONE')}\n"
            explain_text += f"  Rows: {row.get('rows', 'N/A')}\n"
            explain_text += f"  Extra: {row.get('Extra', 'N/A')}\n"
            explain_text += "  ---\n"
        
        return explain_text
        
    except Exception as e:
        logger.warning(f"Could not get EXPLAIN plan: {e}")
        return None


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
    Perform full analysis on a slow query (rules + AI).
    
    Args:
        query_id: ID of the slow query to analyze
    
    Returns:
        Analysis result dictionary
    """
    start_time = datetime.utcnow()
    
    try:
        # Get the query from database
        db = next(get_db())
        slow_query = db.query(SlowQuery).filter(SlowQuery.id == query_id).first()
        
        if not slow_query:
            return {"error": f"Query with ID {query_id} not found"}
        
        logger.info(f"Analyzing query {query_id}...")
        
        # Prepare query context
        query_info = {
            "query_time": slow_query.query_time,
            "rows_examined": slow_query.rows_examined,
            "rows_sent": slow_query.rows_sent,
            "database_name": slow_query.database_name
        }
        
        # Step 1: Get EXPLAIN plan
        explain_plan = get_explain_plan(slow_query.sql_text)
        
        # Step 2: Rule-based analysis
        rule_analysis = analyze_rules(slow_query.sql_text, query_info)
        
        # Step 3: AI analysis with LLaMA
        ai_analysis_text = analyze_with_llama(
            sql=slow_query.sql_text,
            explain_plan=explain_plan,
            context=query_info
        )
        
        # Calculate analysis duration
        analysis_duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Store analysis result
        analysis_result = AnalysisResult(
            slow_query_id=query_id,
            issues_found=json.dumps(rule_analysis["issues"]),
            suggested_indexes=json.dumps(rule_analysis["suggested_indexes"]),
            improvement_priority=rule_analysis["priority"],
            ai_analysis=ai_analysis_text,
            ai_suggestions=ai_analysis_text,  # For simplicity, same as ai_analysis
            analyzed_at=datetime.utcnow(),
            analysis_duration=analysis_duration
        )
        
        db.add(analysis_result)
        
        # Update slow query as analyzed
        slow_query.analyzed = True
        slow_query.analysis_result_id = analysis_result.id
        
        db.commit()
        
        logger.info(f"Query {query_id} analyzed successfully in {analysis_duration:.2f}s")
        
        return {
            "query_id": query_id,
            "analysis_id": analysis_result.id,
            "rule_analysis": rule_analysis,
            "ai_analysis": ai_analysis_text,
            "explain_plan": explain_plan,
            "analysis_duration": analysis_duration,
            "priority": rule_analysis["priority"]
        }
        
    except Exception as e:
        logger.error(f"Error analyzing query {query_id}: {e}", exc_info=True)
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
