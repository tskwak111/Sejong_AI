from collections.abc import Sequence
from datetime import date
from uuid import UUID

import pytest

from sejong_ai_api.db.models import AnswerStatus, Intent, KnowledgeRecord
from sejong_ai_api.llm.contracts import (
    GeneratedAnswer,
    GenerationOutcome,
    GroundedFixture,
    OutcomeCode,
    TokenUsage,
)
from sejong_ai_api.llm.evaluation import EvaluationCaseResult, SyntheticEvaluationService
from sejong_ai_api.llm.fixtures import PreparationCode, SyntheticFixture


class FakeRepository:
    def __init__(self, records: Sequence[KnowledgeRecord]) -> None:
        self._records = tuple(records)
        self.intents: list[Intent] = []

    async def list_active_kb(self, intent: Intent) -> tuple[KnowledgeRecord, ...]:
        self.intents.append(intent)
        return tuple(record for record in self._records if record.category is intent)


class StatefulRepository:
    def __init__(self, first_record: KnowledgeRecord) -> None:
        self._first_record = first_record
        self.calls = 0

    async def list_active_kb(self, intent: Intent) -> tuple[KnowledgeRecord, ...]:
        self.calls += 1
        if self.calls == 1 and self._first_record.category is intent:
            return (self._first_record,)
        return ()


class SpyProvider:
    def __init__(self, outcomes: Sequence[GenerationOutcome]) -> None:
        self._outcomes = list(outcomes)
        self.fixtures: list[GroundedFixture] = []

    @property
    def calls(self) -> int:
        return len(self.fixtures)

    async def generate(self, fixture: GroundedFixture) -> GenerationOutcome:
        self.fixtures.append(fixture)
        if not self._outcomes:
            raise AssertionError("UNEXPECTED_PROVIDER_CALL")
        return self._outcomes.pop(0)


def _fixture(
    fixture_id: str = "T-01",
    question: str = "이사했는데 전입신고 어떻게 해요?",
    intent: Intent = Intent.MOVE_IN_RESIDENT_REGISTRATION,
) -> SyntheticFixture:
    return SyntheticFixture(
        fixture_id=fixture_id,
        question=question,
        expected_intent=intent,
        expected_status=AnswerStatus.SUCCESS,
        contains_pii=False,
    )


def _move_in_record(
    *,
    examples: tuple[str, ...] = (
        "이사했는데 전입신고 어떻게 해요?",
        "전입신고에 필요한 서류가 뭐예요?",
    ),
) -> KnowledgeRecord:
    return KnowledgeRecord(
        public_id="KB-MOVE-001",
        category=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        service_name="전입신고",
        answer_summary="이사한 날부터 14일 이내에 전입신고를 합니다.",
        procedure_steps=("정부24 또는 새 주소지 행정복지센터에서 신고합니다.",),
        required_documents=("신분증",),
        processing_time="즉시",
        fee="없음",
        department="주민등록 담당부서",
        source_title="정부24 전입신고 안내",
        source_url="https://www.gov.kr/",
        last_verified_at=date(2026, 7, 20),
        caution=None,
        question_examples=examples,
    )


def _ungrounded_move_in_record() -> KnowledgeRecord:
    return KnowledgeRecord(
        public_id="KB-MOVE-UNRELATED",
        category=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        service_name="민원 안내",
        answer_summary="승인된 일반 안내입니다.",
        procedure_steps=("담당 부서에 문의합니다.",),
        required_documents=(),
        processing_time=None,
        fee=None,
        department="민원 담당부서",
        source_title="공식 민원 안내",
        source_url="https://www.sejong.go.kr/",
        last_verified_at=date(2026, 7, 20),
        caution=None,
        question_examples=("일반 민원은 어디에 문의하나요?",),
    )


