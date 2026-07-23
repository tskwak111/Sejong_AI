import json

from sejong_ai_api.llm.contracts import GroundedFixture
from sejong_ai_api.llm.prompt import (
    PROMPT_VERSION,
    build_upstage_messages,
    estimate_input_token_upper_bound,
)


def test_canonical_prompt_stays_within_conservative_input_upper_bound(
    grounded_fixture: GroundedFixture,
) -> None:
    messages = build_upstage_messages(grounded_fixture)
    assert estimate_input_token_upper_bound(messages) <= 4096


def test_prompt_is_source_free_and_system_requires_strict_json(
    grounded_fixture: GroundedFixture,
) -> None:
    messages = build_upstage_messages(grounded_fixture)
    serialized = json.dumps(messages, ensure_ascii=False, separators=(",", ":"))
    assert PROMPT_VERSION == "0.1.0-upstage-solar-pro3-synthetic"
    for forbidden in (
        "source_title",
        "source_url",
        "last_verified_at",
        "question_examples",
        "public_id",
    ):
        assert forbidden not in serialized
    assert messages[0]["role"] == "system"
    assert "사실을 추가" in messages[0]["content"]
    assert "JSON만" in messages[0]["content"]
    assert "null" in messages[0]["content"]
    assert "source" in messages[0]["content"]
    assert "intent" in messages[0]["content"]
    assert "status" in messages[0]["content"]


def test_input_upper_bound_is_canonical_complete_message_utf8_length() -> None:
    messages = (
        {"role": "system", "content": "가"},
        {"role": "user", "content": "나"},
    )
    canonical = json.dumps(messages, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    assert estimate_input_token_upper_bound(messages) == len(canonical)
