from pathlib import Path

import pytest

DEEPSEEK_VALID = {
    "CLASSIFIER_PROVIDER": "deepseek",
    "DEEPSEEK_API_KEY": "deepseek-test-key-not-a-real-secret",
    "DEEPSEEK_MODEL": "deepseek-v4-flash",
    "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
    "UPSTAGE_SYNTHETIC_EVALUATION_MODE": "false",
    "UPSTAGE_CLASSIFIER_MODE": "false",
    "UPSTAGE_GROUNDED_CHAT_MODE": "false",
}


def test_classifier_provider_selector_defaults_disabled_and_accepts_only_exact_values() -> None:
    from sejong_ai_api.llm.classifier_provider import (
        ClassifierProvider,
        load_classifier_provider,
    )

    assert (
        load_classifier_provider(environ={}, env_path=Path("missing"))
        is ClassifierProvider.DISABLED
    )
    assert (
        load_classifier_provider(
            environ={"CLASSIFIER_PROVIDER": "upstage"},
            env_path=Path("missing"),
        )
        is ClassifierProvider.UPSTAGE
    )
    assert (
        load_classifier_provider(
            environ={"CLASSIFIER_PROVIDER": "deepseek"},
            env_path=Path("missing"),
        )
        is ClassifierProvider.DEEPSEEK
    )

    for invalid in ("", "DeepSeek", "fallback", "upstage ", " deepseek"):
        assert (
            load_classifier_provider(
                environ={"CLASSIFIER_PROVIDER": invalid},
                env_path=Path("missing"),
            )
            is ClassifierProvider.DISABLED
        )


def test_exact_deepseek_classifier_settings_expose_only_fixed_profile_limits() -> None:
    from sejong_ai_api.llm.deepseek_settings import (
        DeepSeekClassifierSettings,
        load_deepseek_classifier_settings,
    )

    settings = load_deepseek_classifier_settings(
        environ=DEEPSEEK_VALID,
        env_path=Path("missing"),
    )

    assert isinstance(settings, DeepSeekClassifierSettings)
    assert settings.provider == "deepseek"
    assert settings.model == "deepseek-v4-flash"
    assert settings.base_url == "https://api.deepseek.com"
    assert settings.timeout_seconds == 3.0
    assert settings.max_retries == 0
    assert settings.max_concurrency == 1
    assert settings.max_input_chars == 1024
    assert settings.max_input_usage_tokens == 16384
    assert settings.max_output_tokens == 128
    assert settings.temperature == 0.0
    assert settings.thinking_enabled is False
    assert settings.classifier_attempt_cap == 80
    assert settings.generator_attempt_cap == 100
    assert settings.combined_attempt_cap == 160
    assert str(settings.session_cost_cap_usd) == "0.20"
    assert DEEPSEEK_VALID["DEEPSEEK_API_KEY"] not in repr(settings)


def test_deepseek_settings_reject_conflicts_without_reading_any_provider_key() -> None:
    from sejong_ai_api.llm.deepseek_settings import load_deepseek_classifier_settings

    for key, invalid in (
        ("CLASSIFIER_PROVIDER", "upstage"),
        ("DEEPSEEK_MODEL", "deepseek-v3"),
        ("DEEPSEEK_BASE_URL", "https://example.invalid"),
        ("UPSTAGE_SYNTHETIC_EVALUATION_MODE", "true"),
        ("UPSTAGE_CLASSIFIER_MODE", "true"),
    ):
        candidate = {**DEEPSEEK_VALID, key: invalid}
        assert (
            load_deepseek_classifier_settings(
                environ=candidate,
                env_path=Path("missing"),
            )
            is None
        )

    invalid = _ProviderKeyReadFailsMapping(
        {**DEEPSEEK_VALID, "DEEPSEEK_MODEL": "deepseek-v3"}
    )
    assert load_deepseek_classifier_settings(environ=invalid, env_path=Path("missing")) is None


def test_deepseek_and_valid_upstage_generator_profiles_remain_independent() -> None:
    from sejong_ai_api.llm.deepseek_settings import load_deepseek_classifier_settings
    from sejong_ai_api.llm.settings import UpstageChatSettings, load_upstage_chat_settings

    profile = {
        **DEEPSEEK_VALID,
        "LLM_PROVIDER": "upstage",
        "LLM_API_KEY": "upstage-test-key-not-a-real-secret",
        "LLM_MODEL": "solar-pro3",
        "LLM_BASE_URL": "https://api.upstage.ai/v1",
        "LLM_TIMEOUT_SECONDS": "8",
        "LLM_MAX_RETRIES": "0",
        "LLM_MAX_CONCURRENCY": "1",
        "LLM_MAX_INPUT_TOKENS": "4096",
        "LLM_MAX_OUTPUT_TOKENS": "1024",
        "LLM_RUN_ATTEMPT_CAP": "30",
        "UPSTAGE_GROUNDED_CHAT_MODE": "true",
    }

    deepseek = load_deepseek_classifier_settings(environ=profile, env_path=Path("missing"))
    upstage_chat = load_upstage_chat_settings(environ=profile, env_path=Path("missing"))

    assert deepseek is not None
    assert isinstance(upstage_chat, UpstageChatSettings)


