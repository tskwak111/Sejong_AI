"""Strict local/private administrator response contracts."""

from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from sejong_ai_api.contracts.chat import HttpsUrl
from sejong_ai_api.contracts.health import StrictPublicModel

type StoredFailureReason = Literal[
    "INSUFFICIENT_GROUNDING",
    "PERSONAL_LOOKUP",
    "LEGAL_JUDGMENT",
]
type FailedQuestionStatus = Literal["NEW", "REASON_CONFIRMED"]
type CivicScopeGapStatus = Literal["NEW", "PLANNED", "DISMISSED"]
type KBCandidateStatus = Literal["DRAFTED", "PENDING_APPROVAL", "APPROVED", "REJECTED"]
type SupportedIntent = Literal[
    "MOVE_IN_RESIDENT_REGISTRATION",
    "CERTIFICATE_ISSUANCE",
    "BULKY_WASTE",
    "LOCAL_TAX_GENERAL",
]


class FailedQuestion(StrictPublicModel):
    id: UUID
    masked_question: str | None
    intent: SupportedIntent
    fallback_reason: StoredFailureReason
    candidate_eligible: bool
    status: FailedQuestionStatus
    created_at: datetime
    text_expires_at: datetime
    text_purged_at: datetime | None

    @model_validator(mode="after")
    def validate_retention_and_eligibility(self) -> Self:
        expected_eligibility = self.fallback_reason == "INSUFFICIENT_GROUNDING"
        if self.candidate_eligible is not expected_eligibility:
            raise ValueError("candidate eligibility must match fallback reason")
        if self.text_expires_at != self.created_at + timedelta(days=30):
            raise ValueError("question text expiry must be exactly 30 days")
        if (self.masked_question is None) is not (self.text_purged_at is not None):
            raise ValueError("masked question and purge timestamp must transition together")
        if self.text_purged_at is not None and self.text_purged_at < self.text_expires_at:
            raise ValueError("question text cannot be purged before its expiry")
        return self


class FailedQuestionListResponse(StrictPublicModel):
    items: list[FailedQuestion]
    total: Annotated[int, Field(ge=0)]


class FailedQuestionDetailResponse(StrictPublicModel):
    item: FailedQuestion


class CivicScopeGapSummary(StrictPublicModel):
    id: UUID
    masked_question: Annotated[str, Field(min_length=1, max_length=2000)] | None
    status: CivicScopeGapStatus
    created_at: datetime
    updated_at: datetime
    text_expires_at: datetime
    text_purged_at: datetime | None
    reviewed_by: Annotated[str, Field(min_length=1, max_length=200)] | None
    reviewed_at: datetime | None
    review_comment: Annotated[str, Field(min_length=1, max_length=1000)] | None

    @model_validator(mode="after")
    def validate_lifecycle_and_review(self) -> Self:
        if self.text_expires_at != self.created_at + timedelta(days=30):
            raise ValueError("scope-gap text expiry must be exactly 30 days")
        if (self.masked_question is None) is not (self.text_purged_at is not None):
            raise ValueError("scope-gap text and purge timestamp must transition together")
        if self.text_purged_at is not None and self.text_purged_at < self.text_expires_at:
            raise ValueError("scope-gap text cannot be purged before expiry")
        if (
            self.masked_question is not None
            and self.text_expires_at <= datetime.now(UTC)
        ):
            raise ValueError("expired scope-gap text must already be purged")

        review_values = (self.reviewed_by, self.reviewed_at, self.review_comment)
        if self.status == "NEW":
            if any(value is not None for value in review_values):
                raise ValueError("NEW scope gap cannot contain review outcome")
        elif any(value is None for value in review_values):
            raise ValueError("terminal scope gap requires complete review outcome")
        return self


class CivicScopeGapListResponse(StrictPublicModel):
    items: list[CivicScopeGapSummary]
    total: Annotated[int, Field(ge=0)]


