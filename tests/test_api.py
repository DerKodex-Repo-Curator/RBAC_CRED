"""
Tests for FastAPI endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os

# Set a mock API key for testing
os.environ["ANTHROPIC_API_KEY"] = "test-api-key"

from src.api.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestAPIEndpoints:
    """Tests for API endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_discover_roles(self, client):
        """Test roles discovery endpoint."""
        response = client.get("/api/discovery/roles")
        assert response.status_code == 200
        data = response.json()
        assert "roles" in data
        assert "permissions" in data
    
    def test_discover_resources(self, client):
        """Test resources discovery endpoint."""
        response = client.get("/api/discovery/resources")
        assert response.status_code == 200
        data = response.json()
        assert "resources" in data
    
    def test_discover_context(self, client):
        """Test context discovery endpoint."""
        response = client.get("/api/discovery/context")
        assert response.status_code == 200
        data = response.json()
        assert "attributes" in data
    
    def test_discover_all(self, client):
        """Test all schemas discovery endpoint."""
        response = client.get("/api/discovery/all")
        assert response.status_code == 200
        data = response.json()
        assert "roles" in data
        assert "resources" in data
        assert "context" in data
    
    def test_create_session(self, client):
        """Test session creation."""
        response = client.post("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
    
    def test_list_sessions(self, client):
        """Test listing sessions."""
        response = client.get("/api/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
    
    def test_get_cache_info(self, client):
        """Test cache info endpoint."""
        response = client.get("/api/discovery/cache-info")
        assert response.status_code == 200
        data = response.json()
        assert "cache_file" in data


class TestChatEndpoint:
    """Tests for chat endpoint (requires mocking Claude)."""
    
    @patch('src.agent.conversation_agent.anthropic.Anthropic')
    def test_chat_help_command(self, mock_anthropic, client):
        """Test chat with help command (doesn't need Claude)."""
        # First create a session with mocked Claude
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        response = client.post(
            "/api/chat",
            json={"message": "help"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "message" in data
    
    @patch('src.agent.conversation_agent.anthropic.Anthropic')
    def test_chat_list_roles(self, mock_anthropic, client):
        """Test chat with list roles command."""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        response = client.post(
            "/api/chat",
            json={"message": "list roles"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "admin" in data["message"].lower() or "roles" in data["message"].lower()
    
    @patch('src.agent.conversation_agent.anthropic.Anthropic')
    def test_chat_list_resources(self, mock_anthropic, client):
        """Test chat with list resources command."""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        
        response = client.post(
            "/api/chat",
            json={"message": "list resources"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "invoice" in data["message"].lower() or "resources" in data["message"].lower()


class TestPolicyEndpoints:
    """Tests for policy management endpoints."""
    
    def test_get_policy_no_session(self, client):
        """Test getting policy for non-existent session."""
        response = client.get("/api/policy/nonexistent-session")
        assert response.status_code == 404
    
    def test_validate_policy_no_session(self, client):
        """Test validating policy for non-existent session."""
        response = client.post("/api/policy/validate/nonexistent-session")
        assert response.status_code == 404
    
    def test_export_policy_no_session(self, client):
        """Test exporting policy for non-existent session."""
        response = client.post("/api/policy/export/nonexistent-session")
        assert response.status_code == 404


class TestEvaluationEndpoints:
    """Tests for policy evaluation endpoints."""
    
    def test_evaluate_no_session(self, client):
        """Test evaluation without valid session."""
        response = client.post(
            "/api/evaluate",
            json={
                "role": "admin",
                "resource": "invoice",
                "permission": "read"
            }
        )
        assert response.status_code == 400
    
    def test_explain_no_session(self, client):
        """Test explain without valid session."""
        response = client.post(
            "/api/evaluate/explain",
            json={
                "role": "admin",
                "resource": "invoice",
                "permission": "read"
            }
        )
        assert response.status_code == 400
