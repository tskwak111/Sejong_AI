"""Minimal source-free prompt for the closed Upstage question classifier."""

from __future__ import annotations

import json

from sejong_ai_api.chat.classification import SafeQuestion

_SYSTEM_MESSAGE = (
    "시민 질문을 지정된 폐쇄형 분류값으로만 분류하세요. "
    "답변, 출처, 보관 여부, 후보 생성 여부를 작성하지 마세요. "
    "응답은 정확히 네 필드의 JSON 객체 하나만 작성하세요."
)
_OUTPUT_DOMAIN = {
    "route": [
        "SUPPORTED",
        "CIVIC_SCOPE_GAP",
        "NON_CIVIC",
        "NEEDS_FOLLOWUP",
    ],
    "intent": [
        "MOVE_IN_RESIDENT_REGISTRATION",
        "CERTIFICATE_ISSUANCE",
        "BULKY_WASTE",
        "LOCAL_TAX_GENERAL",
        None,
    ],
    "topic_id": "server-known-uppercase-id|null",
    "pending_slot": [
        "CERTIFICATE_KIND",
        "REGION",
        "WASTE_ITEM",
        None,
    ],
}


def build_classifier_messages(
    question: SafeQuestion,
    *,
    max_input_chars: int,
) -> tuple[dict[str, str], ...]:
    """Build the sole prompt accepted by the classifier transport."""

    if (
        type(question) is not SafeQuestion
        or type(max_input_chars) is not int
        or max_input_chars <= 0
    ):
        raise ValueError("CLASSIFIER_PROMPT_INVALID")
    payload = {
        "masked_question": question.text[:max_input_chars],
        "output_domain": _OUTPUT_DOMAIN,
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
