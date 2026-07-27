"""Governed ACTIVE/OFFICIAL topic catalog for bounded retrieval."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from sejong_ai_api.db.models import Intent, KnowledgeRecord

_SUPPORTED_INTENTS = frozenset(
    {
        Intent.MOVE_IN_RESIDENT_REGISTRATION,
        Intent.CERTIFICATE_ISSUANCE,
        Intent.BULKY_WASTE,
        Intent.LOCAL_TAX_GENERAL,
    }
)
_IDENTIFIER_PATTERN = re.compile(r"[A-Z0-9][A-Z0-9._-]{0,63}\Z")
_ROOT_KEYS = frozenset({"schema_version", "data_kind", "topics"})
_TOPIC_KEYS = frozenset({"topic_id", "intent", "coverage_id", "coverage_label"})
_SCHEMA_VERSION = 1
_DATA_KIND = "NON_FACTUAL_RETRIEVAL_METADATA"


def _require_identifier(value: object) -> str:
    if type(value) is not str or _IDENTIFIER_PATTERN.fullmatch(value) is None:
        raise ValueError("TOPIC_COVERAGE_INVALID")
    return value


def _require_label(value: object) -> str:
    if type(value) is not str or not value or value.strip() != value:
        raise ValueError("TOPIC_COVERAGE_INVALID")
    return value


@dataclass(frozen=True, slots=True)
class TopicCoverage:
    topic_id: str
    intent: Intent
    coverage_id: str
    coverage_label: str

    def __post_init__(self) -> None:
        _require_identifier(self.topic_id)
        if type(self.intent) is not Intent or self.intent not in _SUPPORTED_INTENTS:
            raise ValueError("TOPIC_COVERAGE_INVALID")
        _require_identifier(self.coverage_id)
        _require_label(self.coverage_label)


@dataclass(frozen=True, slots=True)
class RuntimeTopic:
    record: KnowledgeRecord
    coverage: TopicCoverage

    def __post_init__(self) -> None:
        if type(self.record) is not KnowledgeRecord or type(self.coverage) is not TopicCoverage:
            raise ValueError("RUNTIME_TOPIC_INVALID")
        if (
            self.record.public_id != self.coverage.topic_id
            or self.record.category is not self.coverage.intent
        ):
            raise ValueError("RUNTIME_TOPIC_INVALID")


@dataclass(frozen=True, slots=True)
class TopicCatalog:
    topics: tuple[RuntimeTopic, ...]

    def __post_init__(self) -> None:
        if type(self.topics) is not tuple or any(
            type(topic) is not RuntimeTopic for topic in self.topics
        ):
            raise ValueError("TOPIC_CATALOG_INVALID")
        if tuple(sorted(topic.record.public_id for topic in self.topics)) != tuple(
            topic.record.public_id for topic in self.topics
        ):
            raise ValueError("TOPIC_CATALOG_INVALID")
        if len({topic.record.public_id for topic in self.topics}) != len(self.topics):
            raise ValueError("TOPIC_CATALOG_INVALID")

    @property
    def provider_eligible(self) -> bool:
        return 1 <= len(self.topics) <= 20

    def find(self, topic_id: str) -> RuntimeTopic | None:
        if type(topic_id) is not str:
            return None
        return next((topic for topic in self.topics if topic.record.public_id == topic_id), None)


def load_topic_coverage(path: Path) -> tuple[TopicCoverage, ...]:
    """Load only the exact versioned non-factual coverage metadata schema."""

    document = json.loads(path.read_text(encoding="utf-8"))
    if type(document) is not dict or set(document) != _ROOT_KEYS:
        raise ValueError("TOPIC_COVERAGE_INVALID")
    if type(document["schema_version"]) is not int or document["schema_version"] != _SCHEMA_VERSION:
        raise ValueError("TOPIC_COVERAGE_INVALID")
    if document["data_kind"] != _DATA_KIND or type(document["data_kind"]) is not str:
        raise ValueError("TOPIC_COVERAGE_INVALID")
    raw_topics = document["topics"]
    if type(raw_topics) is not list:
        raise ValueError("TOPIC_COVERAGE_INVALID")

    coverage: list[TopicCoverage] = []
    for raw_topic in raw_topics:
        if type(raw_topic) is not dict or set(raw_topic) != _TOPIC_KEYS:
            raise ValueError("TOPIC_COVERAGE_INVALID")
        try:
            intent = Intent(raw_topic["intent"])
        except (TypeError, ValueError) as error:
            raise ValueError("TOPIC_COVERAGE_INVALID") from error
        coverage.append(
            TopicCoverage(
                topic_id=raw_topic["topic_id"],
                intent=intent,
                coverage_id=raw_topic["coverage_id"],
                coverage_label=raw_topic["coverage_label"],
            )
        )

    if len({topic.topic_id for topic in coverage}) != len(coverage):
        raise ValueError("TOPIC_COVERAGE_INVALID")
    return tuple(sorted(coverage, key=lambda topic: topic.topic_id))


def build_topic_catalog(
    records: Sequence[KnowledgeRecord],
    coverage: Sequence[TopicCoverage],
) -> TopicCatalog:
    """Intersect current ACTIVE/OFFICIAL records with governed retrieval metadata."""

    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise TypeError("ACTIVE_KNOWLEDGE_SEQUENCE_REQUIRED")
    if not isinstance(coverage, Sequence) or isinstance(coverage, (str, bytes)):
        raise TypeError("TOPIC_COVERAGE_SEQUENCE_REQUIRED")

    governed_by_id: dict[str, TopicCoverage] = {}
    for item in coverage:
        if type(item) is not TopicCoverage:
            raise TypeError("TOPIC_COVERAGE_REQUIRED")
        if item.topic_id in governed_by_id:
            raise ValueError("TOPIC_COVERAGE_INVALID")
        governed_by_id[item.topic_id] = item

    records_by_id: dict[str, KnowledgeRecord] = {}
    for record in records:
        if type(record) is KnowledgeRecord:
            records_by_id[record.public_id] = record

    topics: list[RuntimeTopic] = []
    for topic_id, governed in governed_by_id.items():
        matched_record = records_by_id.get(topic_id)
        if matched_record is not None and matched_record.category is governed.intent:
            topics.append(RuntimeTopic(record=matched_record, coverage=governed))
    return TopicCatalog(tuple(sorted(topics, key=lambda topic: topic.record.public_id)))


__all__ = [
    "RuntimeTopic",
    "TopicCatalog",
    "TopicCoverage",
    "build_topic_catalog",
    "load_topic_coverage",
]
