import os
import sys
import pytest
from fastapi.testclient import TestClient

# Ensure app path is in system path for testing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app

client = TestClient(app)

def test_login_success():
    """Verify local authentication login and JWT generation."""
    response = client.post(
        "/auth/login",
        json={"email": "admin@company.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "Admin"

def test_google_auth_redirect():
    """Verify Google OAuth redirect URL generator endpoint."""
    response = client.get("/auth/google")
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "accounts.google.com" in data["url"]

def test_chat_unauthorized():
    """Verify that chatting without a valid token is blocked."""
    response = client.post(
        "/chat",
        json={"message": "Find Rahul", "token": "invalid-token"}
    )
    assert response.status_code == 401
