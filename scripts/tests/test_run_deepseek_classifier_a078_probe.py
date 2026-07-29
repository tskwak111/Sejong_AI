from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS_ROOT = _REPOSITORY_ROOT / "scripts"
if str(_SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_ROOT))


def _probe() -> Any:
    sys.modules.pop("run_deepseek_classifier_a078_probe", None)
    return importlib.import_module("run_deepseek_classifier_a078_probe")


def _passing_metrics(probe: Any) -> dict[str, object]:
    return {
        "source_sha": "a" * 40,
        "model": "deepseek-v4-flash",
        "connect_timeout_seconds": 3.0,
        "response_timeout_seconds": 10.0,
        "selected_count": 1,
        "outbound_attempt_count": 1,
        "provider_response_count": 1,
        "http_2xx_count": 1,
        "http_rejected_count": 0,
        "transport_no_response_count": 0,
        "strict_parse_count": 0,
        "usage_accepted_count": 0,
        "usage_rejected_count": 1,
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "conservative_all_miss_cost_usd_including_vat": "0.00256256",
        "cost_cap_usd_including_vat": "0.2",
        "runtime_failure_count": 0,
        "invocation_count": 1,
        "retry_count": 0,
        "rerun_count": 0,
        "concurrency": 1,
        "retained_question_count": 0,
        "retained_masked_question_count": 0,
        "retained_request_body_count": 0,
        "retained_response_body_count": 0,
        "retained_invalid_value_count": 0,
        "retained_secret_count": 0,
        "acceptance": "PASS",
    }


def test_probe_identity_is_local_ignored_and_disjoint_from_actual() -> None:
    probe = _probe()

    assert ".superpowers" in probe._PROBE_REPORT_PATH.parts
    assert probe._PROBE_REPORT_PATH.name == "a078-probe-result.json"
    assert probe._PROBE_LEASE_PATH.name == "a078-probe-result.json.run.lock"
    assert probe._PROBE_REPORT_PATH != probe.A078_EVIDENCE_IDENTITY.report_path
    assert probe._PROBE_LEASE_TEXT == "A-078-DEEPSEEK-PROBE one-shot lease\n"


def test_probe_acceptance_requires_one_2xx_response_and_zero_retention() -> None:
    probe = _probe()
    passing = _passing_metrics(probe)

    assert probe._acceptance_passes(passing)
    for field in (
        "provider_response_count",
        "http_2xx_count",
    ):
        failing = {**passing, field: 0, "acceptance": "FAIL"}
        assert not probe._acceptance_passes(failing)
    failing = {**passing, "retained_secret_count": 1, "acceptance": "FAIL"}
    assert not probe._acceptance_passes(failing)
    assert not probe._acceptance_passes(
        {
            **passing,
            "conservative_all_miss_cost_usd_including_vat": "0.2000001",
            "acceptance": "PASS",
        }
    )
    assert not probe._acceptance_passes(
        {**passing, "outbound_attempt_count": True, "acceptance": "PASS"}
    )
    assert not probe._acceptance_passes(
        {**passing, "source_sha": "not-a-source-sha", "acceptance": "PASS"}
    )


def test_probe_main_readiness_does_not_consume_lease_or_call_provider(
    monkeypatch: Any,
    capsys: Any,
) -> None:
    probe = _probe()
    prepared = SimpleNamespace(source_sha="a" * 40)
    monkeypatch.setattr(probe, "_perform_readiness", lambda: prepared)
    monkeypatch.setattr(
        probe,
        "_require_probe_absent",
        lambda: None,
    )
    monkeypatch.setattr(
        probe,
        "_acquire_probe_lease",
        lambda: (_ for _ in ()).throw(AssertionError("lease must not be acquired")),
    )
    monkeypatch.setattr(
        probe,
        "_execute_probe_with_deadline",
        lambda _prepared: (_ for _ in ()).throw(
            AssertionError("provider must not be called")
        ),
    )

    assert probe.main(["--readiness-only"]) == 0
    assert capsys.readouterr().out.strip() == "DEEPSEEK_A078_PROBE_READY"


