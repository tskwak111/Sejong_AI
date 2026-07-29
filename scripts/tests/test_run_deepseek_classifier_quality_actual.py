from __future__ import annotations

import importlib
import sys
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_ROOT = _REPOSITORY_ROOT / "scripts"
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))


def _load_modules() -> tuple[Any, Any, Any, Any, Any, Any, Any]:
    for module_name in (
        "run_deepseek_classifier_quality_actual",
        "run_deepseek_classifier_network_retry_actual",
        "run_deepseek_classifier_prelease_hardened_actual",
        "run_deepseek_classifier_split_timeout_actual",
        "run_deepseek_classifier_network_recovery_actual",
        "run_deepseek_classifier_corrective_actual",
        "run_deepseek_classifier_actual",
    ):
        sys.modules.pop(module_name, None)
    core = importlib.import_module("run_deepseek_classifier_actual")
    a075 = importlib.import_module("run_deepseek_classifier_corrective_actual")
    a076 = importlib.import_module("run_deepseek_classifier_network_recovery_actual")
    a077 = importlib.import_module("run_deepseek_classifier_split_timeout_actual")
    a078 = importlib.import_module("run_deepseek_classifier_prelease_hardened_actual")
    a079 = importlib.import_module("run_deepseek_classifier_network_retry_actual")
    a080 = importlib.import_module("run_deepseek_classifier_quality_actual")
    return core, a075, a076, a077, a078, a079, a080


def test_a080_identity_is_disjoint_and_quality_only() -> None:
    core, a075, a076, a077, a078, a079, a080 = _load_modules()

    identity = a080.A080_EVIDENCE_IDENTITY
    predecessors = (
        core.A074_EVIDENCE_IDENTITY,
        a075.A075_EVIDENCE_IDENTITY,
        a076.A076_EVIDENCE_IDENTITY,
        a077.A077_EVIDENCE_IDENTITY,
        a078.A078_EVIDENCE_IDENTITY,
        a079.A079_EVIDENCE_IDENTITY,
    )

    assert identity.report_path.name == "CHAT-HYBRID-RAG-001-DEEPSEEK-A080-ACTUAL.md"
    assert identity.offline_gate == "A-080-OFFLINE"
    assert identity.offline_lease_text == "A-080-OFFLINE-GATE one-shot lease\n"
    assert identity.actual_lease_text == "A-080-DEEPSEEK-CLASSIFIER one-shot lease\n"
    assert identity.actual_run_deadline_seconds == 100
    assert identity.pre_actual_check is None
    for predecessor in predecessors:
        assert identity.report_path != predecessor.report_path
        assert identity.offline_result_path != predecessor.offline_result_path
        assert identity.offline_lock_path != predecessor.offline_lock_path
        assert identity.offline_stdout_path != predecessor.offline_stdout_path
        assert identity.offline_stderr_path != predecessor.offline_stderr_path


