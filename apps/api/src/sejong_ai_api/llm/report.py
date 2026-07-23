"""Content-free aggregate evidence for the local synthetic evaluation."""

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal

from sejong_ai_api.llm.contracts import OutcomeCode, TokenUsage
from sejong_ai_api.llm.cost import RUN_COST_CAP_USD, estimate_cost_usd
from sejong_ai_api.llm.evaluation import (
    EvaluationCaseResult,
    EvaluationRun,
    ReviewSample,
)
from sejong_ai_api.llm.prompt import PROMPT_VERSION
from sejong_ai_api.llm.settings import UPSTAGE_MODEL, UPSTAGE_PROVIDER

REPORT_SCHEMA_VERSION = "1.0.0"
FIXTURE_SET = "sample_questions_20:T-01..T-10"
PLANNED_GENERATIONS = 30
RUN_COST_CAP_TEXT = "0.05"

_FIXTURE_IDS = tuple(f"T-{number:02d}" for number in range(1, 11))
_FIXTURE_ID_SET = frozenset(_FIXTURE_IDS)
_EXPECTED_CASE_KEYS = frozenset(
    (fixture_id, repetition) for fixture_id in _FIXTURE_IDS for repetition in range(1, 4)
)
_SCORE_REASONS = frozenset(
    {
        "OK",
        "UNNATURAL_KOREAN",
        "INDIRECT",
        "MISSING_OFFICIAL_FACT",
        "UNSUPPORTED_CLAIM",
        "OFFICIAL_FACT_CONTRADICTION",
        "UNCLEAR_NEXT_ACTION",
    }
)
_CONTENT_INVALID_CODES = frozenset(
    {
        OutcomeCode.EMPTY,
        OutcomeCode.TRUNCATED,
        OutcomeCode.SCHEMA_INVALID,
    }
)
_RUN_BLOCKING_CODES = frozenset(
    {
        OutcomeCode.INPUT_LIMIT,
        OutcomeCode.ATTEMPT_CAP,
    }
)


@dataclass(frozen=True, slots=True)
class HumanFixtureScore:
    fixture_id: str
    natural_korean: int
    directness: int
    official_fact_preservation: int
    unsupported_claim_absence: int
    next_action_clarity: int
    decision: str
    reason_code: str

    def __post_init__(self) -> None:
        if type(self.fixture_id) is not str or self.fixture_id not in _FIXTURE_ID_SET:
            raise ValueError("HUMAN_SCORE_FIXTURE_INVALID")
        if any(type(value) is not int or not 1 <= value <= 5 for value in self.dimension_scores):
            raise ValueError("HUMAN_SCORE_INVALID")
        if (
            type(self.decision) is not str
            or type(self.reason_code) is not str
            or self.reason_code not in _SCORE_REASONS
        ):
            raise ValueError("HUMAN_SCORE_DECISION_INVALID")
        expected_decision = "PASS" if self.reason_code == "OK" else "FAIL"
        if self.decision != expected_decision:
            raise ValueError("HUMAN_SCORE_DECISION_INVALID")

    @property
    def dimension_scores(self) -> tuple[int, int, int, int, int]:
        return (
            self.natural_korean,
            self.directness,
            self.official_fact_preservation,
            self.unsupported_claim_absence,
            self.next_action_clarity,
        )


def build_aggregate_report(
    run: EvaluationRun,
    scores: tuple[HumanFixtureScore, ...],
) -> dict[str, object]:
    """Build only aggregate, closed-code evidence from one in-memory run."""
    if type(run) is not EvaluationRun or type(scores) is not tuple:
        raise ValueError("EVALUATION_REPORT_INPUT_INVALID")
    if any(type(case) is not EvaluationCaseResult for case in run.cases):
        raise ValueError("EVALUATION_REPORT_INPUT_INVALID")
    if any(type(sample) is not ReviewSample for sample in run.review_samples):
        raise ValueError("EVALUATION_REPORT_INPUT_INVALID")
    if any(type(score) is not HumanFixtureScore for score in scores):
        raise ValueError("EVALUATION_REPORT_INPUT_INVALID")
    if type(run.planned_generations) is not int or run.planned_generations < 0:
        raise ValueError("EVALUATION_REPORT_INPUT_INVALID")

    outcome_counts: Counter[str] = Counter()
    attempt_outcome_counts: Counter[str] = Counter()
    input_tokens = 0
    cached_input_tokens = 0
    output_tokens = 0
    outbound_attempts = 0
    schema_valid_count = 0
    template_fallback_count = 0

    for case in run.cases:
        outcome_counts[case.outcome_code.value] += 1
        attempt_outcome_counts.update(outcome.value for outcome in case.attempt_outcomes)
        outbound_attempts += case.attempts_used
        input_tokens += case.usage.input_tokens
        cached_input_tokens += case.usage.cached_input_tokens
        output_tokens += case.usage.output_tokens
        if case.outcome_code is OutcomeCode.SUCCESS:
            schema_valid_count += 1
        if case.used_template_fallback:
            template_fallback_count += 1

    usage = TokenUsage(
        input_tokens=input_tokens,
        cached_input_tokens=cached_input_tokens,
        output_tokens=output_tokens,
    )
    estimated_cost = estimate_cost_usd(usage)
    human_review, score_complete = _build_human_review(run.review_samples, scores)
    acceptance = _build_acceptance(
        run=run,
        scores=scores,
        human_review=human_review,
        score_complete=score_complete,
        outbound_attempts=outbound_attempts,
        attempt_outcome_counts=attempt_outcome_counts,
        estimated_cost=estimated_cost,
    )

    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "provider": UPSTAGE_PROVIDER,
        "model": UPSTAGE_MODEL,
        "prompt_version": PROMPT_VERSION,
        "fixture_set": FIXTURE_SET,
        "planned_generations": PLANNED_GENERATIONS,
        "completed_generations": len(run.cases),
        "outbound_attempts": outbound_attempts,
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "attempt_outcome_counts": dict(sorted(attempt_outcome_counts.items())),
        "schema_valid_count": schema_valid_count,
        "template_fallback_count": template_fallback_count,
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd_including_vat": _decimal_text(estimated_cost),
        "cost_cap_usd_including_vat": RUN_COST_CAP_TEXT,
        "human_review": human_review,
        "acceptance": acceptance,
    }


