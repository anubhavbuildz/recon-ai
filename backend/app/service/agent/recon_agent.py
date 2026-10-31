"""Initial agent interface; never executes tools or calls a model."""
from app.api.schemas import ReconResponse
from app.service.tools.registry import list_tools


async def run_recon_agent(target: str) -> ReconResponse:
    list_tools()  # Inspect metadata only. There is deliberately no execution path.
    return ReconResponse(target=target)