def _answer() -> GeneratedAnswer:
    return GeneratedAnswer(
        summary="전입신고 절차를 안내합니다.",
        procedure_steps=["정부24 또는 행정복지센터에서 신고합니다."],
        required_documents=["신분증"],
        processing_time="즉시",
        fee="없음",
        department="주민등록 담당부서",
    )


def _outcome(
    code: OutcomeCode = OutcomeCode.SUCCESS,
    *,
    attempts_used: int = 1,
    attempt_outcomes: tuple[OutcomeCode, ...] | None = None,
) -> GenerationOutcome:
    if attempt_outcomes is None:
        attempt_outcomes = () if attempts_used == 0 else (code,) * attempts_used
    return GenerationOutcome(
        code=code,
        answer=_answer() if code is OutcomeCode.SUCCESS else None,
        usage=TokenUsage(20, 0, 10),
        attempts_used=attempts_used,
        attempt_outcomes=attempt_outcomes,
    )


def _assert_preparation_failure(
    run_code: OutcomeCode | PreparationCode,
    *,
    expected: PreparationCode,
) -> None:
    assert run_code is expected


@pytest.mark.parametrize(
    ("outcome_code", "attempts_used", "attempt_outcomes", "expected_error"),
    [
        (
            OutcomeCode.TIMEOUT,
            1,
            [OutcomeCode.TIMEOUT],
            "ATTEMPT_OUTCOMES_INVALID",
        ),
        (
            OutcomeCode.TIMEOUT,
            1,
            ("provider-content",),
            "ATTEMPT_OUTCOMES_INVALID",
        ),
        (
            OutcomeCode.TIMEOUT,
            2,
            (OutcomeCode.TIMEOUT,),
            "ATTEMPT_OUTCOMES_LENGTH_INVALID",
        ),
        (
            PreparationCode.PRIVACY_UNRESOLVED,
            0,
            (OutcomeCode.TIMEOUT,),
            "PREPARATION_ATTEMPT_OUTCOMES_INVALID",
        ),
    ],
)
def test_evaluation_case_result_rejects_mutable_inconsistent_or_content_trace(
    outcome_code: OutcomeCode | PreparationCode,
    attempts_used: int,
    attempt_outcomes: object,
    expected_error: str,
) -> None:
    with pytest.raises(ValueError, match=expected_error):
        EvaluationCaseResult(
            fixture_id="T-01",
            repetition=1,
            outcome_code=outcome_code,
            attempts_used=attempts_used,
            attempt_outcomes=attempt_outcomes,  # type: ignore[arg-type]
            usage=TokenUsage(0, 0, 0),
            latency_ms=0,
            source_id=None,
            used_template_fallback=False,
        )


