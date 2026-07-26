from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

import pytest

import sejong_ai_api.chat.service as service_module
from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.context import ContextTokenCodec
from sejong_ai_api.chat.idempotency import (
    IdempotencyClaim,
    IdempotencyClaimStatus,
    IdempotencyConflictError,
)
from sejong_ai_api.chat.response import (
    build_fallback_response,
    build_followup_response,
    build_success_response,
)
from sejong_ai_api.chat.service import ChatService, ChatUnavailableError
from sejong_ai_api.contracts.chat import ChatRequest, FollowupResponse, SuccessResponse
from sejong_ai_api.db.errors import (
    DatabaseRuleCode,
    DatabaseRuleError,
    DatabaseUnavailableError,
)
from sejong_ai_api.db.models import (
    AnswerStatus,
    FallbackReason,
    Intent,
    InteractionWrite,
    InteractionWriteResult,
    KnowledgeRecord,
    OfficeRecord,
    Region,
)
from sejong_ai_api.llm.chat_contracts import GroundedAnswerGenerator
from sejong_ai_api.llm.classifier_contracts import (
    ClassifierDecision,
    ClassifierRoute,
)

REQUEST_ID = UUID("11111111-1111-4111-8111-111111111111")
INTERACTION_ID = UUID("22222222-2222-4222-8222-222222222222")
IDEMPOTENCY_KEY = UUID("33333333-3333-4333-8333-333333333333")
RETRY_REQUEST_ID = UUID("44444444-4444-4444-8444-444444444444")
CLAIM_TOKEN = UUID("55555555-5555-4555-8555-555555555555")


def knowledge_record(
    *,
    public_id: str = "KB-TEST-01",
    intent: Intent = Intent.BULKY_WASTE,
    service_name: str = "대형폐기물 배출신청 절차",
    question_examples: tuple[str, ...] = ("대형폐기물은 어떻게 버려요?",),
    required_documents: tuple[str, ...] = (),
    fee: str | None = None,
) -> KnowledgeRecord:
    return KnowledgeRecord(
        public_id=public_id,
        category=intent,
        service_name=service_name,
        answer_summary="승인된 안내 요약입니다.",
        procedure_steps=("승인된 절차를 확인하세요.",),
        required_documents=required_documents,
        processing_time=None,
        fee=fee,
        department="민원 담당 부서",
        source_title="승인된 공식 출처",
        source_url="https://example.invalid/official/source",
        last_verified_at=date(2026, 7, 20),
        caution=None,
        question_examples=question_examples,
    )


def office_record(
    *,
    region: Region = Region.AREUM_DONG,
    intent: Intent = Intent.BULKY_WASTE,
) -> OfficeRecord:
    del intent
    return OfficeRecord(
        public_id="OFFICE-TEST-01",
        region=region,
        office_name="아름동 행정복지센터",
        address="세종특별자치시 시연용 주소",
        phone="044-000-0000",
        opening_hours="평일 09:00~18:00",
        map_url=None,
        department_label="민원창구",
        source_title="승인된 기관 출처",
        source_url="https://example.invalid/official/office",
        last_verified_at=date(2026, 7, 20),
    )


class FakeRepository:
    def __init__(
        self,
        *,
        records: Sequence[KnowledgeRecord] = (),
        offices: Sequence[OfficeRecord] = (),
        fail_reads: bool = False,
        fail_event_write: bool = False,
        fail_scope_gap_write: bool = False,
    ) -> None:
        self.records = tuple(records)
        self.offices = tuple(offices)
        self.fail_reads = fail_reads
        self.fail_event_write = fail_event_write
        self.fail_scope_gap_write = fail_scope_gap_write
        self.active_intents: list[Intent] = []
        self.office_queries: list[tuple[Region, Intent]] = []
        self.events: list[InteractionWrite] = []
        self.scope_gaps: list[str] = []

    async def list_active_kb(self, intent: Intent) -> Sequence[KnowledgeRecord]:
        self.active_intents.append(intent)
        if self.fail_reads:
            raise DatabaseUnavailableError()
        return self.records

    async def list_offices(self, region: Region, intent: Intent) -> Sequence[OfficeRecord]:
        self.office_queries.append((region, intent))
        if self.fail_reads:
            raise DatabaseUnavailableError()
        return self.offices

    async def record_interaction(self, event: InteractionWrite) -> InteractionWriteResult:
        self.events.append(event)
        if self.fail_event_write:
            raise DatabaseUnavailableError()
        return InteractionWriteResult(INTERACTION_ID, None)

    async def record_civic_scope_gap(self, masked_question: str) -> None:
        self.scope_gaps.append(masked_question)
        if self.fail_scope_gap_write:
            raise DatabaseUnavailableError()


@dataclass
class FakeQuestionClassifier:
    result: ClassifierDecision | None
    error: Exception | None = None
    delay_seconds: float = 0
    calls: list[str] = field(default_factory=list)

    async def classify(self, question: SafeQuestion) -> ClassifierDecision | None:
        self.calls.append(question.text)
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if self.error is not None:
            raise self.error
        return self.result


