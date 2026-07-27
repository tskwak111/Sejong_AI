from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.retrieval import (
    GroundingEvidenceKind,
    rank_active_knowledge,
    select_deterministic_topic,
)
from sejong_ai_api.chat.topic_catalog import RuntimeTopic, TopicCatalog, TopicCoverage
from sejong_ai_api.db.models import Intent, KnowledgeRecord
from sejong_ai_api.privacy.redaction import redact_question


def safe_question(text: str) -> SafeQuestion:
    return SafeQuestion(redact_question(text))


def knowledge(**overrides: object) -> KnowledgeRecord:
    values: dict[str, object] = {
        "public_id": "KB-WASTE-01",
        "category": Intent.BULKY_WASTE,
        "service_name": "대형폐기물 배출 신고",
        "answer_summary": "대형폐기물 배출 절차를 안내합니다.",
        "procedure_steps": ("품목과 수수료 확인", "배출 신고"),
        "required_documents": (),
        "processing_time": "신고 후 배출",
        "fee": None,
        "department": "자원순환과",
        "source_title": "세종특별자치시 대형폐기물 안내",
        "source_url": "https://example.invalid/waste",
        "last_verified_at": date(2026, 7, 18),
        "caution": None,
        "question_examples": ("대형폐기물은 어떻게 버리나요?",),
    }
    values.update(overrides)
    return KnowledgeRecord(**values)  # type: ignore[arg-type]


def catalog(*records: KnowledgeRecord) -> TopicCatalog:
    return TopicCatalog(
        tuple(
            RuntimeTopic(
                record=record,
                coverage=TopicCoverage(
                    topic_id=record.public_id,
                    intent=record.category,
                    coverage_id=f"COVERAGE_{index:02d}",
                    coverage_label=f"테스트 범위 {index}",
                ),
            )
            for index, record in enumerate(sorted(records, key=lambda item: item.public_id), 1)
        )
    )


def test_normalized_exact_question_match_has_highest_priority() -> None:
    exact = knowledge(
        public_id="KB-WASTE-02",
        service_name="가구 배출",
        question_examples=("침대 프레임 버리는 방법?",),
    )
    broad = knowledge(
        public_id="KB-WASTE-01",
        service_name="침대 프레임 버리는 방법과 수수료",
        question_examples=("침대 처리",),
    )

    ranked = rank_active_knowledge(
        safe_question("침대 프레임 버리는 방법"),
        Intent.BULKY_WASTE,
        (broad, exact),
    )

    assert tuple(item.record.public_id for item in ranked) == (
        "KB-WASTE-02",
        "KB-WASTE-01",
    )
    assert ranked[0].exact_question_match is True


def test_service_then_procedure_document_overlap_and_public_id_break_ties() -> None:
    question = safe_question("전입신고 신분증 신청서")
    less_coverage = knowledge(
        public_id="KB-MOVE-03",
        category=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        service_name="전입신고",
        procedure_steps=("방문 신청",),
        required_documents=(),
        question_examples=("이사 신고",),
    )
    tied_b = knowledge(
        public_id="KB-MOVE-02",
        category=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        service_name="전입신고",
        procedure_steps=("신청서 제출",),
        required_documents=("신분증",),
        question_examples=("이사 신고",),
    )
    tied_a = knowledge(
        public_id="KB-MOVE-01",
        category=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        service_name="전입신고",
        procedure_steps=("신청서 제출",),
        required_documents=("신분증",),
        question_examples=("이사 신고",),
    )

    ranked = rank_active_knowledge(
        question,
        Intent.MOVE_IN_RESIDENT_REGISTRATION,
        (less_coverage, tied_b, tied_a),
    )

    assert tuple(item.record.public_id for item in ranked) == (
        "KB-MOVE-01",
        "KB-MOVE-02",
        "KB-MOVE-03",
    )


@dataclass(frozen=True)
class UntrustedKnowledgeProjection:
    status: str
    data_origin: str
    record: KnowledgeRecord


