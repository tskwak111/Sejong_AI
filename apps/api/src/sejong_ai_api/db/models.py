"""Immutable typed values for the private database boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import cast
from urllib.parse import urlsplit
from uuid import UUID


class AdminRole(str, Enum):  # noqa: UP042 - approved str/Enum contract
    OPERATOR = "OPERATOR"
    APPROVER = "APPROVER"


class Intent(str, Enum):  # noqa: UP042 - approved str/Enum contract
    MOVE_IN_RESIDENT_REGISTRATION = "MOVE_IN_RESIDENT_REGISTRATION"
    CERTIFICATE_ISSUANCE = "CERTIFICATE_ISSUANCE"
    BULKY_WASTE = "BULKY_WASTE"
    LOCAL_TAX_GENERAL = "LOCAL_TAX_GENERAL"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNKNOWN = "UNKNOWN"


class AnswerStatus(str, Enum):  # noqa: UP042 - approved str/Enum contract
    SUCCESS = "SUCCESS"
    FOLLOWUP = "FOLLOWUP"
    FALLBACK = "FALLBACK"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class FallbackReason(str, Enum):  # noqa: UP042 - approved str/Enum contract
    INSUFFICIENT_GROUNDING = "INSUFFICIENT_GROUNDING"
    PERSONAL_LOOKUP = "PERSONAL_LOOKUP"
    LEGAL_JUDGMENT = "LEGAL_JUDGMENT"
    CIVIC_SCOPE_GAP = "CIVIC_SCOPE_GAP"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class Region(str, Enum):  # noqa: UP042 - approved str/Enum contract
    AREUM_DONG = "아름동"
    DODAM_DONG = "도담동"
    JOCHIWON_EUP = "조치원읍"


class DataOrigin(str, Enum):  # noqa: UP042 - approved str/Enum contract
    OFFICIAL = "OFFICIAL"
    MOCK = "MOCK"


_FEEDBACK_RATINGS = frozenset({"SATISFIED", "DISSATISFIED"})
_FEEDBACK_CATEGORIES = frozenset(
    {
        "MOVE_IN_RESIDENT_REGISTRATION",
        "CERTIFICATE_ISSUANCE",
        "BULKY_WASTE",
        "LOCAL_TAX_GENERAL",
        "OTHER",
    }
)
_FEEDBACK_REASONS = frozenset(
    {
        "INACCURATE",
        "NOT_RELEVANT",
        "HARD_TO_UNDERSTAND",
        "WRONG_CONTACT",
        "OTHER",
    }
)


_SUPPORTED_INTENTS = frozenset(
    {
        Intent.MOVE_IN_RESIDENT_REGISTRATION,
        Intent.CERTIFICATE_ISSUANCE,
        Intent.BULKY_WASTE,
        Intent.LOCAL_TAX_GENERAL,
    }
)
_RETAINABLE_FAILURE_REASONS = frozenset(
    {
        FallbackReason.INSUFFICIENT_GROUNDING,
        FallbackReason.PERSONAL_LOOKUP,
        FallbackReason.LEGAL_JUDGMENT,
    }
)


def _require_uuid(value: object, message: str) -> None:
    if type(value) is not UUID:
        raise ValueError(message)


def _require_enum(value: object, enum_type: type[Enum], message: str) -> None:
    if type(value) is not enum_type:
        raise ValueError(message)


def _require_text(value: object, message: str) -> None:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError(message)


def _require_optional_text(value: object, message: str) -> None:
    if value is not None:
        _require_text(value, message)


def _require_https_url(value: object, message: str) -> None:
    _require_text(value, message)
    parsed = urlsplit(cast(str, value))
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(message)


def _require_optional_https_url(value: object, message: str) -> None:
    if value is not None:
        _require_https_url(value, message)


def _require_text_tuple(value: object, message: str) -> None:
    if type(value) is not tuple:
        raise ValueError(message)
    for item in value:
        _require_text(item, message)


def _require_uuid_tuple(value: object, message: str) -> None:
    if type(value) is not tuple or any(type(item) is not UUID for item in value):
        raise ValueError(message)


def _require_date(value: object, message: str) -> None:
    if type(value) is not date:
        raise ValueError(message)


@dataclass(frozen=True, slots=True)
class Actor:
    actor_id: str
    role: AdminRole

    def __post_init__(self) -> None:
        _require_text(self.actor_id, "ACTOR_ID_INVALID")
        _require_enum(self.role, AdminRole, "ACTOR_ROLE_INVALID")


@dataclass(frozen=True, slots=True)
class CitizenFeedbackWrite:
    response_request_id: UUID
    rating: str
    category: str | None
    reason_code: str | None
    masked_detail: str | None
    detail_was_masked: bool

    def __post_init__(self) -> None:
        _require_uuid(self.response_request_id, "FEEDBACK_REQUEST_ID_INVALID")
        if type(self.rating) is not str or self.rating not in _FEEDBACK_RATINGS:
            raise ValueError("FEEDBACK_RATING_INVALID")
        if self.rating == "SATISFIED":
            dissatisfaction_values = (
                self.category,
                self.reason_code,
                self.masked_detail,
            )
            if any(value is not None for value in dissatisfaction_values):
                raise ValueError("FEEDBACK_SHAPE_INVALID")
            if self.detail_was_masked is not False:
                raise ValueError("FEEDBACK_SHAPE_INVALID")
            return
        if (
            type(self.category) is not str
            or self.category not in _FEEDBACK_CATEGORIES
            or type(self.reason_code) is not str
            or self.reason_code not in _FEEDBACK_REASONS
        ):
            raise ValueError("FEEDBACK_SHAPE_INVALID")
        _require_optional_text(self.masked_detail, "FEEDBACK_DETAIL_INVALID")
        if self.masked_detail is not None and len(self.masked_detail) > 300:
            raise ValueError("FEEDBACK_DETAIL_INVALID")
        if type(self.detail_was_masked) is not bool:
            raise ValueError("FEEDBACK_SHAPE_INVALID")
        if self.reason_code == "OTHER" and self.masked_detail is None:
            raise ValueError("FEEDBACK_SHAPE_INVALID")


@dataclass(frozen=True, slots=True)
class CitizenFeedbackAggregate:
    total: int
    satisfied: int
    dissatisfied: int
    category_counts: tuple[tuple[str, int], ...]
    reason_counts: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        if (
            type(self.total) is not int
            or type(self.satisfied) is not int
            or type(self.dissatisfied) is not int
            or min(self.total, self.satisfied, self.dissatisfied) < 0
            or self.satisfied + self.dissatisfied != self.total
        ):
            raise ValueError("FEEDBACK_AGGREGATE_INVALID")
        for counts in (self.category_counts, self.reason_counts):
            if type(counts) is not tuple or any(
                type(item) is not tuple
                or len(item) != 2
                or type(item[0]) is not str
                or not item[0]
                or type(item[1]) is not int
                or item[1] < 0
                for item in counts
            ):
                raise ValueError("FEEDBACK_AGGREGATE_INVALID")


@dataclass(frozen=True, slots=True)
class InteractionWrite:
    request_id: UUID
    intent: Intent
    answer_status: AnswerStatus
    fallback_reason: FallbackReason | None
    used_source_ids: tuple[str, ...]
    response_time_ms: int
    selected_region: Region | None
    routed_office_public_id: str | None
    is_test: bool
    masked_question: str | None

    def __post_init__(self) -> None:
        _require_uuid(self.request_id, "REQUEST_ID_INVALID")
        _require_enum(self.intent, Intent, "INTENT_INVALID")
        _require_enum(self.answer_status, AnswerStatus, "ANSWER_STATUS_INVALID")
        if self.fallback_reason is not None:
            _require_enum(self.fallback_reason, FallbackReason, "FALLBACK_REASON_INVALID")
        _require_text_tuple(self.used_source_ids, "USED_SOURCE_IDS_INVALID")
        if len(set(self.used_source_ids)) != len(self.used_source_ids):
            raise ValueError("USED_SOURCE_IDS_INVALID")
        if type(self.response_time_ms) is not int or self.response_time_ms < 0:
            raise ValueError("RESPONSE_TIME_MS_INVALID")
        if self.selected_region is not None:
            _require_enum(self.selected_region, Region, "REGION_INVALID")
        _require_optional_text(self.routed_office_public_id, "ROUTED_OFFICE_ID_INVALID")
        if type(self.is_test) is not bool:
            raise ValueError("IS_TEST_INVALID")
        _require_optional_text(self.masked_question, "MASKED_QUESTION_INVALID")
        if not self._combination_is_valid():
            raise ValueError("INTERACTION_COMBINATION_INVALID")

    def _combination_is_valid(self) -> bool:
        no_sources = not self.used_source_ids
        no_masked_text = self.masked_question is None

        if self.answer_status is AnswerStatus.SUCCESS:
            return (
                self.intent in _SUPPORTED_INTENTS
                and self.fallback_reason is None
                and not no_sources
                and no_masked_text
            )
        if self.answer_status is AnswerStatus.FOLLOWUP:
            return (
                (self.intent in _SUPPORTED_INTENTS or self.intent is Intent.UNKNOWN)
                and self.fallback_reason is None
                and no_sources
                and no_masked_text
            )
        if self.answer_status is AnswerStatus.FALLBACK:
            if self.fallback_reason is FallbackReason.OUT_OF_SCOPE:
                return self.intent is Intent.OUT_OF_SCOPE and no_sources and no_masked_text
            return (
                self.fallback_reason in _RETAINABLE_FAILURE_REASONS
                and self.intent in _SUPPORTED_INTENTS
                and no_sources
            )
        return self.fallback_reason is None and no_sources and no_masked_text


@dataclass(frozen=True, slots=True)
class InteractionWriteResult:
    interaction_id: UUID
    failed_question_id: UUID | None

    def __post_init__(self) -> None:
        _require_uuid(self.interaction_id, "INTERACTION_ID_INVALID")
        if self.failed_question_id is not None:
            _require_uuid(self.failed_question_id, "FAILED_QUESTION_ID_INVALID")


@dataclass(frozen=True, slots=True)
class FailureReasonConfirmation:
    failed_question_id: UUID
    actor: Actor
    fallback_reason: FallbackReason

    def __post_init__(self) -> None:
        _require_uuid(self.failed_question_id, "FAILED_QUESTION_ID_INVALID")
        if type(self.actor) is not Actor:
            raise ValueError("ACTOR_INVALID")
        if self.actor.role is not AdminRole.OPERATOR:
            raise ValueError("ACTOR_ROLE_FORBIDDEN")
        _require_enum(self.fallback_reason, FallbackReason, "FALLBACK_REASON_INVALID")
        if self.fallback_reason not in _RETAINABLE_FAILURE_REASONS:
            raise ValueError("FALLBACK_REASON_INVALID")


@dataclass(frozen=True, slots=True)
class CandidateDraft:
    failed_question_id: UUID
    actor: Actor
    title: str
    representative_question: str
    category: Intent
    answer_summary: str
    procedure_steps: tuple[str, ...]
    required_documents: tuple[str, ...]
    processing_time: str | None
    fee: str | None
    department: str
    source_title: str
    source_url: str
    last_verified_at: date
    caution: str | None
    data_origin: DataOrigin

    def __post_init__(self) -> None:
        _require_uuid(self.failed_question_id, "FAILED_QUESTION_ID_INVALID")
        if type(self.actor) is not Actor:
            raise ValueError("ACTOR_INVALID")
        if self.actor.role is not AdminRole.OPERATOR:
            raise ValueError("ACTOR_ROLE_FORBIDDEN")
        _require_text(self.title, "TITLE_INVALID")
        _require_text(self.representative_question, "REPRESENTATIVE_QUESTION_INVALID")
        _require_enum(self.category, Intent, "CATEGORY_INVALID")
        if self.category not in _SUPPORTED_INTENTS:
            raise ValueError("CATEGORY_INVALID")
        _require_text(self.answer_summary, "ANSWER_SUMMARY_INVALID")
        _require_text_tuple(self.procedure_steps, "PROCEDURE_STEPS_INVALID")
        _require_text_tuple(self.required_documents, "REQUIRED_DOCUMENTS_INVALID")
        _require_optional_text(self.processing_time, "PROCESSING_TIME_INVALID")
        _require_optional_text(self.fee, "FEE_INVALID")
        _require_text(self.department, "DEPARTMENT_INVALID")
        _require_text(self.source_title, "SOURCE_TITLE_INVALID")
        _require_https_url(self.source_url, "SOURCE_URL_INVALID")
        _require_date(self.last_verified_at, "LAST_VERIFIED_AT_INVALID")
        _require_optional_text(self.caution, "CAUTION_INVALID")
        _require_enum(self.data_origin, DataOrigin, "DATA_ORIGIN_INVALID")


@dataclass(frozen=True, slots=True)
class KnowledgeRecord:
    public_id: str
    category: Intent
    service_name: str
    answer_summary: str
    procedure_steps: tuple[str, ...]
    required_documents: tuple[str, ...]
    processing_time: str | None
    fee: str | None
    department: str
    source_title: str
    source_url: str
    last_verified_at: date
    caution: str | None
    question_examples: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_text(self.public_id, "PUBLIC_ID_INVALID")
        _require_enum(self.category, Intent, "CATEGORY_INVALID")
        if self.category not in _SUPPORTED_INTENTS:
            raise ValueError("CATEGORY_INVALID")
        _require_text(self.service_name, "SERVICE_NAME_INVALID")
        _require_text(self.answer_summary, "ANSWER_SUMMARY_INVALID")
        _require_text_tuple(self.procedure_steps, "PROCEDURE_STEPS_INVALID")
        _require_text_tuple(self.required_documents, "REQUIRED_DOCUMENTS_INVALID")
        _require_optional_text(self.processing_time, "PROCESSING_TIME_INVALID")
        _require_optional_text(self.fee, "FEE_INVALID")
        _require_text(self.department, "DEPARTMENT_INVALID")
        _require_text(self.source_title, "SOURCE_TITLE_INVALID")
        _require_https_url(self.source_url, "SOURCE_URL_INVALID")
        _require_date(self.last_verified_at, "LAST_VERIFIED_AT_INVALID")
        _require_optional_text(self.caution, "CAUTION_INVALID")
        _require_text_tuple(self.question_examples, "QUESTION_EXAMPLES_INVALID")
        if not self.question_examples:
            raise ValueError("QUESTION_EXAMPLES_INVALID")


@dataclass(frozen=True, slots=True)
class OfficeRecord:
    public_id: str
    region: Region
    office_name: str
    address: str
    phone: str
    opening_hours: str | None
    map_url: str | None
    department_label: str | None
    source_title: str
    source_url: str
    last_verified_at: date

    def __post_init__(self) -> None:
        _require_text(self.public_id, "PUBLIC_ID_INVALID")
        _require_enum(self.region, Region, "REGION_INVALID")
        _require_text(self.office_name, "OFFICE_NAME_INVALID")
        _require_text(self.address, "ADDRESS_INVALID")
        _require_text(self.phone, "PHONE_INVALID")
        _require_optional_text(self.opening_hours, "OPENING_HOURS_INVALID")
        _require_optional_https_url(self.map_url, "MAP_URL_INVALID")
        _require_optional_text(self.department_label, "DEPARTMENT_LABEL_INVALID")
        _require_text(self.source_title, "SOURCE_TITLE_INVALID")
        _require_https_url(self.source_url, "SOURCE_URL_INVALID")
        _require_date(self.last_verified_at, "LAST_VERIFIED_AT_INVALID")


@dataclass(frozen=True, slots=True)
class PurgeResult:
    purged_count: int
    purged_ids: tuple[UUID, ...]

    def __post_init__(self) -> None:
        if type(self.purged_count) is not int or self.purged_count < 0:
            raise ValueError("PURGED_COUNT_INVALID")
        _require_uuid_tuple(self.purged_ids, "PURGED_IDS_INVALID")
        if self.purged_count != len(self.purged_ids):
            raise ValueError("PURGED_IDS_INVALID")
