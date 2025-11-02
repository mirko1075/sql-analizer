"""
Tests for team management endpoints.

Tests:
- Create team
- List teams
- Get team by ID
- Update team
- Delete team
- Add/remove team members
- Team member roles (RBAC)
- Team-based access control
"""
import pytest
from fastapi.testclient import TestClient


class TestTeamCreation:
    """Test team creation."""
    
    def test_create_team(self, client: TestClient, superuser_token: str, organization_id: str):
        """Create a new team."""
        response = client.post(
            "/api/v1/teams",
            json={
                "name": "Development Team",
                "slug": "dev-team",
                "organization_id": organization_id,
                "description": "Development team"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Development Team"
        assert data["slug"] == "dev-team"
        assert "id" in data
    
    def test_create_team_without_org_fails(self, client: TestClient, superuser_token: str):
        """Cannot create team without organization."""
        response = client.post(
            "/api/v1/teams",
            json={
                "name": "Team",
                "slug": "team"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 422
    
    def test_create_team_duplicate_slug_fails(
        self, client: TestClient, superuser_token: str, organization_id: str
    ):
        """Cannot create team with duplicate slug in same org."""
        # Create first team
        client.post(
            "/api/v1/teams",
            json={
                "name": "Team 1",
                "slug": "team",
                "organization_id": organization_id
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        # Try to create second with same slug
        response = client.post(
            "/api/v1/teams",
            json={
                "name": "Team 2",
                "slug": "team",
                "organization_id": organization_id
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 400


class TestTeamRetrieval:
    """Test team retrieval."""
    
    def test_list_teams(self, client: TestClient, superuser_token: str, team_id: str):
        """List all teams user has access to."""
        response = client.get(
            "/api/v1/teams",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_get_team_by_id(self, client: TestClient, superuser_token: str, team_id: str):
        """Get specific team by ID."""
        response = client.get(
            f"/api/v1/teams/{team_id}",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == team_id
        assert "name" in data
        assert "slug" in data
    
    def test_get_team_without_access_fails(self, client: TestClient, regular_user_token: str, team_id: str):
        """Cannot get team without membership."""
        response = client.get(
            f"/api/v1/teams/{team_id}",
            headers={"Authorization": f"Bearer {regular_user_token}"}
        )
        
        # Should fail with 403 or 404
        assert response.status_code in [403, 404]


class TestTeamUpdate:
    """Test team updates."""
    
    def test_update_team(self, client: TestClient, superuser_token: str, team_id: str):
        """Update team details."""
        response = client.put(
            f"/api/v1/teams/{team_id}",
            json={
                "name": "Updated Team Name",
                "description": "Updated description"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Team Name"


class TestTeamMembers:
    """Test team member management."""
    
    def test_add_team_member(self, client: TestClient, superuser_token: str, team_id: str):
        """Add member to team."""
        # First, create a new user to add
        user_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newmember@test.com",
                "password": "Member123!@#",
                "full_name": "New Member"
            }
        )
        new_user_id = user_response.json()["user"]["id"]
        
        # Add to team
        response = client.post(
            f"/api/v1/teams/{team_id}/members",
            json={
                "user_id": new_user_id,
                "role": "MEMBER"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code in [200, 201]
    
    def test_list_team_members(self, client: TestClient, superuser_token: str, team_id: str):
        """List team members."""
        response = client.get(
            f"/api/v1/teams/{team_id}/members",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_update_member_role(self, client: TestClient, superuser_token: str, team_id: str):
        """Update team member role."""
        # First, add a member
        user_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "member2@test.com",
                "password": "Member123!@#",
                "full_name": "Member Two"
            }
        )
        new_user_id = user_response.json()["user"]["id"]
        
        client.post(
            f"/api/v1/teams/{team_id}/members",
            json={
                "user_id": new_user_id,
                "role": "MEMBER"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        # Update role
        response = client.put(
            f"/api/v1/teams/{team_id}/members/{new_user_id}",
            json={"role": "ADMIN"},
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
    
    def test_remove_team_member(self, client: TestClient, superuser_token: str, team_id: str):
        """Remove member from team."""
        # First, add a member
        user_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "member3@test.com",
                "password": "Member123!@#",
                "full_name": "Member Three"
            }
        )
        new_user_id = user_response.json()["user"]["id"]
        
        client.post(
            f"/api/v1/teams/{team_id}/members",
            json={
                "user_id": new_user_id,
                "role": "MEMBER"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        # Remove member
        response = client.delete(
            f"/api/v1/teams/{team_id}/members/{new_user_id}",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code in [200, 204]


class TestTeamRBAC:
    """Test role-based access control."""
    
    def test_viewer_cannot_modify_team(self, client: TestClient, superuser_token: str, team_id: str):
        """VIEWER role cannot modify team."""
        # Create viewer user
        user_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "viewer@test.com",
                "password": "Viewer123!@#",
                "full_name": "Viewer User"
            }
        )
        viewer_token = user_response.json()["access_token"]
        viewer_id = user_response.json()["user"]["id"]
        
        # Add as viewer
        client.post(
            f"/api/v1/teams/{team_id}/members",
            json={
                "user_id": viewer_id,
                "role": "VIEWER"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        # Try to update team
        response = client.put(
            f"/api/v1/teams/{team_id}",
            json={"name": "Hacked Name"},
            headers={"Authorization": f"Bearer {viewer_token}"}
        )
        
        assert response.status_code == 403
    
    def test_member_cannot_add_members(self, client: TestClient, superuser_token: str, team_id: str):
        """MEMBER role cannot add other members."""
        # Create member user
        user_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "member@test.com",
                "password": "Member123!@#",
                "full_name": "Member User"
            }
        )
        member_token = user_response.json()["access_token"]
        member_id = user_response.json()["user"]["id"]
        
        # Add as member
        client.post(
            f"/api/v1/teams/{team_id}/members",
            json={
                "user_id": member_id,
                "role": "MEMBER"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        # Create another user to try to add
        new_user = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.com",
                "password": "New123!@#",
                "full_name": "New User"
            }
        )
        new_user_id = new_user.json()["user"]["id"]
        
        # Try to add new member
        response = client.post(
            f"/api/v1/teams/{team_id}/members",
            json={
                "user_id": new_user_id,
                "role": "MEMBER"
            },
            headers={"Authorization": f"Bearer {member_token}"}
        )
        
        assert response.status_code == 403
