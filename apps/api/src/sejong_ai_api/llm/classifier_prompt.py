"""Bounded prompt for the closed Upstage topic and coverage selector."""

from __future__ import annotations

import json

from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.topic_catalog import TopicCatalog
from sejong_ai_api.db.models import Intent

_MAX_QUESTION_CHARS = 1024
_PROVIDER_INTENT_ORDER = (
    Intent.MOVE_IN_RESIDENT_REGISTRATION,
    Intent.CERTIFICATE_ISSUANCE,
    Intent.BULKY_WASTE,
    Intent.LOCAL_TAX_GENERAL,
)
_SYSTEM_MESSAGE = (
    "JSON;"
    "keys: route,intent,topic_id,coverage_id,pending_slot;"
    "all five values are strings;"
    "no extra key, prose or Markdown;"
    "NONE is exact uppercase ASCII; 없음/none/null/empty are forbidden;"
    "provider intents: the four supported intents or NONE;"
    "MOVE_IN_RESIDENT_REGISTRATION|LOCAL_TAX_GENERAL;"
    "cat={intent:[[topic_id,coverage_id,coverage_label,approved_examples]]};"
    "SUPPORTED intent=cat group key; topic_id/coverage_id=same row;"
    "valid tuples in key order:"
    "SUPPORTED|catalog intent|same-row topic_id|same-row coverage_id|NONE;"
    "NO_TOPIC_MATCH|supported intent|NONE|NONE|NONE;"
    "CIVIC_SCOPE_GAP|NONE|NONE|NONE|NONE;"
    "NON_CIVIC|NONE|NONE|NONE|NONE;"
    "NEEDS_FOLLOWUP|NONE|NONE|NONE|DOMAIN;"
    "NEEDS_FOLLOWUP|supported intent|NONE|NONE|TOPIC_CHOICE;"
    "NEEDS_FOLLOWUP|CERTIFICATE_ISSUANCE|NONE|NONE|CERTIFICATE_KIND;"
    "NEEDS_FOLLOWUP|supported intent|NONE|NONE|REGION;"
    "NEEDS_FOLLOWUP|BULKY_WASTE|NONE|NONE|WASTE_ITEM"
)


def _build_grouped_catalog(catalog: TopicCatalog) -> dict[str, list[list[object]]]:
    grouped: dict[str, list[list[object]]] = {}
    for intent in _PROVIDER_INTENT_ORDER:
        rows: list[list[object]] = [
            [
                topic.record.public_id,
                topic.coverage.coverage_id,
                topic.coverage.coverage_label,
                list(topic.record.question_examples[:2]),
            ]
            for topic in catalog.topics
            if topic.record.category is intent
        ]
        if rows:
            grouped[intent.value] = rows
    return grouped


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
    first = catalog.topics[0]
    payload = {
        "ask": question.text,
        "cat": _build_grouped_catalog(catalog),
        "ex": [
            [
                "SUPPORTED",
                first.record.category.value,
                first.record.public_id,
                first.coverage.coverage_id,
                "NONE",
            ],
            ["CIVIC_SCOPE_GAP", "NONE", "NONE", "NONE", "NONE"],
        ],
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
