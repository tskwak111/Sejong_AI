"""Grounding gate for deterministic, server-bound KB answers."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.retrieval import meaningful_tokens
from sejong_ai_api.db.models import Intent, KnowledgeRecord

_INTENT_ANCHORS: dict[Intent, frozenset[str]] = {
    Intent.MOVE_IN_RESIDENT_REGISTRATION: frozenset(
        {"전입신고", "주소변경", "주민등록", "통보서비스"}
    ),
    Intent.CERTIFICATE_ISSUANCE: frozenset(
        {
            "주민등록",
            "주민등록표",
            "등본",
            "초본",
            "무인민원발급",
            "무인발급기",
        }
    ),
    Intent.BULKY_WASTE: frozenset(
        {"대형폐기물", "폐기물", "침대", "프레임", "매트리스", "소파", "가구", "배출"}
    ),
    Intent.LOCAL_TAX_GENERAL: frozenset(
        {
            "지방세",
            "자동차세",
            "재산세",
            "주민세",
            "취득세",
            "체납",
            "납세증명",
            "전자납부번호",
            "과세증명서",
            "납부확인서",
        }
    ),
}
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
    record: KnowledgeRecord | None,
    *,
    allow_contextual_detail: bool = False,
) -> GroundingDecision:
    """Require exact intent agreement and at least one meaningful token match."""

    if type(question) is not SafeQuestion:
        raise TypeError("SAFE_QUESTION_REQUIRED")
    if type(intent) is not Intent:
        raise ValueError("INTENT_REQUIRED")
    if type(allow_contextual_detail) is not bool:
        raise ValueError("CONTEXTUAL_DETAIL_FLAG_INVALID")
    if type(record) is not KnowledgeRecord or record.category is not intent:
        return GroundingDecision(None, ())

    question_tokens = meaningful_tokens(question.text)
    record_tokens = meaningful_tokens(
        " ".join(
            (
                record.service_name,
                record.answer_summary,
                *record.question_examples,
                *record.procedure_steps,
                *record.required_documents,
            )
        )
    )
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
    overlap = tuple(sorted(question_tokens & record_tokens))
    exact_approved_example = any(
        _compact(example) == question_compact for example in record.question_examples
    )
    if not overlap or (
        not allow_contextual_detail
        and not exact_approved_example
        and not (set(overlap) & _INTENT_ANCHORS.get(intent, frozenset()))
    ):
        return GroundingDecision(None, ())
    return GroundingDecision(record, overlap)


def _compact(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^0-9a-z가-힣]", "", normalized)


__all__ = ["GroundingDecision", "evaluate_grounding"]
