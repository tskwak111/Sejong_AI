from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

import pytest

from sejong_ai_api.chat.classification import SafeQuestion, classify_question
from sejong_ai_api.chat.grounding import evaluate_grounding
from sejong_ai_api.chat.retrieval import (
    select_deterministic_topic,
    validate_semantic_selection,
)
from sejong_ai_api.chat.topic_catalog import build_topic_catalog, load_topic_coverage
from sejong_ai_api.db.models import FallbackReason, Intent, KnowledgeRecord
from sejong_ai_api.llm.classifier_contracts import ClassifierDecision, ClassifierRoute
from sejong_ai_api.privacy.redaction import redact_question

from .test_official_examples import COVERAGE_PATH, load_records

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
SAMPLE_PATH = REPOSITORY_ROOT / "data" / "evaluation" / "sample_questions_20.csv"
SEMANTIC_SAMPLE_TOPICS = {
    "T-02": "KB-MOVE-02",
    "T-07": "KB-WASTE-01",
    "T-08": "KB-WASTE-02",
}


def load_samples() -> tuple[dict[str, str], ...]:
    with SAMPLE_PATH.open(encoding="utf-8-sig", newline="") as stream:
        return tuple(csv.DictReader(stream))


def evaluate(
    sample_id: str,
    question: str,
    records_by_intent: dict[Intent, list[KnowledgeRecord]],
) -> tuple[str, str | None]:
    redaction = redact_question(question)
    if redaction.masked_text is None:
        return "FALLBACK", "PRIVACY_UNRESOLVED"
    safe_question = SafeQuestion(redaction)
    classification = classify_question(safe_question)
    if classification.fallback_reason is not None:
        return "FALLBACK", classification.fallback_reason.value
    if classification.followup_required:
        return "FOLLOWUP", None
    catalog = build_topic_catalog(
        records_by_intent[classification.intent],
        load_topic_coverage(COVERAGE_PATH),
    )
    selection = select_deterministic_topic(
        safe_question,
        classification.intent,
        catalog,
    )
    semantic_topic_id = SEMANTIC_SAMPLE_TOPICS.get(sample_id)
    if selection is None and semantic_topic_id is not None:
        semantic_topic = catalog.find(semantic_topic_id)
        assert semantic_topic is not None
        selection = validate_semantic_selection(
            ClassifierDecision(
                route=ClassifierRoute.SUPPORTED,
                intent=classification.intent,
                topic_id=semantic_topic.record.public_id,
                coverage_id=semantic_topic.coverage.coverage_id,
                pending_slot=None,
            ),
            catalog,
        )
    grounding = evaluate_grounding(
        safe_question,
        classification.intent,
        selection,
    )
    if not grounding.is_grounded:
        return "FALLBACK", FallbackReason.INSUFFICIENT_GROUNDING.value
    return "SUCCESS", None


SAMPLES = load_samples()


@pytest.mark.parametrize(
    "sample",
    [pytest.param(sample, id=sample["test_id"]) for sample in SAMPLES],
)
def test_approved_sample_question_matches_frozen_expectation(sample: dict[str, str]) -> None:
    records_by_intent: defaultdict[Intent, list[KnowledgeRecord]] = defaultdict(list)
    for record in load_records():
        records_by_intent[record.category].append(record)

    actual_status, actual_reason = evaluate(
        sample["test_id"],
        sample["질문"],
        records_by_intent,
    )

    assert actual_status == sample["기대 상태"]
    assert actual_reason == (sample["기대 폴백 사유"] or None)


def test_sample_matrix_remains_exactly_twenty_with_no_policy_skips() -> None:
    assert len(SAMPLES) == 20
    assert {sample["test_id"] for sample in SAMPLES} == {f"T-{index:02d}" for index in range(1, 21)}
