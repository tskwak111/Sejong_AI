import json

import pytest
from pydantic import ValidationError

from sejong_ai_api.llm.contracts import (
    GeneratedAnswer,
    GenerationOutcome,
    OutcomeCode,
    TokenUsage,
)


def test_generated_answer_rejects_provider_owned_source_and_status() -> None:
    payload = {
        "summary": "공식 KB 범위에서 정리한 안내입니다.",
        "procedure_steps": ["첫 번째 절차를 확인합니다."],
        "required_documents": [],
        "processing_time": None,
        "fee": None,
        "department": "민원 담당 부서",
        "source_url": "https://example.invalid",
    }
    with pytest.raises(ValidationError):
        GeneratedAnswer.model_validate_json(json.dumps(payload, ensure_ascii=False))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("input_tokens", -1),
        ("cached_input_tokens", -1),
        ("output_tokens", -1),
        ("input_tokens", True),
    ],
)
def test_token_usage_rejects_negative_or_non_integer_tokens(field: str, value: object) -> None:
    values: dict[str, object] = {
        "input_tokens": 10,
        "cached_input_tokens": 0,
        "output_tokens": 1,
    }
    values[field] = value
    with pytest.raises(ValueError, match="TOKEN_USAGE_INVALID"):
        TokenUsage(**values)  # type: ignore[arg-type]


def test_token_usage_rejects_cached_tokens_above_input_tokens() -> None:
    with pytest.raises(ValueError, match="CACHED_INPUT_TOKENS_INVALID"):
        TokenUsage(input_tokens=1, cached_input_tokens=2, output_tokens=0)


@pytest.mark.parametrize(
    ("code", "answer", "attempts"),
    [
        (OutcomeCode.SUCCESS, None, 1),
        (
            OutcomeCode.TIMEOUT,
            GeneratedAnswer(
                summary="안내",
                procedure_steps=[],
                required_documents=[],
                processing_time=None,
                fee=None,
                department=None,
            ),
            1,
        ),
        (
            OutcomeCode.SUCCESS,
            GeneratedAnswer(
                summary="안내",
                procedure_steps=[],
                required_documents=[],
                processing_time=None,
                fee=None,
                department=None,
            ),
            -1,
        ),
    ],
)
def test_generation_outcome_rejects_invalid_state_combinations(
    code: OutcomeCode, answer: GeneratedAnswer | None, attempts: int
) -> None:
    with pytest.raises(ValueError, match="GENERATION_OUTCOME_INVALID|ATTEMPTS_USED_INVALID"):
        GenerationOutcome(
            code=code,
            answer=answer,
            usage=TokenUsage(input_tokens=0, cached_input_tokens=0, output_tokens=0),
            attempts_used=attempts,
        )
