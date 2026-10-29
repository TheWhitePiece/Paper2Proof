from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from paper2proof import __version__
from paper2proof.config import Settings, get_settings
from paper2proof.schemas.status import APIError, DevelopmentStatus, HealthResponse


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else get_settings()
    app = FastAPI(title="Paper2Proof API", version=__version__)

    @app.middleware("http")
    async def request_identifier(request: Request, call_next):
        request.state.request_id = str(uuid4())
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
        return JSONResponse(status_code=status, content=error.model_dump())

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
                "Local foundation only. Live inference, execution, and persistence are pending."
            ),
        )

    return app
