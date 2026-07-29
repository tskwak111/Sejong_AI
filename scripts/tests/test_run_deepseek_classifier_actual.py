from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from collections import Counter
from dataclasses import replace
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
)
from sejong_ai_api.llm.classifier_diagnostics import (  # noqa: E402
    ClassifierResponseStage,
)
from sejong_ai_api.llm.contracts import TokenUsage  # noqa: E402
from sejong_ai_api.llm.deepseek_settings import (  # noqa: E402
    DeepSeekClassifierSettings,
)
from sejong_ai_api.llm.deepseek_usage import (  # noqa: E402
    estimate_deepseek_cost_usd,
)

_RUNNER_MODULE_NAME = "_sejong_deepseek_classifier_actual_runner_test"
_RUNNER_PATH = _REPOSITORY_ROOT / "scripts" / "run_deepseek_classifier_actual.py"
_EXPECTED_FIXTURE_SHA256 = (
    "4c6bf8cad6a00c94775f36b3731e7878a10722a2031e97e2a49fb8cb2141351d"
)
_FORBIDDEN_SOURCE_REFERENCES = (
    "run_hybrid_rag_actual",
    "run_upstage_classifier_evaluation",
    "CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL",
    "UPSTAGE-CLASSIFIER-ACTUAL",
)
_FORBIDDEN_VALUE_MARKERS = (
    "synthetic-secret-marker",
    "synthetic-invalid-value-marker",
    "synthetic-provider-body-marker",
    "postgresql://synthetic-dsn-marker",
    "authorization: bearer",
)


