"""
Tests for user management endpoints.

Tests:
- Get user profile
- Update user profile
- Change password
- Get user sessions
- Delete account
"""
import pytest
from fastapi.testclient import TestClient


class TestUserProfile:
    """Test user profile management."""
    
    def test_get_user_profile(self, client: TestClient, superuser_token: str):
        """Get current user profile."""
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "full_name" in data
        assert "created_at" in data
    
    def test_update_profile_success(self, client: TestClient, superuser_token: str):
        """Update user profile successfully."""
        response = client.put(
            "/api/v1/users/profile",
            json={
                "full_name": "Updated Name",
                "preferences": {"theme": "dark", "language": "en"}
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["preferences"]["theme"] == "dark"
    
    def test_update_profile_without_auth_fails(self, client: TestClient):
        """Update profile without auth fails."""
        response = client.put(
            "/api/v1/users/profile",
            json={"full_name": "Updated Name"}
        )
        
        assert response.status_code == 401


class TestPasswordChange:
    """Test password change functionality."""
    
    def test_change_password_success(self, client: TestClient):
        """Change password successfully."""
        # Register user
        reg_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@test.com",
                "password": "OldPassword123!@#",
                "full_name": "Test User"
            }
        )
        token = reg_response.json()["access_token"]
        
        # Change password
        response = client.post(
            "/api/v1/users/password",
            json={
                "current_password": "OldPassword123!@#",
                "new_password": "NewPassword123!@#"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        
        # Login with new password
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@test.com",
                "password": "NewPassword123!@#"
            }
        )
        
        assert login_response.status_code == 200
    
    def test_change_password_wrong_current_fails(self, client: TestClient, superuser_token: str):
        """Change password with wrong current password fails."""
        response = client.post(
            "/api/v1/users/password",
            json={
                "current_password": "WrongPassword123!@#",
                "new_password": "NewPassword123!@#"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 400
    
    def test_change_password_weak_new_fails(self, client: TestClient, superuser_token: str):
        """Change password to weak password fails."""
        response = client.post(
            "/api/v1/users/password",
            json={
                "current_password": "Admin123!@#",
                "new_password": "weak"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 422


class TestUserSessions:
    """Test user session management."""
    
    def test_get_user_sessions(self, client: TestClient, superuser_token: str):
        """Get list of user sessions."""
        response = client.get(
            "/api/v1/users/sessions",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data or isinstance(data, list)
    
    def test_revoke_session(self, client: TestClient):
        """Revoke a specific session."""
        # Register and get token
        reg_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@test.com",
                "password": "Test123!@#",
                "full_name": "Test User"
            }
        )
        token = reg_response.json()["access_token"]
        
        # Get sessions
        sessions_response = client.get(
            "/api/v1/users/sessions",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if sessions_response.status_code == 200:
            sessions = sessions_response.json()
            if isinstance(sessions, dict) and "sessions" in sessions:
                sessions = sessions["sessions"]
            
            if len(sessions) > 0:
                session_id = sessions[0]["id"]
                
                # Revoke session
                revoke_response = client.delete(
                    f"/api/v1/users/sessions/{session_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                
                assert revoke_response.status_code in [200, 204]


class TestAccountDeletion:
    """Test account deletion."""
    
    def test_delete_account(self, client: TestClient):
        """Delete user account."""
        # Register user
        reg_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@test.com",
                "password": "Test123!@#",
                "full_name": "Test User"
            }
        )
        token = reg_response.json()["access_token"]
        
        # Delete account
        response = client.delete(
            "/api/v1/users/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code in [200, 204]
        
        # Try to login after deletion
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@test.com",
                "password": "Test123!@#"
            }
        )
        
        assert login_response.status_code == 401
