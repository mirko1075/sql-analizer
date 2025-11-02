"""
Seed initial data for AI Query Analyzer.

This script:
1. Creates initial admin user (Mirko Siddi)
2. Creates default organization and team
3. Migrates existing slow queries to the default team
4. Creates database connections from .env configuration

Run this script after running database migrations:
    python -m backend.seed_initial_data
"""
import sys
from datetime import datetime

from backend.core.config import settings
from backend.core.security import hash_password, encrypt_db_password
from backend.core.logger import get_logger
from backend.db.session import SessionLocal
from backend.db.models import (
    User,
    Organization,
    Team,
    TeamMember,
    DatabaseConnection,
    SlowQueryRaw,
    QueryMetricsDaily,
    QueryFingerprintMetrics
)

logger = get_logger(__name__)


def seed_initial_data():
    """
    Seed the database with initial data.

    Creates:
    - Initial admin user (from settings)
    - Default organization
    - Main team
    - Database connections (from .env)
    - Assigns existing queries to the default team
    """
    db = SessionLocal()

    try:
        logger.info("=" * 70)
        logger.info("Starting initial data seeding...")
        logger.info("=" * 70)

        # =================================================================
        # STEP 1: Create initial admin user
        # =================================================================
        logger.info("\n[1/6] Creating initial admin user...")

        # Check if user already exists
        existing_user = db.query(User).filter(
            User.email == settings.INITIAL_ADMIN_EMAIL
        ).first()

        if existing_user:
            logger.info(f"  ✓ User already exists: {existing_user.email}")
            user = existing_user
        else:
            # Create new user
            hashed_pw = hash_password(settings.INITIAL_ADMIN_PASSWORD)
            user = User(
                email=settings.INITIAL_ADMIN_EMAIL,
                hashed_password=hashed_pw,
                full_name=settings.INITIAL_ADMIN_NAME,
                is_active=True,
                is_superuser=True  # Make initial user a superuser
            )
            db.add(user)
            db.flush()
            logger.info(f"  ✓ Created user: {user.email} (ID: {user.id})")

        # =================================================================
        # STEP 2: Create default organization
        # =================================================================
        logger.info("\n[2/6] Creating default organization...")

        existing_org = db.query(Organization).filter(
            Organization.slug == "default"
        ).first()

        if existing_org:
            logger.info(f"  ✓ Organization already exists: {existing_org.name}")
            organization = existing_org
        else:
            organization = Organization(
                name="Default Organization",
                slug="default",
                description="Default organization for AI Query Analyzer",
                plan_type="PRO",  # Give PRO plan to initial organization
                is_active=True
            )
            db.add(organization)
            db.flush()
            logger.info(f"  ✓ Created organization: {organization.name} (slug: {organization.slug})")

        # =================================================================
        # STEP 3: Create main team
        # =================================================================
        logger.info("\n[3/6] Creating main team...")

        existing_team = db.query(Team).filter(
            Team.organization_id == organization.id,
            Team.name == "Main Team"
        ).first()

        if existing_team:
            logger.info(f"  ✓ Team already exists: {existing_team.name}")
            team = existing_team
        else:
            team = Team(
                organization_id=organization.id,
                name="Main Team",
                description="Default team for query analysis",
                is_active=True
            )
            db.add(team)
            db.flush()
            logger.info(f"  ✓ Created team: {team.name} (ID: {team.id})")

        # =================================================================
        # STEP 4: Add user as OWNER of the team
        # =================================================================
        logger.info("\n[4/6] Adding user to team as OWNER...")

        existing_membership = db.query(TeamMember).filter(
            TeamMember.team_id == team.id,
            TeamMember.user_id == user.id
        ).first()

        if existing_membership:
            logger.info(f"  ✓ User already member of team with role: {existing_membership.role}")
        else:
            team_member = TeamMember(
                team_id=team.id,
                user_id=user.id,
                role='OWNER'
            )
            db.add(team_member)
            logger.info(f"  ✓ Added {user.email} as OWNER of {team.name}")

        # =================================================================
        # STEP 5: Migrate existing queries to default team
        # =================================================================
        logger.info("\n[5/6] Migrating existing queries to default team...")

        # Count queries without team_id
        unassigned_slow_queries = db.query(SlowQueryRaw).filter(
            SlowQueryRaw.team_id.is_(None)
        ).count()

        if unassigned_slow_queries > 0:
            # Assign all unassigned queries to the default team
            db.query(SlowQueryRaw).filter(
                SlowQueryRaw.team_id.is_(None)
            ).update({SlowQueryRaw.team_id: team.id})

            logger.info(f"  ✓ Assigned {unassigned_slow_queries} slow queries to {team.name}")
        else:
            logger.info("  ✓ No unassigned slow queries found")

        # Update metrics tables
        unassigned_daily_metrics = db.query(QueryMetricsDaily).filter(
            QueryMetricsDaily.team_id.is_(None)
        ).count()

        if unassigned_daily_metrics > 0:
            db.query(QueryMetricsDaily).filter(
                QueryMetricsDaily.team_id.is_(None)
            ).update({QueryMetricsDaily.team_id: team.id})
            logger.info(f"  ✓ Assigned {unassigned_daily_metrics} daily metrics to {team.name}")

        unassigned_fingerprint_metrics = db.query(QueryFingerprintMetrics).filter(
            QueryFingerprintMetrics.team_id.is_(None)
        ).count()

        if unassigned_fingerprint_metrics > 0:
            db.query(QueryFingerprintMetrics).filter(
                QueryFingerprintMetrics.team_id.is_(None)
            ).update({QueryFingerprintMetrics.team_id: team.id})
            logger.info(f"  ✓ Assigned {unassigned_fingerprint_metrics} fingerprint metrics to {team.name}")

        # =================================================================
        # STEP 6: Create database connections from .env
        # =================================================================
        logger.info("\n[6/6] Creating database connections from .env configuration...")

        # MySQL Lab Connection
        mysql_conn_name = "MySQL Lab"
        existing_mysql_conn = db.query(DatabaseConnection).filter(
            DatabaseConnection.team_id == team.id,
            DatabaseConnection.name == mysql_conn_name
        ).first()

        if existing_mysql_conn:
            logger.info(f"  ✓ MySQL connection already exists: {mysql_conn_name}")
        else:
            encrypted_mysql_password = encrypt_db_password(settings.mysql_lab.password)
            mysql_conn = DatabaseConnection(
                team_id=team.id,
                name=mysql_conn_name,
                db_type="mysql",
                host=settings.mysql_lab.host,
                port=settings.mysql_lab.port,
                database_name=settings.mysql_lab.database,
                username=settings.mysql_lab.user,
                encrypted_password=encrypted_mysql_password,
                ssl_enabled=False,
                is_active=True
            )
            db.add(mysql_conn)
            logger.info(f"  ✓ Created MySQL connection: {mysql_conn_name} ({settings.mysql_lab.host}:{settings.mysql_lab.port})")

        # PostgreSQL Lab Connection
        pg_conn_name = "PostgreSQL Lab"
        existing_pg_conn = db.query(DatabaseConnection).filter(
            DatabaseConnection.team_id == team.id,
            DatabaseConnection.name == pg_conn_name
        ).first()

        if existing_pg_conn:
            logger.info(f"  ✓ PostgreSQL connection already exists: {pg_conn_name}")
        else:
            encrypted_pg_password = encrypt_db_password(settings.postgres_lab.password)
            pg_conn = DatabaseConnection(
                team_id=team.id,
                name=pg_conn_name,
                db_type="postgres",
                host=settings.postgres_lab.host,
                port=settings.postgres_lab.port,
                database_name=settings.postgres_lab.database,
                username=settings.postgres_lab.user,
                encrypted_password=encrypted_pg_password,
                ssl_enabled=False,
                is_active=True
            )
            db.add(pg_conn)
            logger.info(f"  ✓ Created PostgreSQL connection: {pg_conn_name} ({settings.postgres_lab.host}:{settings.postgres_lab.port})")

        # =================================================================
        # COMMIT ALL CHANGES
        # =================================================================
        db.commit()

        logger.info("\n" + "=" * 70)
        logger.info("✓ Initial data seeding completed successfully!")
        logger.info("=" * 70)
        logger.info("\nSummary:")
        logger.info(f"  User:         {user.email}")
        logger.info(f"  Organization: {organization.name} ({organization.slug})")
        logger.info(f"  Team:         {team.name}")
        logger.info(f"  Role:         OWNER")
        logger.info(f"  Plan:         {organization.plan_type}")
        logger.info(f"  Queries:      {unassigned_slow_queries} migrated")
        logger.info("\nLogin credentials:")
        logger.info(f"  Email:    {settings.INITIAL_ADMIN_EMAIL}")
        logger.info(f"  Password: {settings.INITIAL_ADMIN_PASSWORD}")
        logger.info("\n⚠️  IMPORTANT: Change the password after first login!")
        logger.info("=" * 70)

        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding data: {e}", exc_info=True)
        logger.error("\n✗ Initial data seeding failed!")
        return False

    finally:
        db.close()


def main():
    """
    Main entry point for the seeding script.
    """
    try:
        success = seed_initial_data()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.warning("\n\nSeeding interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
