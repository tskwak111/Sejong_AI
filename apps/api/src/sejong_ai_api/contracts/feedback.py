"""Strict public citizen-feedback contracts without transcript fields."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from sejong_ai_api.contracts.health import StrictPublicModel

type FeedbackRating = Literal["SATISFIED", "DISSATISFIED"]
type FeedbackCategory = Literal[
    "MOVE_IN_RESIDENT_REGISTRATION",
    "CERTIFICATE_ISSUANCE",
    "BULKY_WASTE",
    "LOCAL_TAX_GENERAL",
    "OTHER",
]
type FeedbackReasonCode = Literal[
    "INACCURATE",
    "NOT_RELEVANT",
    "HARD_TO_UNDERSTAND",
    "WRONG_CONTACT",
    "OTHER",
]
type FeedbackDetailStatus = Literal["NOT_PROVIDED", "STORED", "MASKED"]


class FeedbackCreateRequest(StrictPublicModel):
    request_id: UUID
    rating: FeedbackRating
    category: FeedbackCategory | None
    reason_code: FeedbackReasonCode | None
    detail: Annotated[str | None, Field(max_length=300)]

    @field_validator("request_id", mode="before")
    @classmethod
    def parse_canonical_request_id(cls, value: object) -> object:
        if type(value) is UUID:
            return value
        if type(value) is not str:
            raise ValueError("request_id must be a canonical UUID string")
        try:
            parsed = UUID(value)
        except ValueError:
            raise ValueError("request_id must be a canonical UUID string") from None
        if str(parsed) != value:
            raise ValueError("request_id must be a canonical UUID string")
        return parsed

    @field_validator("detail")
    @classmethod
    def require_trimmed_detail(cls, value: str | None) -> str | None:
        if value is not None and (not value or value != value.strip()):
            raise ValueError("detail must be non-empty and trimmed")
        return value

    @model_validator(mode="after")
    def require_rating_shape(self) -> Self:
        if self.rating == "SATISFIED":
            if any(value is not None for value in (self.category, self.reason_code, self.detail)):
                raise ValueError("satisfied feedback cannot include dissatisfaction fields")
            return self
        if self.category is None or self.reason_code is None:
            raise ValueError("dissatisfied feedback requires category and reason")
        if self.reason_code == "OTHER" and self.detail is None:
            raise ValueError("other reason requires detail")
        return self


class FeedbackCreateResponse(StrictPublicModel):
    request_id: UUID
    status: Literal["RECORDED"]
    detail_status: FeedbackDetailStatus


class FeedbackPrivacyErrorDetail(StrictPublicModel):
    code: Literal["FEEDBACK_PRIVACY_UNRESOLVED"]
    message: Literal["개인정보를 빼고 다시 작성해 주세요."]
    request_id: UUID
    retryable: Literal[False]

    @field_validator("retryable", mode="before")
    @classmethod
    def require_boolean_false(cls, value: object) -> object:
        if value is not False:
            raise ValueError("retryable must be false")
        return value


class FeedbackPrivacyErrorEnvelope(StrictPublicModel):
    error: FeedbackPrivacyErrorDetail


class FeedbackConflictErrorDetail(StrictPublicModel):
    code: Literal["FEEDBACK_CONFLICT"]
    message: Literal["이미 제출된 의견과 요청 정보가 다릅니다."]
    request_id: UUID
    retryable: Literal[False]


class FeedbackConflictErrorEnvelope(StrictPublicModel):
    error: FeedbackConflictErrorDetail


class CitizenFeedbackSummaryItem(StrictPublicModel):
    id: UUID
    response_request_id: UUID
    rating: FeedbackRating
    category: FeedbackCategory | None
    reason_code: FeedbackReasonCode | None
    masked_detail: Annotated[str | None, Field(min_length=1, max_length=300)]
    detail_was_masked: bool
    created_at: datetime
    detail_expires_at: datetime | None
    detail_purged_at: datetime | None


class FeedbackCount(StrictPublicModel):
    code: str
    count: Annotated[int, Field(ge=0)]


class FeedbackSummaryResponse(StrictPublicModel):
    total: Annotated[int, Field(ge=0)]
    satisfied: Annotated[int, Field(ge=0)]
    dissatisfied: Annotated[int, Field(ge=0)]
    satisfaction_rate: Annotated[float, Field(ge=0, le=1)] | None
    category_counts: list[FeedbackCount]
    reason_counts: list[FeedbackCount]
    recent: list[CitizenFeedbackSummaryItem]


__all__ = [
    "CitizenFeedbackSummaryItem",
    "FeedbackConflictErrorDetail",
    "FeedbackConflictErrorEnvelope",
    "FeedbackCount",
    "FeedbackCreateRequest",
    "FeedbackCreateResponse",
    "FeedbackDetailStatus",
    "FeedbackPrivacyErrorDetail",
    "FeedbackPrivacyErrorEnvelope",
    "FeedbackSummaryResponse",
]
