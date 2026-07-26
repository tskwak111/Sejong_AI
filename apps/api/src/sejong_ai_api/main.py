"""FastAPI application factory."""

import logging
from collections.abc import Callable
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from sejong_ai_api.admin.service import AdminService
from sejong_ai_api.api.admin import get_admin_enabled, get_admin_service
from sejong_ai_api.api.admin import router as admin_router
from sejong_ai_api.api.chat import ChatResponder, get_chat_responder
from sejong_ai_api.api.chat import router as chat_router
from sejong_ai_api.api.health import ReadinessProbe, get_readiness_probe
from sejong_ai_api.api.health import router as health_router
from sejong_ai_api.api.offices import get_office_directory
from sejong_ai_api.api.offices import router as offices_router
from sejong_ai_api.contracts.admin import AdminErrorEnvelope
from sejong_ai_api.contracts.errors import ValidationErrorDetail, ValidationErrorEnvelope
from sejong_ai_api.core.logging import (
    SafeRequestLoggingMiddleware,
    configure_uvicorn_log_safety,
    get_safe_request_logger,
)
from sejong_ai_api.office.service import OfficeDirectory


def create_app(
    *,
    readiness_probe: ReadinessProbe | None = None,
    chat_responder: ChatResponder | None = None,
    office_directory: OfficeDirectory | None = None,
    admin_enabled: bool = False,
    admin_service: AdminService | None = None,
    request_logger: logging.Logger | None = None,
    request_id_factory: Callable[[], UUID] = uuid4,
) -> FastAPI:
    """Build an import-safe API application with an optional readiness seam."""
    configure_uvicorn_log_safety()
    application = FastAPI(title="Sejong Civil AI API", version="3.2.0-draft")
    application.include_router(health_router)
    application.include_router(chat_router)
    application.include_router(offices_router)
    if admin_enabled and admin_service is not None:
        application.include_router(admin_router)
    application.add_middleware(
        SafeRequestLoggingMiddleware,
        logger=request_logger if request_logger is not None else get_safe_request_logger(),
        request_id_factory=request_id_factory,
    )

    if readiness_probe is not None:
        injected_probe = readiness_probe

        def provide_injected_readiness_probe() -> ReadinessProbe:
            return injected_probe

        application.dependency_overrides[get_readiness_probe] = provide_injected_readiness_probe

    if chat_responder is not None:
        injected_responder = chat_responder

        def provide_injected_chat_responder() -> ChatResponder:
            return injected_responder

        application.dependency_overrides[get_chat_responder] = provide_injected_chat_responder

    if office_directory is not None:
        injected_directory = office_directory

        def provide_injected_office_directory() -> OfficeDirectory:
            return injected_directory

        application.dependency_overrides[get_office_directory] = provide_injected_office_directory

    if admin_enabled and admin_service is not None:
        injected_admin_service = admin_service

        def provide_admin_enabled() -> bool:
            return True

        def provide_injected_admin_service() -> AdminService:
            return injected_admin_service

        application.dependency_overrides[get_admin_enabled] = provide_admin_enabled
        application.dependency_overrides[get_admin_service] = provide_injected_admin_service

    @application.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        _error: RequestValidationError,
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        resolved_request_id = request_id if isinstance(request_id, UUID) else uuid4()
        if request.url.path.startswith("/api/v1/admin/"):
            admin_envelope = AdminErrorEnvelope.model_validate(
                {
                    "error": {
                        "code": "ADMIN_VALIDATION_FAILED",
                        "message": "입력값을 확인해 주세요.",
                        "request_id": resolved_request_id,
                        "retryable": False,
                    }
                }
            )
            return JSONResponse(
                status_code=422,
                content=admin_envelope.model_dump(mode="json"),
            )
        envelope = ValidationErrorEnvelope(
            error=ValidationErrorDetail(
                code="VALIDATION_ERROR",
                message="입력값을 확인해 주세요.",
                request_id=resolved_request_id,
                retryable=False,
            )
        )
        return JSONResponse(status_code=422, content=envelope.model_dump(mode="json"))

    return application


app = create_app()
