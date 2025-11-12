"""
Base class for AI analyzers.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import logging
import time
import uuid

from models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisIssue,
    IssueSeverity
)

logger = logging.getLogger(__name__)


class BaseAnalyzer(ABC):
    """
    Abstract base class for SQL query analyzers.

    Subclasses must implement the _analyze_with_ai method.
    """

    def __init__(self, model_name: str):
        """
        Initialize analyzer.

        Args:
            model_name: Name of the AI model to use
        """
        self.model_name = model_name
        self.stats = {
            'total_analyses': 0,
            'total_issues_found': 0,
            'average_analysis_time_ms': 0,
        }

    @abstractmethod
    def _analyze_with_ai(self, request: AnalysisRequest) -> Dict[str, Any]:
        """
        Perform AI analysis of SQL query.

        This method must be implemented by subclasses to call
        their specific AI provider (OpenAI, Ollama, etc.).

        Args:
            request: Analysis request

        Returns:
            Dictionary with analysis results from AI model

        Raises:
            Exception: If AI analysis fails
        """
        pass

    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        """
        Analyze SQL query for performance issues.

        Args:
            request: Analysis request

        Returns:
            Analysis response with issues and suggestions

        Raises:
            ValueError: If request is invalid
            Exception: If analysis fails
        """
        start_time = time.time()

        try:
            # Validate request
            if not request.sql_query or not request.sql_query.strip():
                raise ValueError("SQL query cannot be empty")

            # Generate unique query ID
            query_id = str(uuid.uuid4())

            logger.info(f"Analyzing query {query_id}")

            # Call AI model
            ai_result = self._analyze_with_ai(request)

            # Parse AI response
            issues = self._parse_ai_response(ai_result)

            # Calculate metrics
            analysis_time_ms = (time.time() - start_time) * 1000

            # Determine overall priority
            optimization_priority = self._calculate_priority(issues)

            # Generate overall assessment
            overall_assessment = self._generate_assessment(issues, request)

            # Build response
            response = AnalysisResponse(
                query_id=query_id,
                issues_found=len(issues),
                issues=issues,
                overall_assessment=overall_assessment,
                optimization_priority=optimization_priority,
                estimated_improvement=self._estimate_improvement(issues),
                ai_model_used=self.model_name,
                analysis_time_ms=analysis_time_ms
            )

            # Update statistics
            self._update_stats(analysis_time_ms, len(issues))

            logger.info(f"Analysis complete: {len(issues)} issues found in {analysis_time_ms:.2f}ms")

            return response

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise

    def _parse_ai_response(self, ai_result: Dict[str, Any]) -> List[AnalysisIssue]:
        """
        Parse AI model response into structured issues.

        Args:
            ai_result: Raw response from AI model

        Returns:
            List of parsed issues
        """
        # This is a basic implementation - subclasses can override for provider-specific parsing
        issues = []

        if "issues" in ai_result and isinstance(ai_result["issues"], list):
            for issue_data in ai_result["issues"]:
                try:
                    issue = AnalysisIssue(**issue_data)
                    issues.append(issue)
                except Exception as e:
                    logger.warning(f"Failed to parse issue: {e}")
                    continue

        return issues

    def _calculate_priority(self, issues: List[AnalysisIssue]) -> IssueSeverity:
        """
        Calculate overall optimization priority based on issues.

        Args:
            issues: List of issues

        Returns:
            Overall priority level
        """
        if not issues:
            return IssueSeverity.INFO

        # Priority order: critical > high > medium > low > info
        severity_order = {
            IssueSeverity.CRITICAL: 5,
            IssueSeverity.HIGH: 4,
            IssueSeverity.MEDIUM: 3,
            IssueSeverity.LOW: 2,
            IssueSeverity.INFO: 1,
        }

        max_severity = max(issues, key=lambda i: severity_order[i.severity])
        return max_severity.severity

    def _generate_assessment(self, issues: List[AnalysisIssue], request: AnalysisRequest) -> str:
        """
        Generate overall assessment summary.

        Args:
            issues: List of issues found
            request: Original request

        Returns:
            Human-readable assessment
        """
        if not issues:
            return "Query appears to be well-optimized. No significant issues detected."

        critical_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == IssueSeverity.HIGH)
        medium_count = sum(1 for i in issues if i.severity == IssueSeverity.MEDIUM)

        if critical_count > 0:
            return f"Query has {critical_count} critical issue(s) that require immediate attention to prevent performance degradation."
        elif high_count > 0:
            return f"Query has {high_count} high-priority issue(s) that should be addressed to improve performance significantly."
        elif medium_count > 0:
            return f"Query has {medium_count} medium-priority issue(s). Consider optimizing for better performance."
        else:
            return "Query has minor optimization opportunities that may provide incremental improvements."

    def _estimate_improvement(self, issues: List[AnalysisIssue]) -> str:
        """
        Estimate overall performance improvement potential.

        Args:
            issues: List of issues

        Returns:
            Estimated improvement description
        """
        if not issues:
            return "No optimization needed"

        critical_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == IssueSeverity.HIGH)

        if critical_count > 0:
            return "80-95% performance improvement possible"
        elif high_count >= 2:
            return "50-80% performance improvement possible"
        elif high_count == 1:
            return "30-50% performance improvement possible"
        else:
            return "10-30% performance improvement possible"

    def _update_stats(self, analysis_time_ms: float, issues_found: int):
        """
        Update analyzer statistics.

        Args:
            analysis_time_ms: Time taken for analysis
            issues_found: Number of issues found
        """
        self.stats['total_analyses'] += 1
        self.stats['total_issues_found'] += issues_found

        # Update rolling average
        total = self.stats['total_analyses']
        current_avg = self.stats['average_analysis_time_ms']
        new_avg = ((current_avg * (total - 1)) + analysis_time_ms) / total
        self.stats['average_analysis_time_ms'] = new_avg

    def get_stats(self) -> Dict[str, Any]:
        """
        Get analyzer statistics.

        Returns:
            Statistics dictionary
        """
        return self.stats.copy()

    def reset_stats(self):
        """Reset analyzer statistics."""
        self.stats = {
            'total_analyses': 0,
            'total_issues_found': 0,
            'average_analysis_time_ms': 0,
        }

    def get_system_prompt(self, database_type: str) -> str:
        """
        Get system prompt for AI model.

        Args:
            database_type: Type of database (mysql, postgresql, etc.)

        Returns:
            System prompt text
        """
        return f"""You are an expert SQL performance analyst specializing in {database_type} databases.

Analyze SQL queries for performance issues and provide structured recommendations.

Focus on:
1. Missing indexes
2. Full table scans
3. N+1 query problems
4. Inefficient JOINs
5. SELECT * usage
6. Suboptimal WHERE clauses
7. Missing LIMIT clauses
8. Expensive operations (ORDER BY, GROUP BY on large datasets)

For each issue found, provide:
- Severity: critical, high, medium, low, or info
- Category: performance, indexing, query_structure, n_plus_one, full_table_scan, missing_index, suboptimal_join, excessive_data, or other
- Title: Brief description (max 200 chars)
- Description: Detailed explanation
- Suggestion: Specific actionable fix
- Estimated impact: Expected performance improvement

Return response in JSON format:
{{
  "issues": [
    {{
      "severity": "high",
      "category": "missing_index",
      "title": "Missing index on user_id",
      "description": "Full table scan on orders table",
      "suggestion": "CREATE INDEX idx_orders_user_id ON orders(user_id);",
      "estimated_impact": "70% query time reduction"
    }}
  ]
}}

If no issues found, return: {{"issues": []}}
"""
