"""Minimal source-free prompt for the closed Upstage question classifier."""

from __future__ import annotations

import json

from sejong_ai_api.chat.classification import SafeQuestion

_SYSTEM_MESSAGE = (
    "시민 질문을 지정된 폐쇄형 분류값으로만 분류하세요. "
    "지원 범위는 전입·주민등록, 증명서 발급, 대형폐기물, 지방세 일반 안내뿐입니다. "
    "이사 뒤 새 거주지나 주소를 행정기관에 반영하려는 표현은 "
    "MOVE_IN_RESIDENT_REGISTRATION입니다. "
    "등본·초본·인감 등 행정 증명 발급은 CERTIFICATE_ISSUANCE입니다. "
    "큰 가구·가전·매트리스처럼 종량제 봉투에 담기 어려운 물건을 버리려는 표현은 "
    "BULKY_WASTE입니다. 지방세·자동차세·재산세의 일반 절차는 LOCAL_TAX_GENERAL입니다. "
    "SUPPORTED는 지원 범위와 의도가 명확할 때 사용하고 intent를 반드시 채우세요. "
    "CIVIC_SCOPE_GAP은 행정·복지·공공 민원이지만 위 네 지원 분야 밖일 때 사용하세요. "
    "월세·장학·수당·지원금, 여권·출생·면허·교통·보건·동물등록은 "
    "CIVIC_SCOPE_GAP 예시입니다. "
    "NON_CIVIC은 날씨·맛집·일상 대화처럼 행정 민원이 아닐 때 사용하세요. "
    "NEEDS_FOLLOWUP은 지원 분야이지만 CERTIFICATE_KIND, REGION 또는 WASTE_ITEM 중 "
    "필수 정보 하나가 부족할 때만 사용하고 intent와 pending_slot을 채우세요. "
    "서버가 알려 준 주제 ID가 없으므로 topic_id는 null로 두세요. "
    "답변, 출처, 보관 여부, 후보 생성 여부를 작성하지 마세요. "
    "응답은 정확히 route, intent, topic_id, pending_slot 네 필드의 JSON 객체 하나만 작성하세요."
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
