import json
from dataclasses import fields

import pytest

from sejong_ai_api.llm.contracts import GeneratedAnswer, OutcomeCode, TokenUsage
from sejong_ai_api.llm.evaluation import (
    EvaluationCaseResult,
    EvaluationRun,
    ReviewSample,
)
from sejong_ai_api.llm.fixtures import PreparationCode
from sejong_ai_api.llm.report import HumanFixtureScore, build_aggregate_report

EXPECTED_REPORT_KEYS = {
    "schema_version",
    "provider",
    "model",
    "prompt_version",
    "fixture_set",
    "planned_generations",
    "completed_generations",
    "outbound_attempts",
    "outcome_counts",
    "attempt_outcome_counts",
    "schema_valid_count",
    "template_fallback_count",
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "estimated_cost_usd_including_vat",
    "cost_cap_usd_including_vat",
    "human_review",
    "acceptance",
}


def _answer(fixture_id: str) -> GeneratedAnswer:
    return GeneratedAnswer(
        summary=f"안전한 합성 답변 {fixture_id}",
        procedure_steps=["승인된 절차를 확인합니다."],
        required_documents=[],
        processing_time=None,
        fee=None,
        department=None,
    )


def _score(
    fixture_id: str,
    *,
    value: int = 5,
    reason_code: str = "OK",
) -> HumanFixtureScore:
    return HumanFixtureScore(
        fixture_id=fixture_id,
        natural_korean=value,
        directness=value,
        official_fact_preservation=value,
        unsupported_claim_absence=value,
        next_action_clarity=value,
        decision="PASS" if reason_code == "OK" else "FAIL",
        reason_code=reason_code,
    )


def _completed_run(
    *,
    replacement: EvaluationCaseResult | None = None,
) -> EvaluationRun:
    cases: list[EvaluationCaseResult] = []
    samples: list[ReviewSample] = []
    for number in range(1, 11):
        fixture_id = f"T-{number:02d}"
        samples.append(
            ReviewSample(
                fixture_id=fixture_id,
                question=f"저장 금지 합성 질문 {fixture_id}",
                answer=_answer(fixture_id),
            )
        )
        for repetition in range(1, 4):
            case = EvaluationCaseResult(
                fixture_id=fixture_id,
                repetition=repetition,
                outcome_code=OutcomeCode.SUCCESS,
                attempts_used=1,
                attempt_outcomes=(OutcomeCode.SUCCESS,),
                usage=TokenUsage(20, 0, 10),
                latency_ms=10,
                source_id=f"KB-{number:02d}",
                used_template_fallback=False,
            )
            if (
                replacement is not None
                and replacement.fixture_id == fixture_id
                and replacement.repetition == repetition
            ):
                case = replacement
            cases.append(case)
    return EvaluationRun(
        planned_generations=30,
        cases=tuple(cases),
        review_samples=tuple(samples),
    )


def _approved_scores() -> tuple[HumanFixtureScore, ...]:
    return tuple(_score(f"T-{number:02d}") for number in range(1, 11))


def test_human_fixture_score_has_exact_closed_fields_and_rejects_bool() -> None:
    assert tuple(field.name for field in fields(HumanFixtureScore)) == (
        "fixture_id",
        "natural_korean",
        "directness",
        "official_fact_preservation",
        "unsupported_claim_absence",
        "next_action_clarity",
        "decision",
        "reason_code",
    )
    with pytest.raises(ValueError, match="HUMAN_SCORE_INVALID"):
        HumanFixtureScore(
            fixture_id="T-01",
            natural_korean=True,  # type: ignore[arg-type]
            directness=5,
            official_fact_preservation=5,
            unsupported_claim_absence=5,
            next_action_clarity=5,
            decision="PASS",
            reason_code="OK",
        )


@pytest.mark.parametrize(
    ("decision", "reason_code"),
    [
        ("FAIL", "OK"),
        ("PASS", "INDIRECT"),
        ("pass", "OK"),
        ("FAIL", "free text"),
    ],
)
def test_human_decision_must_be_derived_from_closed_reason(
    decision: str,
    reason_code: str,
) -> None:
    with pytest.raises(ValueError, match="HUMAN_SCORE_DECISION_INVALID"):
        HumanFixtureScore(
            fixture_id="T-01",
            natural_korean=5,
            directness=5,
            official_fact_preservation=5,
            unsupported_claim_absence=5,
            next_action_clarity=5,
            decision=decision,
            reason_code=reason_code,
        )


def test_complete_report_is_explicit_text_free_and_reconciled() -> None:
    run = _completed_run()
    report = build_aggregate_report(run, _approved_scores())

    assert set(report) == EXPECTED_REPORT_KEYS
    assert report["planned_generations"] == 30
    assert report["completed_generations"] == 30
    assert report["outbound_attempts"] == 30
    assert report["outcome_counts"] == {"SUCCESS": 30}
    assert report["attempt_outcome_counts"] == {"SUCCESS": 30}
    assert report["schema_valid_count"] == 30
    assert report["template_fallback_count"] == 0
    assert report["input_tokens"] == 600
    assert report["cached_input_tokens"] == 0
    assert report["output_tokens"] == 300
    assert report["estimated_cost_usd_including_vat"] == "0.000297"
    assert report["acceptance"] == {
        "json_schema_100_percent": True,
        "critical_fact_errors_zero": True,
        "mean_at_least_4": True,
        "minimum_dimension_at_least_3": True,
        "cost_within_cap": True,
        "overall_pass": True,
    }

    serialized = json.dumps(
        report,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
    )
    for sample in run.review_samples:
        assert sample.question not in serialized
        assert sample.answer.summary not in serialized
    for forbidden in (
        "Authorization",
        "api_key",
        "provider_body",
        "request_id",
        "account",
        "username",
        "hostname",
        "timestamp",
    ):
        assert forbidden not in serialized


