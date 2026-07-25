from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.retrieval import rank_active_knowledge
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
