from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Literal
from uuid import UUID

import pytest
from pydantic import AnyUrl

from sejong_ai_api.admin.service import AdminService, AdminServiceError
from sejong_ai_api.contracts.admin import (
    CandidateReviewRequest,
    CivicScopeGapReviewRequest,
    CivicScopeGapSummary,
    FailedQuestion,
    KBCandidateCreateRequest,
    KBCandidateSummary,
    ReasonConfirmationRequest,
)
from sejong_ai_api.db.models import (
    Actor,
    AdminRole,
    CandidateDraft,
    FallbackReason,
    PurgeResult,
)

FAILED_ID = UUID("10000000-0000-4000-8000-000000000001")
CANDIDATE_ID = UUID("20000000-0000-4000-8000-000000000001")
ACTIVATED_ID = UUID("30000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 7, 22, 3, 0, tzinfo=UTC)


def operator(actor_id: str = "OPERATOR-LOCAL-001") -> Actor:
    return Actor(actor_id=actor_id, role=AdminRole.OPERATOR)


def approver(actor_id: str = "PM-LOCAL-001") -> Actor:
    return Actor(actor_id=actor_id, role=AdminRole.APPROVER)


def failed_question(
    *,
    status: Literal["NEW", "REASON_CONFIRMED"] = "NEW",
    reason: Literal[
        "INSUFFICIENT_GROUNDING", "PERSONAL_LOOKUP", "LEGAL_JUDGMENT"
    ] = "INSUFFICIENT_GROUNDING",
) -> FailedQuestion:
    return FailedQuestion(
        id=FAILED_ID,
        masked_question="침대 프레임 수수료를 알려 주세요.",
        intent="BULKY_WASTE",
        fallback_reason=reason,
        candidate_eligible=reason == "INSUFFICIENT_GROUNDING",
        status=status,
        created_at=NOW,
        text_expires_at=NOW + timedelta(days=30),
        text_purged_at=None,
    )


def candidate(
    *,
    status: Literal["DRAFTED", "PENDING_APPROVAL", "APPROVED", "REJECTED"] = "DRAFTED",
    created_by: str = "OPERATOR-LOCAL-001",
) -> KBCandidateSummary:
    reviewed = status in {"APPROVED", "REJECTED"}
    approved = status == "APPROVED"
    return KBCandidateSummary(
        id=CANDIDATE_ID,
        failed_question_id=FAILED_ID,
        title="침대 프레임 배출 안내",
        representative_question="침대 프레임은 어떻게 버리나요?",
        data_origin="OFFICIAL",
        category="BULKY_WASTE",
        answer_summary="신청 후 배출번호를 붙여 배출합니다.",
        procedure_steps=["신청합니다.", "배출합니다."],
        required_documents=[],
        processing_time=None,
        fee="10,000원",
        department="자원순환과",
        source_title="세종특별자치시 대형폐기물 배출 안내",
        source_url=AnyUrl("https://www.sejong.go.kr/example"),
        last_verified_at=date(2026, 7, 19),
        caution=None,
        status=status,
        created_by=created_by,
        reviewed_by="PM-LOCAL-001" if reviewed else None,
        review_comment="공식 출처를 확인했습니다." if reviewed else None,
        approved_at=NOW if approved else None,
        activated_kb_id=ACTIVATED_ID if approved else None,
        created_at=NOW,
        updated_at=NOW,
    )


def reserved_candidate(**overrides: object) -> KBCandidateSummary:
    values: dict[str, object] = {
        "id": CANDIDATE_ID,
        "failed_question_id": FAILED_ID,
        "title": "침대 프레임 배출 수수료",
        "representative_question": "침대 2인용 프레임 수수료가 얼마예요?",
        "data_origin": "OFFICIAL",
        "category": "BULKY_WASTE",
        "answer_summary": (
            "공식 품목표의 침대 프레임 수수료는 1인용침대 8,000원, "
            "2인용침대 10,000원으로 표시됩니다."
        ),
        "procedure_steps": [
            "공식 품목표에서 침대 프레임의 1인용침대 또는 2인용침대 항목을 확인합니다.",
            "해당 수수료로 공식 배출 절차를 진행합니다.",
        ],
        "required_documents": [],
        "processing_time": None,
        "fee": "1인용침대 8,000원; 2인용침대 10,000원",
        "department": "세종특별자치시시설관리공단",
        "source_title": "배출항목선택",
        "source_url": AnyUrl(
            "https://www.sjwaste.kr/wasteApp/appCategoryPopup.do?menuId=MENU00305"
        ),
        "last_verified_at": date(2026, 7, 18),
        "caution": (
            "공식 품목표의 1인용침대·2인용침대 항목을 그대로 따릅니다. "
            "매트리스 포함 가격이나 실제 규격을 단정하지 않습니다."
        ),
        "status": "PENDING_APPROVAL",
        "created_by": "OPERATOR-LOCAL-001",
        "reviewed_by": None,
        "review_comment": None,
        "approved_at": None,
        "activated_kb_id": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return KBCandidateSummary.model_validate(values)


def create_request(
    *,
    representative_question: str = "침대 프레임은 어떻게 버리나요?",
    answer_summary: str = "신청 후 배출번호를 붙여 배출합니다.",
    source_url: str = "https://www.sejong.go.kr/example",
) -> KBCandidateCreateRequest:
    return KBCandidateCreateRequest(
        failed_question_id=FAILED_ID,
        title="침대 프레임 배출 안내",
        representative_question=representative_question,
        category="BULKY_WASTE",
        answer_summary=answer_summary,
        procedure_steps=["신청합니다.", "배출합니다."],
        required_documents=[],
        processing_time=None,
        fee="10,000원",
        department="자원순환과",
        source_title="세종특별자치시 대형폐기물 배출 안내",
        source_url=AnyUrl(source_url),
        last_verified_at=date(2026, 7, 19),
        caution=None,
    )


def reserved_create_request() -> KBCandidateCreateRequest:
    canonical = reserved_candidate()
    return KBCandidateCreateRequest(
        failed_question_id=canonical.failed_question_id,
        title=canonical.title,
        representative_question=canonical.representative_question,
        category=canonical.category,
        answer_summary=canonical.answer_summary,
        procedure_steps=list(canonical.procedure_steps),
        required_documents=list(canonical.required_documents),
        processing_time=canonical.processing_time,
        fee=canonical.fee,
        department=canonical.department,
        source_title=canonical.source_title,
        source_url=canonical.source_url,
        last_verified_at=canonical.last_verified_at,
        caution=canonical.caution,
    )


class FakeAdminRepository:
    def __init__(self) -> None:
        self.failures = [failed_question()]
        self.candidates = [candidate()]
        self.confirmed: list[tuple[UUID, Actor, FallbackReason]] = []
        self.created: list[CandidateDraft] = []
        self.submitted: list[tuple[UUID, Actor]] = []
        self.approved: list[tuple[UUID, Actor, str]] = []
        self.approved_with_public_id: list[tuple[UUID, Actor, str, str]] = []
        self.rejected: list[tuple[UUID, Actor, str]] = []
        self.purge_calls = 0
        self.scope_gap_purge_calls = 0
        self.scope_gaps = [
            CivicScopeGapSummary(
                id=UUID("68000000-0000-4000-8000-000000000001"),
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
        ]
        self.scope_gap_reviews: list[tuple[UUID, Actor, str, str]] = []

    async def list_failed_questions(
        self, *, reason: str | None, status: str | None
    ) -> tuple[FailedQuestion, ...]:
        return tuple(
            item
            for item in self.failures
            if (reason is None or item.fallback_reason == reason)
            and (status is None or item.status == status)
        )

    async def get_failed_question(self, failed_question_id: UUID) -> FailedQuestion | None:
        return next((item for item in self.failures if item.id == failed_question_id), None)

    async def list_kb_candidates(self) -> tuple[KBCandidateSummary, ...]:
        return tuple(self.candidates)

    async def get_kb_candidate(self, candidate_id: UUID) -> KBCandidateSummary | None:
        return next((item for item in self.candidates if item.id == candidate_id), None)

    async def purge_expired_failed_question_text(self) -> PurgeResult:
        self.purge_calls += 1
        return PurgeResult(purged_count=0, purged_ids=())

    async def list_civic_scope_gaps(
        self, *, status: str | None
    ) -> tuple[CivicScopeGapSummary, ...]:
        return tuple(item for item in self.scope_gaps if status is None or item.status == status)

    async def review_civic_scope_gap(
        self, scope_gap_id: UUID, actor: Actor, decision: str, review_comment: str
    ) -> None:
        self.scope_gap_reviews.append((scope_gap_id, actor, decision, review_comment))

    async def purge_expired_civic_scope_gap_text(self) -> PurgeResult:
        self.scope_gap_purge_calls += 1
        return PurgeResult(purged_count=0, purged_ids=())

    async def confirm_failed_question_reason(
        self,
        failed_question_id: UUID,
        actor: Actor,
        fallback_reason: FallbackReason,
    ) -> None:
        self.confirmed.append((failed_question_id, actor, fallback_reason))

    async def create_kb_candidate(self, draft: CandidateDraft) -> UUID:
        self.created.append(draft)
        return CANDIDATE_ID

    async def submit_kb_candidate(self, candidate_id: UUID, actor: Actor) -> None:
        self.submitted.append((candidate_id, actor))

    async def approve_kb_candidate(
        self, candidate_id: UUID, actor: Actor, review_comment: str
    ) -> str:
        self.approved.append((candidate_id, actor, review_comment))
        return "KB-WASTE-03"

    async def approve_kb_candidate_with_public_id(
        self,
        candidate_id: UUID,
        actor: Actor,
        review_comment: str,
        public_id: str,
    ) -> str:
        self.approved_with_public_id.append((candidate_id, actor, review_comment, public_id))
        return public_id

    async def reject_kb_candidate(
        self, candidate_id: UUID, actor: Actor, review_comment: str
    ) -> None:
        self.rejected.append((candidate_id, actor, review_comment))


class StatefulReservedFlowRepository(FakeAdminRepository):
    """Keep the in-memory state transitions needed for one full service workflow."""

    def __init__(self) -> None:
        super().__init__()
        self.candidates = []

    async def confirm_failed_question_reason(
        self,
        failed_question_id: UUID,
        actor: Actor,
        fallback_reason: FallbackReason,
    ) -> None:
        await super().confirm_failed_question_reason(failed_question_id, actor, fallback_reason)
        self.failures = [
            item.model_copy(
                update={
                    "fallback_reason": fallback_reason,
                    "candidate_eligible": fallback_reason == FallbackReason.INSUFFICIENT_GROUNDING,
                    "status": "REASON_CONFIRMED",
                }
            )
            if item.id == failed_question_id
            else item
            for item in self.failures
        ]

    async def create_kb_candidate(self, draft: CandidateDraft) -> UUID:
        candidate_id = await super().create_kb_candidate(draft)
        self.candidates.append(
            KBCandidateSummary(
                id=candidate_id,
                failed_question_id=draft.failed_question_id,
                title=draft.title,
                representative_question=draft.representative_question,
                data_origin="OFFICIAL",
                category="BULKY_WASTE",
                answer_summary=draft.answer_summary,
                procedure_steps=list(draft.procedure_steps),
                required_documents=list(draft.required_documents),
                processing_time=draft.processing_time,
                fee=draft.fee,
                department=draft.department,
                source_title=draft.source_title,
                source_url=AnyUrl(draft.source_url),
                last_verified_at=draft.last_verified_at,
                caution=draft.caution,
                status="DRAFTED",
                created_by=draft.actor.actor_id,
                reviewed_by=None,
                review_comment=None,
                approved_at=None,
                activated_kb_id=None,
                created_at=NOW,
                updated_at=NOW,
            )
        )
        return candidate_id

    async def submit_kb_candidate(self, candidate_id: UUID, actor: Actor) -> None:
        await super().submit_kb_candidate(candidate_id, actor)
        self.candidates = [
            item.model_copy(update={"status": "PENDING_APPROVAL", "updated_at": NOW})
            if item.id == candidate_id
            else item
            for item in self.candidates
        ]


@pytest.mark.asyncio
async def test_lists_and_filters_failed_questions_for_both_admin_roles() -> None:
    repository = FakeAdminRepository()
    service = AdminService(repository)

    result = await service.list_failed_questions(
        approver(), reason="INSUFFICIENT_GROUNDING", status="NEW"
    )

    assert result.total == 1
    assert result.items[0].id == FAILED_ID
    assert repository.purge_calls == 1


@pytest.mark.asyncio
async def test_lists_scope_gaps_for_both_admin_roles_after_bounded_purge() -> None:
    repository = FakeAdminRepository()
    service = AdminService(repository)

    result = await service.list_civic_scope_gaps(approver(), status="NEW")

    assert result.total == 1
    assert result.items[0].masked_question == "합성 범위 부족 민원"
    assert repository.scope_gap_purge_calls == 1


@pytest.mark.asyncio
async def test_only_approver_can_review_a_new_scope_gap() -> None:
    repository = FakeAdminRepository()
    service = AdminService(repository)
    gap_id = repository.scope_gaps[0].id
    payload = CivicScopeGapReviewRequest(
        decision="PLANNED",
        review_comment="다음 범위로 검토",
    )

    with pytest.raises(AdminServiceError) as caught:
        await service.review_civic_scope_gap(operator(), gap_id, payload)
    assert caught.value.code == "ADMIN_FORBIDDEN"

    result = await service.review_civic_scope_gap(approver(), gap_id, payload)
    assert result.status == "PLANNED"
    assert repository.scope_gap_reviews == [(gap_id, approver(), "PLANNED", "다음 범위로 검토")]


@pytest.mark.asyncio
async def test_missing_failed_question_is_value_free_not_found() -> None:
    service = AdminService(FakeAdminRepository())

    with pytest.raises(AdminServiceError) as caught:
        await service.get_failed_question(operator(), UUID(int=0))

    assert caught.value.code == "ADMIN_NOT_FOUND"
    assert str(FAILED_ID) not in str(caught.value)


@pytest.mark.asyncio
async def test_only_operator_can_confirm_reason() -> None:
    service = AdminService(FakeAdminRepository())

    with pytest.raises(AdminServiceError) as caught:
        await service.confirm_reason(
            approver(), FAILED_ID, ReasonConfirmationRequest(reason="INSUFFICIENT_GROUNDING")
        )

    assert caught.value.code == "ADMIN_FORBIDDEN"


@pytest.mark.asyncio
async def test_confirm_reason_delegates_the_typed_existing_capability() -> None:
    repository = FakeAdminRepository()
    service = AdminService(repository)

    result = await service.confirm_reason(
        operator(), FAILED_ID, ReasonConfirmationRequest(reason="INSUFFICIENT_GROUNDING")
    )

    assert result.status == "REASON_CONFIRMED"
    assert repository.confirmed == [(FAILED_ID, operator(), FallbackReason.INSUFFICIENT_GROUNDING)]


@pytest.mark.asyncio
async def test_candidate_create_rechecks_representative_question_for_pii() -> None:
    repository = FakeAdminRepository()
    repository.failures = [failed_question(status="REASON_CONFIRMED")]
    service = AdminService(repository)

    with pytest.raises(AdminServiceError) as caught:
        await service.create_candidate(
            operator(), create_request(representative_question="김철수의 침대를 버려 주세요.")
        )

    assert caught.value.code == "ADMIN_VALIDATION_FAILED"
    assert repository.created == []


@pytest.mark.asyncio
async def test_candidate_create_rechecks_every_candidate_text_field_for_pii() -> None:
    repository = FakeAdminRepository()
    repository.failures = [failed_question(status="REASON_CONFIRMED")]
    service = AdminService(repository)

    with pytest.raises(AdminServiceError) as caught:
        await service.create_candidate(
            operator(), create_request(answer_summary="test-person@example.com으로 연락하세요.")
        )

    assert caught.value.code == "ADMIN_VALIDATION_FAILED"
    assert repository.created == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_url",
    [
        "https://test-person@example.com/official",
        "https://www.sejong.go.kr/official#010-1234-5678",
        "https://www.sejong.go.kr/official?email=test-person%40example.com",
        "https://example.com/not-an-approved-official-host",
    ],
)
async def test_candidate_create_rejects_unsafe_or_unapproved_source_url(
    source_url: str,
) -> None:
    repository = FakeAdminRepository()
    repository.failures = [failed_question(status="REASON_CONFIRMED")]
    service = AdminService(repository)

    with pytest.raises(AdminServiceError) as caught:
        await service.create_candidate(
            operator(),
            create_request(source_url=source_url),
        )

    assert caught.value.code == "ADMIN_VALIDATION_FAILED"
    assert repository.created == []


@pytest.mark.asyncio
async def test_candidate_create_rejects_pii_in_decoded_source_query_key() -> None:
    repository = FakeAdminRepository()
    repository.failures = [failed_question(status="REASON_CONFIRMED")]
    service = AdminService(repository)

    with pytest.raises(AdminServiceError) as caught:
        await service.create_candidate(
            operator(),
            create_request(
                source_url="https://www.sejong.go.kr/official?test%252540example.com=reference"
            ),
        )

    assert caught.value.code == "ADMIN_VALIDATION_FAILED"
    assert repository.created == []


@pytest.mark.asyncio
async def test_candidate_create_rejects_pii_shaped_subdomain_under_approved_suffix() -> None:
    repository = FakeAdminRepository()
    repository.failures = [failed_question(status="REASON_CONFIRMED")]
    service = AdminService(repository)

    with pytest.raises(AdminServiceError) as caught:
        await service.create_candidate(
            operator(),
            create_request(source_url="https://010-1234-5678.sejong.go.kr/official"),
        )

    assert caught.value.code == "ADMIN_VALIDATION_FAILED"
    assert repository.created == []


@pytest.mark.asyncio
async def test_candidate_create_rejects_pii_shape_under_technical_query_key() -> None:
    repository = FakeAdminRepository()
    repository.failures = [failed_question(status="REASON_CONFIRMED")]
    service = AdminService(repository)

    with pytest.raises(AdminServiceError) as caught:
        await service.create_candidate(
            operator(),
            create_request(source_url="https://plus.gov.kr/search?srvcId=010-1234-5678"),
        )

    assert caught.value.code == "ADMIN_VALIDATION_FAILED"
    assert repository.created == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_url",
    [
        "https://www.sejong.go.kr/official?reference=test%252540example.com",
        "https://www.sejong.go.kr/official?reference=010%25252D1234%25252D5678",
    ],
)
async def test_candidate_create_rejects_triple_percent_encoded_pii_in_source_url(
    source_url: str,
) -> None:
    repository = FakeAdminRepository()
    repository.failures = [failed_question(status="REASON_CONFIRMED")]
    service = AdminService(repository)

    with pytest.raises(AdminServiceError) as caught:
        await service.create_candidate(
            operator(),
            create_request(source_url=source_url),
        )

    assert caught.value.code == "ADMIN_VALIDATION_FAILED"
    assert repository.created == []


@pytest.mark.asyncio
async def test_candidate_create_rejects_source_url_longer_than_redactor_limit() -> None:
    repository = FakeAdminRepository()
    repository.failures = [failed_question(status="REASON_CONFIRMED")]
    service = AdminService(repository)

    with pytest.raises(AdminServiceError) as caught:
        await service.create_candidate(
            operator(),
            create_request(source_url=f"https://www.sejong.go.kr/official?reference={'x' * 1001}"),
        )

    assert caught.value.code == "ADMIN_VALIDATION_FAILED"
    assert repository.created == []


@pytest.mark.asyncio
async def test_candidate_create_rejects_source_url_with_percent_encoding_beyond_bound() -> None:
    repository = FakeAdminRepository()
    repository.failures = [failed_question(status="REASON_CONFIRMED")]
    service = AdminService(repository)

    with pytest.raises(AdminServiceError) as caught:
        await service.create_candidate(
            operator(),
            create_request(source_url="https://www.sejong.go.kr/official?reference=%25252525"),
        )

    assert caught.value.code == "ADMIN_VALIDATION_FAILED"
    assert repository.created == []


@pytest.mark.asyncio
async def test_candidate_create_rejects_fragment_revealed_after_percent_decoding() -> None:
    repository = FakeAdminRepository()
    repository.failures = [failed_question(status="REASON_CONFIRMED")]
    service = AdminService(repository)

    with pytest.raises(AdminServiceError) as caught:
        await service.create_candidate(
            operator(),
            create_request(source_url="https://www.sejong.go.kr/official?reference=%252523proof"),
        )

    assert caught.value.code == "ADMIN_VALIDATION_FAILED"
    assert repository.created == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source_url",
    [
        "https://www.sejong.go.kr/areum/sub02_02.do?cmsNo=1461",
        "https://plus.gov.kr/search/searchdtl/?srvcId=13100000015&typeSn=01",
        (
            "https://www.gov.kr/mw/AA020InfoCappView.do?"
            "CappBizCD=13110000017&HighCtgCD=A09002&tp_seq=01"
        ),
        "https://www.law.go.kr/LSW/lsInfoP.do?lsId=001655&urlMode=lsInfoP",
        "https://www.wetax.go.kr/main.do",
        "https://www.sjwaste.kr/board?menuId=MENU00303&siteId=null",
    ],
)
async def test_candidate_create_accepts_privacy_safe_approved_official_source_url(
    source_url: str,
) -> None:
    repository = FakeAdminRepository()
    repository.failures = [failed_question(status="REASON_CONFIRMED")]
    service = AdminService(repository)

    result = await service.create_candidate(
        operator(),
        create_request(source_url=source_url),
    )

    assert result.status == "DRAFTED"
    assert str(repository.created[0].source_url) == source_url


