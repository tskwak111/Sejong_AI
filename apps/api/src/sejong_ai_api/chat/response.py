"""Server-owned chat response assembly from trusted typed records."""

from __future__ import annotations

from typing import Literal, cast
from uuid import UUID

from pydantic import AnyUrl

from sejong_ai_api.contracts.chat import (
    Fallback,
    FallbackResponse,
    FollowupResponse,
    Office,
    Source,
    SuccessResponse,
)
from sejong_ai_api.db.models import Intent, KnowledgeRecord, OfficeRecord

type FollowupOptionId = Literal[
    "intent.move-in",
    "intent.certificate",
    "intent.bulky-waste",
    "intent.local-tax",
]
type PublicFallbackReason = Literal[
    "INSUFFICIENT_GROUNDING",
    "PERSONAL_LOOKUP",
    "LEGAL_JUDGMENT",
    "OUT_OF_SCOPE",
    "PRIVACY_UNRESOLVED",
]

_FOLLOWUP_LABELS: dict[FollowupOptionId, str] = {
    "intent.move-in": "전입·주민등록",
    "intent.certificate": "증명서 발급",
    "intent.bulky-waste": "대형폐기물",
    "intent.local-tax": "지방세 일반 안내",
}
_FALLBACK_COPY: dict[PublicFallbackReason, tuple[str, str, tuple[str, ...]]] = {
    "INSUFFICIENT_GROUNDING": (
        "확인된 근거가 부족해요",
        "현재 승인된 공식 자료만으로는 정확히 안내하기 어려워요.",
        ("질문의 대상과 목적을 조금 더 구체적으로 적어 주세요.",),
    ),
    "PERSONAL_LOOKUP": (
        "개인 정보 조회는 할 수 없어요",
        "이 서비스는 개인별 신청·처리·고지 상태를 조회하지 않아요.",
        ("정부24 또는 해당 기관의 본인 인증 조회 경로를 이용해 주세요.",),
    ),
    "LEGAL_JUDGMENT": (
        "법적 판단은 제공하지 않아요",
        "개별 사실관계에 따른 법적 결론이나 책임을 단정할 수 없어요.",
        ("일반 절차 안내가 필요하면 법적 판단 없이 다시 질문해 주세요.",),
    ),
    "OUT_OF_SCOPE": (
        "지원 범위 밖의 질문이에요",
        "현재는 전입·주민등록, 증명서, 대형폐기물, 지방세 일반 안내를 지원해요.",
        ("지원 분야 중 하나를 골라 질문해 주세요.",),
    ),
    "PRIVACY_UNRESOLVED": (
        "개인정보를 안전하게 처리하지 못했어요",
        "개인정보를 빼거나 표현을 바꿔서 다시 질문해 주세요.",
        ("이름, 주소, 전화번호, 접수번호 등을 적지 마세요.",),
    ),
}


def build_success_response(
    *,
    request_id: UUID,
    record: KnowledgeRecord,
    office: OfficeRecord | None,
    confidence: float,
    context_token: str | None,
) -> SuccessResponse:
    """Build SUCCESS without inventing facts or source metadata."""

    used_fields = ["answer_summary"]
    if record.procedure_steps:
        used_fields.append("procedure_steps")
    if record.required_documents:
        used_fields.append("required_documents")
    if record.processing_time is not None:
        used_fields.append("processing_time")
    if record.fee is not None:
        used_fields.append("fee")
    used_fields.append("department")

    return SuccessResponse(
        request_id=request_id,
        answer_status="SUCCESS",
        answer_mode="TEMPLATE",
        intent=cast(
            Literal[
                "MOVE_IN_RESIDENT_REGISTRATION",
                "CERTIFICATE_ISSUANCE",
                "BULKY_WASTE",
                "LOCAL_TAX_GENERAL",
            ],
            record.category.value,
        ),
        confidence=confidence,
        summary=record.answer_summary,
        procedure_steps=list(record.procedure_steps),
        required_documents=list(record.required_documents),
        processing_time=record.processing_time,
        fee=record.fee,
        department=record.department,
        sources=[
            Source(
                source_id=record.public_id,
                title=record.source_title,
                url=AnyUrl(record.source_url),
                last_verified_at=record.last_verified_at,
                used_fields=used_fields,
            )
        ],
        office=_public_office(office),
        context_token=context_token,
    )


def build_followup_response(
    *,
    request_id: UUID,
    intent: Intent,
    confidence: float | None,
    option_ids: tuple[FollowupOptionId, ...],
    context_token: str | None,
) -> FollowupResponse:
    """Build a bounded follow-up response from server-defined option IDs."""

    if not option_ids or any(option_id not in _FOLLOWUP_LABELS for option_id in option_ids):
        raise ValueError("FOLLOWUP_OPTION_INVALID")
    if intent not in {
        Intent.MOVE_IN_RESIDENT_REGISTRATION,
        Intent.CERTIFICATE_ISSUANCE,
        Intent.BULKY_WASTE,
        Intent.LOCAL_TAX_GENERAL,
        Intent.UNKNOWN,
    }:
        raise ValueError("FOLLOWUP_INTENT_INVALID")

    return FollowupResponse(
        request_id=request_id,
        answer_status="FOLLOWUP",
        intent=cast(
            Literal[
                "MOVE_IN_RESIDENT_REGISTRATION",
                "CERTIFICATE_ISSUANCE",
                "BULKY_WASTE",
                "LOCAL_TAX_GENERAL",
                "UNKNOWN",
            ],
            intent.value,
        ),
        confidence=confidence,
        sources=[],
        office=None,
        followup_options=[_FOLLOWUP_LABELS[option_id] for option_id in option_ids],
        context_token=context_token,
    )


def build_fallback_response(
    *,
    request_id: UUID,
    intent: Intent,
    reason: PublicFallbackReason,
    office: OfficeRecord | None,
) -> FallbackResponse:
    """Build a fixed-copy policy fallback with no context or source payload."""

    if reason not in _FALLBACK_COPY:
        raise ValueError("FALLBACK_REASON_INVALID")
    title, message, next_actions = _FALLBACK_COPY[reason]
    candidate_eligible = reason == "INSUFFICIENT_GROUNDING"

    return FallbackResponse(
        request_id=request_id,
        answer_status="FALLBACK",
        intent=intent.value,
        confidence=None,
        sources=[],
        fallback=Fallback(
            reason=reason,
            title=title,
            message=message,
            next_actions=list(next_actions),
            candidate_eligible=candidate_eligible,
            office=_public_office(office),
        ),
        context_token=None,
    )


def _public_office(record: OfficeRecord | None) -> Office | None:
    if record is None:
        return None
    return Office(
        id=record.public_id,
        region=record.region.value,
        office_name=record.office_name,
        address=record.address,
        phone=record.phone,
        opening_hours=record.opening_hours,
        map_url=AnyUrl(record.map_url) if record.map_url is not None else None,
        source_title=record.source_title,
        source_url=AnyUrl(record.source_url),
        last_verified_at=record.last_verified_at,
    )


__all__ = [
    "build_fallback_response",
    "build_followup_response",
    "build_success_response",
]
