import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.api.routes import router
from app.core import auth
from app.core.config import get_settings

# Configure only application logs; leave SDK/root logger verbosity unchanged.
app_logger = logging.getLogger("app")
if not app_logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    app_logger.addHandler(handler)
app_logger.setLevel(logging.INFO)
app_logger.propagate = False
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Recon AI", version="0.1.0")
    app.include_router(router)

    @app.middleware("http")
    async def require_login(request: Request, call_next):
        is_login = request.method == "POST" and request.url.path == "/api/v1/auth/login"
        is_preflight = (
            request.method == "OPTIONS"
            and "origin" in request.headers
            and "access-control-request-method" in request.headers
        )
        if not is_login and not is_preflight:
            try:
                request.state.username, request.state.token_hash = auth.session(request)
            except HTTPException as exc:
                return JSONResponse(
                    status_code=exc.status_code,
                    content={
                        "error": {
                            "code": "unauthorized",
                            "message": str(exc.detail),
                        }
                    },
                )
        return await call_next(request)

    @app.exception_handler(RequestValidationError)
    async def validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Invalid request",
                    "details": [
                        {"field": ".".join(map(str, e["loc"])), "message": e["msg"]}
                        for e in exc.errors()
                    ],
                }
            },
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            headers=exc.headers,
            content={
                "error": {
                    "code": "http_error",
                    "message": str(exc.detail),
                }
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled API error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An internal error occurred",
                }
            },
        )

    return app


# Wrap the entire application so even error responses carry CORS headers.
app = CORSMiddleware(
    create_app(),
    allow_origins=get_settings().cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)