@pytest.mark.asyncio
async def test_candidate_create_uses_official_origin_and_operator_identity() -> None:
    repository = FakeAdminRepository()
    repository.failures = [failed_question(status="REASON_CONFIRMED")]
    service = AdminService(repository)

    result = await service.create_candidate(operator(), create_request())

    assert result.status == "DRAFTED"
    assert result.id == CANDIDATE_ID
    assert len(repository.created) == 1
    assert repository.created[0].actor == operator()
    assert repository.created[0].data_origin.value == "OFFICIAL"


@pytest.mark.asyncio
async def test_only_candidate_creator_can_submit_draft() -> None:
    repository = FakeAdminRepository()
    service = AdminService(repository)

    with pytest.raises(AdminServiceError) as caught:
        await service.submit_candidate(operator("OTHER-OPERATOR"), CANDIDATE_ID)

    assert caught.value.code == "ADMIN_FORBIDDEN"
    assert repository.submitted == []


@pytest.mark.asyncio
async def test_creator_cannot_review_own_candidate() -> None:
    repository = FakeAdminRepository()
    repository.candidates = [candidate(status="PENDING_APPROVAL", created_by="PM-LOCAL-001")]
    service = AdminService(repository)

    with pytest.raises(AdminServiceError) as caught:
        await service.review_candidate(
            approver(),
            CANDIDATE_ID,
            CandidateReviewRequest(decision="APPROVED", review_comment="출처를 확인했습니다."),
        )

    assert caught.value.code == "ADMIN_FORBIDDEN"
    assert repository.approved == []