def test_probe_main_writes_aggregate_pass_once_without_sensitive_values(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    probe = _probe()
    report_path = tmp_path / "probe.json"
    lease_path = tmp_path / "probe.json.run.lock"
    prepared = SimpleNamespace(source_sha="a" * 40)
    metrics = _passing_metrics(probe)
    forbidden = (
        "synthetic-question-marker",
        "synthetic-provider-body-marker",
        "synthetic-secret-marker",
        "postgresql://synthetic-dsn-marker",
    )

    monkeypatch.setattr(probe, "_PROBE_REPORT_PATH", report_path)
    monkeypatch.setattr(probe, "_PROBE_LEASE_PATH", lease_path)
    monkeypatch.setattr(probe, "_perform_readiness", lambda: prepared)
    monkeypatch.setattr(probe, "_revalidate_prepared_run", lambda _prepared: None)
    monkeypatch.setattr(
        probe, "_execute_probe_with_deadline", lambda _prepared: metrics
    )

    assert probe.main([]) == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "DEEPSEEK_A078_PROBE_PASS"
    assert captured.err == ""
    document = json.loads(report_path.read_text(encoding="utf-8"))
    assert document == metrics
    assert lease_path.read_bytes() == probe._PROBE_LEASE_TEXT.encode("ascii")
    exposed = report_path.read_text(encoding="utf-8") + lease_path.read_text(
        encoding="ascii"
    )
    assert all(marker not in exposed for marker in forbidden)
    assert probe.main([]) == 2
    assert capsys.readouterr().err.strip() == "DEEPSEEK_A078_PROBE_RUN_ALREADY_RECORDED"


def test_probe_pass_validator_rejects_wrong_source_or_non_2xx(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    probe = _probe()
    report_path = tmp_path / "probe.json"
    lease_path = tmp_path / "probe.json.run.lock"
    monkeypatch.setattr(probe, "_PROBE_REPORT_PATH", report_path)
    monkeypatch.setattr(probe, "_PROBE_LEASE_PATH", lease_path)
    passing = _passing_metrics(probe)
    report_path.write_text(
        json.dumps(passing, ensure_ascii=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    assert probe.require_probe_pass_for_current_source("a" * 40) is False
    lease_path.write_bytes(probe._PROBE_LEASE_TEXT.encode("ascii"))
    assert probe.require_probe_pass_for_current_source("a" * 40) is True
    assert probe.require_probe_pass_for_current_source("b" * 40) is False
    report_path.write_text(
        json.dumps(
            {**passing, "http_2xx_count": 0, "acceptance": "FAIL"},
            ensure_ascii=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    assert probe.require_probe_pass_for_current_source("a" * 40) is False


@pytest.mark.parametrize(
    "invalid_lease",
    (
        "wrong lease\n",
        "x" * 1025,
    ),
)
def test_probe_pass_validator_rejects_wrong_or_oversized_lease(
    tmp_path: Path,
    monkeypatch: Any,
    invalid_lease: str,
) -> None:
    probe = _probe()
    report_path = tmp_path / "probe.json"
    lease_path = tmp_path / "probe.json.run.lock"
    monkeypatch.setattr(probe, "_PROBE_REPORT_PATH", report_path)
    monkeypatch.setattr(probe, "_PROBE_LEASE_PATH", lease_path)
    report_path.write_text(
        json.dumps(
            _passing_metrics(probe),
            ensure_ascii=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    lease_path.write_text(invalid_lease, encoding="ascii")

    assert probe.require_probe_pass_for_current_source("a" * 40) is False


def test_probe_runtime_failure_after_lease_still_writes_immutable_fail_report(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    probe = _probe()
    report_path = tmp_path / "probe.json"
    lease_path = tmp_path / "probe.json.run.lock"
    prepared = SimpleNamespace(
        source_sha="a" * 40,
        settings=SimpleNamespace(
            model="deepseek-v4-flash",
            connect_timeout_seconds=3.0,
            timeout_seconds=10.0,
        ),
    )

    monkeypatch.setattr(probe, "_PROBE_REPORT_PATH", report_path)
    monkeypatch.setattr(probe, "_PROBE_LEASE_PATH", lease_path)
    monkeypatch.setattr(probe, "_perform_readiness", lambda: prepared)
    monkeypatch.setattr(probe, "_revalidate_prepared_run", lambda _prepared: None)
    monkeypatch.setattr(
        probe,
        "_execute_probe_with_deadline",
        lambda _prepared: (_ for _ in ()).throw(TimeoutError),
    )

    assert probe.main([]) == 3
    captured = capsys.readouterr()
    assert captured.err.strip() == "DEEPSEEK_A078_PROBE_RUNTIME_FAILED"
    document = json.loads(report_path.read_text(encoding="utf-8"))
    assert document["acceptance"] == "FAIL"
    assert document["runtime_failure_count"] == 1
    assert document["invocation_count"] == 1
    assert document["rerun_count"] == 0
    assert lease_path.exists()


def test_probe_post_execution_source_drift_writes_fail_not_pass(
    tmp_path: Path,
    monkeypatch: Any,
    capsys: Any,
) -> None:
    probe = _probe()
    report_path = tmp_path / "probe.json"
    lease_path = tmp_path / "probe.json.run.lock"
    prepared = SimpleNamespace(source_sha="a" * 40)
    revalidation_count = 0

    def revalidate_then_drift(_prepared: object) -> None:
        nonlocal revalidation_count
        revalidation_count += 1
        if revalidation_count == 2:
            raise RuntimeError

    monkeypatch.setattr(probe, "_PROBE_REPORT_PATH", report_path)
    monkeypatch.setattr(probe, "_PROBE_LEASE_PATH", lease_path)
    monkeypatch.setattr(probe, "_perform_readiness", lambda: prepared)
    monkeypatch.setattr(probe, "_revalidate_prepared_run", revalidate_then_drift)
    monkeypatch.setattr(
        probe,
        "_execute_probe_with_deadline",
        lambda _prepared: _passing_metrics(probe),
    )

    assert probe.main([]) == 3
    assert revalidation_count == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.strip() == "DEEPSEEK_A078_PROBE_RUNTIME_FAILED"
    document = json.loads(report_path.read_text(encoding="utf-8"))
    assert document["outbound_attempt_count"] == 1
    assert document["http_2xx_count"] == 1
    assert document["runtime_failure_count"] == 1
    assert document["acceptance"] == "FAIL"
    assert lease_path.exists()
