"""Grounding gate for deterministic, server-bound KB answers."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.retrieval import (
    GroundingEvidenceKind,
    TopicSelection,
)
from sejong_ai_api.db.models import Intent, KnowledgeRecord

_RECORD_SPECIFIC_DETAILS: dict[Intent, tuple[str, ...]] = {
    Intent.BULKY_WASTE: ("토퍼",),
    Intent.MOVE_IN_RESIDENT_REGISTRATION: ("모든우편물", "우편물주소"),
}


@dataclass(frozen=True, slots=True)
class GroundingDecision:
    """A grounded record or a closed insufficient-grounding decision.

    High-risk and source properties are derived directly from ``record`` and
    cannot be supplied independently by a caller or text generator.
    """

    record: KnowledgeRecord | None
    matched_tokens: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.record is not None and type(self.record) is not KnowledgeRecord:
            raise ValueError("GROUNDING_RECORD_INVALID")
        if type(self.matched_tokens) is not tuple or any(
            type(token) is not str or not token for token in self.matched_tokens
        ):
            raise ValueError("GROUNDING_MATCH_INVALID")
        if self.record is None and self.matched_tokens:
            raise ValueError("GROUNDING_MATCH_INVALID")

    @property
    def is_grounded(self) -> bool:
        return self.record is not None

    @property
    def processing_time(self) -> str | None:
        return None if self.record is None else self.record.processing_time

    @property
    def fee(self) -> str | None:
        return None if self.record is None else self.record.fee

    @property
    def caution(self) -> str | None:
        return None if self.record is None else self.record.caution

    @property
    def source_title(self) -> str | None:
        return None if self.record is None else self.record.source_title

    @property
    def source_url(self) -> str | None:
        return None if self.record is None else self.record.source_url

    @property
    def last_verified_at(self) -> date | None:
        return None if self.record is None else self.record.last_verified_at


def evaluate_grounding(
    question: SafeQuestion,
    intent: Intent,
    selection: TopicSelection | None,
) -> GroundingDecision:
    """Expose facts only when a typed selection matches the current record."""

    if type(question) is not SafeQuestion:
        raise TypeError("SAFE_QUESTION_REQUIRED")
    if type(intent) is not Intent:
        raise ValueError("INTENT_REQUIRED")
    if selection is None:
        return GroundingDecision(None, ())
    if type(selection) is not TopicSelection:
        raise TypeError("TOPIC_SELECTION_REQUIRED")

    topic = selection.topic
    evidence = selection.evidence
    record = topic.record
    if (
        record.category is not intent
        or evidence.topic_id != record.public_id
        or (
            evidence.kind
            in {
                GroundingEvidenceKind.VALIDATED_SEMANTIC_COVERAGE,
                GroundingEvidenceKind.VALIDATED_CONTEXT_FACET,
            }
            and evidence.coverage_id != topic.coverage.coverage_id
        )
        or (
            evidence.kind
            in {
                GroundingEvidenceKind.EXACT_APPROVED_EXAMPLE,
                GroundingEvidenceKind.UNIQUE_LEXICAL_MATCH,
            }
            and evidence.coverage_id is not None
        )
    ):
        return GroundingDecision(None, ())

    question_compact = _compact(question.text)
    record_compact = _compact(
        " ".join(
            (
                record.service_name,
                record.answer_summary,
                *record.question_examples,
                *record.procedure_steps,
                *record.required_documents,
                record.caution or "",
            )
        )
    )
    for detail in _RECORD_SPECIFIC_DETAILS.get(intent, ()):
        if detail in question_compact and detail not in record_compact:
            return GroundingDecision(None, ())
    return GroundingDecision(record, evidence.matched_tokens)


def _compact(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^0-9a-z가-힣]", "", normalized)


__all__ = ["GroundingDecision", "evaluate_grounding"]