@pytest.mark.asyncio
@pytest.mark.parametrize("decision", ["APPROVED", "REJECTED"])
async def test_different_approver_can_apply_both_review_outcomes(decision: str) -> None:
    repository = FakeAdminRepository()
    repository.candidates = [candidate(status="PENDING_APPROVAL")]
    service = AdminService(repository)

    result = await service.review_candidate(
        approver(),
        CANDIDATE_ID,
        CandidateReviewRequest(
            decision=decision,  # type: ignore[arg-type]
            review_comment="공식 출처를 확인했습니다.",
        ),
    )

    assert result.status == decision
    if decision == "APPROVED":
        assert len(repository.approved) == 1
        assert repository.rejected == []
    else:
        assert len(repository.rejected) == 1
        assert repository.approved == []


@pytest.mark.asyncio
async def test_privacy_safe_reserved_candidate_completes_the_real_service_workflow() -> None:
    repository = StatefulReservedFlowRepository()
    service = AdminService(repository)

    confirmed = await service.confirm_reason(
        operator(),
        FAILED_ID,
        ReasonConfirmationRequest(reason="INSUFFICIENT_GROUNDING"),
    )
    created = await service.create_candidate(operator(), reserved_create_request())
    submitted = await service.submit_candidate(operator(), created.id)
    reviewed = await service.review_candidate(
        approver(),
        created.id,
        CandidateReviewRequest(
            decision="APPROVED",
            review_comment="공식 품목표와 정본 값을 확인했습니다.",
        ),
    )

    assert confirmed.status == "REASON_CONFIRMED"
    assert created.status == "DRAFTED"
    assert submitted.status == "PENDING_APPROVAL"
    assert reviewed.status == "APPROVED"
    assert len(repository.created) == 1
    assert repository.approved == []
    assert repository.approved_with_public_id == [
        (
            CANDIDATE_ID,
            approver(),
            "공식 품목표와 정본 값을 확인했습니다.",
            "KB-WASTE-03",
        )
    ]