class FakeIdempotencyRepository:
    def __init__(
        self,
        claim: IdempotencyClaim,
        *,
        fail_claim: bool = False,
        fail_complete: bool = False,
        fail_abandon: bool = False,
        complete_rule_error: bool = False,
        abandon_rule_error: bool = False,
        abandon_exception: Exception | None = None,
    ) -> None:
        self.claim = claim
        self.fail_claim = fail_claim
        self.fail_complete = fail_complete
        self.fail_abandon = fail_abandon
        self.complete_rule_error = complete_rule_error
        self.abandon_rule_error = abandon_rule_error
        self.abandon_exception = abandon_exception
        self.claims: list[tuple[UUID, str, UUID]] = []
        self.completions: list[tuple[UUID, str, UUID, dict[str, object]]] = []
        self.abandons: list[tuple[UUID, str, UUID]] = []
        self.committed_events: list[InteractionWrite] = []

    async def claim_chat_idempotency(
        self,
        *,
        idempotency_key: UUID,
        request_fingerprint: str,
        claim_token: UUID,
    ) -> IdempotencyClaim:
        self.claims.append((idempotency_key, request_fingerprint, claim_token))
        if self.fail_claim:
            raise DatabaseUnavailableError()
        return self.claim

    async def complete_chat_idempotency(
        self,
        *,
        idempotency_key: UUID,
        request_fingerprint: str,
        claim_token: UUID,
        response_payload: dict[str, object],
    ) -> None:
        self.completions.append(
            (idempotency_key, request_fingerprint, claim_token, response_payload)
        )
        if self.fail_complete:
            raise DatabaseUnavailableError()
        if self.complete_rule_error:
            raise DatabaseRuleError(DatabaseRuleCode.INVALID_CANDIDATE_STATE)

    async def commit_chat_idempotency(
        self,
        *,
        idempotency_key: UUID,
        request_fingerprint: str,
        claim_token: UUID,
        response_payload: dict[str, object],
        interaction: InteractionWrite | None,
    ) -> None:
        await self.complete_chat_idempotency(
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            claim_token=claim_token,
            response_payload=response_payload,
        )
        if interaction is not None:
            self.committed_events.append(interaction)

    async def abandon_chat_idempotency(
        self,
        *,
        idempotency_key: UUID,
        request_fingerprint: str,
        claim_token: UUID,
    ) -> None:
        self.abandons.append((idempotency_key, request_fingerprint, claim_token))
        if self.fail_abandon:
            raise DatabaseUnavailableError()
        if self.abandon_rule_error:
            raise DatabaseRuleError(DatabaseRuleCode.INVALID_CANDIDATE_STATE)
        if self.abandon_exception is not None:
            raise self.abandon_exception


def service(
    repository: FakeRepository,
    *,
    clock_ns: Callable[[], int] | None = None,
    idempotency_repository: FakeIdempotencyRepository | None = None,
    idempotency_claim_factory: Callable[[], UUID] = lambda: CLAIM_TOKEN,
    answer_generator: GroundedAnswerGenerator | None = None,
    question_classifier: FakeQuestionClassifier | None = None,
) -> ChatService:
    ticks = iter((1_000_000, 6_000_000))
    return ChatService(
        repository=repository,
        context_codec=ContextTokenCodec(secret=b"x" * 32, clock=lambda: 1_000),
        request_id_factory=lambda: REQUEST_ID,
        monotonic_ns=clock_ns if clock_ns is not None else lambda: next(ticks),
        is_test=True,
        idempotency_repository=idempotency_repository,
        idempotency_secret=b"i" * 32 if idempotency_repository is not None else None,
        idempotency_claim_factory=idempotency_claim_factory,
        answer_generator=answer_generator,
        question_classifier=question_classifier,
    )


@pytest.mark.asyncio
async def test_success_uses_masked_text_for_lookup_and_server_bound_metadata() -> None:
    raw_phone = "010-1234-5678"
    record = knowledge_record(
        question_examples=("대형폐기물은 어떻게 버려요?",),
    )
    repository = FakeRepository(records=(record,), offices=(office_record(),))

    response = await service(repository).answer(
        ChatRequest(
            question=f"대형폐기물은 어떻게 버려요? 연락처는 {raw_phone}",
            selected_region="아름동",
        )
    )

    assert response.answer_status == "SUCCESS"
    assert response.intent == Intent.BULKY_WASTE.value
    assert response.sources[0].source_id == record.public_id
    assert response.office is not None
    assert response.office.id == "OFFICE-TEST-01"
    assert response.context_token is not None
    assert raw_phone not in response.context_token
    context = ContextTokenCodec(secret=b"x" * 32, clock=lambda: 1_000).read(
        response.context_token
    )
    assert context is not None
    assert context.schema_version == 2
    assert context.topic_id == record.public_id
    assert context.pending_slot is None
    assert context.dialog_act == "ANSWERED"
    assert repository.active_intents == [Intent.BULKY_WASTE]
    assert repository.office_queries == [(Region.AREUM_DONG, Intent.BULKY_WASTE)]
    assert len(repository.events) == 1
    event = repository.events[0]
    assert event.answer_status is AnswerStatus.SUCCESS
    assert event.used_source_ids == (record.public_id,)
    assert event.masked_question is None
    assert event.response_time_ms == 5
    assert raw_phone not in repr(repository.events)