def _runner() -> ModuleType:
    cached = sys.modules.get(_RUNNER_MODULE_NAME)
    if cached is not None:
        return cached
    if not _RUNNER_PATH.is_file():
        pytest.fail("the DeepSeek classifier actual runner is missing")
    spec = importlib.util.spec_from_file_location(_RUNNER_MODULE_NAME, _RUNNER_PATH)
    if spec is None or spec.loader is None:
        pytest.fail("the DeepSeek classifier actual runner cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_RUNNER_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _prepared(runner: ModuleType, report_path: Path) -> Any:
    fixtures = runner._load_fixtures(runner._FIXTURE_PATH)
    selection = runner._select_actual_cases(fixtures)
    catalog = runner._load_pinned_catalog()
    return runner._PreparedRun(
        source_sha="a" * 40,
        settings=DeepSeekClassifierSettings(api_key="synthetic-secret-marker"),
        fixtures=fixtures,
        selection=selection,
        catalog=catalog,
        identities=runner._InputIdentities(
            fixture_sha256=_EXPECTED_FIXTURE_SHA256,
            coverage_sha256="b" * 64,
            official_records_sha256="c" * 64,
            release_manifest_sha256="d" * 64,
            offline_result_sha256="e" * 64,
            release_version="0.1.0-initial.2",
        ),
        report_path=report_path,
    )


def _passing_evidence(runner: ModuleType, report_path: Path) -> Any:
    prepared = _prepared(runner, report_path)
    usage = TokenUsage(input_tokens=900, cached_input_tokens=450, output_tokens=90)
    evidence = runner._new_evidence(prepared)
    evidence.selected_count = 20
    evidence.skip_count = 0
    evidence.deterministic_provider_free_count = 11
    evidence.provider_case_count = 9
    evidence.policy_privacy_probe_count = 4
    evidence.policy_privacy_outbound_count = 0
    evidence.outbound_attempt_count = 9
    evidence.provider_response_count = 9
    evidence.http_2xx_count = 9
    evidence.http_rejected_count = 0
    evidence.transport_no_response_count = 0
    evidence.strict_parse_count = 9
    evidence.server_decision_accepted_count = 9
    evidence.oracle_match_count = 9
    evidence.usage_accepted_count = 9
    evidence.usage_rejected_count = 0
    evidence.response_stage_counts = Counter({ClassifierResponseStage.ACCEPTED: 9})
    evidence.usage = usage
    evidence.conservative_cost_usd = estimate_deepseek_cost_usd(usage)
    return evidence


def test_source_does_not_reuse_a073_or_upstage_actual_runner() -> None:
    source = _RUNNER_PATH.read_text(encoding="utf-8")

    for forbidden in _FORBIDDEN_SOURCE_REFERENCES:
        assert forbidden not in source
    assert "upstage_classifier import" not in source


def test_cli_accepts_only_canonical_fixture_and_report_paths() -> None:
    runner = _runner()

    options = runner._parse_args(
        [
            "--fixture",
            str(runner._FIXTURE_PATH),
            "--report",
            str(runner._REPORT_PATH),
            "--readiness-only",
        ]
    )

    assert options.fixture_path == runner._FIXTURE_PATH.resolve()
    assert options.report_path == runner._REPORT_PATH.resolve()
    assert options.readiness_only is True
    with pytest.raises(runner._ArgumentsInvalid):
        runner._parse_args(
            [
                "--fixture",
                str(runner._FIXTURE_PATH.with_name("other.json")),
                "--report",
                str(runner._REPORT_PATH),
            ]
        )
    with pytest.raises(runner._ArgumentsInvalid):
        runner._parse_args(
            [
                "--fixture",
                str(runner._FIXTURE_PATH),
                "--report",
                str(runner._REPORT_PATH.with_name("other.md")),
            ]
        )


def test_fixture_identity_and_actual_distribution_are_exact() -> None:
    runner = _runner()

    fixtures = runner._load_fixtures(runner._FIXTURE_PATH)
    selection = runner._select_actual_cases(fixtures)

    assert _sha256(runner._FIXTURE_PATH) == _EXPECTED_FIXTURE_SHA256
    assert len(fixtures) == 48
    assert selection.selected_count == 20
    assert selection.skip_count == 0
    assert selection.deterministic_provider_free_count == 11
    assert selection.provider_case_count == 9
    assert len(selection.selected) == 20


def test_four_policy_privacy_probes_cross_real_redaction_boundary_with_zero_outbound() -> (
    None
):
    runner = _runner()
    fixtures = runner._load_fixtures(runner._FIXTURE_PATH)

    result = runner._evaluate_policy_privacy_probes(fixtures)

    assert result.probe_count == 4
    assert result.outbound_count == 0


def test_readiness_only_is_client_lease_report_and_temp_free_and_restores_modes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    report_path = tmp_path / "actual.md"
    options = runner._RunnerOptions(
        fixture_path=runner._FIXTURE_PATH,
        report_path=report_path,
        readiness_only=True,
    )
    environment_before = {
        "UPSTAGE_SYNTHETIC_EVALUATION_MODE": "synthetic-before",
        "UPSTAGE_CLASSIFIER_MODE": "classifier-before",
        "UPSTAGE_GROUNDED_CHAT_MODE": "generator-before",
    }
    for key, value in environment_before.items():
        monkeypatch.setenv(key, value)

    observed_modes: dict[str, str | None] = {}

    def ready(_options: object) -> object:
        observed_modes.update(
            {
                key: os.environ.get(key)
                for key in (
                    "UPSTAGE_SYNTHETIC_EVALUATION_MODE",
                    "UPSTAGE_CLASSIFIER_MODE",
                    "UPSTAGE_GROUNDED_CHAT_MODE",
                )
            }
        )
        return _prepared(runner, report_path)

    monkeypatch.setattr(runner, "_parse_args", lambda _argv=None: options)
    monkeypatch.setattr(runner, "_perform_readiness", ready)
    monkeypatch.setattr(
        runner._RunLease,
        "acquire",
        lambda _path: pytest.fail("readiness must not acquire a lease"),
    )
    monkeypatch.setattr(
        runner,
        "create_deepseek_classifier_client",
        lambda _settings: pytest.fail("readiness must not create a client"),
    )

    assert runner.main([]) == 0
    captured = capsys.readouterr()

    assert observed_modes == {
        "UPSTAGE_SYNTHETIC_EVALUATION_MODE": "false",
        "UPSTAGE_CLASSIFIER_MODE": "false",
        "UPSTAGE_GROUNDED_CHAT_MODE": "false",
    }
    assert {
        key: os.environ.get(key) for key in environment_before
    } == environment_before
    assert captured.out.strip() == "DEEPSEEK_CLASSIFIER_ACTUAL_READY"
    assert captured.err == ""
    assert not report_path.exists()
    assert not report_path.with_name(f"{report_path.name}.run.lock").exists()
    assert not list(tmp_path.glob(".*.tmp"))
    assert "synthetic-secret-marker" not in captured.out


def test_existing_report_or_permanent_lease_blocks_without_mutation(
    tmp_path: Path,
) -> None:
    runner = _runner()
    report_path = tmp_path / "actual.md"
    lease_path = report_path.with_name(f"{report_path.name}.run.lock")

    report_path.write_bytes(b"immutable-report")
    with pytest.raises(runner._RunAlreadyExists):
        runner._require_actual_absent(report_path)
    assert report_path.read_bytes() == b"immutable-report"

    report_path.unlink()
    lease_path.write_bytes(b"immutable-lease")
    with pytest.raises(runner._RunAlreadyExists):
        runner._require_actual_absent(report_path)
    assert lease_path.read_bytes() == b"immutable-lease"


def test_permanent_lease_is_atomic_fsynced_and_never_reusable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    report_path = tmp_path / "actual.md"
    fsync_calls: list[int] = []
    real_fsync = runner.os.fsync

    def recording_fsync(descriptor: int) -> None:
        fsync_calls.append(descriptor)
        real_fsync(descriptor)

    monkeypatch.setattr(runner.os, "fsync", recording_fsync)

    lease = runner._RunLease.acquire(report_path)
    lease_path = report_path.with_name(f"{report_path.name}.run.lock")

    assert lease.lock_path == lease_path
    assert lease_path.is_file()
    assert fsync_calls
    with pytest.raises(runner._RunAlreadyExists):
        runner._RunLease.acquire(report_path)
    assert lease_path.is_file()
    assert not report_path.exists()
    assert all(
        marker not in lease_path.read_text(encoding="ascii").casefold()
        for marker in ("question", "body", "secret", "key", "dsn")
    )


def test_clean_worktree_gate_rejects_untracked_source(tmp_path: Path) -> None:
    runner = _runner()
    repository = tmp_path / "가짜 저장소 with spaces"
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=repository,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "A074 Test"],
        cwd=repository,
        check=True,
    )
    tracked = repository / "tracked.txt"
    tracked.write_text("tracked\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "baseline"], cwd=repository, check=True)

    runner._require_clean_worktree(repository)
    untracked = repository / "scripts" / "untracked_source.py"
    untracked.parent.mkdir()
    untracked.write_text("print('untracked')\n", encoding="utf-8")

    with pytest.raises(runner._ConfigurationInvalid):
        runner._require_clean_worktree(repository)


def test_offline_pass_is_bound_to_exact_head_invocation_one_rerun_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    result_path = tmp_path / "a074-offline-gate-result.json"
    lock_path = tmp_path / "a074-offline-gate-result.json.run.lock"
    stdout_path = tmp_path / "a074-offline-gate.stdout.log"
    stderr_path = tmp_path / "a074-offline-gate.stderr.log"
    stdout_path.write_bytes(b"offline stdout\n")
    stderr_path.write_bytes(b"")
    lock_path.write_bytes(runner._OFFLINE_LEASE_TEXT.encode("ascii"))
    result_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "gate": "A-074-OFFLINE",
                "source_sha": "a" * 40,
                "outcome": "PASS",
                "exit_code": 0,
                "timed_out": False,
                "invocation_count": 1,
                "rerun_count": 0,
                "stdout_sha256": _sha256(stdout_path),
                "stdout_bytes": stdout_path.stat().st_size,
                "stderr_sha256": _sha256(stderr_path),
                "stderr_bytes": stderr_path.stat().st_size,
            },
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "_OFFLINE_RESULT_PATH", result_path)
    monkeypatch.setattr(runner, "_OFFLINE_LOCK_PATH", lock_path)
    monkeypatch.setattr(runner, "_OFFLINE_STDOUT_PATH", stdout_path)
    monkeypatch.setattr(runner, "_OFFLINE_STDERR_PATH", stderr_path)

    identity = runner._require_offline_gate("a" * 40)

    assert identity == _sha256(result_path)
    with pytest.raises(runner._ConfigurationInvalid):
        runner._require_offline_gate("b" * 40)


