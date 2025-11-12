"""
Rule-based query analyzer for multi-tenant version.
Provides immediate analysis without requiring database connection.
"""
import re
from typing import List, Dict, Any


def analyze_query_rules(sql: str, query_time: float = 0, rows_examined: int = 0, rows_sent: int = 0) -> Dict[str, Any]:
    """
    Rule-based query analysis that doesn't require database connection.
    Returns suggestions and issues based on SQL text and metrics.

    Args:
        sql: SQL query text
        query_time: Query execution time in seconds
        rows_examined: Number of rows examined
        rows_sent: Number of rows returned

    Returns:
        Dictionary with problem, root_cause, suggestions, and improvement_level
    """
    suggestions = []
    issues = []
    improvement_level = "LOW"

    sql_lower = sql.lower().strip()

    # Rule 1: SELECT *
    if "select *" in sql_lower or "select * " in sql_lower:
        suggestions.append({
            "type": "BEST_PRACTICE",
            "priority": "MEDIUM",
            "description": "Avoid SELECT * - Specify only needed columns",
            "rationale": "Selecting all columns increases network traffic and memory usage. Only fetch the data you need.",
            "sql": None,
            "estimated_impact": "10-30% reduction in query time and memory usage"
        })
        issues.append("Uses SELECT * which retrieves all columns unnecessarily")
        if improvement_level == "LOW":
            improvement_level = "MEDIUM"

    # Rule 2: Missing WHERE clause
    has_where = "where" in sql_lower
    is_select = sql_lower.startswith("select")
    is_update = sql_lower.startswith("update")
    is_delete = sql_lower.startswith("delete")

    if not has_where and (is_select or is_update or is_delete):
        suggestions.append({
            "type": "CRITICAL",
            "priority": "CRITICAL",
            "description": "Missing WHERE clause - Full table scan detected",
            "rationale": "Without WHERE clause, the query scans the entire table. This is very expensive on large tables.",
            "sql": None,
            "estimated_impact": "70-90% reduction in query time with proper WHERE clause"
        })
        issues.append("No WHERE clause - performs full table scan")
        improvement_level = "CRITICAL"

    # Rule 3: LIKE with leading wildcard
    if re.search(r"like\s+['\"]%", sql_lower):
        suggestions.append({
            "type": "OPTIMIZATION",
            "priority": "MEDIUM",
            "description": "LIKE pattern starts with wildcard (%) - Index cannot be used",
            "rationale": "Leading wildcards prevent index usage. Consider full-text search or restructuring the query.",
            "sql": None,
            "estimated_impact": "40-60% improvement if restructured"
        })
        issues.append("LIKE pattern starts with % preventing index usage")
        if improvement_level == "LOW":
            improvement_level = "MEDIUM"

    # Rule 4: High rows examined vs rows sent ratio
    if rows_examined > 0 and rows_sent > 0:
        ratio = rows_examined / rows_sent
        if ratio > 100:
            suggestions.append({
                "type": "INDEX",
                "priority": "CRITICAL",
                "description": f"Very inefficient query - Examines {rows_examined:,} rows but returns only {rows_sent:,}",
                "rationale": f"Efficiency ratio of {ratio:.1f}:1 indicates missing indexes. Query scans too many unnecessary rows.",
                "sql": "-- Add indexes on columns used in WHERE, JOIN, and ORDER BY clauses",
                "estimated_impact": "80-95% reduction in rows examined with proper indexes"
            })
            issues.append(f"Examines {rows_examined:,} rows but returns only {rows_sent:,} (ratio: {ratio:.1f}:1)")
            improvement_level = "CRITICAL"
        elif ratio > 10:
            suggestions.append({
                "type": "INDEX",
                "priority": "HIGH",
                "description": f"Inefficient query - Examines {rows_examined:,} rows but returns only {rows_sent:,}",
                "rationale": f"Efficiency ratio of {ratio:.1f}:1 suggests missing or unused indexes.",
                "sql": "-- Consider adding indexes on filter columns",
                "estimated_impact": "50-70% reduction in rows examined"
            })
            issues.append(f"Examines {rows_examined:,} rows but returns only {rows_sent:,}")
            if improvement_level not in ["CRITICAL"]:
                improvement_level = "HIGH"
    elif rows_examined > 10000:
        suggestions.append({
            "type": "REVIEW",
            "priority": "MEDIUM",
            "description": f"Large number of rows examined: {rows_examined:,}",
            "rationale": "High row examination count indicates potential for optimization through better indexing.",
            "sql": None,
            "estimated_impact": "Varies depending on index optimization"
        })
        if improvement_level == "LOW":
            improvement_level = "MEDIUM"

    # Rule 5: Slow query time
    if query_time > 5.0:
        suggestions.append({
            "type": "MONITORING",
            "priority": "CRITICAL",
            "description": f"Very slow query execution: {query_time:.2f}s",
            "rationale": "Query takes longer than 5 seconds. This severely impacts user experience and database load.",
            "sql": None,
            "estimated_impact": "Requires investigation - potential 60-90% improvement"
        })
        issues.append(f"Query took {query_time:.2f}s - very slow execution")
        improvement_level = "CRITICAL"
    elif query_time > 2.0:
        suggestions.append({
            "type": "MONITORING",
            "priority": "HIGH",
            "description": f"Slow query execution: {query_time:.2f}s",
            "rationale": "Query exceeds 2 second threshold. Consider optimization to improve performance.",
            "sql": None,
            "estimated_impact": "30-50% improvement possible"
        })
        issues.append(f"Query took {query_time:.2f}s")
        if improvement_level not in ["CRITICAL"]:
            improvement_level = "HIGH"

    # Rule 6: Subqueries
    if "select" in sql_lower and sql_lower.count("select") > 1:
        if " in (select" in sql_lower:
            suggestions.append({
                "type": "OPTIMIZATION",
                "priority": "MEDIUM",
                "description": "Subquery in IN clause detected",
                "rationale": "IN (SELECT...) can often be replaced with JOIN for better performance.",
                "sql": "-- Consider replacing: WHERE col IN (SELECT...) with: JOIN table ON condition",
                "estimated_impact": "20-40% improvement by using JOIN instead"
            })
            if improvement_level == "LOW":
                improvement_level = "MEDIUM"

    # Rule 7: OR conditions
    if " or " in sql_lower and "where" in sql_lower:
        suggestions.append({
            "type": "OPTIMIZATION",
            "priority": "MEDIUM",
            "description": "Multiple OR conditions detected",
            "rationale": "OR conditions can prevent index usage. Consider using UNION or IN clause instead.",
            "sql": "-- Consider replacing: WHERE a=1 OR b=2 with: WHERE a=1 UNION WHERE b=2",
            "estimated_impact": "15-30% improvement in some cases"
        })
        if improvement_level == "LOW":
            improvement_level = "MEDIUM"

    # Rule 8: Functions on indexed columns
    function_pattern = r"where\s+\w+\s*\(.*?\)\s*(?:=|>|<|like)"
    if re.search(function_pattern, sql_lower):
        suggestions.append({
            "type": "OPTIMIZATION",
            "priority": "HIGH",
            "description": "Function applied to column in WHERE clause",
            "rationale": "Functions on columns (e.g., WHERE LOWER(name) = 'test') prevent index usage.",
            "sql": "-- Avoid: WHERE LOWER(col) = 'value'\n-- Prefer: WHERE col = 'value' (use stored computed column if needed)",
            "estimated_impact": "50-70% improvement by avoiding functions"
        })
        if improvement_level == "LOW":
            improvement_level = "HIGH"

    # Rule 9: ORDER BY without LIMIT
    has_order_by = "order by" in sql_lower
    has_limit = "limit" in sql_lower

    if has_order_by and not has_limit and is_select:
        suggestions.append({
            "type": "BEST_PRACTICE",
            "priority": "MEDIUM",
            "description": "ORDER BY without LIMIT - Sorts entire result set",
            "rationale": "Sorting large result sets is expensive. If you don't need all rows, add LIMIT.",
            "sql": "-- Add LIMIT clause if you don't need all results",
            "estimated_impact": "Varies - can be significant for large result sets"
        })
        if improvement_level == "LOW":
            improvement_level = "MEDIUM"

    # Rule 10: DISTINCT usage
    if "distinct" in sql_lower:
        suggestions.append({
            "type": "REVIEW",
            "priority": "MEDIUM",
            "description": "DISTINCT clause detected",
            "rationale": "DISTINCT requires sorting/grouping. Verify if it's truly needed or if the query can be restructured.",
            "sql": None,
            "estimated_impact": "10-30% if DISTINCT can be avoided"
        })
        if improvement_level == "LOW":
            improvement_level = "MEDIUM"

    # Generate problem summary
    if not issues:
        problem = "Query appears to follow basic best practices"
        root_cause = "No critical issues detected in static analysis"
    else:
        problem = "; ".join(issues[:3])  # Top 3 issues
        root_cause = f"Found {len(issues)} issue(s) through rule-based analysis"

    # Estimate speedup
    estimated_speedup_map = {
        "CRITICAL": "5-10x",
        "HIGH": "2-5x",
        "MEDIUM": "1.5-2x",
        "LOW": "1.1-1.5x"
    }

    return {
        "problem": problem,
        "root_cause": root_cause,
        "suggestions": suggestions,
        "improvement_level": improvement_level,
        "estimated_speedup": estimated_speedup_map.get(improvement_level, "1.1-1.5x"),
        "analyzer_version": "1.0.0-multitenant-rule-based",
        "analysis_method": "rule_based",
        "confidence_score": 0.75,  # Rule-based has lower confidence than AI
        "rules_checked": 10,
        "issues_found": len(issues)
    }
