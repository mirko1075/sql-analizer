"""
Pydantic schemas for request/response validation.
"""
from backend.api.schemas.slow_query import (
    SlowQuerySummary,
    SlowQueryDetail,
    SlowQueryWithAnalysis,
    SlowQueryListResponse,
    AnalysisResultSchema,
    SuggestionSchema,
    ErrorResponse,
)
from backend.api.schemas.stats import (
    TableImpactSchema,
    DatabaseStatsSchema,
    GlobalStatsResponse,
    ImprovementSummarySchema,
    QueryTrendSchema,
    HealthCheckResponse,
)

__all__ = [
    # Slow Query schemas
    "SlowQuerySummary",
    "SlowQueryDetail",
    "SlowQueryWithAnalysis",
    "SlowQueryListResponse",
    "AnalysisResultSchema",
    "SuggestionSchema",
    "ErrorResponse",
    # Stats schemas
    "TableImpactSchema",
    "DatabaseStatsSchema",
    "GlobalStatsResponse",
    "ImprovementSummarySchema",
    "QueryTrendSchema",
    "HealthCheckResponse",
]
