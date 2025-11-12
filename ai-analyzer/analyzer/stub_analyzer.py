"""
Stub analyzer implementation for testing.
Returns mock analysis results without calling external AI services.
"""
import logging
from typing import Dict, Any

from .base import BaseAnalyzer
from models.schemas import AnalysisRequest

logger = logging.getLogger(__name__)


class StubAnalyzer(BaseAnalyzer):
    """
    Stub SQL analyzer for testing and development.

    Returns pre-defined mock analysis results without requiring
    external AI services. Useful for:
    - Testing and development
    - CI/CD pipelines
    - Demos without API costs
    """

    def __init__(self, model_config=None):
        """
        Initialize stub analyzer.

        Args:
            model_config: Model configuration (ignored for stub)
        """
        super().__init__("stub-analyzer-v1")
        logger.info("Initialized stub analyzer for testing")

    def _analyze_with_ai(self, request: AnalysisRequest) -> Dict[str, Any]:
        """
        Return mock analysis results.

        Args:
            request: Analysis request

        Returns:
            Dictionary with mock analysis results
        """
        logger.debug(f"Stub analyzer: analyzing query of length {len(request.sql_query)}")

        # Detect common performance issues in the query
        issues = []
        sql_lower = request.sql_query.lower()

        # Check for SELECT *
        if "select *" in sql_lower:
            issues.append({
                "severity": "MEDIUM",
                "category": "Query Structure",
                "description": "Using SELECT * retrieves all columns which may be inefficient",
                "recommendation": "Specify only the columns you need instead of using SELECT *",
                "impact": "Can increase network transfer and memory usage unnecessarily"
            })

        # Check for missing WHERE clause
        if " where " not in sql_lower and "select" in sql_lower:
            issues.append({
                "severity": "HIGH",
                "category": "Query Structure",
                "description": "Query without WHERE clause may scan entire table",
                "recommendation": "Add appropriate WHERE clause to filter results",
                "impact": "Full table scan can be extremely slow on large tables"
            })

        # Check for LIKE with leading wildcard
        if "like '%"  in sql_lower or 'like "%' in sql_lower:
            issues.append({
                "severity": "HIGH",
                "category": "Index Usage",
                "description": "LIKE pattern with leading wildcard prevents index usage",
                "recommendation": "Avoid leading wildcards or consider full-text search",
                "impact": "Cannot use indexes, requires full table scan"
            })

        # Check for functions on indexed columns
        if any(f"({col}" in sql_lower for col in ["date(", "year(", "month(", "upper(", "lower("]):
            issues.append({
                "severity": "MEDIUM",
                "category": "Index Usage",
                "description": "Functions on columns in WHERE clause prevent index usage",
                "recommendation": "Move function to the right side of comparison or use computed columns",
                "impact": "Indexes cannot be used efficiently"
            })

        # Check for OR conditions (can sometimes be inefficient)
        if " or " in sql_lower:
            issues.append({
                "severity": "LOW",
                "category": "Query Structure",
                "description": "OR conditions may prevent optimal index usage",
                "recommendation": "Consider using UNION or IN clause instead of OR",
                "impact": "May require multiple index scans or full table scan"
            })

        # If no issues found, add a positive message
        if not issues:
            issues.append({
                "severity": "INFO",
                "category": "Query Structure",
                "description": "No obvious performance issues detected",
                "recommendation": "Query appears to be well-formed",
                "impact": "None - query structure looks good"
            })

        return {
            "issues": issues,
            "summary": f"Found {len([i for i in issues if i['severity'] != 'INFO'])} potential issues",
            "model_used": "stub-analyzer-v1",
            "analysis_type": "rule-based"
        }
