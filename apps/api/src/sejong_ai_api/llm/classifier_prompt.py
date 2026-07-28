"""Bounded prompt for the closed Upstage topic and coverage selector."""

from __future__ import annotations

import json

from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.topic_catalog import TopicCatalog

_MAX_QUESTION_CHARS = 1024
_CATALOG_COLUMNS = (
    "topic_id",
    "intent",
    "service_name",
    "coverage_id",
    "coverage_label",
    "approved_examples",
)
_SYSTEM_MESSAGE = (
    "JSON route,intent,topic_id,coverage_id,pending_slot=5 strings;NONE=없음;+X;"
    "SUPPORTED=row*3,NONE;NO_TOPIC_MATCH=지원,NONE*3;"
    "CIVIC_SCOPE_GAP/NON_CIVIC=NONE*4;"
    "NEEDS_FOLLOWUP=DOMAIN?NONE:지원,NONE*2,"
    "DOMAIN|TOPIC_CHOICE|CERTIFICATE_KIND|REGION|WASTE_ITEM"
)


def build_classifier_messages(
    question: SafeQuestion,
    catalog: TopicCatalog,
    *,
    max_input_chars: int,
) -> tuple[dict[str, str], ...]:
    """Serialize every eligible governed topic without truncation or sampling."""

    if (
        type(question) is not SafeQuestion
        or type(catalog) is not TopicCatalog
        or not catalog.provider_eligible
        or type(max_input_chars) is not int
        or max_input_chars <= 0
        or max_input_chars > _MAX_QUESTION_CHARS
        or len(question.text) > max_input_chars
    ):
        raise ValueError("CLASSIFIER_PROMPT_INVALID")
    payload = {
        "ask": question.text,
        "catalog": {
            "cols": list(_CATALOG_COLUMNS),
            "rows": [
                [
                    topic.record.public_id,
                    topic.record.category.value,
                    topic.record.service_name,
                    topic.coverage.coverage_id,
                    topic.coverage.coverage_label,
                    list(topic.record.question_examples[:2]),
                ]
                for topic in catalog.topics
            ],
        },
    }
    return (
        {"role": "system", "content": _SYSTEM_MESSAGE},
        {
            "role": "user",
            "content": json.dumps(
                payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        },
    )


def estimate_classifier_input_upper_bound(
    messages: tuple[dict[str, str], ...],
) -> int:
    """Conservatively overestimate Korean token use before transport."""

    return sum(len(message["content"]) for message in messages)


__all__ = [
    "build_classifier_messages",
    "estimate_classifier_input_upper_bound",
]
