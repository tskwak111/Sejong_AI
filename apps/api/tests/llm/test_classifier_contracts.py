from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date

import pytest

from sejong_ai_api.chat.topic_catalog import (
    RuntimeTopic,
    TopicCatalog,
    TopicCoverage,
)
from sejong_ai_api.db.models import Intent, KnowledgeRecord
from sejong_ai_api.llm.classifier_contracts import (
    ClassifierDecision,
    ClassifierRoute,
    parse_classifier_decision,
    parse_classifier_decision_with_stage,
    parse_classifier_wire_decision_with_stage,
)
from sejong_ai_api.llm.classifier_diagnostics import ClassifierResponseStage

EXPECTED_REFINED_STAGES = (
    ClassifierResponseStage.ROUTE_ENUM_REJECTED,
    ClassifierResponseStage.INTENT_ENUM_REJECTED,
    ClassifierResponseStage.PENDING_SLOT_ENUM_REJECTED,
    ClassifierResponseStage.IDENTIFIER_SHAPE_REJECTED,
    ClassifierResponseStage.ROUTE_SHAPE_REJECTED,
)


def _catalog() -> TopicCatalog:
    intent = Intent.BULKY_WASTE
    return TopicCatalog(
        (
            RuntimeTopic(
                record=KnowledgeRecord(
                    public_id="KB-WASTE-01",
                    category=intent,
                    service_name="대형폐기물 배출신청 절차",
                    answer_summary="provider에 보내면 안 되는 답변",
                    procedure_steps=("provider에 보내면 안 되는 절차",),
                    required_documents=(),
                    processing_time=None,
                    fee=None,
                    department="provider에 보내면 안 되는 기관",
                    source_title="provider에 보내면 안 되는 출처",
                    source_url="https://example.invalid/official",
                    last_verified_at=date(2026, 7, 27),
                    caution=None,
                    question_examples=("대형폐기물은 어떻게 신청하나요?",),
                ),
                coverage=TopicCoverage(
                    topic_id="KB-WASTE-01",
                    intent=intent,
                    coverage_id="GENERAL_BULKY_DISPOSAL",
                    coverage_label="일반 가구류 배출 절차",
                ),
            ),
        )
    )


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE",'
            b'"topic_id":"KB-WASTE-01","coverage_id":"GENERAL_BULKY_DISPOSAL",'
            b'"pending_slot":null}',
            ("SUPPORTED", "BULKY_WASTE", "KB-WASTE-01", "GENERAL_BULKY_DISPOSAL", None),
        ),
        (
            b'{"route":"NO_TOPIC_MATCH","intent":"BULKY_WASTE",'
            b'"topic_id":null,"coverage_id":null,"pending_slot":null}',
            ("NO_TOPIC_MATCH", "BULKY_WASTE", None, None, None),
        ),
        (
            b'{"route":"CIVIC_SCOPE_GAP","intent":null,"topic_id":null,'
            b'"coverage_id":null,"pending_slot":null}',
            ("CIVIC_SCOPE_GAP", None, None, None, None),
        ),
        (
            b'{"route":"NON_CIVIC","intent":null,"topic_id":null,'
            b'"coverage_id":null,"pending_slot":null}',
            ("NON_CIVIC", None, None, None, None),
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":null,"topic_id":null,'
            b'"coverage_id":null,"pending_slot":"DOMAIN"}',
            ("NEEDS_FOLLOWUP", None, None, None, "DOMAIN"),
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"LOCAL_TAX_GENERAL",'
            b'"topic_id":null,"coverage_id":null,"pending_slot":"TOPIC_CHOICE"}',
            ("NEEDS_FOLLOWUP", "LOCAL_TAX_GENERAL", None, None, "TOPIC_CHOICE"),
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"CERTIFICATE_ISSUANCE",'
            b'"topic_id":null,"coverage_id":null,"pending_slot":"CERTIFICATE_KIND"}',
            ("NEEDS_FOLLOWUP", "CERTIFICATE_ISSUANCE", None, None, "CERTIFICATE_KIND"),
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"MOVE_IN_RESIDENT_REGISTRATION",'
            b'"topic_id":null,"coverage_id":null,"pending_slot":"REGION"}',
            ("NEEDS_FOLLOWUP", "MOVE_IN_RESIDENT_REGISTRATION", None, None, "REGION"),
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"BULKY_WASTE",'
            b'"topic_id":null,"coverage_id":null,"pending_slot":"WASTE_ITEM"}',
            ("NEEDS_FOLLOWUP", "BULKY_WASTE", None, None, "WASTE_ITEM"),
        ),
    ],
)
def test_parse_classifier_decision_accepts_every_closed_valid_shape(
    payload: bytes,
    expected: tuple[str, str | None, str | None, str | None, str | None],
) -> None:
    decision = parse_classifier_decision(payload, _catalog())

    assert (
        decision.route.value,
        decision.intent.value if decision.intent is not None else None,
        decision.topic_id,
        decision.coverage_id,
        decision.pending_slot.value if decision.pending_slot is not None else None,
    ) == expected


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE",'
            b'"topic_id":"KB-WASTE-01","coverage_id":"GENERAL_BULKY_DISPOSAL",'
            b'"pending_slot":"NONE"}',
            ("SUPPORTED", "BULKY_WASTE", "KB-WASTE-01", "GENERAL_BULKY_DISPOSAL", None),
        ),
        (
            b'{"route":"NO_TOPIC_MATCH","intent":"BULKY_WASTE",'
            b'"topic_id":"NONE","coverage_id":"NONE","pending_slot":"NONE"}',
            ("NO_TOPIC_MATCH", "BULKY_WASTE", None, None, None),
        ),
        (
            b'{"route":"CIVIC_SCOPE_GAP","intent":"NONE","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ("CIVIC_SCOPE_GAP", None, None, None, None),
        ),
        (
            b'{"route":"NON_CIVIC","intent":"NONE","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ("NON_CIVIC", None, None, None, None),
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"NONE",'
            b'"topic_id":"NONE","coverage_id":"NONE","pending_slot":"DOMAIN"}',
            ("NEEDS_FOLLOWUP", None, None, None, "DOMAIN"),
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"LOCAL_TAX_GENERAL",'
            b'"topic_id":"NONE","coverage_id":"NONE","pending_slot":"TOPIC_CHOICE"}',
            ("NEEDS_FOLLOWUP", "LOCAL_TAX_GENERAL", None, None, "TOPIC_CHOICE"),
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"CERTIFICATE_ISSUANCE",'
            b'"topic_id":"NONE","coverage_id":"NONE","pending_slot":"CERTIFICATE_KIND"}',
            ("NEEDS_FOLLOWUP", "CERTIFICATE_ISSUANCE", None, None, "CERTIFICATE_KIND"),
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"MOVE_IN_RESIDENT_REGISTRATION",'
            b'"topic_id":"NONE","coverage_id":"NONE","pending_slot":"REGION"}',
            ("NEEDS_FOLLOWUP", "MOVE_IN_RESIDENT_REGISTRATION", None, None, "REGION"),
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"BULKY_WASTE",'
            b'"topic_id":"NONE","coverage_id":"NONE","pending_slot":"WASTE_ITEM"}',
            ("NEEDS_FOLLOWUP", "BULKY_WASTE", None, None, "WASTE_ITEM"),
        ),
    ],
)
def test_provider_wire_normalizes_exact_none_and_accepts_closed_shapes(
    payload: bytes,
    expected: tuple[str, str | None, str | None, str | None, str | None],
) -> None:
    result = parse_classifier_wire_decision_with_stage(payload, _catalog())

    assert result.stage is ClassifierResponseStage.ACCEPTED
    assert result.decision is not None
    assert (
        result.decision.route.value,
        result.decision.intent.value if result.decision.intent else None,
        result.decision.topic_id,
        result.decision.coverage_id,
        result.decision.pending_slot.value if result.decision.pending_slot else None,
    ) == expected


