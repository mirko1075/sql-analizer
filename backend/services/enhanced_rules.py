"""
Enhanced Rule-Based Query Analyzer.
Comprehensive ruleset for detecting MySQL performance issues.
"""
import re
from typing import Dict, Any, List, Tuple


class QueryRuleAnalyzer:
    """Comprehensive rule-based query analyzer."""
    
    def __init__(self):
        self.issues = []
        self.suggested_indexes = []
        self.recommendations = []
        self.priority = "LOW"
        
    def analyze(self, sql: str, query_info: Dict[str, Any], explain_plan: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run all rules on a query.
        
        Args:
            sql: SQL query text
            query_info: Query performance metrics
            explain_plan: EXPLAIN plan analysis (optional)
            
        Returns:
            Dictionary with issues, suggestions, and priority
        """
        self.issues = []
        self.suggested_indexes = []
        self.recommendations = []
        self.priority = "LOW"
        
        sql_lower = sql.lower()
        
        # Run all rule checks
        self._check_select_star(sql_lower)
        self._check_missing_where(sql_lower)
        self._check_leading_wildcard(sql_lower)
        self._check_examine_ratio(query_info)
        self._check_query_time(query_info)
        self._check_or_conditions(sql_lower)
        self._check_function_on_column(sql_lower)
        self._check_implicit_conversion(sql_lower)
        self._check_subquery_in_select(sql_lower)
        self._check_distinct_usage(sql_lower)
        self._check_order_by_without_limit(sql_lower)
        self._check_union_all_vs_union(sql_lower)
        self._check_join_without_index(sql_lower, explain_plan)
        self._check_filesort(explain_plan)
        self._check_temporary_table(explain_plan)
        self._check_full_table_scan(explain_plan)
        self._check_large_offset(sql_lower)
        self._check_not_in_with_null(sql_lower)
        self._check_count_star_vs_count_column(sql_lower)
        self._check_nested_loops(explain_plan)
        self._check_lock_time(query_info)
        
        # Extract tables for index suggestions
        self._suggest_indexes(sql_lower)
        
        return {
            "issues": self.issues,
            "suggested_indexes": self.suggested_indexes,
            "recommendations": self.recommendations,
            "priority": self.priority,
            "rules_checked": 20
        }
    
    def _update_priority(self, severity: str):
        """Update overall priority based on issue severity."""
        priority_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if priority_order.index(severity) > priority_order.index(self.priority):
            self.priority = severity
    
    def _check_select_star(self, sql: str):
        """Rule 1: SELECT * anti-pattern."""
        if "select *" in sql or "select\t*" in sql or "select\n*" in sql:
            self.issues.append({
                "type": "SELECT_STAR",
                "severity": "MEDIUM",
                "message": "Using SELECT * retrieves all columns, wasting bandwidth and memory. Specify only needed columns.",
                "recommendation": "List specific columns: SELECT col1, col2, col3 FROM ..."
            })
            self._update_priority("MEDIUM")
    
    def _check_missing_where(self, sql: str):
        """Rule 2: Missing WHERE clause."""
        if "where" not in sql and any(op in sql for op in ["select", "update", "delete"]):
            # Exception: aggregations without WHERE might be intentional
            if "group by" not in sql and "count(*)" not in sql:
                self.issues.append({
                    "type": "NO_WHERE_CLAUSE",
                    "severity": "HIGH",
                    "message": "Query has no WHERE clause, performing full table scan on entire table.",
                    "recommendation": "Add WHERE clause to filter rows and use indexes."
                })
                self._update_priority("HIGH")
    
    def _check_leading_wildcard(self, sql: str):
        """Rule 3: LIKE with leading wildcard."""
        if re.search(r"like\s+['\"]%", sql):
            self.issues.append({
                "type": "LEADING_WILDCARD",
                "severity": "MEDIUM",
                "message": "LIKE pattern starts with wildcard (%). This prevents index usage.",
                "recommendation": "Avoid leading wildcards. Consider FULLTEXT index for text search."
            })
            self._update_priority("MEDIUM")
    
    def _check_examine_ratio(self, query_info: Dict[str, Any]):
        """Rule 4: High examine-to-sent ratio."""
        rows_examined = query_info.get("rows_examined", 0)
        rows_sent = query_info.get("rows_sent", 0)
        
        if rows_examined > 0 and rows_sent > 0:
            ratio = rows_examined / rows_sent
            if ratio > 1000:
                self.issues.append({
                    "type": "EXTREME_EXAMINE_RATIO",
                    "severity": "CRITICAL",
                    "message": f"Query examines {rows_examined:,} rows but returns only {rows_sent:,}. Ratio: {ratio:.0f}:1",
                    "recommendation": "Add indexes on WHERE clause columns to reduce rows examined."
                })
                self._update_priority("CRITICAL")
            elif ratio > 100:
                self.issues.append({
                    "type": "HIGH_EXAMINE_RATIO",
                    "severity": "HIGH",
                    "message": f"Query examines {rows_examined:,} rows but returns only {rows_sent:,}. Ratio: {ratio:.1f}:1",
                    "recommendation": "Consider adding composite indexes to improve selectivity."
                })
                self._update_priority("HIGH")
            elif ratio > 10:
                self.issues.append({
                    "type": "MODERATE_EXAMINE_RATIO",
                    "severity": "MEDIUM",
                    "message": f"Query examines {rows_examined:,} rows but returns only {rows_sent:,}. Ratio: {ratio:.1f}:1",
                    "recommendation": "Review indexes on filtered columns."
                })
                self._update_priority("MEDIUM")
    
    def _check_query_time(self, query_info: Dict[str, Any]):
        """Rule 5: Slow execution time."""
        query_time = query_info.get("query_time", 0)
        if query_time > 5.0:
            self.issues.append({
                "type": "VERY_SLOW_EXECUTION",
                "severity": "CRITICAL",
                "message": f"Query took {query_time:.2f}s to execute. This is extremely slow.",
                "recommendation": "Investigate missing indexes, table locks, or query design issues."
            })
            self._update_priority("CRITICAL")
        elif query_time > 2.0:
            self.issues.append({
                "type": "SLOW_EXECUTION",
                "severity": "HIGH",
                "message": f"Query took {query_time:.2f}s to execute. Target < 100ms for most queries.",
                "recommendation": "Review execution plan and consider query optimization."
            })
            self._update_priority("HIGH")
        elif query_time > 1.0:
            self.issues.append({
                "type": "MODERATE_SLOW_EXECUTION",
                "severity": "MEDIUM",
                "message": f"Query took {query_time:.2f}s. Could be optimized.",
                "recommendation": "Check for missing indexes or inefficient joins."
            })
            self._update_priority("MEDIUM")
    
    def _check_or_conditions(self, sql: str):
        """Rule 6: Multiple OR conditions."""
        or_count = len(re.findall(r'\bor\b', sql))
        if or_count >= 3:
            self.issues.append({
                "type": "MULTIPLE_OR_CONDITIONS",
                "severity": "MEDIUM",
                "message": f"Query has {or_count} OR conditions, which can prevent index usage.",
                "recommendation": "Consider using IN clause or UNION ALL instead of multiple ORs."
            })
            self._update_priority("MEDIUM")
    
    def _check_function_on_column(self, sql: str):
        """Rule 7: Functions on indexed columns."""
        # Check for functions in WHERE clause
        if re.search(r"where.*(?:upper|lower|date|year|month|substring|concat|trim)\s*\(", sql):
            self.issues.append({
                "type": "FUNCTION_ON_COLUMN",
                "severity": "HIGH",
                "message": "Using function on column in WHERE clause prevents index usage.",
                "recommendation": "Apply function to comparison value instead, or use computed/virtual columns."
            })
            self._update_priority("HIGH")
    
    def _check_implicit_conversion(self, sql: str):
        """Rule 8: Implicit type conversion."""
        # Detect quoted numbers or unquoted strings
        if re.search(r"where\s+\w+\s*=\s*['\"][0-9]+['\"]", sql):
            self.issues.append({
                "type": "IMPLICIT_CONVERSION",
                "severity": "MEDIUM",
                "message": "Comparing integer column to quoted number causes implicit type conversion.",
                "recommendation": "Remove quotes from numeric values: WHERE id = 123 (not '123')."
            })
            self._update_priority("MEDIUM")
    
    def _check_subquery_in_select(self, sql: str):
        """Rule 9: Correlated subquery in SELECT."""
        if re.search(r"select[^from]*\([^)]*select[^)]*\)", sql):
            self.issues.append({
                "type": "SUBQUERY_IN_SELECT",
                "severity": "HIGH",
                "message": "Subquery in SELECT list may execute once per row (N+1 problem).",
                "recommendation": "Convert to JOIN or use derived table."
            })
            self._update_priority("HIGH")
    
    def _check_distinct_usage(self, sql: str):
        """Rule 10: DISTINCT usage."""
        if "distinct" in sql and "join" in sql:
            self.issues.append({
                "type": "DISTINCT_WITH_JOIN",
                "severity": "MEDIUM",
                "message": "DISTINCT with JOIN may indicate incorrect join causing duplicates.",
                "recommendation": "Review join conditions. Fix join logic instead of using DISTINCT."
            })
            self._update_priority("MEDIUM")
    
    def _check_order_by_without_limit(self, sql: str):
        """Rule 11: ORDER BY without LIMIT."""
        if "order by" in sql and "limit" not in sql:
            self.issues.append({
                "type": "ORDER_BY_WITHOUT_LIMIT",
                "severity": "LOW",
                "message": "ORDER BY without LIMIT sorts entire result set.",
                "recommendation": "Add LIMIT if you don't need all rows, or ensure index supports ORDER BY."
            })
            self._update_priority("LOW")
    
    def _check_union_all_vs_union(self, sql: str):
        """Rule 12: UNION vs UNION ALL."""
        if sql.count("union") > sql.count("union all"):
            self.issues.append({
                "type": "UNION_WITHOUT_ALL",
                "severity": "MEDIUM",
                "message": "UNION removes duplicates (expensive). Use UNION ALL if duplicates are OK.",
                "recommendation": "Replace UNION with UNION ALL if duplicates don't matter."
            })
            self._update_priority("MEDIUM")
    
    def _check_join_without_index(self, sql: str, explain_plan: Dict[str, Any]):
        """Rule 13: JOIN without proper indexes."""
        if explain_plan and "join" in sql:
            for row in explain_plan.get("rows", []):
                if row.get("key") is None and row.get("type") in ["ALL", "index"]:
                    self.issues.append({
                        "type": "JOIN_WITHOUT_INDEX",
                        "severity": "HIGH",
                        "message": f"Table {row.get('table')} in JOIN has no index (type: {row.get('type')}).",
                        "recommendation": "Add index on join column to avoid full table scan."
                    })
                    self._update_priority("HIGH")
    
    def _check_filesort(self, explain_plan: Dict[str, Any]):
        """Rule 14: Using filesort."""
        if explain_plan and explain_plan.get("using_filesort"):
            self.issues.append({
                "type": "USING_FILESORT",
                "severity": "MEDIUM",
                "message": "Query requires filesort operation (sorts data on disk/memory).",
                "recommendation": "Add index that covers ORDER BY columns in same order."
            })
            self._update_priority("MEDIUM")
    
    def _check_temporary_table(self, explain_plan: Dict[str, Any]):
        """Rule 15: Using temporary table."""
        if explain_plan and explain_plan.get("using_temporary"):
            self.issues.append({
                "type": "USING_TEMPORARY",
                "severity": "MEDIUM",
                "message": "Query creates temporary table (expensive for large result sets).",
                "recommendation": "Review GROUP BY, DISTINCT, or UNION usage. Add appropriate indexes."
            })
            self._update_priority("MEDIUM")
    
    def _check_full_table_scan(self, explain_plan: Dict[str, Any]):
        """Rule 16: Full table scan."""
        if explain_plan and explain_plan.get("has_full_scan"):
            rows = explain_plan.get("total_rows_examined", 0)
            if rows > 10000:
                self.issues.append({
                    "type": "FULL_TABLE_SCAN_LARGE",
                    "severity": "CRITICAL",
                    "message": f"Full table scan on {rows:,} rows. Extremely inefficient.",
                    "recommendation": "Add index on WHERE/JOIN columns immediately."
                })
                self._update_priority("CRITICAL")
            elif rows > 1000:
                self.issues.append({
                    "type": "FULL_TABLE_SCAN",
                    "severity": "HIGH",
                    "message": f"Full table scan on {rows:,} rows.",
                    "recommendation": "Add index on filtered columns."
                })
                self._update_priority("HIGH")
    
    def _check_large_offset(self, sql: str):
        """Rule 17: Large OFFSET in pagination."""
        offset_match = re.search(r"offset\s+(\d+)", sql)
        if offset_match:
            offset = int(offset_match.group(1))
            if offset > 10000:
                self.issues.append({
                    "type": "LARGE_OFFSET",
                    "severity": "HIGH",
                    "message": f"Large OFFSET {offset:,} causes MySQL to skip many rows inefficiently.",
                    "recommendation": "Use 'seek method' pagination (WHERE id > last_id) instead of OFFSET."
                })
                self._update_priority("HIGH")
            elif offset > 1000:
                self.issues.append({
                    "type": "MODERATE_OFFSET",
                    "severity": "MEDIUM",
                    "message": f"OFFSET {offset:,} may be slow. Consider seek method.",
                    "recommendation": "For deep pagination, use WHERE id > last_id LIMIT N."
                })
                self._update_priority("MEDIUM")
    
    def _check_not_in_with_null(self, sql: str):
        """Rule 18: NOT IN with potential NULL values."""
        if "not in" in sql:
            self.issues.append({
                "type": "NOT_IN_CLAUSE",
                "severity": "LOW",
                "message": "NOT IN can cause issues with NULL values and may be slower than NOT EXISTS.",
                "recommendation": "Use NOT EXISTS or LEFT JOIN...WHERE NULL instead."
            })
            self._update_priority("LOW")
    
    def _check_count_star_vs_count_column(self, sql: str):
        """Rule 19: COUNT(column) vs COUNT(*)."""
        if re.search(r"count\s*\(\s*\w+\s*\)", sql) and "count(*)" not in sql:
            self.recommendations.append({
                "type": "COUNT_USAGE",
                "message": "Using COUNT(column) excludes NULLs. Use COUNT(*) if you want all rows.",
                "severity": "INFO"
            })
    
    def _check_nested_loops(self, explain_plan: Dict[str, Any]):
        """Rule 20: Inefficient nested loop joins."""
        if explain_plan:
            rows_list = [row.get("rows", 0) for row in explain_plan.get("rows", [])]
            if len(rows_list) >= 2:
                total_loop_cost = 1
                for rows in rows_list:
                    total_loop_cost *= rows
                if total_loop_cost > 1000000:
                    self.issues.append({
                        "type": "INEFFICIENT_NESTED_LOOPS",
                        "severity": "HIGH",
                        "message": f"Nested loop join estimated to process {total_loop_cost:,} row combinations.",
                        "recommendation": "Add indexes on join columns to reduce nested loop cost."
                    })
                    self._update_priority("HIGH")
    
    def _check_lock_time(self, query_info: Dict[str, Any]):
        """Rule 21: High lock time."""
        lock_time = query_info.get("lock_time", 0)
        query_time = query_info.get("query_time", 1)
        
        if lock_time > 1.0:
            self.issues.append({
                "type": "HIGH_LOCK_TIME",
                "severity": "HIGH",
                "message": f"Query spent {lock_time:.2f}s waiting for locks.",
                "recommendation": "Investigate table locking, concurrent writes, or transaction issues."
            })
            self._update_priority("HIGH")
        elif lock_time > 0.1 and (lock_time / query_time) > 0.3:
            self.issues.append({
                "type": "SIGNIFICANT_LOCK_TIME",
                "severity": "MEDIUM",
                "message": f"Lock time {lock_time:.2f}s is {(lock_time/query_time)*100:.0f}% of query time.",
                "recommendation": "Consider using READ COMMITTED isolation or optimize concurrent access."
            })
            self._update_priority("MEDIUM")
    
    def _suggest_indexes(self, sql: str):
        """Extract tables and suggest indexes based on WHERE clause."""
        # Find tables
        table_pattern = r"(?:from|join)\s+`?(\w+)`?"
        tables = re.findall(table_pattern, sql)
        
        if not tables:
            return
        
        # Find WHERE clause
        where_match = re.search(r"where\s+(.+?)(?:group|order|limit|$)", sql, re.DOTALL)
        if not where_match:
            return
        
        where_clause = where_match.group(1)
        
        # Extract columns from WHERE conditions
        # Match: column = value, column > value, column LIKE, column IN, etc.
        column_pattern = r"(\w+)\s*(?:=|>|<|>=|<=|!=|<>|like|in|between)"
        columns = re.findall(column_pattern, where_clause)
        
        # Extract columns from JOIN ON conditions
        join_pattern = r"on\s+(?:\w+\.)?(\w+)\s*=\s*(?:\w+\.)?(\w+)"
        join_columns = re.findall(join_pattern, sql)
        
        # Combine all column suggestions
        all_columns = set(columns)
        for col1, col2 in join_columns:
            all_columns.add(col1)
            all_columns.add(col2)
        
        # Generate index suggestions for each table
        for table in set(tables):
            table_columns = [col for col in all_columns if col not in ['and', 'or', 'not', 'null']]
            
            for col in table_columns:
                self.suggested_indexes.append({
                    "table": table,
                    "column": col,
                    "statement": f"CREATE INDEX idx_{table}_{col} ON {table}({col});",
                    "reason": "Column used in WHERE or JOIN condition"
                })
            
            # Suggest composite index if multiple columns
            if len(table_columns) > 1:
                cols_str = ", ".join(table_columns[:3])  # Max 3 columns
                idx_name = "_".join(table_columns[:3])
                self.suggested_indexes.append({
                    "table": table,
                    "columns": table_columns[:3],
                    "statement": f"CREATE INDEX idx_{table}_{idx_name} ON {table}({cols_str});",
                    "reason": "Composite index for multiple filter conditions"
                })
