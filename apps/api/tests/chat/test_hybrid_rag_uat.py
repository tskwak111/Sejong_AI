from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import count
from pathlib import Path
from uuid import UUID

import pytest

from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.context import ContextTokenCodec
from sejong_ai_api.chat.service import ChatService
from sejong_ai_api.chat.topic_catalog import (
    TopicCatalog,
    build_topic_catalog,
    load_topic_coverage,
)
from sejong_ai_api.contracts.chat import ChatRequest
from sejong_ai_api.db.models import (
    Intent,
    InteractionWrite,
    InteractionWriteResult,
    KnowledgeRecord,
    OfficeRecord,
    Region,
)
from sejong_ai_api.llm.classifier_contracts import ClassifierDecision, ClassifierRoute

from .test_official_examples import COVERAGE_PATH, load_records

FIXTURE_PATH = Path(__file__).with_name("fixtures") / "hybrid-rag-uat.v1.json"
REPORT_PATH = (
    Path(__file__).resolve().parents[4]
    / "docs"
    / "test-reports"
    / "CHAT-HYBRID-RAG-001-OFFLINE-UAT.md"
)
GROUP_COUNTS = {
    "PARAPHRASE_SUCCESS": 20,
    "TOPIC_DISTINCTION": 8,
    "GENERIC_FOLLOWUP": 4,
    "NO_TOPIC_GROUNDING": 4,
    "SCOPE_OR_NON_CIVIC": 4,
    "CONTEXT": 4,
    "PRIVACY_POLICY": 4,
}
CASE_KEYS = {
    "id",
    "group",
    "question",
    "expected_route",
    "expected_intent",
    "expected_topic_id",
    "expected_provider_use",
    "expected_storage",
    "actual_subset",
}
CONTEXT_SEEDS = {
    "HR-041": "이사했는데 전입신고는 어떻게 하나요?",
    "HR-042": "대형폐기물은 어떻게 신청하나요?",
    "HR-043": "주민등록등본은 어떻게 발급하나요?",
    "HR-044": "대형폐기물은 무슨 요일에 내놓나요?",
}


@dataclass(frozen=True, slots=True)
class UatCase:
    case_id: str
    group: str
    question: str
    expected_route: str
    expected_intent: Intent
    expected_topic_id: str | None
    expected_provider_use: int
    expected_storage: str
    actual_subset: bool


def _case(raw: object) -> UatCase:
    assert type(raw) is dict
    assert set(raw) == CASE_KEYS
    assert type(raw["id"]) is str
    assert type(raw["group"]) is str
    assert type(raw["question"]) is str
    assert type(raw["expected_route"]) is str
    assert type(raw["expected_intent"]) is str
    assert raw["expected_topic_id"] is None or type(raw["expected_topic_id"]) is str
    assert raw["expected_provider_use"] in {0, 1}
    assert type(raw["expected_storage"]) is str
    assert type(raw["actual_subset"]) is bool
    return UatCase(
        case_id=raw["id"],
        group=raw["group"],
        question=raw["question"],
        expected_route=raw["expected_route"],
        expected_intent=Intent(raw["expected_intent"]),
        expected_topic_id=raw["expected_topic_id"],
        expected_provider_use=raw["expected_provider_use"],
        expected_storage=raw["expected_storage"],
        actual_subset=raw["actual_subset"],
    )


def load_cases() -> tuple[UatCase, ...]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert type(payload) is dict
    assert set(payload) == {"schema_version", "data_kind", "cases"}
    assert payload["schema_version"] == 1
    assert payload["data_kind"] == "SYNTHETIC_CHAT_UAT"
    assert type(payload["cases"]) is list
    return tuple(_case(case) for case in payload["cases"])