@pytest.mark.parametrize(
    "payload",
    (
        b'{"route":"NON_CIVIC","route":"NON_CIVIC","intent":"NONE",'
        b'"topic_id":"NONE","coverage_id":"NONE","pending_slot":"NONE"}',
        b'{"route":"NON_CIVIC","intent":"NONE","intent":"NONE",'
        b'"topic_id":"NONE","coverage_id":"NONE","pending_slot":"NONE"}',
        b'{"route":"NON_CIVIC","intent":"NONE","topic_id":"NONE",'
        b'"topic_id":"NONE","coverage_id":"NONE","pending_slot":"NONE"}',
        b'{"route":"NON_CIVIC","intent":"NONE","topic_id":"NONE",'
        b'"coverage_id":"NONE","coverage_id":"NONE","pending_slot":"NONE"}',
        b'{"route":"NON_CIVIC","intent":"NONE","topic_id":"NONE",'
        b'"coverage_id":"NONE","pending_slot":"NONE","pending_slot":"NONE"}',
        b'{"route":"NON_CIVIC","intent":{"ambiguous":"NONE","ambiguous":"NONE"},'
        b'"topic_id":"NONE","coverage_id":"NONE","pending_slot":"NONE"}',
        b'{"route":"BAD_ROUTE","intent":"BAD_INTENT","intent":"NONE",'
        b'"topic_id":"NONE","coverage_id":"NONE","pending_slot":"NONE"}',
    ),
    ids=(
        "duplicate-route",
        "duplicate-intent",
        "duplicate-topic-id",
        "duplicate-coverage-id",
        "duplicate-pending-slot",
        "nested-duplicate",
        "duplicate-precedes-bad-enums",
    ),
)
def test_provider_wire_rejects_duplicate_keys_as_json_before_other_validation(
    payload: bytes,
) -> None:
    result = parse_classifier_wire_decision_with_stage(payload, _catalog())

    assert result.decision is None
    assert result.stage is ClassifierResponseStage.JSON_REJECTED


