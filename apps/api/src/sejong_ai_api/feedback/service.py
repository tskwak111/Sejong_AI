"""Mask-first citizen feedback service."""

from __future__ import annotations

from typing import Protocol

from sejong_ai_api.contracts.feedback import (
    FeedbackCreateRequest,
    FeedbackCreateResponse,
    FeedbackDetailStatus,
)
from sejong_ai_api.db.errors import (
    DatabaseRuleError,
    DatabaseUnavailableError,
)
from sejong_ai_api.db.models import CitizenFeedbackWrite
from sejong_ai_api.privacy.redaction import redact_feedback_detail


class FeedbackRepository(Protocol):
    async def record_citizen_feedback(self, write: CitizenFeedbackWrite) -> None: ...


class FeedbackPrivacyUnresolvedError(Exception):
    def __init__(self) -> None:
        super().__init__("FEEDBACK_PRIVACY_UNRESOLVED")


class FeedbackConflictError(Exception):
    def __init__(self) -> None:
        super().__init__("FEEDBACK_CONFLICT")


class FeedbackUnavailableError(Exception):
    def __init__(self) -> None:
        super().__init__("FEEDBACK_UNAVAILABLE")


class FeedbackService:
    def __init__(self, repository: FeedbackRepository) -> None:
        self._repository = repository

    async def record(self, payload: FeedbackCreateRequest) -> FeedbackCreateResponse:
        masked_detail: str | None = None
        detail_was_masked = False
        detail_status: FeedbackDetailStatus = "NOT_PROVIDED"
        if payload.detail is not None:
            redacted = redact_feedback_detail(payload.detail)
            if redacted.masked_text is None:
                raise FeedbackPrivacyUnresolvedError()
            masked_detail = redacted.masked_text
            detail_was_masked = bool(redacted.findings)
            detail_status = "MASKED" if detail_was_masked else "STORED"

        write = CitizenFeedbackWrite(
            response_request_id=payload.request_id,
            rating=payload.rating,
            category=payload.category,
            reason_code=payload.reason_code,
            masked_detail=masked_detail,
            detail_was_masked=detail_was_masked,
        )
        try:
            await self._repository.record_citizen_feedback(write)
        except DatabaseRuleError:
            raise FeedbackConflictError() from None
        except DatabaseUnavailableError:
            raise FeedbackUnavailableError() from None
        return FeedbackCreateResponse(
            request_id=payload.request_id,
            status="RECORDED",
            detail_status=detail_status,
        )


__all__ = [
    "FeedbackConflictError",
    "FeedbackPrivacyUnresolvedError",
    "FeedbackRepository",
    "FeedbackService",
    "FeedbackUnavailableError",
]
