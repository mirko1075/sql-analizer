#!/usr/bin/env python3
"""
Database migration script to add status field to SlowQuery model.
Run this to upgrade existing databases.
"""
import sys
import os

# Add parent directory to path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from db.models import engine, init_db, SlowQuery
from core.logger import setup_logger

logger = setup_logger(__name__, "INFO")

def migrate_database():
    """Add status field and update existing records."""
    
    logger.info("Starting database migration...")
    
    try:
        with engine.connect() as conn:
            # Check if status column already exists
            result = conn.execute(text("PRAGMA table_info(slow_queries)"))
            columns = [row[1] for row in result]
            
            if 'status' in columns:
                logger.info("✅ Status column already exists, skipping column creation")
            else:
                logger.info("Adding status column...")
                conn.execute(text("""
                    ALTER TABLE slow_queries 
                    ADD COLUMN status VARCHAR(20) DEFAULT 'pending'
                """))
                conn.commit()
                logger.info("✅ Status column added")
            
            # Update existing records without status
            logger.info("Updating existing records...")
            result = conn.execute(text("""
                UPDATE slow_queries 
                SET status = CASE 
                    WHEN analyzed = 1 THEN 'analyzed'
                    ELSE 'pending'
                END
                WHERE status IS NULL OR status = ''
            """))
            conn.commit()
            
            updated = result.rowcount
            logger.info(f"✅ Updated {updated} existing records")
            
            # Create indexes if they don't exist
            logger.info("Creating indexes...")
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_status ON slow_queries(status)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_status_collected ON slow_queries(status, collected_at)"))
                conn.commit()
                logger.info("✅ Indexes created")
            except Exception as e:
                logger.warning(f"Index creation note: {e}")
            
        logger.info("=" * 60)
        logger.info("✅ Migration completed successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    migrate_database()
