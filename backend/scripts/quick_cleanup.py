#!/usr/bin/env python3
"""
Quick cleanup script - deletes all collected data without prompts.
Use with caution!
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import SlowQuery, AnalysisResult, get_db
from core.logger import setup_logger
from core.config import settings

logger = setup_logger("quick_cleanup", settings.log_level)


def quick_cleanup():
    """Remove all data quickly without prompts."""
    db = None
    try:
        db = next(get_db())
        
        slow_query_count = db.query(SlowQuery).count()
        analysis_count = db.query(AnalysisResult).count()
        
        logger.info(f"🗑️  Deleting {slow_query_count} slow queries and {analysis_count} analysis results...")
        
        # Delete all
        db.query(AnalysisResult).delete()
        db.query(SlowQuery).delete()
        db.commit()
        
        logger.info(f"✅ Deleted {slow_query_count} slow queries and {analysis_count} analysis results")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        if db:
            db.rollback()
    finally:
        if db:
            db.close()


if __name__ == "__main__":
    quick_cleanup()
