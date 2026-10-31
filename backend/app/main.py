import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.api.routes import router
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Recon AI", version="0.1.0")
    app.include_router(router)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"error": {
            "code": "validation_error", "message": "Invalid request",
            "details": [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]} for e in exc.errors()],
        }})

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, headers=exc.headers, content={"error": {
            "code": "http_error", "message": str(exc.detail),
        }})

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled API error", exc_info=exc)
        return JSONResponse(status_code=500, content={"error": {
            "code": "internal_error", "message": "An internal error occurred",
        }})

    return app


# Wrap the entire application so even error responses carry CORS headers.
app = CORSMiddleware(
    create_app(), allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
)