def test_fixture_is_the_exact_frozen_48_case_hybrid_rag_uat() -> None:
    cases = load_cases()

    assert len(cases) == 48
    assert Counter(case.group for case in cases) == GROUP_COUNTS
    assert len({case.case_id for case in cases}) == 48
    actual_subset = tuple(case for case in cases if case.actual_subset)
    assert len(actual_subset) == 20
    assert Counter(
        (
            "PARAPHRASE_SUCCESS"
            if case.group == "PARAPHRASE_SUCCESS"
            else "TOPIC_DISTINCTION"
            if case.group == "TOPIC_DISTINCTION"
            else "NO_TOPIC_OR_FOLLOWUP"
            if case.group in {"NO_TOPIC_GROUNDING", "GENERIC_FOLLOWUP"}
            else "SCOPE_OR_NON_CIVIC"
        )
        for case in actual_subset
    ) == {
        "PARAPHRASE_SUCCESS": 8,
        "TOPIC_DISTINCTION": 4,
        "NO_TOPIC_OR_FOLLOWUP": 4,
        "SCOPE_OR_NON_CIVIC": 4,
    }
    for case in cases:
        if case.group == "PRIVACY_POLICY":
            assert case.expected_provider_use == 0
            assert case.actual_subset is False


def test_runtime_active_official_catalog_intersection_is_currently_nineteen() -> None:
    catalog = build_topic_catalog(load_records(), load_topic_coverage(COVERAGE_PATH))

    assert len(catalog.topics) == 19
    assert catalog.provider_eligible is True


def test_offline_report_never_repeats_synthetic_privacy_case_text() -> None:
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert all(
        case.question not in report
        for case in load_cases()
        if case.group == "PRIVACY_POLICY"
    )


class RecordingRepository:
    def __init__(self, records: Sequence[KnowledgeRecord]) -> None:
        self.records = tuple(records)
        self.events: list[InteractionWrite] = []
        self.scope_gaps: list[str] = []

    async def list_active_kb(self, intent: Intent) -> Sequence[KnowledgeRecord]:
        return tuple(record for record in self.records if record.category is intent)

    async def list_offices(self, _region: Region, _intent: Intent) -> Sequence[OfficeRecord]:
        return ()

    async def record_interaction(self, event: InteractionWrite) -> InteractionWriteResult:
        self.events.append(event)
        return InteractionWriteResult(
            interaction_id=UUID("22222222-2222-4222-8222-222222222222"),
            failed_question_id=None,
        )

    async def record_civic_scope_gap(self, masked_question: str) -> None:
        self.scope_gaps.append(masked_question)


@dataclass
class ClosedFakeClassifier:
    cases_by_question: dict[str, UatCase]
    calls: list[str] = field(default_factory=list)

    async def classify(
        self,
        question: SafeQuestion,
        catalog: TopicCatalog,
    ) -> ClassifierDecision:
        case = self.cases_by_question[question.text]
        self.calls.append(case.case_id)
        assert catalog.provider_eligible is True
        if case.expected_route == "SUPPORTED":
            assert case.expected_topic_id is not None
            topic = catalog.find(case.expected_topic_id)
            assert topic is not None
            return ClassifierDecision(
                route=ClassifierRoute.SUPPORTED,
                intent=case.expected_intent,
                topic_id=topic.record.public_id,
                coverage_id=topic.coverage.coverage_id,
                pending_slot=None,
            )
        if case.expected_route == "NO_TOPIC_MATCH":
            return ClassifierDecision(
                route=ClassifierRoute.NO_TOPIC_MATCH,
                intent=case.expected_intent,
                topic_id=None,
                coverage_id=None,
                pending_slot=None,
            )
        assert case.expected_route == "CIVIC_SCOPE_GAP"
        return ClassifierDecision(
            route=ClassifierRoute.CIVIC_SCOPE_GAP,
            intent=None,
            topic_id=None,
            coverage_id=None,
            pending_slot=None,
        )