def test_retry_and_provider_failure_counts_remain_text_free_and_reconcile() -> None:
    retry_success = EvaluationCaseResult(
        fixture_id="T-01",
        repetition=1,
        outcome_code=OutcomeCode.SUCCESS,
        attempts_used=2,
        attempt_outcomes=(OutcomeCode.RATE_LIMIT, OutcomeCode.SUCCESS),
        usage=TokenUsage(25, 0, 10),
        latency_ms=20,
        source_id="KB-01",
        used_template_fallback=False,
    )
    timeout = EvaluationCaseResult(
        fixture_id="T-02",
        repetition=2,
        outcome_code=OutcomeCode.TIMEOUT,
        attempts_used=1,
        attempt_outcomes=(OutcomeCode.TIMEOUT,),
        usage=TokenUsage(0, 0, 0),
        latency_ms=15,
        source_id="KB-02",
        used_template_fallback=True,
    )
    run = _completed_run(replacement=retry_success)
    cases = tuple(
        timeout if (case.fixture_id, case.repetition) == ("T-02", 2) else case for case in run.cases
    )
    run = EvaluationRun(
        planned_generations=run.planned_generations,
        cases=cases,
        review_samples=run.review_samples,
    )

    report = build_aggregate_report(run, _approved_scores())

    assert report["outbound_attempts"] == 31
    assert report["outcome_counts"] == {"SUCCESS": 29, "TIMEOUT": 1}
    assert report["attempt_outcome_counts"] == {
        "RATE_LIMIT": 1,
        "SUCCESS": 29,
        "TIMEOUT": 1,
    }
    assert report["template_fallback_count"] == 1
    assert report["acceptance"]["overall_pass"] is False  # type: ignore[index]


def test_content_invalid_attempt_and_incomplete_scores_fail_acceptance() -> None:
    invalid_then_success = EvaluationCaseResult(
        fixture_id="T-01",
        repetition=1,
        outcome_code=OutcomeCode.SUCCESS,
        attempts_used=2,
        attempt_outcomes=(OutcomeCode.SCHEMA_INVALID, OutcomeCode.SUCCESS),
        usage=TokenUsage(20, 0, 10),
        latency_ms=10,
        source_id="KB-01",
        used_template_fallback=False,
    )

    report = build_aggregate_report(
        _completed_run(replacement=invalid_then_success),
        _approved_scores()[:-1],
    )

    acceptance = report["acceptance"]
    assert acceptance["json_schema_100_percent"] is False  # type: ignore[index]
    assert acceptance["overall_pass"] is False  # type: ignore[index]


@pytest.mark.parametrize(
    "terminal_case",
    [
        EvaluationCaseResult(
            fixture_id="T-01",
            repetition=1,
            outcome_code=OutcomeCode.INPUT_LIMIT,
            attempts_used=0,
            attempt_outcomes=(),
            usage=TokenUsage(0, 0, 0),
            latency_ms=0,
            source_id="KB-01",
            used_template_fallback=True,
        ),
        EvaluationCaseResult(
            fixture_id="T-01",
            repetition=1,
            outcome_code=PreparationCode.INSUFFICIENT_GROUNDING,
            attempts_used=0,
            attempt_outcomes=(),
            usage=TokenUsage(0, 0, 0),
            latency_ms=0,
            source_id=None,
            used_template_fallback=False,
        ),
    ],
)
def test_preparation_or_terminal_result_cannot_pass(
    terminal_case: EvaluationCaseResult,
) -> None:
    report = build_aggregate_report(
        _completed_run(replacement=terminal_case),
        _approved_scores(),
    )
    assert report["acceptance"]["overall_pass"] is False  # type: ignore[index]


def test_non_review_run_never_passes() -> None:
    report = build_aggregate_report(_completed_run(), ())

    assert report["human_review"] == {
        "reviewed_fixture_count": 0,
        "mean_score": "0",
        "minimum_dimension_score": None,
        "critical_fact_error_count": 0,
        "decision_counts": {},
        "reason_counts": {},
        "scores": [],
    }
    assert report["acceptance"]["overall_pass"] is False  # type: ignore[index]


def test_forged_review_sample_without_any_success_cannot_pass() -> None:
    run = _completed_run()
    cases = tuple(
        EvaluationCaseResult(
            fixture_id=case.fixture_id,
            repetition=case.repetition,
            outcome_code=OutcomeCode.TIMEOUT,
            attempts_used=1,
            attempt_outcomes=(OutcomeCode.TIMEOUT,),
            usage=TokenUsage(0, 0, 0),
            latency_ms=10,
            source_id=case.source_id,
            used_template_fallback=True,
        )
        if case.fixture_id == "T-01"
        else case
        for case in run.cases
    )
    forged = EvaluationRun(
        planned_generations=30,
        cases=cases,
        review_samples=run.review_samples,
    )

    report = build_aggregate_report(forged, _approved_scores())

    assert report["outbound_attempts"] == 30
    assert report["acceptance"]["overall_pass"] is False  # type: ignore[index]
