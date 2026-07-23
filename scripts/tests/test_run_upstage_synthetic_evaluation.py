from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_API_SOURCE = _REPOSITORY_ROOT / "apps" / "api" / "src"
sys.path.insert(0, str(_API_SOURCE))

from sejong_ai_api.llm.contracts import (  # noqa: E402
    GeneratedAnswer,
    OutcomeCode,
    TokenUsage,
)
from sejong_ai_api.llm.evaluation import (  # noqa: E402
    EvaluationCaseResult,
    EvaluationRun,
    ReviewSample,
)

_MODULE_NAME = "_sejong_upstage_evaluation_runner_test"
_RUNNER_PATH = (
    Path(__file__).resolve().parents[1] / "run_upstage_synthetic_evaluation.py"
)
_SECRET = "synthetic-test-key-that-must-never-print"
_QUESTION = "저장하거나 출력하면 안 되는 합성 질문"
_ANSWER = "오류 경로에서 출력하면 안 되는 합성 답변"


def _database_dsn(scheme: str, authority: str) -> str:
    return f"{scheme}://{authority}"


_DSN = _database_dsn(
    "postgresql",
    "local:password-that-must-never-print@127.0.0.1:54322/postgres",
)


def _runner() -> ModuleType:
    cached = sys.modules.get(_MODULE_NAME)
    if cached is not None:
        return cached
    if not _RUNNER_PATH.is_file():
        raise AssertionError("the Upstage evaluation runner is missing")
    spec = importlib.util.spec_from_file_location(_MODULE_NAME, _RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("the Upstage evaluation runner cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def _one_case_run() -> EvaluationRun:
    answer = GeneratedAnswer(
        summary=_ANSWER,
        procedure_steps=[],
        required_documents=[],
        processing_time=None,
        fee=None,
        department=None,
    )
    return EvaluationRun(
        planned_generations=1,
        cases=(
            EvaluationCaseResult(
                fixture_id="T-01",
                repetition=1,
                outcome_code=OutcomeCode.SUCCESS,
                attempts_used=1,
                attempt_outcomes=(OutcomeCode.SUCCESS,),
                usage=TokenUsage(20, 0, 10),
                latency_ms=1,
                source_id="KB-01",
                used_template_fallback=False,
            ),
        ),
        review_samples=(
            ReviewSample(
                fixture_id="T-01",
                question=_QUESTION,
                answer=answer,
            ),
        ),
    )


class _FakePool:
    def __init__(self, events: list[str], *, open_error: bool = False) -> None:
        self._events = events
        self._open_error = open_error

    async def open(self, *, wait: bool = False) -> None:
        self._events.append(f"pool-open:{wait}")
        if self._open_error:
            raise RuntimeError(f"must not leak {_DSN}")

    async def close(self) -> None:
        self._events.append("pool-close")


class _FakeClient:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    async def aclose(self) -> None:
        self._events.append("client-close")


class _FakeProbe:
    def __init__(self, events: list[str], *, ready: bool) -> None:
        self._events = events
        self._ready = ready

    async def check_ready(self) -> bool:
        self._events.append("readiness")
        return self._ready


class _FakeBudget:
    def __init__(self, events: list[str], attempts_used: int = 1) -> None:
        self._events = events
        self.attempts_used = attempts_used


class _FakeService:
    def __init__(
        self,
        events: list[str],
        run: EvaluationRun,
        *,
        run_error: bool = False,
    ) -> None:
        self._events = events
        self._run = run
        self._run_error = run_error

    async def run(self, *, repetitions: int = 3) -> EvaluationRun:
        self._events.append(f"evaluation:{repetitions}")
        if self._run_error:
            raise RuntimeError(f"must not leak {_QUESTION} {_ANSWER}")
        return self._run


class RunnerTests(unittest.TestCase):
    def _capture_main(self, argv: list[str]) -> tuple[int, str, str]:
        runner = _runner()
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = runner.main(argv)
        return result, stdout.getvalue(), stderr.getvalue()

    def _patch_happy_dependencies(
        self,
        events: list[str],
        *,
        ready: bool = True,
        run: EvaluationRun | None = None,
        run_error: bool = False,
        writes: list[tuple[Path, dict[str, object]]] | None = None,
    ) -> tuple[object, ...]:
        runner = _runner()
        local_settings = SimpleNamespace(database_url=_DSN)
        provider_settings = SimpleNamespace(
            api_key=_SECRET,
            run_attempt_cap=30,
            max_concurrency=1,
        )
        selected_run = _one_case_run() if run is None else run
        pool = _FakePool(events)
        client = _FakeClient(events)
        fixture = object()
        fixtures = (fixture,)
        budget = _FakeBudget(
            events,
            attempts_used=sum(case.attempts_used for case in selected_run.cases),
        )
        output = writes if writes is not None else []

        def load_local() -> object:
            events.append("local-settings")
            return local_settings

        def load_provider() -> object:
            events.append("provider-settings")
            return provider_settings

        def load_fixtures() -> tuple[object, ...]:
            events.append("canonical-fixtures")
            return fixtures

        def create_pool(database_url: str) -> _FakePool:
            self.assertEqual(database_url, _DSN)
            events.append("pool")
            return pool

        def create_repository(selected_pool: object) -> object:
            self.assertIs(selected_pool, pool)
            events.append("repository")
            return object()

        def create_probe(_repository: object) -> _FakeProbe:
            events.append("probe")
            return _FakeProbe(events, ready=ready)

        def create_client(settings: object) -> _FakeClient:
            self.assertIs(settings, provider_settings)
            events.append("client")
            return client

        def create_budget(settings: object) -> _FakeBudget:
            self.assertIs(settings, provider_settings)
            events.append("budget")
            return budget

        def create_provider(
            settings: object,
            selected_client: object,
            selected_budget: object,
        ) -> object:
            self.assertIs(settings, provider_settings)
            self.assertIs(selected_client, client)
            self.assertIs(selected_budget, budget)
            events.append("provider")
            return object()

        def create_service(
            selected_fixtures: object,
            repository: object,
            provider: object,
        ) -> _FakeService:
            self.assertIs(selected_fixtures, fixtures)
            self.assertIsNotNone(repository)
            self.assertIsNotNone(provider)
            events.append("evaluator")
            return _FakeService(events, selected_run, run_error=run_error)

        def write_report(path: Path, report: dict[str, object]) -> None:
            events.append("write")
            output.append((path, report))

        return (
            patch.object(runner, "_load_local_settings", load_local),
            patch.object(runner, "_load_provider_settings", load_provider),
            patch.object(runner, "_load_canonical_fixtures", load_fixtures),
            patch.object(runner, "_create_local_pool", create_pool),
            patch.object(runner, "_create_repository", create_repository),
            patch.object(runner, "_create_readiness_probe", create_probe),
            patch.object(runner, "_create_provider_client", create_client),
            patch.object(runner, "_create_attempt_budget", create_budget),
            patch.object(runner, "_create_provider", create_provider),
            patch.object(runner, "_create_evaluator", create_service),
            patch.object(runner, "_atomic_write_report", write_report),
        )

    def test_missing_provider_configuration_exits_two_with_one_bounded_line(
        self,
    ) -> None:
        runner = _runner()
        with (
            patch.object(
                runner,
                "_load_local_settings",
                return_value=SimpleNamespace(database_url=_DSN),
            ),
            patch.object(runner, "_load_provider_settings", return_value=None),
            patch.object(
                runner,
                "_load_canonical_fixtures",
                side_effect=AssertionError("must not load fixtures"),
            ),
        ):
            result, stdout, stderr = self._capture_main([])

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "LLM_EVALUATION_CONFIGURATION_INVALID\n")

    def test_rejected_argument_never_echoes_its_value(self) -> None:
        result, stdout, stderr = self._capture_main(["--api-key", _SECRET])

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "LLM_EVALUATION_ARGUMENTS_INVALID\n")
        self.assertNotIn(_SECRET, stderr)

    def test_no_cli_override_for_model_url_fixture_output_cap_or_question(self) -> None:
        for option in (
            "--model",
            "--base-url",
            "--fixture-path",
            "--output",
            "--attempt-cap",
            "--question",
        ):
            with self.subTest(option=option):
                result, stdout, stderr = self._capture_main([option, _SECRET])
                self.assertEqual(result, 2)
                self.assertEqual(stdout, "")
                self.assertEqual(stderr, "LLM_EVALUATION_ARGUMENTS_INVALID\n")
                self.assertNotIn(_SECRET, stderr)

    def test_non_tty_review_stops_before_settings_database_and_provider(self) -> None:
        runner = _runner()
        with (
            patch.object(runner, "_review_tty_available", return_value=False),
            patch.object(
                runner,
                "_load_local_settings",
                side_effect=AssertionError("must not load local settings"),
            ),
            patch.object(
                runner,
                "_load_provider_settings",
                side_effect=AssertionError("must not load provider settings"),
            ),
        ):
            result, stdout, stderr = self._capture_main(["--review"])

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "LLM_EVALUATION_REVIEW_TTY_REQUIRED\n")

    def test_readiness_failure_closes_pool_without_provider_construction(self) -> None:
        events: list[str] = []
        writes: list[tuple[Path, dict[str, object]]] = []
        patches = self._patch_happy_dependencies(
            events,
            ready=False,
            writes=writes,
        )
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patch.object(
                _runner(),
                "_create_provider_client",
                side_effect=AssertionError("client must not be constructed"),
            ),
        ):
            result, stdout, stderr = self._capture_main([])

        self.assertEqual(result, 3)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "LLM_EVALUATION_DATABASE_UNAVAILABLE\n")
        self.assertEqual(
            events,
            [
                "local-settings",
                "provider-settings",
                "canonical-fixtures",
                "pool",
                "pool-open:True",
                "repository",
                "probe",
                "readiness",
                "pool-close",
            ],
        )
        self.assertEqual(writes, [])

    def test_success_orders_lifecycle_reconciles_budget_and_writes_fixed_report(
        self,
    ) -> None:
        runner = _runner()
        events: list[str] = []
        writes: list[tuple[Path, dict[str, object]]] = []
        patches = self._patch_happy_dependencies(events, writes=writes)
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patches[7],
            patches[8],
            patches[9],
            patches[10],
            patch.object(
                runner,
                "_configure_event_loop_policy",
                side_effect=lambda platform: events.append(f"policy:{platform}"),
            ),
            patch.object(runner.sys, "platform", "win32"),
        ):
            result, stdout, stderr = self._capture_main([])

        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(
            stdout,
            "LLM_EVALUATION_COMPLETE\n"
            "REPORT=artifacts/llm-002/upstage-synthetic-evaluation.json\n"
            "OVERALL_PASS=false\n",
        )
        self.assertEqual(
            events,
            [
                "policy:win32",
                "local-settings",
                "provider-settings",
                "canonical-fixtures",
                "pool",
                "pool-open:True",
                "repository",
                "probe",
                "readiness",
                "client",
                "budget",
                "provider",
                "evaluator",
                "evaluation:3",
                "write",
                "client-close",
                "pool-close",
            ],
        )
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][0], runner._REPORT_PATH)
        serialized = json.dumps(writes[0][1], ensure_ascii=False, allow_nan=False)
        for forbidden in (_SECRET, _DSN, _QUESTION, _ANSWER):
            self.assertNotIn(forbidden, serialized)

    def test_runtime_failure_closes_client_and_pool_and_emits_no_details(self) -> None:
        events: list[str] = []
        patches = self._patch_happy_dependencies(events, run_error=True)
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patches[7],
            patches[8],
            patches[9],
            patches[10],
        ):
            result, stdout, stderr = self._capture_main([])

        self.assertEqual(result, 4)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "LLM_EVALUATION_RUNTIME_FAILED\n")
        for forbidden in (_SECRET, _DSN, _QUESTION, _ANSWER):
            self.assertNotIn(forbidden, stderr)
        self.assertEqual(events[-2:], ["client-close", "pool-close"])

    def test_budget_case_and_trace_mismatch_fails_before_report_write(self) -> None:
        runner = _runner()
        events: list[str] = []
        writes: list[tuple[Path, dict[str, object]]] = []
        patches = self._patch_happy_dependencies(events, writes=writes)

        def mismatched_budget(_settings: object) -> _FakeBudget:
            events.append("budget")
            return _FakeBudget(events, attempts_used=0)

        def provider_with_mismatched_budget(
            _settings: object,
            _client: object,
            _budget: object,
        ) -> object:
            events.append("provider")
            return object()

        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patches[5],
            patches[6],
            patch.object(runner, "_create_attempt_budget", mismatched_budget),
            patch.object(runner, "_create_provider", provider_with_mismatched_budget),
            patches[9],
            patches[10],
        ):
            result, stdout, stderr = self._capture_main([])

        self.assertEqual(result, 4)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "LLM_EVALUATION_RUNTIME_FAILED\n")
        self.assertEqual(writes, [])
        self.assertEqual(events[-2:], ["client-close", "pool-close"])

    def test_atomic_json_is_deterministic_utf8_and_leaves_no_temporary_file(
        self,
    ) -> None:
        runner = _runner()
        report = {"한글": "값", "a": 1}
        with tempfile.TemporaryDirectory() as directory:
            output_path = Path(directory) / "report.json"
            runner._atomic_write_report(output_path, report)
            first = output_path.read_bytes()
            runner._atomic_write_report(output_path, report)
            second = output_path.read_bytes()

            self.assertEqual(first, second)
            self.assertEqual(first, '{"a":1,"한글":"값"}\n'.encode())
            self.assertEqual(tuple(output_path.parent.iterdir()), (output_path,))

    def test_review_score_parser_derives_decision_and_accepts_no_free_text(
        self,
    ) -> None:
        runner = _runner()
        sample = _one_case_run().review_samples[0]
        answers = iter(["5", "4", "5", "5", "4", "INDIRECT"])
        review_output = io.StringIO()
        with (
            patch("builtins.input", side_effect=lambda _prompt: next(answers)),
            redirect_stdout(review_output),
        ):
            scores = runner._collect_human_scores((sample,))

        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0].fixture_id, "T-01")
        self.assertEqual(scores[0].decision, "FAIL")
        self.assertEqual(scores[0].reason_code, "INDIRECT")
        self.assertIn(_QUESTION, review_output.getvalue())
        self.assertIn(_ANSWER, review_output.getvalue())

        with (
            patch("builtins.input", return_value="because this is free text"),
            self.assertRaises(runner._ReviewInvalid),
        ):
            runner._read_reason_code()


if __name__ == "__main__":
    unittest.main()
