"""Typed runtime models for the approved chat contract intersection."""

from datetime import date
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    AnyUrl,
    ConfigDict,
    Field,
    TypeAdapter,
    UrlConstraints,
    field_validator,
    model_validator,
)

from sejong_ai_api.contracts.health import (
    ServiceUnavailableEnvelope,
    StrictPublicModel,
)

type Intent = Literal[
    "MOVE_IN_RESIDENT_REGISTRATION",
    "CERTIFICATE_ISSUANCE",
    "BULKY_WASTE",
    "LOCAL_TAX_GENERAL",
    "OUT_OF_SCOPE",
    "UNKNOWN",
]
type FallbackReason = Literal[
    "INSUFFICIENT_GROUNDING",
    "PERSONAL_LOOKUP",
    "LEGAL_JUDGMENT",
    "OUT_OF_SCOPE",
    "PRIVACY_UNRESOLVED",
]
type SupportedIntent = Literal[
    "MOVE_IN_RESIDENT_REGISTRATION",
    "CERTIFICATE_ISSUANCE",
    "BULKY_WASTE",
    "LOCAL_TAX_GENERAL",
]
type AnswerMode = Literal["GENERATED", "TEMPLATE"]
type Region = Literal["아름동", "도담동", "조치원읍"]
type ContextToken = Annotated[str, Field(min_length=1, max_length=2048)]
type HttpsUrl = Annotated[AnyUrl, UrlConstraints(allowed_schemes=["https"])]

PRIVACY_FALLBACK_TITLE = "개인정보를 안전하게 처리하지 못했어요"
PRIVACY_FALLBACK_MESSAGE = "개인정보를 빼거나 표현을 바꿔서 다시 질문해 주세요."
PRIVACY_FALLBACK_NEXT_ACTIONS = ("이름, 주소, 전화번호, 접수번호 등을 적지 마세요.",)


class ChatRequest(StrictPublicModel):
    question: Annotated[str, Field(min_length=1, max_length=1000)]
    context_token: ContextToken | None = None
    selected_region: Region | None = None
    simple_language: bool = False


class Source(StrictPublicModel):
    source_id: str
    title: str
    url: HttpsUrl
    last_verified_at: date
    used_fields: list[str] = Field(default_factory=list)


class Office(StrictPublicModel):
    """OpenAPI intentionally permits forward-compatible office fields."""

    model_config = ConfigDict(extra="allow", strict=True)

    id: str
    region: str
    office_name: str
    address: str
    phone: str
    opening_hours: str | None = None
    map_url: HttpsUrl | None = None
    source_title: str
    source_url: HttpsUrl | None = Field(default=None, exclude_if=lambda value: value is None)
    last_verified_at: date

    @field_validator("source_url", mode="before")
    @classmethod
    def reject_explicit_null_source_url(cls, value: object) -> object:
        if value is None:
            raise ValueError("source_url may be omitted but cannot be null")
        return value


class Fallback(StrictPublicModel):
    reason: FallbackReason
    title: str
    message: str
    next_actions: list[str] = Field(default_factory=list)
    candidate_eligible: bool
    office: Office | None = None


class ChatResponseBase(StrictPublicModel):
    request_id: UUID
    intent: Intent
    confidence: Annotated[float | None, Field(ge=0, le=1)] = None
    summary: str | None = None
    procedure_steps: list[str] = Field(default_factory=list)
    required_documents: list[str] = Field(default_factory=list)
    processing_time: str | None = None
    fee: str | None = None
    department: str | None = None
    followup_options: list[str] = Field(default_factory=list)
    fallback: Fallback | None = None


class SuccessResponse(ChatResponseBase):
    answer_status: Literal["SUCCESS"]
    answer_mode: AnswerMode
    intent: SupportedIntent
    sources: Annotated[list[Source], Field(min_length=1)]
    office: Office | None
    followup_options: Annotated[list[str], Field(max_length=0)] = Field(default_factory=list)
    fallback: None = None
    context_token: ContextToken | None


