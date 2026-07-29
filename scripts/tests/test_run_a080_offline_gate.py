from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_WRAPPER_PATH = _REPOSITORY_ROOT / "scripts" / "run_a080_offline_gate.ps1"
_RESULT_RELATIVE = Path(
    ".superpowers/sdd/2026-07-29-deepseek-classifier-quality/"
    "a080-offline-gate-result.json"
)
_LOCK_RELATIVE = _RESULT_RELATIVE.with_name("a080-offline-gate-result.json.run.lock")


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


def _fake_repository(
    tmp_path: Path,
    *,
    verify_exit: int = 0,
    dirty_source: bool = False,
    sleep_seconds: int = 0,
    timeout_seconds: int | None = None,
) -> Path:
    repository = tmp_path / "A080 controlled repository"
    scripts = repository / "scripts"
    scripts.mkdir(parents=True)
    wrapper = _WRAPPER_PATH.read_text(encoding="utf-8")
    if timeout_seconds is not None:
        wrapper = wrapper.replace(
            "$TimeoutSeconds = 3600",
            f"$TimeoutSeconds = {timeout_seconds}",
            1,
        )
    (scripts / _WRAPPER_PATH.name).write_text(wrapper, encoding="utf-8")
    (repository / ".gitignore").write_text(".superpowers/\n", encoding="utf-8")
    (repository / "tracked.txt").write_text("clean\n", encoding="utf-8")
    verify_lines = [
        "param([switch]$Offline)",
        "$repo = Split-Path -Parent $PSScriptRoot",
        '$dir = Join-Path $repo ".superpowers"',
        "[System.IO.Directory]::CreateDirectory($dir) | Out-Null",
        '$marker = Join-Path $dir "stub-invocations.txt"',
        "[System.IO.File]::AppendAllText($marker, 'offline=true' + [Environment]::NewLine)",
    ]
    if dirty_source:
        verify_lines.append('Add-Content -LiteralPath (Join-Path $repo "tracked.txt") -Value "dirty"')
    if sleep_seconds:
        verify_lines.append(f"Start-Sleep -Seconds {sleep_seconds}")
    verify_lines.extend((f"exit {verify_exit}", ""))
    (scripts / "verify.ps1").write_text("\n".join(verify_lines), encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    _git(repository, "config", "user.email", "test@example.invalid")
    _git(repository, "config", "user.name", "A080 Test")
    _git(repository, "add", ".")
    _git(repository, "commit", "-qm", "controlled baseline")
    return repository


def _run_wrapper(repository: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment.update(
        {
            "DEEPSEEK_API_KEY": "not-read",
            "DEEPSEEK_BASE_URL": "http://127.0.0.1:9",
        }
    )
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
        env=environment,
    )


@pytest.mark.parametrize(
    ("verify_exit", "expected_outcome"),
    ((0, "PASS"), (7, "FAIL")),
)
def test_a080_result_is_one_shot_with_an_exact_lf_lease(
    tmp_path: Path,
    verify_exit: int,
    expected_outcome: str,
) -> None:
    repository = _fake_repository(tmp_path, verify_exit=verify_exit)

    completed = _run_wrapper(repository)

    assert completed.returncode == verify_exit
    assert completed.stdout.strip() == f"A080_OFFLINE_GATE_{expected_outcome}"
    assert "not-read" not in completed.stdout + completed.stderr
    result_path = repository / _RESULT_RELATIVE
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["gate"] == "A-080-OFFLINE"
    assert result["outcome"] == expected_outcome
    assert result["invocation_count"] == 1
    assert result["rerun_count"] == 0
    assert (repository / _LOCK_RELATIVE).read_bytes() == b"A-080-OFFLINE-GATE one-shot lease\n"

    result_before = result_path.read_bytes()
    second = _run_wrapper(repository)

    assert second.returncode != 0
    assert result_path.read_bytes() == result_before
    assert (repository / ".superpowers/stub-invocations.txt").read_text(
        encoding="utf-8"
    ).splitlines() == ["offline=true"]


def test_a080_source_dirtiness_closes_the_gate_fail(tmp_path: Path) -> None:
    repository = _fake_repository(tmp_path, dirty_source=True)

    completed = _run_wrapper(repository)

    result = json.loads((repository / _RESULT_RELATIVE).read_text(encoding="utf-8"))
    assert completed.returncode == 125
    assert completed.stdout.strip() == "A080_OFFLINE_GATE_FAIL"
    assert result["outcome"] == "FAIL"
    assert result["exit_code"] == 125


def test_a080_timeout_closes_the_gate_fail(tmp_path: Path) -> None:
    repository = _fake_repository(tmp_path, sleep_seconds=2, timeout_seconds=1)

    completed = _run_wrapper(repository)

    result = json.loads((repository / _RESULT_RELATIVE).read_text(encoding="utf-8"))
    assert completed.returncode == 124
    assert completed.stdout.strip() == "A080_OFFLINE_GATE_FAIL"
    assert result["outcome"] == "FAIL"
    assert result["timed_out"] is True
