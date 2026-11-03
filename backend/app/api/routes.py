from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException, Request
from openai import APITimeoutError
from pydantic import BaseModel, Field

from app.api.schemas import ChatRequest, ChatResponse, ReconRequest, ReconResponse
from app.core import auth
from app.service.agent import orchestrator
from app.service.llm.base import ModelError
from app.service.llm.workflow.chain import run_chat_workflow

router = APIRouter(prefix="/api/v1")


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=4096, repr=False)


@router.post("/auth/login")
async def login(request: LoginRequest) -> dict[str, str]:
    return auth.login(request.username, request.password)


@router.get("/auth/me")
async def current_user(request: Request) -> dict[str, str]:
    return {"username": request.state.username}


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        return await run_chat_workflow(request.question)
    except ValueError as exc:
        raise HTTPException(
            503, "S3 context is not configured or is not a supported text document"
        ) from exc
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(502, "Unable to read the configured S3 document") from exc
    except ModelError as exc:
        if isinstance(exc.__cause__, APITimeoutError):
            raise HTTPException(
                504, "The model timed out. Please retry your question."
            ) from exc
        raise HTTPException(
            502, "Model is unavailable. Check model configuration and retry."
        ) from exc


@router.post("/auth/logout")
async def logout(request: Request) -> dict[str, str]:
    auth.logout(request.state.token_hash)
    return {"status": "signed_out"}


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "recon-ai"}


@router.post("/recon", response_model=ReconResponse)
async def recon(request: ReconRequest) -> ReconResponse:
    return await orchestrator.run_recon(request.target)