@pytest.mark.asyncio
async def test_exact_reserved_candidate_uses_server_owned_public_id_binding() -> None:
    repository = FakeAdminRepository()
    repository.candidates = [reserved_candidate()]
    service = AdminService(repository)

    result = await service.review_candidate(
        approver(),
        CANDIDATE_ID,
        CandidateReviewRequest(
            decision="APPROVED",
            review_comment="공식 품목표와 canonical 값을 확인했습니다.",
        ),
    )

    assert result.status == "APPROVED"
    assert repository.approved == []
    assert repository.approved_with_public_id == [
        (
            CANDIDATE_ID,
            approver(),
            "공식 품목표와 canonical 값을 확인했습니다.",
            "KB-WASTE-03",
        )
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "overrides",
    [
        {"representative_question": "대표 질문 불일치"},
        {"data_origin": "MOCK"},
        {"category": "LOCAL_TAX_GENERAL"},
        {"answer_summary": "답변 불일치"},
        {"procedure_steps": ["절차 불일치"]},
        {"required_documents": ["서류 불일치"]},
        {"processing_time": "즉시"},
        {"fee": "canonical-drift-private-sentinel"},
        {"department": "담당 기관 불일치"},
        {"last_verified_at": date(2026, 7, 17)},
        {"caution": None},
    ],
)
async def test_reserved_identity_claim_with_any_canonical_drift_fails_value_free(
    overrides: dict[str, object],
) -> None:
    repository = FakeAdminRepository()
    repository.candidates = [reserved_candidate(**overrides)]
    service = AdminService(repository)

    with pytest.raises(AdminServiceError) as caught:
        await service.review_candidate(
            approver(),
            CANDIDATE_ID,
            CandidateReviewRequest(
                decision="APPROVED",
                review_comment="공식 품목표를 확인했습니다.",
            ),
        )

    assert caught.value.code == "ADMIN_VALIDATION_FAILED"
    assert str(caught.value) == "ADMIN_OPERATION_REJECTED"
    assert repository.approved == []
    assert repository.approved_with_public_id == []


@pytest.mark.asyncio
async def test_reserved_identity_drift_precedes_self_review_classification() -> None:
    repository = FakeAdminRepository()
    repository.candidates = [
        reserved_candidate(created_by="PM-LOCAL-001", answer_summary="답변 불일치")
    ]
    service = AdminService(repository)

    with pytest.raises(AdminServiceError) as caught:
        await service.review_candidate(
            approver(),
            CANDIDATE_ID,
            CandidateReviewRequest(
                decision="APPROVED",
                review_comment="공식 품목표를 확인했습니다.",
            ),
        )

    assert caught.value.code == "ADMIN_VALIDATION_FAILED"
    assert str(caught.value) == "ADMIN_OPERATION_REJECTED"
    assert repository.approved == []
    assert repository.approved_with_public_id == []
