"""
Tests for AI Analyzer API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from models.schemas import AnalysisResponse, IssueSeverity, IssueCategory, AnalysisIssue
from config import AnalyzerConfig, ModelConfig, ModelProvider


@pytest.fixture
def client():
    """Create test client with mocked analyzer."""
    # Configure test environment
    test_config = AnalyzerConfig(
        require_authentication=False,  # Disable auth for tests
        model=ModelConfig(
            provider=ModelProvider.OPENAI,
            model_name="gpt-4-test",
            api_key="test-key"
        )
    )

    with patch('config.get_config', return_value=test_config):
        with patch('analyzer.factory.get_analyzer') as mock_get_analyzer:
            # Mock analyzer
            mock_analyzer = Mock()
            mock_analyzer.analyze.return_value = AnalysisResponse(
                query_id="test-123",
                issues_found=1,
                issues=[
                    AnalysisIssue(
                        severity=IssueSeverity.HIGH,
                        category=IssueCategory.MISSING_INDEX,
                        title="Missing index on user_id",
                        description="Full table scan detected",
                        suggestion="CREATE INDEX idx_user_id ON orders(user_id);"
                    )
                ],
                overall_assessment="Query has performance issues",
                optimization_priority=IssueSeverity.HIGH,
                ai_model_used="gpt-4-test",
                analysis_time_ms=100.5
            )
            mock_analyzer.get_stats.return_value = {
                'total_analyses': 10,
                'total_issues_found': 5,
                'average_analysis_time_ms': 150.0
            }
            mock_get_analyzer.return_value = mock_analyzer

            with TestClient(app) as test_client:
                yield test_client


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns 200 OK."""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "service" in data
        assert "model_provider" in data
        assert "uptime_seconds" in data


class TestAnalyzeEndpoint:
    """Tests for analyze endpoint."""

    def test_analyze_valid_query(self, client):
        """Test analyzing valid SQL query."""
        request_data = {
            "sql_query": "SELECT * FROM users WHERE id = 1",
            "database_type": "postgresql"
        }

        response = client.post("/api/v1/analyze", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "query_id" in data
        assert "issues_found" in data
        assert "issues" in data
        assert data["issues_found"] >= 0

    def test_analyze_with_metrics(self, client):
        """Test analyzing query with execution metrics."""
        request_data = {
            "sql_query": "SELECT * FROM orders WHERE user_id IN (SELECT id FROM users)",
            "database_type": "mysql",
            "execution_time_ms": 2500.5,
            "rows_examined": 100000,
            "rows_returned": 50
        }

        response = client.post("/api/v1/analyze", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["issues_found"] > 0
        assert len(data["issues"]) > 0
        assert data["ai_model_used"] == "gpt-4-test"

    def test_analyze_empty_query(self, client):
        """Test analyzing empty query returns error."""
        request_data = {
            "sql_query": "",
            "database_type": "postgresql"
        }

        response = client.post("/api/v1/analyze", json=request_data)

        assert response.status_code == 422  # Validation error

    def test_analyze_invalid_database_type(self, client):
        """Test invalid database type returns error."""
        request_data = {
            "sql_query": "SELECT * FROM users",
            "database_type": "invalid_db"
        }

        response = client.post("/api/v1/analyze", json=request_data)

        assert response.status_code == 422  # Validation error


class TestBatchAnalyzeEndpoint:
    """Tests for batch analyze endpoint."""

    def test_batch_analyze(self, client):
        """Test batch analysis of multiple queries."""
        request_data = {
            "queries": [
                {
                    "sql_query": "SELECT * FROM users WHERE id = 1",
                    "database_type": "postgresql"
                },
                {
                    "sql_query": "SELECT * FROM orders",
                    "database_type": "mysql"
                }
            ],
            "parallel": True
        }

        response = client.post("/api/v1/analyze/batch", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["total_queries"] == 2
        assert data["successful"] >= 0
        assert "results" in data
        assert "errors" in data

    def test_batch_analyze_empty_list(self, client):
        """Test batch analysis with empty query list."""
        request_data = {
            "queries": [],
            "parallel": True
        }

        response = client.post("/api/v1/analyze/batch", json=request_data)

        assert response.status_code == 422  # Validation error


class TestStatsEndpoint:
    """Tests for statistics endpoints."""

    def test_get_stats(self, client):
        """Test getting analyzer statistics."""
        response = client.get("/api/v1/stats")

        assert response.status_code == 200
        data = response.json()

        assert "statistics" in data
        assert "total_analyses" in data["statistics"]

    def test_reset_stats(self, client):
        """Test resetting statistics."""
        response = client.post("/api/v1/stats/reset")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"


class TestAuthentication:
    """Tests for API key authentication."""

    @pytest.fixture
    def auth_client(self):
        """Create test client with authentication enabled."""
        test_config = AnalyzerConfig(
            require_authentication=True,
            allowed_api_keys=["test-api-key-123"],
            model=ModelConfig(
                provider=ModelProvider.OPENAI,
                model_name="gpt-4-test",
                api_key="test-key"
            )
        )

        with patch('config.get_config', return_value=test_config):
            with patch('analyzer.factory.get_analyzer') as mock_get_analyzer:
                mock_analyzer = Mock()
                mock_analyzer.analyze.return_value = AnalysisResponse(
                    query_id="test-123",
                    issues_found=0,
                    issues=[],
                    overall_assessment="OK",
                    optimization_priority=IssueSeverity.INFO,
                    ai_model_used="gpt-4-test",
                    analysis_time_ms=50.0
                )
                mock_get_analyzer.return_value = mock_analyzer

                with TestClient(app) as test_client:
                    yield test_client

    def test_analyze_without_api_key(self, auth_client):
        """Test analyze endpoint requires API key."""
        request_data = {
            "sql_query": "SELECT * FROM users",
            "database_type": "postgresql"
        }

        response = auth_client.post("/api/v1/analyze", json=request_data)

        assert response.status_code == 401

    def test_analyze_with_invalid_api_key(self, auth_client):
        """Test analyze endpoint rejects invalid API key."""
        request_data = {
            "sql_query": "SELECT * FROM users",
            "database_type": "postgresql"
        }

        response = auth_client.post(
            "/api/v1/analyze",
            json=request_data,
            headers={"X-API-Key": "invalid-key"}
        )

        assert response.status_code == 403

    def test_analyze_with_valid_api_key(self, auth_client):
        """Test analyze endpoint accepts valid API key."""
        request_data = {
            "sql_query": "SELECT * FROM users",
            "database_type": "postgresql"
        }

        response = auth_client.post(
            "/api/v1/analyze",
            json=request_data,
            headers={"X-API-Key": "test-api-key-123"}
        )

        assert response.status_code == 200
