"""Fail-closed explicit selection for local question classifiers."""

import os
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import TextIO

CLASSIFIER_PROVIDER_KEY = "CLASSIFIER_PROVIDER"


class ClassifierProvider(StrEnum):
    """The only approved classifier-provider selections."""

    DISABLED = "disabled"
    UPSTAGE = "upstage"
    DEEPSEEK = "deepseek"


def load_classifier_provider(
    *,
    environ: Mapping[str, str] | None = None,
    env_path: Path | None = None,
) -> ClassifierProvider:
    """Return an exact selection, defaulting unknown input to disabled."""

    process_values = os.environ if environ is None else environ
    selected_env_path = env_path if env_path is not None else Path(__file__).parents[3] / ".env"
    dotenv_value = _scan_dotenv_selector(selected_env_path)
    value = process_values.get(CLASSIFIER_PROVIDER_KEY, dotenv_value)
    if value is None:
        return ClassifierProvider.DISABLED
    try:
        return ClassifierProvider(value)
    except (TypeError, ValueError):
        return ClassifierProvider.DISABLED


def _scan_dotenv_selector(path: Path) -> str | None:
    if not path.is_file():
        return None

    try:
        with path.open("r", encoding="utf-8", newline=None) as stream:
            value: str | None = None
            while (assignment := _read_assignment_name(stream)) is not None:
                key, has_separator = assignment
                if key != CLASSIFIER_PROVIDER_KEY:
                    if has_separator:
                        _discard_line(stream)
                    continue
                if not has_separator or value is not None:
                    return None
                candidate = _read_line_value(stream)
                if not _is_safe_value(candidate):
                    return None
                value = candidate
    except (OSError, UnicodeDecodeError):
        return None
    return value


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
