#!/usr/bin/env python3
"""Run one immutable aggregate-only DeepSeek transport probe for A-078."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import NoReturn

import run_deepseek_classifier_actual as _core
from sejong_ai_api.chat.classification import SafeQuestion, classify_question
from sejong_ai_api.llm.deepseek_classifier import (
    DeepSeekQuestionClassifier,
    create_deepseek_classifier_client,
)
from sejong_ai_api.llm.deepseek_settings import (
    DEEPSEEK_CONNECT_TIMEOUT_SECONDS,
    DEEPSEEK_MAX_CONCURRENCY,
    DEEPSEEK_MODEL,
    DEEPSEEK_TIMEOUT_SECONDS,
)
from sejong_ai_api.llm.strict_json import load_strict_json_bytes
from sejong_ai_api.privacy.redaction import redact_question

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_EVIDENCE_DIRECTORY = (
    _REPOSITORY_ROOT / ".superpowers" / "sdd" / "2026-07-29-deepseek-prelease-hardening"
)
_PROBE_REPORT_PATH = _EVIDENCE_DIRECTORY / "a078-probe-result.json"
_PROBE_LEASE_PATH = _EVIDENCE_DIRECTORY / "a078-probe-result.json.run.lock"
_PROBE_LEASE_TEXT = "A-078-DEEPSEEK-PROBE one-shot lease\n"
_PROBE_DEADLINE_SECONDS = 12.0
_REPORT_MAX_BYTES = 64 * 1024

A078_EVIDENCE_IDENTITY = _core.EvidenceIdentity(
    report_path=(
        _REPOSITORY_ROOT
        / "docs"
        / "test-reports"
        / "CHAT-HYBRID-RAG-001-DEEPSEEK-A078-ACTUAL.md"
    ),
    offline_result_path=_EVIDENCE_DIRECTORY / "a078-offline-gate-result.json",
    offline_lock_path=_EVIDENCE_DIRECTORY / "a078-offline-gate-result.json.run.lock",
    offline_stdout_path=_EVIDENCE_DIRECTORY / "a078-offline-gate.stdout.log",
    offline_stderr_path=_EVIDENCE_DIRECTORY / "a078-offline-gate.stderr.log",
    offline_gate="A-078-OFFLINE",
    offline_lease_text="A-078-OFFLINE-GATE one-shot lease\n",
    actual_lease_text="A-078-DEEPSEEK-CLASSIFIER one-shot lease\n",
    actual_run_deadline_seconds=100,
)

_REPORT_FIELDS = frozenset(
    {
        "source_sha",
        "model",
        "connect_timeout_seconds",
        "response_timeout_seconds",
        "selected_count",
        "outbound_attempt_count",
        "provider_response_count",
        "http_2xx_count",
        "http_rejected_count",
        "transport_no_response_count",
        "strict_parse_count",
        "usage_accepted_count",
        "usage_rejected_count",
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "conservative_all_miss_cost_usd_including_vat",
        "cost_cap_usd_including_vat",
        "runtime_failure_count",
        "invocation_count",
        "retry_count",
        "rerun_count",
        "concurrency",
        "retained_question_count",
        "retained_masked_question_count",
        "retained_request_body_count",
        "retained_response_body_count",
        "retained_invalid_value_count",
        "retained_secret_count",
        "acceptance",
    }
)
_ZERO_RETENTION_FIELDS = (
    "retained_question_count",
    "retained_masked_question_count",
    "retained_request_body_count",
    "retained_response_body_count",
    "retained_invalid_value_count",
    "retained_secret_count",
)
_NONNEGATIVE_COUNT_FIELDS = (
    "strict_parse_count",
    "usage_accepted_count",
    "usage_rejected_count",
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
)


class _ArgumentsInvalid(ValueError):
    pass


class _ReadinessInvalid(RuntimeError):
    pass


class _RunAlreadyExists(RuntimeError):
    pass


class _EvidenceWriteFailed(RuntimeError):
    pass


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> NoReturn:
        raise _ArgumentsInvalid from None


def _parse_args(argv: Sequence[str] | None) -> bool:
    parser = _SafeArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--readiness-only", action="store_true")
    values = parser.parse_args(argv)
    return bool(values.readiness_only)


def _perform_readiness() -> _core._PreparedRun:
    options = _core._RunnerOptions(
        fixture_path=_core._FIXTURE_PATH,
        report_path=A078_EVIDENCE_IDENTITY.report_path,
        readiness_only=False,
    )
    with _core._bind_corrective_evidence_identity(A078_EVIDENCE_IDENTITY):
        return _core._perform_readiness(options)


def _revalidate_prepared_run(prepared: _core._PreparedRun) -> None:
    with _core._bind_corrective_evidence_identity(A078_EVIDENCE_IDENTITY):
        _core._revalidate_prepared_run(prepared)


def _require_probe_absent() -> None:
    if _PROBE_REPORT_PATH.exists() or _PROBE_LEASE_PATH.exists():
        raise _RunAlreadyExists


def _write_new_file(path: Path, payload: bytes) -> None:
    descriptor: int | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
            0o600,
        )
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise OSError
            offset += written
        os.fsync(descriptor)
    except FileExistsError:
        raise _RunAlreadyExists from None
    except OSError:
        raise _EvidenceWriteFailed from None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _acquire_probe_lease() -> None:
    _write_new_file(_PROBE_LEASE_PATH, _PROBE_LEASE_TEXT.encode("ascii"))


def _strict_nonnegative_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _bounded_cost(value: object) -> bool:
    if type(value) is not str:
        return False
    try:
        parsed = Decimal(value)
    except InvalidOperation:
        return False
    return parsed.is_finite() and Decimal("0") <= parsed <= _core._ACTUAL_COST_CAP_USD


def _criteria_pass(report: Mapping[str, object]) -> bool:
    return (
        frozenset(report) == _REPORT_FIELDS
        and type(report.get("source_sha")) is str
        and re.fullmatch(r"[0-9a-f]{40}", str(report["source_sha"])) is not None
        and report.get("model") == DEEPSEEK_MODEL
        and type(report.get("connect_timeout_seconds")) is float
        and report.get("connect_timeout_seconds") == DEEPSEEK_CONNECT_TIMEOUT_SECONDS
        and type(report.get("response_timeout_seconds")) is float
        and report.get("response_timeout_seconds") == DEEPSEEK_TIMEOUT_SECONDS
        and type(report.get("selected_count")) is int
        and report.get("selected_count") == 1
        and type(report.get("outbound_attempt_count")) is int
        and report.get("outbound_attempt_count") == 1
        and type(report.get("provider_response_count")) is int
        and report.get("provider_response_count") == 1
        and type(report.get("http_2xx_count")) is int
        and report.get("http_2xx_count") == 1
        and type(report.get("http_rejected_count")) is int
        and report.get("http_rejected_count") == 0
        and type(report.get("transport_no_response_count")) is int
        and report.get("transport_no_response_count") == 0
        and all(
            _strict_nonnegative_int(report.get(field))
            for field in _NONNEGATIVE_COUNT_FIELDS
        )
        and _bounded_cost(report.get("conservative_all_miss_cost_usd_including_vat"))
        and report.get("cost_cap_usd_including_vat")
        == _core._decimal_text(_core._ACTUAL_COST_CAP_USD)
        and type(report.get("runtime_failure_count")) is int
        and report.get("runtime_failure_count") == 0
        and type(report.get("invocation_count")) is int
        and report.get("invocation_count") == 1
        and type(report.get("retry_count")) is int
        and report.get("retry_count") == 0
        and type(report.get("rerun_count")) is int
        and report.get("rerun_count") == 0
        and type(report.get("concurrency")) is int
        and report.get("concurrency") == 1
        and all(
            type(report.get(field)) is int and report.get(field) == 0
            for field in _ZERO_RETENTION_FIELDS
        )
    )


def _acceptance_passes(report: Mapping[str, object]) -> bool:
    return _criteria_pass(report) and report.get("acceptance") == "PASS"


async def _execute_probe(prepared: _core._PreparedRun) -> dict[str, object]:
    if type(prepared) is not _core._PreparedRun:
        raise _ReadinessInvalid
    provider_cases = tuple(
        case for case in prepared.selection.selected if case.expected_provider_use == 1
    )
    if len(provider_cases) != _core._EXPECTED_PROVIDER_COUNT:
        raise _ReadinessInvalid
    case = provider_cases[0]
    safe_question = SafeQuestion(redact_question(case.question))
    if not classify_question(safe_question).needs_provider:
        raise _ReadinessInvalid

    ledger = _core._build_ledger(prepared.settings)
    usage_recorder = _core._UsageRecorder()
    decision = None
    client = create_deepseek_classifier_client(prepared.settings)
    async with client:
        classifier = DeepSeekQuestionClassifier(
            settings=prepared.settings,
            client=client,
            ledger=ledger,
            response_observer=usage_recorder.capture,
        )
        decision = await classifier.classify(safe_question, prepared.catalog)

    outbound_count = ledger.classifier_attempts_used
    response_count = usage_recorder.response_count
    report: dict[str, object] = {
        "source_sha": prepared.source_sha,
        "model": prepared.settings.model,
        "connect_timeout_seconds": prepared.settings.connect_timeout_seconds,
        "response_timeout_seconds": prepared.settings.timeout_seconds,
        "selected_count": 1,
        "outbound_attempt_count": outbound_count,
        "provider_response_count": response_count,
        "http_2xx_count": usage_recorder.http_2xx_count,
        "http_rejected_count": usage_recorder.http_rejected_count,
        "transport_no_response_count": max(0, outbound_count - response_count),
        "strict_parse_count": int(decision is not None),
        "usage_accepted_count": usage_recorder.usage_accepted_count,
        "usage_rejected_count": usage_recorder.usage_rejected_count,
        "input_tokens": usage_recorder.usage.input_tokens,
        "cached_input_tokens": usage_recorder.usage.cached_input_tokens,
        "output_tokens": usage_recorder.usage.output_tokens,
        "conservative_all_miss_cost_usd_including_vat": _core._decimal_text(
            ledger.actual_cost_usd
        ),
        "cost_cap_usd_including_vat": _core._decimal_text(_core._ACTUAL_COST_CAP_USD),
        "runtime_failure_count": 0,
        "invocation_count": 1,
        "retry_count": 0,
        "rerun_count": 0,
        "concurrency": DEEPSEEK_MAX_CONCURRENCY,
        "retained_question_count": 0,
        "retained_masked_question_count": 0,
        "retained_request_body_count": 0,
        "retained_response_body_count": 0,
        "retained_invalid_value_count": 0,
        "retained_secret_count": 0,
        "acceptance": "FAIL",
    }
    report["acceptance"] = "PASS" if _criteria_pass(report) else "FAIL"
    return report


def _execute_probe_with_deadline(
    prepared: _core._PreparedRun,
) -> dict[str, object]:
    async def bounded() -> dict[str, object]:
        async with asyncio.timeout(_PROBE_DEADLINE_SECONDS):
            return await _execute_probe(prepared)

    return asyncio.run(bounded())


def _runtime_failure_report(prepared: _core._PreparedRun) -> dict[str, object]:
    try:
        source_sha = prepared.source_sha
        settings = prepared.settings
        model = settings.model
        connect_timeout_seconds = settings.connect_timeout_seconds
        response_timeout_seconds = settings.timeout_seconds
    except (AttributeError, TypeError):
        raise _EvidenceWriteFailed from None
    return {
        "source_sha": source_sha,
        "model": model,
        "connect_timeout_seconds": connect_timeout_seconds,
        "response_timeout_seconds": response_timeout_seconds,
        "selected_count": 1,
        "outbound_attempt_count": 0,
        "provider_response_count": 0,
        "http_2xx_count": 0,
        "http_rejected_count": 0,
        "transport_no_response_count": 0,
        "strict_parse_count": 0,
        "usage_accepted_count": 0,
        "usage_rejected_count": 0,
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "output_tokens": 0,
        "conservative_all_miss_cost_usd_including_vat": "0",
        "cost_cap_usd_including_vat": _core._decimal_text(_core._ACTUAL_COST_CAP_USD),
        "runtime_failure_count": 1,
        "invocation_count": 1,
        "retry_count": 0,
        "rerun_count": 0,
        "concurrency": DEEPSEEK_MAX_CONCURRENCY,
        "retained_question_count": 0,
        "retained_masked_question_count": 0,
        "retained_request_body_count": 0,
        "retained_response_body_count": 0,
        "retained_invalid_value_count": 0,
        "retained_secret_count": 0,
        "acceptance": "FAIL",
    }


def _write_report_once(report: Mapping[str, object]) -> None:
    if frozenset(report) != _REPORT_FIELDS:
        raise _EvidenceWriteFailed
    payload = (
        json.dumps(report, ensure_ascii=True, separators=(",", ":")) + "\n"
    ).encode("ascii")
    if len(payload) > _REPORT_MAX_BYTES:
        raise _EvidenceWriteFailed
    _write_new_file(_PROBE_REPORT_PATH, payload)


def _read_bounded_file(path: Path, *, max_bytes: int) -> bytes:
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError
    with path.open("rb") as stream:
        payload = stream.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError
    return payload


def require_probe_pass_for_current_source(source_sha: str) -> bool:
    if (
        type(source_sha) is not str
        or len(source_sha) != 40
        or any(character not in "0123456789abcdef" for character in source_sha)
    ):
        return False
    try:
        lease_payload = _read_bounded_file(_PROBE_LEASE_PATH, max_bytes=1024)
        if lease_payload != _PROBE_LEASE_TEXT.encode("ascii"):
            return False
        payload = _read_bounded_file(
            _PROBE_REPORT_PATH,
            max_bytes=_REPORT_MAX_BYTES,
        )
        document = load_strict_json_bytes(payload)
    except (OSError, UnicodeError, TypeError, ValueError):
        return False
    return (
        type(document) is dict
        and document.get("source_sha") == source_sha
        and _acceptance_passes(document)
    )


def main(argv: Sequence[str] | None = None) -> int:
    try:
        readiness_only = _parse_args(argv)
    except Exception:
        print("DEEPSEEK_A078_PROBE_ARGUMENTS_INVALID", file=sys.stderr)
        return 2
    try:
        _require_probe_absent()
        prepared = _perform_readiness()
    except _RunAlreadyExists:
        print("DEEPSEEK_A078_PROBE_RUN_ALREADY_RECORDED", file=sys.stderr)
        return 2
    except Exception:
        print("DEEPSEEK_A078_PROBE_READINESS_INVALID", file=sys.stderr)
        return 2
    if readiness_only:
        print("DEEPSEEK_A078_PROBE_READY")
        return 0

    try:
        _revalidate_prepared_run(prepared)
        _acquire_probe_lease()
    except _RunAlreadyExists:
        print("DEEPSEEK_A078_PROBE_RUN_ALREADY_RECORDED", file=sys.stderr)
        return 2
    except Exception:
        print("DEEPSEEK_A078_PROBE_LEASE_FAILED", file=sys.stderr)
        return 2

    execution_failed = False
    try:
        report = _execute_probe_with_deadline(prepared)
    except Exception:
        execution_failed = True
        try:
            report = _runtime_failure_report(prepared)
        except Exception:
            print("DEEPSEEK_A078_PROBE_EVIDENCE_WRITE_FAILED", file=sys.stderr)
            return 3
    if not execution_failed:
        try:
            _revalidate_prepared_run(prepared)
        except Exception:
            execution_failed = True
            report = {
                **report,
                "runtime_failure_count": 1,
                "acceptance": "FAIL",
            }
    try:
        _write_report_once(report)
    except Exception:
        print("DEEPSEEK_A078_PROBE_EVIDENCE_WRITE_FAILED", file=sys.stderr)
        return 3
    if execution_failed:
        print("DEEPSEEK_A078_PROBE_RUNTIME_FAILED", file=sys.stderr)
        return 3
    if not _acceptance_passes(report):
        print("DEEPSEEK_A078_PROBE_ACCEPTANCE_FAILED", file=sys.stderr)
        return 1
    print("DEEPSEEK_A078_PROBE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