@pytest.mark.parametrize(
    ("payload", "expected_stage"),
    [
        (
            b'{"route":"NON_CIVIC","intent":null,"topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ClassifierResponseStage.FIELD_TYPE_REJECTED,
        ),
        (
            b'{"route":1,"intent":"NONE","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ClassifierResponseStage.FIELD_TYPE_REJECTED,
        ),
        (
            b'{"route":"NON_CIVIC","intent":"NONE","topic_id":"NONE","coverage_id":"NONE"}',
            ClassifierResponseStage.KEY_SET_REJECTED,
        ),
        (
            b'{"route":"NON_CIVIC","intent":"NONE","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE","extra":"value"}',
            ClassifierResponseStage.KEY_SET_REJECTED,
        ),
        (
            b'{"route":"NONE","intent":"NONE","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ClassifierResponseStage.ROUTE_ENUM_REJECTED,
        ),
        (
            b'{"route":"NON_CIVIC","intent":"none","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ClassifierResponseStage.INTENT_ENUM_REJECTED,
        ),
        (
            b'{"route":"NON_CIVIC","intent":"NONE","topic_id":"NONE ",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ClassifierResponseStage.IDENTIFIER_SHAPE_REJECTED,
        ),
        (
            b'{"route":"NON_CIVIC","intent":"BULKY_WASTE","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ClassifierResponseStage.ROUTE_SHAPE_REJECTED,
        ),
        (
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE",'
            b'"topic_id":"KB-WASTE-UNKNOWN","coverage_id":"GENERAL_BULKY_DISPOSAL",'
            b'"pending_slot":"NONE"}',
            ClassifierResponseStage.CATALOG_REJECTED,
        ),
        (
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE",'
            b'"topic_id":"KB-WASTE-01","coverage_id":"WRONG_COVERAGE",'
            b'"pending_slot":"NONE"}',
            ClassifierResponseStage.CATALOG_REJECTED,
        ),
    ],
)
def test_provider_wire_rejects_invalid_type_key_sentinel_shape_or_catalog(
    payload: bytes,
    expected_stage: ClassifierResponseStage,
) -> None:
    result = parse_classifier_wire_decision_with_stage(payload, _catalog())

    assert result.decision is None
    assert result.stage is expected_stage


