#!/usr/bin/env python3
"""Run the exact 15-second/one-retry local Upstage synthetic evaluation profile."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, NoReturn, Protocol, cast

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_API_SOURCE = _REPOSITORY_ROOT / "apps" / "api" / "src"
_FIXTURE_PATH = _REPOSITORY_ROOT / "data" / "evaluation" / "sample_questions_20.csv"
_REPORT_RELATIVE_PATH = Path("artifacts/llm-002/upstage-synthetic-evaluation.json")
_REPORT_PATH = _REPOSITORY_ROOT / _REPORT_RELATIVE_PATH
_REPETITIONS = 3

if str(_API_SOURCE) not in sys.path:
    sys.path.insert(0, str(_API_SOURCE))

from sejong_ai_api.llm.contracts import TokenUsage  # noqa: E402
from sejong_ai_api.llm.cost import estimate_cost_usd  # noqa: E402
from sejong_ai_api.llm.evaluation import EvaluationRun, ReviewSample  # noqa: E402
from sejong_ai_api.llm.report import (  # noqa: E402
    HumanFixtureScore,
    build_aggregate_report,
)

_REASON_CODES = frozenset(
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
_SCORE_PROMPTS = (
    "NATURAL_KOREAN_1_TO_5=",
    "DIRECTNESS_1_TO_5=",
    "OFFICIAL_FACT_PRESERVATION_1_TO_5=",
    "UNSUPPORTED_CLAIM_ABSENCE_1_TO_5=",
    "NEXT_ACTION_CLARITY_1_TO_5=",
)


class _AsyncPool(Protocol):
    async def open(self, *, wait: bool = False) -> None: ...

    async def close(self) -> None: ...


class _AsyncClient(Protocol):
    async def aclose(self) -> None: ...


class _ReadinessProbe(Protocol):
    async def check_ready(self) -> bool: ...


class _Evaluator(Protocol):
    async def run(self, *, repetitions: int = 3) -> EvaluationRun: ...


class _ArgumentsInvalid(ValueError):
    """Unsupported CLI input was supplied."""


class _ConfigurationInvalid(RuntimeError):
    """The exact local/provider profile is unavailable."""


class _FixturesInvalid(RuntimeError):
    """The canonical allowlist does not match its bound hash."""


class _DatabaseUnavailable(RuntimeError):
    """The local DB could not prove its exact ready projection."""


class _ReportIntegrityInvalid(RuntimeError):
    """Text-free attempt, budget, token or cost totals did not reconcile."""


class _ReviewInvalid(RuntimeError):
    """TTY review input was not one of the closed values."""


@dataclass(frozen=True, slots=True)
class _RunnerOptions:
    review: bool


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> NoReturn:
        raise _ArgumentsInvalid from None


def _parse_args(argv: Sequence[str] | None = None) -> _RunnerOptions:
    parser = _SafeArgumentParser(
        prog="run_upstage_synthetic_evaluation.py",
        description="Run the fixed local/private Upstage synthetic evaluation.",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="score the ten in-memory samples from a local interactive TTY",
    )
    namespace = parser.parse_args(argv)
    if type(namespace.review) is not bool:
        raise _ArgumentsInvalid
    return _RunnerOptions(review=namespace.review)


def _review_tty_available() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def _configure_event_loop_policy(platform: str) -> None:
    if platform != "win32":
        return
    policy_factory = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if not callable(policy_factory):
        raise _ConfigurationInvalid
    asyncio.set_event_loop_policy(policy_factory())


def _load_local_settings() -> object | None:
    from sejong_ai_api.local import load_local_settings

    return load_local_settings()


def _load_provider_settings() -> object | None:
    """Load only the synthetic profile, never the grounded-chat profile."""
    from sejong_ai_api.llm.settings import load_upstage_synthetic_settings

    return load_upstage_synthetic_settings()


def _load_canonical_fixtures() -> tuple[object, ...]:
    from sejong_ai_api.llm.fixtures import load_allowed_fixtures

    return cast(tuple[object, ...], load_allowed_fixtures(_FIXTURE_PATH))


def _create_local_pool(database_url: str) -> _AsyncPool:
    from sejong_ai_api.db.pool import create_pool

    return cast(_AsyncPool, create_pool(database_url))


def _create_repository(pool: object) -> object:
    from sejong_ai_api.db.repository import PsycopgSejongRepository

    return PsycopgSejongRepository(cast(Any, pool))


def _create_readiness_probe(repository: object) -> _ReadinessProbe:
    from sejong_ai_api.chat.readiness import RepositoryReadinessProbe

    return cast(_ReadinessProbe, RepositoryReadinessProbe(cast(Any, repository)))


def _create_provider_client(settings: object) -> _AsyncClient:
    from sejong_ai_api.llm.settings import UpstageSyntheticSettings
    from sejong_ai_api.llm.upstage import create_upstage_client

    return cast(
        _AsyncClient,
        create_upstage_client(cast(UpstageSyntheticSettings, settings)),
    )


def _create_attempt_budget(settings: object) -> object:
    from sejong_ai_api.llm.limits import AttemptBudget
    from sejong_ai_api.llm.settings import UpstageSyntheticSettings

    selected = cast(UpstageSyntheticSettings, settings)
    return AttemptBudget(
        cap=selected.run_attempt_cap,
        concurrency=selected.max_concurrency,
    )


def _create_provider(
    settings: object,
    client: object,
    budget: object,
) -> object:
    from sejong_ai_api.llm.limits import AttemptBudget
    from sejong_ai_api.llm.settings import UpstageSyntheticSettings
    from sejong_ai_api.llm.upstage import UpstageProvider

    return UpstageProvider(
        settings=cast(UpstageSyntheticSettings, settings),
        client=cast(Any, client),
        budget=cast(AttemptBudget, budget),
    )


def _create_evaluator(
    fixtures: object,
    repository: object,
    provider: object,
) -> _Evaluator:
    from sejong_ai_api.llm.evaluation import SyntheticEvaluationService

    return cast(
        _Evaluator,
        SyntheticEvaluationService(
            fixtures=cast(Any, fixtures),
            repository=cast(Any, repository),
            provider=cast(Any, provider),
        ),
    )


async def _run_evaluation(
    *,
    local_settings: object,
    provider_settings: object,
    fixtures: tuple[object, ...],
    review: bool,
) -> dict[str, object]:
    pool: _AsyncPool | None = None
    client: _AsyncClient | None = None
    try:
        try:
            local_conninfo = getattr(local_settings, "database_url")
            if type(local_conninfo) is not str:
                raise ValueError
            pool = _create_local_pool(local_conninfo)
            await pool.open(wait=True)
            repository = _create_repository(pool)
            probe = _create_readiness_probe(repository)
            if not await probe.check_ready():
                raise _DatabaseUnavailable
        except _DatabaseUnavailable:
            raise
        except Exception:
            raise _DatabaseUnavailable from None

        client = _create_provider_client(provider_settings)
        budget = _create_attempt_budget(provider_settings)
        provider = _create_provider(provider_settings, client, budget)
        evaluator = _create_evaluator(fixtures, repository, provider)
        run = await evaluator.run(repetitions=_REPETITIONS)
        if type(run) is not EvaluationRun:
            raise _ReportIntegrityInvalid

        scores = _collect_human_scores(run.review_samples) if review else ()
        report = build_aggregate_report(run, scores)
        _require_reconciled_report(
            run=run,
            report=report,
            budget=budget,
            provider_settings=provider_settings,
        )
        _atomic_write_report(_REPORT_PATH, report)
        return report
    finally:
        if client is not None:
            with suppress(Exception):
                await client.aclose()
        if pool is not None:
            with suppress(Exception):
                await pool.close()


def _require_reconciled_report(
    *,
    run: EvaluationRun,
    report: dict[str, object],
    budget: object,
    provider_settings: object,
) -> None:
    case_attempts = sum(case.attempts_used for case in run.cases)
    trace_attempts = sum(len(case.attempt_outcomes) for case in run.cases)
    budget_attempts = getattr(budget, "attempts_used", None)
    cap = getattr(provider_settings, "run_attempt_cap", None)
    report_attempts = report.get("outbound_attempts")
    if (
        type(budget_attempts) is not int
        or type(cap) is not int
        or type(report_attempts) is not int
        or case_attempts != trace_attempts
        or case_attempts != budget_attempts
        or case_attempts != report_attempts
        or case_attempts > cap
    ):
        raise _ReportIntegrityInvalid

    input_tokens = report.get("input_tokens")
    cached_input_tokens = report.get("cached_input_tokens")
    output_tokens = report.get("output_tokens")
    cost_text = report.get("estimated_cost_usd_including_vat")
    case_input_tokens = sum(case.usage.input_tokens for case in run.cases)
    case_cached_input_tokens = sum(case.usage.cached_input_tokens for case in run.cases)
    case_output_tokens = sum(case.usage.output_tokens for case in run.cases)
    if (
        type(input_tokens) is not int
        or type(cached_input_tokens) is not int
        or type(output_tokens) is not int
        or type(cost_text) is not str
        or input_tokens != case_input_tokens
        or cached_input_tokens != case_cached_input_tokens
        or output_tokens != case_output_tokens
    ):
        raise _ReportIntegrityInvalid
    try:
        reported_cost = Decimal(cost_text)
        expected_cost = estimate_cost_usd(
            TokenUsage(input_tokens, cached_input_tokens, output_tokens)
        )
    except (ValueError, ArithmeticError):
        raise _ReportIntegrityInvalid from None
    if reported_cost != expected_cost:
        raise _ReportIntegrityInvalid


def _collect_human_scores(
    samples: tuple[ReviewSample, ...],
) -> tuple[HumanFixtureScore, ...]:
    scores: list[HumanFixtureScore] = []
    for sample in samples:
        if type(sample) is not ReviewSample:
            raise _ReviewInvalid
        print(f"FIXTURE={sample.fixture_id}")
        print(f"QUESTION={sample.question}")
        print(f"ANSWER={sample.answer.model_dump_json()}")
        values = tuple(_read_dimension_score(prompt) for prompt in _SCORE_PROMPTS)
        reason_code = _read_reason_code()
        scores.append(
            HumanFixtureScore(
                fixture_id=sample.fixture_id,
                natural_korean=values[0],
                directness=values[1],
                official_fact_preservation=values[2],
                unsupported_claim_absence=values[3],
                next_action_clarity=values[4],
                decision="PASS" if reason_code == "OK" else "FAIL",
                reason_code=reason_code,
            )
        )
    return tuple(scores)


def _read_dimension_score(prompt: str) -> int:
    try:
        raw_value = input(prompt)
    except (EOFError, KeyboardInterrupt):
        raise _ReviewInvalid from None
    if (
        type(raw_value) is not str
        or len(raw_value) != 1
        or not raw_value.isascii()
        or not raw_value.isdecimal()
    ):
        raise _ReviewInvalid
    value = int(raw_value)
    if not 1 <= value <= 5:
        raise _ReviewInvalid
    return value


def _read_reason_code() -> str:
    try:
        value = input("REASON_CODE=")
    except (EOFError, KeyboardInterrupt):
        raise _ReviewInvalid from None
    if type(value) is not str or value not in _REASON_CODES:
        raise _ReviewInvalid
    return value


def _atomic_write_report(path: Path, report: dict[str, object]) -> None:
    if not isinstance(path, Path) or type(report) is not dict:
        raise _ReportIntegrityInvalid
    payload = (
        json.dumps(
            report,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f"{path.name}.tmp")
    try:
        with temporary_path.open("wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        with suppress(OSError):
            temporary_path.unlink()


def _overall_pass(report: dict[str, object]) -> bool:
    acceptance = report.get("acceptance")
    if type(acceptance) is not dict:
        raise _ReportIntegrityInvalid
    value = acceptance.get("overall_pass")
    if type(value) is not bool:
        raise _ReportIntegrityInvalid
    return value


def main(argv: Sequence[str] | None = None) -> int:
    try:
        options = _parse_args(argv)
    except (SystemExit, _ArgumentsInvalid):
        print("LLM_EVALUATION_ARGUMENTS_INVALID", file=sys.stderr)
        return 2

    if options.review and not _review_tty_available():
        print("LLM_EVALUATION_REVIEW_TTY_REQUIRED", file=sys.stderr)
        return 2

    try:
        _configure_event_loop_policy(sys.platform)
        local_settings = _load_local_settings()
        provider_settings = _load_provider_settings()
        if local_settings is None or provider_settings is None:
            raise _ConfigurationInvalid
    except Exception:
        print("LLM_EVALUATION_CONFIGURATION_INVALID", file=sys.stderr)
        return 2

    try:
        fixtures = _load_canonical_fixtures()
    except Exception:
        print("LLM_EVALUATION_FIXTURES_INVALID", file=sys.stderr)
        return 2

    try:
        report = asyncio.run(
            _run_evaluation(
                local_settings=local_settings,
                provider_settings=provider_settings,
                fixtures=fixtures,
                review=options.review,
            )
        )
        passed = _overall_pass(report)
    except _DatabaseUnavailable:
        print("LLM_EVALUATION_DATABASE_UNAVAILABLE", file=sys.stderr)
        return 3
    except _ReviewInvalid:
        print("LLM_EVALUATION_REVIEW_INVALID", file=sys.stderr)
        return 2
    except Exception:
        print("LLM_EVALUATION_RUNTIME_FAILED", file=sys.stderr)
        return 4

    print("LLM_EVALUATION_COMPLETE")
    print(f"REPORT={_REPORT_RELATIVE_PATH.as_posix()}")
    print(f"OVERALL_PASS={str(passed).lower()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