def test_exact_byte_loaders_parse_the_same_snapshot_they_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    fixture_bytes = runner._FIXTURE_PATH.read_bytes()
    coverage_bytes = runner._COVERAGE_PATH.read_bytes()
    official_bytes = runner._OFFICIAL_RECORDS_PATH.read_bytes()
    manifest_bytes = runner._RELEASE_MANIFEST_PATH.read_bytes()
    snapshots: dict[Path, bytes] = {
        runner._FIXTURE_PATH.resolve(): fixture_bytes,
        runner._COVERAGE_PATH.resolve(): coverage_bytes,
        runner._OFFICIAL_RECORDS_PATH.resolve(): official_bytes,
        runner._RELEASE_MANIFEST_PATH.resolve(): manifest_bytes,
    }
    reads: Counter[Path] = Counter()

    def read_once(path: Path, *, max_bytes: int) -> bytes:
        resolved = path.resolve()
        reads[resolved] += 1
        payload = snapshots[resolved]
        assert len(payload) <= max_bytes
        return payload

    monkeypatch.setattr(runner, "_read_bounded_file_once", read_once)
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda *_args, **_kwargs: pytest.fail("loader reread after hashing"),
    )

    fixtures = runner._load_fixtures(runner._FIXTURE_PATH)
    catalog = runner._load_pinned_catalog()

    assert len(fixtures) == 48
    assert len(catalog.topics) == 19
    assert reads == Counter(
        {
            runner._FIXTURE_PATH.resolve(): 1,
            runner._COVERAGE_PATH.resolve(): 1,
            runner._OFFICIAL_RECORDS_PATH.resolve(): 1,
            runner._RELEASE_MANIFEST_PATH.resolve(): 1,
        }
    )


