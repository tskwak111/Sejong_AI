from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_WRAPPER_PATH = _REPOSITORY_ROOT / "scripts" / "run_a079_offline_gate.ps1"
_RESULT_RELATIVE = Path(
    ".superpowers/sdd/2026-07-29-deepseek-network-retry/a079-offline-gate-result.json"
)
_LOCK_RELATIVE = _RESULT_RELATIVE.with_name("a079-offline-gate-result.json.run.lock")


def _powershell() -> str:
    executable = shutil.which("powershell.exe") or shutil.which("powershell")
    if executable is None:
        pytest.skip("Windows PowerShell is required")
    return executable


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _fake_repository(tmp_path: Path, *, verify_exit: int = 0) -> Path:
    repository = tmp_path / "A079 controlled repository"
    scripts = repository / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(_WRAPPER_PATH, scripts / _WRAPPER_PATH.name)
    (repository / ".gitignore").write_text(".superpowers/\n", encoding="utf-8")
    (scripts / "verify.ps1").write_text(
        "\n".join(
            (
                "param([switch]$Offline)",
                "$repo = Split-Path -Parent $PSScriptRoot",
                '$dir = Join-Path $repo ".superpowers"',
                "[System.IO.Directory]::CreateDirectory($dir) | Out-Null",
                '$marker = Join-Path $dir "stub-invocations.txt"',
                "[System.IO.File]::AppendAllText($marker, 'offline=true' + [Environment]::NewLine)",
                f"exit {verify_exit}",
                "",
            )
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    _git(repository, "config", "user.email", "test@example.invalid")
    _git(repository, "config", "user.name", "A079 Test")
    _git(repository, "add", ".")
    _git(repository, "commit", "-qm", "controlled baseline")
    return repository


def _run_wrapper(repository: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            _powershell(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(repository / "scripts" / _WRAPPER_PATH.name),
        ],
        cwd=repository.parent,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )


@pytest.mark.parametrize(
    ("verify_exit", "expected_outcome"),
    ((0, "PASS"), (7, "FAIL")),
)
def test_a079_result_is_one_shot_and_disjoint(
    tmp_path: Path,
    verify_exit: int,
    expected_outcome: str,
) -> None:
    repository = _fake_repository(tmp_path, verify_exit=verify_exit)

    completed = _run_wrapper(repository)

    assert completed.returncode == verify_exit
    assert completed.stdout.strip() == f"A079_OFFLINE_GATE_{expected_outcome}"
    result_path = repository / _RESULT_RELATIVE
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["gate"] == "A-079-OFFLINE"
    assert result["outcome"] == expected_outcome
    assert result["invocation_count"] == 1
    assert result["rerun_count"] == 0
    assert (repository / _LOCK_RELATIVE).read_bytes() == (
        b"A-079-OFFLINE-GATE one-shot lease\n"
    )
    artifact_root = repository / ".superpowers"
    for predecessor in ("a074", "a075", "a076", "a077", "a078"):
        assert not list(artifact_root.rglob(f"*{predecessor}*"))

    result_before = result_path.read_bytes()
    second = _run_wrapper(repository)

    assert second.returncode != 0
    assert result_path.read_bytes() == result_before
    assert (repository / ".superpowers/stub-invocations.txt").read_text(
        encoding="utf-8"
    ).splitlines() == ["offline=true"]
