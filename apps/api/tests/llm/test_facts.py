from __future__ import annotations

from datetime import date

import pytest

from sejong_ai_api.db.models import Intent, KnowledgeRecord
from sejong_ai_api.llm.chat_contracts import GeneratedChatDraft, GroundedChatRequest
from sejong_ai_api.llm.facts import build_grounded_chat_request, materialize_grounded_answer


def _record(
    *,
    processing_time: str | None = "즉시",
    fee: str | None = "수수료 3,000원",
) -> KnowledgeRecord:
    return KnowledgeRecord(
        public_id="KB-PRIVATE-ID-MUST-NOT-LEAK",
        category=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        service_name="전입신고",
        answer_summary="전입신고는 전입한 날부터 14일 이내에 신고합니다.",
        procedure_steps=("정부24 또는 주민센터에서 신고합니다.", "신분증을 준비합니다."),
        required_documents=("신분증",),
        processing_time=processing_time,
        fee=fee,
        department="주민등록 담당 부서",
        source_title="private source title",
        source_url="https://private-source.invalid/secret",
        last_verified_at=date(2026, 7, 25),
        caution="private caution",
        question_examples=("private question example",),
    )


def _request(*, processing_time: str | None = "즉시", fee: str | None = "수수료 3,000원"):
    record = _record(processing_time=processing_time, fee=fee)
    return build_grounded_chat_request(
        masked_question="전입신고 방법을 알려 주세요.",
        intent=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        record=record,
    )


def _draft(
    *,
    summary: str = "전입신고입니다.",
    procedure_step_ids: list[str] | None = None,
    required_document_ids: list[str] | None = None,
    processing_time_id: str | None = "TIME-01",
    fee_id: str | None = "FEE-01",
    department_id: str = "DEPT-01",
) -> GeneratedChatDraft:
    return GeneratedChatDraft(
        summary=summary,
        procedure_step_ids=["STEP-01", "STEP-02"]
        if procedure_step_ids is None
        else procedure_step_ids,
        required_document_ids=["DOC-01"]
        if required_document_ids is None
        else required_document_ids,
        processing_time_id=processing_time_id,
        fee_id=fee_id,
        department_id=department_id,
    )


def test_build_request_issues_only_request_local_facts() -> None:
    request = _request()

    assert request.masked_question == "전입신고 방법을 알려 주세요."
    assert request.intent is Intent.MOVE_IN_RESIDENT_REGISTRATION
    assert request.service_name == "전입신고"
    assert request.approved_summary == "전입신고는 전입한 날부터 14일 이내에 신고합니다."
    assert [(fact.fact_id, fact.kind.value, fact.text) for fact in request.facts] == [
        ("STEP-01", "PROCEDURE_STEP", "정부24 또는 주민센터에서 신고합니다."),
        ("STEP-02", "PROCEDURE_STEP", "신분증을 준비합니다."),
        ("DOC-01", "REQUIRED_DOCUMENT", "신분증"),
        ("TIME-01", "PROCESSING_TIME", "즉시"),
        ("FEE-01", "FEE", "수수료 3,000원"),
        ("DEPT-01", "DEPARTMENT", "주민등록 담당 부서"),
    ]
    serialized = repr(request)
    for forbidden in (
        "KB-PRIVATE-ID-MUST-NOT-LEAK",
        "private source title",
        "private-source.invalid",
        "private caution",
        "private question example",
    ):
        assert forbidden not in serialized


def test_materializes_complete_valid_draft_byte_for_byte() -> None:
    answer = materialize_grounded_answer(_request(), _draft())

    assert answer is not None
    assert answer.summary == "전입신고입니다."
    assert answer.procedure_steps == (
        "정부24 또는 주민센터에서 신고합니다.",
        "신분증을 준비합니다.",
    )
    assert answer.required_documents == ("신분증",)
    assert answer.processing_time == "즉시"
    assert answer.fee == "수수료 3,000원"
    assert answer.department == "주민등록 담당 부서"


@pytest.mark.parametrize(
    "draft",
    [
        _draft(procedure_step_ids=["STEP-01", "STEP-99"]),
        _draft(procedure_step_ids=["STEP-01", "STEP-01"]),
        _draft(procedure_step_ids=["STEP-01"]),
        _draft(procedure_step_ids=["STEP-02", "STEP-01"]),
        _draft(required_document_ids=["DOC-99"]),
        _draft(department_id="DEPT-02"),
    ],
)
def test_rejects_unknown_duplicate_missing_or_reordered_fact_ids(draft: GeneratedChatDraft) -> None:
    assert materialize_grounded_answer(_request(), draft) is None


@pytest.mark.parametrize(
    ("grounded_request", "draft"),
    [
        (_request(processing_time=None), _draft(processing_time_id="TIME-01")),
        (_request(processing_time="즉시"), _draft(processing_time_id=None)),
        (_request(fee=None), _draft(fee_id="FEE-01")),
        (_request(fee="수수료 3,000원"), _draft(fee_id=None)),
    ],
)
def test_rejects_optional_fact_presence_mismatch(
    grounded_request: GroundedChatRequest, draft: GeneratedChatDraft
) -> None:
    assert materialize_grounded_answer(grounded_request, draft) is None


@pytest.mark.parametrize(
    "summary",
    [
        "홍길동의 전입신고 안내입니다.",
        "https://new-fact.invalid 전입신고 안내입니다.",
        "전입신고는 15일 이내에 신고합니다.",
        "전입신고는 2027-01-01에 신고합니다.",
        "전입신고 수수료는 4,000원입니다.",
        "전입신고 [전화번호] 안내입니다.",
        "전입신고 마법 안내입니다.",
        "공식 안내를 쉽게 정리해 드려요.",
    ],
)
def test_summary_validator_fails_closed_for_new_or_unsafe_content(summary: str) -> None:
    assert materialize_grounded_answer(_request(), _draft(summary=summary)) is None
