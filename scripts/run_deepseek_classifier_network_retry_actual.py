#!/usr/bin/env python3
"""Run the isolated A-079 DeepSeek classifier pre-lease-hardened acceptance."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import run_deepseek_classifier_actual as _core
from run_deepseek_classifier_a079_probe import (
    require_probe_pass_for_current_source,
)

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_OFFLINE_DIRECTORY = (
    _REPOSITORY_ROOT / ".superpowers" / "sdd" / "2026-07-29-deepseek-network-retry"
)

A079_EVIDENCE_IDENTITY = _core.EvidenceIdentity(
    report_path=(
        _REPOSITORY_ROOT
        / "docs"
        / "test-reports"
        / "CHAT-HYBRID-RAG-001-DEEPSEEK-A079-ACTUAL.md"
    ),
    offline_result_path=_OFFLINE_DIRECTORY / "a079-offline-gate-result.json",
    offline_lock_path=_OFFLINE_DIRECTORY / "a079-offline-gate-result.json.run.lock",
    offline_stdout_path=_OFFLINE_DIRECTORY / "a079-offline-gate.stdout.log",
    offline_stderr_path=_OFFLINE_DIRECTORY / "a079-offline-gate.stderr.log",
    offline_gate="A-079-OFFLINE",
    offline_lease_text="A-079-OFFLINE-GATE one-shot lease\n",
    actual_lease_text="A-079-DEEPSEEK-CLASSIFIER one-shot lease\n",
    actual_run_deadline_seconds=100,
    pre_actual_check=require_probe_pass_for_current_source,
)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    if "--readiness-only" not in arguments:
        try:
            if not require_probe_pass_for_current_source(_source_sha()):
                raise RuntimeError
        except Exception:
            print("DEEPSEEK_A079_ACTUAL_PROBE_NOT_PASSED", file=sys.stderr)
            return 2
    return _core.main(arguments, evidence_identity=A079_EVIDENCE_IDENTITY)


def _source_sha() -> str:
    return _core._source_sha()


if __name__ == "__main__":
    raise SystemExit(main())
