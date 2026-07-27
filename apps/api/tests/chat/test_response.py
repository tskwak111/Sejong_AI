from datetime import date
from typing import Literal
from uuid import UUID

import pytest

from sejong_ai_api.chat.response import (
    build_fallback_response,
    build_followup_response,
    build_success_response,
)
from sejong_ai_api.contracts.chat import SuccessResponse
from sejong_ai_api.db.models import Intent, KnowledgeRecord, OfficeRecord, Region

REQUEST_ID = UUID("11111111-1111-4111-8111-111111111111")


def knowledge_record(**overrides: object) -> KnowledgeRecord:
    values: dict[str, object] = {
        "public_id": "KB-WASTE-01",
        "category": Intent.BULKY_WASTE,
        "service_name": "대형폐기물 배출신청 절차",
        "answer_summary": "신청 후 배출번호를 확인하고 지정한 장소에 내놓으세요.",
        "procedure_steps": ("품목을 선택하세요.", "배출번호를 표시하세요."),
        "required_documents": (),
        "processing_time": None,
        "fee": "품목별 수수료",
        "department": "자원순환과",
        "source_title": "세종특별자치시 대형폐기물 안내",
        "source_url": "https://example.invalid/official/waste",
        "last_verified_at": date(2026, 7, 20),
        "caution": None,
        "question_examples": ("대형폐기물은 어떻게 버려요?",),
    }
    values.update(overrides)
    return KnowledgeRecord(**values)  # type: ignore[arg-type]


def office_record() -> OfficeRecord:
    return OfficeRecord(
        public_id="OFFICE-AREUM",
        region=Region.AREUM_DONG,
        office_name="아름동 행정복지센터",
        address="세종특별자치시 보듬3로 114",
        phone="044-301-6300",
        opening_hours="평일 09:00~18:00",
        map_url="https://example.invalid/map/areum",
        department_label="민원창구",
        source_title="세종특별자치시 아름동 안내",
        source_url="https://example.invalid/office/areum",
        last_verified_at=date(2026, 7, 20),
    )


def test_success_uses_only_the_selected_kb_and_office_metadata() -> None:
    record = knowledge_record()
    office = office_record()

    response = build_success_response(
        request_id=REQUEST_ID,
        record=record,
        office=office,
        confidence=0.92,
        context_token="signed-token",
    )

    assert response.answer_status == "SUCCESS"
    assert response.answer_mode == "TEMPLATE"
    assert response.intent == record.category.value
    assert response.summary == record.answer_summary
    assert response.procedure_steps == list(record.procedure_steps)
    assert response.required_documents == []
    assert response.processing_time is None
    assert response.fee == record.fee
    assert response.department == record.department
    assert len(response.sources) == 1
    assert response.sources[0].source_id == record.public_id
    assert response.sources[0].title == record.source_title
    assert str(response.sources[0].url) == record.source_url
    assert response.sources[0].last_verified_at == record.last_verified_at
    assert response.sources[0].used_fields == [
        "answer_summary",
        "procedure_steps",
        "fee",
        "department",
    ]
    assert response.fallback is None
    assert response.context_token == "signed-token"
    dumped_office = response.model_dump(mode="json")["office"]
    assert dumped_office == {
        "id": "OFFICE-AREUM",
        "region": "아름동",
        "office_name": "아름동 행정복지센터",
        "address": "세종특별자치시 보듬3로 114",
        "phone": "044-301-6300",
        "opening_hours": "평일 09:00~18:00",
        "map_url": "https://example.invalid/map/areum",
        "source_title": "세종특별자치시 아름동 안내",
        "source_url": "https://example.invalid/office/areum",
        "last_verified_at": "2026-07-20",
    }


def test_success_answer_mode_accepts_only_the_approved_modes() -> None:
    response = build_success_response(
        request_id=REQUEST_ID,
        record=knowledge_record(),
        office=None,
        confidence=0.99,
        context_token=None,
    )

    assert (
        SuccessResponse.model_validate(
            {**response.model_dump(), "answer_mode": "GENERATED"}
        ).answer_mode
        == "GENERATED"
    )