def test_incomplete_grounded_generator_fails_before_llm_api_key_access() -> None:
    from sejong_ai_api.llm.deepseek_settings import load_deepseek_classifier_settings

    incomplete_generator = _UpstageKeyReadFailsMapping(
        {
            **DEEPSEEK_VALID,
            "UPSTAGE_GROUNDED_CHAT_MODE": "true",
            "LLM_PROVIDER": "upstage",
        }
    )

    assert (
        load_deepseek_classifier_settings(
            environ=incomplete_generator,
            env_path=Path("missing"),
        )
        is None
    )


def test_deepseek_loader_reads_no_upstage_key_and_upstage_loader_reads_no_deepseek_key() -> None:
    from sejong_ai_api.llm.deepseek_settings import load_deepseek_classifier_settings
    from sejong_ai_api.llm.settings import load_upstage_chat_settings

    deepseek = load_deepseek_classifier_settings(
        environ=_UpstageKeyReadFailsMapping(DEEPSEEK_VALID),
        env_path=Path("missing"),
    )
    upstage_chat = load_upstage_chat_settings(
        environ=_DeepSeekKeyReadFailsMapping(
            {
                "LLM_PROVIDER": "upstage",
                "LLM_API_KEY": "upstage-test-key-not-a-real-secret",
                "LLM_MODEL": "solar-pro3",
                "LLM_BASE_URL": "https://api.upstage.ai/v1",
                "LLM_TIMEOUT_SECONDS": "8",
                "LLM_MAX_RETRIES": "0",
                "LLM_MAX_CONCURRENCY": "1",
                "LLM_MAX_INPUT_TOKENS": "4096",
                "LLM_MAX_OUTPUT_TOKENS": "1024",
                "LLM_RUN_ATTEMPT_CAP": "30",
                "UPSTAGE_SYNTHETIC_EVALUATION_MODE": "false",
                "UPSTAGE_CLASSIFIER_MODE": "false",
                "UPSTAGE_GROUNDED_CHAT_MODE": "true",
            }
        ),
        env_path=Path("missing"),
    )

    assert deepseek is not None
    assert upstage_chat is not None


def test_deepseek_dotenv_extracts_key_only_after_exact_non_secret_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sejong_ai_api.llm import deepseek_settings

    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(f"{key}={value}" for key, value in DEEPSEEK_VALID.items()),
        encoding="utf-8",
    )
    extractor = deepseek_settings._extract_dotenv_deepseek_api_key
    calls: list[Path] = []

    def observed_extract(path: Path) -> str | None:
        calls.append(path)
        return extractor(path)

    monkeypatch.setattr(deepseek_settings, "_extract_dotenv_deepseek_api_key", observed_extract)

    settings = deepseek_settings.load_deepseek_classifier_settings(
        environ={},
        env_path=env_path,
    )

    assert settings is not None
    assert calls == [env_path]


def test_invalid_deepseek_dotenv_profile_never_enters_key_extraction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sejong_ai_api.llm import deepseek_settings

    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            f"{key}={value}"
            for key, value in {**DEEPSEEK_VALID, "DEEPSEEK_MODEL": "deepseek-v3"}.items()
        ),
        encoding="utf-8",
    )

    def fail_if_called(_path: Path) -> str:
        raise AssertionError("key must not be extracted before non-secret validation")

    monkeypatch.setattr(
        deepseek_settings,
        "_extract_dotenv_deepseek_api_key",
        fail_if_called,
    )

    assert (
        deepseek_settings.load_deepseek_classifier_settings(environ={}, env_path=env_path)
        is None
    )


class _ProviderKeyReadFailsMapping(dict[str, str]):
    def __getitem__(self, key: str) -> str:
        if key in {"DEEPSEEK_API_KEY", "LLM_API_KEY"}:
            raise AssertionError("provider keys must not be read before non-secret validation")
        return super().__getitem__(key)

    def __contains__(self, key: object) -> bool:
        return True if key in {"DEEPSEEK_API_KEY", "LLM_API_KEY"} else super().__contains__(key)


class _UpstageKeyReadFailsMapping(dict[str, str]):
    def __getitem__(self, key: str) -> str:
        if key == "LLM_API_KEY":
            raise AssertionError("DeepSeek settings must not read the Upstage key")
        return super().__getitem__(key)

    def __contains__(self, key: object) -> bool:
        return True if key == "LLM_API_KEY" else super().__contains__(key)


class _DeepSeekKeyReadFailsMapping(dict[str, str]):
    def __getitem__(self, key: str) -> str:
        if key == "DEEPSEEK_API_KEY":
            raise AssertionError("Upstage settings must not read the DeepSeek key")
        return super().__getitem__(key)

    def __contains__(self, key: object) -> bool:
        return True if key == "DEEPSEEK_API_KEY" else super().__contains__(key)
