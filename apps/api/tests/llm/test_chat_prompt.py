import json
from datetime import date

import pytest

from sejong_ai_api.db.models import Intent, KnowledgeRecord
from sejong_ai_api.llm.chat_contracts import GroundedChatRequest
from sejong_ai_api.llm.chat_prompt import (
    build_grounded_chat_messages,
    estimate_grounded_input_upper_bound,
)
from sejong_ai_api.llm.facts import build_grounded_chat_request


def _request() -> GroundedChatRequest:
    record = KnowledgeRecord(
        public_id="KB-PRIVATE-SENTINEL",
        category=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        service_name="전입신고",
        answer_summary="전입한 날부터 14일 이내에 전입신고를 합니다.",
        procedure_steps=("신고서를 작성합니다.",),
        required_documents=("신분증을 준비합니다.",),
        processing_time="즉시",
        fee="수수료 없음",
        department="주민등록 담당부서",
        source_title="SOURCE-TITLE-SENTINEL",
        source_url="https://source-sentinel.invalid/private",
        last_verified_at=date(2026, 7, 25),
        caution="CAUTION-SENTINEL",
        question_examples=("EXAMPLE-SENTINEL",),
    )
    return build_grounded_chat_request(
        masked_question="전입신고 방법을 알려 주세요.",
        intent=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        record=record,
    )


def test_prompt_contains_only_the_approved_payload_fields() -> None:
    messages = build_grounded_chat_messages(_request())

    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    payload = json.loads(messages[1]["content"])
    assert payload == {
        "masked_question": "전입신고 방법을 알려 주세요.",
        "intent": "MOVE_IN_RESIDENT_REGISTRATION",
        "service_name": "전입신고",
        "approved_summary": "전입한 날부터 14일 이내에 전입신고를 합니다.",
        "facts": [
            {"id": "STEP-01", "kind": "PROCEDURE_STEP", "text": "신고서를 작성합니다."},
            {"id": "DOC-01", "kind": "REQUIRED_DOCUMENT", "text": "신분증을 준비합니다."},
            {"id": "TIME-01", "kind": "PROCESSING_TIME", "text": "즉시"},
            {"id": "FEE-01", "kind": "FEE", "text": "수수료 없음"},
            {"id": "DEPT-01", "kind": "DEPARTMENT", "text": "주민등록 담당부서"},
        ],
        "output_schema": {
            "summary": "string<=500",
            "procedure_step_ids": ["STEP-.."],
            "required_document_ids": ["DOC-.."],
            "processing_time_id": "TIME-01|null",
            "fee_id": "FEE-01|null",
            "department_id": "DEPT-01",
        },
    }
    assert "JSON" in messages[0]["content"]
    assert "추가" in messages[0]["content"]


def test_prompt_excludes_source_internal_office_context_and_secret_sentinels() -> None:
    serialized = json.dumps(
        build_grounded_chat_messages(_request()),
        ensure_ascii=False,
        separators=(",", ":"),
    )

    for forbidden_field in (
        "source_title",
        "source_url",
        "last_verified_at",
        "public_id",
        "question_examples",
        "caution",
        "context_token",
        "office",
    ):
        assert forbidden_field not in serialized
    for forbidden_value in (
        "https://source-sentinel.invalid/private",
        "KB-PRIVATE-SENTINEL",
        "SOURCE-TITLE-SENTINEL",
        "CAUTION-SENTINEL",
        "EXAMPLE-SENTINEL",
        "CONTEXT-SENTINEL",
        "OFFICE-SENTINEL",
        "SECRET-SENTINEL",
    ):
        assert forbidden_value not in serialized


def test_input_upper_bound_is_complete_canonical_utf8_byte_length() -> None:
    messages = (
        {"role": "system", "content": "가"},
        {"role": "user", "content": "나"},
    )
    canonical = json.dumps(messages, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    assert estimate_grounded_input_upper_bound(messages) == len(canonical)


def test_prompt_rejects_non_request_without_serializing_it() -> None:
    with pytest.raises(ValueError, match="GROUNDED_CHAT_REQUEST_INVALID"):
        build_grounded_chat_messages(object())  # type: ignore[arg-type]
