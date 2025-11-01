"""
Tests for authentication endpoints.

Tests:
- User registration (superuser and regular users)
- Login
- Token refresh
- Logout
- Get current user info
- Session management
"""
import pytest
from fastapi.testclient import TestClient


class TestRegistration:
    """Test user registration."""
    
    def test_register_first_user_becomes_superuser(self, client: TestClient):
        """First registered user should become superuser."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "admin@test.com",
                "password": "Admin123!@#",
                "full_name": "Admin User"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        
        # Verify user is superuser by calling /me endpoint
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {data['access_token']}"}
        )
        assert me_response.status_code == 200
        user_data = me_response.json()
        assert user_data["email"] == "admin@test.com"
        assert user_data["is_superuser"] is True
    
    def test_register_second_user_not_superuser(self, client: TestClient, superuser_token: str):
        """Second registered user should not be superuser."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@test.com",
                "password": "User123!@#",
                "full_name": "Regular User"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Verify user is not superuser by calling /me endpoint
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {data['access_token']}"}
        )
        assert me_response.status_code == 200
        user_data = me_response.json()
        assert user_data["email"] == "user@test.com"
        assert user_data["is_superuser"] is False
    
    def test_register_duplicate_email_fails(self, client: TestClient):
        """Cannot register with duplicate email."""
        # Register first user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@test.com",
                "password": "Test123!@#",
                "full_name": "Test User"
            }
        )
        
        # Try to register again with same email
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@test.com",
                "password": "Test456!@#",
                "full_name": "Another User"
            }
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()
    
    def test_register_invalid_email_fails(self, client: TestClient):
        """Cannot register with invalid email."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "Test123!@#",
                "full_name": "Test User"
            }
        )
        
        assert response.status_code == 422
    
    def test_register_weak_password_fails(self, client: TestClient):
        """Cannot register with weak password."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@test.com",
                "password": "weak",
                "full_name": "Test User"
            }
        )
        
        assert response.status_code == 422


class TestLogin:
    """Test login functionality."""
    
    def test_login_success(self, client: TestClient):
        """Successful login returns tokens."""
        # Register user first
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@test.com",
                "password": "Test123!@#",
                "full_name": "Test User"
            }
        )
        
        # Login
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@test.com",
                "password": "Test123!@#"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    def test_login_wrong_password_fails(self, client: TestClient):
        """Login with wrong password fails."""
        # Register user first
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@test.com",
                "password": "Test123!@#",
                "full_name": "Test User"
            }
        )
        
        # Try to login with wrong password
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@test.com",
                "password": "WrongPassword123!@#"
            }
        )
        
        assert response.status_code == 401
    
    def test_login_nonexistent_user_fails(self, client: TestClient):
        """Login with non-existent user fails."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@test.com",
                "password": "Test123!@#"
            }
        )
        
        assert response.status_code == 401
    
    def test_login_inactive_user_fails(self, client: TestClient, db):
        """Login with inactive user fails."""
        from backend.db.models import User
        from backend.core.security import hash_password
        
        # Create inactive user directly in DB
        user = User(
            email="inactive@test.com",
            hashed_password=hash_password("Test123!@#"),
            full_name="Inactive User",
            is_active=False,
            is_superuser=False
        )
        db.add(user)
        db.commit()
        
        # Try to login
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "inactive@test.com",
                "password": "Test123!@#"
            }
        )
        
        assert response.status_code == 401


class TestTokenRefresh:
    """Test token refresh functionality."""
    
    def test_refresh_token_success(self, client: TestClient):
        """Refresh token generates new access token."""
        # Register and get tokens
        reg_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@test.com",
                "password": "Test123!@#",
                "full_name": "Test User"
            }
        )
        refresh_token = reg_response.json()["refresh_token"]
        
        # Refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
    
    def test_refresh_with_invalid_token_fails(self, client: TestClient):
        """Refresh with invalid token fails."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"}
        )
        
        assert response.status_code == 401


class TestGetCurrentUser:
    """Test get current user endpoint."""
    
    def test_get_me_success(self, client: TestClient, superuser_token: str):
        """Get current user info with valid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "full_name" in data
        assert "is_superuser" in data
    
    def test_get_me_without_token_fails(self, client: TestClient):
        """Get current user without token fails."""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    def test_get_me_with_invalid_token_fails(self, client: TestClient):
        """Get current user with invalid token fails."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        assert response.status_code == 401


class TestLogout:
    """Test logout functionality."""
    
    def test_logout_success(self, client: TestClient, superuser_token: str):
        """Logout invalidates token."""
        # Logout
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        
        # Try to use token after logout
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert me_response.status_code == 401
    
    def test_logout_without_token_fails(self, client: TestClient):
        """Logout without token fails."""
        response = client.post("/api/v1/auth/logout")
        
        assert response.status_code == 401
