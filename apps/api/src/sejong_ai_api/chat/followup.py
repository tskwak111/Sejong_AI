"""Closed server-owned follow-up plans and option factories."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeGuard

from sejong_ai_api.chat.topic_catalog import TopicCatalog
from sejong_ai_api.db.models import Intent
from sejong_ai_api.llm.classifier_contracts import PendingSlot

_SUPPORTED_INTENTS = frozenset(
    {
        Intent.MOVE_IN_RESIDENT_REGISTRATION,
        Intent.CERTIFICATE_ISSUANCE,
        Intent.BULKY_WASTE,
        Intent.LOCAL_TAX_GENERAL,
    }
)
_DOMAIN_FOLLOWUP_OPTIONS = (
    "전입·주민등록",
    "증명서 발급",
    "대형폐기물",
    "지방세 일반 안내",
)
_REGION_FOLLOWUP_OPTIONS = ("아름동", "도담동", "조치원읍")
_WASTE_ITEM_FOLLOWUP_OPTIONS = ("버리려는 물품을 적어 주세요",)
_TOPIC_FOLLOWUP_ORDER: dict[Intent, tuple[str, ...]] = {
    Intent.MOVE_IN_RESIDENT_REGISTRATION: (
        "KB-MOVE-01",
        "KB-MOVE-02",
        "KB-MOVE-03",
        "KB-MOVE-04",
    ),
    Intent.CERTIFICATE_ISSUANCE: (
        "KB-CERT-02",
        "KB-CERT-03",
        "KB-CERT-01",
    ),
    Intent.BULKY_WASTE: (
        "KB-WASTE-01",
        "KB-WASTE-02",
        "KB-WASTE-03",
        "KB-WASTE-04",
        "KB-WASTE-05",
    ),
    Intent.LOCAL_TAX_GENERAL: (
        "KB-TAX-01",
        "KB-TAX-02",
        "KB-TAX-03",
        "KB-TAX-04",
        "KB-TAX-05",
    ),
}
_CERTIFICATE_SHORT_LABELS = {
    "KB-CERT-02": "주민등록등본 발급",
    "KB-CERT-03": "주민등록초본 발급",
    "KB-CERT-01": "등본과 초본의 차이",
}
_FOLLOWUP_PLAN_PROVENANCE = object()


def _validate_followup_plan(
    intent: Intent,
    pending_slot: PendingSlot,
    options: tuple[str, ...],
) -> None:
    if (
        type(intent) is not Intent
        or type(pending_slot) is not PendingSlot
        or type(options) is not tuple
        or not 1 <= len(options) <= 5
        or len(set(options)) != len(options)
        or any(
            type(option) is not str or not option or option.strip() != option for option in options
        )
    ):
        raise ValueError("FOLLOWUP_PLAN_INVALID")
    if pending_slot is PendingSlot.DOMAIN:
        if intent is not Intent.UNKNOWN:
            raise ValueError("FOLLOWUP_PLAN_INVALID")
        return
    if intent not in _SUPPORTED_INTENTS:
        raise ValueError("FOLLOWUP_PLAN_INVALID")
    if pending_slot is PendingSlot.CERTIFICATE_KIND and intent is not Intent.CERTIFICATE_ISSUANCE:
        raise ValueError("FOLLOWUP_PLAN_INVALID")
    if pending_slot is PendingSlot.WASTE_ITEM and intent is not Intent.BULKY_WASTE:
        raise ValueError("FOLLOWUP_PLAN_INVALID")


@dataclass(frozen=True, slots=True, init=False)
class FollowupPlan:
    """A follow-up plan that only this module's closed factories can mint."""

    intent: Intent
    pending_slot: PendingSlot
    options: tuple[str, ...]
    _provenance: object = field(repr=False, compare=False)

    def __init__(
        self,
        intent: Intent,
        pending_slot: PendingSlot,
        options: tuple[str, ...],
    ) -> None:
        _validate_followup_plan(intent, pending_slot, options)
        raise ValueError("FOLLOWUP_PLAN_FACTORY_REQUIRED")


def _mint_followup_plan(
    intent: Intent,
    pending_slot: PendingSlot,
    options: tuple[str, ...],
) -> FollowupPlan:
    _validate_followup_plan(intent, pending_slot, options)
    plan = object.__new__(FollowupPlan)
    object.__setattr__(plan, "intent", intent)
    object.__setattr__(plan, "pending_slot", pending_slot)
    object.__setattr__(plan, "options", options)
    object.__setattr__(plan, "_provenance", _FOLLOWUP_PLAN_PROVENANCE)
    return plan


def _is_server_owned_followup_plan(value: object) -> TypeGuard[FollowupPlan]:
    return (
        type(value) is FollowupPlan
        and getattr(value, "_provenance", None) is _FOLLOWUP_PLAN_PROVENANCE
    )


def _domain_followup_plan() -> FollowupPlan:
    return _mint_followup_plan(
        Intent.UNKNOWN,
        PendingSlot.DOMAIN,
        _DOMAIN_FOLLOWUP_OPTIONS,
    )


def _region_followup_plan(intent: Intent) -> FollowupPlan:
    return _mint_followup_plan(intent, PendingSlot.REGION, _REGION_FOLLOWUP_OPTIONS)


def _waste_item_followup_plan() -> FollowupPlan:
    return _mint_followup_plan(
        Intent.BULKY_WASTE,
        PendingSlot.WASTE_ITEM,
        _WASTE_ITEM_FOLLOWUP_OPTIONS,
    )


def _followup_plan_from_catalog(
    intent: Intent,
    pending_slot: PendingSlot,
    catalog: TopicCatalog,
) -> FollowupPlan | None:
    if type(catalog) is not TopicCatalog:
        return None
    if pending_slot is PendingSlot.DOMAIN:
        return _domain_followup_plan()
    if pending_slot is PendingSlot.REGION:
        return _region_followup_plan(intent)
    if pending_slot is PendingSlot.WASTE_ITEM:
        return _waste_item_followup_plan() if intent is Intent.BULKY_WASTE else None
    if pending_slot not in {
        PendingSlot.TOPIC_CHOICE,
        PendingSlot.CERTIFICATE_KIND,
    }:
        return None
    if intent not in _SUPPORTED_INTENTS:
        return None
    if pending_slot is PendingSlot.CERTIFICATE_KIND and intent is not Intent.CERTIFICATE_ISSUANCE:
        return None

    topics_by_id = {
        topic.record.public_id: topic for topic in catalog.topics if topic.record.category is intent
    }
    ordered_ids = _TOPIC_FOLLOWUP_ORDER[intent]
    use_certificate_short_labels = intent is Intent.CERTIFICATE_ISSUANCE
    options = tuple(
        (
            _CERTIFICATE_SHORT_LABELS[topic_id]
            if use_certificate_short_labels
            else topics_by_id[topic_id].record.service_name
        )
        for topic_id in ordered_ids
        if topic_id in topics_by_id
    )
    if not options:
        return None
    return _mint_followup_plan(intent, pending_slot, options)


__all__ = ["FollowupPlan"]
