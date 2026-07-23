from collections.abc import Mapping
from pathlib import Path
from typing import cast

from sejong_ai_api.llm.settings import UpstageSyntheticSettings, load_upstage_synthetic_settings

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
