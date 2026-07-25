from collections.abc import Mapping
from pathlib import Path
from typing import cast

import pytest

from sejong_ai_api.llm import settings as settings_module
from sejong_ai_api.llm.settings import (
    UpstageChatSettings,
    UpstageSyntheticSettings,
    load_upstage_chat_settings,
    load_upstage_synthetic_settings,
)

VALID = {
    "LLM_PROVIDER": "upstage",
    "LLM_MODEL": "solar-pro3",
    "LLM_API_KEY": "synthetic-test-key-not-a-real-secret",
    "LLM_BASE_URL": "https://api.upstage.ai/v1",
    "LLM_TIMEOUT_SECONDS": "15",
    "LLM_MAX_RETRIES": "1",
    "LLM_MAX_CONCURRENCY": "1",
    "LLM_MAX_INPUT_TOKENS": "4096",
    "LLM_MAX_OUTPUT_TOKENS": "1024",
    "LLM_RUN_ATTEMPT_CAP": "30",
    "UPSTAGE_SYNTHETIC_EVALUATION_MODE": "true",
    "UPSTAGE_GROUNDED_CHAT_MODE": "false",
}

CHAT_VALID = {
    **VALID,
    "LLM_API_KEY": "chat-test-key-not-a-real-secret",
    "LLM_TIMEOUT_SECONDS": "8",
    "LLM_MAX_RETRIES": "0",
    "UPSTAGE_SYNTHETIC_EVALUATION_MODE": "false",
    "UPSTAGE_GROUNDED_CHAT_MODE": "true",
}


def test_exact_synthetic_settings_load_without_exposing_key() -> None:
    settings = load_upstage_synthetic_settings(environ=VALID, env_path=Path("missing"))

    assert isinstance(settings, UpstageSyntheticSettings)
    assert settings.model == "solar-pro3"
    assert settings.base_url == "https://api.upstage.ai/v1"
    assert settings.timeout_seconds == 15.0
    assert settings.max_retries == 1
    assert settings.max_concurrency == 1
    assert settings.max_input_tokens == 4096
    assert settings.max_output_tokens == 1024
    assert settings.run_attempt_cap == 30
    assert VALID["LLM_API_KEY"] not in repr(settings)


def test_exact_grounded_chat_settings_load_without_exposing_key() -> None:
    settings = load_upstage_chat_settings(environ=CHAT_VALID, env_path=Path("missing"))

    assert isinstance(settings, UpstageChatSettings)
    assert settings.model == "solar-pro3"
    assert settings.base_url == "https://api.upstage.ai/v1"
    assert settings.timeout_seconds == 8.0
    assert settings.max_retries == 0
    assert settings.max_concurrency == 1
    assert settings.max_input_tokens == 4096
    assert settings.max_output_tokens == 1024
    assert settings.run_attempt_cap == 30
    assert CHAT_VALID["LLM_API_KEY"] not in repr(settings)


def test_modes_are_mutually_exclusive_and_disabled_by_default() -> None:
    assert load_upstage_synthetic_settings(environ={}, env_path=Path("missing")) is None
    assert load_upstage_chat_settings(environ={}, env_path=Path("missing")) is None

    for synthetic_mode, chat_mode in (("true", "true"), ("false", "false")):
        synthetic = {
            **VALID,
            "UPSTAGE_SYNTHETIC_EVALUATION_MODE": synthetic_mode,
            "UPSTAGE_GROUNDED_CHAT_MODE": chat_mode,
        }
        chat = {
            **CHAT_VALID,
            "UPSTAGE_SYNTHETIC_EVALUATION_MODE": synthetic_mode,
            "UPSTAGE_GROUNDED_CHAT_MODE": chat_mode,
        }
        assert load_upstage_synthetic_settings(environ=synthetic, env_path=Path("missing")) is None
        assert load_upstage_chat_settings(environ=chat, env_path=Path("missing")) is None


