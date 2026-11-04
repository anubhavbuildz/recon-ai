"""Opt-in live S3/model integration check. Run from backend with PYTHONPATH=.

Reads configured snapshots and sends them to the configured model through the
in-process authenticated API. No browser, infrastructure writes, or S3 uploads.
Only sanitized status metadata is printed; credentials and document text are not.
"""

import json
import logging
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from fastapi.testclient import TestClient

from app.core import auth
from app.core.config import get_settings
from app.main import create_app
from app.service.provide.aws.base import Aws


def main() -> int:
    logging.getLogger("app").setLevel(logging.CRITICAL)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    settings = get_settings()
    started = perf_counter()
    stage = "s3_read"
    try:
        provider = Aws(settings=settings)
        try:
            if settings.s3_snapshot_prefix:
                context = json.loads(provider.read_snapshot_history())
                sources = [sample["source"] for sample in context["snapshots"]]
                timestamps = [
                    sample["last_modified"] for sample in context["snapshots"]
                ]
                assert 1 <= len(sources) <= 3
                assert timestamps == sorted(timestamps, reverse=True)
            else:
                provider.read_configured_text()
                sources = [f"s3://{settings.s3_bucket_name}/{settings.s3_object_key}"]
        finally:
            provider.aws_client.close()
        print(
            json.dumps(
                {"check": stage, "status": "passed", "files_read": len(sources)}
            ),
            flush=True,
        )
        stage = "authenticated_live_chat"
        original_db = auth.SESSION_DB
        try:
            with TemporaryDirectory(prefix="recon-live-") as directory:
                auth.SESSION_DB = Path(directory) / "sessions.sqlite3"
                with TestClient(create_app()) as client:
                    assert (
                        client.post(
                            "/api/v1/chat", json={"question": "test"}
                        ).status_code
                        == 401
                    )
                    login = client.post(
                        "/api/v1/auth/login",
                        json={
                            "username": settings.auth_username,
                            "password": settings.auth_password,
                        },
                    )
                    assert login.status_code == 200, f"Login HTTP {login.status_code}"
                    headers = {"Authorization": f"Bearer {login.json()['token']}"}
                    response = client.post(
                        "/api/v1/chat",
                        headers=headers,
                        json={
                            "question": "Read the configured S3 evidence using call_s3. Briefly summarize each supplied snapshot in a Markdown table with Source, Collection time, Region, EC2 count and EBS count. Use only supplied evidence. Do not expose secrets."
                        },
                    )
                    assert response.status_code == 200, (
                        f"Chat HTTP {response.status_code}"
                    )
                    result = response.json()
                    assert result["message"].strip()
                    actual = result.get("sources") or [result["source"]]
                    # A collector may upload between the two reads; verify scope/count,
                    # rather than requiring an identical moving latest-three selection.
                    expected_prefix = f"s3://{settings.s3_bucket_name}/{settings.s3_snapshot_prefix or settings.s3_object_key}"
                    assert 1 <= len(actual) <= 3
                    assert all(source.startswith(expected_prefix) for source in actual)
                    assert result["source"] == actual[0]
                    logout = client.post("/api/v1/auth/logout", headers=headers)
                    assert logout.status_code == 200
                    assert (
                        client.get("/api/v1/auth/me", headers=headers).status_code
                        == 401
                    )
                    print(
                        json.dumps(
                            {
                                "check": stage,
                                "status": "passed",
                                "http_status": response.status_code,
                                "source_count": len(actual),
                                "answer_characters": len(result["message"]),
                                "markdown_table_present": "|" in result["message"],
                            }
                        ),
                        flush=True,
                    )
        finally:
            auth.SESSION_DB = original_db
    except Exception as exc:
        error = {"check": stage, "status": "failed", "error_type": type(exc).__name__}
        # Assertion messages are authored above and contain only HTTP status metadata.
        if isinstance(exc, AssertionError):
            error["detail"] = str(exc)
        print(json.dumps(error), flush=True)
        return 1
    print(
        json.dumps(
            {"status": "passed", "duration_seconds": round(perf_counter() - started, 2)}
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