def test_refined_classifier_response_stage_values_are_closed_and_legacy_is_retained() -> None:
    assert tuple(stage.value for stage in EXPECTED_REFINED_STAGES) == (
        "ROUTE_ENUM_REJECTED",
        "INTENT_ENUM_REJECTED",
        "PENDING_SLOT_ENUM_REJECTED",
        "IDENTIFIER_SHAPE_REJECTED",
        "ROUTE_SHAPE_REJECTED",
    )
    assert ClassifierResponseStage.ENUM_SHAPE_REJECTED.value == "ENUM_SHAPE_REJECTED"


@pytest.mark.parametrize(
    ("payload", "expected_stage", "forbidden_value"),
    [
        (
            b'{"route":"BAD_ROUTE","intent":"NONE","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ClassifierResponseStage.ROUTE_ENUM_REJECTED,
            "BAD_ROUTE",
        ),
        (
            b'{"route":"NON_CIVIC","intent":"BAD_INTENT","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ClassifierResponseStage.INTENT_ENUM_REJECTED,
            "BAD_INTENT",
        ),
        (
            b'{"route":"NON_CIVIC","intent":"OUT_OF_SCOPE","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ClassifierResponseStage.INTENT_ENUM_REJECTED,
            "OUT_OF_SCOPE",
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"BULKY_WASTE",'
            b'"topic_id":"NONE","coverage_id":"NONE","pending_slot":"BAD_SLOT"}',
            ClassifierResponseStage.PENDING_SLOT_ENUM_REJECTED,
            "BAD_SLOT",
        ),
        (
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE","topic_id":"bad topic",'
            b'"coverage_id":"GENERAL_BULKY_DISPOSAL","pending_slot":"NONE"}',
            ClassifierResponseStage.IDENTIFIER_SHAPE_REJECTED,
            "bad topic",
        ),
        (
            b'{"route":"NON_CIVIC","intent":"BULKY_WASTE","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ClassifierResponseStage.ROUTE_SHAPE_REJECTED,
            "BULKY_WASTE",
        ),
        (
            b'{"route":"BAD_ROUTE","intent":"BAD_INTENT","topic_id":"bad topic",'
            b'"coverage_id":"bad coverage","pending_slot":"BAD_SLOT"}',
            ClassifierResponseStage.ROUTE_ENUM_REJECTED,
            "BAD_ROUTE",
        ),
    ],
)
def test_provider_wire_reports_refined_first_failure_without_reflecting_value(
    payload: bytes,
    expected_stage: ClassifierResponseStage,
    forbidden_value: str,
) -> None:
    result = parse_classifier_wire_decision_with_stage(payload, _catalog())

    assert result.decision is None
    assert result.stage is expected_stage
    assert forbidden_value not in repr(result)


