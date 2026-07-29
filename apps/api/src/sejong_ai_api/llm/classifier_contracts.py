"""Closed, source-free contracts for the optional intent classifier."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any

from sejong_ai_api.chat.topic_catalog import TopicCatalog
from sejong_ai_api.db.models import Intent
from sejong_ai_api.llm.classifier_diagnostics import ClassifierResponseStage
from sejong_ai_api.llm.strict_json import load_strict_json_bytes

_EXPECTED_KEYS = frozenset({"route", "intent", "topic_id", "coverage_id", "pending_slot"})
_NONE_SENTINEL = "NONE"
_NULLABLE_FIELDS = ("intent", "topic_id", "coverage_id", "pending_slot")
_IDENTIFIER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,63}$")
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
    NO_TOPIC_MATCH = "NO_TOPIC_MATCH"
    CIVIC_SCOPE_GAP = "CIVIC_SCOPE_GAP"
    NON_CIVIC = "NON_CIVIC"
    NEEDS_FOLLOWUP = "NEEDS_FOLLOWUP"


class PendingSlot(str, Enum):  # noqa: UP042 - approved public enum shape
    DOMAIN = "DOMAIN"
    TOPIC_CHOICE = "TOPIC_CHOICE"
    CERTIFICATE_KIND = "CERTIFICATE_KIND"
    REGION = "REGION"
    WASTE_ITEM = "WASTE_ITEM"


@dataclass(frozen=True, slots=True)
class ClassifierDecision:
    """Validated provider-neutral decision that cannot contain an answer or source."""

    route: ClassifierRoute
    intent: Intent | None
    topic_id: str | None
    coverage_id: str | None
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
            type(self.topic_id) is not str or _IDENTIFIER_PATTERN.fullmatch(self.topic_id) is None
        ):
            raise ValueError
        if self.coverage_id is not None and (
            type(self.coverage_id) is not str
            or _IDENTIFIER_PATTERN.fullmatch(self.coverage_id) is None
        ):
            raise ValueError
        if self.pending_slot is not None and type(self.pending_slot) is not PendingSlot:
            raise ValueError

        if self.route is ClassifierRoute.SUPPORTED:
            if (
                self.intent not in _SUPPORTED_INTENTS
                or self.topic_id is None
                or self.coverage_id is None
                or self.pending_slot is not None
            ):
                raise ValueError
            return

        if self.route is ClassifierRoute.NO_TOPIC_MATCH:
            if self.intent not in _SUPPORTED_INTENTS or any(
                value is not None for value in (self.topic_id, self.coverage_id, self.pending_slot)
            ):
                raise ValueError
            return

        if self.route in {
            ClassifierRoute.CIVIC_SCOPE_GAP,
            ClassifierRoute.NON_CIVIC,
        }:
            if any(
                value is not None
                for value in (
                    self.intent,
                    self.topic_id,
                    self.coverage_id,
                    self.pending_slot,
                )
            ):
                raise ValueError
            return

        if self.route is not ClassifierRoute.NEEDS_FOLLOWUP or self.pending_slot is None:
            raise ValueError
        if self.topic_id is not None or self.coverage_id is not None:
            raise ValueError
        if self.pending_slot is PendingSlot.DOMAIN:
            if self.intent is not None:
                raise ValueError
            return
        if self.intent not in _SUPPORTED_INTENTS:
            raise ValueError
        if (
            self.pending_slot is PendingSlot.CERTIFICATE_KIND
            and self.intent is not Intent.CERTIFICATE_ISSUANCE
        ):
            raise ValueError
        if self.pending_slot is PendingSlot.WASTE_ITEM and self.intent is not Intent.BULKY_WASTE:
            raise ValueError


@dataclass(frozen=True, slots=True)
class ClassifierDecisionParseResult:
    """A closed decision or one value-free terminal validation stage."""

    decision: ClassifierDecision | None
    stage: ClassifierResponseStage


def _build_classifier_decision_with_stage(
    *,
    route_raw: str,
    intent_raw: str | None,
    topic_id: str | None,
    coverage_id: str | None,
    slot_raw: str | None,
) -> ClassifierDecisionParseResult:
    try:
        route = ClassifierRoute(route_raw)
    except ValueError:
        return ClassifierDecisionParseResult(
            None,
            ClassifierResponseStage.ROUTE_ENUM_REJECTED,
        )

    intent: Intent | None = None
    if intent_raw is not None:
        try:
            intent = Intent(intent_raw)
        except ValueError:
            return ClassifierDecisionParseResult(
                None,
                ClassifierResponseStage.INTENT_ENUM_REJECTED,
            )
        if intent not in _SUPPORTED_INTENTS:
            return ClassifierDecisionParseResult(
                None,
                ClassifierResponseStage.INTENT_ENUM_REJECTED,
            )

    pending_slot: PendingSlot | None = None
    if slot_raw is not None:
        try:
            pending_slot = PendingSlot(slot_raw)
        except ValueError:
            return ClassifierDecisionParseResult(
                None,
                ClassifierResponseStage.PENDING_SLOT_ENUM_REJECTED,
            )

    if (topic_id is not None and _IDENTIFIER_PATTERN.fullmatch(topic_id) is None) or (
        coverage_id is not None and _IDENTIFIER_PATTERN.fullmatch(coverage_id) is None
    ):
        return ClassifierDecisionParseResult(
            None,
            ClassifierResponseStage.IDENTIFIER_SHAPE_REJECTED,
        )

    try:
        decision = ClassifierDecision(
            route=route,
            intent=intent,
            topic_id=topic_id,
            coverage_id=coverage_id,
            pending_slot=pending_slot,
        )
    except (TypeError, ValueError):
        return ClassifierDecisionParseResult(
            None,
            ClassifierResponseStage.ROUTE_SHAPE_REJECTED,
        )
    return ClassifierDecisionParseResult(
        decision,
        ClassifierResponseStage.ACCEPTED,
    )


def parse_classifier_wire_decision_with_stage(
    payload: bytes,
    catalog: TopicCatalog,
) -> ClassifierDecisionParseResult:
    """Parse the all-string provider wire without reflecting provider values."""

    return _parse_classifier_payload_with_stage(
        payload,
        catalog,
        wire_strings=True,
    )


def parse_classifier_decision_with_stage(
    payload: bytes,
    catalog: TopicCatalog,
) -> ClassifierDecisionParseResult:
    """Parse a canonical JSON-null decision without reflecting provider values."""

    return _parse_classifier_payload_with_stage(
        payload,
        catalog,
        wire_strings=False,
    )


def _parse_classifier_payload_with_stage(
    payload: bytes,
    catalog: TopicCatalog,
    *,
    wire_strings: bool,
) -> ClassifierDecisionParseResult:
    """Validate one closed decision after optional provider-wire normalization."""

    if type(payload) is not bytes or type(catalog) is not TopicCatalog:
        return ClassifierDecisionParseResult(
            decision=None,
            stage=ClassifierResponseStage.JSON_REJECTED,
        )
    try:
        raw: Any = load_strict_json_bytes(payload)
    except (UnicodeDecodeError, ValueError):
        return ClassifierDecisionParseResult(
            decision=None,
            stage=ClassifierResponseStage.JSON_REJECTED,
        )
    if type(raw) is not dict or frozenset(raw) != _EXPECTED_KEYS:
        return ClassifierDecisionParseResult(
            decision=None,
            stage=ClassifierResponseStage.KEY_SET_REJECTED,
        )

    if wire_strings:
        if any(type(raw[field]) is not str for field in _EXPECTED_KEYS):
            return ClassifierDecisionParseResult(
                decision=None,
                stage=ClassifierResponseStage.FIELD_TYPE_REJECTED,
            )
        normalized = dict(raw)
        for field in _NULLABLE_FIELDS:
            if normalized[field] == _NONE_SENTINEL:
                normalized[field] = None
        raw = normalized

    route_raw = raw["route"]
    intent_raw = raw["intent"]
    topic_id = raw["topic_id"]
    coverage_id = raw["coverage_id"]
    slot_raw = raw["pending_slot"]
    if (
        type(route_raw) is not str
        or (intent_raw is not None and type(intent_raw) is not str)
        or (topic_id is not None and type(topic_id) is not str)
        or (coverage_id is not None and type(coverage_id) is not str)
        or (slot_raw is not None and type(slot_raw) is not str)
    ):
        return ClassifierDecisionParseResult(
            decision=None,
            stage=ClassifierResponseStage.FIELD_TYPE_REJECTED,
        )

    result = _build_classifier_decision_with_stage(
        route_raw=route_raw,
        intent_raw=intent_raw,
        topic_id=topic_id,
        coverage_id=coverage_id,
        slot_raw=slot_raw,
    )
    if result.decision is None:
        return result
    decision = result.decision

    if decision.route is ClassifierRoute.SUPPORTED:
        selected_topic_id = decision.topic_id
        selected_coverage_id = decision.coverage_id
        topic = catalog.find(selected_topic_id or "")
        if (
            selected_topic_id is None
            or selected_coverage_id is None
            or topic is None
            or topic.record.category is not decision.intent
            or topic.coverage.coverage_id != selected_coverage_id
        ):
            return ClassifierDecisionParseResult(
                decision=None,
                stage=ClassifierResponseStage.CATALOG_REJECTED,
            )
    return ClassifierDecisionParseResult(
        decision=decision,
        stage=ClassifierResponseStage.ACCEPTED,
    )


def parse_classifier_decision(
    payload: bytes,
    catalog: TopicCatalog,
) -> ClassifierDecision:
    """Parse a provider response without reflecting its content on failure."""

    result = parse_classifier_decision_with_stage(payload, catalog)
    if result.decision is None:
        raise ValueError("CLASSIFIER_DECISION_INVALID")
    return result.decision


__all__ = [
    "ClassifierDecision",
    "ClassifierDecisionParseResult",
    "ClassifierRoute",
    "PendingSlot",
    "parse_classifier_decision",
    "parse_classifier_decision_with_stage",
    "parse_classifier_wire_decision_with_stage",
]
