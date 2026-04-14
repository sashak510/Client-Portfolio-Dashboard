"""Tests for user registration and JWT authentication."""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
class TestRegistration:
    def test_register_success(self, api_client: APIClient) -> None:
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepass123",
            "password_confirm": "securepass123",
        }
        response = api_client.post("/api/auth/register/", data)
        assert response.status_code == 201
        assert response.data["username"] == "newuser"
        assert User.objects.filter(username="newuser").exists()

    def test_register_password_mismatch(self, api_client: APIClient) -> None:
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "securepass123",
            "password_confirm": "different123",
        }
        response = api_client.post("/api/auth/register/", data)
        assert response.status_code == 400


@pytest.mark.django_db
class TestLogin:
    def test_token_obtain(self, api_client: APIClient) -> None:
        User.objects.create_user(username="testuser", password="testpass123")
        response = api_client.post(
            "/api/auth/token/",
            {"username": "testuser", "password": "testpass123"},
        )
        assert response.status_code == 200
        assert "access" in response.data
        assert "refresh" in response.data

    def test_token_refresh(self, api_client: APIClient) -> None:
        User.objects.create_user(username="testuser", password="testpass123")
        token_response = api_client.post(
            "/api/auth/token/",
            {"username": "testuser", "password": "testpass123"},
        )
        refresh = token_response.data["refresh"]
        response = api_client.post("/api/auth/token/refresh/", {"refresh": refresh})
        assert response.status_code == 200
        assert "access" in response.data