@pytest.mark.parametrize(
    ("payload", "expected_stage"),
    [
        pytest.param(
            b'{"route":"BAD_ROUTE","intent":"BAD_INTENT","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ClassifierResponseStage.ROUTE_ENUM_REJECTED,
            id="route-before-intent",
        ),
        pytest.param(
            b'{"route":"NEEDS_FOLLOWUP","intent":"BAD_INTENT",'
            b'"topic_id":"NONE","coverage_id":"NONE","pending_slot":"BAD_SLOT"}',
            ClassifierResponseStage.INTENT_ENUM_REJECTED,
            id="intent-before-pending-slot",
        ),
        pytest.param(
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE","topic_id":"bad topic",'
            b'"coverage_id":"GENERAL_BULKY_DISPOSAL","pending_slot":"BAD_SLOT"}',
            ClassifierResponseStage.PENDING_SLOT_ENUM_REJECTED,
            id="pending-slot-before-identifier",
        ),
        pytest.param(
            b'{"route":"NON_CIVIC","intent":"BULKY_WASTE","topic_id":"bad topic",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ClassifierResponseStage.IDENTIFIER_SHAPE_REJECTED,
            id="identifier-before-route-shape",
        ),
        pytest.param(
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE",'
            b'"topic_id":"KB-WASTE-UNKNOWN","coverage_id":"GENERAL_BULKY_DISPOSAL",'
            b'"pending_slot":"REGION"}',
            ClassifierResponseStage.ROUTE_SHAPE_REJECTED,
            id="route-shape-before-catalog",
        ),
    ],
)
def test_provider_wire_compound_errors_follow_adjacent_validation_precedence(
    payload: bytes,
    expected_stage: ClassifierResponseStage,
) -> None:
    result = parse_classifier_wire_decision_with_stage(payload, _catalog())

    assert result.decision is None
    assert result.stage is expected_stage


def test_canonical_and_provider_parsers_share_refined_stage_mapping() -> None:
    canonical = parse_classifier_decision_with_stage(
        b'{"route":"BAD_ROUTE","intent":null,"topic_id":null,'
        b'"coverage_id":null,"pending_slot":null}',
        _catalog(),
    )
    provider = parse_classifier_wire_decision_with_stage(
        b'{"route":"BAD_ROUTE","intent":"NONE","topic_id":"NONE",'
        b'"coverage_id":"NONE","pending_slot":"NONE"}',
        _catalog(),
    )

    assert canonical.stage is ClassifierResponseStage.ROUTE_ENUM_REJECTED
    assert provider.stage is canonical.stage


def test_direct_classifier_decision_keeps_route_shape_invariant() -> None:
    with pytest.raises(ValueError, match="^CLASSIFIER_DECISION_INVALID$"):
        ClassifierDecision(
            route=ClassifierRoute.CIVIC_SCOPE_GAP,
            intent=Intent.OUT_OF_SCOPE,
            topic_id=None,
            coverage_id=None,
            pending_slot=None,
        )


def test_public_parser_keeps_generic_non_reflective_failure() -> None:
    marker = "BAD_ROUTE"

    with pytest.raises(ValueError) as error:
        parse_classifier_decision(
            b'{"route":"BAD_ROUTE","intent":null,"topic_id":null,'
            b'"coverage_id":null,"pending_slot":null}',
            _catalog(),
        )

    assert str(error.value) == "CLASSIFIER_DECISION_INVALID"
    assert marker not in str(error.value)


@pytest.mark.parametrize(
    "payload",
    [
        b'{"route":"BAD_ROUTE","intent":"NONE","topic_id":"NONE",'
        b'"coverage_id":"NONE","pending_slot":"NONE"}',
        b'{"route":"NON_CIVIC","intent":"BAD_INTENT","topic_id":"NONE",'
        b'"coverage_id":"NONE","pending_slot":"NONE"}',
        b'{"route":"NEEDS_FOLLOWUP","intent":"BULKY_WASTE",'
        b'"topic_id":"NONE","coverage_id":"NONE","pending_slot":"BAD_SLOT"}',
        b'{"route":"SUPPORTED","intent":"BULKY_WASTE","topic_id":"bad topic",'
        b'"coverage_id":"GENERAL_BULKY_DISPOSAL","pending_slot":"NONE"}',
        b'{"route":"NON_CIVIC","intent":"BULKY_WASTE","topic_id":"NONE",'
        b'"coverage_id":"NONE","pending_slot":"NONE"}',
    ],
)
def test_new_parser_path_never_emits_legacy_enum_shape_stage(payload: bytes) -> None:
    result = parse_classifier_wire_decision_with_stage(payload, _catalog())

    assert result.decision is None
    assert result.stage in EXPECTED_REFINED_STAGES
    assert result.stage is not ClassifierResponseStage.ENUM_SHAPE_REJECTED


