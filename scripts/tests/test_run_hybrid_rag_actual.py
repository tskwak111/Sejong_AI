from __future__ import annotations

import asyncio
import importlib.util
import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_API_SOURCE = _REPOSITORY_ROOT / "apps" / "api" / "src"
if str(_API_SOURCE) not in sys.path:
    sys.path.insert(0, str(_API_SOURCE))

from sejong_ai_api.chat.classification import SafeQuestion  # noqa: E402
from sejong_ai_api.llm.classifier_contracts import (  # noqa: E402
    ClassifierDecision,
    ClassifierRoute,
)
from sejong_ai_api.llm.contracts import TokenUsage  # noqa: E402
from sejong_ai_api.llm.cost import estimate_cost_usd  # noqa: E402

_RUNNER_MODULE_NAME = "_sejong_hybrid_rag_actual_runner_test"
_RUNNER_PATH = _REPOSITORY_ROOT / "scripts" / "run_hybrid_rag_actual.py"


def _runner() -> ModuleType:
    cached = sys.modules.get(_RUNNER_MODULE_NAME)
    if cached is not None:
        return cached
    if not _RUNNER_PATH.is_file():
        pytest.fail("the hybrid rag actual runner is missing")
    spec = importlib.util.spec_from_file_location(_RUNNER_MODULE_NAME, _RUNNER_PATH)
    if spec is None or spec.loader is None:
        pytest.fail("the hybrid rag actual runner cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_RUNNER_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def test_actual_subset_is_the_exact_pii_free_allowlist() -> None:
    runner = _runner()
    fixtures = runner._load_fixtures(runner._FIXTURE_PATH)

    selected = tuple(case.fixture_id for case in fixtures if case.actual_subset)

    assert selected == (
        "HR-001",
        "HR-002",
        "HR-003",
        "HR-004",
        "HR-005",
        "HR-006",
        "HR-007",
        "HR-008",
        "HR-021",
        "HR-022",
        "HR-023",
        "HR-024",
        "HR-033",
        "HR-034",
        "HR-035",
        "HR-036",
        "HR-037",
        "HR-038",
        "HR-039",
        "HR-040",
    )
    assert all(case.group != "PRIVACY_POLICY" for case in fixtures if case.actual_subset)
    assert all(case.safe_for_provider for case in fixtures if case.actual_subset)
    assert sum(case.expected_provider_use for case in fixtures if case.actual_subset) == 9


def test_injected_offline_selector_writes_only_case_id_aggregates() -> None:
    runner = _runner()
    fixtures = runner._load_fixtures(runner._FIXTURE_PATH)
    selected = tuple(case for case in fixtures if case.actual_subset)
    catalog = runner._build_current_test_catalog()

    class Selector:
        def __init__(self) -> None:
            self.calls = 0

        async def classify(self, question: SafeQuestion) -> ClassifierDecision:
            self.calls += 1
            fixture = next(case for case in selected if case.question == question.text)
            if fixture.expected_route == "SUPPORTED":
                topic = catalog.find(fixture.expected_topic_id)
                assert topic is not None
                return ClassifierDecision(
                    route=ClassifierRoute.SUPPORTED,
                    intent=topic.record.category,
                    topic_id=topic.record.public_id,
                    coverage_id=topic.coverage.coverage_id,
                    pending_slot=None,
                )
            return ClassifierDecision(
                route=ClassifierRoute(fixture.expected_route),
                intent=None,
                topic_id=None,
                coverage_id=None,
                pending_slot=None,
            )

    selector = Selector()
    usage = TokenUsage(90, 0, 45)
    result = asyncio.run(
        runner._evaluate_selected(
            selected,
            selector=selector,
            usage=usage,
            cost_cap=Decimal("0.20"),
        )
    )
    report = runner._build_report(
        result=result,
        usage=usage,
        key_present=True,
        source_sha="a" * 40,
    )
    markdown = runner._report_to_markdown(report)

    assert selector.calls == 9
    assert result.cases_total == 20
    assert result.deterministic_count == 11
    assert result.provider_case_count == 9
    assert result.outbound_attempt_count == 9
    assert report["estimated_cost_usd_including_vat"] == str(estimate_cost_usd(usage))
    assert report["acceptance"] == "PASS"
    assert "HR-001" in markdown
    for forbidden in (
        selected[0].question,
        "api_key",
        "postgresql://",
        "payload",
        "response body",
    ):
        assert forbidden.casefold() not in markdown.casefold()


def test_cost_gate_stops_before_injected_selector_call() -> None:
    runner = _runner()
    fixtures = runner._load_fixtures(runner._FIXTURE_PATH)
    selected = tuple(case for case in fixtures if case.actual_subset)

    class Selector:
        calls = 0

        async def classify(self, _question: object) -> ClassifierDecision:
            self.calls += 1
            raise AssertionError("cost gate must stop before a provider call")

    selector = Selector()
    with pytest.raises(runner._RuntimeFailed):
        asyncio.run(
            runner._evaluate_selected(
                selected,
                selector=selector,
                usage=TokenUsage(0, 0, 0),
                cost_cap=Decimal("0.000001"),
            )
        )
    assert selector.calls == 0
