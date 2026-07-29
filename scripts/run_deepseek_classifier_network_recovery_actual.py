#!/usr/bin/env python3
"""Run the isolated A-076 DeepSeek classifier network-recovery acceptance."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import run_deepseek_classifier_actual as _core

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_OFFLINE_DIRECTORY = (
    _REPOSITORY_ROOT
    / ".superpowers"
    / "sdd"
    / "2026-07-29-deepseek-network-recovery-actual"
)

A076_EVIDENCE_IDENTITY = _core.EvidenceIdentity(
    report_path=(
        _REPOSITORY_ROOT
        / "docs"
        / "test-reports"
        / "CHAT-HYBRID-RAG-001-DEEPSEEK-A076-ACTUAL.md"
    ),
    offline_result_path=_OFFLINE_DIRECTORY / "a076-offline-gate-result.json",
    offline_lock_path=_OFFLINE_DIRECTORY / "a076-offline-gate-result.json.run.lock",
    offline_stdout_path=_OFFLINE_DIRECTORY / "a076-offline-gate.stdout.log",
    offline_stderr_path=_OFFLINE_DIRECTORY / "a076-offline-gate.stderr.log",
    offline_gate="A-076-OFFLINE",
    offline_lease_text="A-076-OFFLINE-GATE one-shot lease\n",
    actual_lease_text="A-076-DEEPSEEK-CLASSIFIER one-shot lease\n",
)


def main(argv: Sequence[str] | None = None) -> int:
    return _core.main(argv, evidence_identity=A076_EVIDENCE_IDENTITY)


if __name__ == "__main__":
    raise SystemExit(main())