def test_canonical_parser_keeps_json_null_and_rejects_provider_sentinel() -> None:
    canonical = parse_classifier_decision(
        b'{"route":"NON_CIVIC","intent":null,"topic_id":null,'
        b'"coverage_id":null,"pending_slot":null}',
        _catalog(),
    )

    assert canonical.route is ClassifierRoute.NON_CIVIC

    with pytest.raises(ValueError, match="^CLASSIFIER_DECISION_INVALID$"):
        parse_classifier_decision(
            b'{"route":"NON_CIVIC","intent":"NONE","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            _catalog(),
        )


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        b"[]",
        (
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE",'
            b'"topic_id":"KB-WASTE-01","coverage_id":"GENERAL_BULKY_DISPOSAL",'
            b'"pending_slot":null,"answer":"invented"}'
        ),
        (
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE",'
            b'"topic_id":"KB-WASTE-01","coverage_id":"GENERAL_BULKY_DISPOSAL",'
            b'"pending_slot":null,"free_text":"invented"}'
        ),
        (
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE",'
            b'"topic_id":"KB-WASTE-01","coverage_id":"GENERAL_BULKY_DISPOSAL",'
            b'"pending_slot":null,"confidence":0.9}'
        ),
        (
            b'{"route":"SUPPORTED","intent":null,"topic_id":"KB-WASTE-01",'
            b'"coverage_id":"GENERAL_BULKY_DISPOSAL","pending_slot":null}'
        ),
        (
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE","topic_id":null,'
            b'"coverage_id":"GENERAL_BULKY_DISPOSAL","pending_slot":null}'
        ),
        (
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE",'
            b'"topic_id":"KB-WASTE-01","coverage_id":null,"pending_slot":null}'
        ),
        (
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE",'
            b'"topic_id":"KB-WASTE-UNKNOWN","coverage_id":"GENERAL_BULKY_DISPOSAL",'
            b'"pending_slot":null}'
        ),
        (
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE",'
            b'"topic_id":"KB-WASTE-01","coverage_id":"WRONG_COVERAGE",'
            b'"pending_slot":null}'
        ),
        (
            b'{"route":"SUPPORTED","intent":"LOCAL_TAX_GENERAL",'
            b'"topic_id":"KB-WASTE-01","coverage_id":"GENERAL_BULKY_DISPOSAL",'
            b'"pending_slot":null}'
        ),
        (
            b'{"route":"NO_TOPIC_MATCH","intent":null,"topic_id":null,'
            b'"coverage_id":null,"pending_slot":null}'
        ),
        (
            b'{"route":"CIVIC_SCOPE_GAP","intent":"BULKY_WASTE","topic_id":null,'
            b'"coverage_id":null,"pending_slot":null}'
        ),
        (
            b'{"route":"NON_CIVIC","intent":null,"topic_id":"KB-WASTE-01",'
            b'"coverage_id":null,"pending_slot":null}'
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"BULKY_WASTE","topic_id":null,'
            b'"coverage_id":null,"pending_slot":"DOMAIN"}'
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":null,"topic_id":null,'
            b'"coverage_id":null,"pending_slot":"TOPIC_CHOICE"}'
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":null,"topic_id":null,'
            b'"coverage_id":null,"pending_slot":"CERTIFICATE_KIND"}'
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":null,"topic_id":null,'
            b'"coverage_id":null,"pending_slot":"REGION"}'
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":null,"topic_id":null,'
            b'"coverage_id":null,"pending_slot":"WASTE_ITEM"}'
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"BULKY_WASTE",'
            b'"topic_id":"KB-WASTE-01","coverage_id":null,'
            b'"pending_slot":"TOPIC_CHOICE"}'
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"BULKY_WASTE",'
            b'"topic_id":null,"coverage_id":"GENERAL_BULKY_DISPOSAL",'
            b'"pending_slot":"TOPIC_CHOICE"}'
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"BULKY_WASTE","topic_id":null,'
            b'"coverage_id":null,"pending_slot":"CERTIFICATE_KIND"}'
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"LOCAL_TAX_GENERAL","topic_id":null,'
            b'"coverage_id":null,"pending_slot":"WASTE_ITEM"}'
        ),
    ],
)
def test_parse_classifier_decision_rejects_open_mismatched_or_incomplete_shapes(
    payload: bytes,
) -> None:
    with pytest.raises(ValueError, match="^CLASSIFIER_DECISION_INVALID$"):
        parse_classifier_decision(payload, _catalog())


