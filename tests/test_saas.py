"""Tests for the SaaS platform: auth, knowledge bases, conversations, documents, and admin."""

import json
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from rag_system.database.models import Base, User
from rag_system.database.engine import get_db
from rag_system.auth.jwt_handler import (
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

# Use in-memory SQLite with StaticPool so all connections share one DB
TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _setup_db():
    """Create tables before each test and drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    """TestClient with a mock pipeline so the real LLM isn't loaded."""
    from unittest.mock import MagicMock
    from rag_system.api.server import create_app

    mock_pipeline = MagicMock()
    mock_pipeline.llm = None
    mock_pipeline.ingestion = MagicMock()
    mock_pipeline.ingestion.vector_store = None

    app = create_app(pipeline=mock_pipeline)
    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


def _signup(client, email="test@example.com", password="testpass123"):
    return client.post("/auth/signup", json={"email": email, "password": password, "full_name": "Test User"})


def _auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


# ── JWT & Password Tests ──────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("mysecret")
        assert verify_password("mysecret", hashed)
        assert not verify_password("wrongpass", hashed)

    def test_hash_is_different_each_time(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2


class TestJWT:
    def test_create_and_decode_access_token(self):
        token = create_access_token("user123", "user")
        payload = decode_token(token)
        assert payload["sub"] == "user123"
        assert payload["role"] == "user"
        assert payload["type"] == "access"

    def test_create_and_decode_refresh_token(self):
        token = create_refresh_token("user456")
        payload = decode_token(token)
        assert payload["sub"] == "user456"
        assert payload["type"] == "refresh"

    def test_password_reset_token(self):
        token = create_password_reset_token("user789")
        payload = decode_token(token)
        assert payload["sub"] == "user789"
        assert payload["type"] == "password_reset"


# ── Auth API Tests ────────────────────────────────────────────────────────

class TestAuthSignup:
    def test_signup_success(self, client):
        resp = _signup(client)
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["role"] == "user"

    def test_signup_duplicate_email(self, client):
        _signup(client)
        resp = _signup(client)
        assert resp.status_code == 409

    def test_signup_short_password(self, client):
        resp = client.post("/auth/signup", json={"email": "a@b.com", "password": "short"})
        assert resp.status_code == 422

    def test_signup_invalid_email(self, client):
        resp = client.post("/auth/signup", json={"email": "notanemail", "password": "testpass123"})
        assert resp.status_code == 422


class TestAuthLogin:
    def test_login_success(self, client):
        _signup(client)
        resp = client.post("/auth/login", json={"email": "test@example.com", "password": "testpass123"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client):
        _signup(client)
        resp = client.post("/auth/login", json={"email": "test@example.com", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/auth/login", json={"email": "no@one.com", "password": "testpass123"})
        assert resp.status_code == 401


class TestAuthRefresh:
    def test_refresh_token(self, client):
        signup_resp = _signup(client)
        refresh = signup_resp.json()["refresh_token"]
        resp = client.post("/auth/refresh", json={"refresh_token": refresh})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_refresh_with_invalid_token(self, client):
        resp = client.post("/auth/refresh", json={"refresh_token": "invalid"})
        assert resp.status_code == 401


class TestPasswordReset:
    def test_password_reset_request(self, client):
        _signup(client)
        resp = client.post("/auth/password-reset-request", json={"email": "test@example.com"})
        assert resp.status_code == 200

    def test_password_reset_nonexistent_email(self, client):
        resp = client.post("/auth/password-reset-request", json={"email": "no@one.com"})
        # Should still return 200 to prevent email enumeration
        assert resp.status_code == 200

    def test_password_reset_confirm(self, client):
        signup_resp = _signup(client)
        user_id = signup_resp.json()["user_id"]
        reset_token = create_password_reset_token(user_id)
        resp = client.post("/auth/password-reset-confirm", json={"token": reset_token, "new_password": "newpass1234"})
        assert resp.status_code == 200
        # Now login with new password
        resp = client.post("/auth/login", json={"email": "test@example.com", "password": "newpass1234"})
        assert resp.status_code == 200


# ── Knowledge Base Tests ──────────────────────────────────────────────────

class TestKnowledgeBases:
    def _get_token(self, client):
        return _signup(client).json()["access_token"]

    def test_create_kb(self, client):
        token = self._get_token(client)
        resp = client.post("/knowledge-bases", json={"name": "My KB", "description": "Test"}, headers=_auth_header(token))
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My KB"
        assert data["status"] == "active"

    def test_list_kbs(self, client):
        token = self._get_token(client)
        client.post("/knowledge-bases", json={"name": "KB 1"}, headers=_auth_header(token))
        client.post("/knowledge-bases", json={"name": "KB 2"}, headers=_auth_header(token))
        resp = client.get("/knowledge-bases", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["total"] == 2

    def test_get_kb(self, client):
        token = self._get_token(client)
        create_resp = client.post("/knowledge-bases", json={"name": "Test KB"}, headers=_auth_header(token))
        kb_id = create_resp.json()["id"]
        resp = client.get(f"/knowledge-bases/{kb_id}", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test KB"

    def test_update_kb(self, client):
        token = self._get_token(client)
        create_resp = client.post("/knowledge-bases", json={"name": "Old"}, headers=_auth_header(token))
        kb_id = create_resp.json()["id"]
        resp = client.patch(f"/knowledge-bases/{kb_id}", json={"name": "New"}, headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"

    def test_delete_kb(self, client):
        token = self._get_token(client)
        create_resp = client.post("/knowledge-bases", json={"name": "Delete Me"}, headers=_auth_header(token))
        kb_id = create_resp.json()["id"]
        resp = client.delete(f"/knowledge-bases/{kb_id}", headers=_auth_header(token))
        assert resp.status_code == 204
        resp = client.get(f"/knowledge-bases/{kb_id}", headers=_auth_header(token))
        assert resp.status_code == 404

    def test_kb_isolation(self, client):
        """Users cannot see each other's knowledge bases."""
        token1 = _signup(client, "user1@test.com").json()["access_token"]
        token2 = _signup(client, "user2@test.com").json()["access_token"]
        client.post("/knowledge-bases", json={"name": "User1 KB"}, headers=_auth_header(token1))
        resp = client.get("/knowledge-bases", headers=_auth_header(token2))
        assert resp.json()["total"] == 0

    def test_unauthenticated_access(self, client):
        resp = client.get("/knowledge-bases")
        assert resp.status_code in (401, 403)


# ── Conversation Tests ────────────────────────────────────────────────────

class TestConversations:
    def _get_token(self, client):
        return _signup(client).json()["access_token"]

    def test_create_conversation(self, client):
        token = self._get_token(client)
        resp = client.post("/conversations", json={"title": "Test Chat"}, headers=_auth_header(token))
        assert resp.status_code == 201
        assert resp.json()["title"] == "Test Chat"

    def test_list_conversations(self, client):
        token = self._get_token(client)
        client.post("/conversations", json={"title": "Chat 1"}, headers=_auth_header(token))
        client.post("/conversations", json={"title": "Chat 2"}, headers=_auth_header(token))
        resp = client.get("/conversations", headers=_auth_header(token))
        assert resp.json()["total"] == 2

    def test_get_conversation_detail(self, client):
        token = self._get_token(client)
        create_resp = client.post("/conversations", json={"title": "Detailed"}, headers=_auth_header(token))
        conv_id = create_resp.json()["id"]
        resp = client.get(f"/conversations/{conv_id}", headers=_auth_header(token))
        assert resp.status_code == 200
        assert "messages" in resp.json()

    def test_update_conversation(self, client):
        token = self._get_token(client)
        create_resp = client.post("/conversations", json={}, headers=_auth_header(token))
        conv_id = create_resp.json()["id"]
        resp = client.patch(f"/conversations/{conv_id}", json={"title": "Updated", "is_pinned": True}, headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"
        assert resp.json()["is_pinned"] is True

    def test_delete_conversation(self, client):
        token = self._get_token(client)
        create_resp = client.post("/conversations", json={}, headers=_auth_header(token))
        conv_id = create_resp.json()["id"]
        resp = client.delete(f"/conversations/{conv_id}", headers=_auth_header(token))
        assert resp.status_code == 204

    def test_conversation_isolation(self, client):
        token1 = _signup(client, "a@test.com").json()["access_token"]
        token2 = _signup(client, "b@test.com").json()["access_token"]
        create_resp = client.post("/conversations", json={"title": "Private"}, headers=_auth_header(token1))
        conv_id = create_resp.json()["id"]
        resp = client.get(f"/conversations/{conv_id}", headers=_auth_header(token2))
        assert resp.status_code == 404


# ── Admin Tests ───────────────────────────────────────────────────────────

class TestAdmin:
    def _make_admin(self, client):
        """Create a user and promote to admin directly in DB."""
        signup_resp = _signup(client, "admin@test.com")
        user_id = signup_resp.json()["user_id"]
        db = TestSessionLocal()
        user = db.query(User).filter(User.id == user_id).first()
        user.role = "admin"
        db.commit()
        db.close()
        # Get a new token with admin role
        token = create_access_token(user_id, "admin")
        return token

    def test_admin_metrics(self, client):
        token = self._make_admin(client)
        resp = client.get("/admin/metrics", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_users" in data
        assert "total_documents" in data
        assert "error_rate" in data

    def test_admin_list_users(self, client):
        token = self._make_admin(client)
        _signup(client, "user@test.com")
        resp = client.get("/admin/users", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.json()["total"] >= 2

    def test_non_admin_denied(self, client):
        token = _signup(client, "user@test.com").json()["access_token"]
        resp = client.get("/admin/metrics", headers=_auth_header(token))
        assert resp.status_code == 403

    def test_analytics_endpoint(self, client):
        token = _signup(client).json()["access_token"]
        resp = client.get("/analytics/queries?days=7", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_queries" in data
        assert "queries_by_day" in data


# ── Existing Endpoints Still Work ─────────────────────────────────────────

class TestLegacyEndpoints:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Agentic RAG" in resp.json()["message"]

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
