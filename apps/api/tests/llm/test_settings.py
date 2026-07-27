from collections.abc import Callable, Mapping
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest

from sejong_ai_api.llm import settings as settings_module
from sejong_ai_api.llm.cost import RUN_COST_CAP_USD
from sejong_ai_api.llm.settings import (
    UpstageChatSettings,
    UpstageClassifierSettings,
    UpstageSyntheticSettings,
    load_upstage_chat_settings,
    load_upstage_classifier_settings,
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
    "UPSTAGE_CLASSIFIER_MODE": "false",
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

CLASSIFIER_VALID = {
    "LLM_PROVIDER": "upstage",
    "LLM_MODEL": "solar-pro3",
    "LLM_API_KEY": "classifier-test-key-not-a-real-secret",
    "LLM_BASE_URL": "https://api.upstage.ai/v1",
    "LLM_MAX_CONCURRENCY": "1",
    "UPSTAGE_SYNTHETIC_EVALUATION_MODE": "false",
    "UPSTAGE_CLASSIFIER_MODE": "true",
    "UPSTAGE_GROUNDED_CHAT_MODE": "false",
    "LLM_CLASSIFIER_TIMEOUT_SECONDS": "3",
    "LLM_CLASSIFIER_MAX_RETRIES": "0",
    "LLM_CLASSIFIER_MAX_INPUT_CHARS": "1024",
    "LLM_CLASSIFIER_MAX_OUTPUT_TOKENS": "128",
    "LLM_CLASSIFIER_ATTEMPT_CAP": "20",
    "LLM_GENERATOR_ATTEMPT_CAP": "30",
    "LLM_COMBINED_ATTEMPT_CAP": "40",
}

COMBINED_VALID = {
    **CHAT_VALID,
    "LLM_API_KEY": "combined-test-key-not-a-real-secret",
    "UPSTAGE_CLASSIFIER_MODE": "true",
    "LLM_CLASSIFIER_TIMEOUT_SECONDS": "3",
    "LLM_CLASSIFIER_MAX_RETRIES": "0",
    "LLM_CLASSIFIER_MAX_INPUT_CHARS": "1024",
    "LLM_CLASSIFIER_MAX_OUTPUT_TOKENS": "128",
    "LLM_CLASSIFIER_ATTEMPT_CAP": "80",
    "LLM_GENERATOR_ATTEMPT_CAP": "100",
    "LLM_COMBINED_ATTEMPT_CAP": "160",
    "LLM_SESSION_COST_CAP_USD": "0.20",
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
    assert Decimal("0.05") == RUN_COST_CAP_USD
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


def test_exact_historical_classifier_only_settings_load_without_exposing_key() -> None:
    settings = load_upstage_classifier_settings(
        environ=CLASSIFIER_VALID,
        env_path=Path("missing"),
    )

    assert isinstance(settings, UpstageClassifierSettings)
    assert settings.model == "solar-pro3"
    assert settings.base_url == "https://api.upstage.ai/v1"
    assert settings.timeout_seconds == 3.0
    assert settings.max_retries == 0
    assert settings.max_concurrency == 1
    assert settings.max_input_chars == 1024
    assert settings.max_output_tokens == 128
    assert settings.classifier_attempt_cap == 20
    assert settings.generator_attempt_cap == 30
    assert settings.combined_attempt_cap == 40
    assert settings.session_cost_cap_usd == Decimal("0.05")
    assert CLASSIFIER_VALID["LLM_API_KEY"] not in repr(settings)


def test_exact_local_interactive_combined_profile_loads_for_both_lanes() -> None:
    classifier = load_upstage_classifier_settings(
        environ=COMBINED_VALID,
        env_path=Path("missing"),
    )
    chat = load_upstage_chat_settings(
        environ=COMBINED_VALID,
        env_path=Path("missing"),
    )

    assert isinstance(classifier, UpstageClassifierSettings)
    assert isinstance(chat, UpstageChatSettings)
    assert classifier.classifier_attempt_cap == 80
    assert classifier.generator_attempt_cap == 100
    assert classifier.combined_attempt_cap == 160
    assert classifier.session_cost_cap_usd == Decimal("0.20")
    assert chat.run_attempt_cap == 30
    assert COMBINED_VALID["LLM_API_KEY"] not in repr(classifier)
    assert COMBINED_VALID["LLM_API_KEY"] not in repr(chat)


def test_classifier_disabled_or_non_exact_profile_fails_closed() -> None:
    assert load_upstage_classifier_settings(environ={}, env_path=Path("missing")) is None
    for key, invalid in (
        ("LLM_PROVIDER", "disabled"),
        ("LLM_MODEL", "solar-pro"),
        ("LLM_BASE_URL", "https://example.invalid/v1"),
        ("LLM_MAX_CONCURRENCY", "2"),
        ("UPSTAGE_SYNTHETIC_EVALUATION_MODE", "true"),
        ("UPSTAGE_CLASSIFIER_MODE", "false"),
        ("LLM_CLASSIFIER_TIMEOUT_SECONDS", "4"),
        ("LLM_CLASSIFIER_MAX_RETRIES", "1"),
        ("LLM_CLASSIFIER_MAX_INPUT_CHARS", "1025"),
        ("LLM_CLASSIFIER_MAX_OUTPUT_TOKENS", "129"),
        ("LLM_CLASSIFIER_ATTEMPT_CAP", "21"),
        ("LLM_GENERATOR_ATTEMPT_CAP", "31"),
        ("LLM_COMBINED_ATTEMPT_CAP", "41"),
    ):
        candidate = dict(CLASSIFIER_VALID)
        candidate[key] = invalid
        assert (
            load_upstage_classifier_settings(
                environ=candidate,
                env_path=Path("missing"),
            )
            is None
        )


def test_combined_profile_rejects_every_non_exact_budget_value() -> None:
    for key, invalid in (
        ("LLM_CLASSIFIER_ATTEMPT_CAP", "79"),
        ("LLM_CLASSIFIER_ATTEMPT_CAP", "080"),
        ("LLM_GENERATOR_ATTEMPT_CAP", "101"),
        ("LLM_COMBINED_ATTEMPT_CAP", "161"),
        ("LLM_SESSION_COST_CAP_USD", "0.2"),
        ("LLM_SESSION_COST_CAP_USD", "0.200"),
        ("LLM_SESSION_COST_CAP_USD", '"0.20"'),
        ("LLM_SESSION_COST_CAP_USD", " 0.20"),
    ):
        candidate = {**COMBINED_VALID, key: invalid}

        assert (
            load_upstage_classifier_settings(
                environ=candidate,
                env_path=Path("missing"),
            )
            is None
        )
        assert load_upstage_chat_settings(environ=candidate, env_path=Path("missing")) is None


def test_invalid_combined_budget_is_rejected_before_api_key_read() -> None:
    invalid = _KeyReadFailsMapping({**COMBINED_VALID, "LLM_SESSION_COST_CAP_USD": "0.200"})

    assert load_upstage_classifier_settings(environ=invalid, env_path=Path("missing")) is None
    assert load_upstage_chat_settings(environ=invalid, env_path=Path("missing")) is None


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
    extractor_value = getattr(settings_module, "_extract_dotenv_api_key", None)
    assert callable(extractor_value), "two-phase dotenv key extraction seam is required"
    extractor = cast(Callable[[Path], str | None], extractor_value)
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


def test_duplicate_combined_cost_cap_dotenv_assignment_fails_closed(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            [
                *(f"{key}={value}" for key, value in COMBINED_VALID.items()),
                "LLM_SESSION_COST_CAP_USD=0.20",
            ]
        ),
        encoding="utf-8",
    )

    assert load_upstage_classifier_settings(environ={}, env_path=env_path) is None
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
