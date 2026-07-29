from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_ROOT = _REPOSITORY_ROOT / "scripts"
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))


def _load_modules() -> tuple[Any, Any, Any]:
    for module_name in (
        "run_deepseek_classifier_network_recovery_actual",
        "run_deepseek_classifier_corrective_actual",
        "run_deepseek_classifier_actual",
    ):
        sys.modules.pop(module_name, None)
    core = importlib.import_module("run_deepseek_classifier_actual")
    a075 = importlib.import_module("run_deepseek_classifier_corrective_actual")
    a076 = importlib.import_module("run_deepseek_classifier_network_recovery_actual")
    return core, a075, a076


def test_a076_identity_is_disjoint_from_a074_and_a075() -> None:
    core, a075, a076 = _load_modules()

    profile = a076.A076_EVIDENCE_IDENTITY
    predecessors = (core.A074_EVIDENCE_IDENTITY, a075.A075_EVIDENCE_IDENTITY)

    assert profile.report_path.name == "CHAT-HYBRID-RAG-001-DEEPSEEK-A076-ACTUAL.md"
    assert profile.offline_gate == "A-076-OFFLINE"
    assert profile.offline_lease_text == "A-076-OFFLINE-GATE one-shot lease\n"
    assert profile.actual_lease_text == "A-076-DEEPSEEK-CLASSIFIER one-shot lease\n"
    for predecessor in predecessors:
        assert profile.report_path != predecessor.report_path
        assert profile.offline_result_path != predecessor.offline_result_path
        assert profile.offline_lock_path != predecessor.offline_lock_path
        assert profile.offline_stdout_path != predecessor.offline_stdout_path
        assert profile.offline_stderr_path != predecessor.offline_stderr_path


def test_a076_readiness_uses_its_report_and_restores_a074(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    core, _, a076 = _load_modules()
    original = core._current_evidence_identity()
    captured_report_paths: list[Path] = []

    def fake_readiness(options: Any) -> object:
        captured_report_paths.append(options.report_path)
        return object()

    monkeypatch.setattr(core, "_perform_readiness", fake_readiness)

    result = a076.main(
        [
            "--fixture",
            str(core._FIXTURE_PATH),
            "--report",
            str(a076.A076_EVIDENCE_IDENTITY.report_path),
            "--readiness-only",
        ]
    )

    assert result == 0
    assert capsys.readouterr().out.strip() == "DEEPSEEK_CLASSIFIER_ACTUAL_READY"
    assert captured_report_paths == [a076.A076_EVIDENCE_IDENTITY.report_path.resolve()]
    assert core._current_evidence_identity() == original == core.A074_EVIDENCE_IDENTITY


def test_a076_runner_rejects_a075_report(capsys: Any) -> None:
    _, a075, a076 = _load_modules()

    result = a076.main(
        [
            "--fixture",
            str(
                _REPOSITORY_ROOT / "apps/api/tests/chat/fixtures/hybrid-rag-uat.v1.json"
            ),
            "--report",
            str(a075.A075_EVIDENCE_IDENTITY.report_path),
            "--readiness-only",
        ]
    )

    assert result == 2
    assert (
        capsys.readouterr().err.strip()
        == "DEEPSEEK_CLASSIFIER_ACTUAL_ARGUMENTS_INVALID"
    )


def test_a076_fails_closed_if_core_identity_drifted(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    core, _, a076 = _load_modules()
    monkeypatch.setattr(core, "_REPORT_PATH", Path("unexpected-report.md"))

    result = a076.main(
        [
            "--fixture",
            str(core._FIXTURE_PATH),
            "--report",
            str(a076.A076_EVIDENCE_IDENTITY.report_path),
            "--readiness-only",
        ]
    )

    assert result == 2
    assert (
        capsys.readouterr().err.strip()
        == "DEEPSEEK_CLASSIFIER_EVIDENCE_IDENTITY_INVALID"
    )
