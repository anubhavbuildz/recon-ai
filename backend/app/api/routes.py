from fastapi import APIRouter

from app.api.schemas import ReconRequest, ReconResponse
from app.service.agent import orchestrator

router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "recon-ai"}


@router.post("/recon", response_model=ReconResponse)
async def recon(request: ReconRequest) -> ReconResponse:
    return await orchestrator.run_recon(request.target)