def _build_human_review(
    samples: tuple[ReviewSample, ...],
    scores: tuple[HumanFixtureScore, ...],
) -> tuple[dict[str, object], bool]:
    dimension_values = tuple(value for score in scores for value in score.dimension_scores)
    mean = (
        Decimal(sum(dimension_values)) / Decimal(len(dimension_values))
        if dimension_values
        else Decimal(0)
    )
    minimum = min(dimension_values) if dimension_values else None
    decision_counts = Counter(score.decision for score in scores)
    reason_counts = Counter(score.reason_code for score in scores)
    sample_ids = tuple(sample.fixture_id for sample in samples)
    score_ids = tuple(score.fixture_id for score in scores)
    score_complete = (
        len(samples) == len(_FIXTURE_IDS)
        and len(set(sample_ids)) == len(_FIXTURE_IDS)
        and set(sample_ids) == _FIXTURE_ID_SET
        and len(scores) == len(_FIXTURE_IDS)
        and len(set(score_ids)) == len(_FIXTURE_IDS)
        and set(score_ids) == set(sample_ids)
    )

    return (
        {
            "reviewed_fixture_count": len(scores),
            "mean_score": _decimal_text(mean),
            "minimum_dimension_score": minimum,
            "critical_fact_error_count": reason_counts["OFFICIAL_FACT_CONTRADICTION"],
            "decision_counts": dict(sorted(decision_counts.items())),
            "reason_counts": dict(sorted(reason_counts.items())),
            "scores": [
                _serialize_score(score)
                for score in sorted(scores, key=lambda item: item.fixture_id)
            ],
        },
        score_complete,
    )


def _build_acceptance(
    *,
    run: EvaluationRun,
    scores: tuple[HumanFixtureScore, ...],
    human_review: dict[str, object],
    score_complete: bool,
    outbound_attempts: int,
    attempt_outcome_counts: Counter[str],
    estimated_cost: Decimal,
) -> dict[str, bool]:
    content_invalid_count = sum(
        attempt_outcome_counts[code.value] for code in _CONTENT_INVALID_CODES
    )
    json_schema_100_percent = content_invalid_count == 0
    critical_fact_errors_zero = human_review["critical_fact_error_count"] == 0
    mean_at_least_4 = Decimal(str(human_review["mean_score"])) >= Decimal(4)
    minimum = human_review["minimum_dimension_score"]
    minimum_dimension_at_least_3 = type(minimum) is int and minimum >= 3
    cost_within_cap = estimated_cost <= RUN_COST_CAP_USD

    case_keys = tuple((case.fixture_id, case.repetition) for case in run.cases)
    exact_safe_plan = (
        run.planned_generations == PLANNED_GENERATIONS
        and len(run.cases) == PLANNED_GENERATIONS
        and len(set(case_keys)) == PLANNED_GENERATIONS
        and set(case_keys) == _EXPECTED_CASE_KEYS
    )
    trace_reconciles = (
        outbound_attempts == sum(len(case.attempt_outcomes) for case in run.cases)
        and outbound_attempts <= 30
    )
    no_preparation_or_terminal = all(
        type(case.outcome_code) is OutcomeCode and case.outcome_code not in _RUN_BLOCKING_CODES
        for case in run.cases
    )
    every_provider_failure_fell_back = all(
        case.outcome_code is OutcomeCode.SUCCESS or case.used_template_fallback
        for case in run.cases
        if type(case.outcome_code) is OutcomeCode
    )
    successful_fixture_ids = {
        case.fixture_id for case in run.cases if case.outcome_code is OutcomeCode.SUCCESS
    }
    every_review_sample_has_success = all(
        sample.fixture_id in successful_fixture_ids for sample in run.review_samples
    )
    decisions_are_derived = all(
        score.decision == ("PASS" if score.reason_code == "OK" else "FAIL") for score in scores
    )

    overall_pass = all(
        (
            json_schema_100_percent,
            critical_fact_errors_zero,
            mean_at_least_4,
            minimum_dimension_at_least_3,
            cost_within_cap,
            score_complete,
            exact_safe_plan,
            trace_reconciles,
            no_preparation_or_terminal,
            every_provider_failure_fell_back,
            every_review_sample_has_success,
            decisions_are_derived,
        )
    )
    return {
        "json_schema_100_percent": json_schema_100_percent,
        "critical_fact_errors_zero": critical_fact_errors_zero,
        "mean_at_least_4": mean_at_least_4,
        "minimum_dimension_at_least_3": minimum_dimension_at_least_3,
        "cost_within_cap": cost_within_cap,
        "overall_pass": overall_pass,
    }


def _serialize_score(score: HumanFixtureScore) -> dict[str, int | str]:
    return {
        "fixture_id": score.fixture_id,
        "natural_korean": score.natural_korean,
        "directness": score.directness,
        "official_fact_preservation": score.official_fact_preservation,
        "unsupported_claim_absence": score.unsupported_claim_absence,
        "next_action_clarity": score.next_action_clarity,
        "decision": score.decision,
        "reason_code": score.reason_code,
    }


def _decimal_text(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


__all__ = [
    "HumanFixtureScore",
    "build_aggregate_report",
]
