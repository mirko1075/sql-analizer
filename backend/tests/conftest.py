"""
Pytest configuration and fixtures for multi-tenant testing.
"""
import pytest
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from db.models_multitenant import Base, Organization, Team, Identity, User, UserRole
from core.security import hash_password


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def engine():
    """Create a test database engine."""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine):
    """Create a test database session."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def sample_organization(db_session):
    """Create a sample organization."""
    org = Organization(
        name="Test Organization",
        settings={"test": True}
    )
    db_session.add(org)
    db_session.flush()

    # Generate API key
    api_key = org.generate_api_key()
    db_session.commit()
    db_session.refresh(org)

    # Store API key for testing (would normally only be shown once)
    org._test_api_key = api_key

    return org


@pytest.fixture(scope="function")
def sample_team(db_session, sample_organization):
    """Create a sample team."""
    team = Team(
        organization_id=sample_organization.id,
        name="Engineering"
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


@pytest.fixture(scope="function")
def sample_identity(db_session, sample_team):
    """Create a sample identity."""
    identity = Identity(
        team_id=sample_team.id,
        name="Backend Services"
    )
    db_session.add(identity)
    db_session.commit()
    db_session.refresh(identity)
    return identity


@pytest.fixture(scope="function")
def sample_user(db_session, sample_organization, sample_identity):
    """Create a sample regular user."""
    user = User(
        organization_id=sample_organization.id,
        identity_id=sample_identity.id,
        email="user@test.local",
        password_hash=hash_password("Test123!"),
        full_name="Test User",
        role=UserRole.USER,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Store plain password for testing
    user._test_password = "Test123!"

    return user


@pytest.fixture(scope="function")
def sample_org_admin(db_session, sample_organization, sample_identity):
    """Create a sample org admin user."""
    user = User(
        organization_id=sample_organization.id,
        identity_id=sample_identity.id,
        email="admin@test.local",
        password_hash=hash_password("Admin123!"),
        full_name="Admin User",
        role=UserRole.ORG_ADMIN,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    user._test_password = "Admin123!"

    return user


@pytest.fixture(scope="function")
def sample_super_admin(db_session, sample_organization, sample_identity):
    """Create a sample super admin user."""
    user = User(
        organization_id=sample_organization.id,
        identity_id=sample_identity.id,
        email="superadmin@test.local",
        password_hash=hash_password("SuperAdmin123!"),
        full_name="Super Admin",
        role=UserRole.SUPER_ADMIN,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    user._test_password = "SuperAdmin123!"

    return user


@pytest.fixture(scope="function")
def second_organization(db_session):
    """Create a second organization for multi-tenant testing."""
    org = Organization(
        name="Second Organization",
        settings={"test": True, "org_number": 2}
    )
    db_session.add(org)
    db_session.flush()

    api_key = org.generate_api_key()
    db_session.commit()
    db_session.refresh(org)

    org._test_api_key = api_key

    return org


@pytest.fixture(scope="function")
def second_team(db_session, second_organization):
    """Create a team in the second organization."""
    team = Team(
        organization_id=second_organization.id,
        name="Data Team"
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


@pytest.fixture(scope="function")
def second_identity(db_session, second_team):
    """Create an identity in the second organization."""
    identity = Identity(
        team_id=second_team.id,
        name="Analytics"
    )
    db_session.add(identity)
    db_session.commit()
    db_session.refresh(identity)
    return identity


@pytest.fixture(scope="function")
def second_org_user(db_session, second_organization, second_identity):
    """Create a user in the second organization."""
    user = User(
        organization_id=second_organization.id,
        identity_id=second_identity.id,
        email="user2@test.local",
        password_hash=hash_password("Test123!"),
        full_name="Second Org User",
        role=UserRole.USER,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    user._test_password = "Test123!"

    return user
