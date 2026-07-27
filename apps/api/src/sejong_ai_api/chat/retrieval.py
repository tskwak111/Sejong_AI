"""Deterministic lexical ranking over the ACTIVE/OFFICIAL DB projection."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.topic_catalog import RuntimeTopic, TopicCatalog
from sejong_ai_api.db.models import Intent, KnowledgeRecord
from sejong_ai_api.llm.classifier_contracts import (
    ClassifierDecision,
    ClassifierRoute,
)

_SUPPORTED_INTENTS = frozenset(
    {
        Intent.MOVE_IN_RESIDENT_REGISTRATION,
        Intent.CERTIFICATE_ISSUANCE,
        Intent.BULKY_WASTE,
        Intent.LOCAL_TAX_GENERAL,
    }
)
_TOKEN_PATTERN = re.compile(r"[0-9a-z가-힣]+")
_PARTICLE_SUFFIXES = (
    "은요",
    "는요",
    "에서는",
    "에게서",
    "으로는",
    "하고",
    "에서",
    "으로",
    "에게",
    "까지",
    "부터",
    "처럼",
    "보다",
    "라도",
    "이나",
    "는",
    "은",
    "이",
    "가",
    "을",
    "를",
    "에",
    "로",
    "와",
    "과",
    "도",
    "만",
)
_STOP_WORDS = frozenset(
    {
        "어떻게",
        "방법",
        "알려주세",
        "알려주세요",
        "알려줘",
        "궁금해요",
        "궁금합니다",
        "싶어요",
        "하나요",
        "해요",
        "문의",
        "민원",
    }
)
_APPROVED_SEMANTIC_TERMS = frozenset(
    {
        "전입신고",
        "주소변경",
        "주민등록",
        "주민등록표",
        "통보서비스",
        "등본",
        "초본",
        "증명서",
        "무인민원발급",
        "무인발급기",
        "발급",
        "대형폐기물",
        "폐기물",
        "침대",
        "프레임",
        "매트리스",
        "소파",
        "가구",
        "배출",
        "수수료",
        "지방세",
        "자동차세",
        "재산세",
        "주민세",
        "취득세",
        "체납",
        "납세증명",
        "납부",
        "전자납부번호",
        "과세증명서",
        "납부확인서",
        "신분증",
        "신청서",
    }
)
_INTENT_ANCHORS: dict[Intent, frozenset[str]] = {
    Intent.MOVE_IN_RESIDENT_REGISTRATION: frozenset(
        {"전입신고", "주소이전", "주소변경", "주민등록", "통보서비스"}
    ),
    Intent.CERTIFICATE_ISSUANCE: frozenset(
        {"주민등록", "주민등록표", "등본", "초본", "무인민원발급", "무인발급기"}
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


class GroundingEvidenceKind(str, Enum):  # noqa: UP042 - approved public enum shape
    EXACT_APPROVED_EXAMPLE = "EXACT_APPROVED_EXAMPLE"
    UNIQUE_LEXICAL_MATCH = "UNIQUE_LEXICAL_MATCH"
    VALIDATED_SEMANTIC_COVERAGE = "VALIDATED_SEMANTIC_COVERAGE"
    VALIDATED_CONTEXT_FACET = "VALIDATED_CONTEXT_FACET"


@dataclass(frozen=True, slots=True)
class GroundingEvidence:
    kind: GroundingEvidenceKind
    topic_id: str
    coverage_id: str | None
    matched_tokens: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.kind) is not GroundingEvidenceKind
            or type(self.topic_id) is not str
            or not self.topic_id
            or (
                self.coverage_id is not None
                and (type(self.coverage_id) is not str or not self.coverage_id)
            )
            or type(self.matched_tokens) is not tuple
            or any(type(token) is not str or not token for token in self.matched_tokens)
        ):
            raise ValueError("GROUNDING_EVIDENCE_INVALID")
        if self.kind in {
            GroundingEvidenceKind.VALIDATED_SEMANTIC_COVERAGE,
            GroundingEvidenceKind.VALIDATED_CONTEXT_FACET,
        }:
            if self.coverage_id is None:
                raise ValueError("GROUNDING_EVIDENCE_INVALID")
        elif self.coverage_id is not None:
            raise ValueError("GROUNDING_EVIDENCE_INVALID")


@dataclass(frozen=True, slots=True)
class TopicSelection:
    topic: RuntimeTopic
    evidence: GroundingEvidence

    def __post_init__(self) -> None:
        if type(self.topic) is not RuntimeTopic or type(self.evidence) is not GroundingEvidence:
            raise ValueError("TOPIC_SELECTION_INVALID")


@dataclass(frozen=True, slots=True)
class RankedKnowledge:
    """A ranked record from ``app_api.list_active_kb`` only."""

    record: KnowledgeRecord
    exact_question_match: bool
    service_or_example_overlap: int
    procedure_document_overlap: int

    def __post_init__(self) -> None:
        if type(self.record) is not KnowledgeRecord:
            raise ValueError("ACTIVE_KNOWLEDGE_REQUIRED")
        if type(self.exact_question_match) is not bool:
            raise ValueError("RANK_INVALID")
        if (
            type(self.service_or_example_overlap) is not int
            or self.service_or_example_overlap < 0
            or type(self.procedure_document_overlap) is not int
            or self.procedure_document_overlap < 0
        ):
            raise ValueError("RANK_INVALID")


def rank_active_knowledge(
    question: SafeQuestion,
    intent: Intent,
    records: Sequence[KnowledgeRecord],
) -> tuple[RankedKnowledge, ...]:
    """Rank already-filtered ACTIVE/OFFICIAL records for one supported intent.

    ``KnowledgeRecord`` is intentionally the value-free projection returned by
    ``SejongRepository.list_active_kb``.  Objects carrying draft/non-active
    state are not this projection and are ignored at this boundary.
    """

    if type(question) is not SafeQuestion:
        raise TypeError("SAFE_QUESTION_REQUIRED")
    if type(intent) is not Intent or intent not in _SUPPORTED_INTENTS:
        raise ValueError("SUPPORTED_INTENT_REQUIRED")
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise TypeError("ACTIVE_KNOWLEDGE_SEQUENCE_REQUIRED")

    query_exact = normalize_for_exact(question.text)
    query_tokens = meaningful_tokens(question.text)
    ranked: list[RankedKnowledge] = []
    for record in records:
        if type(record) is not KnowledgeRecord or record.category is not intent:
            continue
        exact = any(
            normalize_for_exact(example) == query_exact for example in record.question_examples
        )
        service_and_examples = meaningful_tokens(
            " ".join((record.service_name, *record.question_examples))
        )
        procedure_and_documents = meaningful_tokens(
            " ".join((*record.procedure_steps, *record.required_documents))
        )
        ranked.append(
            RankedKnowledge(
                record=record,
                exact_question_match=exact,
                service_or_example_overlap=len(query_tokens & service_and_examples),
                procedure_document_overlap=len(query_tokens & procedure_and_documents),
            )
        )

    return tuple(
        sorted(
            ranked,
            key=lambda item: (
                -int(item.exact_question_match),
                -item.service_or_example_overlap,
                -item.procedure_document_overlap,
                item.record.public_id,
            ),
        )
    )


def select_deterministic_topic(
    question: SafeQuestion,
    intent: Intent,
    catalog: TopicCatalog,
) -> TopicSelection | None:
    """Select only exact or uniquely anchored lexical evidence from this catalog."""

    if type(question) is not SafeQuestion:
        raise TypeError("SAFE_QUESTION_REQUIRED")
    if type(intent) is not Intent or intent not in _SUPPORTED_INTENTS:
        raise ValueError("SUPPORTED_INTENT_REQUIRED")
    if type(catalog) is not TopicCatalog:
        raise TypeError("TOPIC_CATALOG_REQUIRED")

    topics_by_id = {
        topic.record.public_id: topic
        for topic in catalog.topics
        if topic.record.category is intent
    }
    ranked = rank_active_knowledge(
        question,
        intent,
        tuple(topic.record for topic in topics_by_id.values()),
    )
    if not ranked:
        return None

    top = ranked[0]
    topic = topics_by_id.get(top.record.public_id)
    if topic is None:
        return None
    matched_tokens = _matched_service_or_example_tokens(question, top.record)
    if top.exact_question_match:
        return TopicSelection(
            topic=topic,
            evidence=GroundingEvidence(
                kind=GroundingEvidenceKind.EXACT_APPROVED_EXAMPLE,
                topic_id=topic.record.public_id,
                coverage_id=None,
                matched_tokens=matched_tokens,
            ),
        )

    top_score = (top.service_or_example_overlap, top.procedure_document_overlap)
    if (
        top_score == (0, 0)
        or top.service_or_example_overlap == 0
        or not (meaningful_tokens(question.text) & _INTENT_ANCHORS[intent])
    ):
        return None
    if len(ranked) > 1:
        second = ranked[1]
        second_score = (second.service_or_example_overlap, second.procedure_document_overlap)
        if top_score <= second_score:
            return None
    return TopicSelection(
        topic=topic,
        evidence=GroundingEvidence(
            kind=GroundingEvidenceKind.UNIQUE_LEXICAL_MATCH,
            topic_id=topic.record.public_id,
            coverage_id=None,
            matched_tokens=matched_tokens,
        ),
    )


def validate_semantic_selection(
    decision: ClassifierDecision,
    catalog: TopicCatalog,
) -> TopicSelection | None:
    """Accept only the current catalog's exact supported topic and coverage pair."""

    if type(decision) is not ClassifierDecision or type(catalog) is not TopicCatalog:
        return None
    if (
        decision.route is not ClassifierRoute.SUPPORTED
        or decision.intent is None
        or decision.topic_id is None
        or decision.coverage_id is None
    ):
        return None
    topic = catalog.find(decision.topic_id)
    if (
        topic is None
        or topic.record.category is not decision.intent
        or topic.coverage.intent is not decision.intent
        or topic.coverage.coverage_id != decision.coverage_id
    ):
        return None
    return TopicSelection(
        topic=topic,
        evidence=GroundingEvidence(
            kind=GroundingEvidenceKind.VALIDATED_SEMANTIC_COVERAGE,
            topic_id=decision.topic_id,
            coverage_id=decision.coverage_id,
        ),
    )


