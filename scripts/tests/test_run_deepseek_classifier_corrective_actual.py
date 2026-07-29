from __future__ import annotations

import hashlib
import importlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_ROOT = _REPOSITORY_ROOT / "scripts"
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))


def _load_modules() -> tuple[Any, Any]:
    sys.modules.pop("run_deepseek_classifier_corrective_actual", None)
    sys.modules.pop("run_deepseek_classifier_actual", None)
    core = importlib.import_module("run_deepseek_classifier_actual")
    corrective = importlib.import_module("run_deepseek_classifier_corrective_actual")
    return core, corrective


def test_corrective_identity_is_disjoint_from_a074() -> None:
    core, corrective = _load_modules()

    profile = corrective.A075_EVIDENCE_IDENTITY
    a074 = core.A074_EVIDENCE_IDENTITY

    assert profile.report_path.name == "CHAT-HYBRID-RAG-001-DEEPSEEK-A075-ACTUAL.md"
    assert profile.report_path != a074.report_path
    assert profile.offline_result_path != a074.offline_result_path
    assert profile.offline_lock_path != a074.offline_lock_path
    assert profile.offline_stdout_path != a074.offline_stdout_path
    assert profile.offline_stderr_path != a074.offline_stderr_path
    assert profile.offline_gate == "A-075-OFFLINE"
    assert profile.offline_lease_text == "A-075-OFFLINE-GATE one-shot lease\n"
    assert profile.actual_lease_text == "A-075-DEEPSEEK-CLASSIFIER one-shot lease\n"


def test_corrective_readiness_uses_a075_report_and_restores_a074(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    core, corrective = _load_modules()
    original = core._current_evidence_identity()
    captured_report_paths: list[Path] = []

    def fake_readiness(options: Any) -> object:
        captured_report_paths.append(options.report_path)
        return object()

    monkeypatch.setattr(core, "_perform_readiness", fake_readiness)

    result = corrective.main(
        [
            "--fixture",
            str(core._FIXTURE_PATH),
            "--report",
            str(corrective.A075_EVIDENCE_IDENTITY.report_path),
            "--readiness-only",
        ]
    )

    assert result == 0
    assert capsys.readouterr().out.strip() == "DEEPSEEK_CLASSIFIER_ACTUAL_READY"
    assert captured_report_paths == [
        corrective.A075_EVIDENCE_IDENTITY.report_path.resolve()
    ]
    assert core._current_evidence_identity() == original == core.A074_EVIDENCE_IDENTITY


def test_corrective_runner_rejects_a074_report(
    capsys: pytest.CaptureFixture[str],
) -> None:
    core, corrective = _load_modules()

    result = corrective.main(
        [
            "--fixture",
            str(core._FIXTURE_PATH),
            "--report",
            str(core.A074_EVIDENCE_IDENTITY.report_path),
            "--readiness-only",
        ]
    )

    assert result == 2
    assert (
        capsys.readouterr().err.strip()
        == "DEEPSEEK_CLASSIFIER_ACTUAL_ARGUMENTS_INVALID"
    )


def test_corrective_runner_fails_closed_if_core_identity_drifted(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    core, corrective = _load_modules()
    monkeypatch.setattr(core, "_REPORT_PATH", Path("unexpected-report.md"))

    result = corrective.main(
        [
            "--fixture",
            str(core._FIXTURE_PATH),
            "--report",
            str(corrective.A075_EVIDENCE_IDENTITY.report_path),
            "--readiness-only",
        ]
    )

    assert result == 2
    assert (
        capsys.readouterr().err.strip()
        == "DEEPSEEK_CLASSIFIER_EVIDENCE_IDENTITY_INVALID"
    )


def test_corrective_offline_result_requires_a075_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    core, corrective = _load_modules()
    identity = corrective.A075_EVIDENCE_IDENTITY
    source_sha = "a" * 40
    stdout = b"offline stdout\n"
    stderr = b""

    def result_payload(gate: str) -> bytes:
        return json.dumps(
            {
                "schema_version": 1,
                "gate": gate,
                "source_sha": source_sha,
                "outcome": "PASS",
                "exit_code": 0,
                "timed_out": False,
                "invocation_count": 1,
                "rerun_count": 0,
                "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
                "stdout_bytes": len(stdout),
                "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
                "stderr_bytes": len(stderr),
            },
            separators=(",", ":"),
        ).encode("utf-8")

    payloads = {
        identity.offline_lock_path.resolve(): identity.offline_lease_text.encode(
            "ascii"
        ),
        identity.offline_result_path.resolve(): result_payload("A-075-OFFLINE"),
        identity.offline_stdout_path.resolve(): stdout,
        identity.offline_stderr_path.resolve(): stderr,
    }
    monkeypatch.setattr(
        core,
        "_read_bounded_file_once",
        lambda path, *, max_bytes: payloads[path.resolve()],
    )

    with core._bind_corrective_evidence_identity(identity):
        assert (
            core._require_offline_gate(source_sha)
            == hashlib.sha256(
                payloads[identity.offline_result_path.resolve()]
            ).hexdigest()
        )
        payloads[identity.offline_result_path.resolve()] = result_payload(
            "A-074-OFFLINE"
        )
        with pytest.raises(core._ConfigurationInvalid):
            core._require_offline_gate(source_sha)
