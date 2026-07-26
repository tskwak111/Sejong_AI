"""Fixed-statement asynchronous adapter for the private database capability API."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from datetime import date
from typing import Any, Protocol
from uuid import UUID

import psycopg
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool
from pydantic import ValidationError

from sejong_ai_api.admin.candidate_binding import RESERVED_KB_PUBLIC_ID
from sejong_ai_api.chat.idempotency import IdempotencyClaim, IdempotencyClaimStatus
from sejong_ai_api.contracts.admin import (
    CivicScopeGapSummary,
    FailedQuestion,
    KBCandidateSummary,
)
from sejong_ai_api.contracts.chat import CHAT_RESPONSE_ADAPTER
from sejong_ai_api.db.errors import DatabaseUnavailableError, map_database_error
from sejong_ai_api.db.models import (
    Actor,
    AdminRole,
    CandidateDraft,
    FailureReasonConfirmation,
    FallbackReason,
    Intent,
    InteractionWrite,
    InteractionWriteResult,
    KnowledgeRecord,
    OfficeRecord,
    PurgeResult,
    Region,
)

LIST_ACTIVE_KB_SQL = "SELECT * FROM app_api.list_active_kb(%s)"
LIST_OFFICES_SQL = "SELECT * FROM app_api.list_offices(%s, %s)"
RECORD_INTERACTION_SQL = (
    "SELECT * FROM app_api.record_interaction(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)
CONFIRM_FAILED_QUESTION_REASON_SQL = "SELECT app_api.confirm_failed_question_reason(%s, %s, %s, %s)"
CREATE_KB_CANDIDATE_SQL = (
    "SELECT app_api.create_kb_candidate(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
    "%s, %s, %s, %s, %s, %s, %s)"
)
SUBMIT_KB_CANDIDATE_SQL = "SELECT app_api.submit_kb_candidate(%s, %s, %s)"
APPROVE_KB_CANDIDATE_SQL = "SELECT app_api.approve_kb_candidate(%s, %s, %s, %s)"
APPROVE_KB_CANDIDATE_WITH_PUBLIC_ID_SQL = (
    "SELECT app_api.approve_kb_candidate_with_public_id(%s, %s, %s, %s, %s)"
)
REJECT_KB_CANDIDATE_SQL = "SELECT app_api.reject_kb_candidate(%s, %s, %s, %s)"
PURGE_EXPIRED_FAILED_QUESTION_TEXT_SQL = (
    "SELECT * FROM app_api.purge_expired_failed_question_text()"
)
LIST_FAILED_QUESTIONS_SQL = "SELECT * FROM app_api.list_failed_questions(%s, %s)"
GET_FAILED_QUESTION_SQL = "SELECT * FROM app_api.get_failed_question(%s)"
LIST_KB_CANDIDATES_SQL = "SELECT * FROM app_api.list_kb_candidates()"
GET_KB_CANDIDATE_SQL = "SELECT * FROM app_api.get_kb_candidate(%s)"
CLAIM_CHAT_IDEMPOTENCY_SQL = "SELECT * FROM app_api.claim_chat_idempotency(%s, %s, %s)"
COMPLETE_CHAT_IDEMPOTENCY_SQL = "SELECT app_api.complete_chat_idempotency(%s, %s, %s, %s)"
ABANDON_CHAT_IDEMPOTENCY_SQL = "SELECT app_api.abandon_chat_idempotency(%s, %s, %s)"
PURGE_EXPIRED_CHAT_IDEMPOTENCY_SQL = "SELECT * FROM app_api.purge_expired_chat_idempotency()"
RECORD_CIVIC_SCOPE_GAP_SQL = "SELECT app_api.record_civic_scope_gap(%s)"
LIST_CIVIC_SCOPE_GAPS_SQL = "SELECT * FROM app_api.list_civic_scope_gaps(%s)"
REVIEW_CIVIC_SCOPE_GAP_SQL = (
    "SELECT app_api.review_civic_scope_gap(%s, %s, %s, %s, %s)"
)
PURGE_EXPIRED_CIVIC_SCOPE_GAP_TEXT_SQL = (
    "SELECT * FROM app_api.purge_expired_civic_scope_gap_text()"
)

_SUPPORTED_INTENTS = frozenset(
    {
        Intent.MOVE_IN_RESIDENT_REGISTRATION,
        Intent.CERTIFICATE_ISSUANCE,
        Intent.BULKY_WASTE,
        Intent.LOCAL_TAX_GENERAL,
    }
)
_CONFIRMABLE_REASONS = frozenset(
    {
        FallbackReason.INSUFFICIENT_GROUNDING,
        FallbackReason.PERSONAL_LOOKUP,
        FallbackReason.LEGAL_JUDGMENT,
    }
)
_ADMIN_FAILURE_REASONS = frozenset(reason.value for reason in _CONFIRMABLE_REASONS)
_ADMIN_FAILURE_STATUSES = frozenset({"NEW", "REASON_CONFIRMED"})
_CIVIC_SCOPE_GAP_STATUSES = frozenset({"NEW", "PLANNED", "DISMISSED"})
_CIVIC_SCOPE_GAP_DECISIONS = frozenset({"PLANNED", "DISMISSED"})
_IDEMPOTENCY_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$", re.ASCII)
_IDEMPOTENCY_VALIDATION_REQUEST_ID = "00000000-0000-4000-8000-000000000000"


def _canonical_idempotency_response_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


_FORBIDDEN_IDEMPOTENCY_RESPONSE_KEYS = frozenset(
    _canonical_idempotency_response_key(key)
    for key in {
        "access_token",
        "api_key",
        "api_secret",
        "authorization",
        "authorization_header",
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
_MAX_IDEMPOTENCY_RESPONSE_BYTES = 65_536


class SejongRepository(Protocol):
    async def list_active_kb(self, intent: Intent) -> Sequence[KnowledgeRecord]: ...

    async def list_offices(self, region: Region, intent: Intent) -> Sequence[OfficeRecord]: ...

    async def record_interaction(self, event: InteractionWrite) -> InteractionWriteResult: ...

    async def confirm_failed_question_reason(
        self,
        failed_question_id: UUID,
        actor: Actor,
        fallback_reason: FallbackReason,
    ) -> None: ...

    async def create_kb_candidate(self, draft: CandidateDraft) -> UUID: ...

    async def submit_kb_candidate(self, candidate_id: UUID, actor: Actor) -> None: ...

    async def approve_kb_candidate(
        self, candidate_id: UUID, actor: Actor, review_comment: str
    ) -> str: ...

    async def approve_kb_candidate_with_public_id(
        self,
        candidate_id: UUID,
        actor: Actor,
        review_comment: str,
        public_id: str,
    ) -> str: ...

    async def reject_kb_candidate(
        self, candidate_id: UUID, actor: Actor, review_comment: str
    ) -> None: ...

    async def purge_expired_failed_question_text(self) -> PurgeResult: ...

    async def list_failed_questions(
        self, *, reason: str | None, status: str | None
    ) -> Sequence[FailedQuestion]: ...

    async def get_failed_question(self, failed_question_id: UUID) -> FailedQuestion | None: ...

    async def list_kb_candidates(self) -> Sequence[KBCandidateSummary]: ...

    async def get_kb_candidate(self, candidate_id: UUID) -> KBCandidateSummary | None: ...

    async def record_civic_scope_gap(self, masked_question: str) -> None: ...

    async def list_civic_scope_gaps(
        self, *, status: str | None
    ) -> Sequence[CivicScopeGapSummary]: ...

    async def review_civic_scope_gap(
        self,
        scope_gap_id: UUID,
        actor: Actor,
        decision: str,
        review_comment: str,
    ) -> None: ...

    async def purge_expired_civic_scope_gap_text(self) -> PurgeResult: ...

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

    async def purge_expired_chat_idempotency(self) -> PurgeResult: ...


def _require_supported_intent(intent: object) -> Intent:
    if type(intent) is not Intent or intent not in _SUPPORTED_INTENTS:
        raise ValueError("CATEGORY_INVALID")
    return intent


def _require_region(region: object) -> Region:
    if type(region) is not Region:
        raise ValueError("REGION_INVALID")
    return region


def _require_uuid(value: object, message: str) -> UUID:
    if type(value) is not UUID:
        raise ValueError(message)
    return value


def _require_actor(actor: object, expected_role: AdminRole) -> Actor:
    if type(actor) is not Actor or actor.role is not expected_role:
        raise ValueError("ACTOR_ROLE_FORBIDDEN")
    return actor


def _require_review_comment(value: object) -> str:
    if type(value) is not str or not value or value.strip() != value or len(value) > 1000:
        raise ValueError("REVIEW_COMMENT_INVALID")
    return value


def _require_admin_read_filter(value: object, allowed: frozenset[str]) -> str | None:
    if value is None:
        return None
    if type(value) is not str or value not in allowed:
        raise ValueError("ADMIN_READ_FILTER_INVALID")
    return value


def _require_idempotency_digest(value: object) -> str:
    if type(value) is not str or _IDEMPOTENCY_DIGEST_PATTERN.fullmatch(value) is None:
        raise ValueError("IDEMPOTENCY_DIGEST_INVALID")
    return value


def _response_has_forbidden_key(value: object) -> bool:
    if type(value) is dict:
        for key, nested in value.items():
            if type(key) is not str:
                return True
            if _canonical_idempotency_response_key(key) in _FORBIDDEN_IDEMPOTENCY_RESPONSE_KEYS:
                return True
            if _response_has_forbidden_key(nested):
                return True
        return False
    if type(value) is list:
        return any(_response_has_forbidden_key(item) for item in value)
    return type(value) not in {str, int, float, bool, type(None)}


def _require_safe_response_json(value: object) -> dict[str, Any]:
    if type(value) is not dict or not value or _response_has_forbidden_key(value):
        raise ValueError("IDEMPOTENCY_RESPONSE_UNSAFE")
    try:
        stored_encoded = json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
        candidate = value.copy()
        candidate["request_id"] = _IDEMPOTENCY_VALIDATION_REQUEST_ID
        candidate["context_token"] = None
        validated = CHAT_RESPONSE_ADAPTER.validate_json(
            json.dumps(
                candidate,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        )
    except (TypeError, ValueError):
        raise ValueError("IDEMPOTENCY_RESPONSE_UNSAFE") from None
    if (
        len(stored_encoded) > _MAX_IDEMPOTENCY_RESPONSE_BYTES
        or validated.model_dump(
            mode="json",
            exclude={"request_id", "context_token"},
        )
        != value
    ):
        raise ValueError("IDEMPOTENCY_RESPONSE_UNSAFE")
    return value.copy()


def _required_text(value: object) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError("MALFORMED_DATABASE_RESULT")
    return value


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    return _required_text(value)


def _required_uuid(value: object) -> UUID:
    if type(value) is not UUID:
        raise ValueError("MALFORMED_DATABASE_RESULT")
    return value


def _optional_uuid(value: object) -> UUID | None:
    if value is None:
        return None
    return _required_uuid(value)


def _required_date(value: object) -> date:
    if type(value) is not date:
        raise ValueError("MALFORMED_DATABASE_RESULT")
    return value


def _text_array(value: object) -> tuple[str, ...]:
    if type(value) is not list:
        raise ValueError("MALFORMED_DATABASE_RESULT")
    return tuple(_required_text(item) for item in value)


def _uuid_array(value: object) -> tuple[UUID, ...]:
    if type(value) is not list:
        raise ValueError("MALFORMED_DATABASE_RESULT")
    return tuple(_required_uuid(item) for item in value)


def _knowledge_record(row: dict[str, Any]) -> KnowledgeRecord:
    return KnowledgeRecord(
        public_id=_required_text(row["public_id"]),
        category=Intent(_required_text(row["category"])),
        service_name=_required_text(row["service_name"]),
        answer_summary=_required_text(row["answer_summary"]),
        procedure_steps=_text_array(row["procedure_steps"]),
        required_documents=_text_array(row["required_documents"]),
        processing_time=_optional_text(row["processing_time"]),
        fee=_optional_text(row["fee"]),
        department=_required_text(row["department"]),
        source_title=_required_text(row["source_title"]),
        source_url=_required_text(row["source_url"]),
        last_verified_at=_required_date(row["last_verified_at"]),
        caution=_optional_text(row["caution"]),
        question_examples=_text_array(row["question_examples"]),
    )


def _office_record(row: dict[str, Any]) -> OfficeRecord:
    return OfficeRecord(
        public_id=_required_text(row["public_id"]),
        region=Region(_required_text(row["region"])),
        office_name=_required_text(row["office_name"]),
        address=_required_text(row["address"]),
        phone=_required_text(row["phone"]),
        opening_hours=_optional_text(row["opening_hours"]),
        map_url=_optional_text(row["map_url"]),
        department_label=_optional_text(row["department_label"]),
        source_title=_required_text(row["source_title"]),
        source_url=_required_text(row["source_url"]),
        last_verified_at=_required_date(row["last_verified_at"]),
    )


def _safe_knowledge_records(rows: list[dict[str, Any]]) -> tuple[KnowledgeRecord, ...]:
    try:
        return tuple(_knowledge_record(row) for row in rows)
    except (KeyError, TypeError, ValueError):
        raise DatabaseUnavailableError() from None


def _safe_office_records(rows: list[dict[str, Any]]) -> tuple[OfficeRecord, ...]:
    try:
        return tuple(_office_record(row) for row in rows)
    except (KeyError, TypeError, ValueError):
        raise DatabaseUnavailableError() from None


def _safe_failed_questions(rows: list[dict[str, Any]]) -> tuple[FailedQuestion, ...]:
    try:
        return tuple(FailedQuestion.model_validate(row) for row in rows)
    except (TypeError, ValueError, ValidationError):
        raise DatabaseUnavailableError() from None


def _safe_candidates(rows: list[dict[str, Any]]) -> tuple[KBCandidateSummary, ...]:
    try:
        return tuple(KBCandidateSummary.model_validate(row) for row in rows)
    except (TypeError, ValueError, ValidationError):
        raise DatabaseUnavailableError() from None


def _safe_civic_scope_gaps(
    rows: list[dict[str, Any]],
) -> tuple[CivicScopeGapSummary, ...]:
    try:
        return tuple(CivicScopeGapSummary.model_validate(row) for row in rows)
    except (TypeError, ValueError, ValidationError):
        raise DatabaseUnavailableError() from None


class PsycopgSejongRepository:
    def __init__(
        self,
        pool: AsyncConnectionPool[AsyncConnection[dict[str, Any]]],
    ) -> None:
        self._pool = pool

    async def list_active_kb(self, intent: Intent) -> tuple[KnowledgeRecord, ...]:
        valid_intent = _require_supported_intent(intent)
        try:
            async with (
                self._pool.connection() as connection,
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(LIST_ACTIVE_KB_SQL, (valid_intent.value,))
                rows = await cursor.fetchall()
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc
        return _safe_knowledge_records(rows)

    async def list_offices(self, region: Region, intent: Intent) -> tuple[OfficeRecord, ...]:
        valid_region = _require_region(region)
        valid_intent = _require_supported_intent(intent)
        try:
            async with (
                self._pool.connection() as connection,
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(LIST_OFFICES_SQL, (valid_region.value, valid_intent.value))
                rows = await cursor.fetchall()
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc
        return _safe_office_records(rows)

    async def record_interaction(self, event: InteractionWrite) -> InteractionWriteResult:
        if type(event) is not InteractionWrite:
            raise ValueError("INTERACTION_INVALID")
        parameters = self._interaction_parameters(event)
        try:
            async with (
                self._pool.connection() as connection,
                connection.transaction(),
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(RECORD_INTERACTION_SQL, parameters)
                rows = await cursor.fetchall()
                result = self._interaction_result(rows)
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc
        return result

    async def confirm_failed_question_reason(
        self,
        failed_question_id: UUID,
        actor: Actor,
        fallback_reason: FallbackReason,
    ) -> None:
        valid_id = _require_uuid(failed_question_id, "FAILED_QUESTION_ID_INVALID")
        valid_actor = _require_actor(actor, AdminRole.OPERATOR)
        if (
            type(fallback_reason) is not FallbackReason
            or fallback_reason not in _CONFIRMABLE_REASONS
        ):
            raise ValueError("FALLBACK_REASON_INVALID")
        confirmation = FailureReasonConfirmation(valid_id, valid_actor, fallback_reason)
        await self._execute_void_write(
            CONFIRM_FAILED_QUESTION_REASON_SQL,
            (
                confirmation.failed_question_id,
                confirmation.actor.actor_id,
                confirmation.actor.role.value,
                confirmation.fallback_reason.value,
            ),
        )

    async def create_kb_candidate(self, draft: CandidateDraft) -> UUID:
        if type(draft) is not CandidateDraft:
            raise ValueError("CANDIDATE_DRAFT_INVALID")
        parameters = (
            draft.failed_question_id,
            draft.actor.actor_id,
            draft.actor.role.value,
            draft.title,
            draft.representative_question,
            draft.category.value,
            draft.answer_summary,
            Jsonb(list(draft.procedure_steps)),
            Jsonb(list(draft.required_documents)),
            draft.processing_time,
            draft.fee,
            draft.department,
            draft.source_title,
            draft.source_url,
            draft.last_verified_at,
            draft.caution,
            draft.data_origin.value,
        )
        try:
            async with (
                self._pool.connection() as connection,
                connection.transaction(),
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(CREATE_KB_CANDIDATE_SQL, parameters)
                rows = await cursor.fetchall()
                result = self._scalar_uuid(rows, "create_kb_candidate")
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc
        return result

    async def submit_kb_candidate(self, candidate_id: UUID, actor: Actor) -> None:
        valid_id = _require_uuid(candidate_id, "CANDIDATE_ID_INVALID")
        valid_actor = _require_actor(actor, AdminRole.OPERATOR)
        await self._execute_void_write(
            SUBMIT_KB_CANDIDATE_SQL,
            (valid_id, valid_actor.actor_id, valid_actor.role.value),
        )

    async def approve_kb_candidate(
        self, candidate_id: UUID, actor: Actor, review_comment: str
    ) -> str:
        valid_id = _require_uuid(candidate_id, "CANDIDATE_ID_INVALID")
        valid_actor = _require_actor(actor, AdminRole.APPROVER)
        valid_comment = _require_review_comment(review_comment)
        parameters = (
            valid_id,
            valid_actor.actor_id,
            valid_actor.role.value,
            valid_comment,
        )
        try:
            async with (
                self._pool.connection() as connection,
                connection.transaction(),
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(APPROVE_KB_CANDIDATE_SQL, parameters)
                rows = await cursor.fetchall()
                result = self._scalar_text(rows, "approve_kb_candidate")
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc
        return result

    async def approve_kb_candidate_with_public_id(
        self,
        candidate_id: UUID,
        actor: Actor,
        review_comment: str,
        public_id: str,
    ) -> str:
        valid_id = _require_uuid(candidate_id, "CANDIDATE_ID_INVALID")
        valid_actor = _require_actor(actor, AdminRole.APPROVER)
        valid_comment = _require_review_comment(review_comment)
        if type(public_id) is not str or public_id != RESERVED_KB_PUBLIC_ID:
            raise ValueError("PUBLIC_ID_INVALID")
        parameters = (
            valid_id,
            valid_actor.actor_id,
            valid_actor.role.value,
            valid_comment,
            RESERVED_KB_PUBLIC_ID,
        )
        try:
            async with (
                self._pool.connection() as connection,
                connection.transaction(),
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(APPROVE_KB_CANDIDATE_WITH_PUBLIC_ID_SQL, parameters)
                rows = await cursor.fetchall()
                result = self._scalar_text(rows, "approve_kb_candidate_with_public_id")
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc
        return result

    async def reject_kb_candidate(
        self, candidate_id: UUID, actor: Actor, review_comment: str
    ) -> None:
        valid_id = _require_uuid(candidate_id, "CANDIDATE_ID_INVALID")
        valid_actor = _require_actor(actor, AdminRole.APPROVER)
        valid_comment = _require_review_comment(review_comment)
        await self._execute_void_write(
            REJECT_KB_CANDIDATE_SQL,
            (
                valid_id,
                valid_actor.actor_id,
                valid_actor.role.value,
                valid_comment,
            ),
        )

    async def purge_expired_failed_question_text(self) -> PurgeResult:
        try:
            async with (
                self._pool.connection() as connection,
                connection.transaction(),
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(PURGE_EXPIRED_FAILED_QUESTION_TEXT_SQL, ())
                rows = await cursor.fetchall()
                result = self._purge_result(rows)
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc
        return result

    async def list_failed_questions(
        self, *, reason: str | None, status: str | None
    ) -> tuple[FailedQuestion, ...]:
        valid_reason = _require_admin_read_filter(reason, _ADMIN_FAILURE_REASONS)
        valid_status = _require_admin_read_filter(status, _ADMIN_FAILURE_STATUSES)
        try:
            async with (
                self._pool.connection() as connection,
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(LIST_FAILED_QUESTIONS_SQL, (valid_reason, valid_status))
                rows = await cursor.fetchall()
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc
        return _safe_failed_questions(rows)

    async def get_failed_question(self, failed_question_id: UUID) -> FailedQuestion | None:
        valid_id = _require_uuid(failed_question_id, "FAILED_QUESTION_ID_INVALID")
        try:
            async with (
                self._pool.connection() as connection,
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(GET_FAILED_QUESTION_SQL, (valid_id,))
                rows = await cursor.fetchall()
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc
        if not rows:
            return None
        if len(rows) != 1:
            raise DatabaseUnavailableError()
        return _safe_failed_questions(rows)[0]

    async def list_kb_candidates(self) -> tuple[KBCandidateSummary, ...]:
        try:
            async with (
                self._pool.connection() as connection,
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(LIST_KB_CANDIDATES_SQL, ())
                rows = await cursor.fetchall()
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc
        return _safe_candidates(rows)

    async def get_kb_candidate(self, candidate_id: UUID) -> KBCandidateSummary | None:
        valid_id = _require_uuid(candidate_id, "CANDIDATE_ID_INVALID")
        try:
            async with (
                self._pool.connection() as connection,
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(GET_KB_CANDIDATE_SQL, (valid_id,))
                rows = await cursor.fetchall()
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc
        if not rows:
            return None
        if len(rows) != 1:
            raise DatabaseUnavailableError()
        return _safe_candidates(rows)[0]

    async def record_civic_scope_gap(self, masked_question: str) -> None:
        valid_text = _required_text(masked_question)
        if len(valid_text) > 2000:
            raise ValueError("CIVIC_SCOPE_GAP_TEXT_INVALID")
        try:
            async with (
                self._pool.connection() as connection,
                connection.transaction(),
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(RECORD_CIVIC_SCOPE_GAP_SQL, (valid_text,))
                rows = await cursor.fetchall()
                self._scalar_uuid(rows, "record_civic_scope_gap")
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc

    async def list_civic_scope_gaps(
        self, *, status: str | None
    ) -> tuple[CivicScopeGapSummary, ...]:
        valid_status = _require_admin_read_filter(status, _CIVIC_SCOPE_GAP_STATUSES)
        try:
            async with (
                self._pool.connection() as connection,
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(LIST_CIVIC_SCOPE_GAPS_SQL, (valid_status,))
                rows = await cursor.fetchall()
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc
        return _safe_civic_scope_gaps(rows)

    async def review_civic_scope_gap(
        self,
        scope_gap_id: UUID,
        actor: Actor,
        decision: str,
        review_comment: str,
    ) -> None:
        valid_id = _require_uuid(scope_gap_id, "CIVIC_SCOPE_GAP_ID_INVALID")
        valid_actor = _require_actor(actor, AdminRole.APPROVER)
        valid_decision = _require_admin_read_filter(decision, _CIVIC_SCOPE_GAP_DECISIONS)
        if valid_decision is None:
            raise ValueError("CIVIC_SCOPE_GAP_DECISION_INVALID")
        valid_comment = _require_review_comment(review_comment)
        await self._execute_void_write(
            REVIEW_CIVIC_SCOPE_GAP_SQL,
            (
                valid_id,
                valid_actor.actor_id,
                valid_actor.role.value,
                valid_decision,
                valid_comment,
            ),
        )

    async def purge_expired_civic_scope_gap_text(self) -> PurgeResult:
        try:
            async with (
                self._pool.connection() as connection,
                connection.transaction(),
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(PURGE_EXPIRED_CIVIC_SCOPE_GAP_TEXT_SQL, ())
                rows = await cursor.fetchall()
                result = self._purge_result(rows)
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc
        return result

    async def claim_chat_idempotency(
        self,
        *,
        idempotency_key: UUID,
        request_fingerprint: str,
        claim_token: UUID,
    ) -> IdempotencyClaim:
        valid_key = _require_uuid(idempotency_key, "IDEMPOTENCY_KEY_INVALID")
        valid_digest = _require_idempotency_digest(request_fingerprint)
        valid_claim_token = _require_uuid(claim_token, "CLAIM_TOKEN_INVALID")
        try:
            async with (
                self._pool.connection() as connection,
                connection.transaction(),
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(
                    CLAIM_CHAT_IDEMPOTENCY_SQL,
                    (valid_key, valid_digest, valid_claim_token),
                )
                rows = await cursor.fetchall()
                result = self._idempotency_claim(rows)
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc
        return result

    async def complete_chat_idempotency(
        self,
        *,
        idempotency_key: UUID,
        request_fingerprint: str,
        claim_token: UUID,
        response_payload: dict[str, object],
    ) -> None:
        valid_key = _require_uuid(idempotency_key, "IDEMPOTENCY_KEY_INVALID")
        valid_digest = _require_idempotency_digest(request_fingerprint)
        valid_claim_token = _require_uuid(claim_token, "CLAIM_TOKEN_INVALID")
        valid_response = _require_safe_response_json(response_payload)
        await self._execute_void_write(
            COMPLETE_CHAT_IDEMPOTENCY_SQL,
            (valid_key, valid_digest, valid_claim_token, Jsonb(valid_response)),
        )

    async def commit_chat_idempotency(
        self,
        *,
        idempotency_key: UUID,
        request_fingerprint: str,
        claim_token: UUID,
        response_payload: dict[str, object],
        interaction: InteractionWrite | None,
    ) -> None:
        valid_key = _require_uuid(idempotency_key, "IDEMPOTENCY_KEY_INVALID")
        valid_digest = _require_idempotency_digest(request_fingerprint)
        valid_claim_token = _require_uuid(claim_token, "CLAIM_TOKEN_INVALID")
        valid_response = _require_safe_response_json(response_payload)
        if interaction is not None and type(interaction) is not InteractionWrite:
            raise ValueError("INTERACTION_INVALID")
        try:
            async with (
                self._pool.connection() as connection,
                connection.transaction(),
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                if interaction is not None:
                    await cursor.execute(
                        RECORD_INTERACTION_SQL,
                        self._interaction_parameters(interaction),
                    )
                    self._interaction_result(await cursor.fetchall())
                await cursor.execute(
                    COMPLETE_CHAT_IDEMPOTENCY_SQL,
                    (valid_key, valid_digest, valid_claim_token, Jsonb(valid_response)),
                )
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc

    async def abandon_chat_idempotency(
        self,
        *,
        idempotency_key: UUID,
        request_fingerprint: str,
        claim_token: UUID,
    ) -> None:
        valid_key = _require_uuid(idempotency_key, "IDEMPOTENCY_KEY_INVALID")
        valid_digest = _require_idempotency_digest(request_fingerprint)
        valid_claim_token = _require_uuid(claim_token, "CLAIM_TOKEN_INVALID")
        await self._execute_void_write(
            ABANDON_CHAT_IDEMPOTENCY_SQL,
            (valid_key, valid_digest, valid_claim_token),
        )

    async def purge_expired_chat_idempotency(self) -> PurgeResult:
        try:
            async with (
                self._pool.connection() as connection,
                connection.transaction(),
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(PURGE_EXPIRED_CHAT_IDEMPOTENCY_SQL, ())
                rows = await cursor.fetchall()
                result = self._purge_result(rows)
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc
        return result

    async def _execute_void_write(self, sql: str, parameters: tuple[object, ...]) -> None:
        try:
            async with (
                self._pool.connection() as connection,
                connection.transaction(),
                connection.cursor(row_factory=dict_row) as cursor,
            ):
                await cursor.execute(sql, parameters)
        except psycopg.Error as exc:
            raise map_database_error(exc) from exc

    @staticmethod
    def _interaction_parameters(event: InteractionWrite) -> tuple[object, ...]:
        return (
            event.request_id,
            event.intent.value,
            event.answer_status.value,
            event.fallback_reason.value if event.fallback_reason is not None else None,
            list(event.used_source_ids),
            event.response_time_ms,
            event.selected_region.value if event.selected_region is not None else None,
            event.routed_office_public_id,
            event.is_test,
            event.masked_question,
        )

    @staticmethod
    def _single_row(
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if len(rows) != 1:
            raise DatabaseUnavailableError()
        return rows[0]

    @classmethod
    def _interaction_result(cls, rows: list[dict[str, Any]]) -> InteractionWriteResult:
        try:
            row = cls._single_row(rows)
            return InteractionWriteResult(
                interaction_id=_required_uuid(row["interaction_id"]),
                failed_question_id=_optional_uuid(row["failed_question_id"]),
            )
        except (KeyError, TypeError, ValueError):
            raise DatabaseUnavailableError() from None

    @classmethod
    def _scalar_uuid(cls, rows: list[dict[str, Any]], key: str) -> UUID:
        try:
            return _required_uuid(cls._single_row(rows)[key])
        except (KeyError, TypeError, ValueError):
            raise DatabaseUnavailableError() from None

    @classmethod
    def _scalar_text(cls, rows: list[dict[str, Any]], key: str) -> str:
        try:
            return _required_text(cls._single_row(rows)[key])
        except (KeyError, TypeError, ValueError):
            raise DatabaseUnavailableError() from None

    @classmethod
    def _purge_result(cls, rows: list[dict[str, Any]]) -> PurgeResult:
        try:
            row = cls._single_row(rows)
            purged_count = row["purged_count"]
            if type(purged_count) is not int:
                raise ValueError("MALFORMED_DATABASE_RESULT")
            return PurgeResult(
                purged_count=purged_count,
                purged_ids=_uuid_array(row["purged_ids"]),
            )
        except (KeyError, TypeError, ValueError):
            raise DatabaseUnavailableError() from None

    @classmethod
    def _idempotency_claim(cls, rows: list[dict[str, Any]]) -> IdempotencyClaim:
        try:
            row = cls._single_row(rows)
            raw_response = row["response_json"]
            response = None
            if raw_response is not None:
                response = _require_safe_response_json(raw_response)
            return IdempotencyClaim(
                status=IdempotencyClaimStatus(_required_text(row["disposition"])),
                response_payload=response,
            )
        except (KeyError, TypeError, ValueError):
            raise DatabaseUnavailableError() from None
