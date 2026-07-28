from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx
import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_API_SOURCE = _REPOSITORY_ROOT / "apps" / "api" / "src"
if str(_API_SOURCE) not in sys.path:
    sys.path.insert(0, str(_API_SOURCE))

from sejong_ai_api.chat.classification import SafeQuestion  # noqa: E402
from sejong_ai_api.db.models import Intent  # noqa: E402
from sejong_ai_api.llm.classifier_contracts import (  # noqa: E402
    ClassifierDecision,
    ClassifierRoute,
    parse_classifier_wire_decision_with_stage,
)
from sejong_ai_api.llm.classifier_diagnostics import (  # noqa: E402
    ClassifierResponseStage,
)
from sejong_ai_api.llm.contracts import TokenUsage  # noqa: E402
from sejong_ai_api.llm.cost import estimate_cost_usd  # noqa: E402
from sejong_ai_api.llm.settings import UpstageClassifierSettings  # noqa: E402

_RUNNER_MODULE_NAME = "_sejong_hybrid_rag_actual_runner_test"
_RUNNER_PATH = _REPOSITORY_ROOT / "scripts" / "run_hybrid_rag_actual.py"
_APPROVED_CASE_TABLE_COLUMNS = (
    "Fixture ID",
    "Evidence kind",
    "Provider decision accepted",
    "Actual provider route/topic match",
    "Outbound",
)
_FORBIDDEN_PRIVACY_MARKERS = (
    "provider payload",
    "provider body",
    "response body",
    "invalid value",
    "status detail",
    "exception",
    "question",
    "api_key",
    "authorization",
    "bearer ",
    "database_url",
    "dsn",
    "postgresql://",
    "offline-test-key",
    "secret",
    "| Fixture ID | Provider response stage |",
)


