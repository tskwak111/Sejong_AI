"""Short-lived, signed, client-carried chat context.

The token is an integrity-protected hint, not an authentication mechanism. Its
payload is intentionally small and closed; it never contains citizen text or
official-source data.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal, cast
from uuid import UUID, uuid4

CONTEXT_TOKEN_SCHEMA_VERSION = 2
CONTEXT_TOKEN_TTL_SECONDS = 900
MAX_CONTEXT_TOKEN_LENGTH = 2048
_MIN_SECRET_BYTES = 32

type Intent = Literal[
    "MOVE_IN_RESIDENT_REGISTRATION",
    "CERTIFICATE_ISSUANCE",
    "BULKY_WASTE",
    "LOCAL_TAX_GENERAL",
    "OUT_OF_SCOPE",
    "UNKNOWN",
]
type Region = Literal["아름동", "도담동", "조치원읍"]
type ContextAnswerStatus = Literal["SUCCESS", "FOLLOWUP"]
type PendingSlot = Literal["CERTIFICATE_KIND", "REGION", "WASTE_ITEM"]
type DialogAct = Literal[
    "ANSWERED",
    "ASKING_SLOT",
    "CHANGING_REGION",
    "CHANGING_TOPIC",
]
type FollowupOptionId = Literal[
    "intent.move-in",
    "intent.certificate",
    "intent.bulky-waste",
    "intent.local-tax",
]
type Clock = Callable[[], int]
type NonceFactory = Callable[[], UUID]

_INTENTS = frozenset(
    {
        "MOVE_IN_RESIDENT_REGISTRATION",
        "CERTIFICATE_ISSUANCE",
        "BULKY_WASTE",
        "LOCAL_TAX_GENERAL",
        "OUT_OF_SCOPE",
        "UNKNOWN",
    }
)
_REGIONS = frozenset({"아름동", "도담동", "조치원읍"})
_ANSWER_STATUSES = frozenset({"SUCCESS", "FOLLOWUP"})
_PENDING_SLOTS = frozenset({"CERTIFICATE_KIND", "REGION", "WASTE_ITEM"})
_DIALOG_ACTS = frozenset({"ANSWERED", "ASKING_SLOT", "CHANGING_REGION", "CHANGING_TOPIC"})
_TOPIC_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,63}$")
_FOLLOWUP_OPTION_IDS = frozenset(
    {
        "intent.move-in",
        "intent.certificate",
        "intent.bulky-waste",
        "intent.local-tax",
    }
)
_V1_REQUIRED_CLAIMS = frozenset(
    {
        "answer_status",
        "exp",
        "iat",
        "last_intent",
        "schema_version",
        "selected_region",
    }
)
_V1_OPTIONAL_CLAIMS = frozenset({"followup_option_id"})
_V2_REQUIRED_CLAIMS = frozenset(
    {
        "answer_status",
        "dialog_act",
        "exp",
        "iat",
        "last_intent",
        "nonce",
        "schema_version",
        "selected_region",
    }
)
_V2_OPTIONAL_CLAIMS = frozenset({"pending_slot", "topic_id"})


@dataclass(frozen=True, slots=True)
class ChatContext:
    """Validated, non-sensitive context recovered from a client token."""

    schema_version: int
    issued_at: int
    expires_at: int
    last_intent: Intent
    selected_region: Region | None
    answer_status: ContextAnswerStatus
    nonce: UUID | None = None
    topic_id: str | None = None
    pending_slot: PendingSlot | None = None
    dialog_act: DialogAct | None = None
    followup_option_id: str | None = None


class ContextTokenCodec:
    """Issue v2 and silently validate v1/v2 HMAC-SHA-256 context tokens."""

    __slots__ = ("_clock", "_nonce_factory", "_secret")

    def __init__(
        self,
        *,
        secret: bytes,
        clock: Clock,
        nonce_factory: NonceFactory = uuid4,
    ) -> None:
        if type(secret) is not bytes:
            raise TypeError("context token secret must be bytes")
        if len(secret) < _MIN_SECRET_BYTES:
            raise ValueError("context token secret must contain at least 32 bytes")
        if not callable(clock):
            raise TypeError("context token clock must be callable")
        if not callable(nonce_factory):
            raise TypeError("context token nonce factory must be callable")
        self._secret = secret
        self._clock = clock
        self._nonce_factory = nonce_factory

    def issue(
        self,
        *,
        last_intent: Intent,
        selected_region: Region | None,
        answer_status: ContextAnswerStatus,
        dialog_act: DialogAct,
        topic_id: str | None = None,
        pending_slot: PendingSlot | None = None,
    ) -> str:
        """Return a new signed token for the supplied bounded context."""

        if type(last_intent) is not str or last_intent not in _INTENTS:
            raise ValueError("last_intent is not allowed")
        if selected_region is not None and (
            type(selected_region) is not str or selected_region not in _REGIONS
        ):
            raise ValueError("selected_region is not allowed")
        if type(answer_status) is not str or answer_status not in _ANSWER_STATUSES:
            raise ValueError("answer_status is not allowed")
        if topic_id is not None and not _valid_topic_id(topic_id):
            raise ValueError("topic_id is not a valid server identifier")
        if pending_slot is not None and (
            type(pending_slot) is not str or pending_slot not in _PENDING_SLOTS
        ):
            raise ValueError("pending_slot is not allowed")
        if type(dialog_act) is not str or dialog_act not in _DIALOG_ACTS:
            raise ValueError("dialog_act is not allowed")

        issued_at = self._now()
        nonce = self._nonce_factory()
        if type(nonce) is not UUID or nonce.int == 0:
            raise ValueError("context token nonce factory must return a non-zero UUID")
        payload: dict[str, object] = {
            "answer_status": answer_status,
            "dialog_act": dialog_act,
            "exp": issued_at + CONTEXT_TOKEN_TTL_SECONDS,
            "iat": issued_at,
            "last_intent": last_intent,
            "nonce": str(nonce),
            "schema_version": CONTEXT_TOKEN_SCHEMA_VERSION,
            "selected_region": selected_region,
        }
        if topic_id is not None:
            payload["topic_id"] = topic_id
        if pending_slot is not None:
            payload["pending_slot"] = pending_slot

        payload_segment = _encode_base64url(_canonical_json(payload))
        signature = hmac.new(
            self._secret,
            payload_segment.encode("ascii"),
            hashlib.sha256,
        ).digest()
        token = f"{payload_segment}.{_encode_base64url(signature)}"
        if len(token) > MAX_CONTEXT_TOKEN_LENGTH:
            raise ValueError("context token exceeds the maximum length")
        return token

    def read(self, token: str | None) -> ChatContext | None:
        """Return valid context, or silently reset to no context for any bad token."""

        if type(token) is not str or not token or len(token) > MAX_CONTEXT_TOKEN_LENGTH:
            return None

        try:
            payload_segment, signature_segment = _split_token(token)
            supplied_signature = _decode_base64url(signature_segment)
            if len(supplied_signature) != hashlib.sha256().digest_size:
                return None

            expected_signature = hmac.new(
                self._secret,
                payload_segment.encode("ascii"),
                hashlib.sha256,
            ).digest()
            if not hmac.compare_digest(supplied_signature, expected_signature):
                return None

            payload_bytes = _decode_base64url(payload_segment)
            payload_object = json.loads(payload_bytes.decode("utf-8"))
            if type(payload_object) is not dict:
                return None
            payload = cast(dict[str, object], payload_object)
            if payload_bytes != _canonical_json(payload):
                return None
            return self._validate_claims(payload)
        except (
            ValueError,
            UnicodeError,
            binascii.Error,
            json.JSONDecodeError,
            RecursionError,
        ):
            return None

    def _now(self) -> int:
        now = self._clock()
        if type(now) is not int:
            raise TypeError("context token clock must return an integer epoch second")
        if now < 0:
            raise ValueError("context token clock cannot return a negative epoch second")
        return now

    def _validate_claims(self, payload: Mapping[str, object]) -> ChatContext | None:
        schema_version = payload.get("schema_version")
        if type(schema_version) is not int:
            return None
        if schema_version == 1:
            return self._validate_v1_claims(payload)
        if schema_version == CONTEXT_TOKEN_SCHEMA_VERSION:
            return self._validate_v2_claims(payload)
        return None

    def _validate_v1_claims(self, payload: Mapping[str, object]) -> ChatContext | None:
        claim_names = frozenset(payload)
        if not _V1_REQUIRED_CLAIMS.issubset(claim_names):
            return None
        if not claim_names.issubset(_V1_REQUIRED_CLAIMS | _V1_OPTIONAL_CLAIMS):
            return None

        schema_version = payload["schema_version"]
        issued_at = payload["iat"]
        expires_at = payload["exp"]
        last_intent = payload["last_intent"]
        selected_region = payload["selected_region"]
        answer_status = payload["answer_status"]
        followup_option_id = payload.get("followup_option_id")

        if type(schema_version) is not int or schema_version != 1:
            return None
        if not self._valid_times(issued_at, expires_at):
            return None
        if type(last_intent) is not str or last_intent not in _INTENTS:
            return None
        if selected_region is not None and (
            type(selected_region) is not str or selected_region not in _REGIONS
        ):
            return None
        if type(answer_status) is not str or answer_status not in _ANSWER_STATUSES:
            return None
        if "followup_option_id" in payload and not _valid_followup_option_id(followup_option_id):
            return None

        return ChatContext(
            schema_version=schema_version,
            issued_at=cast(int, issued_at),
            expires_at=cast(int, expires_at),
            last_intent=cast(Intent, last_intent),
            selected_region=cast(Region | None, selected_region),
            answer_status=cast(ContextAnswerStatus, answer_status),
            followup_option_id=cast(str | None, followup_option_id),
        )

    def _validate_v2_claims(self, payload: Mapping[str, object]) -> ChatContext | None:
        claim_names = frozenset(payload)
        if not _V2_REQUIRED_CLAIMS.issubset(claim_names):
            return None
        if not claim_names.issubset(_V2_REQUIRED_CLAIMS | _V2_OPTIONAL_CLAIMS):
            return None

        issued_at = payload["iat"]
        expires_at = payload["exp"]
        last_intent = payload["last_intent"]
        selected_region = payload["selected_region"]
        answer_status = payload["answer_status"]
        nonce_raw = payload["nonce"]
        topic_id = payload.get("topic_id")
        pending_slot = payload.get("pending_slot")
        dialog_act = payload["dialog_act"]

        if not self._valid_times(issued_at, expires_at):
            return None
        if type(last_intent) is not str or last_intent not in _INTENTS:
            return None
        if selected_region is not None and (
            type(selected_region) is not str or selected_region not in _REGIONS
        ):
            return None
        if type(answer_status) is not str or answer_status not in _ANSWER_STATUSES:
            return None
        nonce = _valid_nonce(nonce_raw)
        if nonce is None:
            return None
        if topic_id is not None and not _valid_topic_id(topic_id):
            return None
        if pending_slot is not None and (
            type(pending_slot) is not str or pending_slot not in _PENDING_SLOTS
        ):
            return None
        if type(dialog_act) is not str or dialog_act not in _DIALOG_ACTS:
            return None

        return ChatContext(
            schema_version=CONTEXT_TOKEN_SCHEMA_VERSION,
            issued_at=cast(int, issued_at),
            expires_at=cast(int, expires_at),
            nonce=nonce,
            last_intent=cast(Intent, last_intent),
            selected_region=cast(Region | None, selected_region),
            answer_status=cast(ContextAnswerStatus, answer_status),
            topic_id=cast(str | None, topic_id),
            pending_slot=cast(PendingSlot | None, pending_slot),
            dialog_act=cast(DialogAct, dialog_act),
        )

    def _valid_times(self, issued_at: object, expires_at: object) -> bool:
        if type(issued_at) is not int or type(expires_at) is not int:
            return False
        if issued_at < 0 or expires_at - issued_at != CONTEXT_TOKEN_TTL_SECONDS:
            return False
        now = self._now()
        return issued_at <= now < expires_at


def _canonical_json(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _encode_base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode_base64url(value: str) -> bytes:
    if not value or "=" in value:
        raise ValueError("non-canonical base64url")
    encoded = value.encode("ascii")
    padding = b"=" * (-len(encoded) % 4)
    decoded = base64.b64decode(encoded + padding, altchars=b"-_", validate=True)
    if _encode_base64url(decoded) != value:
        raise ValueError("non-canonical base64url")
    return decoded


def _split_token(token: str) -> tuple[str, str]:
    parts = token.split(".")
    if len(parts) != 2 or not all(parts):
        raise ValueError("malformed token")
    return parts[0], parts[1]


def _valid_followup_option_id(value: object) -> bool:
    return type(value) is str and value in _FOLLOWUP_OPTION_IDS


def _valid_topic_id(value: object) -> bool:
    return type(value) is str and _TOPIC_ID_PATTERN.fullmatch(value) is not None


def _valid_nonce(value: object) -> UUID | None:
    if type(value) is not str:
        return None
    try:
        nonce = UUID(value)
    except ValueError:
        return None
    if str(nonce) != value or nonce.int == 0:
        return None
    return nonce


__all__ = [
    "CONTEXT_TOKEN_SCHEMA_VERSION",
    "CONTEXT_TOKEN_TTL_SECONDS",
    "MAX_CONTEXT_TOKEN_LENGTH",
    "ChatContext",
    "ContextTokenCodec",
]
