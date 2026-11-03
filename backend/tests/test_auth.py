import hashlib
import sqlite3
from contextlib import closing

import jwt
import pytest
from fastapi.testclient import TestClient

from app.core import auth
from app.main import create_app


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("AUTH_USERNAME", "admin")
    monkeypatch.setenv("AUTH_PASSWORD", "test-password")
    monkeypatch.setenv("JWT_SECRET", "test-signing-secret-with-at-least-32-bytes")
    monkeypatch.setattr(auth, "SESSION_DB", tmp_path / "sessions.sqlite3")
    with TestClient(create_app()) as client:
        yield client


def sign_in(client):
    response = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "test-password"}
    )
    assert response.status_code == 200
    return response.json()["token"]


def test_login_persists_and_signout_revokes(client):
    token = sign_in(client)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/auth/me", headers=headers).json() == {
        "username": "admin"
    }
    # A fresh app instance still recognizes the saved session.
    with TestClient(create_app()) as restarted:
        assert restarted.get("/api/v1/auth/me", headers=headers).status_code == 200
    with closing(sqlite3.connect(auth.SESSION_DB)) as db:
        row = db.execute("SELECT token_hash FROM sessions").fetchone()
        assert row[0] == hashlib.sha256(token.encode()).hexdigest()
        assert row[0] != token
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_login_fails_with_wrong_credentials(client):
    for username, password in [("admin", "wrong"), ("wrong", "test-password")]:
        assert (
            client.post(
                "/api/v1/auth/login", json={"username": username, "password": password}
            ).status_code
            == 401
        )


def test_unconfigured_login_fails_closed(client, monkeypatch):
    monkeypatch.delenv("AUTH_PASSWORD")
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "test-password"},
        ).status_code
        == 503
    )
    assert (
        client.post("/api/v1/recon", json={"target": "example.com"}).status_code == 401
    )


def test_protected_endpoints_reject_missing_and_forged_tokens(client):
    for headers in [{}, {"Authorization": "Bearer forged"}]:
        assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
        assert (
            client.post(
                "/api/v1/recon", headers=headers, json={"target": "example.com"}
            ).status_code
            == 401
        )
    for path in [
        "/api/v1/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/missing",
        "/api/v1/auth/login",
    ]:
        assert client.get(path).status_code == 401
    assert client.options("/api/v1/health").status_code == 401
    token = sign_in(client)
    headers = {"Authorization": f"Bearer {token}"}
    for path in ["/api/v1/health", "/docs", "/redoc", "/openapi.json"]:
        assert client.get(path, headers=headers).status_code == 200


def test_credential_change_invalidates_session(client, monkeypatch):
    token = sign_in(client)
    monkeypatch.setenv("AUTH_PASSWORD", "new-password")
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        ).status_code
        == 401
    )


def test_jwt_claims_and_tampering(client):
    token = sign_in(client)
    claims = jwt.decode(
        token,
        "test-signing-secret-with-at-least-32-bytes",
        algorithms=["HS256"],
        audience="recon-ai-frontend",
        issuer="recon-ai",
    )
    assert claims["sub"] == "admin"
    assert claims["jti"]
    assert "iat" in claims
    assert "exp" not in claims
    claims["sub"] = "someone-else"
    forged = jwt.encode(
        claims, "a-different-signing-key-with-32-bytes", algorithm="HS256"
    )
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {forged}"}
        ).status_code
        == 401
    )
    unsigned = jwt.encode(claims, "", algorithm="none")
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {unsigned}"}
        ).status_code
        == 401
    )


def test_secret_rotation_revokes_existing_tokens(client, monkeypatch):
    token = sign_in(client)
    monkeypatch.setenv("JWT_SECRET", "replacement-secret-with-at-least-32-bytes")
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
        ).status_code
        == 401
    )
    new_token = sign_in(client)
    assert (
        client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {new_token}"}
        ).status_code
        == 200
    )


@pytest.mark.parametrize("secret", ["", "short"])
def test_missing_or_weak_jwt_secret_fails_closed(client, monkeypatch, secret):
    monkeypatch.setenv("JWT_SECRET", secret)
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "test-password"},
        ).status_code
        == 503
    )


def test_authenticated_chat_route(client, monkeypatch):
    from unittest.mock import AsyncMock

    from app.api import routes
    from app.api.schemas import ChatResponse

    workflow = AsyncMock(
        return_value=ChatResponse(message="Answer", source="s3://bucket/key")
    )
    monkeypatch.setattr(routes, "run_chat_workflow", workflow)
    assert client.post("/api/v1/chat", json={"question": "Explain"}).status_code == 401
    token = sign_in(client)
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/v1/chat", headers=headers, json={"question": "Explain"}
    )
    assert response.json() == {
        "message": "Answer",
        "source": "s3://bucket/key",
        "sources": [],
    }
    workflow.assert_awaited_once_with("Explain")
    assert (
        client.post(
            "/api/v1/chat", headers=headers, json={"question": "  "}
        ).status_code
        == 422
    )


def test_chat_timeout_returns_clear_504(client, monkeypatch):
    from unittest.mock import AsyncMock

    import httpx
    from openai import APITimeoutError

    from app.api import routes
    from app.service.llm.base import ModelError

    error = ModelError("Model request timed out")
    error.__cause__ = APITimeoutError(
        request=httpx.Request("POST", "https://example.com")
    )
    monkeypatch.setattr(routes, "run_chat_workflow", AsyncMock(side_effect=error))
    token = sign_in(client)
    response = client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={"question": "Analyze my EC2 instances."},
    )
    assert response.status_code == 504
    assert (
        response.json()["error"]["message"]
        == "The model timed out. Please retry your question."
    )
