from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from sejong_ai_api.chat.classification import SafeQuestion, classify_question
from sejong_ai_api.chat.grounding import evaluate_grounding
from sejong_ai_api.chat.retrieval import select_deterministic_topic
from sejong_ai_api.chat.topic_catalog import build_topic_catalog, load_topic_coverage
from sejong_ai_api.db.models import Intent, KnowledgeRecord
from sejong_ai_api.privacy.redaction import redact_question

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
RELEASE_PATH = (
    REPOSITORY_ROOT / "data" / "official" / "releases" / "0.1.0-initial.2" / "kb_records.json"
)
COVERAGE_PATH = REPOSITORY_ROOT / "data" / "retrieval" / "topic-coverage.v1.json"


def load_records() -> tuple[KnowledgeRecord, ...]:
    payload: dict[str, Any] = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
    return tuple(
        KnowledgeRecord(
            public_id=item["id"],
            category=Intent(item["category"]),
            service_name=item["service_name"],
            answer_summary=item["answer_summary"],
            procedure_steps=tuple(item["procedure_steps"]),
            required_documents=tuple(item["required_documents"]),
            processing_time=item["processing_time"],
            fee=item["fee"],
            department=item["department"],
            source_title=item["source_title"],
            source_url=item["source_url"],
            last_verified_at=date.fromisoformat(item["last_verified_at"]),
            caution=item["caution"],
            question_examples=tuple(item["question_examples"]),
        )
        for item in payload["records"]
    )


def test_every_approved_initial_question_example_reaches_its_grounded_record() -> None:
    records = load_records()
    records_by_intent: defaultdict[Intent, list[KnowledgeRecord]] = defaultdict(list)
    for record in records:
        records_by_intent[record.category].append(record)

    checked = 0
    for expected_record in records:
        for example in expected_record.question_examples:
            safe_question = SafeQuestion(redact_question(example))
            classification = classify_question(safe_question)
            assert classification.intent is expected_record.category, (
                expected_record.public_id,
                example,
                classification,
            )
            assert classification.followup_required is False
            assert classification.fallback_reason is None

            catalog = build_topic_catalog(
                records_by_intent[expected_record.category],
                load_topic_coverage(COVERAGE_PATH),
            )
            selection = select_deterministic_topic(
                safe_question,
                expected_record.category,
                catalog,
            )
            assert selection is not None
            assert selection.topic.record.public_id == expected_record.public_id
            decision = evaluate_grounding(
                safe_question,
                expected_record.category,
                selection,
            )
            assert decision.is_grounded is True, (expected_record.public_id, example)
            checked += 1

    assert checked == 57
