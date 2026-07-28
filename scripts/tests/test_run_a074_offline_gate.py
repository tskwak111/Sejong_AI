from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_WRAPPER_PATH = _REPOSITORY_ROOT / "scripts" / "run_a074_offline_gate.ps1"
_RESULT_RELATIVE = Path(
    ".superpowers/sdd/2026-07-29-deepseek-classifier-provider/"
    "a074-offline-gate-result.json"
)
_LOCK_RELATIVE = _RESULT_RELATIVE.with_name("a074-offline-gate-result.json.run.lock")
_STDOUT_RELATIVE = _RESULT_RELATIVE.with_name("a074-offline-gate.stdout.log")
_STDERR_RELATIVE = _RESULT_RELATIVE.with_name("a074-offline-gate.stderr.log")


def _powershell() -> str:
    executable = shutil.which("powershell.exe") or shutil.which("powershell")
    if executable is None:
        pytest.skip("Windows PowerShell is required for the controlled wrapper test")
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
    repository = tmp_path / "가짜 저장소 with spaces"
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
    _git(repository, "config", "user.name", "A074 Test")
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


def _commit_controlled_change(repository: Path, message: str) -> None:
    _git(repository, "add", ".")
    _git(repository, "commit", "-qm", message)


def test_wrapper_is_fixed_ps51_start_process_and_denies_actual_runners() -> None:
    source = _WRAPPER_PATH.read_text(encoding="utf-8")

    assert "$TimeoutSeconds = 3600" in source
    assert 0 < int(source.split("$PollSeconds = ", 1)[1].splitlines()[0]) <= 60
    assert "Start-Process" in source
    assert "-RedirectStandardOutput" in source
    assert "-RedirectStandardError" in source
    assert '"-NoProfile"' in source
    assert '"-ExecutionPolicy"' in source
    assert '"Bypass"' in source
    assert '"-File"' in source
    assert '"-Offline"' in source
    assert "taskkill.exe" in source
    assert '"/PID"' in source
    assert '"/T"' in source
    assert '"/F"' in source
    assert "WaitForExit" in source
    assert "$leaseAcquired = $true" in source
    assert "$processTerminationConfirmed = $true" in source
    assert "run_hybrid_rag_actual" not in source
    assert "run_upstage_classifier_evaluation" not in source
    assert "run_deepseek_classifier_actual" not in source
    assert "A-073" not in source


