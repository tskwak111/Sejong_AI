"""Fail-closed local/private administrator workflow orchestration."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Sequence
from typing import Literal, Protocol, TypeVar
from urllib.parse import SplitResult, parse_qsl, unquote, urlsplit
from uuid import UUID

from sejong_ai_api.admin.candidate_binding import (
    RESERVED_KB_PUBLIC_ID,
    claims_reserved_binding,
    is_exact_reserved_candidate,
)
from sejong_ai_api.contracts.admin import (
    CandidateReviewRequest,
    CivicScopeGapListResponse,
    CivicScopeGapReviewRequest,
    CivicScopeGapReviewResponse,
    CivicScopeGapSummary,
    FailedQuestion,
    FailedQuestionDetailResponse,
    FailedQuestionListResponse,
    KBCandidateCreateRequest,
    KBCandidateCreateResponse,
    KBCandidateListResponse,
    KBCandidateReviewResponse,
    KBCandidateSubmitResponse,
    KBCandidateSummary,
    ReasonConfirmationRequest,
    ReasonConfirmationResponse,
)
from sejong_ai_api.db.errors import (
    DatabaseRuleCode,
    DatabaseRuleError,
    DatabaseUnavailableError,
)
from sejong_ai_api.db.models import (
    Actor,
    AdminRole,
    CandidateDraft,
    DataOrigin,
    FallbackReason,
    Intent,
    PurgeResult,
)
from sejong_ai_api.privacy import redact_question

type AdminErrorCode = Literal[
    "ADMIN_ROUTE_DISABLED",
    "ADMIN_FORBIDDEN",
    "ADMIN_NOT_FOUND",
    "ADMIN_INVALID_STATE",
    "ADMIN_VALIDATION_FAILED",
]

_FAILURE_REASONS = frozenset({"INSUFFICIENT_GROUNDING", "PERSONAL_LOOKUP", "LEGAL_JUDGMENT"})
_FAILURE_STATUSES = frozenset({"NEW", "REASON_CONFIRMED"})
_CIVIC_SCOPE_GAP_STATUSES = frozenset({"NEW", "PLANNED", "DISMISSED"})
_SENSITIVE_SOURCE_QUERY_KEYS = frozenset(
    {
        "account",
        "api_key",
        "apikey",
        "auth",
        "card",
        "email",
        "jumin",
        "mobile",
        "name",
        "password",
        "passwd",
        "phone",
        "pin",
        "pwd",
        "resident",
        "rrn",
        "secret",
        "token",
        "user",
        "username",
    }
)
_APPROVED_SOURCE_HOSTS = frozenset(
    {
        "www.sejong.go.kr",
        "plus.gov.kr",
        "www.gov.kr",
        "www.law.go.kr",
        "www.wetax.go.kr",
        "www.sjwaste.kr",
    }
)
_TECHNICAL_SOURCE_QUERY_PATTERNS = {
    "srvcid": re.compile(r"13\d{9}"),
    "cappbizcd": re.compile(r"13\d{9}"),
    "typesn": re.compile(r"\d{2}"),
    "tp_seq": re.compile(r"\d{2}"),
    "highctgcd": re.compile(r"[A-Z]\d{5}"),
    "lsid": re.compile(r"\d{6}"),
    "urlmode": re.compile(r"lsInfoP"),
    "menuid": re.compile(r"MENU\d{5}"),
    "siteid": re.compile(r"null"),
}
_MAX_SOURCE_URL_LENGTH = 1000
_MAX_SOURCE_URL_PERCENT_DECODING_PASSES = 4
_PERCENT_ENCODED_OCTET = re.compile(r"%[0-9A-Fa-f]{2}")
_TECHNICAL_SOURCE_PATH_SUFFIX = ".do"


class AdminServiceError(Exception):
    """Stable value-free application error translated by the HTTP adapter."""

    def __init__(self, code: AdminErrorCode) -> None:
        self.code = code
        super().__init__("ADMIN_OPERATION_REJECTED")


class AdminRepository(Protocol):
    """Admin read port plus the existing constrained DB write capabilities."""

    async def list_failed_questions(
        self, *, reason: str | None, status: str | None
    ) -> Sequence[FailedQuestion]: ...

    async def get_failed_question(self, failed_question_id: UUID) -> FailedQuestion | None: ...

    async def list_kb_candidates(self) -> Sequence[KBCandidateSummary]: ...

    async def get_kb_candidate(self, candidate_id: UUID) -> KBCandidateSummary | None: ...

    async def purge_expired_failed_question_text(self) -> PurgeResult: ...

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


T = TypeVar("T")


class AdminService:
    """Enforce role and workflow rules before the DB enforces them again."""

    def __init__(self, repository: AdminRepository) -> None:
        self._repository = repository

    async def list_failed_questions(
        self,
        actor: Actor,
        *,
        reason: str | None,
        status: str | None,
    ) -> FailedQuestionListResponse:
        self._require_admin(actor)
        if reason is not None and reason not in _FAILURE_REASONS:
            raise AdminServiceError("ADMIN_VALIDATION_FAILED")
        if status is not None and status not in _FAILURE_STATUSES:
            raise AdminServiceError("ADMIN_VALIDATION_FAILED")
        await self._safe_call(self._repository.purge_expired_failed_question_text)
        items = await self._safe_call(
            lambda: self._repository.list_failed_questions(reason=reason, status=status)
        )
        return FailedQuestionListResponse(items=list(items), total=len(items))

    async def get_failed_question(
        self,
        actor: Actor,
        failed_question_id: UUID,
    ) -> FailedQuestionDetailResponse:
        self._require_admin(actor)
        await self._safe_call(self._repository.purge_expired_failed_question_text)
        item = await self._safe_call(
            lambda: self._repository.get_failed_question(failed_question_id)
        )
        if item is None:
            raise AdminServiceError("ADMIN_NOT_FOUND")
        return FailedQuestionDetailResponse(item=item)

    async def confirm_reason(
        self,
        actor: Actor,
        failed_question_id: UUID,
        payload: ReasonConfirmationRequest,
    ) -> ReasonConfirmationResponse:
        self._require_role(actor, AdminRole.OPERATOR)
        current = await self._get_failure_for_change(failed_question_id)
        if current.status != "NEW":
            raise AdminServiceError("ADMIN_INVALID_STATE")
        fallback_reason = FallbackReason(payload.reason)
        await self._safe_call(
            lambda: self._repository.confirm_failed_question_reason(
                failed_question_id,
                actor,
                fallback_reason,
            )
        )
        return ReasonConfirmationResponse(id=failed_question_id, status="REASON_CONFIRMED")

    async def list_candidates(self, actor: Actor) -> KBCandidateListResponse:
        self._require_admin(actor)
        items = await self._safe_call(self._repository.list_kb_candidates)
        return KBCandidateListResponse(items=list(items), total=len(items))

    async def list_civic_scope_gaps(
        self,
        actor: Actor,
        *,
        status: str | None,
    ) -> CivicScopeGapListResponse:
        self._require_admin(actor)
        if status is not None and status not in _CIVIC_SCOPE_GAP_STATUSES:
            raise AdminServiceError("ADMIN_VALIDATION_FAILED")
        await self._safe_call(self._repository.purge_expired_civic_scope_gap_text)
        items = await self._safe_call(
            lambda: self._repository.list_civic_scope_gaps(status=status)
        )
        return CivicScopeGapListResponse(items=list(items), total=len(items))

    async def review_civic_scope_gap(
        self,
        actor: Actor,
        scope_gap_id: UUID,
        payload: CivicScopeGapReviewRequest,
    ) -> CivicScopeGapReviewResponse:
        self._require_role(actor, AdminRole.APPROVER)
        items = await self._safe_call(
            lambda: self._repository.list_civic_scope_gaps(status=None)
        )
        item = next((candidate for candidate in items if candidate.id == scope_gap_id), None)
        if item is None:
            raise AdminServiceError("ADMIN_NOT_FOUND")
        if item.status != "NEW":
            raise AdminServiceError("ADMIN_INVALID_STATE")
        await self._safe_call(
            lambda: self._repository.review_civic_scope_gap(
                scope_gap_id,
                actor,
                payload.decision,
                payload.review_comment,
            )
        )
        return CivicScopeGapReviewResponse(id=scope_gap_id, status=payload.decision)

    async def create_candidate(
        self,
        actor: Actor,
        payload: KBCandidateCreateRequest,
    ) -> KBCandidateCreateResponse:
        self._require_role(actor, AdminRole.OPERATOR)
        failure = await self._get_failure_for_change(payload.failed_question_id)
        if (
            failure.status != "REASON_CONFIRMED"
            or failure.fallback_reason != "INSUFFICIENT_GROUNDING"
            or not failure.candidate_eligible
        ):
            raise AdminServiceError("ADMIN_INVALID_STATE")
        self._require_privacy_safe_candidate(payload)
        try:
            draft = CandidateDraft(
                failed_question_id=payload.failed_question_id,
                actor=actor,
                title=payload.title,
                representative_question=payload.representative_question,
                category=Intent(payload.category),
                answer_summary=payload.answer_summary,
                procedure_steps=tuple(payload.procedure_steps),
                required_documents=tuple(payload.required_documents),
                processing_time=payload.processing_time,
                fee=payload.fee,
                department=payload.department,
                source_title=payload.source_title,
                source_url=str(payload.source_url),
                last_verified_at=payload.last_verified_at,
                caution=payload.caution,
                data_origin=DataOrigin.OFFICIAL,
            )
        except ValueError:
            raise AdminServiceError("ADMIN_VALIDATION_FAILED") from None
        candidate_id = await self._safe_call(lambda: self._repository.create_kb_candidate(draft))
        return KBCandidateCreateResponse(id=candidate_id, status="DRAFTED")

    async def submit_candidate(
        self,
        actor: Actor,
        candidate_id: UUID,
    ) -> KBCandidateSubmitResponse:
        self._require_role(actor, AdminRole.OPERATOR)
        candidate = await self._get_candidate_for_change(candidate_id)
        if candidate.status != "DRAFTED":
            raise AdminServiceError("ADMIN_INVALID_STATE")
        if candidate.created_by != actor.actor_id:
            raise AdminServiceError("ADMIN_FORBIDDEN")
        await self._safe_call(lambda: self._repository.submit_kb_candidate(candidate_id, actor))
        return KBCandidateSubmitResponse(id=candidate_id, status="PENDING_APPROVAL")

    async def review_candidate(
        self,
        actor: Actor,
        candidate_id: UUID,
        payload: CandidateReviewRequest,
    ) -> KBCandidateReviewResponse:
        self._require_role(actor, AdminRole.APPROVER)
        candidate = await self._get_candidate_for_change(candidate_id)
        if candidate.status != "PENDING_APPROVAL":
            raise AdminServiceError("ADMIN_INVALID_STATE")
        reserved_binding = claims_reserved_binding(candidate)
        if (
            payload.decision == "APPROVED"
            and reserved_binding
            and not is_exact_reserved_candidate(candidate)
        ):
            raise AdminServiceError("ADMIN_VALIDATION_FAILED")
        if candidate.created_by == actor.actor_id:
            raise AdminServiceError("ADMIN_FORBIDDEN")
        if payload.decision == "APPROVED":
            if reserved_binding:
                await self._safe_call(
                    lambda: self._repository.approve_kb_candidate_with_public_id(
                        candidate_id,
                        actor,
                        payload.review_comment,
                        RESERVED_KB_PUBLIC_ID,
                    )
                )
            else:
                await self._safe_call(
                    lambda: self._repository.approve_kb_candidate(
                        candidate_id,
                        actor,
                        payload.review_comment,
                    )
                )
        else:
            await self._safe_call(
                lambda: self._repository.reject_kb_candidate(
                    candidate_id,
                    actor,
                    payload.review_comment,
                )
            )
        return KBCandidateReviewResponse(id=candidate_id, status=payload.decision)

    async def _get_failure_for_change(self, failed_question_id: UUID) -> FailedQuestion:
        item = await self._safe_call(
            lambda: self._repository.get_failed_question(failed_question_id)
        )
        if item is None:
            raise AdminServiceError("ADMIN_NOT_FOUND")
        return item

    async def _get_candidate_for_change(self, candidate_id: UUID) -> KBCandidateSummary:
        item = await self._safe_call(lambda: self._repository.get_kb_candidate(candidate_id))
        if item is None:
            raise AdminServiceError("ADMIN_NOT_FOUND")
        return item

    @staticmethod
    def _require_admin(actor: Actor) -> None:
        if type(actor) is not Actor or actor.role not in {
            AdminRole.OPERATOR,
            AdminRole.APPROVER,
        }:
            raise AdminServiceError("ADMIN_FORBIDDEN")

    @staticmethod
    def _require_role(actor: Actor, role: AdminRole) -> None:
        if type(actor) is not Actor or actor.role is not role:
            raise AdminServiceError("ADMIN_FORBIDDEN")

    @staticmethod
    def _require_privacy_safe_candidate(payload: KBCandidateCreateRequest) -> None:
        values = (
            payload.title,
            payload.representative_question,
            payload.answer_summary,
            *payload.procedure_steps,
            *payload.required_documents,
            payload.processing_time,
            payload.fee,
            payload.department,
            payload.source_title,
            payload.caution,
        )
        for value in values:
            if value is None:
                continue
            result = redact_question(value)
            if result.masked_text is None or result.masked_text != value or result.findings:
                raise AdminServiceError("ADMIN_VALIDATION_FAILED")
        AdminService._require_privacy_safe_source_url(str(payload.source_url))

    @staticmethod
    def _require_privacy_safe_source_url(value: str) -> None:
        try:
            if len(value) > _MAX_SOURCE_URL_LENGTH:
                raise ValueError
            AdminService._parse_approved_source_url(value)
            decoded = value
            for _ in range(_MAX_SOURCE_URL_PERCENT_DECODING_PASSES):
                next_decoded = unquote(decoded)
                if next_decoded == decoded:
                    if _PERCENT_ENCODED_OCTET.search(decoded):
                        raise ValueError
                    break
                decoded = next_decoded
            else:
                raise ValueError
            if len(decoded) > _MAX_SOURCE_URL_LENGTH:
                raise ValueError
            parsed = AdminService._parse_approved_source_url(decoded)
            path_to_scan = parsed.path
            if path_to_scan.endswith(_TECHNICAL_SOURCE_PATH_SUFFIX):
                path_to_scan = path_to_scan[: -len(_TECHNICAL_SOURCE_PATH_SUFFIX)]
            if path_to_scan:
                AdminService._require_privacy_safe_source_url_component(path_to_scan)
            for key, query_value in parse_qsl(parsed.query, keep_blank_values=True):
                AdminService._require_privacy_safe_source_url_component(key)
                normalized_key = key.casefold()
                if normalized_key in _SENSITIVE_SOURCE_QUERY_KEYS:
                    raise ValueError
                technical_pattern = _TECHNICAL_SOURCE_QUERY_PATTERNS.get(normalized_key)
                if technical_pattern is not None:
                    if technical_pattern.fullmatch(query_value) is None:
                        raise ValueError
                    continue
                AdminService._require_privacy_safe_source_url_component(query_value)
        except (TypeError, ValueError):
            raise AdminServiceError("ADMIN_VALIDATION_FAILED") from None

    @staticmethod
    def _parse_approved_source_url(value: str) -> SplitResult:
        parsed = urlsplit(value)
        hostname = (parsed.hostname or "").rstrip(".").casefold()
        if (
            parsed.scheme.casefold() != "https"
            or hostname not in _APPROVED_SOURCE_HOSTS
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in {None, 443}
            or bool(parsed.fragment)
        ):
            raise ValueError
        return parsed

    @staticmethod
    def _require_privacy_safe_source_url_component(value: str) -> None:
        result = redact_question(value)
        if result.masked_text is None or result.masked_text != value or result.findings:
            raise ValueError

    @staticmethod
    async def _safe_call(operation: Callable[[], Awaitable[T]]) -> T:
        try:
            return await operation()
        except DatabaseRuleError as exc:
            if exc.code in {
                DatabaseRuleCode.FORBIDDEN_ACTOR_ROLE,
                DatabaseRuleCode.SELF_APPROVAL,
            }:
                raise AdminServiceError("ADMIN_FORBIDDEN") from None
            if exc.code in {
                DatabaseRuleCode.INCOMPLETE_CANDIDATE,
                DatabaseRuleCode.DISALLOWED_ORIGIN,
            }:
                raise AdminServiceError("ADMIN_VALIDATION_FAILED") from None
            raise AdminServiceError("ADMIN_INVALID_STATE") from None
        except DatabaseUnavailableError:
            raise AdminServiceError("ADMIN_INVALID_STATE") from None


__all__ = ["AdminRepository", "AdminService", "AdminServiceError"]