def test_a080_readiness_binds_quality_identity_without_a_probe(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    core, _, _, _, _, _, a080 = _load_modules()
    observed: list[tuple[float, object]] = []

    def fake_readiness(_options: Any) -> object:
        observed.append((core._ACTUAL_RUN_DEADLINE_SECONDS, core._PRE_ACTUAL_CHECK))
        return object()

    monkeypatch.setattr(core, "_perform_readiness", fake_readiness)

    result = a080.main(
        [
            "--fixture",
            str(core._FIXTURE_PATH),
            "--report",
            str(a080.A080_EVIDENCE_IDENTITY.report_path),
            "--readiness-only",
        ]
    )

    assert result == 0
    assert capsys.readouterr().out.strip() == "DEEPSEEK_CLASSIFIER_ACTUAL_READY"
    assert observed == [(100, None)]
    assert core._current_evidence_identity() == core.A074_EVIDENCE_IDENTITY


@pytest.mark.parametrize("offline_state", ("absent", "wrong"))
def test_a080_readiness_rejects_non_passing_offline_evidence_before_settings(
    tmp_path: Path,
    monkeypatch: Any,
    offline_state: str,
) -> None:
    core, _, _, _, _, _, a080 = _load_modules()
    identity = _temporary_identity(core, a080, tmp_path)
    monkeypatch.setattr(core, "_REPOSITORY_ROOT", identity.report_path.parents[2])
    _prepare_readiness_without_settings(monkeypatch, core)
    settings_read = False

    def settings_forbidden() -> object:
        nonlocal settings_read
        settings_read = True
        raise AssertionError("settings must not be read before offline evidence passes")

    monkeypatch.setattr(core, "load_deepseek_classifier_settings", settings_forbidden)
    if offline_state == "wrong":
        _write_offline_evidence(identity, gate="A-079-OFFLINE")

    with core._bind_corrective_evidence_identity(identity):
        options = core._RunnerOptions(core._FIXTURE_PATH, identity.report_path, True)
        with pytest.raises(core._ConfigurationInvalid):
            core._perform_readiness(options)

    assert settings_read is False


def test_a080_readiness_rejects_an_existing_actual_report(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    core, _, _, _, _, _, a080 = _load_modules()
    identity = _temporary_identity(core, a080, tmp_path)
    monkeypatch.setattr(core, "_REPOSITORY_ROOT", identity.report_path.parents[2])
    identity.report_path.parent.mkdir(parents=True)
    identity.report_path.write_text("immutable report", encoding="ascii")
    _prepare_readiness_without_settings(monkeypatch, core, preserve_actual_absence=True)

    with core._bind_corrective_evidence_identity(identity):
        options = core._RunnerOptions(core._FIXTURE_PATH, identity.report_path, True)
        with pytest.raises(core._RunAlreadyExists):
            core._perform_readiness(options)


def _temporary_identity(core: Any, a080: Any, tmp_path: Path) -> Any:
    repository = tmp_path / "repository"
    offline = repository / ".superpowers" / "a080"
    return replace(
        a080.A080_EVIDENCE_IDENTITY,
        report_path=repository / "docs" / "test-reports" / "a080.md",
        offline_result_path=offline / "result.json",
        offline_lock_path=offline / "result.json.run.lock",
        offline_stdout_path=offline / "stdout.log",
        offline_stderr_path=offline / "stderr.log",
    )


def _prepare_readiness_without_settings(
    monkeypatch: Any,
    core: Any,
    *,
    preserve_actual_absence: bool = False,
) -> None:
    if not preserve_actual_absence:
        monkeypatch.setattr(core, "_require_actual_absent", lambda _report: None)
    monkeypatch.setattr(core, "_load_fixtures", lambda _fixture: ())
    monkeypatch.setattr(core, "_select_actual_cases", lambda _fixtures: object())
    monkeypatch.setattr(
        core,
        "_evaluate_policy_privacy_probes",
        lambda _fixtures: type("Probes", (), {"probe_count": 0, "outbound_count": 0})(),
    )
    monkeypatch.setattr(core, "_EXPECTED_POLICY_PRIVACY_PROBE_COUNT", 0)
    monkeypatch.setattr(core, "_source_sha", lambda: "a" * 40)
    monkeypatch.setattr(core, "_require_clean_worktree", lambda: None)


def _write_offline_evidence(identity: Any, *, gate: str) -> None:
    identity.offline_result_path.parent.mkdir(parents=True)
    identity.offline_lock_path.write_bytes(identity.offline_lease_text.encode("ascii"))
    identity.offline_stdout_path.write_bytes(b"")
    identity.offline_stderr_path.write_bytes(b"")
    result = (
        '{"schema_version":1,"gate":"%s","source_sha":"%s",'
        '"outcome":"PASS","exit_code":0,"timed_out":false,'
        '"invocation_count":1,"rerun_count":0,"stdout_sha256":"%s",'
        '"stdout_bytes":0,"stderr_sha256":"%s","stderr_bytes":0}\n'
        % (gate, "a" * 40, sha256(b"").hexdigest(), sha256(b"").hexdigest())
    )
    identity.offline_result_path.write_text(result, encoding="ascii")
