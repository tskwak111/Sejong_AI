"""HTTP boundary for read-only official office lookup."""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from sejong_ai_api.contracts.chat import SupportedIntent
from sejong_ai_api.contracts.errors import ValidationErrorEnvelope
from sejong_ai_api.contracts.health import (
    ServiceUnavailableDetail,
    ServiceUnavailableEnvelope,
)
from sejong_ai_api.contracts.offices import OfficeListResponse
from sejong_ai_api.db.models import Intent, Region
from sejong_ai_api.office.service import (
    ClosedOfficeDirectory,
    OfficeDirectory,
    OfficeDirectoryUnavailableError,
)

RETRY_AFTER_SECONDS = 30
router = APIRouter(prefix="/api/v1", tags=["offices"])
_CLOSED_DIRECTORY: OfficeDirectory = ClosedOfficeDirectory()


def get_office_directory() -> OfficeDirectory:
    return _CLOSED_DIRECTORY


@router.get(
    "/offices",
    operation_id="listOffices",
    response_model=OfficeListResponse,
    responses={
        422: {"model": ValidationErrorEnvelope, "description": "Invalid query"},
        503: {"model": ServiceUnavailableEnvelope, "description": "Dependency unavailable"},
    },
)
async def list_offices(
    request: Request,
    region: Annotated[Region, Query()],
    intent: Annotated[SupportedIntent, Query()],
    directory: Annotated[OfficeDirectory, Depends(get_office_directory)],
) -> OfficeListResponse | JSONResponse:
    try:
        items = await directory.list_offices(region, Intent(intent))
    except OfficeDirectoryUnavailableError:
        request_id = getattr(request.state, "request_id", None)
        resolved_request_id = request_id if isinstance(request_id, UUID) else uuid4()
        unavailable = ServiceUnavailableEnvelope(
            error=ServiceUnavailableDetail(
                code="SERVICE_UNAVAILABLE",
                message="잠시 후 다시 시도해 주세요.",
                request_id=resolved_request_id,
                retryable=True,
            )
        )
        return JSONResponse(
            status_code=503,
            headers={"Retry-After": str(RETRY_AFTER_SECONDS)},
            content=unavailable.model_dump(mode="json"),
        )
    return OfficeListResponse(items=list(items))


__all__ = ["get_office_directory", "router"]
