from __future__ import annotations

import secrets
import subprocess
from pathlib import Path

from provision_local_database_login import update_env_assignment

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TARGET_ENV_KEY = "CONTEXT_TOKEN_SECRET"
TARGET_RELATIVE_PATH = Path("apps") / "api" / ".env"
MINIMUM_SECRET_BYTES = 32


def resolve_git_common_dir(repository_root: Path) -> Path:
    result = subprocess.run(
        [
            "git",
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        ],
        cwd=repository_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    output = result.stdout.strip()
    if (
        result.returncode != 0
        or not output
        or "\x00" in output
        or len(output.splitlines()) != 1
    ):
        raise ValueError("LOCAL_GIT_COMMON_DIR_INVALID")
    return Path(output).resolve()


def resolve_primary_env_path(common_git_dir: Path) -> Path:
    resolved_common_dir = common_git_dir.resolve()
    if (
        resolved_common_dir.name.casefold() != ".git"
        or not resolved_common_dir.is_dir()
    ):
        raise ValueError("LOCAL_GIT_COMMON_DIR_INVALID")
    repository_root = resolved_common_dir.parent
    env_path = (repository_root / TARGET_RELATIVE_PATH).resolve()
    if env_path.parent.parent.parent != repository_root:
        raise ValueError("LOCAL_CONTEXT_ENV_PATH_INVALID")
    return env_path


def assert_target_is_gitignored(repository_root: Path, env_path: Path) -> None:
    expected = (repository_root.resolve() / TARGET_RELATIVE_PATH).resolve()
    if env_path.resolve() != expected or env_path.is_symlink():
        raise ValueError("LOCAL_CONTEXT_ENV_PATH_INVALID")
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", TARGET_RELATIVE_PATH.as_posix()],
        cwd=repository_root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise ValueError("LOCAL_CONTEXT_ENV_NOT_IGNORED")


def _validate_generated_secret(value: str) -> None:
    try:
        encoded = value.encode("utf-8")
    except UnicodeError:
        raise ValueError("LOCAL_CONTEXT_SECRET_GENERATION_INVALID") from None
    if (
        len(encoded) < MINIMUM_SECRET_BYTES
        or not value.isascii()
        or value != value.strip()
        or any(character in value for character in "\x00\r\n")
    ):
        raise ValueError("LOCAL_CONTEXT_SECRET_GENERATION_INVALID")


def provision_context_secret(env_path: Path) -> None:
    secret = secrets.token_urlsafe(MINIMUM_SECRET_BYTES)
    _validate_generated_secret(secret)
    update_env_assignment(env_path, TARGET_ENV_KEY, secret)


def main() -> int:
    try:
        common_git_dir = resolve_git_common_dir(REPOSITORY_ROOT)
        env_path = resolve_primary_env_path(common_git_dir)
        assert_target_is_gitignored(common_git_dir.parent, env_path)
        provision_context_secret(env_path)
    except (OSError, UnicodeError, ValueError):
        print("[FAIL] step=PROVISION-LOCAL-CONTEXT-SECRET reason=operational code=1")
        return 1

    print("[PASS] step=PROVISION-LOCAL-CONTEXT-SECRET")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
