"""Fail-closed settings for mutually exclusive local Upstage profiles."""

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

UPSTAGE_CHAT_TIMEOUT_SECONDS = 8.0
UPSTAGE_CHAT_MAX_RETRIES = 0

_KEY_NAME = "LLM_API_KEY"
_SETTINGS_KEYS = (
    "LLM_PROVIDER",
    "LLM_MODEL",
    _KEY_NAME,
    "LLM_BASE_URL",
    "LLM_TIMEOUT_SECONDS",
    "LLM_MAX_RETRIES",
    "LLM_MAX_CONCURRENCY",
    "LLM_MAX_INPUT_TOKENS",
    "LLM_MAX_OUTPUT_TOKENS",
    "LLM_RUN_ATTEMPT_CAP",
    "UPSTAGE_SYNTHETIC_EVALUATION_MODE",
    "UPSTAGE_GROUNDED_CHAT_MODE",
)
_NON_SECRET_SETTINGS_KEYS = tuple(key for key in _SETTINGS_KEYS if key != _KEY_NAME)

_SYNTHETIC_EXACT_VALUES = {
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
    "UPSTAGE_GROUNDED_CHAT_MODE": "false",
}
_CHAT_EXACT_VALUES = {
    **_SYNTHETIC_EXACT_VALUES,
    "LLM_TIMEOUT_SECONDS": "8",
    "LLM_MAX_RETRIES": "0",
    "UPSTAGE_SYNTHETIC_EVALUATION_MODE": "false",
    "UPSTAGE_GROUNDED_CHAT_MODE": "true",
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


@dataclass(frozen=True, slots=True)
class UpstageChatSettings:
    api_key: str = field(repr=False)
    provider: str = UPSTAGE_PROVIDER
    model: str = UPSTAGE_MODEL
    base_url: str = UPSTAGE_BASE_URL
    timeout_seconds: float = UPSTAGE_CHAT_TIMEOUT_SECONDS
    max_retries: int = UPSTAGE_CHAT_MAX_RETRIES
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
    api_key = _load_profile_api_key(
        expected_values=_SYNTHETIC_EXACT_VALUES,
        environ=environ,
        env_path=env_path,
    )
    return UpstageSyntheticSettings(api_key=api_key) if api_key is not None else None


def load_upstage_chat_settings(
    *,
    environ: Mapping[str, str] | None = None,
    env_path: Path | None = None,
) -> UpstageChatSettings | None:
    """Return settings only for the exact local grounded-chat profile."""
    api_key = _load_profile_api_key(
        expected_values=_CHAT_EXACT_VALUES,
        environ=environ,
        env_path=env_path,
    )
    return UpstageChatSettings(api_key=api_key) if api_key is not None else None


def _load_profile_api_key(
    *,
    expected_values: Mapping[str, str],
    environ: Mapping[str, str] | None,
    env_path: Path | None,
) -> str | None:
    process_values = os.environ if environ is None else environ
    dotenv_values = _load_dotenv(
        env_path if env_path is not None else Path(__file__).parents[3] / ".env"
    )
    if dotenv_values is None:
        return None

    non_secret_values = {
        key: _merged_value(key, process_values, dotenv_values) for key in _NON_SECRET_SETTINGS_KEYS
    }
    if any(value is None or not _is_safe_value(value) for value in non_secret_values.values()):
        return None
    if any(non_secret_values[key] != expected for key, expected in expected_values.items()):
        return None

    api_key = _merged_value(_KEY_NAME, process_values, dotenv_values)
    if not _is_safe_value(api_key) or not api_key:
        return None
    return api_key


def _merged_value(
    key: str,
    process_values: Mapping[str, str],
    dotenv_values: Mapping[str, str],
) -> str | None:
    return process_values[key] if key in process_values else dotenv_values.get(key)


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
        and '"' not in value
        and "'" not in value
        and value.isascii()
    )
