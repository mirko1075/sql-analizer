"""
Database initialization script.
Creates tables and initial super admin user.
"""
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from db.models_multitenant import (
    Base, engine, SessionLocal, init_db,
    Organization, Team, Identity, User, UserRole
)
from passlib.context import CryptContext
from datetime import datetime

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_super_admin(
    db,
    email: str = "admin@dbpower.local",
    password: str = "admin123",
    full_name: str = "Super Administrator"
):
    """
    Create initial super admin user with default organization.
    """
    # Check if super admin already exists
    existing_admin = db.query(User).filter(
        User.email == email,
        User.role == UserRole.SUPER_ADMIN
    ).first()

    if existing_admin:
        print(f"⚠️  Super admin '{email}' already exists.")
        return existing_admin

    # Create default organization for super admin
    org = Organization(
        name="DBPower System",
        settings={
            "is_system_org": True,
            "description": "System organization for super administrators"
        }
    )
    db.add(org)
    db.flush()  # Get org.id

    # Generate API key for organization
    api_key = org.generate_api_key()
    print(f"\n🔑 Organization API Key: {api_key}")
    print("⚠️  SAVE THIS KEY! It will not be shown again.\n")

    # Create default team
    team = Team(
        organization_id=org.id,
        name="Admin Team"
    )
    db.add(team)
    db.flush()

    # Create default identity
    identity = Identity(
        team_id=team.id,
        name="System Identity"
    )
    db.add(identity)
    db.flush()

    # Create super admin user
    admin_user = User(
        organization_id=org.id,
        identity_id=identity.id,
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role=UserRole.SUPER_ADMIN,
        is_active=True
    )
    db.add(admin_user)
    db.commit()

    print(f"✅ Super admin user created:")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    print(f"   Role: {admin_user.role.value}")
    print(f"   Organization: {org.name} (ID: {org.id})")

    return admin_user


def create_demo_organization(db):
    """
    Create a demo organization with sample data for testing.
    """
    # Check if demo org already exists
    existing_org = db.query(Organization).filter(
        Organization.name == "Demo Company"
    ).first()

    if existing_org:
        print(f"⚠️  Demo organization already exists.")
        return existing_org

    # Create demo organization
    org = Organization(
        name="Demo Company",
        settings={
            "is_demo": True,
            "description": "Demo organization for testing"
        }
    )
    db.add(org)
    db.flush()

    # Generate API key
    api_key = org.generate_api_key()
    print(f"\n🔑 Demo Organization API Key: {api_key}")
    print("⚠️  SAVE THIS KEY for testing!\n")

    # Create teams
    engineering_team = Team(organization_id=org.id, name="Engineering")
    data_team = Team(organization_id=org.id, name="Data Team")
    db.add(engineering_team)
    db.add(data_team)
    db.flush()

    # Create identities
    backend_identity = Identity(team_id=engineering_team.id, name="Backend Services")
    frontend_identity = Identity(team_id=engineering_team.id, name="Frontend Services")
    analytics_identity = Identity(team_id=data_team.id, name="Analytics DB")

    db.add(backend_identity)
    db.add(frontend_identity)
    db.add(analytics_identity)
    db.flush()

    # Create users
    org_admin = User(
        organization_id=org.id,
        identity_id=backend_identity.id,
        email="admin@democompany.local",
        password_hash=hash_password("demo123"),
        full_name="Demo Admin",
        role=UserRole.ORG_ADMIN,
        is_active=True
    )

    team_lead = User(
        organization_id=org.id,
        identity_id=backend_identity.id,
        email="teamlead@democompany.local",
        password_hash=hash_password("demo123"),
        full_name="Demo Team Lead",
        role=UserRole.TEAM_LEAD,
        is_active=True
    )

    regular_user = User(
        organization_id=org.id,
        identity_id=backend_identity.id,
        email="user@democompany.local",
        password_hash=hash_password("demo123"),
        full_name="Demo User",
        role=UserRole.USER,
        is_active=True
    )

    db.add(org_admin)
    db.add(team_lead)
    db.add(regular_user)
    db.commit()

    print(f"✅ Demo organization created:")
    print(f"   Organization: {org.name} (ID: {org.id})")
    print(f"   Teams: Engineering, Data Team")
    print(f"   Identities: Backend Services, Frontend Services, Analytics DB")
    print(f"\n   Demo Users:")
    print(f"   - admin@democompany.local / demo123 (ORG_ADMIN)")
    print(f"   - teamlead@democompany.local / demo123 (TEAM_LEAD)")
    print(f"   - user@democompany.local / demo123 (USER)")

    return org


def main():
    """Initialize database and create initial data."""
    print("=" * 70)
    print("DBPower AI Cloud - Database Initialization")
    print("=" * 70)

    # Check if database URL is configured
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("\n⚠️  DATABASE_URL not set. Using default configuration.")
        print(f"   Using: {engine.url}")

    print("\n📦 Creating database tables...")
    init_db()
    print("✅ Tables created successfully.")

    # Create session
    db = SessionLocal()

    try:
        # Create super admin
        print("\n👤 Creating super admin user...")
        super_admin_email = os.getenv("SUPER_ADMIN_EMAIL", "admin@dbpower.local")
        super_admin_password = os.getenv("SUPER_ADMIN_PASSWORD", "admin123")
        super_admin_name = os.getenv("SUPER_ADMIN_NAME", "Super Administrator")

        create_super_admin(
            db,
            email=super_admin_email,
            password=super_admin_password,
            full_name=super_admin_name
        )

        # Create demo organization (optional)
        create_demo = os.getenv("CREATE_DEMO_ORG", "true").lower() == "true"
        if create_demo:
            print("\n🏢 Creating demo organization...")
            create_demo_organization(db)

        print("\n" + "=" * 70)
        print("✅ Database initialization completed!")
        print("=" * 70)
        print("\n🚀 You can now start the application:")
        print("   uvicorn main:app --reload")
        print("\n📚 Next steps:")
        print("   1. Login with super admin credentials")
        print("   2. Create organizations for your customers")
        print("   3. Configure client agents with organization API keys")
        print("\n⚠️  IMPORTANT: Change default passwords in production!")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