def test_only_active_official_projection_records_for_the_requested_intent_are_ranked() -> None:
    active = knowledge(public_id="KB-WASTE-ACTIVE")
    other_intent = knowledge(
        public_id="KB-TAX-ACTIVE",
        category=Intent.LOCAL_TAX_GENERAL,
    )
    draft = UntrustedKnowledgeProjection(
        "DRAFT",
        "OFFICIAL",
        knowledge(public_id="KB-WASTE-DRAFT"),
    )
    candidate = UntrustedKnowledgeProjection(
        "CANDIDATE",
        "OFFICIAL",
        knowledge(public_id="KB-WASTE-CANDIDATE"),
    )
    mock = UntrustedKnowledgeProjection(
        "ACTIVE",
        "MOCK",
        knowledge(public_id="KB-WASTE-MOCK"),
    )

    ranked = rank_active_knowledge(
        safe_question("대형폐기물 배출 신고"),
        Intent.BULKY_WASTE,
        (draft, candidate, mock, other_intent, active),  # type: ignore[arg-type]
    )

    assert tuple(item.record.public_id for item in ranked) == ("KB-WASTE-ACTIVE",)


def test_retriever_rejects_raw_question_text() -> None:
    with pytest.raises(TypeError, match="^SAFE_QUESTION_REQUIRED$"):
        rank_active_knowledge(
            "raw citizen text",  # type: ignore[arg-type]
            Intent.BULKY_WASTE,
            (),
        )


def test_deterministic_selector_prefers_an_exact_approved_example_in_current_catalog() -> None:
    exact = knowledge(
        public_id="KB-WASTE-EXACT",
        question_examples=("침대 프레임 버리는 방법?",),
    )
    lexical = knowledge(
        public_id="KB-WASTE-LEXICAL",
        service_name="침대 프레임 배출 신고",
        question_examples=("침대 배출 신고",),
    )

    selected = select_deterministic_topic(
        safe_question("침대 프레임 버리는 방법"),
        Intent.BULKY_WASTE,
        catalog(lexical, exact),
    )

    assert selected is not None
    assert selected.topic.record is exact
    assert selected.evidence.kind is GroundingEvidenceKind.EXACT_APPROVED_EXAMPLE


def test_deterministic_selector_returns_one_unique_strong_lexical_topic() -> None:
    move = knowledge(
        public_id="KB-MOVE-01",
        category=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        service_name="주소이전 전입신고",
        question_examples=("전입신고 방법",),
    )
    other = knowledge(
        public_id="KB-MOVE-02",
        category=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        service_name="주민등록 통보서비스",
        question_examples=("통보서비스 신청",),
    )

    selected = select_deterministic_topic(
        safe_question("주소이전 신고는 어디에서 하나요?"),
        Intent.MOVE_IN_RESIDENT_REGISTRATION,
        catalog(move, other),
    )

    assert selected is not None
    assert selected.topic.record is move
    assert selected.evidence.kind is GroundingEvidenceKind.UNIQUE_LEXICAL_MATCH
    assert "주소이전" in selected.evidence.matched_tokens


def test_deterministic_selector_rejects_tied_top_two_lexical_topics() -> None:
    first = knowledge(
        public_id="KB-MOVE-01",
        category=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        service_name="전입신고",
        procedure_steps=("신청서 제출",),
    )
    second = knowledge(
        public_id="KB-MOVE-02",
        category=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        service_name="전입신고",
        procedure_steps=("신청서 제출",),
    )

    assert (
        select_deterministic_topic(
            safe_question("전입신고 신청서"),
            Intent.MOVE_IN_RESIDENT_REGISTRATION,
            catalog(first, second),
        )
        is None
    )


def test_deterministic_selector_rejects_overlap_without_an_intent_anchor() -> None:
    record = knowledge(
        public_id="KB-MOVE-01",
        category=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        service_name="방문 신청서 제출",
        procedure_steps=("신청서 제출",),
    )

    assert (
        select_deterministic_topic(
            safe_question("신청서 제출 방법"),
            Intent.MOVE_IN_RESIDENT_REGISTRATION,
            catalog(record),
        )
        is None
    )


def test_deterministic_selector_never_selects_a_zero_score_record() -> None:
    waste = knowledge(
        public_id="KB-WASTE-01",
        service_name="대형폐기물 배출 신고",
        question_examples=("대형폐기물은 어떻게 버리나요?",),
    )

    assert (
        select_deterministic_topic(
            safe_question("못 쓰는 냉장고를 버릴 때 신고해야 하나요?"),
            Intent.BULKY_WASTE,
            catalog(waste),
        )
        is None
    )
