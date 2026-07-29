from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_WRAPPER_PATH = _REPOSITORY_ROOT / "scripts" / "run_a075_offline_gate.ps1"
_RESULT_RELATIVE = Path(
    ".superpowers/sdd/2026-07-29-deepseek-corrective-actual/"
    "a075-offline-gate-result.json"
)
_LOCK_RELATIVE = _RESULT_RELATIVE.with_name("a075-offline-gate-result.json.run.lock")
_STDOUT_RELATIVE = _RESULT_RELATIVE.with_name("a075-offline-gate.stdout.log")
_STDERR_RELATIVE = _RESULT_RELATIVE.with_name("a075-offline-gate.stderr.log")


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fake_repository(tmp_path: Path, *, verify_exit: int = 0) -> Path:
    repository = tmp_path / "A075 controlled repository"
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
                '$line = "offline=" + $Offline.ToString().ToLowerInvariant()',
                "[System.IO.File]::AppendAllText($marker, $line + [Environment]::NewLine)",
                'Write-Output "controlled stdout"',
                '[Console]::Error.WriteLine("controlled stderr")',
                f"exit {verify_exit}",
                "",
            )
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    _git(repository, "config", "user.email", "test@example.invalid")
    _git(repository, "config", "user.name", "A075 Test")
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


def test_controlled_pass_is_a075_one_shot_and_never_creates_a074_artifacts(
    tmp_path: Path,
) -> None:
    repository = _fake_repository(tmp_path)
    source_sha = _git(repository, "rev-parse", "HEAD")

    completed = _run_wrapper(repository)

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "A075_OFFLINE_GATE_PASS"
    result_path = repository / _RESULT_RELATIVE
    lock_path = repository / _LOCK_RELATIVE
    stdout_path = repository / _STDOUT_RELATIVE
    stderr_path = repository / _STDERR_RELATIVE
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result == {
        "schema_version": 1,
        "gate": "A-075-OFFLINE",
        "source_sha": source_sha,
        "outcome": "PASS",
        "exit_code": 0,
        "timed_out": False,
        "invocation_count": 1,
        "rerun_count": 0,
        "stdout_sha256": _sha256(stdout_path),
        "stdout_bytes": stdout_path.stat().st_size,
        "stderr_sha256": _sha256(stderr_path),
        "stderr_bytes": stderr_path.stat().st_size,
    }
    assert (
        lock_path.read_text(encoding="ascii") == "A-075-OFFLINE-GATE one-shot lease\n"
    )
    assert not list(repository.rglob("*a074*"))
    assert (repository / ".superpowers/stub-invocations.txt").read_text(
        encoding="utf-8"
    ).splitlines() == ["offline=true"]

    result_before = result_path.read_bytes()
    second = _run_wrapper(repository)

    assert second.returncode != 0
    assert result_path.read_bytes() == result_before
    assert (repository / ".superpowers/stub-invocations.txt").read_text(
        encoding="utf-8"
    ).splitlines() == ["offline=true"]


def test_controlled_failure_is_immutable_a075_fail(tmp_path: Path) -> None:
    repository = _fake_repository(tmp_path, verify_exit=7)

    completed = _run_wrapper(repository)

    assert completed.returncode == 7
    assert completed.stdout.strip() == "A075_OFFLINE_GATE_FAIL"
    result = json.loads((repository / _RESULT_RELATIVE).read_text(encoding="utf-8"))
    assert result["gate"] == "A-075-OFFLINE"
    assert result["outcome"] == "FAIL"
    assert result["exit_code"] == 7
    assert result["invocation_count"] == 1
    assert result["rerun_count"] == 0
    assert (repository / _LOCK_RELATIVE).is_file()
