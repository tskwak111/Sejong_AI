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