@pytest.mark.asyncio
async def test_privacy_unresolved_stops_before_repository_and_provider() -> None:
    repository = FakeRepository((_move_in_record(),))
    provider = SpyProvider((_outcome(),))
    fixture = _fixture(question="질문\u202e값")
    service = SyntheticEvaluationService(
        fixtures=(fixture,),
        repository=repository,
        provider=provider,
    )

    run = await service.run(repetitions=3)

    assert run.planned_generations == 3
    assert len(run.cases) == 1
    result = run.cases[0]
    _assert_preparation_failure(
        result.outcome_code,
        expected=PreparationCode.PRIVACY_UNRESOLVED,
    )
    assert result.attempts_used == 0
    assert result.attempt_outcomes == ()
    assert result.usage == TokenUsage(0, 0, 0)
    assert result.latency_ms == 0
    assert result.source_id is None
    assert result.used_template_fallback is False
    assert repository.intents == []
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_non_success_classification_stops_before_repository_and_provider() -> None:
    repository = FakeRepository((_move_in_record(),))
    provider = SpyProvider((_outcome(),))
    service = SyntheticEvaluationService(
        fixtures=(_fixture(question="신고하고 싶어요."),),
        repository=repository,
        provider=provider,
    )

    run = await service.run()

    assert len(run.cases) == 1
    result = run.cases[0]
    _assert_preparation_failure(
        result.outcome_code,
        expected=PreparationCode.NOT_DETERMINISTIC_SUCCESS,
    )
    assert result.attempts_used == result.latency_ms == 0
    assert result.attempt_outcomes == ()
    assert result.usage == TokenUsage(0, 0, 0)
    assert result.source_id is None
    assert repository.intents == []
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_classification_that_disagrees_with_canonical_expectation_stops() -> None:
    repository = FakeRepository((_move_in_record(),))
    provider = SpyProvider((_outcome(),))
    service = SyntheticEvaluationService(
        fixtures=(_fixture(intent=Intent.LOCAL_TAX_GENERAL),),
        repository=repository,
        provider=provider,
    )

    run = await service.run()

    assert len(run.cases) == 1
    result = run.cases[0]
    _assert_preparation_failure(
        result.outcome_code,
        expected=PreparationCode.NOT_DETERMINISTIC_SUCCESS,
    )
    assert result.attempts_used == result.latency_ms == 0
    assert result.attempt_outcomes == ()
    assert result.usage == TokenUsage(0, 0, 0)
    assert result.source_id is None
    assert repository.intents == []
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_no_active_record_stops_before_provider() -> None:
    repository = FakeRepository(())
    provider = SpyProvider((_outcome(),))
    service = SyntheticEvaluationService(
        fixtures=(_fixture(),),
        repository=repository,
        provider=provider,
    )

    run = await service.run()

    assert len(run.cases) == 1
    result = run.cases[0]
    _assert_preparation_failure(
        result.outcome_code,
        expected=PreparationCode.INSUFFICIENT_GROUNDING,
    )
    assert result.attempts_used == result.latency_ms == 0
    assert result.attempt_outcomes == ()
    assert result.usage == TokenUsage(0, 0, 0)
    assert result.source_id is None
    assert repository.intents == [Intent.MOVE_IN_RESIDENT_REGISTRATION]
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_grounding_failure_stops_before_provider() -> None:
    repository = FakeRepository((_ungrounded_move_in_record(),))
    provider = SpyProvider((_outcome(),))
    service = SyntheticEvaluationService(
        fixtures=(_fixture(),),
        repository=repository,
        provider=provider,
    )

    run = await service.run()

    assert len(run.cases) == 1
    result = run.cases[0]
    _assert_preparation_failure(
        result.outcome_code,
        expected=PreparationCode.INSUFFICIENT_GROUNDING,
    )
    assert result.attempts_used == result.latency_ms == 0
    assert result.attempt_outcomes == ()
    assert result.usage == TokenUsage(0, 0, 0)
    assert result.source_id is None
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_grounded_success_calls_provider_and_binds_server_source() -> None:
    record = _move_in_record()
    trace = (OutcomeCode.RATE_LIMIT, OutcomeCode.SUCCESS)
    provider = SpyProvider((_outcome(attempts_used=2, attempt_outcomes=trace),))
    service = SyntheticEvaluationService(
        fixtures=(_fixture(),),
        repository=FakeRepository((record,)),
        provider=provider,
    )

    run = await service.run(repetitions=1)

    assert provider.calls == 1
    assert provider.fixtures[0] == GroundedFixture(
        fixture_id="T-01",
        masked_question="이사했는데 전입신고 어떻게 해요?",
        intent=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        record=record,
    )
    assert run.cases[0].outcome_code is OutcomeCode.SUCCESS
    assert run.cases[0].attempt_outcomes == trace
    assert run.cases[0].source_id == record.public_id
    assert run.cases[0].used_template_fallback is False
    assert len(run.review_samples) == 1
    assert run.review_samples[0].fixture_id == "T-01"
    assert run.review_samples[0].question == "이사했는데 전입신고 어떻게 해요?"
    assert run.review_samples[0].answer == _answer()


