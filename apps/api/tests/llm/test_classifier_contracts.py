from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from sejong_ai_api.db.models import Intent
from sejong_ai_api.llm.classifier_contracts import (
    ClassifierDecision,
    ClassifierRoute,
    PendingSlot,
    parse_classifier_decision,
)


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (
            b'{"route":"SUPPORTED","intent":"CERTIFICATE_ISSUANCE",'
            b'"topic_id":"KB-CERT-01","pending_slot":null}',
            ClassifierDecision(
                route=ClassifierRoute.SUPPORTED,
                intent=Intent.CERTIFICATE_ISSUANCE,
                topic_id="KB-CERT-01",
                pending_slot=None,
            ),
        ),
        (
            b'{"route":"CIVIC_SCOPE_GAP","intent":null,"topic_id":null,"pending_slot":null}',
            ClassifierDecision(
                route=ClassifierRoute.CIVIC_SCOPE_GAP,
                intent=None,
                topic_id=None,
                pending_slot=None,
            ),
        ),
        (
            b'{"route":"NON_CIVIC","intent":null,"topic_id":null,"pending_slot":null}',
            ClassifierDecision(
                route=ClassifierRoute.NON_CIVIC,
                intent=None,
                topic_id=None,
                pending_slot=None,
            ),
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"CERTIFICATE_ISSUANCE",'
            b'"topic_id":null,"pending_slot":"CERTIFICATE_KIND"}',
            ClassifierDecision(
                route=ClassifierRoute.NEEDS_FOLLOWUP,
                intent=Intent.CERTIFICATE_ISSUANCE,
                topic_id=None,
                pending_slot=PendingSlot.CERTIFICATE_KIND,
            ),
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"BULKY_WASTE",'
            b'"topic_id":null,"pending_slot":"WASTE_ITEM"}',
            ClassifierDecision(
                route=ClassifierRoute.NEEDS_FOLLOWUP,
                intent=Intent.BULKY_WASTE,
                topic_id=None,
                pending_slot=PendingSlot.WASTE_ITEM,
            ),
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"MOVE_IN_RESIDENT_REGISTRATION",'
            b'"topic_id":null,"pending_slot":"REGION"}',
            ClassifierDecision(
                route=ClassifierRoute.NEEDS_FOLLOWUP,
                intent=Intent.MOVE_IN_RESIDENT_REGISTRATION,
                topic_id=None,
                pending_slot=PendingSlot.REGION,
            ),
        ),
    ],
)
def test_parse_classifier_decision_accepts_only_closed_valid_shapes(
    payload: bytes,
    expected: ClassifierDecision,
) -> None:
    assert parse_classifier_decision(payload) == expected


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        b"[]",
        (
            b'{"route":"SUPPORTED","intent":"CERTIFICATE_ISSUANCE",'
            b'"topic_id":null,"pending_slot":null,"answer":"invented"}'
        ),
        b'{"route":"UNKNOWN","intent":null,"topic_id":null,"pending_slot":null}',
        b'{"route":"SUPPORTED","intent":null,"topic_id":null,"pending_slot":null}',
        (b'{"route":"SUPPORTED","intent":"OUT_OF_SCOPE","topic_id":null,"pending_slot":null}'),
        (
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE",'
            b'"topic_id":null,"pending_slot":"WASTE_ITEM"}'
        ),
        (b'{"route":"CIVIC_SCOPE_GAP","intent":"BULKY_WASTE","topic_id":null,"pending_slot":null}'),
        (b'{"route":"NON_CIVIC","intent":null,"topic_id":"KB-WEATHER","pending_slot":null}'),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"CERTIFICATE_ISSUANCE",'
            b'"topic_id":null,"pending_slot":null}'
        ),
        (b'{"route":"NEEDS_FOLLOWUP","intent":"UNKNOWN","topic_id":null,"pending_slot":"REGION"}'),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"BULKY_WASTE",'
            b'"topic_id":"has spaces","pending_slot":"WASTE_ITEM"}'
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"BULKY_WASTE",'
            b'"topic_id":null,"pending_slot":"CERTIFICATE_KIND"}'
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"LOCAL_TAX_GENERAL",'
            b'"topic_id":null,"pending_slot":"WASTE_ITEM"}'
        ),
    ],
)
def test_parse_classifier_decision_rejects_invalid_or_open_ended_shapes(
    payload: bytes,
) -> None:
    with pytest.raises(ValueError, match="^CLASSIFIER_DECISION_INVALID$"):
        parse_classifier_decision(payload)


def test_classifier_decision_is_immutable() -> None:
    decision = parse_classifier_decision(
        b'{"route":"NON_CIVIC","intent":null,"topic_id":null,"pending_slot":null}'
    )

    with pytest.raises(FrozenInstanceError):
        decision.topic_id = "KB-INVENTED"  # type: ignore[misc]


def test_direct_classifier_decision_rejects_inconsistent_combination() -> None:
    with pytest.raises(ValueError, match="^CLASSIFIER_DECISION_INVALID$"):
        ClassifierDecision(
            route=ClassifierRoute.NON_CIVIC,
            intent=Intent.LOCAL_TAX_GENERAL,
            topic_id=None,
            pending_slot=None,
        )


def test_parser_never_reflects_provider_content_in_errors() -> None:
    sensitive_marker = "DO-NOT-REFLECT-THIS"

    with pytest.raises(ValueError) as error:
        parse_classifier_decision(sensitive_marker.encode("utf-8"))

    assert str(error.value) == "CLASSIFIER_DECISION_INVALID"
    assert sensitive_marker not in str(error.value)
