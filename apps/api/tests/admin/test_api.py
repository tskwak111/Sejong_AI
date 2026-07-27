from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import ValidationError

from sejong_ai_api.admin.service import AdminServiceError
from sejong_ai_api.api.admin import (
    get_admin_enabled,
    get_admin_service,
    router,
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
    ReasonConfirmationRequest,
    ReasonConfirmationResponse,
)
from sejong_ai_api.db.models import Actor, AdminRole

REQUEST_ID = UUID("11111111-1111-4111-8111-111111111111")
FAILED_ID = UUID("10000000-0000-4000-8000-000000000001")
CANDIDATE_ID = UUID("20000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 7, 22, 3, 0, tzinfo=UTC)
SCOPE_GAP_ID = UUID("68000000-0000-4000-8000-000000000001")


def failure() -> FailedQuestion:
    return FailedQuestion(
        id=FAILED_ID,
        masked_question="침대 프레임 수수료를 알려 주세요.",
        intent="BULKY_WASTE",
        fallback_reason="INSUFFICIENT_GROUNDING",
        candidate_eligible=True,
        status="NEW",
        created_at=NOW,
        text_expires_at=NOW + timedelta(days=30),
        text_purged_at=None,
    )


class RouteService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Actor]] = []
        self.created_payloads: list[KBCandidateCreateRequest] = []
        self.error: AdminServiceError | None = None

    def _record(self, name: str, actor: Actor) -> None:
        self.calls.append((name, actor))
        if self.error is not None:
            raise self.error

    async def list_failed_questions(
        self, actor: Actor, *, reason: str | None, status: str | None
    ) -> FailedQuestionListResponse:
        del reason, status
        self._record("list_failed_questions", actor)
        return FailedQuestionListResponse(items=[failure()], total=1)

    async def get_failed_question(
        self, actor: Actor, failed_question_id: UUID
    ) -> FailedQuestionDetailResponse:
        del failed_question_id
        self._record("get_failed_question", actor)
        return FailedQuestionDetailResponse(item=failure())

    async def confirm_reason(
        self,
        actor: Actor,
        failed_question_id: UUID,
        payload: ReasonConfirmationRequest,
    ) -> ReasonConfirmationResponse:
        del failed_question_id, payload
        self._record("confirm_reason", actor)
        return ReasonConfirmationResponse(id=FAILED_ID, status="REASON_CONFIRMED")

    async def list_candidates(self, actor: Actor) -> KBCandidateListResponse:
        self._record("list_candidates", actor)
        return KBCandidateListResponse(items=[], total=0)

    async def list_civic_scope_gaps(
        self, actor: Actor, *, status: str | None
    ) -> CivicScopeGapListResponse:
        del status
        self._record("list_civic_scope_gaps", actor)
        return CivicScopeGapListResponse(
            items=[
                CivicScopeGapSummary(
                    id=SCOPE_GAP_ID,
                    masked_question="합성 범위 부족 민원",
                    status="NEW",
                    created_at=NOW,
                    updated_at=NOW,
                    text_expires_at=NOW + timedelta(days=30),
                    text_purged_at=None,
                    reviewed_by=None,
                    reviewed_at=None,
                    review_comment=None,
                )
            ],
            total=1,
        )

    async def review_civic_scope_gap(
        self,
        actor: Actor,
        scope_gap_id: UUID,
        payload: CivicScopeGapReviewRequest,
    ) -> CivicScopeGapReviewResponse:
        del scope_gap_id
        self._record("review_civic_scope_gap", actor)
        return CivicScopeGapReviewResponse(id=SCOPE_GAP_ID, status=payload.decision)

    async def create_candidate(
        self, actor: Actor, payload: KBCandidateCreateRequest
    ) -> KBCandidateCreateResponse:
        self._record("create_candidate", actor)
        self.created_payloads.append(payload)
        return KBCandidateCreateResponse(id=CANDIDATE_ID, status="DRAFTED")

    async def submit_candidate(self, actor: Actor, candidate_id: UUID) -> KBCandidateSubmitResponse:
        del candidate_id
        self._record("submit_candidate", actor)
        return KBCandidateSubmitResponse(id=CANDIDATE_ID, status="PENDING_APPROVAL")

    async def review_candidate(
        self,
        actor: Actor,
        candidate_id: UUID,
        payload: CandidateReviewRequest,
    ) -> KBCandidateReviewResponse:
        del candidate_id
        self._record("review_candidate", actor)
        return KBCandidateReviewResponse(id=CANDIDATE_ID, status=payload.decision)


