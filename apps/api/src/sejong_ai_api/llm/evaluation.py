"""Sequential, fail-closed evaluation over server-owned synthetic fixtures."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from time import perf_counter_ns
from typing import Protocol
from uuid import UUID, uuid4

from sejong_ai_api.chat.classification import SafeQuestion, classify_question
from sejong_ai_api.chat.grounding import evaluate_grounding
from sejong_ai_api.chat.response import build_success_response
from sejong_ai_api.chat.retrieval import rank_active_knowledge
from sejong_ai_api.db.models import AnswerStatus, Intent, KnowledgeRecord
from sejong_ai_api.llm.contracts import (
    GeneratedAnswer,
    GenerationOutcome,
    GroundedFixture,
    OutcomeCode,
    TokenUsage,
)
from sejong_ai_api.llm.fixtures import (
    PreparationCode,
    PreparedCaseFailure,
    SyntheticFixture,
)
from sejong_ai_api.privacy.redaction import redact_question

_RUN_TERMINAL_CODES = frozenset({OutcomeCode.ATTEMPT_CAP, OutcomeCode.INPUT_LIMIT})
_ZERO_USAGE = TokenUsage(0, 0, 0)


class EvaluationRepository(Protocol):
    async def list_active_kb(self, intent: Intent) -> Sequence[KnowledgeRecord]: ...


class EvaluationProvider(Protocol):
    async def generate(self, fixture: GroundedFixture) -> GenerationOutcome: ...


@dataclass(frozen=True, slots=True)
class ReviewSample:
    fixture_id: str
    question: str
    answer: GeneratedAnswer


@dataclass(frozen=True, slots=True)
class EvaluationCaseResult:
    fixture_id: str
    repetition: int
    outcome_code: OutcomeCode | PreparationCode
    attempts_used: int
    attempt_outcomes: tuple[OutcomeCode, ...]
    usage: TokenUsage
    latency_ms: int
    source_id: str | None
    used_template_fallback: bool

    def __post_init__(self) -> None:
        if type(self.attempt_outcomes) is not tuple or any(
            type(outcome) is not OutcomeCode for outcome in self.attempt_outcomes
        ):
            raise ValueError("ATTEMPT_OUTCOMES_INVALID")
        if type(self.outcome_code) is OutcomeCode and (
            len(self.attempt_outcomes) != self.attempts_used
        ):
            raise ValueError("ATTEMPT_OUTCOMES_LENGTH_INVALID")
        if type(self.outcome_code) is PreparationCode and self.attempt_outcomes:
            raise ValueError("PREPARATION_ATTEMPT_OUTCOMES_INVALID")


@dataclass(frozen=True, slots=True)
class EvaluationRun:
    planned_generations: int
    cases: tuple[EvaluationCaseResult, ...]
    review_samples: tuple[ReviewSample, ...]


class SyntheticEvaluationService:
    """Run the approved synthetic fixtures through deterministic gates first."""

    def __init__(
        self,
        *,
        fixtures: Sequence[SyntheticFixture],
        repository: EvaluationRepository,
        provider: EvaluationProvider,
        monotonic_ns: Callable[[], int] = perf_counter_ns,
        uuid_factory: Callable[[], UUID] = uuid4,
    ) -> None:
        if not isinstance(fixtures, Sequence) or isinstance(fixtures, (str, bytes)):
            raise ValueError("SYNTHETIC_FIXTURES_INVALID")
        normalized = tuple(fixtures)
        if not normalized or any(type(fixture) is not SyntheticFixture for fixture in normalized):
            raise ValueError("SYNTHETIC_FIXTURES_INVALID")
        fixture_ids = tuple(fixture.fixture_id for fixture in normalized)
        if len(set(fixture_ids)) != len(fixture_ids):
            raise ValueError("SYNTHETIC_FIXTURES_INVALID")
        self._fixtures = tuple(sorted(normalized, key=lambda fixture: fixture.fixture_id))
        self._repository = repository
        self._provider = provider
        self._monotonic_ns = monotonic_ns
        self._uuid_factory = uuid_factory

    async def prepare_case(
        self,
        fixture: SyntheticFixture,
    ) -> GroundedFixture | PreparedCaseFailure:
        """Apply privacy, deterministic classification, ACTIVE retrieval and grounding."""
        if type(fixture) is not SyntheticFixture:
            raise ValueError("SYNTHETIC_FIXTURE_INVALID")
        if fixture.expected_status is not AnswerStatus.SUCCESS or fixture.contains_pii:
            return PreparedCaseFailure(PreparationCode.NOT_DETERMINISTIC_SUCCESS)

        redaction = redact_question(fixture.question)
        if redaction.masked_text is None or not redaction.safe_for_synthetic_provider:
            return PreparedCaseFailure(PreparationCode.PRIVACY_UNRESOLVED)

        safe_question = SafeQuestion(redaction)
        classification = classify_question(safe_question)
        if (
            classification.followup_required
            or classification.fallback_reason is not None
            or classification.intent is Intent.UNKNOWN
            or classification.intent is not fixture.expected_intent
        ):
            return PreparedCaseFailure(PreparationCode.NOT_DETERMINISTIC_SUCCESS)

        records = await self._repository.list_active_kb(classification.intent)
        ranked = rank_active_knowledge(safe_question, classification.intent, records)
        top = ranked[0] if ranked else None
        grounding = evaluate_grounding(
            safe_question,
            classification.intent,
            top.record if top is not None else None,
        )
        if not grounding.is_grounded or grounding.record is None:
            return PreparedCaseFailure(PreparationCode.INSUFFICIENT_GROUNDING)

        return GroundedFixture(
            fixture_id=fixture.fixture_id,
            masked_question=safe_question.text,
            intent=classification.intent,
            record=grounding.record,
        )

    async def run(self, *, repetitions: int = 3) -> EvaluationRun:
        """Run fixtures by ID and repetition, stopping on preparation or run-wide limits."""
        if type(repetitions) is not int or repetitions <= 0:
            raise ValueError("EVALUATION_REPETITIONS_INVALID")

        planned_generations = len(self._fixtures) * repetitions
        cases: list[EvaluationCaseResult] = []
        review_samples: list[ReviewSample] = []

        for fixture in self._fixtures:
            for repetition in range(1, repetitions + 1):
                prepared = await self.prepare_case(fixture)
                if isinstance(prepared, PreparedCaseFailure):
                    cases.append(
                        EvaluationCaseResult(
                            fixture_id=fixture.fixture_id,
                            repetition=repetition,
                            outcome_code=prepared.code,
                            attempts_used=0,
                            attempt_outcomes=(),
                            usage=_ZERO_USAGE,
                            latency_ms=0,
                            source_id=None,
                            used_template_fallback=False,
                        )
                    )
                    return EvaluationRun(
                        planned_generations=planned_generations,
                        cases=tuple(cases),
                        review_samples=tuple(review_samples),
                    )

                started_ns = self._read_monotonic_ns()
                outcome = await self._provider.generate(prepared)
                latency_ms = max(0, (self._read_monotonic_ns() - started_ns) // 1_000_000)
                if type(outcome) is not GenerationOutcome:
                    raise ValueError("GENERATION_OUTCOME_INVALID")

                used_template_fallback = outcome.code is not OutcomeCode.SUCCESS
                if used_template_fallback:
                    self._build_template_answer(prepared.record)
                elif not any(sample.fixture_id == fixture.fixture_id for sample in review_samples):
                    if outcome.answer is None:
                        raise AssertionError("SUCCESS_ANSWER_REQUIRED")
                    review_samples.append(
                        ReviewSample(
                            fixture_id=fixture.fixture_id,
                            question=fixture.question,
                            answer=outcome.answer,
                        )
                    )

                cases.append(
                    EvaluationCaseResult(
                        fixture_id=fixture.fixture_id,
                        repetition=repetition,
                        outcome_code=outcome.code,
                        attempts_used=outcome.attempts_used,
                        attempt_outcomes=outcome.attempt_outcomes,
                        usage=outcome.usage,
                        latency_ms=latency_ms,
                        source_id=prepared.record.public_id,
                        used_template_fallback=used_template_fallback,
                    )
                )
                if outcome.code in _RUN_TERMINAL_CODES:
                    return EvaluationRun(
                        planned_generations=planned_generations,
                        cases=tuple(cases),
                        review_samples=tuple(review_samples),
                    )

        return EvaluationRun(
            planned_generations=planned_generations,
            cases=tuple(cases),
            review_samples=tuple(review_samples),
        )

    def _build_template_answer(self, record: KnowledgeRecord) -> GeneratedAnswer:
        response = build_success_response(
            request_id=self._uuid_factory(),
            record=record,
            office=None,
            confidence=1.0,
            context_token=None,
        )
        if response.summary is None:
            raise AssertionError("TEMPLATE_SUMMARY_REQUIRED")
        return GeneratedAnswer(
            summary=response.summary,
            procedure_steps=response.procedure_steps,
            required_documents=response.required_documents,
            processing_time=response.processing_time,
            fee=response.fee,
            department=response.department,
        )

    def _read_monotonic_ns(self) -> int:
        value = self._monotonic_ns()
        if type(value) is not int or value < 0:
            raise ValueError("MONOTONIC_CLOCK_INVALID")
        return value


__all__ = [
    "EvaluationCaseResult",
    "EvaluationRun",
    "ReviewSample",
    "SyntheticEvaluationService",
]