def _matched_service_or_example_tokens(
    question: SafeQuestion,
    record: KnowledgeRecord,
) -> tuple[str, ...]:
    service_or_examples = meaningful_tokens(
        " ".join((record.service_name, *record.question_examples))
    )
    return tuple(sorted(meaningful_tokens(question.text) & service_or_examples))


def normalize_for_exact(value: str) -> str:
    """Normalize whitespace and punctuation for exact example comparison."""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[^0-9a-z가-힣]", "", normalized)


def meaningful_tokens(value: str) -> frozenset[str]:
    """Return deterministic, bounded lexical tokens for Korean MVP matching."""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    tokens: set[str] = set()
    for raw_token in _TOKEN_PATTERN.findall(normalized):
        token = _strip_particle(raw_token)
        if len(token) < 2 or token in _STOP_WORDS:
            continue
        tokens.add(token)
        tokens.update(term for term in _APPROVED_SEMANTIC_TERMS if term in token)
    return frozenset(tokens)


def _strip_particle(token: str) -> str:
    for suffix in _PARTICLE_SUFFIXES:
        if token.endswith(suffix) and len(token) - len(suffix) >= 2:
            return token[: -len(suffix)]
    return token


__all__ = [
    "GroundingEvidence",
    "GroundingEvidenceKind",
    "RankedKnowledge",
    "TopicSelection",
    "meaningful_tokens",
    "normalize_for_exact",
    "rank_active_knowledge",
    "select_deterministic_topic",
    "validate_semantic_selection",
]
