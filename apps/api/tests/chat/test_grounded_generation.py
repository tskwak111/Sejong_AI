from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

import pytest

from sejong_ai_api.chat.idempotency import IdempotencyClaim, IdempotencyClaimStatus
from sejong_ai_api.chat.service import ChatUnavailableError
from sejong_ai_api.contracts.chat import ChatRequest, SuccessResponse
from sejong_ai_api.llm.chat_contracts import (
    GeneratedChatDraft,
    GroundedChatOutcomeCode,
    GroundedChatRequest,
    GroundedChatResult,
)

from .test_service import (
    IDEMPOTENCY_KEY,
    REQUEST_ID,
    RETRY_REQUEST_ID,
    FakeIdempotencyRepository,
    FakeRepository,
    knowledge_record,
    office_record,
    service,
)


def _valid_draft(*, summary: str = "승인된 안내 요약을 쉽게 정리") -> GeneratedChatDraft:
    return GeneratedChatDraft(
        summary=summary,
        procedure_step_ids=["STEP-01"],
        required_document_ids=[],
        processing_time_id=None,
        fee_id=None,
        department_id="DEPT-01",
    )


@dataclass
class CountingGenerator:
    result: GroundedChatResult | None = field(
        default_factory=lambda: GroundedChatResult(
            code=GroundedChatOutcomeCode.SUCCESS,
            draft=_valid_draft(),
        )
    )
    error: Exception | None = None
    requests: list[GroundedChatRequest] = field(default_factory=list)

    async def generate(self, request: GroundedChatRequest) -> GroundedChatResult:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        if self.result is None:
            raise AssertionError("test generator result required")
        return self.result


@pytest.mark.asyncio
async def test_grounded_supported_request_uses_one_generated_answer_with_server_metadata() -> None:
    raw_phone = "010-1234-5678"
    record = knowledge_record()
    repository = FakeRepository(records=(record,), offices=(office_record(),))
    generator = CountingGenerator()

    response = await service(repository, answer_generator=generator).answer(
        ChatRequest(
            question=f"대형폐기물은 어떻게 버려요? 연락처는 {raw_phone}",
            selected_region="아름동",
        )
    )

    assert response.answer_status == "SUCCESS"
    assert response.answer_mode == "GENERATED"
    assert response.summary == "승인된 안내 요약을 쉽게 정리"
    assert response.procedure_steps == ["승인된 절차를 확인하세요."]
    assert response.required_documents == []
    assert response.processing_time is None
    assert response.fee is None
    assert response.department == "민원 담당 부서"
    assert response.sources[0].source_id == record.public_id
    assert response.office is not None
    assert response.office.id == "OFFICE-TEST-01"
    assert len(generator.requests) == 1
    assert raw_phone not in generator.requests[0].masked_question
    assert "[전화번호]" in generator.requests[0].masked_question
    assert record.source_url not in repr(generator.requests[0])
    assert record.public_id not in repr(generator.requests[0])
    assert raw_phone not in repr(repository.events)
    assert response.summary not in repr(repository.events)


@pytest.mark.asyncio
async def test_generator_disabled_keeps_complete_official_template() -> None:
    record = knowledge_record()

    response = await service(FakeRepository(records=(record,))).answer(
        ChatRequest(question="대형폐기물은 어떻게 버려요?")
    )

    assert response.answer_status == "SUCCESS"
    assert response.answer_mode == "TEMPLATE"
    assert response.summary == record.answer_summary
    assert response.procedure_steps == list(record.procedure_steps)
    assert response.department == record.department
    assert response.sources[0].source_id == record.public_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "question",
    [
        "김철수",
        "신고하고 싶어요.",
        "침대 프레임 배출 수수료를 알려줘.",
        "내 자동차세 체납액을 조회해줘.",
        "전입신고를 안 하면 법적으로 처벌받는지 판단해줘.",
        "오늘 세종시 날씨를 알려줘.",
    ],
)
async def test_non_grounded_and_policy_paths_never_call_generator(question: str) -> None:
    generator = CountingGenerator()

    response = await service(FakeRepository(), answer_generator=generator).answer(
        ChatRequest(question=question)
    )

    assert response.answer_status in {"FOLLOWUP", "FALLBACK"}
    assert generator.requests == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "outcome",
    [
        GroundedChatOutcomeCode.ATTEMPT_CAP,
        GroundedChatOutcomeCode.TIMEOUT,
        GroundedChatOutcomeCode.TRANSPORT,
        GroundedChatOutcomeCode.RATE_LIMIT,
        GroundedChatOutcomeCode.AUTH,
        GroundedChatOutcomeCode.HTTP_ERROR,
        GroundedChatOutcomeCode.EMPTY,
        GroundedChatOutcomeCode.TRUNCATED,
        GroundedChatOutcomeCode.SCHEMA_INVALID,
        GroundedChatOutcomeCode.INPUT_LIMIT,
    ],
)
async def test_typed_generator_failures_use_complete_template(
    outcome: GroundedChatOutcomeCode,
) -> None:
    record = knowledge_record()
    generator = CountingGenerator(result=GroundedChatResult(code=outcome))

    response = await service(
        FakeRepository(records=(record,)),
        answer_generator=generator,
    ).answer(ChatRequest(question="대형폐기물은 어떻게 버려요?"))

    assert response.answer_status == "SUCCESS"
    assert response.answer_mode == "TEMPLATE"
    assert response.summary == record.answer_summary
    assert response.procedure_steps == list(record.procedure_steps)
    assert response.department == record.department
    assert response.sources[0].source_id == record.public_id
    assert len(generator.requests) == 1


