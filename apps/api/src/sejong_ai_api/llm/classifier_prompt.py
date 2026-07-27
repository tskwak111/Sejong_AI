"""Bounded prompt for the closed Upstage topic and coverage selector."""

from __future__ import annotations

import json

from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.topic_catalog import TopicCatalog

_MAX_QUESTION_CHARS = 1024
_SYSTEM_MESSAGE = (
    "주어진 질문과 topic_catalog만 사용해 JSON 객체 하나만 반환하세요. "
    "키는 정확히 route,intent,topic_id,coverage_id,pending_slot입니다. "
    "route는 SUPPORTED,NO_TOPIC_MATCH,CIVIC_SCOPE_GAP,NON_CIVIC,NEEDS_FOLLOWUP 중 하나입니다. "
    "intent는 MOVE_IN_RESIDENT_REGISTRATION,CERTIFICATE_ISSUANCE,BULKY_WASTE,"
    "LOCAL_TAX_GENERAL 또는 null입니다. "
    "pending_slot은 DOMAIN,TOPIC_CHOICE,CERTIFICATE_KIND,REGION,WASTE_ITEM 또는 null입니다. "
    "SUPPORTED는 catalog의 동일 항목에 있는 intent,topic_id,coverage_id를 채우고 "
    "pending_slot은 null입니다. "
    "NO_TOPIC_MATCH는 intent만 채웁니다. "
    "CIVIC_SCOPE_GAP과 NON_CIVIC은 나머지를 모두 null로 둡니다. "
    "NEEDS_FOLLOWUP은 topic_id와 coverage_id를 null로 두며, DOMAIN은 intent도 null이고 "
    "다른 pending_slot은 intent를 채웁니다. "
    "위 다섯 키 외의 키나 자유 문장을 추가하지 마세요."
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
        "masked_question": question.text,
        "topic_catalog": [
            {
                "topic_id": topic.record.public_id,
                "intent": topic.record.category.value,
                "service_name": topic.record.service_name,
                "coverage_id": topic.coverage.coverage_id,
                "coverage_label": topic.coverage.coverage_label,
                "approved_examples": list(topic.record.question_examples[:2]),
            }
            for topic in catalog.topics
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