def test_classifier_decision_is_immutable() -> None:
    decision = parse_classifier_decision(
        b'{"route":"NON_CIVIC","intent":null,"topic_id":null,'
        b'"coverage_id":null,"pending_slot":null}',
        _catalog(),
    )

    with pytest.raises(FrozenInstanceError):
        decision.topic_id = "KB-INVENTED"  # type: ignore[misc]


def test_direct_classifier_decision_rejects_inconsistent_combination() -> None:
    with pytest.raises(ValueError, match="^CLASSIFIER_DECISION_INVALID$"):
        ClassifierDecision(
            route=ClassifierRoute.NON_CIVIC,
            intent=Intent.LOCAL_TAX_GENERAL,
            topic_id=None,
            coverage_id=None,
            pending_slot=None,
        )


def test_parser_never_reflects_provider_content_in_errors() -> None:
    sensitive_marker = "DO-NOT-REFLECT-THIS"

    with pytest.raises(ValueError) as error:
        parse_classifier_decision(sensitive_marker.encode("utf-8"), _catalog())

    assert str(error.value) == "CLASSIFIER_DECISION_INVALID"
    assert sensitive_marker not in str(error.value)


@pytest.mark.parametrize(
    ("payload", "expected_stage", "accepted"),
    [
        (b"not-json", ClassifierResponseStage.JSON_REJECTED, False),
        (b"[]", ClassifierResponseStage.KEY_SET_REJECTED, False),
        (
            b'{"route":1,"intent":null,"topic_id":null,"coverage_id":null,"pending_slot":null}',
            ClassifierResponseStage.FIELD_TYPE_REJECTED,
            False,
        ),
        (
            b'{"route":"UNBOUNDED","intent":null,"topic_id":null,'
            b'"coverage_id":null,"pending_slot":null}',
            ClassifierResponseStage.ROUTE_ENUM_REJECTED,
            False,
        ),
        (
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE",'
            b'"topic_id":"KB-WASTE-UNKNOWN",'
            b'"coverage_id":"GENERAL_BULKY_DISPOSAL","pending_slot":null}',
            ClassifierResponseStage.CATALOG_REJECTED,
            False,
        ),
        (
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE",'
            b'"topic_id":"KB-WASTE-01",'
            b'"coverage_id":"GENERAL_BULKY_DISPOSAL","pending_slot":null}',
            ClassifierResponseStage.ACCEPTED,
            True,
        ),
    ],
)
def test_diagnostic_parser_returns_only_terminal_stage_and_closed_decision(
    payload: bytes,
    expected_stage: ClassifierResponseStage,
    accepted: bool,
) -> None:
    result = parse_classifier_decision_with_stage(payload, _catalog())

    assert result.stage is expected_stage
    assert (result.decision is not None) is accepted
    assert tuple(result.__dataclass_fields__) == ("decision", "stage")
