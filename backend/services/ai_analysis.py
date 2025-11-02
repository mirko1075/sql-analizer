"""
AI analysis orchestration service.

Provides functions to trigger AI-driven analysis for specific slow queries
using database context metadata and persists results.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend.core.logger import get_logger
from backend.db.models import AIAnalysisResult, SlowQueryRaw
from backend.db.session import get_db_context
from backend.services.ai_stub import get_ai_analyzer
from backend.services.db_context_collector import DatabaseContextCollector
from backend.services.fingerprint import extract_tables_from_query

logger = get_logger(__name__)


class AIAnalysisService:
    """Encapsulates AI analysis workflow for slow queries."""

    def __init__(self, collector: Optional[DatabaseContextCollector] = None):
        self.collector = collector or DatabaseContextCollector()

    def analyze_query(
        self,
        query_id: UUID,
        force: bool = False,
        tables_hint: Optional[List[str]] = None,
    ) -> AIAnalysisResult:
        """
        Run AI analysis for a slow query.

        Args:
            query_id: Identifier of the slow query
            force: Run analysis even if a cached AI result exists
            tables_hint: Optional override for involved tables
        """
        with get_db_context() as db:
            query = db.query(SlowQueryRaw).filter(SlowQueryRaw.id == query_id).first()
            if not query:
                raise ValueError(f"Slow query {query_id} not found")

            if query.ai_analysis and not force:
                logger.info("Returning cached AI analysis for query %s", query_id)
                return query.ai_analysis

            table_names = tables_hint or extract_tables_from_query(query.full_sql or "")
            context = self.collector.get_context(query.source_db_type, table_names)

            ai_analyzer = get_ai_analyzer()
            ai_payload = ai_analyzer.analyze_query(
                sql=query.full_sql,
                explain_plan=query.plan_json,
                db_type=query.source_db_type,
                duration_ms=float(query.duration_ms),
                rows_examined=query.rows_examined,
                rows_returned=query.rows_returned,
                db_context=context,
            )

            ai_model = self._persist_result(db, query, ai_payload, context, force)
            db.commit()
            db.refresh(ai_model)
            return ai_model

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _persist_result(
        self,
        db: Session,
        query: SlowQueryRaw,
        ai_payload: Dict[str, Any],
        context: Dict[str, Any],
        force: bool,
    ) -> AIAnalysisResult:
        """Create or update AIAnalysisResult record."""
        if query.ai_analysis and force:
            logger.info("Replacing existing AI analysis for query %s", query.id)
            old_analysis = query.ai_analysis
            query.ai_analysis = None
            query.ai_analysis_id = None
            db.delete(old_analysis)
            db.flush()

        result = AIAnalysisResult(
            slow_query_id=query.id,
            provider=ai_payload.get("provider", "stub"),
            model=ai_payload.get("model", "mock-v1"),
            summary=ai_payload.get("summary") or ai_payload.get("problem", "AI summary unavailable"),
            root_cause=ai_payload.get("root_cause", "AI root cause unavailable"),
            recommendations=ai_payload.get("recommendations", []),
            improvement_level=ai_payload.get("improvement_level"),
            estimated_speedup=ai_payload.get("estimated_speedup"),
            confidence_score=self._as_decimal(ai_payload.get("confidence")),
            prompt_metadata={
                "db_context": context,
                "analysis_metadata": ai_payload.get("metadata"),
            },
            provider_response=ai_payload.get("provider_response"),
            analyzed_at=datetime.utcnow(),
        )

        db.add(result)
        db.flush()

        query.ai_analysis_id = result.id
        query.ai_analysis = result

        return result

    @staticmethod
    def _as_decimal(value: Optional[Any]) -> Optional[Decimal]:
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (ValueError, TypeError):
            logger.warning("Unable to convert confidence value %s to Decimal", value)
            return None


def analyze_query_with_ai(query_id: UUID, force: bool = False) -> AIAnalysisResult:
    """Convenience function used by API routes."""
    service = AIAnalysisService()
    return service.analyze_query(query_id=query_id, force=force)