def _service(
    repository: RecordingRepository,
    classifier: ClosedFakeClassifier,
) -> ChatService:
    ticks = count(1_000_000, 5_000_000)
    return ChatService(
        repository=repository,
        context_codec=ContextTokenCodec(secret=b"x" * 32, clock=lambda: 1_000),
        request_id_factory=lambda: UUID("11111111-1111-4111-8111-111111111111"),
        monotonic_ns=lambda: next(ticks),
        is_test=True,
        question_classifier=classifier,
        topic_coverage=load_topic_coverage(COVERAGE_PATH),
    )


def _expected_answer_status(case: UatCase) -> str:
    if case.expected_route == "SUPPORTED":
        return "SUCCESS"
    if case.expected_route == "NEEDS_FOLLOWUP":
        return "FOLLOWUP"
    return "FALLBACK"


def _expected_fallback_reason(case: UatCase) -> str | None:
    return {
        "NO_TOPIC_MATCH": "INSUFFICIENT_GROUNDING",
        "CIVIC_SCOPE_GAP": "CIVIC_SCOPE_GAP",
        "NON_CIVIC": "OUT_OF_SCOPE",
        "PERSONAL_LOOKUP": "PERSONAL_LOOKUP",
        "LEGAL_JUDGMENT": "LEGAL_JUDGMENT",
    }.get(case.expected_route)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", load_cases(), ids=lambda case: case.case_id)
async def test_every_frozen_case_uses_the_real_offline_hybrid_rag_pipeline(
    case: UatCase,
) -> None:
    repository = RecordingRepository(load_records())
    classifier = ClosedFakeClassifier(
        {
            provider_case.question: provider_case
            for provider_case in load_cases()
            if provider_case.expected_provider_use
        }
    )
    selected = _service(repository, classifier)
    context_token: str | None = None
    if case.case_id in CONTEXT_SEEDS:
        seeded = await selected.answer(ChatRequest(question=CONTEXT_SEEDS[case.case_id]))
        assert seeded.answer_status == "SUCCESS"
        context_token = seeded.context_token
    before_events = len(repository.events)
    before_scope_gaps = len(repository.scope_gaps)
    before_calls = len(classifier.calls)

    response = await selected.answer(
        ChatRequest(question=case.question, context_token=context_token)
    )

    assert response.answer_status == _expected_answer_status(case)
    assert response.intent == case.expected_intent.value
    expected_fallback_reason = _expected_fallback_reason(case)
    if expected_fallback_reason is None:
        assert response.answer_status != "FALLBACK"
    else:
        assert response.fallback is not None
        assert response.fallback.reason == expected_fallback_reason
    assert len(classifier.calls) - before_calls == case.expected_provider_use
    if case.expected_topic_id is None:
        assert response.sources == []
    else:
        assert [source.source_id for source in response.sources] == [case.expected_topic_id]

    event_delta = repository.events[before_events:]
    scope_delta = repository.scope_gaps[before_scope_gaps:]
    if case.expected_storage == "VALUE_FREE_SUCCESS":
        assert len(event_delta) == 1
        assert event_delta[0].masked_question is None
        assert event_delta[0].used_source_ids == (case.expected_topic_id,)
        assert scope_delta == []
    elif case.expected_storage == "VALUE_FREE_FOLLOWUP":
        assert len(event_delta) == 1
        assert event_delta[0].masked_question is None
        assert event_delta[0].used_source_ids == ()
        assert scope_delta == []
    elif case.expected_storage == "MASKED_GROUNDING_FAILURE":
        assert len(event_delta) == 1
        assert event_delta[0].masked_question == case.question
        assert event_delta[0].used_source_ids == ()
        assert scope_delta == []
    elif case.expected_route == "CIVIC_SCOPE_GAP":
        assert event_delta == []
        assert scope_delta == [case.question]
    else:
        assert case.expected_storage in {"VALUE_FREE_SCOPE", "VALUE_FREE_PRIVACY"}
        assert event_delta == []
        assert scope_delta == []

    if case.group == "PRIVACY_POLICY":
        raw_phone = case.question.split()[1]
        assert raw_phone not in repr(classifier.calls)
        assert raw_phone not in repr(repository.events)
        assert raw_phone not in repr(repository.scope_gaps)
