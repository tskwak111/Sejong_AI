from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pytest

from sejong_ai_api.chat.topic_catalog import (
    TopicCoverage,
    build_topic_catalog,
    load_topic_coverage,
)
from sejong_ai_api.db.models import Intent, KnowledgeRecord

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
METADATA_PATH = REPOSITORY_ROOT / "data" / "retrieval" / "topic-coverage.v1.json"
SUPPORTED_INTENTS = (
    Intent.CERTIFICATE_ISSUANCE,
    Intent.MOVE_IN_RESIDENT_REGISTRATION,
    Intent.LOCAL_TAX_GENERAL,
    Intent.BULKY_WASTE,
)


def knowledge(
    public_id: str,
    category: Intent = Intent.BULKY_WASTE,
) -> KnowledgeRecord:
    return KnowledgeRecord(
        public_id=public_id,
        category=category,
        service_name="Governed service",
        answer_summary="Governed summary",
        procedure_steps=("Governed step",),
        required_documents=(),
        processing_time=None,
        fee=None,
        department="Governed department",
        source_title="Governed source",
        source_url="https://example.invalid/governed",
        last_verified_at=date(2026, 7, 27),
        caution=None,
        question_examples=("Governed example",),
    )


def coverage(
    topic_id: str,
    intent: Intent = Intent.BULKY_WASTE,
) -> TopicCoverage:
    return TopicCoverage(
        topic_id=topic_id,
        intent=intent,
        coverage_id="GOVERNED_COVERAGE",
        coverage_label="Governed retrieval boundary",
    )


@dataclass(frozen=True)
class UntrustedKnowledgeProjection:
    record: KnowledgeRecord