@pytest.mark.asyncio
async def test_privacy_unresolved_returns_fixed_fallback_and_uses_no_repository() -> None:
    repository = FakeRepository(fail_reads=True)

    response = await service(repository).answer(ChatRequest(question="김철수"))

    assert response.answer_status == "FALLBACK"
    assert response.intent == Intent.UNKNOWN.value
    assert response.fallback.reason == "PRIVACY_UNRESOLVED"
    assert response.fallback.candidate_eligible is False
    assert response.sources == []
    assert response.context_token is None
    assert repository.active_intents == []
    assert repository.office_queries == []
    assert repository.events == []


@pytest.mark.asyncio
async def test_ambiguous_question_is_followup_and_never_creates_a_failed_question() -> None:
    repository = FakeRepository()

    response = await service(repository).answer(ChatRequest(question="신고하고 싶어요."))

    assert response.answer_status == "FOLLOWUP"
    assert response.intent == Intent.UNKNOWN.value
    assert len(response.followup_options) == 4
    assert response.context_token is not None
    assert repository.active_intents == []
    assert repository.events == []
    assert repository.scope_gaps == []


@pytest.mark.asyncio
async def test_generic_certificate_requests_exact_certificate_kind() -> None:
    repository = FakeRepository()
    classifier = FakeQuestionClassifier(result=None)

    response = await service(
        repository,
        question_classifier=classifier,
    ).answer(ChatRequest(question="증명서 발급해야해"))

    assert response.answer_status == "FOLLOWUP"
    assert response.intent == Intent.CERTIFICATE_ISSUANCE.value
    assert response.followup_options == [
        "주민등록등본 발급",
        "주민등록초본 발급",
        "등본과 초본의 차이",
        "주민등록표 열람",
        "무인민원발급기 이용",
    ]
    assert response.context_token is not None
    context = ContextTokenCodec(secret=b"x" * 32, clock=lambda: 1_000).read(
        response.context_token
    )
    assert context is not None
    assert context.schema_version == 2
    assert context.topic_id is None
    assert context.pending_slot == "CERTIFICATE_KIND"
    assert context.dialog_act == "ASKING_SLOT"
    assert classifier.calls == []
    assert repository.active_intents == []
    assert repository.scope_gaps == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "question",
    [
        "청년 월세 지원 어떻게 해요?",
        "장학금 신청 어떻게 해요?",
        "가족관계증명서 어떻게 발급받아요?",
    ],
)
async def test_civic_scope_gap_uses_separate_queue_without_event_or_failed_row(
    question: str,
) -> None:
    repository = FakeRepository()
    classifier = FakeQuestionClassifier(
        result=ClassifierDecision(
            route=ClassifierRoute.CIVIC_SCOPE_GAP,
            intent=None,
            topic_id=None,
            pending_slot=None,
        )
    )

    response = await service(
        repository,
        question_classifier=classifier,
    ).answer(ChatRequest(question=question))

    assert response.answer_status == "FALLBACK"
    assert response.intent == Intent.OUT_OF_SCOPE.value
    assert response.fallback.reason == "CIVIC_SCOPE_GAP"
    assert response.fallback.candidate_eligible is False
    assert response.sources == []
    assert response.context_token is None
    assert classifier.calls == [question]
    assert repository.scope_gaps == [question]
    assert repository.events == []
    assert repository.active_intents == []


@pytest.mark.asyncio
async def test_scope_gap_queue_write_failure_keeps_public_policy_response() -> None:
    repository = FakeRepository(fail_scope_gap_write=True)
    classifier = FakeQuestionClassifier(
        result=ClassifierDecision(
            route=ClassifierRoute.CIVIC_SCOPE_GAP,
            intent=None,
            topic_id=None,
            pending_slot=None,
        )
    )

    response = await service(
        repository,
        question_classifier=classifier,
    ).answer(ChatRequest(question="청년 월세 지원 어떻게 해요?"))

    assert response.answer_status == "FALLBACK"
    assert response.fallback.reason == "CIVIC_SCOPE_GAP"
    assert repository.events == []


@pytest.mark.asyncio
async def test_classifier_failure_uses_storage_free_domain_followup() -> None:
    repository = FakeRepository()
    classifier = FakeQuestionClassifier(
        result=None,
        error=RuntimeError("PROVIDER-PRIVATE-SENTINEL"),
    )

    response = await service(
        repository,
        question_classifier=classifier,
    ).answer(ChatRequest(question="청년 월세 지원 어떻게 해요?"))

    assert response.answer_status == "FOLLOWUP"
    assert response.intent == Intent.UNKNOWN.value
    assert len(response.followup_options) == 4
    assert classifier.calls == ["청년 월세 지원 어떻게 해요?"]
    assert repository.events == []
    assert repository.scope_gaps == []


@pytest.mark.asyncio
async def test_classifier_hard_wall_uses_storage_free_domain_followup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(service_module, "_PROVIDER_HARD_WALL_SECONDS", 0.001)
    repository = FakeRepository()
    classifier = FakeQuestionClassifier(
        result=None,
        delay_seconds=1,
    )

    response = await service(
        repository,
        question_classifier=classifier,
    ).answer(ChatRequest(question="청년 월세 지원 어떻게 해요?"))

    assert response.answer_status == "FOLLOWUP"
    assert classifier.calls == ["청년 월세 지원 어떻게 해요?"]
    assert repository.events == []
    assert repository.scope_gaps == []


