from __future__ import annotations

import re

import pytest

from sejong_ai_api.chat.idempotency import (
    IdempotencyClaim,
    IdempotencyClaimStatus,
    fingerprint_chat_request,
)
from sejong_ai_api.contracts.chat import ChatRequest


def test_request_fingerprint_is_stable_hmac_and_contains_no_input() -> None:
    request = ChatRequest(
        question="RAW-QUESTION-MUST-NOT-BE-STORED",
        selected_region="아름동",
        simple_language=True,
    )

    first = fingerprint_chat_request(request, secret=b"s" * 32)
    second = fingerprint_chat_request(request, secret=b"s" * 32)

    assert first == second
    assert re.fullmatch(r"[0-9a-f]{64}", first)
    assert request.question not in first
    assert "아름동" not in first
    assert repr(b"s" * 32) not in repr(first)


def test_request_fingerprint_is_domain_and_payload_sensitive() -> None:
    base = ChatRequest(question="대형폐기물 배출 방법", simple_language=False)
    changed = ChatRequest(question="대형폐기물 배출 방법", simple_language=True)

    assert fingerprint_chat_request(base, secret=b"a" * 32) != fingerprint_chat_request(
        changed,
        secret=b"a" * 32,
    )
    assert fingerprint_chat_request(base, secret=b"a" * 32) != fingerprint_chat_request(
        base,
        secret=b"b" * 32,
    )


@pytest.mark.parametrize(
    "secret",
    [b"", b"short", "not-bytes"],
)
def test_request_fingerprint_rejects_invalid_secret(secret: object) -> None:
    with pytest.raises(ValueError, match="^IDEMPOTENCY_SECRET_INVALID$"):
        fingerprint_chat_request(
            ChatRequest(question="대형폐기물 배출 방법"),
            secret=secret,  # type: ignore[arg-type]
        )


def test_completed_claim_requires_a_safe_response_payload() -> None:
    with pytest.raises(ValueError, match="^IDEMPOTENCY_CLAIM_INVALID$"):
        IdempotencyClaim(status=IdempotencyClaimStatus.COMPLETED)

    with pytest.raises(ValueError, match="^IDEMPOTENCY_CLAIM_INVALID$"):
        IdempotencyClaim(
            status=IdempotencyClaimStatus.ACQUIRED,
            response_payload={"answer_status": "FALLBACK"},
        )


@pytest.mark.parametrize(
    "payload",
    [
        {"request_id": "must-not-persist"},
        {"correlation_id": "must-not-persist"},
        {"correlation_request_id": "must-not-persist"},
        {"context_token": "must-not-persist"},
        {"context": {"value": "must-not-persist"}},
        {"fallback": {"question": "must-not-persist"}},
        {"fallback": {"masked_question": "must-not-persist"}},
        {"fallback": {"raw_question": "must-not-persist"}},
        {"fallback": {"request": "must-not-persist"}},
        {"fallback": {"request_body": "must-not-persist"}},
        {"fallback": {"provider_request": "must-not-persist"}},
        {"fallback": {"provider_response": "must-not-persist"}},
        {"fallback": {"provider_content": "must-not-persist"}},
        {"fallback": {"provider_error": "must-not-persist"}},
        {"fallback": {"provider_result": "must-not-persist"}},
        {"fallback": {"draft": "must-not-persist"}},
        {"fallback": {"prompt": "must-not-persist"}},
        {"sources": [{"transcript": "must-not-persist"}]},
    ],
)
def test_completed_claim_rejects_persistent_correlation_or_conversation_values(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="^IDEMPOTENCY_CLAIM_INVALID$"):
        IdempotencyClaim(
            status=IdempotencyClaimStatus.COMPLETED,
            response_payload=payload,
        )


def test_completed_claim_accepts_only_safe_chat_response_fields() -> None:
    claim = IdempotencyClaim(
        status=IdempotencyClaimStatus.COMPLETED,
        response_payload={
            "answer_status": "FALLBACK",
            "intent": "UNKNOWN",
            "sources": [],
            "fallback": {"reason": "PERSONAL_LOOKUP"},
            "answer_mode": "TEMPLATE",
        },
    )

    assert claim.status is IdempotencyClaimStatus.COMPLETED