@pytest.mark.asyncio
async def test_provider_failure_uses_server_template_fallback_without_review_sample() -> None:
    record = _move_in_record()
    provider = SpyProvider((_outcome(OutcomeCode.TIMEOUT),))
    issued_request_ids: list[UUID] = []

    def issue_request_id() -> UUID:
        request_id = UUID("00000000-0000-4000-8000-000000000001")
        issued_request_ids.append(request_id)
        return request_id

    service = SyntheticEvaluationService(
        fixtures=(_fixture(),),
        repository=FakeRepository((record,)),
        provider=provider,
        uuid_factory=issue_request_id,
    )

    run = await service.run(repetitions=1)

    assert provider.calls == 1
    result = run.cases[0]
    assert result.outcome_code is OutcomeCode.TIMEOUT
    assert result.source_id == record.public_id
    assert result.used_template_fallback is True
    assert issued_request_ids == [UUID("00000000-0000-4000-8000-000000000001")]
    assert run.review_samples == ()


@pytest.mark.asyncio
async def test_run_sorts_fixture_ids_and_repeats_sequentially() -> None:
    first = _fixture()
    second = _fixture(
        fixture_id="T-02",
        question="전입신고에 필요한 서류가 뭐예요?",
    )
    provider = SpyProvider(tuple(_outcome() for _ in range(4)))
    service = SyntheticEvaluationService(
        fixtures=(second, first),
        repository=FakeRepository((_move_in_record(),)),
        provider=provider,
    )

    run = await service.run(repetitions=2)

    assert run.planned_generations == 4
    assert tuple((case.fixture_id, case.repetition) for case in run.cases) == (
        ("T-01", 1),
        ("T-01", 2),
        ("T-02", 1),
        ("T-02", 2),
    )
    assert tuple(fixture.fixture_id for fixture in provider.fixtures) == (
        "T-01",
        "T-01",
        "T-02",
        "T-02",
    )
    assert tuple(sample.fixture_id for sample in run.review_samples) == ("T-01", "T-02")


@pytest.mark.asyncio
async def test_each_repetition_revalidates_active_grounding_and_stops_on_drift() -> None:
    record = _move_in_record()
    repository = StatefulRepository(record)
    provider = SpyProvider((_outcome(),))
    service = SyntheticEvaluationService(
        fixtures=(_fixture(),),
        repository=repository,
        provider=provider,
    )

    run = await service.run(repetitions=3)

    assert run.planned_generations == 3
    assert len(run.cases) == 2
    assert run.cases[0].outcome_code is OutcomeCode.SUCCESS
    assert run.cases[0].repetition == 1
    second = run.cases[1]
    assert second.outcome_code is PreparationCode.INSUFFICIENT_GROUNDING
    assert second.repetition == 2
    assert second.attempts_used == second.latency_ms == 0
    assert second.attempt_outcomes == ()
    assert second.usage == TokenUsage(0, 0, 0)
    assert second.source_id is None
    assert second.used_template_fallback is False
    assert repository.calls == 2
    assert provider.calls == 1
    assert tuple(sample.fixture_id for sample in run.review_samples) == ("T-01",)


@pytest.mark.asyncio
@pytest.mark.parametrize("terminal_code", [OutcomeCode.ATTEMPT_CAP, OutcomeCode.INPUT_LIMIT])
async def test_run_wide_terminal_outcome_stops_remaining_cases(
    terminal_code: OutcomeCode,
) -> None:
    provider = SpyProvider((_outcome(terminal_code, attempts_used=0), _outcome()))
    service = SyntheticEvaluationService(
        fixtures=(_fixture(),),
        repository=FakeRepository((_move_in_record(),)),
        provider=provider,
    )

    run = await service.run(repetitions=3)

    assert len(run.cases) == 1
    assert run.cases[0].outcome_code is terminal_code
    assert run.cases[0].used_template_fallback is True
    assert provider.calls == 1
