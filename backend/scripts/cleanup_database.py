#!/usr/bin/env python3
"""
Database Cleanup Script
Removes all collected slow queries and analysis results.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.models import SlowQuery, AnalysisResult, get_db, init_db
from core.logger import setup_logger
from core.config import settings

logger = setup_logger("cleanup", settings.log_level)


def cleanup_all_data():
    """Remove all slow queries and analysis results."""
    try:
        db = next(get_db())
        
        # Count records before deletion
        slow_query_count = db.query(SlowQuery).count()
        analysis_count = db.query(AnalysisResult).count()
        
        logger.info(f"Found {slow_query_count} slow queries and {analysis_count} analysis results")
        
        if slow_query_count == 0 and analysis_count == 0:
            logger.info("✅ Database is already clean")
            return
        
        # Ask for confirmation
        print(f"\n⚠️  WARNING: This will delete:")
        print(f"   - {slow_query_count} slow queries")
        print(f"   - {analysis_count} analysis results")
        response = input("\nAre you sure? (yes/no): ")
        
        if response.lower() != 'yes':
            logger.info("❌ Cleanup cancelled")
            return
        
        # Delete all analysis results first (foreign key dependency)
        logger.info("🗑️  Deleting analysis results...")
        db.query(AnalysisResult).delete()
        
        # Delete all slow queries
        logger.info("🗑️  Deleting slow queries...")
        db.query(SlowQuery).delete()
        
        # Commit changes
        db.commit()
        
        logger.info("✅ Database cleaned successfully!")
        logger.info(f"   Deleted {slow_query_count} slow queries")
        logger.info(f"   Deleted {analysis_count} analysis results")
        
    except Exception as e:
        logger.error(f"❌ Error during cleanup: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


def reset_database():
    """Drop and recreate all tables."""
    try:
        logger.info("🔄 Resetting database (drop and recreate tables)...")
        
        response = input("\n⚠️  WARNING: This will DROP all tables and recreate them. Continue? (yes/no): ")
        if response.lower() != 'yes':
            logger.info("❌ Reset cancelled")
            return
        
        from db.models import Base, engine
        
        # Drop all tables
        logger.info("🗑️  Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        
        # Recreate tables
        logger.info("🔨 Creating tables...")
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Database reset successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error during reset: {e}", exc_info=True)


if __name__ == "__main__":
    print("=" * 60)
    print("DBPower - Database Cleanup Script")
    print("=" * 60)
    print("\nOptions:")
    print("  1. Clean all data (keep tables)")
    print("  2. Reset database (drop and recreate tables)")
    print("  3. Exit")
    
    choice = input("\nSelect option (1/2/3): ")
    
    if choice == "1":
        cleanup_all_data()
    elif choice == "2":
        reset_database()
    elif choice == "3":
        logger.info("👋 Exiting...")
    else:
        logger.error("❌ Invalid option")
