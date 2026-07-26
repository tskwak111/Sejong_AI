from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.grounding import evaluate_grounding
from sejong_ai_api.db.models import Intent, KnowledgeRecord
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


def test_grounding_requires_matching_intent_and_meaningful_token_overlap() -> None:
    record = knowledge()

    grounded = evaluate_grounding(
        safe_question("침대 프레임 배출 수수료를 알려주세요."),
        Intent.BULKY_WASTE,
        record,
    )

    assert grounded.is_grounded is True
    assert grounded.record is record
    assert "침대" in grounded.matched_tokens
    assert "프레임" in grounded.matched_tokens


def test_grounding_rejects_wrong_intent_or_zero_semantic_overlap() -> None:
    record = knowledge()

    wrong_intent = evaluate_grounding(
        safe_question("침대 프레임 배출 방법"),
        Intent.LOCAL_TAX_GENERAL,
        record,
    )
    unrelated = evaluate_grounding(
        safe_question("자동차세 납부 방법"),
        Intent.BULKY_WASTE,
        record,
    )

    assert wrong_intent.is_grounded is False
    assert wrong_intent.record is None
    assert unrelated.is_grounded is False
    assert unrelated.record is None


def test_grounding_matches_approved_terms_inside_compound_korean_tokens() -> None:
    decision = evaluate_grounding(
        safe_question("침대프레임 버려요."),
        Intent.BULKY_WASTE,
        knowledge(),
    )

    assert decision.is_grounded is True
    assert {"침대", "프레임"}.issubset(decision.matched_tokens)


def test_exact_approved_question_example_can_ground_without_keyword_anchor() -> None:
    question = "이 민원 신청 방법 알려줘"
    record = knowledge(question_examples=(question,))

    exact = evaluate_grounding(
        safe_question(question),
        Intent.BULKY_WASTE,
        record,
    )
    near_but_unapproved = evaluate_grounding(
        safe_question("이 민원 접수 방법 알려줘"),
        Intent.BULKY_WASTE,
        record,
    )

    assert exact.is_grounded is True
    assert near_but_unapproved.is_grounded is False


def test_high_risk_and_source_facts_are_read_only_views_of_the_kb_record() -> None:
    record = knowledge(
        processing_time="신고 즉시",
        fee="10,000원",
        caution="공식 배출 기준 확인",
    )

    decision = evaluate_grounding(
        safe_question("침대 프레임 수수료"),
        Intent.BULKY_WASTE,
        record,
    )

    assert decision.processing_time == record.processing_time
    assert decision.fee == record.fee
    assert decision.caution == record.caution
    assert decision.source_title == record.source_title
    assert decision.source_url == record.source_url
    assert decision.last_verified_at == record.last_verified_at
    with pytest.raises(FrozenInstanceError):
        decision.record = knowledge(fee="임의 생성 금액")  # type: ignore[misc]


def test_missing_high_risk_kb_fields_remain_missing() -> None:
    record = knowledge(processing_time=None, fee=None, caution=None)

    decision = evaluate_grounding(
        safe_question("침대 프레임 배출 방법"),
        Intent.BULKY_WASTE,
        record,
    )

    assert decision.is_grounded is True
    assert decision.processing_time is None
    assert decision.fee is None
    assert decision.caution is None


def test_grounding_rejects_raw_question_text() -> None:
    with pytest.raises(TypeError, match="^SAFE_QUESTION_REQUIRED$"):
        evaluate_grounding(
            "raw citizen text",  # type: ignore[arg-type]
            Intent.BULKY_WASTE,
            knowledge(),
        )


def test_generic_issue_word_cannot_ground_an_unsupported_certificate() -> None:
    record = knowledge(
        category=Intent.CERTIFICATE_ISSUANCE,
        service_name="주민등록등본 발급 방법",
        question_examples=("등본을 어떻게 발급하나요?",),
    )

    decision = evaluate_grounding(
        safe_question("경력증명서 발급 방법"),
        Intent.CERTIFICATE_ISSUANCE,
        record,
    )

    assert decision.is_grounded is False


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
                category=Intent.MOVE_IN_RESIDENT_REGISTRATION,
                service_name="주민등록 관련 주소변경 통보서비스",
                question_examples=("주소 변경 통보서비스는 어떻게 신청하나요?",),
            ),
        ),
    ],
)
def test_grounding_rejects_unapproved_record_specific_detail(
    question: str,
    intent: Intent,
    record: KnowledgeRecord,
) -> None:
    decision = evaluate_grounding(safe_question(question), intent, record)

    assert decision.is_grounded is False


def test_grounding_accepts_newly_approved_detail_when_record_contains_it() -> None:
    record = knowledge(
        service_name="매트리스 토퍼 배출 수수료",
        question_examples=("매트리스 토퍼 수수료가 얼마예요?",),
    )

    decision = evaluate_grounding(
        safe_question("매트리스 토퍼만 버리면 수수료가 얼마예요?"),
        Intent.BULKY_WASTE,
        record,
    )

    assert decision.is_grounded is True


def test_validated_context_can_reuse_current_active_topic_for_bounded_detail() -> None:
    record = knowledge(
        service_name="대형폐기물 배출 안내",
        question_examples=("대형폐기물은 어떻게 버리나요?",),
    )

    decision = evaluate_grounding(
        safe_question("비용은요?"),
        Intent.BULKY_WASTE,
        record,
        allow_contextual_detail=True,
    )

    assert decision.is_grounded is True
    assert decision.record is record
