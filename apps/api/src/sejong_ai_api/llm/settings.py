"""Fail-closed settings for the approved local synthetic Upstage profile."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

UPSTAGE_PROVIDER = "upstage"
UPSTAGE_MODEL = "solar-pro3"
UPSTAGE_BASE_URL = "https://api.upstage.ai/v1"
UPSTAGE_TIMEOUT_SECONDS = 15.0
UPSTAGE_MAX_RETRIES = 1
UPSTAGE_MAX_CONCURRENCY = 1
UPSTAGE_MAX_INPUT_TOKENS = 4096
UPSTAGE_MAX_OUTPUT_TOKENS = 1024
UPSTAGE_RUN_ATTEMPT_CAP = 30

_SETTINGS_KEYS = (
    "LLM_PROVIDER",
    "LLM_MODEL",
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_TIMEOUT_SECONDS",
    "LLM_MAX_RETRIES",
    "LLM_MAX_CONCURRENCY",
    "LLM_MAX_INPUT_TOKENS",
    "LLM_MAX_OUTPUT_TOKENS",
    "LLM_RUN_ATTEMPT_CAP",
    "UPSTAGE_SYNTHETIC_EVALUATION_MODE",
)

_EXACT_VALUES = {
    "LLM_PROVIDER": UPSTAGE_PROVIDER,
    "LLM_MODEL": UPSTAGE_MODEL,
    "LLM_BASE_URL": UPSTAGE_BASE_URL,
    "LLM_TIMEOUT_SECONDS": "15",
    "LLM_MAX_RETRIES": "1",
    "LLM_MAX_CONCURRENCY": "1",
    "LLM_MAX_INPUT_TOKENS": "4096",
    "LLM_MAX_OUTPUT_TOKENS": "1024",
    "LLM_RUN_ATTEMPT_CAP": "30",
    "UPSTAGE_SYNTHETIC_EVALUATION_MODE": "true",
}


@dataclass(frozen=True, slots=True)
class UpstageSyntheticSettings:
    api_key: str = field(repr=False)
    provider: str = UPSTAGE_PROVIDER
    model: str = UPSTAGE_MODEL
    base_url: str = UPSTAGE_BASE_URL
    timeout_seconds: float = UPSTAGE_TIMEOUT_SECONDS
    max_retries: int = UPSTAGE_MAX_RETRIES
    max_concurrency: int = UPSTAGE_MAX_CONCURRENCY
    max_input_tokens: int = UPSTAGE_MAX_INPUT_TOKENS
    max_output_tokens: int = UPSTAGE_MAX_OUTPUT_TOKENS
    run_attempt_cap: int = UPSTAGE_RUN_ATTEMPT_CAP


def load_upstage_synthetic_settings(
    *,
    environ: Mapping[str, str] | None = None,
    env_path: Path | None = None,
) -> UpstageSyntheticSettings | None:
    """Return settings only for the exact approved local synthetic profile."""
    process_values = os.environ if environ is None else environ
    dotenv_values = _load_dotenv(
        env_path if env_path is not None else Path(__file__).parents[3] / ".env"
    )
    if dotenv_values is None:
        return None

    values = {
        key: process_values[key] if key in process_values else dotenv_values.get(key)
        for key in _SETTINGS_KEYS
    }
    if any(value is None or not _is_safe_value(value) for value in values.values()):
        return None

    api_key = values["LLM_API_KEY"]
    if not api_key or any(values[key] != expected for key, expected in _EXACT_VALUES.items()):
        return None

    return UpstageSyntheticSettings(api_key=api_key)


def _load_dotenv(path: Path) -> dict[str, str] | None:
    if not path.is_file():
        return {}

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return None

    values: dict[str, str] = {}
    for line in lines:
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        normalized_key = key.strip()
        if not key:
            return None
        if normalized_key in _SETTINGS_KEYS:
            if not separator or key != normalized_key:
                return None
            if key in values or not _is_safe_value(value):
                return None
            values[key] = value
    return values


def _is_safe_value(value: object) -> bool:
    return (
        isinstance(value, str)
        and value == value.strip()
        and "\x00" not in value
        and "\r" not in value
        and "\n" not in value
        and "\"" not in value
        and "'" not in value
        and value.isascii()
    )
