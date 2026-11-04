"""Read-only LangChain tool scoped to the configured S3 document."""

import asyncio
import logging
from time import perf_counter

from langchain_core.tools import tool

from app.core.config import Settings
from app.service.provide.aws.base import Aws

logger = logging.getLogger(__name__)


def create_call_s3_tool(settings: Settings):
    @tool
    async def call_s3() -> str:
        """Read AWS evidence from S3. With a configured prefix, returns up to three newest JSON files
        by S3 LastModified, including their sources and modification timestamps."""

        def read():
            provider = Aws(settings=settings)
            try:
                if settings.s3_snapshot_prefix:
                    return provider.read_snapshot_history()
                return provider.read_configured_text()
            finally:
                provider.aws_client.close()

        started = perf_counter()
        logger.info("S3 tool read started")
        try:
            document = await asyncio.to_thread(read)
            logger.info(
                "S3 tool read completed characters=%d duration_ms=%.1f",
                len(document),
                (perf_counter() - started) * 1000,
            )
            return document
        except Exception as exc:
            logger.error(
                "S3 tool read failed error_type=%s duration_ms=%.1f",
                type(exc).__name__,
                (perf_counter() - started) * 1000,
            )
            raise

    return call_s3