@pytest.mark.parametrize(
    "mutation",
    ("head", "dirty", "fixture", "offline", "settings"),
)
def test_prelease_revalidation_rejects_every_prepared_identity_drift(
    mutation: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    prepared = _prepared(runner, tmp_path / "actual.md")
    fixture = tmp_path / "fixture.json"
    coverage = tmp_path / "coverage.json"
    official = tmp_path / "records.json"
    manifest = tmp_path / "manifest.json"
    fixture.write_bytes(b"fixture-snapshot")
    coverage.write_bytes(b"coverage-snapshot")
    official.write_bytes(b"official-snapshot")
    manifest.write_bytes(b"manifest-snapshot")
    identities = replace(
        prepared.identities,
        fixture_sha256=_sha256(fixture),
        coverage_sha256=_sha256(coverage),
        official_records_sha256=_sha256(official),
        release_manifest_sha256=_sha256(manifest),
        offline_result_sha256="e" * 64,
    )
    prepared = replace(prepared, identities=identities)
    monkeypatch.setattr(runner, "_FIXTURE_PATH", fixture)
    monkeypatch.setattr(runner, "_COVERAGE_PATH", coverage)
    monkeypatch.setattr(runner, "_OFFICIAL_RECORDS_PATH", official)
    monkeypatch.setattr(runner, "_RELEASE_MANIFEST_PATH", manifest)
    monkeypatch.setattr(runner, "_source_sha", lambda: prepared.source_sha)
    monkeypatch.setattr(runner, "_require_clean_worktree", lambda: None)
    monkeypatch.setattr(
        runner,
        "_require_offline_gate",
        lambda _source_sha: prepared.identities.offline_result_sha256,
    )
    monkeypatch.setattr(
        runner,
        "load_deepseek_classifier_settings",
        lambda: prepared.settings,
    )

    if mutation == "head":
        monkeypatch.setattr(runner, "_source_sha", lambda: "f" * 40)
    elif mutation == "dirty":
        monkeypatch.setattr(
            runner,
            "_require_clean_worktree",
            lambda: (_ for _ in ()).throw(runner._ConfigurationInvalid()),
        )
    elif mutation == "fixture":
        fixture.write_bytes(b"mutated-fixture")
    elif mutation == "offline":
        monkeypatch.setattr(
            runner,
            "_require_offline_gate",
            lambda _source_sha: "0" * 64,
        )
    else:
        changed_settings = DeepSeekClassifierSettings(api_key="different-synthetic-key")
        monkeypatch.setattr(
            runner,
            "load_deepseek_classifier_settings",
            lambda: changed_settings,
        )

    with pytest.raises(runner._ConfigurationInvalid):
        runner._revalidate_prepared_run(prepared)


def test_main_revalidates_immediately_before_lease_and_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    report_path = tmp_path / "actual.md"
    options = runner._RunnerOptions(
        fixture_path=runner._FIXTURE_PATH,
        report_path=report_path,
        readiness_only=False,
    )
    prepared = _prepared(runner, report_path)
    lease_calls = 0
    client_calls = 0
    monkeypatch.setattr(runner, "_parse_args", lambda _argv=None: options)
    monkeypatch.setattr(runner, "_perform_readiness", lambda _options: prepared)
    monkeypatch.setattr(
        runner,
        "_revalidate_prepared_run",
        lambda _prepared: (_ for _ in ()).throw(runner._ConfigurationInvalid()),
    )

    def lease_forbidden(_path: object) -> None:
        nonlocal lease_calls
        lease_calls += 1

    def client_forbidden(_settings: object) -> None:
        nonlocal client_calls
        client_calls += 1

    monkeypatch.setattr(runner._RunLease, "acquire", lease_forbidden)
    monkeypatch.setattr(runner, "create_deepseek_classifier_client", client_forbidden)

    assert runner.main([]) == 2
    captured = capsys.readouterr()

    assert lease_calls == 0
    assert client_calls == 0
    assert "READINESS_INVALID" in captured.err
    assert not report_path.exists()
    assert not report_path.with_name(f"{report_path.name}.run.lock").exists()


def test_aggregate_actual_deadline_bounds_slow_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()

    async def slow_actual(_prepared: object, _evidence: object) -> None:
        await asyncio.sleep(0.05)

    monkeypatch.setattr(runner, "_execute_actual", slow_actual)
    monkeypatch.setattr(runner, "_ACTUAL_RUN_DEADLINE_SECONDS", 0.01)
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        asyncio.run(runner._execute_actual_with_deadline(object(), object()))
    elapsed = time.monotonic() - started

    assert elapsed < 0.04


def test_corrective_identity_binds_its_own_actual_deadline_and_restores_a074() -> None:
    runner = _runner()
    offline_directory = (
        _REPOSITORY_ROOT / ".superpowers" / "sdd" / "synthetic-corrective-deadline-test"
    )
    identity = runner.EvidenceIdentity(
        report_path=(
            _REPOSITORY_ROOT
            / "docs"
            / "test-reports"
            / "SYNTHETIC-CORRECTIVE-DEADLINE-TEST.md"
        ),
        offline_result_path=offline_directory / "result.json",
        offline_lock_path=offline_directory / "result.json.run.lock",
        offline_stdout_path=offline_directory / "stdout.log",
        offline_stderr_path=offline_directory / "stderr.log",
        offline_gate="A-999-OFFLINE",
        offline_lease_text="A-999-OFFLINE-GATE one-shot lease\n",
        actual_lease_text="A-999-DEEPSEEK-CLASSIFIER one-shot lease\n",
        actual_run_deadline_seconds=100,
    )

    assert runner.A074_EVIDENCE_IDENTITY.actual_run_deadline_seconds == 32
    with runner._bind_corrective_evidence_identity(identity):
        assert runner._ACTUAL_RUN_DEADLINE_SECONDS == 100
        assert runner._current_evidence_identity() == identity
    assert runner._ACTUAL_RUN_DEADLINE_SECONDS == 32
    assert runner._current_evidence_identity() == runner.A074_EVIDENCE_IDENTITY


def test_pre_actual_check_runs_after_revalidation_and_before_lease(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    offline_directory = (
        _REPOSITORY_ROOT / ".superpowers" / "sdd" / "synthetic-pre-actual-check-test"
    )
    report_path = (
        _REPOSITORY_ROOT
        / "docs"
        / "test-reports"
        / "SYNTHETIC-PRE-ACTUAL-CHECK-TEST.md"
    )
    order: list[str] = []

    def reject_pre_actual(source_sha: str) -> bool:
        order.append(f"precheck:{source_sha}")
        return False

    identity = runner.EvidenceIdentity(
        report_path=report_path,
        offline_result_path=offline_directory / "result.json",
        offline_lock_path=offline_directory / "result.json.run.lock",
        offline_stdout_path=offline_directory / "stdout.log",
        offline_stderr_path=offline_directory / "stderr.log",
        offline_gate="A-998-OFFLINE",
        offline_lease_text="A-998-OFFLINE-GATE one-shot lease\n",
        actual_lease_text="A-998-DEEPSEEK-CLASSIFIER one-shot lease\n",
        actual_run_deadline_seconds=100,
        pre_actual_check=reject_pre_actual,
    )
    options = runner._RunnerOptions(
        fixture_path=runner._FIXTURE_PATH,
        report_path=report_path,
        readiness_only=False,
    )
    prepared = _prepared(runner, report_path)
    monkeypatch.setattr(runner, "_parse_args", lambda _argv=None: options)
    monkeypatch.setattr(runner, "_perform_readiness", lambda _options: prepared)
    monkeypatch.setattr(runner, "_new_evidence", lambda _prepared: object())
    monkeypatch.setattr(
        runner,
        "_revalidate_prepared_run",
        lambda _prepared: order.append("revalidated"),
    )
    monkeypatch.setattr(
        runner._RunLease,
        "acquire",
        lambda _path: pytest.fail("lease must remain unconsumed"),
    )

    assert runner.main([], evidence_identity=identity) == 2
    assert order == ["revalidated", f"precheck:{prepared.source_sha}"]
    assert (
        capsys.readouterr().err.strip()
        == "DEEPSEEK_CLASSIFIER_ACTUAL_READINESS_INVALID"
    )


def test_pre_actual_check_is_followed_by_final_revalidation_before_lease(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    offline_directory = (
        _REPOSITORY_ROOT / ".superpowers" / "sdd" / "synthetic-final-revalidation-test"
    )
    report_path = (
        _REPOSITORY_ROOT
        / "docs"
        / "test-reports"
        / "SYNTHETIC-FINAL-REVALIDATION-TEST.md"
    )
    order: list[str] = []

    def accept_pre_actual(source_sha: str) -> bool:
        order.append(f"precheck:{source_sha}")
        return True

    identity = runner.EvidenceIdentity(
        report_path=report_path,
        offline_result_path=offline_directory / "result.json",
        offline_lock_path=offline_directory / "result.json.run.lock",
        offline_stdout_path=offline_directory / "stdout.log",
        offline_stderr_path=offline_directory / "stderr.log",
        offline_gate="A-997-OFFLINE",
        offline_lease_text="A-997-OFFLINE-GATE one-shot lease\n",
        actual_lease_text="A-997-DEEPSEEK-CLASSIFIER one-shot lease\n",
        actual_run_deadline_seconds=100,
        pre_actual_check=accept_pre_actual,
    )
    options = runner._RunnerOptions(
        fixture_path=runner._FIXTURE_PATH,
        report_path=report_path,
        readiness_only=False,
    )
    prepared = _prepared(runner, report_path)
    revalidation_count = 0

    def revalidate_then_drift(_prepared: object) -> None:
        nonlocal revalidation_count
        revalidation_count += 1
        order.append("revalidated")
        if revalidation_count == 2:
            raise RuntimeError

    monkeypatch.setattr(runner, "_parse_args", lambda _argv=None: options)
    monkeypatch.setattr(runner, "_perform_readiness", lambda _options: prepared)
    monkeypatch.setattr(runner, "_new_evidence", lambda _prepared: object())
    monkeypatch.setattr(runner, "_revalidate_prepared_run", revalidate_then_drift)
    monkeypatch.setattr(
        runner._RunLease,
        "acquire",
        lambda _path: pytest.fail("lease must remain unconsumed"),
    )

    assert runner.main([], evidence_identity=identity) == 2
    assert order == [
        "revalidated",
        f"precheck:{prepared.source_sha}",
        "revalidated",
    ]
    assert (
        capsys.readouterr().err.strip()
        == "DEEPSEEK_CLASSIFIER_ACTUAL_READINESS_INVALID"
    )


def test_readiness_rejects_nine_worst_case_costs_over_cap_before_lease_or_network(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    options = runner._RunnerOptions(
        fixture_path=runner._FIXTURE_PATH,
        report_path=runner._REPORT_PATH,
        readiness_only=False,
    )
    lease_calls = 0
    client_calls = 0
    monkeypatch.setattr(runner, "_parse_args", lambda _argv=None: options)
    monkeypatch.setattr(runner, "_source_sha", lambda *_args: "a" * 40)
    monkeypatch.setattr(runner, "_require_clean_worktree", lambda *_args: None)
    monkeypatch.setattr(runner, "_require_offline_gate", lambda _sha: "e" * 64)
    monkeypatch.setattr(
        runner,
        "load_deepseek_classifier_settings",
        lambda: DeepSeekClassifierSettings(api_key="synthetic-secret-marker"),
    )
    monkeypatch.setattr(
        runner,
        "_worst_case_classifier_cost",
        lambda: Decimal("0.03"),
    )

    def lease_forbidden(_path: object) -> None:
        nonlocal lease_calls
        lease_calls += 1

    def client_forbidden(_settings: object) -> None:
        nonlocal client_calls
        client_calls += 1

    monkeypatch.setattr(runner._RunLease, "acquire", lease_forbidden)
    monkeypatch.setattr(
        runner,
        "create_deepseek_classifier_client",
        client_forbidden,
    )

    assert runner.main([]) == 2
    captured = capsys.readouterr()
    assert lease_calls == 0
    assert client_calls == 0
    assert "READINESS_INVALID" in captured.err
    assert "synthetic-secret-marker" not in captured.out + captured.err


def test_selected_twenty_use_real_deterministic_boundary_and_exact_nine_oracles() -> (
    None
):
    runner = _runner()
    report_path = runner._REPORT_PATH
    prepared = _prepared(runner, report_path)
    ledger = runner._build_ledger(prepared.settings)
    question_to_case = {
        case.question: case
        for case in prepared.selection.selected
        if case.expected_provider_use == 1
    }

    class PassingClassifier:
        async def classify(
            self, question: SafeQuestion, catalog: object
        ) -> ClassifierDecision:
            case = question_to_case[question.text]
            async with ledger.reserve_classifier() as reservation:
                reservation.record_usage(TokenUsage(100, 50, 10))
            return _literal_oracle(case.fixture_id)

    evidence = runner._new_evidence(prepared)
    result = asyncio.run(
        runner._evaluate_selected(
            prepared.selection.selected,
            classifier=PassingClassifier(),
            catalog=prepared.catalog,
            ledger=ledger,
            evidence=evidence,
        )
    )

    assert result.selected_count == 20
    assert result.skip_count == 0
    assert result.deterministic_provider_free_count == 11
    assert result.provider_case_count == 9
    assert result.outbound_attempt_count == 9
    assert result.server_decision_accepted_count == 9
    assert result.oracle_match_count == 9


@pytest.mark.parametrize("failure_kind", ("none", "http", "wire"))
def test_real_adapter_mock_transport_derives_nine_aggregate_observations_without_retry(
    failure_kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    prepared = _prepared(runner, tmp_path / "actual.md")
    provider_cases = tuple(
        case for case in prepared.selection.selected if case.expected_provider_use == 1
    )
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        request_text = request.content.decode("utf-8")
        matched = tuple(
            case for case in provider_cases if case.question in request_text
        )
        assert len(matched) == 1
        decision = _literal_oracle(matched[0].fixture_id)
        if calls == 1 and failure_kind == "http":
            return httpx.Response(
                429, json={"ignored": "synthetic-provider-body-marker"}
            )
        content = _wire_for_decision(decision)
        if calls == 1 and failure_kind == "wire":
            content = json.dumps(
                {
                    **json.loads(content),
                    "synthetic-invalid-value-marker": "ignored",
                },
                separators=(",", ":"),
            )
        response_envelope = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": content},
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 10,
                "total_tokens": 110,
                "prompt_cache_hit_tokens": 50,
                "prompt_cache_miss_tokens": 50,
            },
        }
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            stream=httpx.ByteStream(
                json.dumps(
                    response_envelope,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
            ),
        )

    def client_factory(settings: DeepSeekClassifierSettings) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=settings.base_url,
            headers={"Authorization": "Bearer synthetic-secret-marker"},
            transport=httpx.MockTransport(handler),
            timeout=3,
        )

    monkeypatch.setattr(
        runner,
        "create_deepseek_classifier_client",
        client_factory,
    )
    evidence = runner._new_evidence(prepared)

    asyncio.run(runner._execute_actual(prepared, evidence))
    report = runner._build_report(evidence)
    markdown = runner._report_to_markdown(report)

    assert calls == 9
    assert evidence.outbound_attempt_count == 9
    assert evidence.provider_response_count == 9
    assert sum(evidence.response_stage_counts.values()) == 9
    assert evidence.retry_count == 0
    if failure_kind == "none":
        assert evidence.http_2xx_count == 9
        assert evidence.strict_parse_count == 9
        assert evidence.server_decision_accepted_count == 9
        assert evidence.oracle_match_count == 9
        assert evidence.usage_accepted_count == 9
        assert report["acceptance"] == "PASS"
    else:
        assert report["acceptance"] == "FAIL"
        assert evidence.strict_parse_count == 8
        assert evidence.server_decision_accepted_count == 8
        assert evidence.oracle_match_count == 8
        assert calls == 9
    for marker in _FORBIDDEN_VALUE_MARKERS:
        assert marker not in markdown.casefold()


@pytest.mark.parametrize(
    ("field", "bad_value"),
    (
        ("selected_count", 19),
        ("skip_count", 1),
        ("deterministic_provider_free_count", 10),
        ("provider_case_count", 8),
        ("policy_privacy_probe_count", 3),
        ("policy_privacy_outbound_count", 1),
        ("outbound_attempt_count", 8),
        ("provider_response_count", 8),
        ("http_2xx_count", 8),
        ("http_rejected_count", 1),
        ("transport_no_response_count", 1),
        ("strict_parse_count", 8),
        ("server_decision_accepted_count", 8),
        ("oracle_match_count", 8),
        ("usage_accepted_count", 8),
        ("usage_rejected_count", 1),
        ("runtime_failure_count", 1),
        ("retry_count", 1),
        ("rerun_count", 1),
        ("retained_question_count", 1),
        ("retained_masked_question_count", 1),
        ("retained_request_body_count", 1),
        ("retained_response_body_count", 1),
        ("retained_invalid_value_count", 1),
        ("retained_secret_count", 1),
    ),
)
def test_pass_requires_every_exact_aggregate(field: str, bad_value: object) -> None:
    runner = _runner()
    evidence = _passing_evidence(runner, runner._REPORT_PATH)

    assert runner._build_report(evidence)["acceptance"] == "PASS"
    mutated = replace(evidence, **{field: bad_value})

    assert runner._build_report(mutated)["acceptance"] == "FAIL"


def test_pass_uses_conservative_all_miss_vat_cost_and_cap() -> None:
    runner = _runner()
    evidence = _passing_evidence(runner, runner._REPORT_PATH)
    expected = estimate_deepseek_cost_usd(evidence.usage)

    assert evidence.usage.cached_input_tokens > 0
    assert evidence.conservative_cost_usd == expected
    assert expected <= Decimal("0.20")
    assert runner._build_report(evidence)["acceptance"] == "PASS"

    over_cap = replace(evidence, conservative_cost_usd=Decimal("0.200000001"))
    assert runner._build_report(over_cap)["acceptance"] == "FAIL"


def test_report_console_and_lease_are_aggregate_only() -> None:
    runner = _runner()
    evidence = _passing_evidence(runner, runner._REPORT_PATH)
    report = runner._build_report(evidence)
    markdown = runner._report_to_markdown(report)
    console = runner._safe_console_report(report)
    fixture_document = json.loads(runner._FIXTURE_PATH.read_text(encoding="utf-8"))

    combined = markdown + console
    for case in fixture_document["cases"]:
        assert case["id"] not in combined
        assert case["question"] not in combined
    for marker in _FORBIDDEN_VALUE_MARKERS:
        assert marker not in combined.casefold()
    assert "| `acceptance` | `PASS` |" in markdown
    assert json.loads(console)["acceptance"] == "PASS"
    assert "cases" not in report


def test_post_lease_failure_writes_one_immutable_aggregate_fail_and_keeps_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    report_path = tmp_path / "actual.md"
    options = runner._RunnerOptions(
        fixture_path=runner._FIXTURE_PATH,
        report_path=report_path,
        readiness_only=False,
    )
    prepared = _prepared(runner, report_path)
    execution_calls = 0

    monkeypatch.setattr(runner, "_parse_args", lambda _argv=None: options)
    monkeypatch.setattr(runner, "_perform_readiness", lambda _options: prepared)
    monkeypatch.setattr(runner, "_revalidate_prepared_run", lambda _prepared: None)

    async def fail_after_lease(_prepared: object, _evidence: object) -> None:
        nonlocal execution_calls
        execution_calls += 1
        lease_path = report_path.with_name(f"{report_path.name}.run.lock")
        assert lease_path.is_file()
        raise RuntimeError(
            "synthetic-provider-body-marker synthetic-invalid-value-marker "
            "synthetic-secret-marker postgresql://synthetic-dsn-marker"
        )

    monkeypatch.setattr(runner, "_execute_actual", fail_after_lease)

    assert runner.main([]) == 3
    first_console = capsys.readouterr()
    report_bytes = report_path.read_bytes()
    lease_path = report_path.with_name(f"{report_path.name}.run.lock")

    assert execution_calls == 1
    assert lease_path.is_file()
    assert "| `acceptance` | `FAIL` |" in report_bytes.decode("utf-8")
    for marker in _FORBIDDEN_VALUE_MARKERS:
        assert (
            marker
            not in (
                first_console.out + first_console.err + report_bytes.decode("utf-8")
            ).casefold()
        )

    assert runner.main([]) == 2
    second_console = capsys.readouterr()
    assert execution_calls == 1
    assert report_path.read_bytes() == report_bytes
    assert lease_path.is_file()
    assert "RUN_ALREADY_RECORDED" in second_console.err


def test_runtime_exception_forces_fail_even_if_all_observed_aggregates_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    report_path = tmp_path / "actual.md"
    options = runner._RunnerOptions(
        fixture_path=runner._FIXTURE_PATH,
        report_path=report_path,
        readiness_only=False,
    )
    prepared = _prepared(runner, report_path)
    passing_evidence = _passing_evidence(runner, report_path)
    monkeypatch.setattr(runner, "_parse_args", lambda _argv=None: options)
    monkeypatch.setattr(runner, "_perform_readiness", lambda _options: prepared)
    monkeypatch.setattr(runner, "_revalidate_prepared_run", lambda _prepared: None)
    monkeypatch.setattr(runner, "_new_evidence", lambda _prepared: passing_evidence)

    async def fail_after_complete_observation(
        _prepared: object,
        _evidence: object,
    ) -> None:
        raise RuntimeError("synthetic-secret-marker")

    monkeypatch.setattr(runner, "_execute_actual", fail_after_complete_observation)

    assert runner.main([]) == 3
    captured = capsys.readouterr()
    report = report_path.read_text(encoding="utf-8")

    assert "| `runtime_failure_count` | `1` |" in report
    assert "| `acceptance` | `FAIL` |" in report
    assert "synthetic-secret-marker" not in captured.out + captured.err + report


def test_network_free_evidence_preparation_failure_does_not_consume_actual(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    report_path = tmp_path / "actual.md"
    options = runner._RunnerOptions(
        fixture_path=runner._FIXTURE_PATH,
        report_path=report_path,
        readiness_only=False,
    )
    prepared = _prepared(runner, report_path)
    lease_calls = 0
    client_calls = 0
    monkeypatch.setattr(runner, "_parse_args", lambda _argv=None: options)
    monkeypatch.setattr(runner, "_perform_readiness", lambda _options: prepared)
    monkeypatch.setattr(
        runner,
        "_new_evidence",
        lambda _prepared: (_ for _ in ()).throw(
            runner._ConfigurationInvalid("synthetic-secret-marker")
        ),
    )

    def lease_forbidden(_path: object) -> None:
        nonlocal lease_calls
        lease_calls += 1

    def client_forbidden(_settings: object) -> None:
        nonlocal client_calls
        client_calls += 1

    monkeypatch.setattr(runner._RunLease, "acquire", lease_forbidden)
    monkeypatch.setattr(
        runner,
        "create_deepseek_classifier_client",
        client_forbidden,
    )

    assert runner.main([]) == 2
    captured = capsys.readouterr()

    assert lease_calls == 0
    assert client_calls == 0
    assert not report_path.exists()
    assert not report_path.with_name(f"{report_path.name}.run.lock").exists()
    assert "READINESS_INVALID" in captured.err
    assert "synthetic-secret-marker" not in captured.out + captured.err


def test_report_write_failure_retains_permanent_lease(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    report_path = tmp_path / "actual.md"
    options = runner._RunnerOptions(
        fixture_path=runner._FIXTURE_PATH,
        report_path=report_path,
        readiness_only=False,
    )
    prepared = _prepared(runner, report_path)
    monkeypatch.setattr(runner, "_parse_args", lambda _argv=None: options)
    monkeypatch.setattr(runner, "_perform_readiness", lambda _options: prepared)
    monkeypatch.setattr(runner, "_revalidate_prepared_run", lambda _prepared: None)

    async def fail(_prepared: object, _evidence: object) -> None:
        raise RuntimeError("synthetic-secret-marker")

    monkeypatch.setattr(runner, "_execute_actual", fail)
    monkeypatch.setattr(
        runner,
        "_write_report_once",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(runner._EvidenceWriteFailed()),
    )

    assert runner.main([]) == 3
    captured = capsys.readouterr()

    assert not report_path.exists()
    assert report_path.with_name(f"{report_path.name}.run.lock").is_file()
    assert "EVIDENCE_WRITE_FAILED" in captured.err
    assert "synthetic-secret-marker" not in captured.out + captured.err


def _literal_oracle(fixture_id: str) -> ClassifierDecision:
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
    raise AssertionError("unexpected controlled oracle")


def _wire_for_decision(decision: ClassifierDecision) -> str:
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
    )
