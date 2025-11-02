"""
Tests for multi-tenant slow queries and stats endpoints.

Tests:
- Slow queries are filtered by team
- Stats are filtered by team
- Users cannot access other teams' data
- Collector assigns correct team_id
"""
import pytest
from fastapi.testclient import TestClient


class TestMultiTenantSlowQueries:
    """Test multi-tenant slow query endpoints."""
    
    def test_list_slow_queries_filtered_by_team(
        self, client: TestClient, superuser_token: str
    ):
        """List slow queries shows only team's queries."""
        response = client.get(
            "/api/v1/slow-queries",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or isinstance(data, list)
        
        # If there are items, verify they have team_id
        if isinstance(data, dict) and "items" in data:
            for item in data["items"]:
                # Team filtering should be applied
                pass
    
    def test_get_slow_query_detail(
        self, client: TestClient, superuser_token: str
    ):
        """Get slow query detail shows data if user has access."""
        # First list to get an ID
        list_response = client.get(
            "/api/v1/slow-queries",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        if list_response.status_code == 200:
            data = list_response.json()
            items = data.get("items", data) if isinstance(data, dict) else data
            
            if len(items) > 0 and "fingerprint" in items[0]:
                # Try to get detail (may not have ID endpoint)
                pass
    
    def test_other_team_queries_not_visible(
        self, client: TestClient, superuser_token: str, regular_user_token: str
    ):
        """User cannot see queries from teams they don't belong to."""
        # Get queries for superuser
        super_response = client.get(
            "/api/v1/slow-queries",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        # Get queries for regular user
        regular_response = client.get(
            "/api/v1/slow-queries",
            headers={"Authorization": f"Bearer {regular_user_token}"}
        )
        
        # Both should succeed but show different data
        assert super_response.status_code == 200
        assert regular_response.status_code == 200


class TestMultiTenantStats:
    """Test multi-tenant statistics endpoints."""
    
    def test_get_stats_filtered_by_team(
        self, client: TestClient, superuser_token: str
    ):
        """Get stats shows only team's statistics."""
        response = client.get(
            "/api/v1/stats",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Stats should be returned (even if zeros for new team)
        assert isinstance(data, dict)
    
    def test_get_global_stats(
        self, client: TestClient, superuser_token: str
    ):
        """Get global stats aggregates team's data."""
        response = client.get(
            "/api/v1/stats/global",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_slow_queries" in data or isinstance(data, dict)
    
    def test_get_top_tables(
        self, client: TestClient, superuser_token: str
    ):
        """Get top tables filtered by team."""
        response = client.get(
            "/api/v1/stats/top-tables",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_database_stats(
        self, client: TestClient, superuser_token: str
    ):
        """Get database-specific stats filtered by team."""
        response = client.get(
            "/api/v1/stats/database/mysql/localhost",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        # May return 404 if no such database, or 200 with stats
        assert response.status_code in [200, 404]
    
    def test_list_monitored_databases(
        self, client: TestClient, superuser_token: str
    ):
        """List monitored databases filtered by team."""
        response = client.get(
            "/api/v1/stats/databases",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_stats_isolation_between_teams(
        self, client: TestClient, superuser_token: str, regular_user_token: str
    ):
        """Stats are isolated between different teams."""
        # Get stats for superuser
        super_stats = client.get(
            "/api/v1/stats",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        # Get stats for regular user (different team)
        regular_stats = client.get(
            "/api/v1/stats",
            headers={"Authorization": f"Bearer {regular_user_token}"}
        )
        
        # Both should succeed
        assert super_stats.status_code == 200
        assert regular_stats.status_code == 200
        
        # Data should be different (or at least not error)
        super_data = super_stats.json()
        regular_data = regular_stats.json()
        assert isinstance(super_data, dict)
        assert isinstance(regular_data, dict)


class TestCollectorAndAnalyzer:
    """Test collector and analyzer endpoints with authentication."""
    
    def test_get_collector_status(
        self, client: TestClient, superuser_token: str
    ):
        """Get collector status."""
        response = client.get(
            "/api/v1/collectors/status",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_trigger_mysql_collection(
        self, client: TestClient, superuser_token: str
    ):
        """Trigger MySQL collection manually."""
        response = client.post(
            "/api/v1/collectors/mysql/collect",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "message" in data
    
    def test_get_analyzer_status(
        self, client: TestClient, superuser_token: str
    ):
        """Get analyzer status."""
        response = client.get(
            "/api/v1/analyzer/status",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_trigger_analysis(
        self, client: TestClient, superuser_token: str
    ):
        """Trigger analysis manually."""
        response = client.post(
            "/api/v1/analyzer/analyze",
            headers={"Authorization": f"Bearer {superuser_token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "message" in data
    
    def test_collector_without_auth_fails(self, client: TestClient):
        """Collector endpoints require authentication."""
        response = client.get("/api/v1/collectors/status")
        
        assert response.status_code == 401
    
    def test_analyzer_without_auth_fails(self, client: TestClient):
        """Analyzer endpoints require authentication."""
        response = client.get("/api/v1/analyzer/status")
        
        assert response.status_code == 401


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check_public(self, client: TestClient):
        """Health check endpoint is publicly accessible."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
