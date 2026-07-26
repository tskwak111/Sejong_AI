"""Pure, closed contracts for a grounded citizen-chat generation attempt."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Protocol

from pydantic import Field

from sejong_ai_api.contracts.health import StrictPublicModel
from sejong_ai_api.db.models import Intent


class FactKind(StrEnum):
    """The only fact categories that a grounded chat prompt may carry."""

    PROCEDURE_STEP = "PROCEDURE_STEP"
    REQUIRED_DOCUMENT = "REQUIRED_DOCUMENT"
    PROCESSING_TIME = "PROCESSING_TIME"
    FEE = "FEE"
    DEPARTMENT = "DEPARTMENT"


@dataclass(frozen=True, slots=True)
class GroundedFact:
    """A server-issued, request-local reference to one approved fact."""

    fact_id: str
    kind: FactKind
    text: str

    def __post_init__(self) -> None:
        if (
            type(self.fact_id) is not str
            or not self.fact_id
            or self.fact_id.strip() != self.fact_id
            or type(self.kind) is not FactKind
            or type(self.text) is not str
            or not self.text
            or self.text.strip() != self.text
        ):
            raise ValueError("GROUNDED_FACT_INVALID")


def _is_canonical_fact_sequence(facts: object) -> bool:
    if type(facts) is not tuple or not facts:
        return False
    try:
        if any(
            type(fact) is not GroundedFact
            or type(fact.fact_id) is not str
            or type(fact.kind) is not FactKind
            or type(fact.text) is not str
            or not fact.text
            or fact.text.strip() != fact.text
            for fact in facts
        ):
            return False

        cursor = 0
        for kind, prefix in (
            (FactKind.PROCEDURE_STEP, "STEP"),
            (FactKind.REQUIRED_DOCUMENT, "DOC"),
        ):
            index = 1
            while cursor < len(facts) and facts[cursor].kind is kind:
                if index > 12 or facts[cursor].fact_id != f"{prefix}-{index:02d}":
                    return False
                cursor += 1
                index += 1

        for kind, fact_id in (
            (FactKind.PROCESSING_TIME, "TIME-01"),
            (FactKind.FEE, "FEE-01"),
        ):
            if cursor < len(facts) and facts[cursor].kind is kind:
                if facts[cursor].fact_id != fact_id:
                    return False
                cursor += 1

        return (
            cursor + 1 == len(facts)
            and facts[cursor].kind is FactKind.DEPARTMENT
            and facts[cursor].fact_id == "DEPT-01"
        )
    except (AttributeError, TypeError):
        return False


@dataclass(frozen=True, slots=True)
class GroundedChatRequest:
    """Provider-safe facts derived from exactly one grounded knowledge record."""

    masked_question: str
    intent: Intent
    service_name: str
    approved_summary: str
    facts: tuple[GroundedFact, ...]

    def __post_init__(self) -> None:
        if (
            type(self.masked_question) is not str
            or not self.masked_question
            or self.masked_question.strip() != self.masked_question
            or type(self.intent) is not Intent
            or type(self.service_name) is not str
            or not self.service_name
            or self.service_name.strip() != self.service_name
            or type(self.approved_summary) is not str
            or not self.approved_summary
            or self.approved_summary.strip() != self.approved_summary
            or type(self.facts) is not tuple
            or not _is_canonical_fact_sequence(self.facts)
        ):
            raise ValueError("GROUNDED_CHAT_REQUEST_INVALID")


class GeneratedChatDraft(StrictPublicModel):
    """The provider's closed, identifier-only draft payload."""

    summary: Annotated[str, Field(min_length=1, max_length=500)]
    procedure_step_ids: Annotated[list[str], Field(max_length=12)]
    required_document_ids: Annotated[list[str], Field(max_length=12)]
    processing_time_id: str | None
    fee_id: str | None
    department_id: str


@dataclass(frozen=True, slots=True)
class MaterializedChatAnswer:
    """A locally materialized answer with official fields copied byte-for-byte."""

    summary: str
    procedure_steps: tuple[str, ...]
    required_documents: tuple[str, ...]
    processing_time: str | None
    fee: str | None
    department: str

    def __post_init__(self) -> None:
        if (
            type(self.summary) is not str
            or not self.summary
            or type(self.procedure_steps) is not tuple
            or type(self.required_documents) is not tuple
            or any(type(step) is not str or not step for step in self.procedure_steps)
            or any(
                type(document) is not str or not document for document in self.required_documents
            )
            or (self.processing_time is not None and type(self.processing_time) is not str)
            or (self.fee is not None and type(self.fee) is not str)
            or type(self.department) is not str
            or not self.department
        ):
            raise ValueError("MATERIALIZED_CHAT_ANSWER_INVALID")


class GroundedChatOutcomeCode(StrEnum):
    SUCCESS = "SUCCESS"
    ATTEMPT_CAP = "ATTEMPT_CAP"
    TIMEOUT = "TIMEOUT"
    TRANSPORT = "TRANSPORT"
    RATE_LIMIT = "RATE_LIMIT"
    AUTH = "AUTH"
    HTTP_ERROR = "HTTP_ERROR"
    EMPTY = "EMPTY"
    TRUNCATED = "TRUNCATED"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    INPUT_LIMIT = "INPUT_LIMIT"


@dataclass(frozen=True, slots=True)
class GroundedChatResult:
    """Content-free adapter outcome used by the post-grounding service."""

    code: GroundedChatOutcomeCode
    draft: GeneratedChatDraft | None = None

    def __post_init__(self) -> None:
        if type(self.code) is not GroundedChatOutcomeCode or (
            (self.code is GroundedChatOutcomeCode.SUCCESS) is not (self.draft is not None)
        ):
            raise ValueError("GROUNDED_CHAT_RESULT_INVALID")
        if self.draft is not None and type(self.draft) is not GeneratedChatDraft:
            raise ValueError("GROUNDED_CHAT_RESULT_INVALID")


class GroundedAnswerGenerator(Protocol):
    """A provider-neutral one-attempt generator boundary."""

    async def generate(self, request: GroundedChatRequest) -> GroundedChatResult: ...
