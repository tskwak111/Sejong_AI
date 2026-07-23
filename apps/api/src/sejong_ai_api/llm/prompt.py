"""Canonical source-free prompts for approved synthetic fixtures."""

import json

from sejong_ai_api.llm.contracts import GroundedFixture

PROMPT_VERSION = "0.1.0-upstage-solar-pro3-synthetic"

_SYSTEM_MESSAGE = (
    "승인된 공식 KB에 있는 사실만 사용하고 사실을 추가하지 마세요. "
    "응답은 JSON만 작성하세요. KB의 null 값은 반드시 null로 유지하세요. "
    "source, intent, status 필드는 절대 출력하지 마세요."
)


def build_upstage_messages(fixture: GroundedFixture) -> tuple[dict[str, str], ...]:
    """Build the only complete prompt form accepted by the synthetic transport."""
    if type(fixture) is not GroundedFixture:
        raise ValueError("GROUNDED_FIXTURE_INVALID")

    record = fixture.record
    payload = {
        "question": fixture.masked_question,
        "intent": fixture.intent.value,
        "official_kb": {
            "service_name": record.service_name,
            "answer_summary": record.answer_summary,
            "procedure_steps": list(record.procedure_steps),
            "required_documents": list(record.required_documents),
            "processing_time": record.processing_time,
            "fee": record.fee,
            "department": record.department,
            "caution": record.caution,
        },
        "output_schema": {
            "summary": "string, 1..500",
            "procedure_steps": "list[string], max 12",
            "required_documents": "list[string], max 12",
            "processing_time": "string 1..200 or null",
            "fee": "string 1..200 or null",
            "department": "string 1..200 or null",
        },
    }
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    _assert_source_free(serialized)
    return (
        {"role": "system", "content": _SYSTEM_MESSAGE},
        {"role": "user", "content": serialized},
    )


def estimate_input_token_upper_bound(messages: tuple[dict[str, str], ...]) -> int:
    """Return a deliberately conservative tokenizer-free UTF-8 input upper bound."""
    canonical = json.dumps(messages, ensure_ascii=False, separators=(",", ":"))
    return len(canonical.encode("utf-8"))


def _assert_source_free(serialized: str) -> None:
    forbidden_fields = (
        "source_title",
        "source_url",
        "last_verified_at",
        "question_examples",
        "public_id",
    )
    if any(field in serialized for field in forbidden_fields):
        raise AssertionError("SOURCE_FIELD_IN_PROMPT")
