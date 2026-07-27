"""Closed, source-free contracts for the optional intent classifier."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from sejong_ai_api.db.models import Intent

_EXPECTED_KEYS = frozenset({"route", "intent", "topic_id", "pending_slot"})
_TOPIC_ID_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,63}$")
_SUPPORTED_INTENTS = frozenset(
    {
        Intent.MOVE_IN_RESIDENT_REGISTRATION,
        Intent.CERTIFICATE_ISSUANCE,
        Intent.BULKY_WASTE,
        Intent.LOCAL_TAX_GENERAL,
    }
)


class ClassifierRoute(str, Enum):  # noqa: UP042 - approved public enum shape
    SUPPORTED = "SUPPORTED"
    CIVIC_SCOPE_GAP = "CIVIC_SCOPE_GAP"
    NON_CIVIC = "NON_CIVIC"
    NEEDS_FOLLOWUP = "NEEDS_FOLLOWUP"


class PendingSlot(str, Enum):  # noqa: UP042 - approved public enum shape
    CERTIFICATE_KIND = "CERTIFICATE_KIND"
    REGION = "REGION"
    WASTE_ITEM = "WASTE_ITEM"


@dataclass(frozen=True, slots=True)
class ClassifierDecision:
    """Validated provider-neutral decision that cannot contain an answer or source."""

    route: ClassifierRoute
    intent: Intent | None
    topic_id: str | None
    pending_slot: PendingSlot | None

    def __post_init__(self) -> None:
        try:
            self._validate()
        except (TypeError, ValueError) as error:
            raise ValueError("CLASSIFIER_DECISION_INVALID") from error

    def _validate(self) -> None:
        if type(self.route) is not ClassifierRoute:
            raise ValueError
        if self.intent is not None and type(self.intent) is not Intent:
            raise ValueError
        if self.topic_id is not None and (
            type(self.topic_id) is not str or _TOPIC_ID_PATTERN.fullmatch(self.topic_id) is None
        ):
            raise ValueError
        if self.pending_slot is not None and type(self.pending_slot) is not PendingSlot:
            raise ValueError

        if self.route is ClassifierRoute.SUPPORTED:
            if self.intent not in _SUPPORTED_INTENTS or self.pending_slot is not None:
                raise ValueError
            return

        if self.route in {
            ClassifierRoute.CIVIC_SCOPE_GAP,
            ClassifierRoute.NON_CIVIC,
        }:
            if any(value is not None for value in (self.intent, self.topic_id, self.pending_slot)):
                raise ValueError
            return

        if (
            self.route is not ClassifierRoute.NEEDS_FOLLOWUP
            or self.intent not in _SUPPORTED_INTENTS
            or self.pending_slot is None
        ):
            raise ValueError
        if (
            self.pending_slot is PendingSlot.CERTIFICATE_KIND
            and self.intent is not Intent.CERTIFICATE_ISSUANCE
        ):
            raise ValueError
        if self.pending_slot is PendingSlot.WASTE_ITEM and self.intent is not Intent.BULKY_WASTE:
            raise ValueError


def parse_classifier_decision(payload: bytes) -> ClassifierDecision:
    """Parse a provider response without reflecting its content on failure."""

    try:
        if type(payload) is not bytes:
            raise ValueError
        raw: Any = json.loads(payload.decode("utf-8"))
        if type(raw) is not dict or frozenset(raw) != _EXPECTED_KEYS:
            raise ValueError
        route_raw = raw["route"]
        intent_raw = raw["intent"]
        topic_id = raw["topic_id"]
        slot_raw = raw["pending_slot"]
        if type(route_raw) is not str:
            raise ValueError
        if intent_raw is not None and type(intent_raw) is not str:
            raise ValueError
        if topic_id is not None and type(topic_id) is not str:
            raise ValueError
        if slot_raw is not None and type(slot_raw) is not str:
            raise ValueError

        return ClassifierDecision(
            route=ClassifierRoute(route_raw),
            intent=Intent(intent_raw) if intent_raw is not None else None,
            topic_id=topic_id,
            pending_slot=PendingSlot(slot_raw) if slot_raw is not None else None,
        )
    except (KeyError, TypeError, UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError("CLASSIFIER_DECISION_INVALID") from error


__all__ = [
    "ClassifierDecision",
    "ClassifierRoute",
    "PendingSlot",
    "parse_classifier_decision",
]
