"""Closed, provider-neutral values for local synthetic generation."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from sejong_ai_api.db.models import Intent, KnowledgeRecord


class GeneratedAnswer(BaseModel):
    """The complete source-free payload the provider is permitted to return."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    summary: Annotated[str, Field(min_length=1, max_length=500)]
    procedure_steps: Annotated[list[str], Field(max_length=12)]
    required_documents: Annotated[list[str], Field(max_length=12)]
    processing_time: Annotated[str, Field(min_length=1, max_length=200)] | None
    fee: Annotated[str, Field(min_length=1, max_length=200)] | None
    department: Annotated[str, Field(min_length=1, max_length=200)] | None


@dataclass(frozen=True, slots=True)
class GroundedFixture:
    fixture_id: str
    masked_question: str
    intent: Intent
    record: KnowledgeRecord

    def __post_init__(self) -> None:
        if type(self.fixture_id) is not str or not self.fixture_id:
            raise ValueError("FIXTURE_ID_INVALID")
        if type(self.masked_question) is not str or not self.masked_question:
            raise ValueError("MASKED_QUESTION_INVALID")
        if type(self.intent) is not Intent:
            raise ValueError("INTENT_INVALID")
        if type(self.record) is not KnowledgeRecord:
            raise ValueError("KNOWLEDGE_RECORD_INVALID")
        if self.record.category is not self.intent:
            raise ValueError("GROUNDED_FIXTURE_INTENT_INVALID")


@dataclass(frozen=True, slots=True)
class TokenUsage:
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int

    def __post_init__(self) -> None:
        if any(
            type(value) is not int or value < 0
            for value in (self.input_tokens, self.cached_input_tokens, self.output_tokens)
        ):
            raise ValueError("TOKEN_USAGE_INVALID")
        if self.cached_input_tokens > self.input_tokens:
            raise ValueError("CACHED_INPUT_TOKENS_INVALID")


class OutcomeCode(str, Enum):  # noqa: UP042 - approved str/Enum contract
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
class GenerationOutcome:
    code: OutcomeCode
    answer: GeneratedAnswer | None
    usage: TokenUsage
    attempts_used: int

    def __post_init__(self) -> None:
        if type(self.code) is not OutcomeCode:
            raise ValueError("OUTCOME_CODE_INVALID")
        if self.answer is not None and type(self.answer) is not GeneratedAnswer:
            raise ValueError("GENERATED_ANSWER_INVALID")
        if type(self.usage) is not TokenUsage:
            raise ValueError("TOKEN_USAGE_INVALID")
        if type(self.attempts_used) is not int or self.attempts_used < 0:
            raise ValueError("ATTEMPTS_USED_INVALID")
        if (self.code is OutcomeCode.SUCCESS) is not (self.answer is not None):
            raise ValueError("GENERATION_OUTCOME_INVALID")
