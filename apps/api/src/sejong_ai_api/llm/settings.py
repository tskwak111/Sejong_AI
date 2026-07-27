"""Fail-closed settings for mutually exclusive local Upstage profiles."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import TextIO

from sejong_ai_api.llm.cost import RUN_COST_CAP_USD
from sejong_ai_api.llm.limits import LOCAL_INTERACTIVE_COST_CAP_USD

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

UPSTAGE_CLASSIFIER_TIMEOUT_SECONDS = 3.0
UPSTAGE_CLASSIFIER_MAX_RETRIES = 0
UPSTAGE_CLASSIFIER_MAX_INPUT_CHARS = 1024
UPSTAGE_CLASSIFIER_MAX_OUTPUT_TOKENS = 128
UPSTAGE_CLASSIFIER_ATTEMPT_CAP = 20
UPSTAGE_GENERATOR_ATTEMPT_CAP = 30
UPSTAGE_COMBINED_ATTEMPT_CAP = 40
UPSTAGE_LOCAL_INTERACTIVE_CLASSIFIER_ATTEMPT_CAP = 80
UPSTAGE_LOCAL_INTERACTIVE_GENERATOR_ATTEMPT_CAP = 100
UPSTAGE_LOCAL_INTERACTIVE_COMBINED_ATTEMPT_CAP = 160

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
    "LLM_CLASSIFIER_TIMEOUT_SECONDS",
    "LLM_CLASSIFIER_MAX_RETRIES",
    "LLM_CLASSIFIER_MAX_INPUT_CHARS",
    "LLM_CLASSIFIER_MAX_OUTPUT_TOKENS",
    "LLM_CLASSIFIER_ATTEMPT_CAP",
    "LLM_GENERATOR_ATTEMPT_CAP",
    "LLM_COMBINED_ATTEMPT_CAP",
    "LLM_SESSION_COST_CAP_USD",
    "UPSTAGE_SYNTHETIC_EVALUATION_MODE",
    "UPSTAGE_CLASSIFIER_MODE",
    "UPSTAGE_GROUNDED_CHAT_MODE",
)

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
    "UPSTAGE_CLASSIFIER_MODE": "false",
    "UPSTAGE_GROUNDED_CHAT_MODE": "false",
}
_CHAT_EXACT_VALUES = {
    **_SYNTHETIC_EXACT_VALUES,
    "LLM_TIMEOUT_SECONDS": "8",
    "LLM_MAX_RETRIES": "0",
    "UPSTAGE_SYNTHETIC_EVALUATION_MODE": "false",
    "UPSTAGE_GROUNDED_CHAT_MODE": "true",
}
_CLASSIFIER_EXACT_VALUES = {
    "LLM_PROVIDER": UPSTAGE_PROVIDER,
    "LLM_MODEL": UPSTAGE_MODEL,
    "LLM_BASE_URL": UPSTAGE_BASE_URL,
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
_COMBINED_CLASSIFIER_EXACT_VALUES = {
    **_CLASSIFIER_EXACT_VALUES,
    "UPSTAGE_GROUNDED_CHAT_MODE": "true",
    "LLM_CLASSIFIER_ATTEMPT_CAP": "80",
    "LLM_GENERATOR_ATTEMPT_CAP": "100",
    "LLM_COMBINED_ATTEMPT_CAP": "160",
    "LLM_SESSION_COST_CAP_USD": "0.20",
}
_COMBINED_CHAT_EXACT_VALUES = {
    **_CHAT_EXACT_VALUES,
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


@dataclass(frozen=True, slots=True)
class UpstageClassifierSettings:
    api_key: str = field(repr=False)
    provider: str = UPSTAGE_PROVIDER
    model: str = UPSTAGE_MODEL
    base_url: str = UPSTAGE_BASE_URL
    timeout_seconds: float = UPSTAGE_CLASSIFIER_TIMEOUT_SECONDS
    max_retries: int = UPSTAGE_CLASSIFIER_MAX_RETRIES
    max_concurrency: int = UPSTAGE_MAX_CONCURRENCY
    max_input_chars: int = UPSTAGE_CLASSIFIER_MAX_INPUT_CHARS
    max_output_tokens: int = UPSTAGE_CLASSIFIER_MAX_OUTPUT_TOKENS
    classifier_attempt_cap: int = UPSTAGE_CLASSIFIER_ATTEMPT_CAP
    generator_attempt_cap: int = UPSTAGE_GENERATOR_ATTEMPT_CAP
    combined_attempt_cap: int = UPSTAGE_COMBINED_ATTEMPT_CAP
    session_cost_cap_usd: Decimal = RUN_COST_CAP_USD


@dataclass(frozen=True, slots=True)
class _DotenvNonSecretProfile:
    values: Mapping[str, str]
    api_key_assignments: int


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
    for expected_values in (
        _CHAT_EXACT_VALUES,
        _COMBINED_CHAT_EXACT_VALUES,
    ):
        api_key = _load_profile_api_key(
            expected_values=expected_values,
            environ=environ,
            env_path=env_path,
        )
        if api_key is not None:
            return UpstageChatSettings(api_key=api_key)
    return None


def load_upstage_classifier_settings(
    *,
    environ: Mapping[str, str] | None = None,
    env_path: Path | None = None,
) -> UpstageClassifierSettings | None:
    """Return settings only for an exact classifier-only or combined profile."""

    for expected_values in (
        _CLASSIFIER_EXACT_VALUES,
        _COMBINED_CLASSIFIER_EXACT_VALUES,
    ):
        api_key = _load_profile_api_key(
            expected_values=expected_values,
            environ=environ,
            env_path=env_path,
        )
        if api_key is not None:
            return UpstageClassifierSettings(
                api_key=api_key,
                classifier_attempt_cap=int(expected_values["LLM_CLASSIFIER_ATTEMPT_CAP"]),
                generator_attempt_cap=int(expected_values["LLM_GENERATOR_ATTEMPT_CAP"]),
                combined_attempt_cap=int(expected_values["LLM_COMBINED_ATTEMPT_CAP"]),
                session_cost_cap_usd=(
                    LOCAL_INTERACTIVE_COST_CAP_USD
                    if "LLM_SESSION_COST_CAP_USD" in expected_values
                    else RUN_COST_CAP_USD
                ),
            )
    return None


def _load_profile_api_key(
    *,
    expected_values: Mapping[str, str],
    environ: Mapping[str, str] | None,
    env_path: Path | None,
) -> str | None:
    process_values = os.environ if environ is None else environ
    selected_env_path = env_path if env_path is not None else Path(__file__).parents[3] / ".env"
    dotenv_profile = _scan_dotenv_non_secret(selected_env_path)
    if dotenv_profile is None:
        return None

    non_secret_values = {
        key: _merged_value(key, process_values, dotenv_profile.values) for key in expected_values
    }
    if any(value is None or not _is_safe_value(value) for value in non_secret_values.values()):
        return None
    if any(non_secret_values[key] != expected for key, expected in expected_values.items()):
        return None

    api_key: str | None
    if _KEY_NAME in process_values:
        api_key = process_values[_KEY_NAME]
    else:
        if dotenv_profile.api_key_assignments != 1:
            return None
        api_key = _extract_dotenv_api_key(selected_env_path)
    if not _is_safe_value(api_key) or not api_key:
        return None
    return api_key


def _merged_value(
    key: str,
    process_values: Mapping[str, str],
    dotenv_values: Mapping[str, str],
) -> str | None:
    return process_values[key] if key in process_values else dotenv_values.get(key)


def _scan_dotenv_non_secret(path: Path) -> _DotenvNonSecretProfile | None:
    if not path.is_file():
        return _DotenvNonSecretProfile(values={}, api_key_assignments=0)

    try:
        with path.open("r", encoding="utf-8", newline=None) as stream:
            values: dict[str, str] = {}
            api_key_assignments = 0
            while (assignment := _read_assignment_name(stream)) is not None:
                key, has_separator = assignment
                normalized_key = key.strip()
                if not key:
                    if has_separator:
                        return None
                    continue
                if normalized_key not in _SETTINGS_KEYS:
                    if has_separator:
                        _discard_line(stream)
                    continue
                if not has_separator or key != normalized_key:
                    return None
                if key == _KEY_NAME:
                    api_key_assignments += 1
                    if api_key_assignments > 1:
                        return None
                    _discard_line(stream)
                    continue
                value = _read_line_value(stream)
                if key in values or not _is_safe_value(value):
                    return None
                values[key] = value
    except (OSError, UnicodeDecodeError):
        return None
    return _DotenvNonSecretProfile(
        values=values,
        api_key_assignments=api_key_assignments,
    )


def _extract_dotenv_api_key(path: Path) -> str | None:
    if not path.is_file():
        return None

    try:
        with path.open("r", encoding="utf-8", newline=None) as stream:
            api_key: str | None = None
            while (assignment := _read_assignment_name(stream)) is not None:
                key, has_separator = assignment
                if not has_separator:
                    continue
                if key == _KEY_NAME:
                    if api_key is not None:
                        return None
                    api_key = _read_line_value(stream)
                else:
                    _discard_line(stream)
    except (OSError, UnicodeDecodeError):
        return None
    return api_key


def _read_assignment_name(stream: TextIO) -> tuple[str, bool] | None:
    characters: list[str] = []
    while True:
        character = stream.read(1)
        if character == "":
            return ("".join(characters), False) if characters else None
        if character == "\n":
            return ("".join(characters), False)
        if character == "=":
            return ("".join(characters), True)
        characters.append(character)


def _read_line_value(stream: TextIO) -> str:
    characters: list[str] = []
    while True:
        character = stream.read(1)
        if character in ("", "\n"):
            return "".join(characters)
        characters.append(character)


def _discard_line(stream: TextIO) -> None:
    while stream.read(1) not in ("", "\n"):
        pass


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