def test_controlled_fake_repo_pass_invokes_verify_offline_once_and_keeps_artifacts(
    tmp_path: Path,
) -> None:
    repository = _fake_repository(tmp_path)
    source_sha = _git(repository, "rev-parse", "HEAD")

    completed = _run_wrapper(repository)

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "A074_OFFLINE_GATE_PASS"
    assert completed.stderr == ""
    result_path = repository / _RESULT_RELATIVE
    lock_path = repository / _LOCK_RELATIVE
    stdout_path = repository / _STDOUT_RELATIVE
    stderr_path = repository / _STDERR_RELATIVE
    assert result_path.is_file()
    assert lock_path.is_file()
    assert stdout_path.is_file()
    assert stderr_path.is_file()
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result == {
        "schema_version": 1,
        "gate": "A-074-OFFLINE",
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
    assert (repository / ".superpowers/stub-invocations.txt").read_text(
        encoding="utf-8"
    ).splitlines() == ["offline=true"]
    assert _git(repository, "status", "--porcelain=v1", "--untracked-files=all") == ""

    result_before = result_path.read_bytes()
    lock_before = lock_path.read_bytes()
    second = _run_wrapper(repository)

    assert second.returncode != 0
    assert result_path.read_bytes() == result_before
    assert lock_path.read_bytes() == lock_before
    assert (repository / ".superpowers/stub-invocations.txt").read_text(
        encoding="utf-8"
    ).splitlines() == ["offline=true"]


def test_controlled_fake_repo_failure_is_one_shot_aggregate(
    tmp_path: Path,
) -> None:
    repository = _fake_repository(tmp_path, verify_exit=7)
    source_sha = _git(repository, "rev-parse", "HEAD")

    completed = _run_wrapper(repository)

    assert completed.returncode == 7
    assert completed.stdout.strip() == "A074_OFFLINE_GATE_FAIL"
    result_path = repository / _RESULT_RELATIVE
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["source_sha"] == source_sha
    assert result["outcome"] == "FAIL"
    assert result["exit_code"] == 7
    assert result["timed_out"] is False
    assert result["invocation_count"] == 1
    assert result["rerun_count"] == 0
    assert (repository / _LOCK_RELATIVE).is_file()
    assert (repository / ".superpowers/stub-invocations.txt").read_text(
        encoding="utf-8"
    ).splitlines() == ["offline=true"]


def test_dirty_or_untracked_source_is_rejected_before_lock_or_stub(
    tmp_path: Path,
) -> None:
    repository = _fake_repository(tmp_path)
    untracked_source = repository / "scripts" / "untracked_source.py"
    untracked_source.write_text("print('untracked')\n", encoding="utf-8")

    completed = _run_wrapper(repository)

    assert completed.returncode != 0
    assert not (repository / _RESULT_RELATIVE).exists()
    assert not (repository / _LOCK_RELATIVE).exists()
    assert not (repository / _STDOUT_RELATIVE).exists()
    assert not (repository / _STDERR_RELATIVE).exists()
    assert not (repository / ".superpowers/stub-invocations.txt").exists()


def test_concurrent_starter_without_lock_ownership_cannot_publish_result(
    tmp_path: Path,
) -> None:
    repository = _fake_repository(tmp_path)
    wrapper_path = repository / "scripts" / _WRAPPER_PATH.name
    source = wrapper_path.read_text(encoding="utf-8")
    barrier = "\n".join(
        (
            '$barrier = Join-Path $repoRoot ".superpowers\\concurrent-barrier"',
            "[System.IO.Directory]::CreateDirectory($barrier) | Out-Null",
            '$ready = Join-Path $barrier ("ready-" + $PID.ToString())',
            '[System.IO.File]::WriteAllText($ready, "ready")',
            "while (@(Get-ChildItem -LiteralPath $barrier).Count -lt 2) {",
            "    Start-Sleep -Milliseconds 20",
            "}",
        )
    )
    marker = "}\n\n$exitCode = 125"
    assert source.count(marker) == 1
    wrapper_path.write_text(
        source.replace(marker, f"}}\n\n{barrier}\n\n$exitCode = 125"),
        encoding="utf-8",
    )
    verify_path = repository / "scripts" / "verify.ps1"
    verify_source = verify_path.read_text(encoding="utf-8")
    verify_path.write_text(
        verify_source.replace(
            'Write-Output "controlled stdout"',
            'Start-Sleep -Milliseconds 1000\nWrite-Output "controlled stdout"',
        ),
        encoding="utf-8",
    )
    _commit_controlled_change(repository, "add controlled concurrency barrier")
    command = [
        _powershell(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(wrapper_path),
    ]

    processes = [
        subprocess.Popen(
            command,
            cwd=repository.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(2)
    ]
    completed = [
        (*process.communicate(timeout=30), process.returncode) for process in processes
    ]

    assert sorted(item[2] for item in completed)[0] == 0
    assert sum(item[2] == 0 for item in completed) == 1
    result_path = repository / _RESULT_RELATIVE
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["outcome"] == "PASS"
    assert result["exit_code"] == 0
    assert result["invocation_count"] == 1
    assert result["rerun_count"] == 0
    assert (repository / ".superpowers/stub-invocations.txt").read_text(
        encoding="utf-8"
    ).splitlines() == ["offline=true"]
    assert result["stdout_sha256"] == _sha256(repository / _STDOUT_RELATIVE)
    assert result["stderr_sha256"] == _sha256(repository / _STDERR_RELATIVE)


def test_unconfirmed_timeout_termination_never_publishes_mutable_log_hashes(
    tmp_path: Path,
) -> None:
    repository = _fake_repository(tmp_path)
    wrapper_path = repository / "scripts" / _WRAPPER_PATH.name
    source = wrapper_path.read_text(encoding="utf-8")
    source = source.replace("$TimeoutSeconds = 3600", "$TimeoutSeconds = 1")
    kill_line = '$taskkill = Join-Path $env:SystemRoot "System32\\taskkill.exe"'
    assert source.count(kill_line) == 1
    source = source.replace(
        kill_line,
        'throw "CONTROLLED_PROCESS_TREE_KILL_FAILURE"\n    ' + kill_line,
    )
    wrapper_path.write_text(source, encoding="utf-8")
    verify_path = repository / "scripts" / "verify.ps1"
    verify_path.write_text(
        "\n".join(
            (
                "param([switch]$Offline)",
                "$repo = Split-Path -Parent $PSScriptRoot",
                '$dir = Join-Path $repo ".superpowers"',
                "[System.IO.Directory]::CreateDirectory($dir) | Out-Null",
                '$marker = Join-Path $dir "stub-invocations.txt"',
                '[System.IO.File]::AppendAllText($marker, "started" + [Environment]::NewLine)',
                "Start-Sleep -Milliseconds 4000",
                '[System.IO.File]::AppendAllText($marker, "finished" + [Environment]::NewLine)',
                'Write-Output "controlled stdout after failed kill"',
                "exit 0",
                "",
            )
        ),
        encoding="utf-8",
    )
    _commit_controlled_change(repository, "add controlled kill failure")

    completed = _run_wrapper(repository)

    assert completed.returncode == 125
    assert (repository / _LOCK_RELATIVE).is_file()
    assert not (repository / _RESULT_RELATIVE).exists()
    marker_path = repository / ".superpowers/stub-invocations.txt"
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        if marker_path.exists() and "finished" in marker_path.read_text(
            encoding="utf-8"
        ):
            break
        time.sleep(0.05)
    assert not (repository / _RESULT_RELATIVE).exists()
    assert marker_path.read_text(encoding="utf-8").splitlines() == [
        "started",
        "finished",
    ]
