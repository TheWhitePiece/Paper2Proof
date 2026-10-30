from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, SecretStr
from starlette.exceptions import HTTPException

from paper2proof import __version__
from paper2proof.auth import LocalAuth
from paper2proof.config import Settings, get_settings
from paper2proof.pdf.parser import PDFError
from paper2proof.schemas.status import APIError, DevelopmentStatus, HealthResponse
from paper2proof.store import Conflict
from paper2proof.workspace import Workspace
from services.api.workflow import router


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else get_settings()
    app = FastAPI(title="Paper2Proof API", version=__version__)
    workspace = Workspace(config.data_dir)
    auth = LocalAuth(workspace.store)
    app.state.workspace = workspace
    app.include_router(router(workspace))

    class Login(BaseModel):
        access_code: SecretStr = Field(max_length=200)

    @app.get("/api/v1/session")
    def session(request: Request):
        return {
            "authenticated": auth.authenticated(request.cookies.get("p2p_session")),
            "mode": "single_owner_local",
        }

    @app.post("/api/v1/session")
    def login(body: Login, request: Request):
        token = auth.login(body.access_code.get_secret_value())
        if not token:
            return error_response(
                request, 401, "invalid_access_code", "Incorrect local access code"
            )
        response = JSONResponse({"authenticated": True})
        response.set_cookie(
            "p2p_session", token, httponly=True, samesite="strict", max_age=12 * 3600
        )
        return response

    @app.delete("/api/v1/session")
    def logout(request: Request):
        auth.logout(request.cookies.get("p2p_session"))
        response = JSONResponse({"authenticated": False})
        response.delete_cookie("p2p_session")
        return response

    @app.middleware("http")
    async def request_identifier(request: Request, call_next):
        request.state.request_id = str(uuid4())
        public = {"/api/v1/health", "/api/v1/status", "/api/v1/session"}
        if request.url.path.startswith("/api/v1/") and request.url.path not in public:
            if not auth.authenticated(request.cookies.get("p2p_session")):
                return error_response(
                    request, 401, "authentication_required", "Sign in to the local workspace"
                )
        origin = request.headers.get("origin")
        if (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and origin
            and origin
            not in {
                "http://127.0.0.1:3000",
                "http://localhost:3000",
                "http://127.0.0.1:8000",
                "http://localhost:8000",
            }
        ):
            return error_response(request, 403, "origin_rejected", "Local browser origin required")
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    def error_response(request: Request, status: int, code: str, message: str, details=None):
        error = APIError(
            code=code,
            message=message,
            details=details or [],
            request_id=request.state.request_id,
        )
        return JSONResponse(
            status_code=status,
            content=error.model_dump(),
            headers={"X-Request-ID": request.state.request_id},
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return error_response(request, exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Do not echo request values, which can contain credentials or private text.
        details = [
            {"field": ".".join(map(str, item["loc"])), "type": item["type"]}
            for item in exc.errors()
        ]
        return error_response(request, 422, "validation_error", "Invalid request", details)

    @app.exception_handler(PDFError)
    async def pdf_error(request: Request, exc: PDFError):
        return error_response(
            request, 413 if exc.code == "pdf_size_limit" else 422, exc.code, str(exc)
        )

    @app.exception_handler(Conflict)
    async def conflict(request: Request, exc: Conflict):
        return error_response(request, 409, "conflict", str(exc))

    @app.exception_handler(KeyError)
    async def not_found(request: Request, exc: KeyError):
        return error_response(request, 404, "not_found", "Resource not found")

    @app.exception_handler(ValueError)
    async def invalid(request: Request, exc: ValueError):
        return error_response(request, 422, "invalid_operation", str(exc)[:1000])

    @app.get("/api/v1/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        # Liveness only: not evidence of database, model, or sandbox connectivity.
        return HealthResponse(version=__version__)

    @app.get("/api/v1/status", response_model=DevelopmentStatus)
    def development_status() -> DevelopmentStatus:
        return DevelopmentStatus(
            provider=config.provider,
            runner=config.runner,
            message=(
                "Single-user offline workspace: PDF review, durable local jobs, "
                "code previews and fixture evidence. Live inference and sandbox execution pending."
            ),
        )

    return app