@pytest.mark.asyncio
async def test_non_civic_weather_has_zero_provider_and_repository_use() -> None:
    repository = FakeRepository(fail_reads=True)
    classifier = FakeQuestionClassifier(result=None)

    response = await service(
        repository,
        question_classifier=classifier,
    ).answer(ChatRequest(question="오늘 날씨 어때요?"))

    assert response.answer_status == "FALLBACK"
    assert response.fallback.reason == "OUT_OF_SCOPE"
    assert classifier.calls == []
    assert repository.active_intents == []
    assert repository.events == []
    assert repository.scope_gaps == []


@pytest.mark.asyncio
async def test_provider_non_civic_decision_has_zero_repository_use() -> None:
    repository = FakeRepository(fail_reads=True)
    classifier = FakeQuestionClassifier(
        result=ClassifierDecision(
            route=ClassifierRoute.NON_CIVIC,
            intent=None,
            topic_id=None,
            pending_slot=None,
        )
    )

    response = await service(
        repository,
        question_classifier=classifier,
    ).answer(ChatRequest(question="게임 추천해줘"))

    assert response.answer_status == "FALLBACK"
    assert response.fallback.reason == "OUT_OF_SCOPE"
    assert classifier.calls == ["게임 추천해줘"]
    assert repository.active_intents == []
    assert repository.events == []
    assert repository.scope_gaps == []


@pytest.mark.asyncio
async def test_provider_supported_decision_continues_through_active_grounding() -> None:
    question = "이 민원 신청 방법 알려줘"
    record = knowledge_record(
        intent=Intent.BULKY_WASTE,
        question_examples=(question,),
    )
    repository = FakeRepository(records=(record,))
    classifier = FakeQuestionClassifier(
        result=ClassifierDecision(
            route=ClassifierRoute.SUPPORTED,
            intent=Intent.BULKY_WASTE,
            topic_id=None,
            pending_slot=None,
        )
    )

    response = await service(
        repository,
        question_classifier=classifier,
    ).answer(ChatRequest(question=question))

    assert response.answer_status == "SUCCESS"
    assert response.intent == Intent.BULKY_WASTE.value
    assert classifier.calls == [question]
    assert repository.active_intents == [Intent.BULKY_WASTE]
    assert len(repository.events) == 1
    assert repository.events[0].answer_status is AnswerStatus.SUCCESS


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "question",
    [
        "김철수",
        "내 자동차세 체납액을 조회해줘.",
        "전입신고를 안 하면 법적으로 처벌받는지 판단해줘.",
    ],
)
async def test_privacy_and_policy_paths_never_call_classifier(
    question: str,
) -> None:
    repository = FakeRepository(fail_reads=True)
    classifier = FakeQuestionClassifier(result=None)

    response = await service(
        repository,
        question_classifier=classifier,
    ).answer(ChatRequest(question=question))

    assert response.answer_status == "FALLBACK"
    assert classifier.calls == []
    assert repository.active_intents == []
    assert repository.events == []
    assert repository.scope_gaps == []


@pytest.mark.asyncio
async def test_idempotent_scope_gap_records_queue_only_after_first_commit() -> None:
    repository = FakeRepository()
    classifier = FakeQuestionClassifier(
        result=ClassifierDecision(
            route=ClassifierRoute.CIVIC_SCOPE_GAP,
            intent=None,
            topic_id=None,
            pending_slot=None,
        )
    )
    idempotency = FakeIdempotencyRepository(
        IdempotencyClaim(status=IdempotencyClaimStatus.ACQUIRED)
    )
    selected = service(
        repository,
        question_classifier=classifier,
        idempotency_repository=idempotency,
    )
    request = ChatRequest(question="청년 월세 지원 어떻게 해요?")

    first = await selected.answer(
        request,
        request_id=REQUEST_ID,
        idempotency_key=IDEMPOTENCY_KEY,
    )
    idempotency.claim = IdempotencyClaim(
        status=IdempotencyClaimStatus.COMPLETED,
        response_payload=idempotency.completions[0][3],
    )
    replay = await selected.answer(
        request,
        request_id=RETRY_REQUEST_ID,
        idempotency_key=IDEMPOTENCY_KEY,
    )

    assert first.fallback.reason == "CIVIC_SCOPE_GAP"
    assert replay.fallback.reason == "CIVIC_SCOPE_GAP"
    assert classifier.calls == ["청년 월세 지원 어떻게 해요?"]
    assert repository.scope_gaps == ["청년 월세 지원 어떻게 해요?"]
    assert repository.events == []
    assert idempotency.committed_events == []


