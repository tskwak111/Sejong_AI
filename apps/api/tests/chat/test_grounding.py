from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.grounding import evaluate_grounding
from sejong_ai_api.chat.retrieval import (
    GroundingEvidence,
    GroundingEvidenceKind,
    TopicSelection,
    validate_semantic_selection,
)
from sejong_ai_api.chat.topic_catalog import RuntimeTopic, TopicCatalog, TopicCoverage
from sejong_ai_api.db.models import Intent, KnowledgeRecord
from sejong_ai_api.llm.classifier_contracts import ClassifierDecision, ClassifierRoute
from sejong_ai_api.privacy.redaction import redact_question


def safe_question(text: str) -> SafeQuestion:
    return SafeQuestion(redact_question(text))


def knowledge(**overrides: object) -> KnowledgeRecord:
    values: dict[str, object] = {
        "public_id": "KB-WASTE-01",
        "category": Intent.BULKY_WASTE,
        "service_name": "대형폐기물 침대 프레임 배출",
        "answer_summary": "신고 후 지정 장소에 배출합니다.",
        "procedure_steps": ("수수료 확인", "배출 신고"),
        "required_documents": (),
        "processing_time": "신고 즉시",
        "fee": "공식 품목표에서 확인",
        "department": "자원순환과",
        "source_title": "세종특별자치시 대형폐기물 안내",
        "source_url": "https://example.invalid/waste",
        "last_verified_at": date(2026, 7, 18),
        "caution": "수거일 전날 배출",
        "question_examples": ("침대 프레임은 어떻게 버리나요?",),
    }
    values.update(overrides)
    return KnowledgeRecord(**values)  # type: ignore[arg-type]


def runtime_topic(
    record: KnowledgeRecord,
    *,
    coverage_id: str = "GENERAL_BULKY_DISPOSAL",
) -> RuntimeTopic:
    return RuntimeTopic(
        record=record,
        coverage=TopicCoverage(
            topic_id=record.public_id,
            intent=record.category,
            coverage_id=coverage_id,
            coverage_label="테스트 범위",
        ),
    )


def catalog(*topics: RuntimeTopic) -> TopicCatalog:
    return TopicCatalog(tuple(sorted(topics, key=lambda item: item.record.public_id)))


def selection(
    topic: RuntimeTopic,
    kind: GroundingEvidenceKind = GroundingEvidenceKind.VALIDATED_SEMANTIC_COVERAGE,
    *,
    topic_id: str | None = None,
    coverage_id: str | None = None,
    matched_tokens: tuple[str, ...] = (),
) -> TopicSelection:
    return TopicSelection(
        topic=topic,
        evidence=GroundingEvidence(
            kind=kind,
            topic_id=topic.record.public_id if topic_id is None else topic_id,
            coverage_id=(
                topic.coverage.coverage_id
                if coverage_id is None
                and kind
                in {
                    GroundingEvidenceKind.VALIDATED_SEMANTIC_COVERAGE,
                    GroundingEvidenceKind.VALIDATED_CONTEXT_FACET,
                }
                else coverage_id
            ),
            matched_tokens=matched_tokens,
        ),
    )


def semantic_decision(
    topic: RuntimeTopic,
    *,
    intent: Intent | None = None,
    coverage_id: str | None = None,
) -> ClassifierDecision:
    return ClassifierDecision(
        route=ClassifierRoute.SUPPORTED,
        intent=topic.record.category if intent is None else intent,
        topic_id=topic.record.public_id,
        coverage_id=topic.coverage.coverage_id if coverage_id is None else coverage_id,
        pending_slot=None,
    )


def test_semantic_selection_requires_current_catalog_topic_coverage_and_intent() -> None:
    topic = runtime_topic(knowledge())
    current_catalog = catalog(topic)

    selected = validate_semantic_selection(semantic_decision(topic), current_catalog)

    assert selected is not None
    assert selected.topic is topic
    assert selected.evidence.kind is GroundingEvidenceKind.VALIDATED_SEMANTIC_COVERAGE
    assert selected.evidence.coverage_id == "GENERAL_BULKY_DISPOSAL"


