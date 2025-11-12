"""
Analysis API Routes.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any

from services.analyzer import analyze_query, get_analysis_result
from services.collector import collect_slow_queries
from core.logger import setup_logger
from core.config import settings

logger = setup_logger(__name__, settings.log_level)

router = APIRouter(prefix="/api/v1/analyze", tags=["analyze"])


@router.post("/collect")
async def trigger_collection() -> Dict[str, Any]:
    """
    Manually trigger slow query collection.
    
    Returns:
        Collection result with number of queries collected
    """
    try:
        result = collect_slow_queries()
        
        return {
            "status": "completed",
            "collected": result.get("collected", 0),
            "message": result.get("message", "Collection completed")
        }
        
    except Exception as e:
        logger.error(f"Error triggering collection: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{query_id}")
async def trigger_analysis(query_id: int) -> Dict[str, Any]:
    """
    Trigger analysis for a specific slow query.
    
    Path Parameters:
        query_id: ID of the slow query to analyze
    
    Returns:
        Analysis result or job status
    """
    try:
        # Run analysis asynchronously
        result = await analyze_query(query_id)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "status": "completed",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering analysis for query {query_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules/{query_id}")
async def analyze_with_rules(query_id: int) -> Dict[str, Any]:
    """
    Perform rule-based analysis only (no AI).
    This is fast and can be run automatically when queries are detected.

    Path Parameters:
        query_id: ID of the slow query to analyze

    Returns:
        Rule-based analysis result with issues and index suggestions
    """
    try:
        from services.enhanced_rules import QueryRuleAnalyzer
        from services.analyzer import get_explain_plan
        from db.models import SlowQuery, AnalysisResult, get_db
        from datetime import datetime
        import json

        db = next(get_db())
        slow_query = db.query(SlowQuery).filter(SlowQuery.id == query_id).first()

        if not slow_query:
            raise HTTPException(status_code=404, detail=f"Query {query_id} not found")

        start_time = datetime.utcnow()

        # Prepare query info
        query_info = {
            "query_time": slow_query.query_time,
            "lock_time": slow_query.lock_time,
            "rows_examined": slow_query.rows_examined,
            "rows_sent": slow_query.rows_sent,
        }

        # Get EXPLAIN plan
        explain_plan = get_explain_plan(slow_query.sql_text)

        # Run enhanced rule analysis
        rule_analyzer = QueryRuleAnalyzer()
        rule_analysis = rule_analyzer.analyze(
            sql=slow_query.sql_text,
            query_info=query_info,
            explain_plan=explain_plan
        )

        analysis_duration = (datetime.utcnow() - start_time).total_seconds()

        # Store or update analysis result (rule-based only)
        analysis_result = db.query(AnalysisResult).filter(
            AnalysisResult.slow_query_id == query_id
        ).first()

        if not analysis_result:
            analysis_result = AnalysisResult(slow_query_id=query_id)
            db.add(analysis_result)

        # Update rule-based fields
        analysis_result.issues_found = json.dumps(rule_analysis["issues"])
        analysis_result.suggested_indexes = json.dumps(rule_analysis["suggested_indexes"])
        analysis_result.improvement_priority = rule_analysis["priority"]
        analysis_result.analyzed_at = datetime.utcnow()
        analysis_result.analysis_duration = analysis_duration

        # Mark query as analyzed (at least with rules)
        slow_query.analyzed = True
        slow_query.analysis_result_id = analysis_result.id
        if slow_query.status == 'pending':
            slow_query.status = 'analyzed'

        db.commit()

        logger.info(f"✅ Rule-based analysis complete for query {query_id} in {analysis_duration:.2f}s")

        return {
            "success": True,
            "query_id": query_id,
            "analysis_type": "rules_only",
            "issues": rule_analysis["issues"],
            "suggested_indexes": rule_analysis["suggested_indexes"],
            "recommendations": rule_analysis.get("recommendations", []),
            "priority": rule_analysis["priority"],
            "rules_checked": rule_analysis["rules_checked"],
            "analysis_duration": analysis_duration,
            "timestamp": datetime.utcnow().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in rule-based analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{query_id}")
async def get_analysis(query_id: int) -> Dict[str, Any]:
    """
    Get analysis result for a query.

    Path Parameters:
        query_id: ID of the slow query

    Returns:
        Analysis result with issues, suggestions, and AI insights
    """
    try:
        result = get_analysis_result(query_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis not found for query {query_id}. Query may not have been analyzed yet."
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis for query {query_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
