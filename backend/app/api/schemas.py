"""Public API contracts and purely syntactic target validation (no DNS)."""
import ipaddress
import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReconRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: str = Field(min_length=1, max_length=2048)

    @field_validator("target")
    @classmethod
    def normalize_target(cls, value: str) -> str:
        value = value.strip()
        if not value or any(c.isspace() or ord(c) < 32 for c in value) or "\\" in value:
            raise ValueError("Enter a valid domain or HTTPS URL")
        if "://" in value:
            try:
                parsed = urlsplit(value)
                if parsed.scheme.lower() != "https" or not parsed.netloc:
                    raise ValueError("Only HTTPS URLs are supported")
                if parsed.username is not None or parsed.password is not None:
                    raise ValueError("Embedded credentials are not allowed")
                if parsed.netloc.endswith(":"):
                    raise ValueError("URL port must not be empty")
                port = parsed.port
                if port is not None and not 1 <= port <= 65535:
                    raise ValueError("Invalid URL port")
                host = parsed.hostname or ""
            except ValueError as exc:
                raise ValueError("Enter a valid HTTPS URL without credentials") from exc
        else:
            host = value
        host = host.lower().removesuffix(".")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError("IP literals are not allowed")
        # ASCII DNS names only; Unicode domains must be supplied as punycode.
        labels = host.split(".")
        if (len(host) > 253 or len(labels) < 2 or host.endswith(".localhost")
                or not re.fullmatch(r"[a-z][a-z0-9-]*", labels[-1])
                or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels)):
            raise ValueError("Enter a valid public domain name; localhost is not allowed")
        return host


class ReconResponse(BaseModel):
    target: str
    status: Literal["not_executed"] = "not_executed"
    message: str = "Reconnaissance tools are not configured yet."
    agents: list[str] = Field(default_factory=list)
