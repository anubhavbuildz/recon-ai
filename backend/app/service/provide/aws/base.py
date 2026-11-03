"""AWS client and S3 bucket setup helpers."""

import json
import re
from datetime import datetime, timedelta, timezone

import boto3

from app.core.config import Settings, get_settings

# Add approved, existing S3 bucket names here.
VALID_BUCKET_NAMES: list[str] = []


class Aws:
    def __init__(
        self, service_name: str = "s3", settings: Settings | None = None
    ) -> None:
        self.settings = settings if settings is not None else get_settings()
        options = {}
        if service_name == "s3" and self.settings.s3_region:
            options["region_name"] = self.settings.s3_region
        self.aws_client = boto3.client(service_name, **options)

    def _setup_bucket(self, bucket_name: str | None = None, file_key: str = "") -> str:
        """Check access to an existing S3 bucket and return the object's URI.

        No object is uploaded. Credential and AWS API errors propagate to
        the caller, including access errors for existing buckets.
        """
        if self.aws_client.meta.service_model.service_name != "s3":
            raise ValueError("Bucket setup requires an S3 client")
        if bucket_name is None:
            bucket_name = self.settings.s3_bucket_name
        if not bucket_name or not bucket_name.strip():
            raise ValueError("bucket_name must not be empty")
        if (
            bucket_name not in VALID_BUCKET_NAMES
            and bucket_name != self.settings.s3_bucket_name
        ):
            raise ValueError(f"Bucket {bucket_name!r} is not in VALID_BUCKET_NAMES")
        if not file_key or not file_key.strip():
            raise ValueError("file_key must not be empty")

        self.aws_client.head_bucket(Bucket=bucket_name)

        return f"s3://{bucket_name}/{file_key}"

    def read_configured_text(self) -> str:
        """Read only the configured UTF-8 object, with a strict byte limit."""
        if not self.settings.s3_bucket_name or not self.settings.s3_object_key:
            raise ValueError("Configure S3_BUCKET_NAME and S3_OBJECT_KEY")
        return self._read_text(self.settings.s3_object_key, self.settings.s3_max_bytes)

    def _read_text(self, key: str, byte_limit: int) -> str:
        response = self.aws_client.get_object(
            Bucket=self.settings.s3_bucket_name, Key=key
        )
        body = response["Body"]
        try:
            if response.get("ContentLength", 0) > byte_limit:
                raise ValueError("S3 object exceeds S3_MAX_BYTES")
            data = body.read(byte_limit + 1)
            if len(data) > byte_limit:
                raise ValueError("S3 object exceeds S3_MAX_BYTES")
            text = data.decode("utf-8-sig")
            if not text.strip():
                raise ValueError("S3 object is empty")
            return text
        finally:
            body.close()

    def read_snapshot_history(self, now: datetime | None = None) -> str:
        """Read the latest JSON snapshot per UTC day in a bounded history window."""
        if not self.settings.s3_bucket_name or not self.settings.s3_snapshot_prefix:
            raise ValueError("Configure S3_BUCKET_NAME and S3_SNAPSHOT_PREFIX")
        now = now or datetime.now(timezone.utc)
        today = now.astimezone(timezone.utc).date()
        prefix = self.settings.s3_snapshot_prefix.rstrip("/") + "/"
        snapshots = []
        missing_dates = []
        remaining = self.settings.s3_max_bytes
        for offset in range(self.settings.s3_history_days):
            day = today - timedelta(days=offset)
            daily_prefix = f"{prefix}{day:%Y/%m/%d}/"
            latest = None
            paginator = self.aws_client.get_paginator("list_objects_v2")
            for page in paginator.paginate(
                Bucket=self.settings.s3_bucket_name, Prefix=daily_prefix
            ):
                for item in page.get("Contents", []):
                    key = item["Key"]
                    if key.startswith(daily_prefix) and re.fullmatch(
                        r"\d{8}T\d{6}Z\.json", key[len(daily_prefix) :]
                    ):
                        if latest is None or key > latest:
                            latest = key
            if latest is None:
                missing_dates.append(day.isoformat())
                continue
            text = self._read_text(latest, remaining)
            remaining -= len(text.encode("utf-8"))
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("Snapshot must be a JSON object")
            snapshots.append(
                {
                    "snapshot_date": day.isoformat(),
                    "source": f"s3://{self.settings.s3_bucket_name}/{latest}",
                    "data": data,
                }
            )
        if not snapshots:
            raise ValueError("No snapshots found in the configured date window")
        result = json.dumps(
            {
                "timezone": "UTC",
                "selection": "Latest snapshot per day, not every 5-minute sample",
                "snapshots": snapshots,
                "missing_dates": missing_dates,
            },
            ensure_ascii=False,
        )
        if len(result.encode("utf-8")) > self.settings.s3_max_bytes:
            raise ValueError("Combined snapshot context exceeds S3_MAX_BYTES")
        return result