@pytest.mark.asyncio
async def test_signed_context_resolves_a_short_followup_without_storing_transcript() -> None:
    record = knowledge_record(
        intent=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        service_name="방문 전입신고 준비물",
        question_examples=("전입신고 준비물은 무엇인가요?",),
        required_documents=("신분증",),
    )
    repository = FakeRepository(records=(record,))
    codec = ContextTokenCodec(secret=b"x" * 32, clock=lambda: 1_000)
    token = codec.issue(
        last_intent=Intent.MOVE_IN_RESIDENT_REGISTRATION.value,
        selected_region=None,
        answer_status="SUCCESS",
        dialog_act="ANSWERED",
    )
    ticks = iter((1_000_000, 2_000_000))
    chat_service = ChatService(
        repository=repository,
        context_codec=codec,
        request_id_factory=lambda: REQUEST_ID,
        monotonic_ns=lambda: next(ticks),
        is_test=True,
    )

    response = await chat_service.answer(ChatRequest(question="준비물은요?", context_token=token))

    assert response.answer_status == "SUCCESS"
    assert response.intent == Intent.MOVE_IN_RESIDENT_REGISTRATION.value
    assert repository.active_intents == [Intent.MOVE_IN_RESIDENT_REGISTRATION]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "question",
    ["비용은요?", "준비물은요?", "온라인도 돼요?"],
)
async def test_v2_context_resolves_bounded_detail_against_same_current_active_topic(
    question: str,
) -> None:
    record = knowledge_record(
        public_id="KB-WASTE-CONTEXT-01",
        required_documents=("배출 품목과 규격",),
        fee="품목별 수수료",
    )
    repository = FakeRepository(records=(record,))
    codec = ContextTokenCodec(secret=b"x" * 32, clock=lambda: 1_000)
    token = codec.issue(
        last_intent=Intent.BULKY_WASTE.value,
        selected_region=None,
        answer_status="SUCCESS",
        dialog_act="ANSWERED",
        topic_id=record.public_id,
    )

    response = await service(repository).answer(
        ChatRequest(question=question, context_token=token)
    )

    assert response.answer_status == "SUCCESS"
    assert [source.source_id for source in response.sources] == [record.public_id]
    assert repository.active_intents == [Intent.BULKY_WASTE]
    assert response.context_token is not None
    context = codec.read(response.context_token)
    assert context is not None
    assert context.topic_id == record.public_id
    assert context.dialog_act == "ANSWERED"


@pytest.mark.asyncio
async def test_stale_context_topic_never_falls_through_to_another_active_record() -> None:
    other_record = knowledge_record(public_id="KB-WASTE-OTHER-01")
    repository = FakeRepository(records=(other_record,))
    codec = ContextTokenCodec(secret=b"x" * 32, clock=lambda: 1_000)
    token = codec.issue(
        last_intent=Intent.BULKY_WASTE.value,
        selected_region=None,
        answer_status="SUCCESS",
        dialog_act="ANSWERED",
        topic_id="KB-WASTE-REMOVED-01",
    )

    response = await service(repository).answer(
        ChatRequest(question="비용은요?", context_token=token)
    )

    assert response.answer_status == "FALLBACK"
    assert response.fallback.reason == "INSUFFICIENT_GROUNDING"
    assert response.sources == []
    assert repository.active_intents == [Intent.BULKY_WASTE]


@pytest.mark.asyncio
async def test_office_followup_without_region_asks_only_for_allowed_region() -> None:
    record = knowledge_record(public_id="KB-WASTE-OFFICE-01")
    repository = FakeRepository(records=(record,))
    codec = ContextTokenCodec(secret=b"x" * 32, clock=lambda: 1_000)
    token = codec.issue(
        last_intent=Intent.BULKY_WASTE.value,
        selected_region=None,
        answer_status="SUCCESS",
        dialog_act="ANSWERED",
        topic_id=record.public_id,
    )

    response = await service(repository).answer(
        ChatRequest(question="어디로 가요?", context_token=token)
    )

    assert response.answer_status == "FOLLOWUP"
    assert response.followup_options == ["아름동", "도담동", "조치원읍"]
    assert response.sources == []
    assert repository.office_queries == []
    assert response.context_token is not None
    context = codec.read(response.context_token)
    assert context is not None
    assert context.topic_id == record.public_id
    assert context.pending_slot == "REGION"
    assert context.dialog_act == "ASKING_SLOT"


@pytest.mark.asyncio
async def test_region_change_rebinds_only_the_allowed_official_office() -> None:
    record = knowledge_record(public_id="KB-WASTE-REGION-01")
    repository = FakeRepository(
        records=(record,),
        offices=(office_record(region=Region.DODAM_DONG),),
    )
    codec = ContextTokenCodec(secret=b"x" * 32, clock=lambda: 1_000)
    token = codec.issue(
        last_intent=Intent.BULKY_WASTE.value,
        selected_region="아름동",
        answer_status="SUCCESS",
        dialog_act="ANSWERED",
        topic_id=record.public_id,
    )

    response = await service(repository).answer(
        ChatRequest(question="도담동으로 바꿔줘", context_token=token)
    )

    assert response.answer_status == "SUCCESS"
    assert repository.office_queries == [(Region.DODAM_DONG, Intent.BULKY_WASTE)]
    assert response.office is not None
    assert response.context_token is not None
    context = codec.read(response.context_token)
    assert context is not None
    assert context.selected_region == "도담동"
    assert context.dialog_act == "CHANGING_REGION"


