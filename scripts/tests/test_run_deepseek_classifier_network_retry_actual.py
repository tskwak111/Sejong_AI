from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_ROOT = _REPOSITORY_ROOT / "scripts"
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))


def _load_modules() -> tuple[Any, Any, Any, Any, Any, Any]:
    for module_name in (
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
    return core, a075, a076, a077, a078, a079


def test_a079_identity_is_disjoint_and_owns_longer_aggregate_deadline() -> None:
    core, a075, a076, a077, a078, a079 = _load_modules()

    profile = a079.A079_EVIDENCE_IDENTITY
    predecessors = (
        core.A074_EVIDENCE_IDENTITY,
        a075.A075_EVIDENCE_IDENTITY,
        a076.A076_EVIDENCE_IDENTITY,
        a077.A077_EVIDENCE_IDENTITY,
        a078.A078_EVIDENCE_IDENTITY,
    )

    assert profile.report_path.name == "CHAT-HYBRID-RAG-001-DEEPSEEK-A079-ACTUAL.md"
    assert profile.offline_gate == "A-079-OFFLINE"
    assert profile.actual_run_deadline_seconds == 100
    assert tuple(
        predecessor.actual_run_deadline_seconds for predecessor in predecessors
    ) == (32, 32, 32, 100, 100)
    for predecessor in predecessors:
        assert profile.report_path != predecessor.report_path
        assert profile.offline_result_path != predecessor.offline_result_path
        assert profile.offline_lock_path != predecessor.offline_lock_path
        assert profile.offline_stdout_path != predecessor.offline_stdout_path
        assert profile.offline_stderr_path != predecessor.offline_stderr_path
    assert profile.pre_actual_check is a079.require_probe_pass_for_current_source


def test_a079_readiness_binds_deadline_and_restores_a074(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    core, _, _, _, _, a079 = _load_modules()
    observed_deadlines: list[float] = []

    def fake_readiness(_options: Any) -> object:
        observed_deadlines.append(core._ACTUAL_RUN_DEADLINE_SECONDS)
        return object()

    monkeypatch.setattr(core, "_perform_readiness", fake_readiness)

    result = a079.main(
        [
            "--fixture",
            str(core._FIXTURE_PATH),
            "--report",
            str(a079.A079_EVIDENCE_IDENTITY.report_path),
            "--readiness-only",
        ]
    )

    assert result == 0
    assert capsys.readouterr().out.strip() == "DEEPSEEK_CLASSIFIER_ACTUAL_READY"
    assert observed_deadlines == [100]
    assert core._ACTUAL_RUN_DEADLINE_SECONDS == 32
    assert core._current_evidence_identity() == core.A074_EVIDENCE_IDENTITY


def test_a079_actual_is_blocked_until_same_source_probe_passes(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    core, _, _, _, _, a079 = _load_modules()
    core_calls = 0

    def core_forbidden(*_args: Any, **_kwargs: Any) -> int:
        nonlocal core_calls
        core_calls += 1
        return 0

    monkeypatch.setattr(core, "main", core_forbidden)
    monkeypatch.setattr(
        a079,
        "require_probe_pass_for_current_source",
        lambda _source_sha: False,
    )
    monkeypatch.setattr(a079, "_source_sha", lambda: "a" * 40)

    assert a079.main([]) == 2
    assert core_calls == 0
    assert capsys.readouterr().err.strip() == "DEEPSEEK_A079_ACTUAL_PROBE_NOT_PASSED"
