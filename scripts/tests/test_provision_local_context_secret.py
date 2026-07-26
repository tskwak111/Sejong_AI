from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

_MODULE_NAME = "_sejong_provision_local_context_secret_test"
_SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
_RUNNER_PATH = _SCRIPTS_ROOT / "provision_local_context_secret.py"


def _runner() -> ModuleType:
    cached = sys.modules.get(_MODULE_NAME)
    if cached is not None:
        return cached
    if not _RUNNER_PATH.is_file():
        pytest.fail("the local context-secret provisioner is missing")
    spec = importlib.util.spec_from_file_location(_MODULE_NAME, _RUNNER_PATH)
    if spec is None or spec.loader is None:
        pytest.fail("the local context-secret provisioner cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_MODULE_NAME] = module
    sys.path.insert(0, str(_SCRIPTS_ROOT))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(_SCRIPTS_ROOT))
    return module


def _initialize_repository(path: Path, *, ignored: bool) -> Path:
    path.mkdir()
    subprocess.run(
        ["git", "init", "--quiet"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    if ignored:
        (path / ".gitignore").write_text("apps/api/.env\n", encoding="utf-8")
    env_path = path / "apps" / "api" / ".env"
    env_path.parent.mkdir(parents=True)
    return env_path


def test_primary_env_path_is_fixed_under_the_common_git_directory(
    tmp_path: Path,
) -> None:
    runner = _runner()
    common_git_dir = tmp_path / "repository" / ".git"
    common_git_dir.mkdir(parents=True)

    assert runner.resolve_primary_env_path(common_git_dir) == (
        tmp_path / "repository" / "apps" / "api" / ".env"
    )

    with pytest.raises(ValueError, match="LOCAL_GIT_COMMON_DIR_INVALID"):
        runner.resolve_primary_env_path(tmp_path / "repository" / "other")


def test_provision_replaces_only_context_secret_and_preserves_existing_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    env_path = tmp_path / ".env"
    old_secret = "old-context-secret-sentinel"
    new_secret = "n" * 43
    original = (
        b"LLM_API_KEY=provider-key-sentinel\r\n"
        + f"CONTEXT_TOKEN_SECRET={old_secret}\r\n".encode()
        + b"DATABASE_URL=database-url-sentinel\r\n"
    )
    env_path.write_bytes(original)
    monkeypatch.setattr(runner.secrets, "token_urlsafe", lambda _size: new_secret)

    runner.provision_context_secret(env_path)

    assert env_path.read_bytes() == (
        b"LLM_API_KEY=provider-key-sentinel\r\n"
        + f"CONTEXT_TOKEN_SECRET={new_secret}\r\n".encode()
        + b"DATABASE_URL=database-url-sentinel\r\n"
    )
    assert old_secret.encode() not in env_path.read_bytes()


@pytest.mark.parametrize(
    "generated",
    ["short", "x" * 32 + "\nforbidden", "가" * 10],
)
def test_invalid_generated_secret_leaves_existing_file_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    generated: str,
) -> None:
    runner = _runner()
    env_path = tmp_path / ".env"
    original = b"CONTEXT_TOKEN_SECRET=existing-safe-value-sentinel\n"
    env_path.write_bytes(original)
    monkeypatch.setattr(runner.secrets, "token_urlsafe", lambda _size: generated)

    with pytest.raises(ValueError, match="LOCAL_CONTEXT_SECRET_GENERATION_INVALID"):
        runner.provision_context_secret(env_path)

    assert env_path.read_bytes() == original


def test_main_updates_only_an_ignored_env_and_keeps_output_value_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    repository = tmp_path / "repository"
    env_path = _initialize_repository(repository, ignored=True)
    old_secret = "old-main-secret-sentinel"
    generated_secret = "g" * 43
    env_path.write_text(
        f"CONTEXT_TOKEN_SECRET={old_secret}\nOTHER_SETTING=preserved\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(runner, "REPOSITORY_ROOT", repository)
    monkeypatch.setattr(
        runner.secrets,
        "token_urlsafe",
        lambda _size: generated_secret,
    )

    assert runner.main() == 0

    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert combined.strip() == "[PASS] step=PROVISION-LOCAL-CONTEXT-SECRET"
    assert old_secret not in combined
    assert generated_secret not in combined
    assert env_path.read_text(encoding="utf-8") == (
        f"CONTEXT_TOKEN_SECRET={generated_secret}\nOTHER_SETTING=preserved\n"
    )


def test_main_refuses_a_non_ignored_target_before_generation_or_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    repository = tmp_path / "repository"
    env_path = _initialize_repository(repository, ignored=False)
    original = b"CONTEXT_TOKEN_SECRET=existing-secret-sentinel\n"
    env_path.write_bytes(original)
    generated = False

    def unexpected_generation(_size: int) -> str:
        nonlocal generated
        generated = True
        return "x" * 43

    monkeypatch.setattr(runner, "REPOSITORY_ROOT", repository)
    monkeypatch.setattr(runner.secrets, "token_urlsafe", unexpected_generation)

    assert runner.main() == 1

    captured = capsys.readouterr()
    assert (captured.out + captured.err).strip() == (
        "[FAIL] step=PROVISION-LOCAL-CONTEXT-SECRET reason=operational code=1"
    )
    assert generated is False
    assert env_path.read_bytes() == original
