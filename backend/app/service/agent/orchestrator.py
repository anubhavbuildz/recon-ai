"""Coordinates the API and workflow without model-specific settings."""

from app.api.schemas import ReconResponse
from app.service.llm.workflow import chain


async def run_recon(target: str) -> ReconResponse:
    return await chain.run_workflow(target)
