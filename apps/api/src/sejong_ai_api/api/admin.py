"""Disabled-by-default local/private administrator HTTP adapter."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, Request, status
from fastapi.responses import JSONResponse

from sejong_ai_api.admin.service import AdminService, AdminServiceError
from sejong_ai_api.contracts.admin import (
    AdminErrorEnvelope,
    CandidateReviewRequest,
    CivicScopeGapListResponse,
    CivicScopeGapReviewRequest,
    CivicScopeGapReviewResponse,
    FailedQuestionDetailResponse,
    FailedQuestionListResponse,
    KBCandidateCreateRequest,
    KBCandidateCreateResponse,
    KBCandidateListResponse,
    KBCandidateReviewResponse,
    KBCandidateSubmitResponse,
    ReasonConfirmationRequest,
    ReasonConfirmationResponse,
)
from sejong_ai_api.db.models import Actor, AdminRole

_ERROR_STATUS = {
    "ADMIN_ROUTE_DISABLED": status.HTTP_403_FORBIDDEN,
    "ADMIN_FORBIDDEN": status.HTTP_403_FORBIDDEN,
    "ADMIN_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "ADMIN_INVALID_STATE": status.HTTP_409_CONFLICT,
    "ADMIN_VALIDATION_FAILED": status.HTTP_422_UNPROCESSABLE_CONTENT,
}
_ERROR_MESSAGE = {
    "ADMIN_ROUTE_DISABLED": "관리자 기능을 사용할 수 없습니다.",
    "ADMIN_FORBIDDEN": "이 작업을 수행할 권한이 없습니다.",
    "ADMIN_NOT_FOUND": "대상을 찾을 수 없습니다.",
    "ADMIN_INVALID_STATE": "현재 상태에서는 이 작업을 수행할 수 없습니다.",
    "ADMIN_VALIDATION_FAILED": "입력값을 확인해 주세요.",
}
_ALLOWED_DEMO_ACTORS = frozenset(
    {
        ("OPERATOR-LOCAL-001", AdminRole.OPERATOR),
        ("PM-LOCAL-001", AdminRole.APPROVER),
    }
)


def get_admin_enabled() -> bool:
    """Keep every admin route closed until local composition opts in."""
    return False


def get_admin_service() -> AdminService | None:
    """Keep DB access absent until a local-only composition supplies it."""
    return None


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _request_id(request: Request) -> UUID:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, UUID) else uuid4()


def _error_response(request: Request, code: str) -> JSONResponse:
    envelope = AdminErrorEnvelope.model_validate(
        {
            "error": {
                "code": code,
                "message": _ERROR_MESSAGE[code],
                "request_id": _request_id(request),
                "retryable": False,
            }
        }
    )
    return JSONResponse(
        status_code=_ERROR_STATUS[code],
        content=envelope.model_dump(mode="json"),
    )


def _resolve_context(
    request: Request,
    *,
    enabled: bool,
    service: AdminService | None,
    actor_id: str,
    role: str,
) -> tuple[AdminService, Actor] | JSONResponse:
    if not enabled or service is None:
        return _error_response(request, "ADMIN_ROUTE_DISABLED")
    try:
        actor = Actor(actor_id=actor_id, role=AdminRole(role))
    except ValueError:
        return _error_response(request, "ADMIN_FORBIDDEN")
    if (actor.actor_id, actor.role) not in _ALLOWED_DEMO_ACTORS:
        return _error_response(request, "ADMIN_FORBIDDEN")
    return service, actor


def _service_error(request: Request, error: AdminServiceError) -> JSONResponse:
    return _error_response(request, error.code)


AdminEnabled = Annotated[bool, Depends(get_admin_enabled)]
AdminServiceDependency = Annotated[AdminService | None, Depends(get_admin_service)]
ActorIdHeader = Annotated[str, Header(alias="X-Demo-Actor-Id")]
RoleHeader = Annotated[str, Header(alias="X-Demo-Role")]


@router.get(
    "/failed-questions",
    response_model=FailedQuestionListResponse,
    operation_id="listFailedQuestions",
    responses={403: {"model": AdminErrorEnvelope}},
)
async def list_failed_questions(
    request: Request,
    enabled: AdminEnabled,
    service: AdminServiceDependency,
    actor_id: ActorIdHeader,
    role: RoleHeader,
    reason: Annotated[str | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> FailedQuestionListResponse | JSONResponse:
    context = _resolve_context(
        request, enabled=enabled, service=service, actor_id=actor_id, role=role
    )
    if isinstance(context, JSONResponse):
        return context
    resolved_service, actor = context
    try:
        return await resolved_service.list_failed_questions(
            actor,
            reason=reason,
            status=status_filter,
        )
    except AdminServiceError as error:
        return _service_error(request, error)


@router.get(
    "/failed-questions/{id}",
    response_model=FailedQuestionDetailResponse,
    operation_id="getFailedQuestion",
    responses={
        403: {"model": AdminErrorEnvelope},
        404: {"model": AdminErrorEnvelope},
    },
)
async def get_failed_question(
    request: Request,
    id: UUID,
    enabled: AdminEnabled,
    service: AdminServiceDependency,
    actor_id: ActorIdHeader,
    role: RoleHeader,
) -> FailedQuestionDetailResponse | JSONResponse:
    context = _resolve_context(
        request, enabled=enabled, service=service, actor_id=actor_id, role=role
    )
    if isinstance(context, JSONResponse):
        return context
    resolved_service, actor = context
    try:
        return await resolved_service.get_failed_question(actor, id)
    except AdminServiceError as error:
        return _service_error(request, error)


@router.patch(
    "/failed-questions/{id}/reason",
    response_model=ReasonConfirmationResponse,
    operation_id="confirmFallbackReason",
    responses={
        403: {"model": AdminErrorEnvelope},
        404: {"model": AdminErrorEnvelope},
        409: {"model": AdminErrorEnvelope},
        422: {"model": AdminErrorEnvelope},
    },
)
async def confirm_fallback_reason(
    request: Request,
    id: UUID,
    payload: ReasonConfirmationRequest,
    enabled: AdminEnabled,
    service: AdminServiceDependency,
    actor_id: ActorIdHeader,
    role: RoleHeader,
) -> ReasonConfirmationResponse | JSONResponse:
    context = _resolve_context(
        request, enabled=enabled, service=service, actor_id=actor_id, role=role
    )
    if isinstance(context, JSONResponse):
        return context
    resolved_service, actor = context
    try:
        return await resolved_service.confirm_reason(actor, id, payload)
    except AdminServiceError as error:
        return _service_error(request, error)


@router.get(
    "/civic-scope-gaps",
    response_model=CivicScopeGapListResponse,
    operation_id="listCivicScopeGaps",
    responses={
        403: {"model": AdminErrorEnvelope},
        422: {"model": AdminErrorEnvelope},
    },
)
async def list_civic_scope_gaps(
    request: Request,
    enabled: AdminEnabled,
    service: AdminServiceDependency,
    actor_id: ActorIdHeader,
    role: RoleHeader,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> CivicScopeGapListResponse | JSONResponse:
    context = _resolve_context(
        request, enabled=enabled, service=service, actor_id=actor_id, role=role
    )
    if isinstance(context, JSONResponse):
        return context
    resolved_service, actor = context
    try:
        return await resolved_service.list_civic_scope_gaps(
            actor,
            status=status_filter,
        )
    except AdminServiceError as error:
        return _service_error(request, error)


@router.patch(
    "/civic-scope-gaps/{id}/review",
    response_model=CivicScopeGapReviewResponse,
    operation_id="reviewCivicScopeGap",
    responses={
        403: {"model": AdminErrorEnvelope},
        404: {"model": AdminErrorEnvelope},
        409: {"model": AdminErrorEnvelope},
        422: {"model": AdminErrorEnvelope},
    },
)
async def review_civic_scope_gap(
    request: Request,
    id: UUID,
    payload: CivicScopeGapReviewRequest,
    enabled: AdminEnabled,
    service: AdminServiceDependency,
    actor_id: ActorIdHeader,
    role: RoleHeader,
) -> CivicScopeGapReviewResponse | JSONResponse:
    context = _resolve_context(
        request, enabled=enabled, service=service, actor_id=actor_id, role=role
    )
    if isinstance(context, JSONResponse):
        return context
    resolved_service, actor = context
    try:
        return await resolved_service.review_civic_scope_gap(actor, id, payload)
    except AdminServiceError as error:
        return _service_error(request, error)


@router.get(
    "/kb-candidates",
    response_model=KBCandidateListResponse,
    operation_id="listKBCandidates",
    responses={403: {"model": AdminErrorEnvelope}},
)
async def list_kb_candidates(
    request: Request,
    enabled: AdminEnabled,
    service: AdminServiceDependency,
    actor_id: ActorIdHeader,
    role: RoleHeader,
) -> KBCandidateListResponse | JSONResponse:
    context = _resolve_context(
        request, enabled=enabled, service=service, actor_id=actor_id, role=role
    )
    if isinstance(context, JSONResponse):
        return context
    resolved_service, actor = context
    try:
        return await resolved_service.list_candidates(actor)
    except AdminServiceError as error:
        return _service_error(request, error)


@router.post(
    "/kb-candidates",
    response_model=KBCandidateCreateResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="createKBCandidate",
    responses={
        403: {"model": AdminErrorEnvelope},
        409: {"model": AdminErrorEnvelope},
        422: {"model": AdminErrorEnvelope},
    },
)
async def create_kb_candidate(
    request: Request,
    payload: KBCandidateCreateRequest,
    enabled: AdminEnabled,
    service: AdminServiceDependency,
    actor_id: ActorIdHeader,
    role: RoleHeader,
) -> KBCandidateCreateResponse | JSONResponse:
    context = _resolve_context(
        request, enabled=enabled, service=service, actor_id=actor_id, role=role
    )
    if isinstance(context, JSONResponse):
        return context
    resolved_service, actor = context
    try:
        return await resolved_service.create_candidate(actor, payload)
    except AdminServiceError as error:
        return _service_error(request, error)


@router.post(
    "/kb-candidates/{id}/submit",
    response_model=KBCandidateSubmitResponse,
    operation_id="submitKBCandidate",
    responses={
        403: {"model": AdminErrorEnvelope},
        404: {"model": AdminErrorEnvelope},
        409: {"model": AdminErrorEnvelope},
    },
)
async def submit_kb_candidate(
    request: Request,
    id: UUID,
    enabled: AdminEnabled,
    service: AdminServiceDependency,
    actor_id: ActorIdHeader,
    role: RoleHeader,
) -> KBCandidateSubmitResponse | JSONResponse:
    context = _resolve_context(
        request, enabled=enabled, service=service, actor_id=actor_id, role=role
    )
    if isinstance(context, JSONResponse):
        return context
    resolved_service, actor = context
    try:
        return await resolved_service.submit_candidate(actor, id)
    except AdminServiceError as error:
        return _service_error(request, error)


@router.patch(
    "/kb-candidates/{id}/review",
    response_model=KBCandidateReviewResponse,
    operation_id="reviewKBCandidate",
    responses={
        403: {"model": AdminErrorEnvelope},
        404: {"model": AdminErrorEnvelope},
        409: {"model": AdminErrorEnvelope},
        422: {"model": AdminErrorEnvelope},
    },
)
async def review_kb_candidate(
    request: Request,
    id: UUID,
    payload: CandidateReviewRequest,
    enabled: AdminEnabled,
    service: AdminServiceDependency,
    actor_id: ActorIdHeader,
    role: RoleHeader,
) -> KBCandidateReviewResponse | JSONResponse:
    context = _resolve_context(
        request, enabled=enabled, service=service, actor_id=actor_id, role=role
    )
    if isinstance(context, JSONResponse):
        return context
    resolved_service, actor = context
    try:
        return await resolved_service.review_candidate(actor, id, payload)
    except AdminServiceError as error:
        return _service_error(request, error)


__all__ = ["get_admin_enabled", "get_admin_service", "router"]
