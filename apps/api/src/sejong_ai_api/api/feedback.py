"""Public, privacy-safe citizen feedback endpoint."""

from __future__ import annotations

from typing import Annotated, Protocol
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from sejong_ai_api.contracts.feedback import (
    FeedbackConflictErrorDetail,
    FeedbackConflictErrorEnvelope,
    FeedbackCreateRequest,
    FeedbackCreateResponse,
    FeedbackPrivacyErrorDetail,
    FeedbackPrivacyErrorEnvelope,
)
from sejong_ai_api.contracts.health import (
    ServiceUnavailableDetail,
    ServiceUnavailableEnvelope,
)
from sejong_ai_api.feedback.service import (
    FeedbackConflictError,
    FeedbackPrivacyUnresolvedError,
    FeedbackUnavailableError,
)


class FeedbackRecorder(Protocol):
    async def record(self, payload: FeedbackCreateRequest) -> FeedbackCreateResponse: ...


class ClosedFeedbackRecorder:
    async def record(self, payload: FeedbackCreateRequest) -> FeedbackCreateResponse:
        del payload
        raise FeedbackUnavailableError()


_CLOSED_RECORDER: FeedbackRecorder = ClosedFeedbackRecorder()


def get_feedback_recorder() -> FeedbackRecorder:
    return _CLOSED_RECORDER


router = APIRouter(prefix="/api/v1", tags=["feedback"])


def _request_id(request: Request) -> UUID:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, UUID) else uuid4()


@router.post(
    "/feedback",
    response_model=FeedbackCreateResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createCitizenFeedback",
    responses={
        409: {"model": FeedbackConflictErrorEnvelope},
        422: {"model": FeedbackPrivacyErrorEnvelope},
        503: {"model": ServiceUnavailableEnvelope},
    },
)
async def create_citizen_feedback(
    request: Request,
    payload: FeedbackCreateRequest,
    recorder: Annotated[FeedbackRecorder, Depends(get_feedback_recorder)],
) -> FeedbackCreateResponse | JSONResponse:
    request_id = _request_id(request)
    try:
        return await recorder.record(payload)
    except FeedbackPrivacyUnresolvedError:
        privacy_envelope = FeedbackPrivacyErrorEnvelope(
            error=FeedbackPrivacyErrorDetail(
                code="FEEDBACK_PRIVACY_UNRESOLVED",
                message="개인정보를 빼고 다시 작성해 주세요.",
                request_id=request_id,
                retryable=False,
            )
        )
        return JSONResponse(
            status_code=422,
            content=privacy_envelope.model_dump(mode="json"),
        )
    except FeedbackConflictError:
        conflict_envelope = FeedbackConflictErrorEnvelope(
            error=FeedbackConflictErrorDetail(
                code="FEEDBACK_CONFLICT",
                message="이미 제출된 의견과 요청 정보가 다릅니다.",
                request_id=request_id,
                retryable=False,
            )
        )
        return JSONResponse(
            status_code=409,
            content=conflict_envelope.model_dump(mode="json"),
        )
    except FeedbackUnavailableError:
        unavailable_envelope = ServiceUnavailableEnvelope(
            error=ServiceUnavailableDetail(
                code="SERVICE_UNAVAILABLE",
                message="잠시 후 다시 시도해 주세요.",
                request_id=request_id,
                retryable=True,
            )
        )
        return JSONResponse(
            status_code=503,
            content=unavailable_envelope.model_dump(mode="json"),
        )


__all__ = ["FeedbackRecorder", "get_feedback_recorder", "router"]
