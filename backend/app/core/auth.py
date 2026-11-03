"""Signed JWT sessions with persistent server-side revocation."""

import hashlib
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

import jwt
from fastapi import HTTPException, Request

from app.core.config import get_settings

SESSION_DB = Path(__file__).resolve().parents[2] / ".data" / "sessions.sqlite3"


@contextmanager
def database():
    SESSION_DB.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(SESSION_DB)
    try:
        with connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, credential_hash TEXT NOT NULL)"
            )
            yield connection
    finally:
        connection.close()


def credential_hash(username: str, password: str) -> str:
    return hashlib.sha256(f"{username}\0{password}".encode()).hexdigest()


def login(username: str, password: str) -> dict[str, str]:
    settings = get_settings()
    if not settings.auth_username or not settings.auth_password:
        raise HTTPException(
            503,
            "Login is not configured. Set AUTH_USERNAME and AUTH_PASSWORD on the backend.",
        )
    valid_user = secrets.compare_digest(
        username.encode(), settings.auth_username.encode()
    )
    valid_password = secrets.compare_digest(
        password.encode(), settings.auth_password.encode()
    )
    if not (valid_user and valid_password):
        raise HTTPException(401, "Invalid username or password")
    if not settings.jwt_secret or len(settings.jwt_secret.encode()) < 32:
        raise HTTPException(
            503,
            "Set JWT_SECRET to a strong secret of at least 32 bytes on the backend.",
        )
    token = jwt.encode(
        {
            "sub": username,
            "jti": secrets.token_urlsafe(32),
            "iat": int(time.time()),
            "iss": "recon-ai",
            "aud": "recon-ai-frontend",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    with database() as connection:
        connection.execute(
            "INSERT INTO sessions VALUES (?, ?, ?)",
            (
                hashlib.sha256(token.encode()).hexdigest(),
                username,
                credential_hash(settings.auth_username, settings.auth_password),
            ),
        )
    return {"token": token, "username": username}


def session(request: Request) -> tuple[str, str]:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token or len(token) > 8192:
        raise HTTPException(401, "Sign in to continue")
    settings = get_settings()
    if not settings.jwt_secret or len(settings.jwt_secret.encode()) < 32:
        raise HTTPException(401, "Session is no longer valid. Sign in again.")
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer="recon-ai",
            audience="recon-ai-frontend",
            options={"require": ["sub", "jti", "iat", "iss", "aud"]},
        )
        if (
            not isinstance(claims["sub"], str)
            or not isinstance(claims["jti"], str)
            or not claims["jti"]
        ):
            raise jwt.InvalidTokenError()
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Session is no longer valid. Sign in again.") from None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with database() as connection:
        row = connection.execute(
            "SELECT username, credential_hash FROM sessions WHERE token_hash = ?",
            (token_hash,),
        ).fetchone()
    if not row or not settings.auth_username or not settings.auth_password:
        raise HTTPException(401, "Session is no longer valid. Sign in again.")
    if (
        row[0] != claims["sub"]
        or row[0] != settings.auth_username
        or not secrets.compare_digest(
            row[1], credential_hash(settings.auth_username, settings.auth_password)
        )
    ):
        raise HTTPException(401, "Session is no longer valid. Sign in again.")
    return row[0], token_hash


def logout(token_hash: str) -> None:
    with database() as connection:
        connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
