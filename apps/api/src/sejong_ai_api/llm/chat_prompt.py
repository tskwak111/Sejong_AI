"""Source-free prompt boundary for grounded citizen-chat generation."""

import json

from sejong_ai_api.llm.chat_contracts import GroundedChatRequest

_SYSTEM_MESSAGE = (
    "제공된 승인 행정 사실만 사용하고 새로운 사실을 추가하지 마세요. "
    "요약은 제공된 질문과 사실 범위를 벗어나지 않아야 합니다. "
    "나머지 항목은 제공된 식별자만 선택하세요. "
    "응답은 지정된 구조의 JSON 객체 하나만 작성하고 추가 필드를 넣지 마세요."
)
_OUTPUT_SCHEMA = {
    "summary": "string<=500",
    "procedure_step_ids": ["STEP-.."],
    "required_document_ids": ["DOC-.."],
    "processing_time_id": "TIME-01|null",
    "fee_id": "FEE-01|null",
    "department_id": "DEPT-01",
}


def build_grounded_chat_messages(
    request: GroundedChatRequest,
) -> tuple[dict[str, str], ...]:
    """Build the sole minimal prompt accepted by the grounded-chat transport."""
    safe_request = _revalidate_request(request)
    payload = {
        "masked_question": safe_request.masked_question,
        "intent": safe_request.intent.value,
        "service_name": safe_request.service_name,
        "approved_summary": safe_request.approved_summary,
        "facts": [
            {
                "id": fact.fact_id,
                "kind": fact.kind.value,
                "text": fact.text,
            }
            for fact in safe_request.facts
        ],
        "output_schema": _OUTPUT_SCHEMA,
    }
    serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return (
        {"role": "system", "content": _SYSTEM_MESSAGE},
        {"role": "user", "content": serialized},
    )


def estimate_grounded_input_upper_bound(
    messages: tuple[dict[str, str], ...],
) -> int:
    """Return a conservative tokenizer-free upper bound over the complete request."""
    canonical = json.dumps(messages, ensure_ascii=False, separators=(",", ":"))
    return len(canonical.encode("utf-8"))


def _revalidate_request(request: GroundedChatRequest) -> GroundedChatRequest:
    if type(request) is not GroundedChatRequest:
        raise ValueError("GROUNDED_CHAT_REQUEST_INVALID")
    try:
        return GroundedChatRequest(
            masked_question=request.masked_question,
            intent=request.intent,
            service_name=request.service_name,
            approved_summary=request.approved_summary,
            facts=request.facts,
        )
    except (AttributeError, TypeError, ValueError):
        raise ValueError("GROUNDED_CHAT_REQUEST_INVALID") from None
