"""Duplicate-rejecting JSON boundary shared by provider adapters."""

from __future__ import annotations

import json
from typing import Any


class DuplicateJsonKeyError(ValueError):
    """Raised without reflecting a duplicate provider-controlled key."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKeyError("JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def load_strict_json_bytes(payload: bytes) -> Any:
    """Decode one UTF-8 JSON value while rejecting duplicate keys recursively."""

    if type(payload) is not bytes:
        raise ValueError("JSON_BYTES_REQUIRED")
    return json.loads(
        payload.decode("utf-8"),
        object_pairs_hook=_unique_object,
    )


__all__ = ["DuplicateJsonKeyError", "load_strict_json_bytes"]
