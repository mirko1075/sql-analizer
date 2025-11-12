"""
API Routes for AI Analysis (on-demand).
Separate endpoints for rule-based and AI analysis.
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime

from db.models import SlowQuery, AnalysisResult, get_db
from services.enhanced_rules import QueryRuleAnalyzer
from services.interactive_ai import analyze_query_interactive
from services.analyzer import (
    get_explain_plan,
    get_table_schema,
    get_table_indexes,
    extract_table_names
)
from core.logger import setup_logger
from core.config import settings

logger = setup_logger(__name__, settings.log_level)

router = APIRouter(prefix="/api/v1/ai", tags=["ai-analysis"])


@router.post("/analyze/{query_id}")
async def analyze_with_ai(query_id: int) -> Dict[str, Any]:
    """
    Perform AI analysis on a query (on-demand, triggered by user).
    
    This performs:
    1. Enhanced rule-based analysis (20+ rules)
    2. Interactive AI analysis with DB query capability
    
    The AI can request additional data from the database during analysis.
    
    Path Parameters:
        query_id: ID of the slow query to analyze
    
    Returns:
        Analysis result with rule-based + AI insights
    """
    logger.info(f"🎯 User-triggered AI analysis for query {query_id}")
    
    try:
        db = next(get_db())
        slow_query = db.query(SlowQuery).filter(SlowQuery.id == query_id).first()
        
        if not slow_query:
            raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
        
        start_time = datetime.utcnow()
        
        # ==== STEP 1: Enhanced Rule-Based Analysis ====
        logger.info("📋 Running enhanced rule-based analysis (20+ rules)...")
        
        query_info = {
            "query_time": slow_query.query_time,
            "lock_time": slow_query.lock_time,
            "rows_examined": slow_query.rows_examined,
            "rows_sent": slow_query.rows_sent,
        }
        
        # Get EXPLAIN plan
        explain_plan = get_explain_plan(slow_query.sql_text)
        
        # Run enhanced rules
        rule_analyzer = QueryRuleAnalyzer()
        rule_analysis = rule_analyzer.analyze(
            sql=slow_query.sql_text,
            query_info=query_info,
            explain_plan=explain_plan
        )
        
        logger.info(f"✅ Rule analysis complete: {len(rule_analysis['issues'])} issues found")
        
        # ==== STEP 2: Get Schema Context ====
        logger.info("📊 Gathering schema context...")
        
        tables = extract_table_names(slow_query.sql_text)
        schema_info = {}
        
        for table in tables:
            schema = get_table_schema(table)
            indexes = get_table_indexes(table)
            if schema:
                schema_info[table] = {
                    **schema,
                    "indexes": indexes
                }
        
        # Format EXPLAIN as text
        explain_text = ""
        if explain_plan:
            for row in explain_plan.get("rows", []):
                explain_text += f"Table: {row['table']}\n"
                explain_text += f"  Type: {row['type']}\n"
                explain_text += f"  Key: {row['key']}\n"
                explain_text += f"  Rows: {row['rows']}\n"
                explain_text += f"  Extra: {row['Extra']}\n"
                explain_text += "  ---\n"
        
        # ==== STEP 3: Interactive AI Analysis ====
        logger.info("🤖 Starting interactive AI analysis...")
        logger.info("   AI can request additional database queries during analysis")
        
        ai_result = await analyze_query_interactive(
            sql_query=slow_query.sql_text,
            explain_plan=explain_text,
            schema_info=schema_info,
            table_stats=query_info
        )
        
        if not ai_result.get('success'):
            logger.error(f"AI analysis failed: {ai_result.get('error')}")
            ai_analysis_text = f"AI analysis failed: {ai_result.get('error')}"
            ai_metadata = {
                "error": ai_result.get('error'),
                "iterations": 0,
                "db_queries": 0
            }
        else:
            ai_analysis_text = ai_result['analysis']
            ai_metadata = {
                "iterations": ai_result.get('iterations', 0),
                "db_queries_executed": ai_result.get('db_queries_executed', 0),
                "provider": ai_result.get('provider'),
                "model": ai_result.get('model'),
                "tokens_used": ai_result.get('total_tokens'),
                "duration_ms": ai_result.get('total_duration_ms')
            }
            
            logger.info(f"✅ AI analysis complete:")
            logger.info(f"   Iterations: {ai_metadata['iterations']}")
            logger.info(f"   DB queries executed: {ai_metadata['db_queries_executed']}")
            logger.info(f"   Provider: {ai_metadata['provider']}")
            logger.info(f"   Duration: {ai_metadata['duration_ms']:.0f}ms")
        
        # ==== STEP 4: Store Results ====
        analysis_duration = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info("💾 Storing analysis results...")
        
        # Create or update analysis result
        import json
        analysis_result = db.query(AnalysisResult).filter(
            AnalysisResult.slow_query_id == query_id
        ).first()
        
        if not analysis_result:
            analysis_result = AnalysisResult(slow_query_id=query_id)
            db.add(analysis_result)
        
        analysis_result.issues_found = json.dumps(rule_analysis["issues"])
        analysis_result.suggested_indexes = json.dumps(rule_analysis["suggested_indexes"])
        analysis_result.improvement_priority = rule_analysis["priority"]
        analysis_result.ai_analysis = ai_analysis_text
        analysis_result.ai_suggestions = ai_analysis_text
        analysis_result.analyzed_at = datetime.utcnow()
        analysis_result.analysis_duration = analysis_duration
        
        # Update slow query status
        slow_query.analyzed = True
        slow_query.status = 'analyzed'
        
        db.commit()
        
        logger.info(f"✅ Analysis complete in {analysis_duration:.2f}s")
        
        return {
            "success": True,
            "query_id": query_id,
            "rule_analysis": {
                "issues": rule_analysis["issues"],
                "suggested_indexes": rule_analysis["suggested_indexes"],
                "recommendations": rule_analysis.get("recommendations", []),
                "priority": rule_analysis["priority"],
                "rules_checked": rule_analysis["rules_checked"]
            },
            "ai_analysis": {
                "text": ai_analysis_text,
                "metadata": ai_metadata
            },
            "execution_plan": explain_plan,
            "schema_info": schema_info,
            "analysis_duration": analysis_duration,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in AI analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{query_id}")
async def get_ai_analysis(query_id: int) -> Dict[str, Any]:
    """
    Get existing AI analysis for a query.
    
    Path Parameters:
        query_id: ID of the slow query
    
    Returns:
        Analysis result if available
    """
    try:
        db = next(get_db())
        slow_query = db.query(SlowQuery).filter(SlowQuery.id == query_id).first()
        
        if not slow_query:
            raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
        
        if not slow_query.analyzed:
            raise HTTPException(status_code=404, detail=f"Query {query_id} has not been analyzed yet")
        
        analysis = db.query(AnalysisResult).filter(
            AnalysisResult.slow_query_id == query_id
        ).first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail=f"Analysis not found for query {query_id}")
        
        import json
        
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
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_ai_status() -> Dict[str, Any]:
    """
    Get AI service status and capabilities.
    
    Returns:
        Current AI provider info and capabilities
    """
    try:
        from services.ai import get_ai_provider, check_provider_health
        
        provider = get_ai_provider()
        healthy = await check_provider_health()
        
        return {
            "provider": provider.__class__.__name__.replace('Provider', '').lower(),
            "model": getattr(provider, 'model', 'unknown'),
            "status": "healthy" if healthy else "unhealthy",
            "privacy": "local" if settings.ai_provider == "llama" else "cloud",
            "capabilities": {
                "rule_based_analysis": True,
                "ai_analysis": healthy,
                "interactive_analysis": healthy,
                "db_query_access": healthy
            },
            "features": {
                "enhanced_rules": True,
                "rules_count": 21,
                "db_query_capability": True,
                "conversation_max_iterations": 5
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting AI status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
