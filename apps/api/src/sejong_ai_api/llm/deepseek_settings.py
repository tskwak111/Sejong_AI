"""Fail-closed immutable settings for the local DeepSeek classifier lane."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import TextIO

from sejong_ai_api.llm.classifier_provider import (
    ClassifierProvider,
    load_classifier_provider,
)
from sejong_ai_api.llm.limits import LOCAL_INTERACTIVE_COST_CAP_USD

DEEPSEEK_PROVIDER = "deepseek"
DEEPSEEK_MODEL = "deepseek-v4-flash"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_TIMEOUT_SECONDS = 3.0
DEEPSEEK_MAX_RETRIES = 0
DEEPSEEK_MAX_CONCURRENCY = 1
DEEPSEEK_MAX_INPUT_CHARS = 1024
DEEPSEEK_MAX_INPUT_USAGE_TOKENS = 16384
DEEPSEEK_MAX_OUTPUT_TOKENS = 128
DEEPSEEK_TEMPERATURE = 0.0
DEEPSEEK_THINKING_ENABLED = False
DEEPSEEK_CLASSIFIER_ATTEMPT_CAP = 80
DEEPSEEK_GENERATOR_ATTEMPT_CAP = 100
DEEPSEEK_COMBINED_ATTEMPT_CAP = 160

_KEY_NAME = "DEEPSEEK_API_KEY"
_EXACT_NON_SECRET_VALUES = {
    "CLASSIFIER_PROVIDER": DEEPSEEK_PROVIDER,
    "DEEPSEEK_MODEL": DEEPSEEK_MODEL,
    "DEEPSEEK_BASE_URL": DEEPSEEK_BASE_URL,
    "UPSTAGE_SYNTHETIC_EVALUATION_MODE": "false",
    "UPSTAGE_CLASSIFIER_MODE": "false",
}
_SETTINGS_KEYS = frozenset((*_EXACT_NON_SECRET_VALUES, _KEY_NAME))


@dataclass(frozen=True, slots=True)
class DeepSeekClassifierSettings:
    """Values immutable at construction and fixed by the approved profile."""

    api_key: str = field(repr=False)
    provider: str = field(default=DEEPSEEK_PROVIDER, init=False)
    model: str = field(default=DEEPSEEK_MODEL, init=False)
    base_url: str = field(default=DEEPSEEK_BASE_URL, init=False)
    timeout_seconds: float = field(default=DEEPSEEK_TIMEOUT_SECONDS, init=False)
    max_retries: int = field(default=DEEPSEEK_MAX_RETRIES, init=False)
    max_concurrency: int = field(default=DEEPSEEK_MAX_CONCURRENCY, init=False)
    max_input_chars: int = field(default=DEEPSEEK_MAX_INPUT_CHARS, init=False)
    max_input_usage_tokens: int = field(default=DEEPSEEK_MAX_INPUT_USAGE_TOKENS, init=False)
    max_output_tokens: int = field(default=DEEPSEEK_MAX_OUTPUT_TOKENS, init=False)
    temperature: float = field(default=DEEPSEEK_TEMPERATURE, init=False)
    thinking_enabled: bool = field(default=DEEPSEEK_THINKING_ENABLED, init=False)
    classifier_attempt_cap: int = field(default=DEEPSEEK_CLASSIFIER_ATTEMPT_CAP, init=False)
    generator_attempt_cap: int = field(default=DEEPSEEK_GENERATOR_ATTEMPT_CAP, init=False)
    combined_attempt_cap: int = field(default=DEEPSEEK_COMBINED_ATTEMPT_CAP, init=False)
    session_cost_cap_usd: Decimal = field(
        default=LOCAL_INTERACTIVE_COST_CAP_USD,
        init=False,
    )


@dataclass(frozen=True, slots=True)
class _DotenvNonSecretProfile:
    values: Mapping[str, str]
    api_key_assignments: int


def load_deepseek_classifier_settings(
    *,
    environ: Mapping[str, str] | None = None,
    env_path: Path | None = None,
) -> DeepSeekClassifierSettings | None:
    """Return settings only for the exact approved DeepSeek classifier profile."""

    process_values = os.environ if environ is None else environ
    selected_env_path = env_path if env_path is not None else Path(__file__).parents[3] / ".env"
    if (
        load_classifier_provider(environ=process_values, env_path=selected_env_path)
        is not ClassifierProvider.DEEPSEEK
    ):
        return None

    api_key = _load_profile_api_key(
        environ=process_values,
        env_path=selected_env_path,
    )
    return DeepSeekClassifierSettings(api_key=api_key) if api_key is not None else None


def _load_profile_api_key(
    *,
    environ: Mapping[str, str],
    env_path: Path,
) -> str | None:
    dotenv_profile = _scan_dotenv_non_secret(env_path)
    if dotenv_profile is None:
        return None

    non_secret_values = {
        key: _merged_value(key, environ, dotenv_profile.values)
        for key in _EXACT_NON_SECRET_VALUES
    }
    if any(value is None or not _is_safe_value(value) for value in non_secret_values.values()):
        return None
    if any(
        non_secret_values[key] != expected
        for key, expected in _EXACT_NON_SECRET_VALUES.items()
    ):
        return None

    api_key: str | None
    if _KEY_NAME in environ:
        api_key = environ[_KEY_NAME]
    else:
        if dotenv_profile.api_key_assignments != 1:
            return None
        api_key = _extract_dotenv_deepseek_api_key(env_path)
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


def _extract_dotenv_deepseek_api_key(path: Path) -> str | None:
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
