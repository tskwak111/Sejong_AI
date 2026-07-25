from __future__ import annotations

import re
from typing import cast

import pytest

from sejong_ai_api.chat.idempotency import (
    IdempotencyClaim,
    IdempotencyClaimStatus,
    fingerprint_chat_request,
)
from sejong_ai_api.contracts.chat import ChatRequest


def _safe_fallback_payload() -> dict[str, object]:
    return {
        "intent": "UNKNOWN",
        "confidence": None,
        "summary": None,
        "procedure_steps": [],
        "required_documents": [],
        "processing_time": None,
        "fee": None,
        "department": None,
        "followup_options": [],
        "fallback": {
            "reason": "PERSONAL_LOOKUP",
            "title": "개인 정보 조회는 할 수 없어요",
            "message": "이 서비스는 개인별 신청·처리·고지 상태를 조회하지 않아요.",
            "next_actions": ["정부24 또는 해당 기관의 본인 인증 조회 경로를 이용해 주세요."],
            "candidate_eligible": False,
            "office": None,
        },
        "answer_status": "FALLBACK",
        "sources": [],
    }


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
        {"answer_status": "FALLBACK"},
        {"arbitrary": {"nested": "json"}},
    ],
)
def test_completed_claim_rejects_incomplete_or_arbitrary_json(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="^IDEMPOTENCY_CLAIM_INVALID$"):
        IdempotencyClaim(
            status=IdempotencyClaimStatus.COMPLETED,
            response_payload=payload,
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


@pytest.mark.parametrize(
    "credential_key",
    [
        "access_token",
        "Api_Key",
        "api_secret",
        "Authorization",
        "bearer_token",
        "client_secret",
        "LLM_API_KEY",
        "provider_api_key",
        "provider_secret",
        "secret",
        "secret_access_key",
    ],
)
def test_completed_claim_rejects_nested_provider_credential_keys(
    credential_key: str,
) -> None:
    payload = _safe_fallback_payload()
    fallback = cast(dict[str, object], payload["fallback"])
    fallback["office"] = {
        "id": "OFFICE-TEST-01",
        "region": "아름동",
        "office_name": "아름동 행정복지센터",
        "address": "세종특별자치시 시연용 주소",
        "phone": "044-000-0000",
        "opening_hours": "평일 09:00~18:00",
        "map_url": None,
        "source_title": "승인된 기관 출처",
        "source_url": "https://example.invalid/official/office",
        "last_verified_at": "2026-07-20",
        credential_key: "provider-credential-must-not-persist",
    }

    with pytest.raises(ValueError, match="^IDEMPOTENCY_CLAIM_INVALID$"):
        IdempotencyClaim(
            status=IdempotencyClaimStatus.COMPLETED,
            response_payload=payload,
        )


def test_completed_claim_accepts_only_safe_chat_response_fields() -> None:
    payload = _safe_fallback_payload()

    claim = IdempotencyClaim(
        status=IdempotencyClaimStatus.COMPLETED,
        response_payload=payload,
    )

    assert claim.status is IdempotencyClaimStatus.COMPLETED
    assert claim.response_payload == payload