@pytest.mark.asyncio
async def test_explicit_new_intent_takes_precedence_over_prior_topic() -> None:
    old_record = knowledge_record(public_id="KB-WASTE-OLD-01")
    new_record = knowledge_record(
        public_id="KB-MOVE-NEW-01",
        intent=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        service_name="전입신고 방법",
        question_examples=("전입신고 어떻게 해요?",),
    )
    repository = FakeRepository(records=(old_record, new_record))
    codec = ContextTokenCodec(secret=b"x" * 32, clock=lambda: 1_000)
    token = codec.issue(
        last_intent=Intent.BULKY_WASTE.value,
        selected_region=None,
        answer_status="SUCCESS",
        dialog_act="ANSWERED",
        topic_id=old_record.public_id,
    )

    response = await service(repository).answer(
        ChatRequest(question="전입신고 어떻게 해요?", context_token=token)
    )

    assert response.answer_status == "SUCCESS"
    assert response.intent == Intent.MOVE_IN_RESIDENT_REGISTRATION.value
    assert [source.source_id for source in response.sources] == [new_record.public_id]
    assert response.context_token is not None
    context = codec.read(response.context_token)
    assert context is not None
    assert context.topic_id == new_record.public_id
    assert context.dialog_act == "CHANGING_TOPIC"


@pytest.mark.asyncio
async def test_invalid_context_silently_resets_to_followup() -> None:
    repository = FakeRepository()

    response = await service(repository).answer(
        ChatRequest(question="준비물은요?", context_token="tampered.token")
    )

    assert response.answer_status == "FOLLOWUP"
    assert response.intent == Intent.UNKNOWN.value
    assert repository.active_intents == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "reason", "intent", "event_is_stored", "masked_is_stored"),
    [
        (
            "침대 프레임 배출 수수료를 알려줘.",
            FallbackReason.INSUFFICIENT_GROUNDING,
            Intent.BULKY_WASTE,
            True,
            True,
        ),
        (
            "내 자동차세 체납액을 조회해줘.",
            FallbackReason.PERSONAL_LOOKUP,
            Intent.UNKNOWN,
            False,
            False,
        ),
        (
            "전입신고를 안 하면 법적으로 처벌받는지 판단해줘.",
            FallbackReason.LEGAL_JUDGMENT,
            Intent.UNKNOWN,
            False,
            False,
        ),
        (
            "오늘 세종시 날씨를 알려줘.",
            FallbackReason.OUT_OF_SCOPE,
            Intent.OUT_OF_SCOPE,
            False,
            False,
        ),
    ],
)
async def test_policy_fallback_event_matrix(
    question: str,
    reason: FallbackReason,
    intent: Intent,
    event_is_stored: bool,
    masked_is_stored: bool,
) -> None:
    repository = FakeRepository()

    response = await service(repository).answer(ChatRequest(question=question))

    assert response.answer_status == "FALLBACK"
    assert response.intent == intent.value
    assert response.fallback.reason == reason.value
    assert response.fallback.candidate_eligible is (reason is FallbackReason.INSUFFICIENT_GROUNDING)
    assert response.context_token is None
    assert len(repository.events) == int(event_is_stored)
    if not event_is_stored:
        assert repository.active_intents == []
        assert repository.office_queries == []
        return
    event = repository.events[0]
    assert event.intent is intent
    assert event.fallback_reason is reason
    assert (event.masked_question is not None) is masked_is_stored


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "reason"),
    [
        ("접수번호 SJ-2026-123456 처리됐어?", "PERSONAL_LOOKUP"),
        ("내가 기초생활수급 대상인지 판단해줘.", "LEGAL_JUDGMENT"),
        ("이 행정처분이 법적으로 부당한가요?", "LEGAL_JUDGMENT"),
    ],
)
async def test_generic_policy_fallback_does_not_persist_or_query_repository(
    question: str,
    reason: str,
) -> None:
    repository = FakeRepository(fail_reads=True, fail_event_write=True)

    response = await service(repository).answer(ChatRequest(question=question))

    assert response.answer_status == "FALLBACK"
    assert response.intent == "UNKNOWN"
    assert response.fallback.reason == reason
    assert response.fallback.candidate_eligible is False
    assert repository.active_intents == []
    assert repository.office_queries == []
    assert repository.events == []


@pytest.mark.asyncio
async def test_required_kb_read_failure_is_a_value_free_unavailable_error() -> None:
    repository = FakeRepository(fail_reads=True)

    with pytest.raises(ChatUnavailableError, match="^CHAT_UNAVAILABLE$") as captured:
        await service(repository).answer(ChatRequest(question="대형폐기물 배출 방법"))

    assert "대형폐기물" not in repr(captured.value)
    assert repository.events == []


@pytest.mark.asyncio
async def test_event_write_failure_does_not_discard_an_already_safe_answer() -> None:
    repository = FakeRepository(
        records=(knowledge_record(),),
        fail_event_write=True,
    )

    response = await service(repository).answer(ChatRequest(question="대형폐기물은 어떻게 버려요?"))

    assert response.answer_status == "SUCCESS"
    assert len(repository.events) == 1