def _runner() -> ModuleType:
    cached = sys.modules.get(_RUNNER_MODULE_NAME)
    if cached is not None:
        return cached
    if not _RUNNER_PATH.is_file():
        pytest.fail("the hybrid rag actual runner is missing")
    spec = importlib.util.spec_from_file_location(_RUNNER_MODULE_NAME, _RUNNER_PATH)
    if spec is None or spec.loader is None:
        pytest.fail("the hybrid rag actual runner cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_RUNNER_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def _oracle_wire_payload(decision: ClassifierDecision) -> bytes:
    def nullable(value: object | None) -> str:
        if value is None:
            return "NONE"
        return value.value if hasattr(value, "value") else str(value)

    return json.dumps(
        {
            "route": decision.route.value,
            "intent": nullable(decision.intent),
            "topic_id": nullable(decision.topic_id),
            "coverage_id": nullable(decision.coverage_id),
            "pending_slot": nullable(decision.pending_slot),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _markdown_columns(line: str) -> tuple[str, ...]:
    return tuple(cell.strip() for cell in line.strip().strip("|").split("|"))


def _assert_aggregate_case_table_and_non_retention(
    markdown: str,
    *,
    selected_questions: tuple[str, ...],
    console: str = "",
) -> None:
    lines = markdown.splitlines()
    case_headers = tuple(
        (index, line)
        for index, line in enumerate(lines)
        if _markdown_columns(line)[:1] == ("Fixture ID",)
    )

    assert len(case_headers) == 1
    header_index, header = case_headers[0]
    assert _markdown_columns(header) == _APPROVED_CASE_TABLE_COLUMNS
    assert len(_markdown_columns(lines[header_index + 1])) == len(
        _APPROVED_CASE_TABLE_COLUMNS
    )
    for row in lines[header_index + 2 :]:
        if not row.startswith("|"):
            break
        assert len(_markdown_columns(row)) == len(_APPROVED_CASE_TABLE_COLUMNS)

    evidence = (console + markdown).casefold()
    for question in selected_questions:
        assert question.casefold() not in evidence
    for marker in _FORBIDDEN_PRIVACY_MARKERS:
        assert marker.casefold() not in evidence


def test_actual_subset_is_the_exact_pii_free_allowlist() -> None:
    runner = _runner()
    fixtures = runner._load_fixtures(runner._FIXTURE_PATH)

    selected = tuple(case.fixture_id for case in fixtures if case.actual_subset)

    assert selected == (
        "HR-001",
        "HR-002",
        "HR-003",
        "HR-004",
        "HR-005",
        "HR-006",
        "HR-007",
        "HR-008",
        "HR-021",
        "HR-022",
        "HR-023",
        "HR-024",
        "HR-033",
        "HR-034",
        "HR-035",
        "HR-036",
        "HR-037",
        "HR-038",
        "HR-039",
        "HR-040",
    )
    assert all(
        case.group != "PRIVACY_POLICY" for case in fixtures if case.actual_subset
    )
    assert all(case.safe_for_provider for case in fixtures if case.actual_subset)
    assert (
        sum(case.expected_provider_use for case in fixtures if case.actual_subset) == 9
    )


def test_actual_provider_subset_oracles_round_trip_through_production_wire_parser() -> (
    None
):
    runner = _runner()
    fixtures = runner._load_fixtures(runner._FIXTURE_PATH)
    _, catalog = runner._load_pinned_inputs()
    provider_cases = tuple(
        case
        for case in fixtures
        if case.actual_subset and case.expected_provider_use == 1
    )

    assert tuple(case.fixture_id for case in provider_cases) == (
        "HR-001",
        "HR-002",
        "HR-003",
        "HR-004",
        "HR-007",
        "HR-008",
        "HR-037",
        "HR-039",
        "HR-040",
    )
    for case in provider_cases:
        oracle = _oracle_decision(runner, case.fixture_id)
        parsed = parse_classifier_wire_decision_with_stage(
            _oracle_wire_payload(oracle),
            catalog,
        )

        assert parsed.stage is ClassifierResponseStage.ACCEPTED
        assert parsed.decision == oracle


def test_scope_gap_out_of_scope_fixture_uses_civic_scope_gap_all_none_provider_wire() -> (
    None
):
    runner = _runner()
    fixtures = {
        case.fixture_id: case for case in runner._load_fixtures(runner._FIXTURE_PATH)
    }

    for fixture_id in ("HR-037", "HR-039", "HR-040"):
        fixture = fixtures[fixture_id]
        provider_wire = _oracle_wire_payload(_oracle_decision(runner, fixture_id))

        assert json.loads(provider_wire.decode("utf-8")) == {
            "route": "CIVIC_SCOPE_GAP",
            "intent": "NONE",
            "topic_id": "NONE",
            "coverage_id": "NONE",
            "pending_slot": "NONE",
        }
        assert fixture.expected_intent == "OUT_OF_SCOPE"


def test_injected_offline_selector_writes_only_case_id_aggregates() -> None:
    runner = _runner()
    fixtures = runner._load_fixtures(runner._FIXTURE_PATH)
    selected = tuple(case for case in fixtures if case.actual_subset)
    fixture_id_by_question = {case.question: case.fixture_id for case in selected}

    class Selector:
        def __init__(self) -> None:
            self.calls = 0

        async def classify(self, question: SafeQuestion) -> ClassifierDecision:
            self.calls += 1
            return _oracle_decision(
                runner,
                fixture_id_by_question[question.text],
            )

    selector = Selector()
    usage = TokenUsage(90, 0, 45)
    result = asyncio.run(
        runner._evaluate_selected(
            selected,
            selector=selector,
            usage=usage,
            cost_cap=Decimal("0.20"),
        )
    )
    report = runner._build_report(
        result=result,
        usage=usage,
        key_present=True,
        source_sha="a" * 40,
    )
    markdown = runner._report_to_markdown(report)

    assert selector.calls == 9
    assert result.cases_total == 20
    assert result.deterministic_count == 11
    assert result.provider_case_count == 9
    assert result.outbound_attempt_count == 9
    assert result.route_topic_match_count == 9
    assert Decimal(report["observed_usage_cost_usd_including_vat"]) == (
        estimate_cost_usd(usage)
    )
    assert report["acceptance"] == "PASS"
    assert "HR-001" in markdown
    assert (
        "`PRIOR_OFFLINE_PROVIDER_FREE` | `not-applicable` | `not-applicable` | `0`"
    ) in markdown
    _assert_aggregate_case_table_and_non_retention(
        markdown,
        selected_questions=tuple(case.question for case in selected),
    )


def test_cost_gate_stops_before_injected_selector_call() -> None:
    runner = _runner()
    fixtures = runner._load_fixtures(runner._FIXTURE_PATH)
    selected = tuple(case for case in fixtures if case.actual_subset)

    class Selector:
        calls = 0

        async def classify(self, _question: object) -> ClassifierDecision:
            self.calls += 1
            raise AssertionError("cost gate must stop before a provider call")

    selector = Selector()
    with pytest.raises(runner._RuntimeFailed):
        asyncio.run(
            runner._evaluate_selected(
                selected,
                selector=selector,
                usage=TokenUsage(0, 0, 0),
                cost_cap=Decimal("0.000001"),
            )
        )
    assert selector.calls == 0


def test_case_outbound_evidence_uses_ledger_delta_not_expected_use() -> None:
    runner = _runner()
    fixtures = runner._load_fixtures(runner._FIXTURE_PATH)
    selected = tuple(case for case in fixtures if case.actual_subset)
    fixture_id_by_question = {case.question: case.fixture_id for case in selected}
    evidence = runner._RunEvidence(ledger=runner._build_ledger(_combined_settings()))

    class NonReservingSelector:
        async def classify(self, safe: SafeQuestion) -> ClassifierDecision:
            return _oracle_decision(runner, fixture_id_by_question[safe.text])

    result = asyncio.run(
        runner._evaluate_selected(
            selected,
            selector=NonReservingSelector(),
            usage=TokenUsage(0, 0, 0),
            cost_cap=Decimal("0.20"),
            evidence=evidence,
        )
    )

    provider_rows = tuple(
        case
        for case in result.cases
        if case.evidence_kind == "ACTUAL_PROVIDER_SELECTOR"
    )
    assert result.outbound_attempt_count == 0
    assert all(case.outbound_count == 0 for case in provider_rows)


def test_authoritative_offline_evidence_is_exactly_identity_pinned() -> None:
    runner = _runner()

    assert runner._require_offline_gate() == (
        "e699315d87cce99ad9a1e46e80cc18b6194db5b2cf251f57ad02e5acdc4042fe"
    )


def test_pinned_inputs_validate_release_and_active_official_projection() -> None:
    runner = _runner()

    identities, catalog = runner._load_pinned_inputs()

    assert identities.fixture_sha256 == (
        "4c6bf8cad6a00c94775f36b3731e7878a10722a2031e97e2a49fb8cb2141351d"
    )
    assert identities.coverage_sha256 == (
        "94b856bf87723893cbce9b29bf4c7125828a1624b79f6419c58d45b6bb5eb663"
    )
    assert identities.official_records_sha256 == (
        "1c4c303d8f0057d285023ba18a3d2829fcf856c1140baa270456aaf061c0fdaf"
    )
    assert identities.release_manifest_sha256 == (
        "0ccf3326616fdf0d9d96622f560e30da75d457c8295fc8bf37d2a601829a11a9"
    )
    assert identities.release_version == "0.1.0-initial.2"
    assert len(catalog.topics) == 19


def test_usage_recorder_records_value_free_response_families_and_strict_usage() -> None:
    runner = _runner()
    recorder = runner._UsageRecorder()
    valid = httpx.Response(
        200,
        json={
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "total_tokens": 30,
                "prompt_tokens_details": {"cached_tokens": 5},
            }
        },
    )
    invalid_usage = httpx.Response(
        200,
        json={"usage": {"prompt_tokens": "not-an-integer", "completion_tokens": 10}},
    )
    client_error = httpx.Response(
        401,
        json={"error": {"message": "must never be retained"}},
    )
    server_error = httpx.Response(
        503,
        json={"usage": {"prompt_tokens": 20, "completion_tokens": 10}},
    )
    other_status = httpx.Response(302)

    asyncio.run(recorder.capture(valid))
    asyncio.run(recorder.capture(invalid_usage))
    asyncio.run(recorder.capture(client_error))
    asyncio.run(recorder.capture(server_error))
    asyncio.run(recorder.capture(other_status))

    assert recorder.usage == TokenUsage(20, 5, 10)
    assert recorder.complete_response_count == 1
    assert recorder.rejected_response_count == 4
    assert recorder.response_count == 5
    assert recorder.http_2xx_count == 2
    assert recorder.http_4xx_count == 1
    assert recorder.http_5xx_count == 1
    assert recorder.http_other_count == 1
    assert recorder.usage_rejected_count == 1


def test_response_stage_recorder_accepts_only_closed_enum_and_counts_aggregates() -> (
    None
):
    runner = _runner()
    recorder = runner._ResponseStageRecorder()

    recorder.capture(ClassifierResponseStage.ACCEPTED)
    recorder.capture(ClassifierResponseStage.ACCEPTED)
    recorder.capture(ClassifierResponseStage.JSON_REJECTED)

    assert recorder.total == 3
    assert recorder.count(ClassifierResponseStage.ACCEPTED) == 2
    assert recorder.count(ClassifierResponseStage.JSON_REJECTED) == 1
    with pytest.raises(ValueError, match="CLASSIFIER_RESPONSE_STAGE_INVALID"):
        recorder.capture("ACCEPTED")


def test_report_has_all_response_stage_aggregate_fields_in_fixed_order() -> None:
    runner = _runner()
    stage_fields = tuple(
        field for field in runner._REPORT_FIELDS if field.startswith("provider_stage_")
    )

    assert stage_fields == tuple(
        f"provider_stage_{stage.value.casefold()}_count"
        for stage in ClassifierResponseStage
    )
    assert "provider_response_stage_total" in runner._REPORT_FIELDS
    assert "provider_stage_enum_shape_rejected_count" in stage_fields


def test_cross_process_lease_blocks_concurrent_and_existing_evidence(
    tmp_path: Path,
) -> None:
    runner = _runner()
    report_path = tmp_path / "evidence.md"
    first = runner._RunLease.acquire(report_path)
    try:
        with pytest.raises(runner._RunAlreadyExists):
            runner._RunLease.acquire(report_path)
    finally:
        first.release(report_written=False)

    report_path.write_text("acknowledgement required", encoding="utf-8")
    with pytest.raises(runner._RunAlreadyExists):
        runner._RunLease.acquire(report_path)


def test_atomic_report_uses_unique_same_directory_temporary_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    destination = tmp_path / "evidence.md"
    replaced_sources: list[Path] = []
    real_replace = os.replace

    def capture_replace(source: str | Path, target: str | Path) -> None:
        source_path = Path(source)
        assert source_path.parent == destination.parent
        replaced_sources.append(source_path)
        real_replace(source, target)

    monkeypatch.setattr(runner.os, "replace", capture_replace)
    runner._atomic_write_text(destination, "first\n")
    runner._atomic_write_text(destination, "second\n")

    assert destination.read_text(encoding="utf-8") == "second\n"
    assert len(set(replaced_sources)) == 2
    assert not any(path.exists() for path in replaced_sources)


def test_windows_destination_sharing_failure_preserves_old_evidence_and_cleans_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    destination = tmp_path / "evidence.md"
    destination.write_text("old evidence\n", encoding="utf-8")

    def sharing_violation(_source: object, _target: object) -> None:
        raise PermissionError("synthetic Windows sharing violation")

    monkeypatch.setattr(runner.os, "replace", sharing_violation)

    with pytest.raises(runner._RuntimeFailed):
        runner._atomic_write_text(destination, "new evidence\n")

    assert destination.read_text(encoding="utf-8") == "old evidence\n"
    assert not list(tmp_path.glob(".evidence.md.*.tmp"))


def _combined_settings() -> UpstageClassifierSettings:
    return UpstageClassifierSettings(
        api_key="offline-test-key",
        classifier_attempt_cap=80,
        generator_attempt_cap=100,
        combined_attempt_cap=160,
        session_cost_cap_usd=Decimal("0.20"),
    )


def test_main_preflight_failure_writes_sanitized_fail_before_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    report_path = tmp_path / "actual.md"
    options = runner._RunnerOptions(runner._FIXTURE_PATH, report_path)
    client_calls = 0
    environment_before = dict(os.environ)

    monkeypatch.setattr(runner, "_parse_args", lambda _argv=None: options)
    monkeypatch.setattr(
        runner,
        "_require_offline_gate",
        lambda: (_ for _ in ()).throw(
            runner._ConfigurationInvalid(
                "question=private payload=secret postgresql://sensitive"
            )
        ),
    )

    def forbidden_client(_settings: object) -> object:
        nonlocal client_calls
        client_calls += 1
        raise AssertionError("client must not be constructed")

    monkeypatch.setattr(runner, "create_upstage_classifier_client", forbidden_client)

    assert runner.main([]) == 2
    captured = capsys.readouterr()
    report = report_path.read_text(encoding="utf-8")

    assert client_calls == 0
    assert os.environ == environment_before
    assert "`acceptance` | `FAIL`" in report
    for forbidden in ("private", "payload=", "postgresql://", "secret"):
        assert forbidden not in (captured.out + captured.err + report).casefold()


def test_fail_report_build_failure_keeps_console_value_free_and_lease_for_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    report_path = tmp_path / "actual.md"
    options = runner._RunnerOptions(runner._FIXTURE_PATH, report_path)

    monkeypatch.setattr(runner, "_parse_args", lambda _argv=None: options)

    async def fail_execute(_options: object, _evidence: object) -> object:
        raise runner._RuntimeFailed("private payload postgresql://sensitive")

    monkeypatch.setattr(runner, "_execute_actual", fail_execute)
    monkeypatch.setattr(
        runner,
        "_build_evidence_report",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            runner._RuntimeFailed("private report payload")
        ),
    )

    assert runner.main([]) == 3
    captured = capsys.readouterr()

    assert not report_path.exists()
    assert report_path.with_name(f"{report_path.name}.run.lock").exists()
    assert "EVIDENCE_WRITE_FAILED" in captured.err
    for forbidden in ("private", "payload", "postgresql://", "sensitive"):
        assert forbidden not in (captured.out + captured.err).casefold()


def test_main_partial_failure_records_bounded_attempt_and_cost_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    report_path = tmp_path / "actual.md"
    options = runner._RunnerOptions(runner._FIXTURE_PATH, report_path)
    settings = _combined_settings()

    monkeypatch.setattr(runner, "_parse_args", lambda _argv=None: options)
    monkeypatch.setattr(
        runner, "_require_offline_gate", lambda: runner._EXPECTED_OFFLINE_SHA256
    )
    monkeypatch.setattr(runner, "_require_clean_secret_scan", lambda: None)
    monkeypatch.setattr(runner, "_require_protected_inputs_clean", lambda: None)
    monkeypatch.setattr(runner, "load_upstage_classifier_settings", lambda: settings)
    monkeypatch.setattr(
        runner, "create_upstage_classifier_client", lambda _settings: _FakeClient()
    )

    calls = 0

    def selector_factory(
        _settings: object,
        _client: object,
        ledger: Any,
        catalog: Any,
        recorder: Any,
        response_stages: Any,
    ) -> Any:
        del catalog

        class PartialSelector:
            async def classify(self, question: SafeQuestion) -> ClassifierDecision:
                nonlocal calls
                calls += 1
                async with ledger.reserve_classifier() as reservation:
                    if calls == 1:
                        usage = TokenUsage(20, 5, 10)
                        reservation.record_usage(usage)
                        await recorder.capture(
                            httpx.Response(
                                200,
                                json={
                                    "usage": {
                                        "prompt_tokens": 20,
                                        "completion_tokens": 10,
                                        "prompt_tokens_details": {"cached_tokens": 5},
                                    }
                                },
                            )
                        )
                        response_stages.capture(
                            ClassifierResponseStage.ROUTE_ENUM_REJECTED
                        )
                        return _oracle_decision(runner, "HR-001")
                    raise RuntimeError(
                        f"private question payload key postgresql:// {question.text}"
                    )

        return PartialSelector()

    monkeypatch.setattr(runner, "_create_selector", selector_factory)

    assert runner.main([]) == 3
    captured = capsys.readouterr()
    report = report_path.read_text(encoding="utf-8")

    assert "`outbound_attempt_count` | `2`" in report
    assert "`provider_response_count` | `1`" in report
    assert "`provider_http_2xx_count` | `1`" in report
    assert "`provider_transport_no_response_count` | `1`" in report
    assert "`provider_decision_accepted_count` | `1`" in report
    assert "`provider_response_stage_total` | `1`" in report
    assert "`provider_stage_route_enum_rejected_count` | `1`" in report
    assert "`provider_stage_enum_shape_rejected_count` | `0`" in report
    assert "`observed_usage_response_count` | `1`" in report
    assert "`conservative_charged_attempt_count` | `1`" in report
    assert "`acceptance` | `FAIL`" in report
    stage_fields = tuple(
        f"provider_stage_{stage.value.casefold()}_count"
        for stage in ClassifierResponseStage
    )
    stage_lines = tuple(
        line for line in report.splitlines() if line.startswith("| `provider_stage_")
    )
    assert stage_lines == tuple(
        f"| `{field}` | `{1 if field == 'provider_stage_route_enum_rejected_count' else 0}` |"
        for field in stage_fields
    )
    for forbidden in (
        "private",
        "payload",
        "postgresql://",
        "question",
        "invalid value",
        "status detail",
        "exception",
        "offline-test-key",
        "| Fixture ID | Provider response stage |",
    ):
        assert (
            forbidden.casefold()
            not in (captured.out + captured.err + report).casefold()
        )


@pytest.mark.parametrize(
    "failing_gate",
    ("fixtures", "offline", "secret", "protected", "settings", "inputs", "source"),
)
def test_execute_preflight_gates_all_finish_before_client_creation(
    failing_gate: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    evidence = runner._RunEvidence()
    options = runner._RunnerOptions(runner._FIXTURE_PATH, runner._REPORT_PATH)
    settings = _combined_settings()
    client_calls = 0

    monkeypatch.setattr(
        runner, "_require_offline_gate", lambda: runner._EXPECTED_OFFLINE_SHA256
    )
    monkeypatch.setattr(runner, "_require_clean_secret_scan", lambda: None)
    monkeypatch.setattr(runner, "_require_protected_inputs_clean", lambda: None)
    monkeypatch.setattr(runner, "load_upstage_classifier_settings", lambda: settings)
    monkeypatch.setattr(runner, "_source_sha", lambda: "a" * 40)

    if failing_gate == "fixtures":
        monkeypatch.setattr(
            runner,
            "_load_fixtures",
            lambda _path: (_ for _ in ()).throw(runner._FixturesInvalid()),
        )
    elif failing_gate == "offline":
        monkeypatch.setattr(
            runner,
            "_require_offline_gate",
            lambda: (_ for _ in ()).throw(runner._ConfigurationInvalid()),
        )
    elif failing_gate == "secret":
        monkeypatch.setattr(
            runner,
            "_require_clean_secret_scan",
            lambda: (_ for _ in ()).throw(runner._ConfigurationInvalid()),
        )
    elif failing_gate == "protected":
        monkeypatch.setattr(
            runner,
            "_require_protected_inputs_clean",
            lambda: (_ for _ in ()).throw(runner._ConfigurationInvalid()),
        )
    elif failing_gate == "settings":
        monkeypatch.setattr(runner, "load_upstage_classifier_settings", lambda: None)
    elif failing_gate == "inputs":
        monkeypatch.setattr(
            runner,
            "_load_pinned_inputs",
            lambda: (_ for _ in ()).throw(runner._ConfigurationInvalid()),
        )
    else:
        monkeypatch.setattr(
            runner,
            "_source_sha",
            lambda: (_ for _ in ()).throw(runner._ConfigurationInvalid()),
        )

    def forbidden_client(_settings: object) -> object:
        nonlocal client_calls
        client_calls += 1
        raise AssertionError("preflight must finish before client construction")

    monkeypatch.setattr(runner, "create_upstage_classifier_client", forbidden_client)

    with pytest.raises((runner._ConfigurationInvalid, runner._FixturesInvalid)):
        asyncio.run(runner._execute_actual(options, evidence))

    assert client_calls == 0
    assert evidence.ledger is None


def test_exact_combined_profile_is_required() -> None:
    runner = _runner()

    runner._validate_settings(_combined_settings())
    with pytest.raises(runner._ConfigurationInvalid):
        runner._validate_settings(
            UpstageClassifierSettings(
                api_key="offline-test-key",
                classifier_attempt_cap=80,
                generator_attempt_cap=100,
                combined_attempt_cap=160,
                session_cost_cap_usd=Decimal("0.20"),
                max_retries=1,
            )
        )


def test_main_pass_is_atomic_aggregate_only_and_blocks_implicit_rerun(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    report_path = tmp_path / "actual.md"
    options = runner._RunnerOptions(runner._FIXTURE_PATH, report_path)
    settings = _combined_settings()
    fixtures = runner._load_fixtures(runner._FIXTURE_PATH)
    fixture_id_by_question = {
        case.question: case.fixture_id for case in fixtures if case.actual_subset
    }
    client_calls = 0
    environment_before = dict(os.environ)

    monkeypatch.setattr(runner, "_parse_args", lambda _argv=None: options)
    monkeypatch.setattr(runner, "_require_clean_secret_scan", lambda: None)
    monkeypatch.setattr(runner, "_require_protected_inputs_clean", lambda: None)
    monkeypatch.setattr(runner, "load_upstage_classifier_settings", lambda: settings)

    def client_factory(_settings: object) -> _FakeClient:
        nonlocal client_calls
        client_calls += 1
        return _FakeClient()

    monkeypatch.setattr(runner, "create_upstage_classifier_client", client_factory)

    def selector_factory(
        _settings: object,
        _client: object,
        ledger: Any,
        _catalog: Any,
        recorder: Any,
        response_stages: Any,
    ) -> Any:
        class PassingSelector:
            async def classify(self, safe: SafeQuestion) -> ClassifierDecision:
                usage = TokenUsage(20, 5, 10)
                async with ledger.reserve_classifier() as reservation:
                    reservation.record_usage(usage)
                    await recorder.capture(
                        httpx.Response(
                            200,
                            json={
                                "usage": {
                                    "prompt_tokens": 20,
                                    "completion_tokens": 10,
                                    "total_tokens": 30,
                                    "cached_tokens": 5,
                                }
                            },
                        )
                    )
                    response_stages.capture(ClassifierResponseStage.ACCEPTED)
                return _oracle_decision(
                    runner,
                    fixture_id_by_question[safe.text],
                )

        return PassingSelector()

    monkeypatch.setattr(runner, "_create_selector", selector_factory)

    assert runner.main([]) == 0
    first_console = capsys.readouterr()
    report = report_path.read_text(encoding="utf-8")
    console_report = json.loads(first_console.out)

    assert client_calls == 1
    assert os.environ == environment_before
    assert "`provider_route_topic_match_count` | `9`" in report
    assert "`prior_offline_deterministic_provider_free_count` | `11`" in report
    assert "`provider_response_count` | `9`" in report
    assert "`provider_http_2xx_count` | `9`" in report
    assert "`provider_transport_no_response_count` | `0`" in report
    assert "`provider_usage_rejected_count` | `0`" in report
    assert "`provider_decision_accepted_count` | `9`" in report
    assert "`provider_decision_rejected_count` | `0`" in report
    assert "`provider_contract_mismatch_count` | `0`" in report
    assert "`provider_response_stage_total` | `9`" in report
    assert "`provider_stage_accepted_count` | `9`" in report
    for stage in ClassifierResponseStage:
        expected = 9 if stage is ClassifierResponseStage.ACCEPTED else 0
        assert (
            f"`provider_stage_{stage.value.casefold()}_count` | `{expected}`" in report
        )
    stage_fields = tuple(
        f"provider_stage_{stage.value.casefold()}_count"
        for stage in ClassifierResponseStage
    )
    assert (
        tuple(field for field in console_report if field.startswith("provider_stage_"))
        == stage_fields
    )
    assert tuple(
        line for line in report.splitlines() if line.startswith("| `provider_stage_")
    ) == tuple(
        f"| `{field}` | `{9 if field == 'provider_stage_accepted_count' else 0}` |"
        for field in stage_fields
    )
    assert report.count("provider_stage_enum_shape_rejected_count") == 1
    assert console_report["provider_stage_enum_shape_rejected_count"] == 0
    assert "`cost_reconciled` | `True`" in report
    assert "`acceptance` | `PASS`" in report
    assert not list(tmp_path.glob(".*.tmp"))
    _assert_aggregate_case_table_and_non_retention(
        report,
        selected_questions=tuple(
            case.question for case in fixtures if case.actual_subset
        ),
        console=first_console.out + first_console.err,
    )

    report_before_rerun = report_path.read_bytes()
    assert runner.main([]) == 2
    second_console = capsys.readouterr()

    assert client_calls == 1
    assert report_path.read_bytes() == report_before_rerun
    assert "RUN_ALREADY_RECORDED" in second_console.err


class _FakeClient:
    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None


def _oracle_decision(runner: ModuleType, fixture_id: str) -> ClassifierDecision:
    supported = {
        "HR-001": (
            Intent.MOVE_IN_RESIDENT_REGISTRATION,
            "KB-MOVE-01",
            "MOVE_IN_OVERVIEW_APPLICATION",
        ),
        "HR-002": (
            Intent.MOVE_IN_RESIDENT_REGISTRATION,
            "KB-MOVE-03",
            "MOVE_IN_ONLINE_APPLICATION",
        ),
        "HR-003": (
            Intent.MOVE_IN_RESIDENT_REGISTRATION,
            "KB-MOVE-02",
            "MOVE_IN_VISIT_REQUIREMENTS",
        ),
        "HR-004": (
            Intent.MOVE_IN_RESIDENT_REGISTRATION,
            "KB-MOVE-04",
            "RESIDENT_NOTIFICATION_SERVICE",
        ),
        "HR-007": (
            Intent.CERTIFICATE_ISSUANCE,
            "KB-CERT-03",
            "RESIDENT_REGISTER_TRANSCRIPT_ISSUANCE",
        ),
        "HR-008": (
            Intent.CERTIFICATE_ISSUANCE,
            "KB-CERT-04",
            "RESIDENT_REGISTER_VIEWING",
        ),
    }
    if fixture_id in supported:
        intent, topic_id, coverage_id = supported[fixture_id]
        return ClassifierDecision(
            ClassifierRoute.SUPPORTED,
            intent,
            topic_id,
            coverage_id,
            None,
        )
    if fixture_id in {"HR-037", "HR-039", "HR-040"}:
        return ClassifierDecision(
            ClassifierRoute.CIVIC_SCOPE_GAP,
            None,
            None,
            None,
            None,
        )
    raise AssertionError(f"unhandled test oracle id: {fixture_id}")
