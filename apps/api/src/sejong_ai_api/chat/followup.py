"""Closed server-owned follow-up plans and option factories."""

from __future__ import annotations

from dataclasses import dataclass, field

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


@dataclass(frozen=True, slots=True, init=False)
class FollowupPlan:
    """A follow-up plan backed only by a fixed source or current typed catalog."""

    intent: Intent
    pending_slot: PendingSlot
    _catalog: TopicCatalog | None = field(repr=False)

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise ValueError("FOLLOWUP_PLAN_FACTORY_REQUIRED")

    @property
    def options(self) -> tuple[str, ...]:
        """Derive public labels from the fixed domain or current catalog source."""

        if (
            self.intent is Intent.UNKNOWN
            and self.pending_slot is PendingSlot.DOMAIN
            and self._catalog is None
        ):
            return _DOMAIN_FOLLOWUP_OPTIONS
        if (
            type(self.intent) is not Intent
            or self.intent not in _SUPPORTED_INTENTS
            or type(self.pending_slot) is not PendingSlot
            or type(self._catalog) is not TopicCatalog
        ):
            raise ValueError("FOLLOWUP_PLAN_SOURCE_INVALID")

        topics_by_id = {
            topic.record.public_id: topic
            for topic in self._catalog.topics
            if topic.record.category is self.intent
        }
        if not topics_by_id:
            raise ValueError("FOLLOWUP_PLAN_SOURCE_INVALID")
        if self.pending_slot is PendingSlot.REGION:
            return _REGION_FOLLOWUP_OPTIONS
        if self.pending_slot is PendingSlot.WASTE_ITEM:
            if self.intent is not Intent.BULKY_WASTE:
                raise ValueError("FOLLOWUP_PLAN_SOURCE_INVALID")
            return _WASTE_ITEM_FOLLOWUP_OPTIONS
        if self.pending_slot not in {
            PendingSlot.TOPIC_CHOICE,
            PendingSlot.CERTIFICATE_KIND,
        }:
            raise ValueError("FOLLOWUP_PLAN_SOURCE_INVALID")
        if (
            self.pending_slot is PendingSlot.CERTIFICATE_KIND
            and self.intent is not Intent.CERTIFICATE_ISSUANCE
        ):
            raise ValueError("FOLLOWUP_PLAN_SOURCE_INVALID")

        ordered_ids = _TOPIC_FOLLOWUP_ORDER[self.intent]
        use_certificate_short_labels = self.intent is Intent.CERTIFICATE_ISSUANCE
        options = tuple(
            (
                _CERTIFICATE_SHORT_LABELS[topic_id]
                if use_certificate_short_labels
                else topics_by_id[topic_id].record.service_name
            )
            for topic_id in ordered_ids
            if topic_id in topics_by_id
        )
        if (
            not 1 <= len(options) <= 5
            or len(set(options)) != len(options)
            or any(
                type(option) is not str or not option or option.strip() != option
                for option in options
            )
        ):
            raise ValueError("FOLLOWUP_PLAN_SOURCE_INVALID")
        return options


def _domain_followup_plan() -> FollowupPlan:
    plan = object.__new__(FollowupPlan)
    object.__setattr__(plan, "intent", Intent.UNKNOWN)
    object.__setattr__(plan, "pending_slot", PendingSlot.DOMAIN)
    object.__setattr__(plan, "_catalog", None)
    return plan


def _followup_plan_from_catalog(
    intent: Intent,
    pending_slot: PendingSlot,
    catalog: TopicCatalog,
) -> FollowupPlan | None:
    if type(catalog) is not TopicCatalog:
        return None
    if pending_slot is PendingSlot.DOMAIN:
        return _domain_followup_plan()
    plan = object.__new__(FollowupPlan)
    object.__setattr__(plan, "intent", intent)
    object.__setattr__(plan, "pending_slot", pending_slot)
    object.__setattr__(plan, "_catalog", catalog)
    try:
        _ = plan.options
    except (AttributeError, ValueError):
        return None
    return plan


__all__ = ["FollowupPlan"]
