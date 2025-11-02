"""
Run database migration script.

This script applies SQL migration files to the database.

Usage:
    python -m backend.run_migration
"""
import sys
from pathlib import Path

from backend.core.logger import get_logger
from backend.db.session import SessionLocal

logger = get_logger(__name__)


def run_migration(migration_file: str):
    """
    Run a SQL migration file.

    Args:
        migration_file: Path to the SQL migration file
    """
    migration_path = Path(migration_file)

    if not migration_path.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False

    logger.info(f"Running migration: {migration_path.name}")

    db = SessionLocal()

    try:
        # Read the SQL migration file
        with open(migration_path, 'r') as f:
            sql_content = f.read()

        # Execute the migration
        db.execute(sql_content)
        db.commit()

        logger.info(f"✓ Migration completed successfully: {migration_path.name}")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"✗ Migration failed: {e}", exc_info=True)
        return False

    finally:
        db.close()


def main():
    """
    Main entry point for running migrations.
    """
    logger.info("=" * 70)
    logger.info("Database Migration Runner")
    logger.info("=" * 70)

    # Run the auth and multi-tenancy migration
    migration_file = Path(__file__).parent / "db" / "migrations" / "001_add_auth_multitenancy.sql"

    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        sys.exit(1)

    logger.info(f"\nApplying migration: {migration_file.name}")
    logger.info("-" * 70)

    success = run_migration(str(migration_file))

    logger.info("=" * 70)

    if success:
        logger.info("✓ All migrations completed successfully!")
        logger.info("\nNext step: Run the seed script to create initial data:")
        logger.info("    python -m backend.seed_initial_data")
        sys.exit(0)
    else:
        logger.error("✗ Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\n\nMigration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