def test_grounded_chat_rejects_every_non_exact_profile_value() -> None:
    for key, invalid in (
        ("LLM_PROVIDER", "disabled"),
        ("LLM_MODEL", "solar-pro"),
        ("LLM_BASE_URL", "https://example.invalid/v1"),
        ("LLM_TIMEOUT_SECONDS", "15"),
        ("LLM_MAX_RETRIES", "1"),
        ("LLM_MAX_CONCURRENCY", "2"),
        ("LLM_MAX_INPUT_TOKENS", "4097"),
        ("LLM_MAX_OUTPUT_TOKENS", "2048"),
        ("LLM_RUN_ATTEMPT_CAP", "31"),
        ("UPSTAGE_SYNTHETIC_EVALUATION_MODE", "true"),
        ("UPSTAGE_GROUNDED_CHAT_MODE", "false"),
    ):
        candidate = dict(CHAT_VALID)
        candidate[key] = invalid
        assert load_upstage_chat_settings(environ=candidate, env_path=Path("missing")) is None


class _KeyReadFailsMapping(dict[str, str]):
    def __getitem__(self, key: str) -> str:
        if key == "LLM_API_KEY":
            raise AssertionError("key must not be read before non-secret validation")
        return super().__getitem__(key)

    def __contains__(self, key: object) -> bool:
        return True if key == "LLM_API_KEY" else super().__contains__(key)


def test_invalid_non_secret_chat_configuration_does_not_read_key() -> None:
    invalid = _KeyReadFailsMapping({**CHAT_VALID, "LLM_TIMEOUT_SECONDS": "15"})

    assert load_upstage_chat_settings(environ=invalid, env_path=Path("missing")) is None


def test_invalid_dotenv_profile_never_enters_file_key_extraction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = getattr(settings_module, "_extract_dotenv_api_key", None)
    assert callable(extractor), "two-phase dotenv key extraction seam is required"
    env_path = tmp_path / ".env"
    invalid = {**CHAT_VALID, "LLM_TIMEOUT_SECONDS": "15"}
    env_path.write_text(
        "\n".join(f"{key}={value}" for key, value in invalid.items()),
        encoding="utf-8",
    )

    def fail_if_called(_path: Path) -> str:
        raise AssertionError("file key must not be extracted before exact profile validation")

    monkeypatch.setattr(
        settings_module,
        "_extract_dotenv_api_key",
        fail_if_called,
    )

    assert load_upstage_chat_settings(environ={}, env_path=env_path) is None


def test_exact_dotenv_profile_extracts_file_key_only_in_phase_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = getattr(settings_module, "_extract_dotenv_api_key", None)
    assert callable(extractor), "two-phase dotenv key extraction seam is required"
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(f"{key}={value}" for key, value in CHAT_VALID.items()),
        encoding="utf-8",
    )
    calls: list[Path] = []

    def observed_extract(path: Path) -> str | None:
        calls.append(path)
        return extractor(path)

    monkeypatch.setattr(
        settings_module,
        "_extract_dotenv_api_key",
        observed_extract,
    )

    settings = load_upstage_chat_settings(environ={}, env_path=env_path)

    assert isinstance(settings, UpstageChatSettings)
    assert calls == [env_path]


def test_process_key_wins_without_extracting_valid_file_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = getattr(settings_module, "_extract_dotenv_api_key", None)
    assert callable(extractor), "two-phase dotenv key extraction seam is required"
    env_path = tmp_path / ".env"
    file_profile = {**CHAT_VALID, "LLM_API_KEY": "file-fallback-key-not-a-real-secret"}
    env_path.write_text(
        "\n".join(f"{key}={value}" for key, value in file_profile.items()),
        encoding="utf-8",
    )

    def fail_if_called(_path: Path) -> str:
        raise AssertionError("process key must win without file key extraction")

    monkeypatch.setattr(
        settings_module,
        "_extract_dotenv_api_key",
        fail_if_called,
    )

    settings = load_upstage_chat_settings(environ=CHAT_VALID, env_path=env_path)

    assert isinstance(settings, UpstageChatSettings)
    assert settings.api_key == CHAT_VALID["LLM_API_KEY"]


def test_duplicate_file_key_fails_before_extraction_phase(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = getattr(settings_module, "_extract_dotenv_api_key", None)
    assert callable(extractor), "two-phase dotenv key extraction seam is required"
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                *(f"{key}={value}" for key, value in CHAT_VALID.items()),
                "LLM_API_KEY=duplicate-key-not-a-real-secret",
            ]
        ),
        encoding="utf-8",
    )

    def fail_if_called(_path: Path) -> str:
        raise AssertionError("duplicate key must fail before file key extraction")

    monkeypatch.setattr(
        settings_module,
        "_extract_dotenv_api_key",
        fail_if_called,
    )

    assert load_upstage_chat_settings(environ={}, env_path=env_path) is None


