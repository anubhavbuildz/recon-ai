"""Coordinates the API and workflow without model-specific settings."""
from app.api.schemas import ReconResponse
from app.service.llm.workflow import graph


async def run_recon(target: str) -> ReconResponse:
    return await graph.run_workflow(target)
