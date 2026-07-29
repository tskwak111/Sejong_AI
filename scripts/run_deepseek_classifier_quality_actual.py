#!/usr/bin/env python3
"""Run the isolated A-080 DeepSeek classifier quality acceptance."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import run_deepseek_classifier_actual as _core

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_OFFLINE_DIRECTORY = (
    _REPOSITORY_ROOT / ".superpowers" / "sdd" / "2026-07-29-deepseek-classifier-quality"
)

A080_EVIDENCE_IDENTITY = _core.EvidenceIdentity(
    report_path=(
        _REPOSITORY_ROOT
        / "docs"
        / "test-reports"
        / "CHAT-HYBRID-RAG-001-DEEPSEEK-A080-ACTUAL.md"
    ),
    offline_result_path=_OFFLINE_DIRECTORY / "a080-offline-gate-result.json",
    offline_lock_path=_OFFLINE_DIRECTORY / "a080-offline-gate-result.json.run.lock",
    offline_stdout_path=_OFFLINE_DIRECTORY / "a080-offline-gate.stdout.log",
    offline_stderr_path=_OFFLINE_DIRECTORY / "a080-offline-gate.stderr.log",
    offline_gate="A-080-OFFLINE",
    offline_lease_text="A-080-OFFLINE-GATE one-shot lease\n",
    actual_lease_text="A-080-DEEPSEEK-CLASSIFIER one-shot lease\n",
    actual_run_deadline_seconds=100,
    pre_actual_check=None,
)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    return _core.main(arguments, evidence_identity=A080_EVIDENCE_IDENTITY)


if __name__ == "__main__":
    raise SystemExit(main())