def test_success_omits_unavailable_optional_high_risk_fields() -> None:
    response = build_success_response(
        request_id=REQUEST_ID,
        record=knowledge_record(processing_time=None, fee=None),
        office=None,
        confidence=0.8,
        context_token="signed-token",
    )

    assert response.processing_time is None
    assert response.fee is None
    assert response.office is None
    assert "processing_time" not in response.sources[0].used_fields
    assert "fee" not in response.sources[0].used_fields


def test_followup_is_value_free_and_requires_server_options() -> None:
    response = build_followup_response(
        request_id=REQUEST_ID,
        intent=Intent.UNKNOWN,
        confidence=None,
        option_ids=("intent.move-in", "intent.certificate"),
        context_token="signed-followup",
    )

    assert response.answer_status == "FOLLOWUP"
    assert response.intent == "UNKNOWN"
    assert response.summary is None
    assert response.sources == []
    assert response.followup_options == ["전입·주민등록", "증명서 발급"]
    assert response.context_token == "signed-followup"


@pytest.mark.parametrize(
    ("reason", "intent", "candidate_eligible"),
    [
        ("INSUFFICIENT_GROUNDING", Intent.BULKY_WASTE, True),
        ("PERSONAL_LOOKUP", Intent.UNKNOWN, False),
        ("LEGAL_JUDGMENT", Intent.UNKNOWN, False),
        ("CIVIC_SCOPE_GAP", Intent.OUT_OF_SCOPE, False),
        ("OUT_OF_SCOPE", Intent.OUT_OF_SCOPE, False),
        ("PRIVACY_UNRESOLVED", Intent.UNKNOWN, False),
    ],
)
def test_fallback_matrix_is_closed_and_never_returns_context_or_sources(
    reason: Literal[
        "INSUFFICIENT_GROUNDING",
        "PERSONAL_LOOKUP",
        "LEGAL_JUDGMENT",
        "CIVIC_SCOPE_GAP",
        "OUT_OF_SCOPE",
        "PRIVACY_UNRESOLVED",
    ],
    intent: Intent,
    candidate_eligible: bool,
) -> None:
    response = build_fallback_response(
        request_id=REQUEST_ID,
        intent=intent,
        reason=reason,
        office=None,
    )

    assert response.answer_status == "FALLBACK"
    assert response.intent == intent.value
    assert response.confidence is None
    assert response.sources == []
    assert response.context_token is None
    assert response.fallback.reason == reason
    assert response.fallback.candidate_eligible is candidate_eligible
    assert response.fallback.office is None
    assert response.fallback.title
    assert response.fallback.message
    assert response.fallback.next_actions
    if reason == "INSUFFICIENT_GROUNDING":
        assert (
            response.fallback.message
            == "지원 분야이지만 현재 승인된 공식 자료에서 직접 답할 근거를 찾지 못했어요."
        )


def test_certificate_followup_uses_exact_five_server_owned_options() -> None:
    response = build_followup_response(
        request_id=REQUEST_ID,
        intent=Intent.CERTIFICATE_ISSUANCE,
        confidence=None,
        option_ids=(
            "certificate.resident-copy",
            "certificate.resident-abstract",
            "certificate.copy-vs-abstract",
            "certificate.resident-register-inspection",
            "certificate.unmanned-kiosk",
        ),
        context_token="signed-certificate-followup",
    )

    assert response.followup_options == [
        "주민등록등본 발급",
        "주민등록초본 발급",
        "등본과 초본의 차이",
        "주민등록표 열람",
        "무인민원발급기 이용",
    ]


def test_response_builders_reject_unknown_server_values() -> None:
    with pytest.raises(ValueError, match="^FOLLOWUP_OPTION_INVALID$"):
        build_followup_response(
            request_id=REQUEST_ID,
            intent=Intent.UNKNOWN,
            confidence=None,
            option_ids=("citizen-controlled-value",),  # type: ignore[arg-type]
            context_token=None,
        )

    with pytest.raises(ValueError, match="^FALLBACK_REASON_INVALID$"):
        build_fallback_response(
            request_id=REQUEST_ID,
            intent=Intent.UNKNOWN,
            reason="UNTRACKED_REASON",  # type: ignore[arg-type]
            office=None,
        )