@pytest.mark.parametrize(
    "decision,catalog_topics",
    [
        pytest.param(
            lambda topic: semantic_decision(topic, coverage_id="WRONG_COVERAGE"),
            lambda topic: (topic,),
            id="coverage-mismatch",
        ),
        pytest.param(
            lambda topic: semantic_decision(topic, intent=Intent.LOCAL_TAX_GENERAL),
            lambda topic: (topic,),
            id="intent-mismatch",
        ),
        pytest.param(
            lambda topic: semantic_decision(topic),
            lambda _topic: (),
            id="inactive-topic-absent",
        ),
    ],
)
def test_semantic_selection_rejects_invalid_current_catalog_membership(
    decision: object,
    catalog_topics: object,
) -> None:
    topic = runtime_topic(knowledge())

    assert (
        validate_semantic_selection(
            decision(topic),  # type: ignore[operator]
            catalog(*catalog_topics(topic)),  # type: ignore[operator]
        )
        is None
    )


def test_grounding_accepts_only_matching_typed_semantic_evidence() -> None:
    record = knowledge(processing_time="신고 즉시", fee="10,000원")
    topic = runtime_topic(record)

    grounded = evaluate_grounding(
        safe_question("새 집 이사 뒤 큰 가구 처리 절차가 궁금해요."),
        Intent.BULKY_WASTE,
        selection(topic),
    )

    assert grounded.is_grounded is True
    assert grounded.record is record
    assert grounded.processing_time == "신고 즉시"
    assert grounded.fee == "10,000원"
    assert grounded.source_title == record.source_title
    with pytest.raises(FrozenInstanceError):
        grounded.record = knowledge(fee="임의 생성 금액")  # type: ignore[misc]


def test_grounding_rejects_evidence_for_a_different_topic_or_coverage() -> None:
    topic = runtime_topic(knowledge())

    wrong_topic = evaluate_grounding(
        safe_question("침대 프레임 배출 방법"),
        Intent.BULKY_WASTE,
        selection(topic, topic_id="KB-WASTE-OTHER"),
    )
    wrong_coverage = evaluate_grounding(
        safe_question("침대 프레임 배출 방법"),
        Intent.BULKY_WASTE,
        selection(topic, coverage_id="WRONG_COVERAGE"),
    )

    assert wrong_topic.is_grounded is False
    assert wrong_coverage.is_grounded is False


def test_context_facet_evidence_can_ground_only_the_current_record() -> None:
    record = knowledge(service_name="대형폐기물 배출 안내")
    topic = runtime_topic(record)

    decision = evaluate_grounding(
        safe_question("비용은요?"),
        Intent.BULKY_WASTE,
        selection(topic, GroundingEvidenceKind.VALIDATED_CONTEXT_FACET),
    )

    assert decision.is_grounded is True
    assert decision.record is record


@pytest.mark.parametrize(
    ("question", "intent", "record"),
    [
        (
            "매트리스 토퍼만 버리면 수수료가 얼마예요?",
            Intent.BULKY_WASTE,
            knowledge(
                service_name="매트리스 배출 수수료",
                question_examples=("매트리스 수수료가 있나요?",),
            ),
        ),
        (
            "전입신고하면 모든 우편물 주소도 자동으로 바뀌나요?",
            Intent.MOVE_IN_RESIDENT_REGISTRATION,
            knowledge(
                public_id="KB-MOVE-01",
                category=Intent.MOVE_IN_RESIDENT_REGISTRATION,
                service_name="주민등록 관련 주소변경 통보서비스",
                question_examples=("주소 변경 통보서비스는 어떻게 신청하나요?",),
            ),
        ),
    ],
)
def test_grounding_preserves_record_specific_negative_detail_guards(
    question: str,
    intent: Intent,
    record: KnowledgeRecord,
) -> None:
    topic = runtime_topic(record)

    decision = evaluate_grounding(safe_question(question), intent, selection(topic))

    assert decision.is_grounded is False


def test_grounding_accepts_newly_approved_record_specific_detail() -> None:
    record = knowledge(
        service_name="매트리스 토퍼 배출 수수료",
        question_examples=("매트리스 토퍼 수수료가 얼마예요?",),
    )

    decision = evaluate_grounding(
        safe_question("매트리스 토퍼만 버리면 수수료가 얼마예요?"),
        Intent.BULKY_WASTE,
        selection(runtime_topic(record)),
    )

    assert decision.is_grounded is True


def test_grounding_rejects_raw_question_or_untyped_selection() -> None:
    topic = runtime_topic(knowledge())

    with pytest.raises(TypeError, match="^SAFE_QUESTION_REQUIRED$"):
        evaluate_grounding(
            "raw citizen text",  # type: ignore[arg-type]
            Intent.BULKY_WASTE,
            selection(topic),
        )
    with pytest.raises(TypeError, match="^TOPIC_SELECTION_REQUIRED$"):
        evaluate_grounding(
            safe_question("침대 프레임 배출 방법"),
            Intent.BULKY_WASTE,
            topic.record,  # type: ignore[arg-type]
        )
