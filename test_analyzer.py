#!/usr/bin/env python3
"""
Test script for analyzer service.

Tests query analysis functionality to verify it works correctly.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.core.logger import get_logger
from backend.services.analyzer import QueryAnalyzer
from backend.services.ai_stub import AIAnalyzer, get_ai_analyzer
from backend.db.session import get_db_context
from backend.db.models import SlowQueryRaw, AnalysisResult

logger = get_logger(__name__)

print("=" * 60)
print("Analyzer Service Test")
print("=" * 60)

# Check for pending queries
print("\n[1/3] Checking for queries to analyze...")
print("-" * 60)
with get_db_context() as db:
    pending_count = db.query(SlowQueryRaw).filter(
        SlowQueryRaw.status == 'NEW'
    ).count()

    analyzed_count = db.query(SlowQueryRaw).filter(
        SlowQueryRaw.status == 'ANALYZED'
    ).count()

    total_count = db.query(SlowQueryRaw).count()

    print(f"Total queries: {total_count}")
    print(f"  Pending (NEW): {pending_count}")
    print(f"  Analyzed: {analyzed_count}")

if pending_count == 0:
    print("\n⚠ No pending queries to analyze.")
    print("Run the collectors first to gather slow queries:")
    print("  python3 test_collectors.py")
else:
    # Test analyzer
    print("\n[2/3] Running Query Analyzer...")
    print("-" * 60)
    try:
        analyzer = QueryAnalyzer()
        count = analyzer.analyze_all_pending(limit=10)
        print(f"✓ Analyzer completed: {count} queries analyzed")

        # Check results
        with get_db_context() as db:
            analyses = db.query(AnalysisResult).limit(5).all()

            if analyses:
                print(f"\n  Sample analyses:")
                for analysis in analyses:
                    print(f"\n  Query ID: {analysis.slow_query_id}")
                    print(f"    Problem: {analysis.problem}")
                    print(f"    Root cause: {analysis.root_cause[:80]}...")
                    print(f"    Improvement level: {analysis.improvement_level}")
                    print(f"    Estimated speedup: {analysis.estimated_speedup}")
                    print(f"    Suggestions: {len(analysis.suggestions)} recommendations")
                    print(f"    Method: {analysis.analysis_method}")
                    print(f"    Confidence: {analysis.confidence_score}")

    except Exception as e:
        print(f"✗ Analyzer test failed: {e}")
        import traceback
        traceback.print_exc()

# Test AI stub
print("\n[3/3] Testing AI Analyzer Stub...")
print("-" * 60)
try:
    ai_analyzer = get_ai_analyzer()

    result = ai_analyzer.analyze_query(
        sql="SELECT * FROM users WHERE status = 'active' AND created_at > '2024-01-01'",
        explain_plan=None,
        db_type="mysql",
        duration_ms=1500.0
    )

    print(f"✓ AI analyzer stub working")
    print(f"  Provider: {result.get('provider')}")
    print(f"  Model: {result.get('model')}")
    print(f"  Confidence: {result.get('confidence')}")
    print(f"  Insights: {len(result.get('ai_insights', []))} insights")
    print(f"\n  Sample insights:")
    for insight in result.get('ai_insights', []):
        print(f"    - {insight}")

except Exception as e:
    print(f"✗ AI analyzer test failed: {e}")
    import traceback
    traceback.print_exc()

# Summary
print("\n" + "=" * 60)
print("✓ Analyzer tests completed!")
print("=" * 60)

print("\nTo view analysis results, run:")
print("  docker exec ai-analyzer-internal-db psql -U ai_core -d ai_core")
print("  SELECT COUNT(*), improvement_level FROM analysis_result GROUP BY improvement_level;")