def application(*, enabled: bool, service: RouteService | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):  # type: ignore[no-untyped-def]
        request.state.request_id = REQUEST_ID
        return await call_next(request)

    app.dependency_overrides[get_admin_enabled] = lambda: enabled
    if service is not None:
        app.dependency_overrides[get_admin_service] = lambda: service
    return app


def headers(*, actor_id: str = "OPERATOR-LOCAL-001", role: str = "OPERATOR") -> dict[str, str]:
    return {"X-Demo-Actor-Id": actor_id, "X-Demo-Role": role}


def candidate_create_payload() -> dict[str, object]:
    return {
        "failed_question_id": str(FAILED_ID),
        "title": "침대 프레임 배출 수수료",
        "representative_question": "침대 2인용 프레임 수수료가 얼마예요?",
        "category": "BULKY_WASTE",
        "answer_summary": "공식 품목표에서 수수료를 확인합니다.",
        "procedure_steps": ["품목을 확인합니다."],
        "required_documents": [],
        "processing_time": None,
        "fee": "10,000원",
        "department": "자원순환과",
        "source_title": "세종특별자치시 대형폐기물 배출 안내",
        "source_url": "https://www.sejong.go.kr/example",
        "last_verified_at": "2026-07-19",
        "caution": None,
    }


def test_admin_routes_are_disabled_by_default_with_exact_value_free_error() -> None:
    with TestClient(application(enabled=False)) as client:
        response = client.get("/api/v1/admin/failed-questions", headers=headers())

    assert response.status_code == 403
    assert response.json() == {
        "error": {
            "code": "ADMIN_ROUTE_DISABLED",
            "message": "관리자 기능을 사용할 수 없습니다.",
            "request_id": str(REQUEST_ID),
            "retryable": False,
        }
    }


def test_enabled_admin_route_requires_both_demo_actor_headers() -> None:
    with TestClient(application(enabled=True, service=RouteService())) as client:
        response = client.get("/api/v1/admin/failed-questions")

    assert response.status_code == 422


def test_enabled_admin_route_rejects_an_unapproved_demo_actor_identity() -> None:
    service = RouteService()

    with TestClient(application(enabled=True, service=service)) as client:
        response = client.get(
            "/api/v1/admin/failed-questions",
            headers=headers(actor_id="CALLER-CHOSEN-001", role="OPERATOR"),
        )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ADMIN_FORBIDDEN"
    assert service.calls == []


def test_failed_question_list_forwards_typed_filters_and_actor() -> None:
    service = RouteService()

    with TestClient(application(enabled=True, service=service)) as client:
        response = client.get(
            "/api/v1/admin/failed-questions?reason=INSUFFICIENT_GROUNDING&status=NEW",
            headers=headers(role="APPROVER", actor_id="PM-LOCAL-001"),
        )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert service.calls == [("list_failed_questions", Actor("PM-LOCAL-001", AdminRole.APPROVER))]


def test_operator_reason_confirmation_is_wired_to_the_service() -> None:
    service = RouteService()

    with TestClient(application(enabled=True, service=service)) as client:
        response = client.patch(
            f"/api/v1/admin/failed-questions/{FAILED_ID}/reason",
            headers=headers(),
            json={"reason": "INSUFFICIENT_GROUNDING"},
        )

    assert response.status_code == 200
    assert response.json() == {"id": str(FAILED_ID), "status": "REASON_CONFIRMED"}
    assert service.calls[0][0] == "confirm_reason"