@pytest.mark.asyncio
async def test_generator_exception_is_discarded_without_persistence_or_response_leak(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sentinel = "PROVIDER-PRIVATE-ERROR-SENTINEL"
    record = knowledge_record()
    repository = FakeRepository(records=(record,))
    generator = CountingGenerator(error=RuntimeError(sentinel))

    response = await service(repository, answer_generator=generator).answer(
        ChatRequest(question="대형폐기물은 어떻게 버려요?")
    )

    assert cast(SuccessResponse, response).answer_mode == "TEMPLATE"
    assert sentinel not in repr(response)
    assert sentinel not in repr(repository.events)
    assert sentinel not in caplog.text
    assert len(repository.events) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "draft",
    [
        _valid_draft(summary="승인되지 않은 새로운 사실입니다."),
        GeneratedChatDraft(
            summary="승인된 안내 요약입니다.",
            procedure_step_ids=["STEP-99"],
            required_document_ids=[],
            processing_time_id=None,
            fee_id=None,
            department_id="DEPT-01",
        ),
    ],
)
async def test_rejected_generated_draft_falls_back_to_complete_template(
    draft: GeneratedChatDraft,
) -> None:
    record = knowledge_record()
    generator = CountingGenerator(
        result=GroundedChatResult(
            code=GroundedChatOutcomeCode.SUCCESS,
            draft=draft,
        )
    )

    response = await service(
        FakeRepository(records=(record,)),
        answer_generator=generator,
    ).answer(ChatRequest(question="대형폐기물은 어떻게 버려요?"))

    assert cast(SuccessResponse, response).answer_mode == "TEMPLATE"
    assert response.summary == record.answer_summary
    assert response.procedure_steps == list(record.procedure_steps)
    assert response.department == record.department
    assert response.sources[0].source_id == record.public_id


@pytest.mark.asyncio
async def test_completed_same_key_replay_never_calls_generator_twice() -> None:
    record = knowledge_record()
    generator = CountingGenerator()
    idempotency = FakeIdempotencyRepository(
        IdempotencyClaim(status=IdempotencyClaimStatus.ACQUIRED)
    )
    selected = service(
        FakeRepository(records=(record,)),
        answer_generator=generator,
        idempotency_repository=idempotency,
    )
    request = ChatRequest(question="대형폐기물은 어떻게 버려요?")

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

    assert cast(SuccessResponse, first).answer_mode == "GENERATED"
    assert cast(SuccessResponse, replay).answer_mode == "GENERATED"
    assert replay.request_id == RETRY_REQUEST_ID
    assert len(generator.requests) == 1
    assert len(idempotency.completions) == 1
    assert len(idempotency.committed_events) == 1


@pytest.mark.asyncio
async def test_commit_uncertainty_never_retries_or_abandons_generated_attempt() -> None:
    generator = CountingGenerator()
    idempotency = FakeIdempotencyRepository(
        IdempotencyClaim(status=IdempotencyClaimStatus.ACQUIRED),
        fail_complete=True,
    )

    with pytest.raises(ChatUnavailableError, match="^CHAT_UNAVAILABLE$"):
        await service(
            FakeRepository(records=(knowledge_record(),)),
            answer_generator=generator,
            idempotency_repository=idempotency,
        ).answer(
            ChatRequest(question="대형폐기물은 어떻게 버려요?"),
            request_id=REQUEST_ID,
            idempotency_key=IDEMPOTENCY_KEY,
        )

    assert len(generator.requests) == 1
    assert len(idempotency.completions) == 1
    assert idempotency.abandons == []
    assert idempotency.committed_events == []


@pytest.mark.asyncio
async def test_in_progress_same_key_returns_template_without_generation_or_write() -> None:
    record = knowledge_record()
    generator = CountingGenerator()
    idempotency = FakeIdempotencyRepository(
        IdempotencyClaim(status=IdempotencyClaimStatus.IN_PROGRESS)
    )
    repository = FakeRepository(records=(record,))

    response = await service(
        repository,
        answer_generator=generator,
        idempotency_repository=idempotency,
    ).answer(
        ChatRequest(question="대형폐기물은 어떻게 버려요?"),
        request_id=RETRY_REQUEST_ID,
        idempotency_key=IDEMPOTENCY_KEY,
    )

    assert response.answer_status == "SUCCESS"
    assert cast(SuccessResponse, response).answer_mode == "TEMPLATE"
    assert response.summary == record.answer_summary
    assert generator.requests == []
    assert repository.events == []
    assert idempotency.completions == []
    assert idempotency.committed_events == []
    assert idempotency.abandons == []