def write_metadata(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_governed_metadata_has_the_exact_versioned_shape_and_topic_ids() -> None:
    raw = json.loads(METADATA_PATH.read_text(encoding="utf-8"))

    assert set(raw) == {"schema_version", "data_kind", "topics"}
    assert raw["schema_version"] == 1
    assert raw["data_kind"] == "NON_FACTUAL_RETRIEVAL_METADATA"
    assert tuple(topic["topic_id"] for topic in raw["topics"]) == (
        "KB-CERT-01",
        "KB-CERT-02",
        "KB-CERT-03",
        "KB-CERT-04",
        "KB-CERT-05",
        "KB-MOVE-01",
        "KB-MOVE-02",
        "KB-MOVE-03",
        "KB-MOVE-04",
        "KB-MOVE-05",
        "KB-TAX-01",
        "KB-TAX-02",
        "KB-TAX-03",
        "KB-TAX-04",
        "KB-TAX-05",
        "KB-WASTE-01",
        "KB-WASTE-02",
        "KB-WASTE-03",
        "KB-WASTE-04",
        "KB-WASTE-05",
    )
    assert len(raw["topics"]) == len({topic["topic_id"] for topic in raw["topics"]}) == 20
    for topic in raw["topics"]:
        assert set(topic) == {"topic_id", "intent", "coverage_id", "coverage_label"}
        assert topic["intent"] in {intent.value for intent in SUPPORTED_INTENTS}
        assert topic["coverage_id"].isupper()
        assert topic["coverage_id"].replace("_", "").isalnum()
        assert topic["coverage_label"].strip()


@pytest.mark.parametrize(
    "payload",
    (
        {"schema_version": 1, "data_kind": "NON_FACTUAL_RETRIEVAL_METADATA"},
        {
            "schema_version": 1,
            "data_kind": "NON_FACTUAL_RETRIEVAL_METADATA",
            "topics": [],
            "unexpected": True,
        },
        {
            "schema_version": 1,
            "data_kind": "NON_FACTUAL_RETRIEVAL_METADATA",
            "topics": [
                {
                    "topic_id": "KB-WASTE-01",
                    "intent": "BULKY_WASTE",
                    "coverage_id": "GOVERNED_COVERAGE",
                    "coverage_label": "Governed retrieval boundary",
                    "unexpected": True,
                }
            ],
        },
    ),
)
def test_loader_rejects_missing_or_extra_governance_keys(tmp_path: Path, payload: object) -> None:
    metadata_path = tmp_path / "topic-coverage.v1.json"
    write_metadata(metadata_path, payload)

    with pytest.raises(ValueError):
        load_topic_coverage(metadata_path)


def test_loader_rejects_duplicate_topics_and_invalid_coverage_values(tmp_path: Path) -> None:
    metadata_path = tmp_path / "topic-coverage.v1.json"
    write_metadata(
        metadata_path,
        {
            "schema_version": 1,
            "data_kind": "NON_FACTUAL_RETRIEVAL_METADATA",
            "topics": [
                {
                    "topic_id": "KB-WASTE-01",
                    "intent": "BULKY_WASTE",
                    "coverage_id": "invalid coverage",
                    "coverage_label": " ",
                },
                {
                    "topic_id": "KB-WASTE-01",
                    "intent": "BULKY_WASTE",
                    "coverage_id": "GOVERNED_COVERAGE",
                    "coverage_label": "Governed retrieval boundary",
                },
            ],
        },
    )

    with pytest.raises(ValueError):
        load_topic_coverage(metadata_path)


def test_loader_returns_sorted_typed_coverage(tmp_path: Path) -> None:
    metadata_path = tmp_path / "topic-coverage.v1.json"
    write_metadata(
        metadata_path,
        {
            "schema_version": 1,
            "data_kind": "NON_FACTUAL_RETRIEVAL_METADATA",
            "topics": [
                {
                    "topic_id": "KB-WASTE-02",
                    "intent": "BULKY_WASTE",
                    "coverage_id": "SECOND_COVERAGE",
                    "coverage_label": "Second retrieval boundary",
                },
                {
                    "topic_id": "KB-WASTE-01",
                    "intent": "BULKY_WASTE",
                    "coverage_id": "FIRST_COVERAGE",
                    "coverage_label": "First retrieval boundary",
                },
            ],
        },
    )

    loaded = load_topic_coverage(metadata_path)

    assert tuple(item.topic_id for item in loaded) == ("KB-WASTE-01", "KB-WASTE-02")
    assert loaded[0].intent is Intent.BULKY_WASTE


def test_runtime_catalog_is_a_sorted_active_projection_intersection() -> None:
    catalog = build_topic_catalog(
        (
            knowledge("KB-MOVE-01", Intent.MOVE_IN_RESIDENT_REGISTRATION),
            knowledge("KB-WASTE-01"),
            knowledge("KB-WASTE-NOT-GOVERNED"),
            UntrustedKnowledgeProjection(knowledge("KB-WASTE-02")),
        ),
        (
            coverage("KB-WASTE-02"),
            coverage("KB-MOVE-01", Intent.MOVE_IN_RESIDENT_REGISTRATION),
            coverage("KB-WASTE-01"),
        ),
    )

    assert tuple(topic.record.public_id for topic in catalog.topics) == (
        "KB-MOVE-01",
        "KB-WASTE-01",
    )
    assert catalog.find("KB-WASTE-01") is not None
    assert catalog.find("KB-WASTE-02") is None
    assert catalog.provider_eligible is True


def test_runtime_catalog_provider_eligibility_enforces_zero_one_twenty_and_twenty_one() -> None:
    one_coverage = (coverage("KB-WASTE-01"),)
    twenty_coverage = tuple(coverage(f"KB-WASTE-{index:02}") for index in range(1, 21))
    twenty_one_coverage = (*twenty_coverage, coverage("KB-WASTE-21"))

    empty_catalog = build_topic_catalog((), one_coverage)
    one_catalog = build_topic_catalog((knowledge("KB-WASTE-01"),), one_coverage)
    twenty_catalog = build_topic_catalog(
        tuple(knowledge(f"KB-WASTE-{index:02}") for index in range(1, 21)),
        twenty_coverage,
    )
    twenty_one_catalog = build_topic_catalog(
        tuple(knowledge(f"KB-WASTE-{index:02}") for index in range(1, 22)),
        twenty_one_coverage,
    )

    assert len(empty_catalog.topics) == 0
    assert empty_catalog.provider_eligible is False
    assert len(one_catalog.topics) == 1
    assert one_catalog.provider_eligible is True
    assert len(twenty_catalog.topics) == 20
    assert twenty_catalog.provider_eligible is True
    assert len(twenty_one_catalog.topics) == 21
    assert twenty_one_catalog.provider_eligible is False
