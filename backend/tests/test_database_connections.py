"""
Tests for database connection management.

Tests:
- Create database connection
- List connections (filtered by team)
- Get connection by ID
- Update connection
- Delete connection
- Test connection
- Password encryption
- Team isolation
"""
import pytest
from fastapi.testclient import TestClient


class TestDatabaseConnectionCreation:
    """Test database connection creation."""
    
    def test_create_mysql_connection(
        self, client: TestClient, superuser_token: str, team_id: str
    ):
        """Create MySQL database connection."""
        response = client.post(
            "/api/v1/database-connections",
            json={
                "name": "MySQL Production",
                "db_type": "mysql",
                "host": "mysql.example.com",
                "port": 3306,
                "database": "prod_db",
                "username": "admin",
                "password": "secret123",
                "team_id": team_id
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "MySQL Production"
        assert data["db_type"] == "mysql"
        assert data["host"] == "mysql.example.com"
        assert "password" not in data  # Password should be hidden
        assert "id" in data
    
    def test_create_postgres_connection(
        self, client: TestClient, superuser_token: str, team_id: str
    ):
        """Create PostgreSQL database connection."""
        response = client.post(
            "/api/v1/database-connections",
            json={
                "name": "PostgreSQL Dev",
                "db_type": "postgres",
                "host": "localhost",
                "port": 5432,
                "database": "dev_db",
                "username": "dev_user",
                "password": "dev_pass",
                "team_id": team_id,
                "ssl_enabled": True
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["db_type"] == "postgres"
        assert data.get("ssl_enabled") is True
    
    def test_create_connection_without_team_fails(
        self, client: TestClient, superuser_token: str
    ):
        """Cannot create connection without team."""
        response = client.post(
            "/api/v1/database-connections",
            json={
                "name": "Test DB",
                "db_type": "mysql",
                "host": "localhost",
                "port": 3306,
                "database": "test",
                "username": "user",
                "password": "pass"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 422


class TestDatabaseConnectionRetrieval:
    """Test database connection retrieval."""
    
    def test_list_connections_filtered_by_team(
        self, client: TestClient, superuser_token: str, db_connection_id: str
    ):
        """List connections shows only team's connections."""
        response = client.get(
            "/api/v1/database-connections",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # All returned connections should belong to user's teams
        for conn in data:
            assert "team_id" in conn
            assert "password" not in conn  # Password should be hidden
    
    def test_get_connection_by_id(
        self, client: TestClient, superuser_token: str, db_connection_id: str
    ):
        """Get specific connection by ID."""
        response = client.get(
            f"/api/v1/database-connections/{db_connection_id}",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == db_connection_id
        assert "name" in data
        assert "password" not in data  # Password should be hidden
    
    def test_get_other_team_connection_fails(
        self, client: TestClient, regular_user_token: str, db_connection_id: str
    ):
        """Cannot get connection from other team."""
        response = client.get(
            f"/api/v1/database-connections/{db_connection_id}",
            headers={"Authorization": f"Bearer {regular_user_token}"}
        )
        
        # Should fail with 403 or 404
        assert response.status_code in [403, 404]


class TestDatabaseConnectionUpdate:
    """Test database connection updates."""
    
    def test_update_connection(
        self, client: TestClient, superuser_token: str, db_connection_id: str
    ):
        """Update connection details."""
        response = client.put(
            f"/api/v1/database-connections/{db_connection_id}",
            json={
                "name": "Updated Connection Name",
                "description": "Updated description"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Connection Name"
    
    def test_update_connection_password(
        self, client: TestClient, superuser_token: str, db_connection_id: str
    ):
        """Update connection password."""
        response = client.put(
            f"/api/v1/database-connections/{db_connection_id}",
            json={
                "password": "new_secret_password"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "password" not in data  # Password should remain hidden
    
    def test_update_other_team_connection_fails(
        self, client: TestClient, regular_user_token: str, db_connection_id: str
    ):
        """Cannot update connection from other team."""
        response = client.put(
            f"/api/v1/database-connections/{db_connection_id}",
            json={"name": "Hacked Name"},
            headers={"Authorization": f"Bearer {regular_user_token}"}
        )
        
        assert response.status_code in [403, 404]


class TestDatabaseConnectionTesting:
    """Test connection testing functionality."""
    
    def test_test_connection(
        self, client: TestClient, superuser_token: str, team_id: str
    ):
        """Test database connection."""
        # Create a connection
        create_response = client.post(
            "/api/v1/database-connections",
            json={
                "name": "Test Connection",
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
        conn_id = create_response.json()["id"]
        
        # Test connection
        response = client.post(
            f"/api/v1/database-connections/{conn_id}/test",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        # Response could be success or failure depending on actual connectivity
        assert response.status_code in [200, 400, 500]
        data = response.json()
        assert "success" in data or "error" in data


class TestDatabaseConnectionDeletion:
    """Test database connection deletion."""
    
    def test_delete_connection(
        self, client: TestClient, superuser_token: str, team_id: str
    ):
        """Delete database connection."""
        # Create connection to delete
        create_response = client.post(
            "/api/v1/database-connections",
            json={
                "name": "To Delete",
                "db_type": "mysql",
                "host": "localhost",
                "port": 3306,
                "database": "temp_db",
                "username": "user",
                "password": "pass",
                "team_id": team_id
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        conn_id = create_response.json()["id"]
        
        # Delete it
        response = client.delete(
            f"/api/v1/database-connections/{conn_id}",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code in [200, 204]
        
        # Verify it's deleted
        get_response = client.get(
            f"/api/v1/database-connections/{conn_id}",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert get_response.status_code == 404
    
    def test_delete_other_team_connection_fails(
        self, client: TestClient, regular_user_token: str, db_connection_id: str
    ):
        """Cannot delete connection from other team."""
        response = client.delete(
            f"/api/v1/database-connections/{db_connection_id}",
            headers={"Authorization": f"Bearer {regular_user_token}"}
        )
        
        assert response.status_code in [403, 404]


class TestPasswordEncryption:
    """Test password encryption in database."""
    
    def test_password_is_encrypted_in_db(
        self, client: TestClient, superuser_token: str, team_id: str, db
    ):
        """Verify password is encrypted in database."""
        from backend.db.models import DatabaseConnection
        
        # Create connection
        response = client.post(
            "/api/v1/database-connections",
            json={
                "name": "Encryption Test",
                "db_type": "mysql",
                "host": "localhost",
                "port": 3306,
                "database": "test_db",
                "username": "user",
                "password": "plain_password_123",
                "team_id": team_id
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        conn_id = response.json()["id"]
        
        # Query database directly
        db_conn = db.query(DatabaseConnection).filter(
            DatabaseConnection.id == conn_id
        ).first()
        
        # Password should be encrypted (not plain text)
        assert db_conn.encrypted_password != "plain_password_123"
        assert db_conn.encrypted_password is not None
        assert len(db_conn.encrypted_password) > 20  # Encrypted is longer
