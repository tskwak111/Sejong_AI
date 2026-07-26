from __future__ import annotations

import pytest
from pydantic import ValidationError

from sejong_ai_api.llm.chat_contracts import (
    GeneratedChatDraft,
    GroundedChatOutcomeCode,
    GroundedChatResult,
)
from sejong_ai_api.llm.contracts import TokenUsage


def test_generated_draft_rejects_extra_provider_field() -> None:
    with pytest.raises(ValidationError):
        GeneratedChatDraft.model_validate(
            {
                "summary": "전입신고입니다.",
                "procedure_step_ids": ["STEP-01"],
                "required_document_ids": [],
                "processing_time_id": None,
                "fee_id": None,
                "department_id": "DEPT-01",
                "source_url": "https://provider-must-not-control.invalid",
            }
        )


def test_grounded_result_requires_draft_for_success() -> None:
    with pytest.raises(ValueError, match="GROUNDED_CHAT_RESULT_INVALID"):
        GroundedChatResult(code=GroundedChatOutcomeCode.SUCCESS)


def test_grounded_result_rejects_draft_for_non_success() -> None:
    draft = GeneratedChatDraft(
        summary="전입신고입니다.",
        procedure_step_ids=["STEP-01"],
        required_document_ids=[],
        processing_time_id=None,
        fee_id=None,
        department_id="DEPT-01",
    )

    with pytest.raises(ValueError, match="GROUNDED_CHAT_RESULT_INVALID"):
        GroundedChatResult(code=GroundedChatOutcomeCode.TIMEOUT, draft=draft)


def test_grounded_result_defaults_to_content_free_zero_usage() -> None:
    result = GroundedChatResult(code=GroundedChatOutcomeCode.TIMEOUT)

    assert result.usage == TokenUsage(0, 0, 0)


def test_grounded_result_requires_exact_token_usage() -> None:
    with pytest.raises(ValueError, match="GROUNDED_CHAT_RESULT_INVALID"):
        GroundedChatResult(
            code=GroundedChatOutcomeCode.TIMEOUT,
            usage={"input_tokens": 1, "cached_input_tokens": 0, "output_tokens": 1},  # type: ignore[arg-type]
        )