class CivicScopeGapReviewRequest(StrictPublicModel):
    decision: Literal["PLANNED", "DISMISSED"]
    review_comment: Annotated[str, Field(min_length=1, max_length=1000)]

    @field_validator("review_comment")
    @classmethod
    def require_trimmed_review_comment(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("review comment must be non-empty and trimmed")
        return value


class CivicScopeGapReviewResponse(StrictPublicModel):
    id: UUID
    status: Literal["PLANNED", "DISMISSED"]


class ReasonConfirmationResponse(StrictPublicModel):
    id: UUID
    status: Literal["REASON_CONFIRMED"]


class ReasonConfirmationRequest(StrictPublicModel):
    reason: StoredFailureReason


class KBCandidateSummary(StrictPublicModel):
    id: UUID
    failed_question_id: UUID
    title: Annotated[str, Field(min_length=1, max_length=200)]
    representative_question: Annotated[str, Field(min_length=1, max_length=1000)]
    data_origin: Literal["OFFICIAL", "MOCK"]
    category: SupportedIntent
    answer_summary: Annotated[str, Field(min_length=1)]
    procedure_steps: list[str]
    required_documents: list[str]
    processing_time: str | None
    fee: str | None
    department: Annotated[str, Field(min_length=1)]
    source_title: Annotated[str, Field(min_length=1)]
    source_url: HttpsUrl
    last_verified_at: date
    caution: str | None
    status: KBCandidateStatus
    created_by: Annotated[str, Field(min_length=1, max_length=100)]
    reviewed_by: Annotated[str, Field(min_length=1, max_length=100)] | None
    review_comment: Annotated[str, Field(min_length=1, max_length=1000)] | None
    approved_at: datetime | None
    activated_kb_id: UUID | None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_review_state(self) -> Self:
        if self.status in {"DRAFTED", "PENDING_APPROVAL"}:
            if any(
                value is not None
                for value in (
                    self.reviewed_by,
                    self.review_comment,
                    self.approved_at,
                    self.activated_kb_id,
                )
            ):
                raise ValueError("unreviewed candidate cannot contain review outcome fields")
            return self

        if self.reviewed_by is None or self.review_comment is None:
            raise ValueError("reviewed candidate requires reviewer and review comment")
        if self.reviewed_by == self.created_by:
            raise ValueError("candidate creator cannot review their own candidate")
        if self.status == "APPROVED":
            if self.approved_at is None or self.activated_kb_id is None:
                raise ValueError("approved candidate requires activation evidence")
            if self.data_origin != "OFFICIAL":
                raise ValueError("approved candidate must use official data")
        elif self.approved_at is not None or self.activated_kb_id is not None:
            raise ValueError("rejected candidate cannot contain activation evidence")
        return self


class KBCandidateListResponse(StrictPublicModel):
    items: list[KBCandidateSummary]
    total: Annotated[int, Field(ge=0)]


class KBCandidateCreateResponse(StrictPublicModel):
    id: UUID
    status: Literal["DRAFTED"]


class KBCandidateSubmitResponse(StrictPublicModel):
    id: UUID
    status: Literal["PENDING_APPROVAL"]


class KBCandidateReviewResponse(StrictPublicModel):
    id: UUID
    status: Literal["APPROVED", "REJECTED"]


class KBCandidateCreateRequest(StrictPublicModel):
    failed_question_id: UUID
    title: Annotated[str, Field(min_length=1, max_length=200)]
    representative_question: Annotated[str, Field(min_length=1, max_length=1000)]
    category: SupportedIntent
    answer_summary: Annotated[str, Field(min_length=1)]
    procedure_steps: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    processing_time: str | None = None
    fee: str | None = None
    department: Annotated[str, Field(min_length=1)]
    source_title: Annotated[str, Field(min_length=1)]
    source_url: HttpsUrl
    last_verified_at: date
    caution: str | None = None

    @field_validator("failed_question_id", mode="before")
    @classmethod
    def parse_canonical_failed_question_id(cls, value: object) -> UUID:
        if isinstance(value, UUID):
            return value
        if not isinstance(value, str):
            raise ValueError("failed question ID must be a canonical UUID string")
        try:
            parsed = UUID(value)
        except ValueError as error:
            raise ValueError("failed question ID must be a canonical UUID string") from error
        if str(parsed) != value:
            raise ValueError("failed question ID must be a canonical UUID string")
        return parsed

    @field_validator("last_verified_at", mode="before")
    @classmethod
    def parse_canonical_last_verified_at(cls, value: object) -> date:
        if isinstance(value, datetime):
            raise ValueError("last verified date must use YYYY-MM-DD")
        if isinstance(value, date):
            return value
        if not isinstance(value, str):
            raise ValueError("last verified date must use YYYY-MM-DD")
        try:
            parsed = date.fromisoformat(value)
        except ValueError as error:
            raise ValueError("last verified date must use YYYY-MM-DD") from error
        if parsed.isoformat() != value:
            raise ValueError("last verified date must use YYYY-MM-DD")
        return parsed


class CandidateReviewRequest(StrictPublicModel):
    decision: Literal["APPROVED", "REJECTED"]
    review_comment: Annotated[str, Field(min_length=1, max_length=1000)]

    @field_validator("review_comment")
    @classmethod
    def reject_blank_review_comment(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("review comment cannot be blank")
        return value


class AdminRouteDisabledError(StrictPublicModel):
    code: Literal["ADMIN_ROUTE_DISABLED"]
    message: Literal["관리자 기능을 사용할 수 없습니다."]
    request_id: UUID
    retryable: Literal[False]


class AdminForbiddenError(StrictPublicModel):
    code: Literal["ADMIN_FORBIDDEN"]
    message: Literal["이 작업을 수행할 권한이 없습니다."]
    request_id: UUID
    retryable: Literal[False]


class AdminNotFoundError(StrictPublicModel):
    code: Literal["ADMIN_NOT_FOUND"]
    message: Literal["대상을 찾을 수 없습니다."]
    request_id: UUID
    retryable: Literal[False]


class AdminInvalidStateError(StrictPublicModel):
    code: Literal["ADMIN_INVALID_STATE"]
    message: Literal["현재 상태에서는 이 작업을 수행할 수 없습니다."]
    request_id: UUID
    retryable: Literal[False]


class AdminValidationFailedError(StrictPublicModel):
    code: Literal["ADMIN_VALIDATION_FAILED"]
    message: Literal["입력값을 확인해 주세요."]
    request_id: UUID
    retryable: Literal[False]


type AdminError = Annotated[
    AdminRouteDisabledError
    | AdminForbiddenError
    | AdminNotFoundError
    | AdminInvalidStateError
    | AdminValidationFailedError,
    Field(discriminator="code"),
]


class AdminErrorEnvelope(StrictPublicModel):
    error: AdminError


__all__ = [
    "AdminErrorEnvelope",
    "CivicScopeGapListResponse",
    "CivicScopeGapReviewRequest",
    "CivicScopeGapReviewResponse",
    "CivicScopeGapSummary",
    "FailedQuestion",
    "FailedQuestionDetailResponse",
    "FailedQuestionListResponse",
    "KBCandidateCreateRequest",
    "KBCandidateCreateResponse",
    "KBCandidateListResponse",
    "KBCandidateReviewResponse",
    "KBCandidateSubmitResponse",
    "KBCandidateSummary",
    "CandidateReviewRequest",
    "ReasonConfirmationRequest",
    "ReasonConfirmationResponse",
]