def test_process_values_override_file_and_preserve_synthetic_profile(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    file_chat = {**CHAT_VALID, "LLM_TIMEOUT_SECONDS": "15"}
    env_path.write_text(
        "\n".join(f"{key}={value}" for key, value in file_chat.items()),
        encoding="utf-8",
    )
    process_synthetic = dict(VALID)

    chat = load_upstage_chat_settings(environ={"LLM_TIMEOUT_SECONDS": "8"}, env_path=env_path)
    synthetic = load_upstage_synthetic_settings(environ=process_synthetic, env_path=env_path)

    assert isinstance(chat, UpstageChatSettings)
    assert isinstance(synthetic, UpstageSyntheticSettings)


def test_duplicate_chat_mode_dotenv_assignment_fails_closed(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                *(f"{key}={value}" for key, value in CHAT_VALID.items()),
                "UPSTAGE_GROUNDED_CHAT_MODE=true",
            ]
        ),
        encoding="utf-8",
    )

    assert load_upstage_chat_settings(environ={}, env_path=env_path) is None


def test_disabled_or_non_exact_values_fail_closed() -> None:
    for key, invalid in (
        ("LLM_PROVIDER", "disabled"),
        ("LLM_MODEL", "solar-pro"),
        ("LLM_BASE_URL", "https://example.invalid/v1"),
        ("LLM_TIMEOUT_SECONDS", "14"),
        ("LLM_MAX_RETRIES", "2"),
        ("LLM_MAX_CONCURRENCY", "2"),
        ("LLM_MAX_INPUT_TOKENS", "4097"),
        ("LLM_MAX_OUTPUT_TOKENS", "2048"),
        ("LLM_RUN_ATTEMPT_CAP", "31"),
        ("UPSTAGE_SYNTHETIC_EVALUATION_MODE", "false"),
    ):
        candidate = dict(VALID)
        candidate[key] = invalid

        assert load_upstage_synthetic_settings(environ=candidate, env_path=Path("missing")) is None


def test_malformed_or_ambiguous_values_fail_closed(tmp_path: Path) -> None:
    for key, invalid in (
        ("LLM_API_KEY", ""),
        ("LLM_PROVIDER", " upstage"),
        ("LLM_MODEL", '"solar-pro3"'),
        ("LLM_BASE_URL", "https://api.upstage.ai/v1/"),
        ("LLM_BASE_URL", "https://api.upstage.ai/v1?x=1"),
        ("LLM_TIMEOUT_SECONDS", "１５"),
        ("LLM_MAX_RETRIES", "1\n"),
    ):
        candidate = dict(VALID)
        candidate[key] = invalid
        assert (
            load_upstage_synthetic_settings(environ=candidate, env_path=tmp_path / "none") is None
        )


def test_duplicate_allowlisted_dotenv_assignment_fails_closed(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            (
                "LLM_PROVIDER=upstage",
                "LLM_PROVIDER=upstage",
                "LLM_MODEL=solar-pro3",
                "LLM_API_KEY=synthetic-test-key-not-a-real-secret",
                "LLM_BASE_URL=https://api.upstage.ai/v1",
                "LLM_TIMEOUT_SECONDS=15",
                "LLM_MAX_RETRIES=1",
                "LLM_MAX_CONCURRENCY=1",
                "LLM_MAX_INPUT_TOKENS=4096",
                "LLM_MAX_OUTPUT_TOKENS=1024",
                "LLM_RUN_ATTEMPT_CAP=30",
                "UPSTAGE_SYNTHETIC_EVALUATION_MODE=true",
            )
        ),
        encoding="utf-8",
    )

    assert load_upstage_synthetic_settings(environ={}, env_path=env_path) is None


def test_malformed_allowlisted_dotenv_assignments_fail_closed(
    tmp_path: Path,
) -> None:
    for assignment in ("LLM_PROVIDER", "LLM_PROVIDER =upstage", "=upstage"):
        env_path = tmp_path / ".env"
        env_path.write_text(assignment, encoding="utf-8")

        assert load_upstage_synthetic_settings(environ=VALID, env_path=env_path) is None


def test_non_string_runtime_value_fails_closed() -> None:
    malformed = cast(Mapping[str, str], {**VALID, "LLM_PROVIDER": 1})

    assert load_upstage_synthetic_settings(environ=malformed, env_path=Path("missing")) is None
