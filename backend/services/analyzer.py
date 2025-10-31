"""
Query analyzer service.

Analyzes slow queries using rule-based patterns and AI assistance
to generate optimization suggestions.
"""
import json
import binascii
from datetime import datetime
from typing import Dict, Any, List, Optional
from decimal import Decimal

from backend.core.config import settings
from backend.core.logger import get_logger
from backend.db.session import get_db_context
from backend.db.models import SlowQueryRaw, AnalysisResult
from backend.services.fingerprint import extract_tables_from_query

logger = get_logger(__name__)


def decode_hex_sql(sql: str) -> str:
    """
    Decode hex-encoded SQL string if needed.

    Args:
        sql: SQL string (may be hex-encoded with \\x prefix)

    Returns:
        Decoded SQL string
    """
    if not sql or not isinstance(sql, str):
        return sql

    # Check if string is hex-encoded (starts with \x)
    if sql.startswith('\\x'):
        try:
            # Remove \x prefix and decode hex
            hex_string = sql[2:]
            decoded_bytes = binascii.unhexlify(hex_string)
            return decoded_bytes.decode('utf-8')
        except Exception as e:
            logger.warning(f"Failed to decode hex SQL: {e}")
            return sql  # Return original if decoding fails

    return sql


class QueryAnalyzer:
    """
    Analyzes slow queries to identify performance issues and generate suggestions.

    Uses a combination of:
    - Rule-based pattern matching for common issues
    - EXPLAIN plan analysis
    - AI-assisted insights (when available)
    """

    def __init__(self, version: str = "1.0.0"):
        """Initialize analyzer with version."""
        self.version = version

    def analyze_query(self, query_id: str) -> Optional[str]:
        """
        Analyze a single slow query by ID.

        Args:
            query_id: UUID of the slow query to analyze

        Returns:
            Analysis result ID if successful, None otherwise
        """
        with get_db_context() as db:
            # Fetch query
            query = db.query(SlowQueryRaw).filter(
                SlowQueryRaw.id == query_id
            ).first()

            if not query:
                logger.error(f"Query not found: {query_id}")
                return None

            # Check if already analyzed
            if query.analysis:
                logger.info(f"Query {query_id} already has analysis, skipping")
                return str(query.analysis.id)

            try:
                # Perform analysis
                analysis_data = self._analyze(query)

                # Store results
                analysis = AnalysisResult(
                    slow_query_id=query.id,
                    problem=analysis_data['problem'],
                    root_cause=analysis_data['root_cause'],
                    suggestions=analysis_data['suggestions'],
                    improvement_level=analysis_data['improvement_level'],
                    estimated_speedup=analysis_data['estimated_speedup'],
                    analyzer_version=self.version,
                    analysis_method=analysis_data.get('method', 'rule_based'),
                    confidence_score=Decimal(str(analysis_data.get('confidence', 0.85))),
                    analysis_metadata=analysis_data.get('metadata', {}),
                    analyzed_at=datetime.utcnow()
                )

                db.add(analysis)

                # Update query status
                query.status = 'ANALYZED'

                db.commit()
                db.refresh(analysis)

                logger.info(f"✓ Analysis complete for query {query_id}: {analysis_data['improvement_level']}")
                return str(analysis.id)

            except Exception as e:
                logger.error(f"Analysis failed for query {query_id}: {e}", exc_info=True)
                query.status = 'ERROR'
                db.commit()
                return None

    def _analyze(self, query: SlowQueryRaw) -> Dict[str, Any]:
        """
        Internal analysis logic.

        Args:
            query: SlowQueryRaw model instance

        Returns:
            Dictionary with analysis results
        """
        # Decode hex-encoded SQL if needed
        decoded_sql = decode_hex_sql(query.full_sql)

        # Initialize analysis result
        result = {
            'problem': '',
            'root_cause': '',
            'suggestions': [],
            'improvement_level': 'LOW',
            'estimated_speedup': 'minimal',
            'method': 'rule_based',
            'confidence': 0.85,
            'metadata': {}
        }

        # Extract tables
        tables = extract_tables_from_query(decoded_sql)
        result['metadata']['tables'] = tables

        # Analyze EXPLAIN plan if available
        if query.plan_json:
            plan_analysis = self._analyze_explain_plan(
                query.plan_json,
                query.source_db_type
            )
            result.update(plan_analysis)
        else:
            # No plan available, use heuristics
            result.update(self._analyze_heuristics(query))

        # Try AI-enhanced analysis if enabled
        if settings.ai_provider != 'stub':
            try:
                from backend.services.ai_stub import get_ai_analyzer
                ai_analyzer = get_ai_analyzer()

                result = ai_analyzer.enhance_analysis(
                    rule_based_analysis=result,
                    sql=decoded_sql,
                    explain_plan=query.plan_json,
                    db_type=query.source_db_type,
                    duration_ms=float(query.duration_ms),
                    rows_examined=query.rows_examined,
                    rows_returned=query.rows_returned
                )
                logger.info(f"Enhanced analysis with AI ({settings.ai_provider})")
            except Exception as e:
                logger.warning(f"AI analysis failed, using rule-based only: {e}")

        return result

    def _analyze_explain_plan(
        self,
        plan_json: Dict[str, Any],
        db_type: str
    ) -> Dict[str, Any]:
        """
        Analyze EXPLAIN plan to identify issues.

        Args:
            plan_json: Parsed EXPLAIN output
            db_type: Database type (mysql, postgres)

        Returns:
            Analysis findings
        """
        if db_type == 'mysql':
            return self._analyze_mysql_plan(plan_json)
        elif db_type == 'postgres':
            return self._analyze_postgres_plan(plan_json)
        else:
            return self._default_analysis()

    def _analyze_mysql_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze MySQL EXPLAIN FORMAT=JSON output.

        MySQL EXPLAIN structure:
        {
          "query_block": {
            "select_id": 1,
            "table": {...},
            "cost_info": {...}
          }
        }
        """
        result = self._default_analysis()

        try:
            query_block = plan.get('query_block', {})
            table_info = query_block.get('table', {})

            # Check for full table scan
            access_type = table_info.get('access_type', '')
            if access_type in ['ALL', 'index']:
                result['problem'] = 'Full table scan detected'
                result['root_cause'] = (
                    f"Query is performing a full table scan (access_type: {access_type}). "
                    "This means every row in the table is being examined, which is very slow for large tables."
                )
                result['improvement_level'] = 'HIGH'
                result['estimated_speedup'] = '10-100x'
                result['confidence'] = 0.90

                # Get table name
                table_name = table_info.get('table_name', 'unknown')

                # Suggest index
                result['suggestions'].append({
                    'type': 'INDEX',
                    'priority': 'HIGH',
                    'description': f'Add index to {table_name} to avoid full table scan',
                    'sql': f'-- Analyze query and add appropriate index on {table_name}',
                    'estimated_impact': '10-100x improvement'
                })

            # Check for filesort
            if 'filesort' in str(query_block).lower():
                result['suggestions'].append({
                    'type': 'INDEX',
                    'priority': 'MEDIUM',
                    'description': 'Add index to avoid filesort operation',
                    'sql': '-- Add index on ORDER BY columns',
                    'estimated_impact': '2-5x improvement'
                })
                if result['improvement_level'] == 'LOW':
                    result['improvement_level'] = 'MEDIUM'

            # Check rows examined
            rows = table_info.get('rows_examined_per_scan', 0)
            if rows > 100000:
                if result['problem'] == '':
                    result['problem'] = f'Large number of rows examined ({rows:,})'
                result['root_cause'] = (
                    f"Query examines {rows:,} rows. "
                    "This indicates missing or ineffective indexes."
                )
                if result['improvement_level'] == 'LOW':
                    result['improvement_level'] = 'MEDIUM'

        except Exception as e:
            logger.warning(f"Error analyzing MySQL plan: {e}")

        return result

    def _analyze_postgres_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze PostgreSQL EXPLAIN (FORMAT JSON) output.

        PostgreSQL EXPLAIN structure:
        {
          "Plan": {
            "Node Type": "Seq Scan",
            "Relation Name": "table",
            "Total Cost": 123.45,
            ...
          }
        }
        """
        result = self._default_analysis()

        try:
            plan_node = plan.get('Plan', {})
            node_type = plan_node.get('Node Type', '')

            # Check for sequential scan
            if node_type == 'Seq Scan':
                table_name = plan_node.get('Relation Name', 'unknown')
                result['problem'] = 'Sequential scan detected'
                result['root_cause'] = (
                    f"Query is performing a sequential scan on {table_name}. "
                    "PostgreSQL is reading every row in the table sequentially, which is slow for large tables."
                )
                result['improvement_level'] = 'HIGH'
                result['estimated_speedup'] = '10-100x'
                result['confidence'] = 0.90

                result['suggestions'].append({
                    'type': 'INDEX',
                    'priority': 'HIGH',
                    'description': f'Add index to {table_name} to enable index scan',
                    'sql': f'-- CREATE INDEX idx_{table_name}_cols ON {table_name}(column_name);',
                    'estimated_impact': '10-100x improvement'
                })

            # Check for high cost
            total_cost = plan_node.get('Total Cost', 0)
            if total_cost > 10000:
                if result['problem'] == '':
                    result['problem'] = f'High query cost ({total_cost:.2f})'
                result['root_cause'] = (
                    f"Query has high execution cost estimate ({total_cost:.2f}). "
                    "This usually indicates inefficient query structure or missing indexes."
                )
                if result['improvement_level'] == 'LOW':
                    result['improvement_level'] = 'MEDIUM'

                result['suggestions'].append({
                    'type': 'OPTIMIZATION',
                    'priority': 'MEDIUM',
                    'description': 'Review query structure and consider query rewrite',
                    'sql': '-- Consider breaking down complex query or adding indexes',
                    'estimated_impact': '2-10x improvement'
                })

        except Exception as e:
            logger.warning(f"Error analyzing PostgreSQL plan: {e}")

        return result

    def _analyze_heuristics(self, query: SlowQueryRaw) -> Dict[str, Any]:
        """
        Analyze query using heuristics when EXPLAIN plan is not available.

        Args:
            query: SlowQueryRaw instance

        Returns:
            Analysis findings
        """
        result = self._default_analysis()

        # Check rows examined vs returned ratio
        # Handle case where rows_returned can be 0 (INSERT, UPDATE, DELETE)
        if query.rows_examined is not None and query.rows_examined > 0:
            rows_returned = query.rows_returned if query.rows_returned is not None else 1
            ratio = query.rows_examined / max(rows_returned, 1)

            if ratio > 100:
                result['problem'] = 'Inefficient query: examining too many rows'
                result['root_cause'] = (
                    f"Query examines {query.rows_examined:,} rows but returns only {query.rows_returned:,} rows "
                    f"(ratio: {ratio:.1f}:1). This suggests missing or ineffective indexes."
                )
                result['improvement_level'] = 'HIGH'
                result['estimated_speedup'] = '10-50x'
                result['confidence'] = 0.80

                result['suggestions'].append({
                    'type': 'INDEX',
                    'priority': 'HIGH',
                    'description': 'Add indexes to reduce rows examined',
                    'sql': '-- Analyze WHERE clauses and add appropriate indexes',
                    'estimated_impact': '10-50x improvement'
                })
            elif ratio > 10:
                result['problem'] = 'Moderate inefficiency in row scanning'
                result['root_cause'] = (
                    f"Query examines {query.rows_examined:,} rows to return {query.rows_returned:,} rows. "
                    "Consider adding indexes to narrow down the scan."
                )
                result['improvement_level'] = 'MEDIUM'
                result['estimated_speedup'] = '2-10x'

                result['suggestions'].append({
                    'type': 'INDEX',
                    'priority': 'MEDIUM',
                    'description': 'Consider adding indexes to improve filtering',
                    'sql': '-- Review WHERE clauses and add selective indexes',
                    'estimated_impact': '2-10x improvement'
                })

        # Check duration
        if query.duration_ms > 5000:  # > 5 seconds
            if result['improvement_level'] == 'LOW':
                result['improvement_level'] = 'MEDIUM'

            result['suggestions'].append({
                'type': 'REVIEW',
                'priority': 'HIGH',
                'description': 'Query takes more than 5 seconds - requires urgent optimization',
                'sql': '-- Consider query rewrite, partitioning, or caching',
                'estimated_impact': 'Critical performance issue'
            })

        return result

    def _default_analysis(self) -> Dict[str, Any]:
        """Return default analysis structure."""
        return {
            'problem': 'Slow query detected',
            'root_cause': 'Query execution time exceeds threshold',
            'suggestions': [
                {
                    'type': 'REVIEW',
                    'priority': 'MEDIUM',
                    'description': 'Review query and add appropriate indexes',
                    'sql': '-- Analyze query patterns and optimize',
                    'estimated_impact': 'Varies'
                }
            ],
            'improvement_level': 'LOW',
            'estimated_speedup': '2-5x',
            'confidence': 0.70
        }

    def analyze_all_pending(self, limit: int = 50) -> int:
        """
        Analyze all queries with status 'NEW'.

        Args:
            limit: Maximum number of queries to analyze in one batch

        Returns:
            Number of queries analyzed
        """
        with get_db_context() as db:
            # Fetch pending queries
            pending_queries = db.query(SlowQueryRaw).filter(
                SlowQueryRaw.status == 'NEW'
            ).limit(limit).all()

            if not pending_queries:
                logger.info("No pending queries to analyze")
                return 0

            analyzed_count = 0

            for query in pending_queries:
                try:
                    result_id = self.analyze_query(str(query.id))
                    if result_id:
                        analyzed_count += 1
                except Exception as e:
                    logger.error(f"Failed to analyze query {query.id}: {e}")
                    continue

            logger.info(f"✓ Analyzed {analyzed_count} of {len(pending_queries)} pending queries")
            return analyzed_count


# Example usage
if __name__ == "__main__":
    analyzer = QueryAnalyzer()
    count = analyzer.analyze_all_pending()
    print(f"Analyzed {count} queries")
