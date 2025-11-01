"""
Pytest configuration and shared fixtures.
"""
import os
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.main import app
from backend.db.session import get_db
from backend.db.models import Base
from backend.core.config import settings

# Use PostgreSQL test database instead of SQLite
# This ensures compatibility with UUID and other PostgreSQL-specific types
TEST_DB_NAME = "ai_core_test"
# Use internal-db service name when running inside Docker
SQLALCHEMY_TEST_DATABASE_URL = f"postgresql://ai_core:ai_core@internal-db:5432/{TEST_DB_NAME}"

# Create test engine
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URL)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Create a fresh database for each test.
    """
    # Drop all tables before creating (with CASCADE to handle circular dependencies)
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """
    Create a test client with database session override.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def superuser_token(client: TestClient) -> str:
    """
    Register and login as superuser (first user), return access token.
    """
    # Register
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@test.com",
            "password": "Admin123!@#",
            "full_name": "Admin User"
        }
    )
    assert response.status_code == 201  # Changed from 200 to 201
    data = response.json()
    return data["access_token"]


@pytest.fixture(scope="function")
def regular_user_token(client: TestClient) -> str:
    """
    Register and login as regular user, return access token.
    """
    # Register
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "user@test.com",
            "password": "User123!@#",
            "full_name": "Regular User"
        }
    )
    assert response.status_code == 201  # Changed from 200 to 201
    data = response.json()
    return data["access_token"]


@pytest.fixture(scope="function")
def organization_id(client: TestClient, superuser_token: str) -> str:
    """
    Create a test organization and return its ID.
    """
    response = client.post(
        "/api/v1/organizations",
        json={
            "name": "Test Organization",
            "slug": "test-org"
        },
        headers={"Authorization": f"Bearer {superuser_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    return data["id"]


@pytest.fixture(scope="function")
def team_id(client: TestClient, superuser_token: str, organization_id: str) -> str:
    """
    Create a test team and return its ID.
    """
    response = client.post(
        "/api/v1/teams",
        json={
            "name": "Development Team",
            "slug": "dev-team",
            "organization_id": organization_id
        },
        headers={"Authorization": f"Bearer {superuser_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    return data["id"]


@pytest.fixture(scope="function")
def db_connection_id(client: TestClient, superuser_token: str, team_id: str) -> str:
    """
    Create a test database connection and return its ID.
    """
    response = client.post(
        "/api/v1/database-connections",
        json={
            "name": "Test MySQL",
            "db_type": "mysql",
            "host": "localhost",
            "port": 3306,
            "database": "test_db",
            "username": "test_user",
            "password": "test_pass",
            "team_id": team_id
        },
        headers={"Authorization": f"Bearer {superuser_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    return data["id"]


@pytest.fixture(scope="function")
def auth_headers(superuser_token: str) -> dict:
    """
    Return authorization headers with superuser token.
    """
    return {"Authorization": f"Bearer {superuser_token}"}