class FollowupResponse(ChatResponseBase):
    answer_status: Literal["FOLLOWUP"]
    intent: SupportedIntent | Literal["UNKNOWN"]
    summary: None = None
    procedure_steps: Annotated[list[str], Field(max_length=0)] = Field(default_factory=list)
    required_documents: Annotated[list[str], Field(max_length=0)] = Field(default_factory=list)
    processing_time: None = None
    fee: None = None
    department: None = None
    sources: Annotated[list[Source], Field(max_length=0)]
    office: None
    followup_options: Annotated[list[str], Field(min_length=1)]
    fallback: None = None
    context_token: ContextToken | None


class FallbackResponse(ChatResponseBase):
    answer_status: Literal["FALLBACK"]
    confidence: None = None
    summary: None = None
    procedure_steps: Annotated[list[str], Field(max_length=0)] = Field(default_factory=list)
    required_documents: Annotated[list[str], Field(max_length=0)] = Field(default_factory=list)
    processing_time: None = None
    fee: None = None
    department: None = None
    sources: Annotated[list[Source], Field(max_length=0)]
    followup_options: Annotated[list[str], Field(max_length=0)] = Field(default_factory=list)
    fallback: Fallback
    context_token: None

    @model_validator(mode="after")
    def validate_fallback_semantics(self) -> Self:
        reason = self.fallback.reason
        expected_candidate_eligible = reason == "INSUFFICIENT_GROUNDING"
        if self.fallback.candidate_eligible is not expected_candidate_eligible:
            raise ValueError("fallback candidate eligibility does not match its reason")

        if reason == "OUT_OF_SCOPE" and self.intent != "OUT_OF_SCOPE":
            raise ValueError("OUT_OF_SCOPE fallback requires OUT_OF_SCOPE intent")
        if reason == "INSUFFICIENT_GROUNDING" and self.intent not in {
            "MOVE_IN_RESIDENT_REGISTRATION",
            "CERTIFICATE_ISSUANCE",
            "BULKY_WASTE",
            "LOCAL_TAX_GENERAL",
        }:
            raise ValueError("INSUFFICIENT_GROUNDING requires a supported intent")

        if reason in {"PERSONAL_LOOKUP", "LEGAL_JUDGMENT"} and self.intent != "UNKNOWN":
            raise ValueError("policy fallback requires UNKNOWN intent")

        if reason == "PRIVACY_UNRESOLVED":
            if self.intent != "UNKNOWN":
                raise ValueError("PRIVACY_UNRESOLVED requires UNKNOWN intent")
            if "confidence" not in self.model_fields_set:
                raise ValueError("PRIVACY_UNRESOLVED requires explicit null confidence")
            if "office" not in self.fallback.model_fields_set or self.fallback.office is not None:
                raise ValueError("PRIVACY_UNRESOLVED requires explicit null office")
            if self.fallback.title != PRIVACY_FALLBACK_TITLE:
                raise ValueError("PRIVACY_UNRESOLVED requires the approved safe title")
            if self.fallback.message != PRIVACY_FALLBACK_MESSAGE:
                raise ValueError("PRIVACY_UNRESOLVED requires the approved safe message")
            if tuple(self.fallback.next_actions) != PRIVACY_FALLBACK_NEXT_ACTIONS:
                raise ValueError("PRIVACY_UNRESOLVED requires the approved safe next action")
        return self


type ChatResponse = Annotated[
    SuccessResponse | FollowupResponse | FallbackResponse,
    Field(discriminator="answer_status"),
]
CHAT_RESPONSE_ADAPTER: TypeAdapter[ChatResponse] = TypeAdapter(ChatResponse)


__all__ = [
    "CHAT_RESPONSE_ADAPTER",
    "AnswerMode",
    "ChatRequest",
    "ChatResponse",
    "FallbackResponse",
    "FollowupResponse",
    "HttpsUrl",
    "Office",
    "ServiceUnavailableEnvelope",
    "Source",
    "SuccessResponse",
]
