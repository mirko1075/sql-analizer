#!/usr/bin/env python3
"""
Test Query Analyzer
===================
This script tests the query analyzer in isolation.

Prerequisites:
- Internal database running on localhost:5440
- Some slow queries already collected in the database
- Environment loaded from .env.lab

Usage:
    python3 test-analyzer.py [--limit N] [--no-analyze]
"""

import os
import sys
import argparse
from pathlib import Path

# Setup paths
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

# Load environment
env_file = SCRIPT_DIR / '.env.lab'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

from backend.services.analyzer import QueryAnalyzer
from backend.db.session import get_db_context
from backend.db.models import SlowQueryRaw, AnalysisResult
from backend.core.logger import get_logger
from sqlalchemy import func

logger = get_logger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Test query analyzer')
    parser.add_argument('--limit', type=int, default=10,
                        help='Number of queries to analyze (default: 10)')
    parser.add_argument('--no-analyze', action='store_true',
                        help='Do not run analysis, just show stats')
    args = parser.parse_args()

    print("\n" + "=" * 70)
    print("Query Analyzer Test")
    print("=" * 70 + "\n")

    try:
        # Check database status
        print("Checking database for queries...")

        with get_db_context() as db:
            total_count = db.query(SlowQueryRaw).count()
            new_count = db.query(SlowQueryRaw).filter(
                SlowQueryRaw.status == 'NEW'
            ).count()
            analyzed_count = db.query(SlowQueryRaw).filter(
                SlowQueryRaw.status == 'ANALYZED'
            ).count()

            print(f"  Total queries in database: {total_count}")
            print(f"  New (pending analysis): {new_count}")
            print(f"  Already analyzed: {analyzed_count}")

        if total_count == 0:
            print("\n✗ No queries in database!")
            print("\nRun collector first:")
            print("  python3 test-collectors.py")
            sys.exit(1)

        if new_count == 0:
            print("\n✓ All queries have been analyzed")
            if not args.no_analyze:
                print("\nTo re-analyze, update query status in database:")
                print("  UPDATE slow_queries_raw SET status = 'NEW';")
        else:
            print(f"\n✓ Found {new_count} queries pending analysis")

        # Run analyzer if requested
        if not args.no_analyze and new_count > 0:
            print(f"\nAnalyzing up to {args.limit} queries...")

            analyzer = QueryAnalyzer()
            analyzed = analyzer.analyze_all_pending(limit=args.limit)

            print(f"✓ Analyzed {analyzed} queries")

        # Show analysis results
        print("\nAnalysis Results:")
        print("-" * 70)

        with get_db_context() as db:
            # Get improvement level breakdown
            improvement_breakdown = db.query(
                AnalysisResult.improvement_level,
                func.count(AnalysisResult.id)
            ).group_by(AnalysisResult.improvement_level).all()

            if improvement_breakdown:
                print("\nImprovement Level Breakdown:")
                for level, count in improvement_breakdown:
                    print(f"  {level.value}: {count}")

            # Get analysis method breakdown
            method_breakdown = db.query(
                AnalysisResult.analysis_method,
                func.count(AnalysisResult.id)
            ).group_by(AnalysisResult.analysis_method).all()

            if method_breakdown:
                print("\nAnalysis Method Breakdown:")
                for method, count in method_breakdown:
                    print(f"  {method.value}: {count}")

            # Show sample analyses
            analyses = db.query(AnalysisResult).order_by(
                AnalysisResult.analyzed_at.desc()
            ).limit(5).all()

            if analyses:
                print(f"\nRecent Analyses (showing {len(analyses)}):")
                for i, analysis in enumerate(analyses, 1):
                    # Get associated query
                    query = db.query(SlowQueryRaw).filter(
                        SlowQueryRaw.id == analysis.slow_query_id
                    ).first()

                    print(f"\n{i}. Query ID: {analysis.slow_query_id}")
                    if query:
                        print(f"   SQL: {query.full_sql[:70]}...")
                        print(f"   Duration: {float(query.duration_ms)}ms")
                    print(f"   Problem: {analysis.problem}")
                    print(f"   Improvement Level: {analysis.improvement_level.value}")
                    print(f"   Estimated Speedup: {analysis.estimated_speedup}")
                    print(f"   Confidence: {float(analysis.confidence_score):.2f}")
                    print(f"   Method: {analysis.analysis_method.value}")

                    # Show suggestions
                    if analysis.suggestions:
                        print(f"   Suggestions:")
                        suggestions = analysis.suggestions if isinstance(analysis.suggestions, list) else []
                        for j, suggestion in enumerate(suggestions[:3], 1):
                            if isinstance(suggestion, dict):
                                action = suggestion.get('action', 'N/A')
                                print(f"     {j}. {action}")
                            else:
                                print(f"     {j}. {suggestion}")

        print("\n" + "=" * 70)
        print("✓ Analyzer test complete!")
        print("=" * 70)

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