@pytest.mark.asyncio
async def test_idempotency_claim_completes_with_only_the_safe_response_payload() -> None:
    repository = FakeRepository()
    idempotency = FakeIdempotencyRepository(
        IdempotencyClaim(status=IdempotencyClaimStatus.ACQUIRED)
    )
    sentinel = "김철수"

    response = await service(repository, idempotency_repository=idempotency).answer(
        ChatRequest(question=sentinel),
        request_id=REQUEST_ID,
        idempotency_key=IDEMPOTENCY_KEY,
    )

    assert response.answer_status == "FALLBACK"
    assert len(idempotency.claims) == 1
    assert idempotency.claims[0][0] == IDEMPOTENCY_KEY
    assert idempotency.claims[0][2] == CLAIM_TOKEN
    assert idempotency.claims[0][2] != REQUEST_ID
    assert len(idempotency.completions) == 1
    payload = idempotency.completions[0][3]
    assert "request_id" not in payload
    assert "context_token" not in payload
    assert "question" not in repr(payload).casefold()
    assert sentinel not in repr(idempotency.claims)
    assert sentinel not in repr(payload)
    assert idempotency.abandons == []


@pytest.mark.asyncio
async def test_completed_idempotency_replay_uses_the_current_correlation_request_id() -> None:
    stored = build_fallback_response(
        request_id=REQUEST_ID,
        intent=Intent.UNKNOWN,
        reason="PRIVACY_UNRESOLVED",
        office=None,
    ).model_dump(mode="json", exclude={"request_id", "context_token"})
    idempotency = FakeIdempotencyRepository(
        IdempotencyClaim(
            status=IdempotencyClaimStatus.COMPLETED,
            response_payload=stored,
        )
    )
    repository = FakeRepository(fail_reads=True, fail_event_write=True)

    response = await service(repository, idempotency_repository=idempotency).answer(
        ChatRequest(question="김철수"),
        request_id=RETRY_REQUEST_ID,
        idempotency_key=IDEMPOTENCY_KEY,
    )

    assert response.request_id == RETRY_REQUEST_ID
    assert response.context_token is None
    assert repository.active_intents == []
    assert repository.events == []
    assert idempotency.completions == []
    assert idempotency.abandons == []


@pytest.mark.asyncio
@pytest.mark.parametrize("answer_status", ["SUCCESS", "FOLLOWUP"])
async def test_completed_conversational_replay_reissues_a_memory_only_context_token(
    answer_status: str,
) -> None:
    stored_response: SuccessResponse | FollowupResponse
    if answer_status == "SUCCESS":
        stored_response = build_success_response(
            request_id=REQUEST_ID,
            record=knowledge_record(),
            office=None,
            confidence=0.99,
            context_token="old-token-must-not-persist",
        )
    else:
        stored_response = build_followup_response(
            request_id=REQUEST_ID,
            intent=Intent.UNKNOWN,
            confidence=None,
            option_ids=("intent.bulky-waste",),
            context_token="old-token-must-not-persist",
        )
    stored = stored_response.model_dump(
        mode="json",
        exclude={"request_id", "context_token"},
    )
    idempotency = FakeIdempotencyRepository(
        IdempotencyClaim(
            status=IdempotencyClaimStatus.COMPLETED,
            response_payload=stored,
        )
    )

    response = await service(
        FakeRepository(fail_reads=True, fail_event_write=True),
        idempotency_repository=idempotency,
    ).answer(
        ChatRequest(question="대형폐기물 안내", selected_region="아름동"),
        request_id=RETRY_REQUEST_ID,
        idempotency_key=IDEMPOTENCY_KEY,
    )

    assert response.request_id == RETRY_REQUEST_ID
    assert response.context_token is not None
    assert response.context_token != "old-token-must-not-persist"
    replayed_context = ContextTokenCodec(secret=b"x" * 32, clock=lambda: 1_000).read(
        response.context_token
    )
    assert replayed_context is not None
    assert replayed_context.answer_status == answer_status
    assert replayed_context.last_intent == response.intent
    assert replayed_context.selected_region == "아름동"
    assert "old-token-must-not-persist" not in repr(idempotency.claim.response_payload)


@pytest.mark.asyncio
async def test_conflicting_idempotency_claim_is_a_value_free_error() -> None:
    idempotency = FakeIdempotencyRepository(
        IdempotencyClaim(status=IdempotencyClaimStatus.CONFLICT)
    )

    with pytest.raises(IdempotencyConflictError):
        await service(FakeRepository(), idempotency_repository=idempotency).answer(
            ChatRequest(question="김철수"),
            request_id=REQUEST_ID,
            idempotency_key=IDEMPOTENCY_KEY,
        )

    assert idempotency.completions == []
    assert idempotency.abandons == []


@pytest.mark.asyncio
async def test_answer_failure_abandons_an_acquired_idempotency_claim() -> None:
    idempotency = FakeIdempotencyRepository(
        IdempotencyClaim(status=IdempotencyClaimStatus.ACQUIRED)
    )

    with pytest.raises(ChatUnavailableError):
        await service(
            FakeRepository(fail_reads=True),
            idempotency_repository=idempotency,
        ).answer(
            ChatRequest(question="대형폐기물 배출 방법"),
            request_id=REQUEST_ID,
            idempotency_key=IDEMPOTENCY_KEY,
        )

    assert len(idempotency.abandons) == 1
    assert idempotency.completions == []


