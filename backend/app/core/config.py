"""Environment configuration, independent of agent logic."""
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class Settings(BaseModel):
    cors_origins: list[str] = Field(default_factory=lambda: [
        "http://localhost:5173", "http://127.0.0.1:5173"
    ])
    llm_api_key: str | None = Field(default=None, repr=False)
    llm_base_url: str | None = None
    llm_model: str | None = None
    llm_timeout_seconds: float = Field(default=30, gt=0)


def get_settings() -> Settings:
    values = {
        "llm_api_key": os.getenv("LLM_API_KEY") or None,
        "llm_base_url": os.getenv("LLM_BASE_URL") or None,
        "llm_model": os.getenv("LLM_MODEL") or None,
        "llm_timeout_seconds": os.getenv("LLM_TIMEOUT_SECONDS", "30"),
    }
    if "CORS_ORIGINS" in os.environ:
        values["cors_origins"] = [x.strip() for x in os.environ["CORS_ORIGINS"].split(",") if x.strip()]
    return Settings(**values)