def test_scope_gap_list_and_approver_review_are_wired() -> None:
    service = RouteService()
    review_headers = headers(actor_id="PM-LOCAL-001", role="APPROVER")

    with TestClient(application(enabled=True, service=service)) as client:
        listed = client.get(
            "/api/v1/admin/civic-scope-gaps?status=NEW",
            headers=review_headers,
        )
        reviewed = client.patch(
            f"/api/v1/admin/civic-scope-gaps/{SCOPE_GAP_ID}/review",
            headers=review_headers,
            json={"decision": "PLANNED", "review_comment": "다음 범위로 검토"},
        )

    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert reviewed.status_code == 200
    assert reviewed.json() == {"id": str(SCOPE_GAP_ID), "status": "PLANNED"}
    assert [name for name, _actor in service.calls] == [
        "list_civic_scope_gaps",
        "review_civic_scope_gap",
    ]


def test_candidate_create_converts_canonical_wire_uuid_and_date_before_service() -> None:
    service = RouteService()

    with TestClient(application(enabled=True, service=service)) as client:
        response = client.post(
            "/api/v1/admin/kb-candidates",
            headers=headers(),
            json=candidate_create_payload(),
        )

    assert response.status_code == 201
    assert response.json() == {"id": str(CANDIDATE_ID), "status": "DRAFTED"}
    assert service.calls == [("create_candidate", Actor("OPERATOR-LOCAL-001", AdminRole.OPERATOR))]
    assert len(service.created_payloads) == 1
    received = service.created_payloads[0]
    assert type(received.failed_question_id) is UUID
    assert received.failed_question_id == FAILED_ID
    assert type(received.last_verified_at) is date
    assert received.last_verified_at == date(2026, 7, 19)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("failed_question_id", "10000000000040008000000000000001"),
        ("failed_question_id", "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"),
        ("failed_question_id", 1),
        ("failed_question_id", True),
        ("last_verified_at", "20260719"),
        ("last_verified_at", "2026-02-30"),
        ("last_verified_at", 1),
        ("last_verified_at", True),
    ],
)
def test_candidate_create_rejects_noncanonical_or_non_string_wire_values_before_service(
    field: str, invalid_value: object
) -> None:
    service = RouteService()
    payload = candidate_create_payload()
    payload[field] = invalid_value

    with TestClient(application(enabled=True, service=service)) as client:
        response = client.post(
            "/api/v1/admin/kb-candidates",
            headers=headers(),
            json=payload,
        )

    assert response.status_code == 422
    assert service.calls == []
    assert service.created_payloads == []


def test_candidate_create_request_accepts_only_exact_internal_uuid_and_date_types() -> None:
    payload = candidate_create_payload()
    payload["failed_question_id"] = FAILED_ID
    payload["last_verified_at"] = date(2026, 7, 19)

    request = KBCandidateCreateRequest.model_validate(payload)

    assert type(request.failed_question_id) is UUID
    assert type(request.last_verified_at) is date

    payload["last_verified_at"] = datetime(2026, 7, 19, tzinfo=UTC)
    with pytest.raises(ValidationError):
        KBCandidateCreateRequest.model_validate(payload)


def test_service_errors_map_to_exact_admin_envelopes_without_exception_text() -> None:
    service = RouteService()
    service.error = AdminServiceError("ADMIN_INVALID_STATE")

    with TestClient(application(enabled=True, service=service)) as client:
        response = client.post(
            f"/api/v1/admin/kb-candidates/{CANDIDATE_ID}/submit",
            headers=headers(),
        )

    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "ADMIN_INVALID_STATE",
        "message": "현재 상태에서는 이 작업을 수행할 수 없습니다.",
        "request_id": str(REQUEST_ID),
        "retryable": False,
    }
    assert "ADMIN_INVALID_STATE" not in response.text.replace('"code":"ADMIN_INVALID_STATE"', "")