@pytest.mark.asyncio
async def test_completion_failure_stays_claimed_and_blocks_duplicate_side_effects() -> None:
    idempotency = FakeIdempotencyRepository(
        IdempotencyClaim(status=IdempotencyClaimStatus.ACQUIRED),
        fail_complete=True,
    )

    with pytest.raises(ChatUnavailableError):
        await service(FakeRepository(), idempotency_repository=idempotency).answer(
            ChatRequest(question="김철수"),
            request_id=REQUEST_ID,
            idempotency_key=IDEMPOTENCY_KEY,
        )

    assert len(idempotency.completions) == 1
    assert idempotency.abandons == []


@pytest.mark.asyncio
async def test_completion_failure_rolls_back_failed_question_before_expired_lease_retry() -> None:
    repository = FakeRepository()
    idempotency = FakeIdempotencyRepository(
        IdempotencyClaim(status=IdempotencyClaimStatus.ACQUIRED),
        fail_complete=True,
    )
    ticks = iter((1_000_000, 6_000_000, 7_000_000, 12_000_000))
    selected = service(
        repository,
        clock_ns=lambda: next(ticks),
        idempotency_repository=idempotency,
    )
    request = ChatRequest(question="침대 프레임 수수료를 알려 주세요.")

    with pytest.raises(ChatUnavailableError, match="^CHAT_UNAVAILABLE$"):
        await selected.answer(
            request,
            request_id=REQUEST_ID,
            idempotency_key=IDEMPOTENCY_KEY,
        )

    assert repository.events == []
    assert idempotency.committed_events == []

    idempotency.fail_complete = False
    response = await selected.answer(
        request,
        request_id=RETRY_REQUEST_ID,
        idempotency_key=IDEMPOTENCY_KEY,
    )

    assert response.answer_status == "FALLBACK"
    assert repository.events == []
    assert len(idempotency.committed_events) == 1
    assert idempotency.committed_events[0].fallback_reason is FallbackReason.INSUFFICIENT_GROUNDING


@pytest.mark.asyncio
async def test_expired_claim_completion_rule_error_is_value_free_unavailable() -> None:
    repository = FakeRepository()
    idempotency = FakeIdempotencyRepository(
        IdempotencyClaim(status=IdempotencyClaimStatus.ACQUIRED),
        complete_rule_error=True,
    )

    with pytest.raises(ChatUnavailableError, match="^CHAT_UNAVAILABLE$") as captured:
        await service(repository, idempotency_repository=idempotency).answer(
            ChatRequest(question="침대 프레임 수수료를 알려 주세요."),
            request_id=REQUEST_ID,
            idempotency_key=IDEMPOTENCY_KEY,
        )

    assert "INVALID_CANDIDATE_STATE" not in repr(captured.value)
    assert repository.events == []
    assert idempotency.committed_events == []


@pytest.mark.asyncio
async def test_expired_claim_abandon_rule_error_cannot_mask_original_failure() -> None:
    idempotency = FakeIdempotencyRepository(
        IdempotencyClaim(status=IdempotencyClaimStatus.ACQUIRED),
        abandon_rule_error=True,
    )

    with pytest.raises(ChatUnavailableError, match="^CHAT_UNAVAILABLE$") as captured:
        await service(
            FakeRepository(fail_reads=True),
            idempotency_repository=idempotency,
        ).answer(
            ChatRequest(question="대형폐기물 배출 방법"),
            request_id=REQUEST_ID,
            idempotency_key=IDEMPOTENCY_KEY,
        )

    assert "INVALID_CANDIDATE_STATE" not in repr(captured.value)
    assert len(idempotency.abandons) == 1


@pytest.mark.asyncio
async def test_abandon_cleanup_programming_error_cannot_mask_original_failure() -> None:
    idempotency = FakeIdempotencyRepository(
        IdempotencyClaim(status=IdempotencyClaimStatus.ACQUIRED),
        abandon_exception=RuntimeError("synthetic-cleanup-error"),
    )

    with pytest.raises(ChatUnavailableError, match="^CHAT_UNAVAILABLE$") as captured:
        await service(
            FakeRepository(fail_reads=True),
            idempotency_repository=idempotency,
        ).answer(
            ChatRequest(question="대형폐기물 배출 방법"),
            request_id=REQUEST_ID,
            idempotency_key=IDEMPOTENCY_KEY,
        )

    assert "synthetic-cleanup-error" not in repr(captured.value)
    assert len(idempotency.abandons) == 1


@pytest.mark.asyncio
async def test_correlation_request_id_is_rejected_as_a_claim_token() -> None:
    idempotency = FakeIdempotencyRepository(
        IdempotencyClaim(status=IdempotencyClaimStatus.ACQUIRED)
    )
    selected = service(
        FakeRepository(),
        idempotency_repository=idempotency,
        idempotency_claim_factory=lambda: REQUEST_ID,
    )

    with pytest.raises(ChatUnavailableError):
        await selected.answer(
            ChatRequest(question="김철수"),
            request_id=REQUEST_ID,
            idempotency_key=IDEMPOTENCY_KEY,
        )

    assert idempotency.claims == []


@pytest.mark.asyncio
async def test_idempotency_key_fails_closed_without_durable_repository() -> None:
    with pytest.raises(ChatUnavailableError):
        await service(FakeRepository()).answer(
            ChatRequest(question="김철수"),
            request_id=REQUEST_ID,
            idempotency_key=IDEMPOTENCY_KEY,
        )
