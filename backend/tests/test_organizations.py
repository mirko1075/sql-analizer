"""
Tests for organization management endpoints.

Tests:
- Create organization (superuser only)
- List organizations
- Get organization by ID
- Update organization
- Delete organization
- Access control
"""
import pytest
from fastapi.testclient import TestClient


class TestOrganizationCreation:
    """Test organization creation."""
    
    def test_create_organization_as_superuser(self, client: TestClient, superuser_token: str):
        """Superuser can create organization."""
        response = client.post(
            "/api/v1/organizations",
            json={
                "name": "Test Organization",
                "slug": "test-org",
                "description": "A test organization"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Organization"
        assert data["slug"] == "test-org"
        assert "id" in data
    
    def test_create_organization_as_regular_user_fails(self, client: TestClient, regular_user_token: str):
        """Regular user cannot create organization."""
        response = client.post(
            "/api/v1/organizations",
            json={
                "name": "Test Organization",
                "slug": "test-org"
            },
            headers={"Authorization": f"Bearer {regular_user_token}"}
        )
        
        assert response.status_code == 403
    
    def test_create_organization_duplicate_slug_fails(self, client: TestClient, superuser_token: str):
        """Cannot create organization with duplicate slug."""
        # Create first organization
        client.post(
            "/api/v1/organizations",
            json={
                "name": "Organization 1",
                "slug": "test-org"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        # Try to create second with same slug
        response = client.post(
            "/api/v1/organizations",
            json={
                "name": "Organization 2",
                "slug": "test-org"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 400
    
    def test_create_organization_without_auth_fails(self, client: TestClient):
        """Cannot create organization without authentication."""
        response = client.post(
            "/api/v1/organizations",
            json={
                "name": "Test Organization",
                "slug": "test-org"
            }
        )
        
        assert response.status_code == 401


class TestOrganizationRetrieval:
    """Test organization retrieval."""
    
    def test_list_organizations(self, client: TestClient, superuser_token: str, organization_id: str):
        """List all organizations."""
        response = client.get(
            "/api/v1/organizations",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_get_organization_by_id(self, client: TestClient, superuser_token: str, organization_id: str):
        """Get specific organization by ID."""
        response = client.get(
            f"/api/v1/organizations/{organization_id}",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == organization_id
        assert "name" in data
        assert "slug" in data
    
    def test_get_nonexistent_organization_fails(self, client: TestClient, superuser_token: str):
        """Get non-existent organization fails."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(
            f"/api/v1/organizations/{fake_id}",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 404


class TestOrganizationUpdate:
    """Test organization updates."""
    
    def test_update_organization(self, client: TestClient, superuser_token: str, organization_id: str):
        """Update organization details."""
        response = client.put(
            f"/api/v1/organizations/{organization_id}",
            json={
                "name": "Updated Organization Name",
                "description": "Updated description"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Organization Name"
        assert data["description"] == "Updated description"
    
    def test_update_organization_as_regular_user_fails(
        self, client: TestClient, regular_user_token: str, organization_id: str
    ):
        """Regular user cannot update organization."""
        response = client.put(
            f"/api/v1/organizations/{organization_id}",
            json={"name": "Updated Name"},
            headers={"Authorization": f"Bearer {regular_user_token}"}
        )
        
        assert response.status_code == 403


class TestOrganizationDeletion:
    """Test organization deletion."""
    
    def test_delete_organization(self, client: TestClient, superuser_token: str):
        """Delete organization."""
        # Create organization to delete
        create_response = client.post(
            "/api/v1/organizations",
            json={
                "name": "To Delete",
                "slug": "to-delete"
            },
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        org_id = create_response.json()["id"]
        
        # Delete it
        response = client.delete(
            f"/api/v1/organizations/{org_id}",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code in [200, 204]
        
        # Verify it's deleted
        get_response = client.get(
            f"/api/v1/organizations/{org_id}",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert get_response.status_code == 404
    
    def test_delete_organization_as_regular_user_fails(
        self, client: TestClient, regular_user_token: str, organization_id: str
    ):
        """Regular user cannot delete organization."""
        response = client.delete(
            f"/api/v1/organizations/{organization_id}",
            headers={"Authorization": f"Bearer {regular_user_token}"}
        )
        
        assert response.status_code == 403
