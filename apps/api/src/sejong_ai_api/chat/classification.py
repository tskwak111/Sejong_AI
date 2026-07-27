"""Deterministic policy and intent classification for redacted chat questions.

This module accepts only :class:`SafeQuestion`, which can only be constructed
from a successful privacy-redaction result.  It performs no logging, storage,
network, repository, or provider I/O.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from sejong_ai_api.db.models import FallbackReason, Intent
from sejong_ai_api.llm.classifier_contracts import (
    ClassifierDecision,
    ClassifierRoute,
    PendingSlot,
)
from sejong_ai_api.privacy.redaction import RedactionResult

_SUPPORTED_INTENTS = frozenset(
    {
        Intent.MOVE_IN_RESIDENT_REGISTRATION,
        Intent.CERTIFICATE_ISSUANCE,
        Intent.BULKY_WASTE,
        Intent.LOCAL_TAX_GENERAL,
    }
)
_TOKEN_WORD_PATTERN = re.compile(r"[0-9a-z가-힣]+")

_INTENT_TERMS: dict[Intent, tuple[tuple[str, int], ...]] = {
    Intent.MOVE_IN_RESIDENT_REGISTRATION: (
        ("전입신고", 4),
        ("주소이전", 4),
        ("주소변경", 4),
        ("이사신고", 4),
        ("통보서비스", 4),
        ("전입", 3),
        ("세대주변경", 3),
    ),
    Intent.CERTIFICATE_ISSUANCE: (
        ("주민등록등본", 4),
        ("주민등록초본", 4),
        ("주민등록표", 4),
        ("무인민원발급", 4),
        ("무인발급기", 4),
        ("인감증명", 4),
        ("등본", 3),
        ("초본", 3),
        ("주민등록열람", 3),
    ),
    Intent.BULKY_WASTE: (
        ("대형폐기물", 4),
        ("배출신고", 4),
        ("폐기물", 3),
        ("침대프레임", 3),
        ("침대", 3),
        ("프레임", 3),
        ("매트리스", 3),
        ("가구배출", 3),
        ("폐기물스티커", 3),
        ("소파배출", 3),
    ),
    Intent.LOCAL_TAX_GENERAL: (
        ("지방세", 4),
        ("자동차세", 4),
        ("재산세", 4),
        ("주민세", 4),
        ("취득세", 4),
        ("납세증명", 4),
        ("전자납부번호", 4),
        ("과세증명서", 4),
        ("납부확인서", 4),
        ("체납액", 3),
        ("세금", 2),
    ),
}

_NON_CIVIC_TERMS = (
    "날씨",
    "맛집",
)
_UNSUPPORTED_ADMIN_TERMS = (
    "버스",
    "교통",
    "병원",
    "여권",
    "운전면허",
    "출생신고",
    "복지급여",
    "졸업증명서",
    "재학증명서",
    "성적증명서",
    "가족관계증명서",
    "건강진단서",
    "진단서",
    "반려동물",
    "동물등록",
)
_FIRST_PERSON_TERMS = frozenset({"내", "내가", "나의", "저의", "제", "제가", "본인"})
_PERSONAL_LOOKUP_TERMS = (
    "체납액",
    "납부내역",
    "접수번호",
    "신청상태",
    "처리상태",
    "발급상태",
    "신고상태",
    "민원번호",
)
_LOOKUP_ACTIONS = ("조회", "알려", "확인", "보여", "됐", "완료")
_LEGAL_TERMS = (
    "법적으로",
    "법률판단",
    "위법",
    "불법",
    "처벌",
    "유죄",
    "소송",
    "법적책임",
    "합법",
    "벌금",
    "과태료",
)
_QUALIFICATION_TERMS = (
    "대상인지",
    "대상여부",
    "수급대상",
    "자격이되는지",
    "자격여부",
)
_JUDGMENT_ACTIONS = ("판단", "결정", "해당하는지")


@dataclass(frozen=True, slots=True, init=False)
class SafeQuestion:
    """Masked text proven safe by the privacy core."""

    _text: str

    def __init__(self, redaction: RedactionResult) -> None:
        if type(redaction) is not RedactionResult:
            raise TypeError("SAFE_QUESTION_REQUIRED")
        if (
            redaction.masked_text is None
            or redaction.safe_for_failure_storage is not True
            or redaction.safe_for_synthetic_provider is not True
            or redaction.unresolved_reason is not None
        ):
            raise ValueError("SAFE_QUESTION_REQUIRED")
        object.__setattr__(self, "_text", redaction.masked_text)

    @property
    def text(self) -> str:
        return self._text


@dataclass(frozen=True, slots=True)
class ClassificationOutcome:
    intent: Intent
    followup_required: bool
    fallback_reason: FallbackReason | None
    route: ClassifierRoute | None = None
    topic_id: str | None = None
    coverage_id: str | None = None
    pending_slot: PendingSlot | None = None
    needs_provider: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.intent) is not Intent
            or type(self.followup_required) is not bool
            or type(self.needs_provider) is not bool
        ):
            raise ValueError("CLASSIFICATION_OUTCOME_INVALID")
        if self.fallback_reason is not None and type(self.fallback_reason) is not FallbackReason:
            raise ValueError("CLASSIFICATION_OUTCOME_INVALID")
        if self.route is not None and type(self.route) is not ClassifierRoute:
            raise ValueError("CLASSIFICATION_OUTCOME_INVALID")
        if self.topic_id is not None and type(self.topic_id) is not str:
            raise ValueError("CLASSIFICATION_OUTCOME_INVALID")
        if self.coverage_id is not None and type(self.coverage_id) is not str:
            raise ValueError("CLASSIFICATION_OUTCOME_INVALID")
        if self.pending_slot is not None and type(self.pending_slot) is not PendingSlot:
            raise ValueError("CLASSIFICATION_OUTCOME_INVALID")
        if (self.topic_id is None) is not (self.coverage_id is None):
            raise ValueError("CLASSIFICATION_OUTCOME_INVALID")

        if self.needs_provider:
            if (
                self.route is not None
                or self.intent is not Intent.UNKNOWN
                or not self.followup_required
                or self.fallback_reason is not None
                or self.topic_id is not None
                or self.coverage_id is not None
                or self.pending_slot is not None
            ):
                raise ValueError("CLASSIFICATION_OUTCOME_INVALID")
            return

        if self.route is None:
            if (
                self.followup_required
                or self.intent is not Intent.UNKNOWN
                or self.fallback_reason
                not in {
                    FallbackReason.PERSONAL_LOOKUP,
                    FallbackReason.LEGAL_JUDGMENT,
                }
                or self.topic_id is not None
                or self.coverage_id is not None
                or self.pending_slot is not None
            ):
                raise ValueError("CLASSIFICATION_OUTCOME_INVALID")
            return

        if self.route in {ClassifierRoute.NON_CIVIC, ClassifierRoute.CIVIC_SCOPE_GAP}:
            if (
                self.intent is not Intent.OUT_OF_SCOPE
                or self.followup_required
                or self.fallback_reason is not FallbackReason.OUT_OF_SCOPE
                or self.topic_id is not None
                or self.coverage_id is not None
                or self.pending_slot is not None
            ):
                raise ValueError("CLASSIFICATION_OUTCOME_INVALID")
            return

        if self.route is ClassifierRoute.SUPPORTED:
            if (
                self.followup_required
                or self.fallback_reason is not None
                or self.pending_slot is not None
            ):
                raise ValueError("CLASSIFICATION_OUTCOME_INVALID")
        elif self.route is ClassifierRoute.NEEDS_FOLLOWUP:
            if (
                not self.followup_required
                or self.fallback_reason is not None
                or self.topic_id is not None
                or self.coverage_id is not None
            ):
                raise ValueError("CLASSIFICATION_OUTCOME_INVALID")
        else:
            raise ValueError("CLASSIFICATION_OUTCOME_INVALID")

        if self.route is not ClassifierRoute.SUPPORTED or self.topic_id is not None:
            try:
                ClassifierDecision(
                    route=self.route,
                    intent=self.intent,
                    topic_id=self.topic_id,
                    coverage_id=self.coverage_id,
                    pending_slot=self.pending_slot,
                )
            except ValueError as error:
                raise ValueError("CLASSIFICATION_OUTCOME_INVALID") from error
        if self.intent not in _SUPPORTED_INTENTS:
            raise ValueError("CLASSIFICATION_OUTCOME_INVALID")


def classify_question(question: SafeQuestion) -> ClassificationOutcome:
    """Classify a privacy-safe question without any external side effects."""

    if type(question) is not SafeQuestion:
        raise TypeError("SAFE_QUESTION_REQUIRED")
    compact = _compact(question.text)

    if _is_personal_lookup(question.text, compact):
        return ClassificationOutcome(
            Intent.UNKNOWN,
            False,
            FallbackReason.PERSONAL_LOOKUP,
        )
    if _is_legal_judgment(compact):
        return ClassificationOutcome(Intent.UNKNOWN, False, FallbackReason.LEGAL_JUDGMENT)

    scores = {
        intent: max((weight for term, weight in terms if term in compact), default=0)
        for intent, terms in _INTENT_TERMS.items()
    }
    highest_score = max(scores.values())
    if highest_score == 0 and any(term in compact for term in _NON_CIVIC_TERMS):
        return ClassificationOutcome(
            Intent.OUT_OF_SCOPE,
            followup_required=False,
            fallback_reason=FallbackReason.OUT_OF_SCOPE,
            route=ClassifierRoute.NON_CIVIC,
        )
    best_intents = tuple(
        intent for intent, score in scores.items() if score == highest_score and score
    )
    if len(best_intents) == 1:
        intent = best_intents[0]
        return ClassificationOutcome(
            intent,
            False,
            None,
            route=ClassifierRoute.SUPPORTED,
        )

    if (
        highest_score == 0
        and "증명서" in compact
        and not any(term in compact for term in _UNSUPPORTED_ADMIN_TERMS)
    ):
        return ClassificationOutcome(
            Intent.CERTIFICATE_ISSUANCE,
            followup_required=True,
            fallback_reason=None,
            route=ClassifierRoute.NEEDS_FOLLOWUP,
            pending_slot=PendingSlot.CERTIFICATE_KIND,
        )

    return ClassificationOutcome(
        Intent.UNKNOWN,
        followup_required=True,
        fallback_reason=None,
        needs_provider=True,
    )


def _compact(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^0-9a-z가-힣]", "", normalized)


def _is_personal_lookup(value: str, compact: str) -> bool:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    words = _TOKEN_WORD_PATTERN.findall(normalized)
    has_subject = any(word in _FIRST_PERSON_TERMS for word in words)
    has_subject = has_subject or any(
        word.startswith(("내자동차세", "내재산세", "내주민세", "제자동차세", "제재산세"))
        for word in words
    )
    has_personal_target = any(term in compact for term in _PERSONAL_LOOKUP_TERMS)
    has_lookup_action = any(term in compact for term in _LOOKUP_ACTIONS)
    intrinsically_personal = any(
        term in compact for term in _PERSONAL_LOOKUP_TERMS if term not in {"체납액", "납부내역"}
    )
    return (has_subject and has_personal_target) or (intrinsically_personal and has_lookup_action)


def _is_legal_judgment(compact: str) -> bool:
    if any(term in compact for term in _LEGAL_TERMS):
        return True
    return any(term in compact for term in _QUALIFICATION_TERMS) and any(
        action in compact for action in _JUDGMENT_ACTIONS
    )


__all__ = ["ClassificationOutcome", "SafeQuestion", "classify_question"]
