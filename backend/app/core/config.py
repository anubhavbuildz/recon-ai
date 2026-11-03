"""Environment configuration, independent of agent logic."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Settings(BaseModel):
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    llm_api_key: str | None = Field(default=None, repr=False)
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_timeout_seconds: float = Field(default=30, gt=0)
    max_tokens: int | None = Field(default=1024, repr=False)
    s3_bucket_name: str | None = None
    s3_region: str | None = None
    s3_object_key: str | None = None
    s3_snapshot_prefix: str | None = None
    s3_history_days: int = Field(default=3, ge=1, le=14)
    s3_max_bytes: int = Field(default=200_000, gt=0, le=2_000_000)
    auth_username: str | None = None
    auth_password: str | None = Field(default=None, repr=False)
    jwt_secret: str | None = Field(default=None, repr=False)


def get_settings() -> Settings:
    values = {
        "llm_api_key": os.getenv("LLM_API_KEY") or None,
        "llm_base_url": os.getenv("LLM_BASE_URL") or None,
        "llm_model": os.getenv("LLM_MODEL") or None,
        "llm_timeout_seconds": os.getenv("LLM_TIMEOUT_SECONDS", "30"),
        "max_tokens": os.getenv("MAX_TOKEN") or None,
        "s3_bucket_name": os.getenv("S3_BUCKET_NAME", "").strip() or None,
        "s3_snapshot_prefix": os.getenv("S3_SNAPSHOT_PREFIX", "").strip() or None,
        "s3_history_days": os.getenv("S3_HISTORY_DAYS", "3"),
        "s3_object_key": os.getenv("S3_OBJECT_KEY") or None,
        "s3_max_bytes": os.getenv("S3_MAX_BYTES", "200000"),
        "s3_region": os.getenv("S3_REGION", "").strip() or None,
        "auth_username": os.getenv("AUTH_USERNAME") or None,
        "auth_password": os.getenv("AUTH_PASSWORD") or None,
        "jwt_secret": os.getenv("JWT_SECRET") or None,
    }
    if "CORS_ORIGINS" in os.environ:
        values["cors_origins"] = [
            x.strip() for x in os.environ["CORS_ORIGINS"].split(",") if x.strip()
        ]
    return Settings(**values)
