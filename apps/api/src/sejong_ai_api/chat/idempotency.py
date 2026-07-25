"""Privacy-safe primitives and repository protocol for chat idempotency."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from sejong_ai_api.contracts.chat import CHAT_RESPONSE_ADAPTER, ChatRequest
from sejong_ai_api.db.models import InteractionWrite

_FINGERPRINT_DOMAIN = b"sejong-ai:chat-idempotency:v1\x00"
_VALIDATION_REQUEST_ID = "00000000-0000-4000-8000-000000000000"
_FORBIDDEN_RESPONSE_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "api_secret",
        "authorization",
        "bearer_token",
        "client_secret",
        "context",
        "context_token",
        "correlation_id",
        "correlation_request_id",
        "draft",
        "llm_api_key",
        "masked_question",
        "prompt",
        "provider_api_key",
        "provider_body",
        "provider_content",
        "provider_error",
        "provider_request",
        "provider_response",
        "provider_result",
        "provider_secret",
        "question",
        "raw_question",
        "request",
        "request_body",
        "request_id",
        "secret",
        "secret_access_key",
        "transcript",
    }
)


class IdempotencyClaimStatus(StrEnum):
    ACQUIRED = "ACQUIRED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True, slots=True)
class IdempotencyClaim:
    status: IdempotencyClaimStatus
    response_payload: dict[str, object] | None = None

    def __post_init__(self) -> None:
        if type(self.status) is not IdempotencyClaimStatus:
            raise ValueError("IDEMPOTENCY_CLAIM_INVALID")
        if self.status is IdempotencyClaimStatus.COMPLETED:
            if not _is_safe_response_payload(self.response_payload):
                raise ValueError("IDEMPOTENCY_CLAIM_INVALID")
            return
        if self.response_payload is not None:
            raise ValueError("IDEMPOTENCY_CLAIM_INVALID")


class ChatIdempotencyRepository(Protocol):
    async def claim_chat_idempotency(
        self,
        *,
        idempotency_key: UUID,
        request_fingerprint: str,
        claim_token: UUID,
    ) -> IdempotencyClaim: ...

    async def complete_chat_idempotency(
        self,
        *,
        idempotency_key: UUID,
        request_fingerprint: str,
        claim_token: UUID,
        response_payload: dict[str, object],
    ) -> None: ...

    async def commit_chat_idempotency(
        self,
        *,
        idempotency_key: UUID,
        request_fingerprint: str,
        claim_token: UUID,
        response_payload: dict[str, object],
        interaction: InteractionWrite | None,
    ) -> None: ...

    async def abandon_chat_idempotency(
        self,
        *,
        idempotency_key: UUID,
        request_fingerprint: str,
        claim_token: UUID,
    ) -> None: ...


def fingerprint_chat_request(request: ChatRequest, *, secret: bytes) -> str:
    """Return a domain-separated HMAC without retaining raw request values."""

    if type(request) is not ChatRequest:
        raise TypeError("CHAT_REQUEST_REQUIRED")
    if type(secret) is not bytes or len(secret) < 32:
        raise ValueError("IDEMPOTENCY_SECRET_INVALID")
    canonical = json.dumps(
        request.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hmac.new(secret, _FINGERPRINT_DOMAIN + canonical, hashlib.sha256).hexdigest()


def _contains_forbidden_key(value: object) -> bool:
    if type(value) is dict:
        for key, nested in value.items():
            if type(key) is not str or key.casefold() in _FORBIDDEN_RESPONSE_KEYS:
                return True
            if _contains_forbidden_key(nested):
                return True
        return False
    if type(value) is list:
        return any(_contains_forbidden_key(item) for item in value)
    return False


def _is_safe_response_payload(value: object) -> bool:
    if type(value) is not dict or not value or _contains_forbidden_key(value):
        return False
    candidate = value.copy()
    candidate["request_id"] = _VALIDATION_REQUEST_ID
    candidate["context_token"] = None
    try:
        validated = CHAT_RESPONSE_ADAPTER.validate_json(
            json.dumps(
                candidate,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        )
    except (TypeError, ValueError):
        return False
    return (
        validated.model_dump(
            mode="json",
            exclude={"request_id", "context_token"},
        )
        == value
    )


class IdempotencyConflictError(Exception):
    """The same public key was reused for a different safe request identity."""

    def __init__(self) -> None:
        super().__init__("IDEMPOTENCY_CONFLICT")


class IdempotencyInProgressError(Exception):
    """A matching request is already being processed."""

    def __init__(self) -> None:
        super().__init__("IDEMPOTENCY_IN_PROGRESS")


__all__ = [
    "ChatIdempotencyRepository",
    "IdempotencyClaim",
    "IdempotencyClaimStatus",
    "IdempotencyConflictError",
    "IdempotencyInProgressError",
    "fingerprint_chat_request",
]
