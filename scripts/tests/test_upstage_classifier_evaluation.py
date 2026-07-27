from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import httpx
import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_API_SOURCE = _REPOSITORY_ROOT / "apps" / "api" / "src"
if str(_API_SOURCE) not in sys.path:
    sys.path.insert(0, str(_API_SOURCE))

from sejong_ai_api.chat.classification import SafeQuestion  # noqa: E402
from sejong_ai_api.db.models import Intent  # noqa: E402
from sejong_ai_api.llm.classifier_contracts import (  # noqa: E402
    ClassifierDecision,
    ClassifierRoute,
)
from sejong_ai_api.llm.contracts import TokenUsage  # noqa: E402
from sejong_ai_api.llm.cost import estimate_cost_usd  # noqa: E402
from sejong_ai_api.llm.settings import UpstageClassifierSettings  # noqa: E402
from sejong_ai_api.llm.upstage_classifier import QuestionClassifier  # noqa: E402
from sejong_ai_api.privacy.redaction import redact_question  # noqa: E402

_RUNNER_MODULE_NAME = "_sejong_upstage_classifier_evaluation_test"
_RUNNER_PATH = _REPOSITORY_ROOT / "scripts" / "run_upstage_classifier_evaluation.py"


def _runner() -> ModuleType:
    cached = sys.modules.get(_RUNNER_MODULE_NAME)
    if cached is not None:
        return cached
    if not _RUNNER_PATH.is_file():
        pytest.fail("the Upstage classifier evaluation runner is missing")
    spec = importlib.util.spec_from_file_location(_RUNNER_MODULE_NAME, _RUNNER_PATH)
    if spec is None or spec.loader is None:
        pytest.fail("the Upstage classifier evaluation runner cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_RUNNER_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def _fixture_payload() -> list[dict[str, object]]:
    path = (
        _REPOSITORY_ROOT / "apps" / "api" / "tests" / "fixtures" / "classifier-60.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert type(payload) is list
    return payload


@dataclass
class _FakeClassifier:
    decisions: list[ClassifierDecision | None]
    calls: int = 0

    async def classify(self, _question: object) -> ClassifierDecision | None:
        decision = self.decisions[self.calls]
        self.calls += 1
        return decision


def test_fixture_validator_requires_exact_frozen_distribution(
    tmp_path: Path,
) -> None:
    runner = _runner()
    path = tmp_path / "classifier-60.json"
    path.write_text(
        json.dumps(_fixture_payload(), ensure_ascii=False), encoding="utf-8"
    )

    fixtures = runner._load_fixtures(path)

    assert len(fixtures) == 60
    assert sum(case.execution == "PROVIDER" for case in fixtures) == 20
    assert sum(case.execution == "DETERMINISTIC" for case in fixtures) == 40

    invalid = _fixture_payload()
    invalid[-1]["id"] = invalid[0]["id"]
    path.write_text(json.dumps(invalid, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(runner._FixturesInvalid):
        runner._load_fixtures(path)


def test_policy_privacy_fixture_cannot_be_marked_for_provider(
    tmp_path: Path,
) -> None:
    runner = _runner()
    payload = _fixture_payload()
    payload[-1]["execution"] = "PROVIDER"
    path = tmp_path / "classifier-60.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(runner._FixturesInvalid):
        runner._load_fixtures(path)


def test_historical_actual_runner_constructs_exact_cost_aware_ledger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    builder = getattr(runner, "_build_historical_ledger", None)
    assert callable(builder)
    settings = UpstageClassifierSettings(
        api_key="historical-test-key-not-a-real-secret"
    )
    real_ledger = builder(settings)
    assert type(real_ledger) is runner.ProviderAttemptLedger
    assert real_ledger.actual_cost_usd == Decimal("0")

    captured: dict[str, object] = {}
    sentinel = object()

    def capture_ledger(**kwargs: object) -> object:
        captured.update(kwargs)
        return sentinel

    monkeypatch.setattr(runner, "ProviderAttemptLedger", capture_ledger)

    ledger = builder(settings)

    assert ledger is sentinel
    assert captured == {
        "classifier_cap": 20,
        "generator_cap": 30,
        "combined_cap": 40,
        "cost_cap_usd": Decimal("0.05"),
        "classifier_worst_case_usd": estimate_cost_usd(TokenUsage(4096, 0, 128)),
        "generator_worst_case_usd": estimate_cost_usd(TokenUsage(4096, 0, 1024)),
    }


def test_evaluation_calls_only_provider_cases_and_keeps_policy_outbound_zero(
    tmp_path: Path,
) -> None:
    runner = _runner()
    payload = _fixture_payload()
    path = tmp_path / "classifier-60.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    fixtures = runner._load_fixtures(path)
    decisions: list[ClassifierDecision | None] = []
    for case in fixtures:
        if case.execution != "PROVIDER":
            continue
        expected_pair = runner._EXPECTED_SUPPORTED_TOPIC_COVERAGE.get(case.fixture_id)
        decisions.append(
            ClassifierDecision(
                route=ClassifierRoute(case.expected_code),
                intent=(
                    Intent(case.expected_intent)
                    if case.expected_intent is not None
                    else None
                ),
                topic_id=expected_pair[0] if expected_pair is not None else None,
                coverage_id=expected_pair[1] if expected_pair is not None else None,
                pending_slot=None,
            )
        )
    classifier = _FakeClassifier(decisions)

    result = asyncio.run(
        runner._evaluate(
            fixtures,
            classifier=classifier,
            usage=TokenUsage(400, 0, 100),
            cost_cap=Decimal("0.05"),
        )
    )

    assert classifier.calls == 20
    assert result.cases_total == 60
    assert result.outbound_attempt_count == 20
    assert result.policy_privacy_outbound_count == 0
    assert result.correct_count == 60
    assert result.skip_count == 0


def test_supported_mapping_is_exact_and_catalog_governed() -> None:
    runner = _runner()
    fixtures = runner._load_fixtures(
        _REPOSITORY_ROOT
        / "apps"
        / "api"
        / "tests"
        / "fixtures"
        / "classifier-60.json"
    )
    supported_provider_ids = {
        case.fixture_id
        for case in fixtures
        if case.execution == "PROVIDER" and case.expected_code == "SUPPORTED"
    }
    catalog = runner._build_current_test_catalog()
    governed_pairs = {
        (topic.record.public_id, topic.coverage.coverage_id)
        for topic in catalog.topics
    }

    assert len(catalog.topics) == 20
    assert set(runner._EXPECTED_SUPPORTED_TOPIC_COVERAGE) == supported_provider_ids
    assert set(runner._EXPECTED_SUPPORTED_TOPIC_COVERAGE.values()) <= governed_pairs


def test_decision_match_requires_the_exact_supported_topic_coverage_pair() -> None:
    runner = _runner()
    fixture = next(
        case
        for case in runner._load_fixtures(
            _REPOSITORY_ROOT
            / "apps"
            / "api"
            / "tests"
            / "fixtures"
            / "classifier-60.json"
        )
        if case.fixture_id == "C-11"
    )
    topic_id, coverage_id = runner._EXPECTED_SUPPORTED_TOPIC_COVERAGE["C-11"]
    exact = ClassifierDecision(
        route=ClassifierRoute.SUPPORTED,
        intent=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        topic_id=topic_id,
        coverage_id=coverage_id,
        pending_slot=None,
    )
    wrong = ClassifierDecision(
        route=ClassifierRoute.SUPPORTED,
        intent=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        topic_id="KB-MOVE-02",
        coverage_id="MOVE_IN_VISIT_REQUIREMENTS",
        pending_slot=None,
    )

    assert runner._decision_matches(fixture, exact) is True
    assert runner._decision_matches(fixture, wrong) is False


def test_c18_is_exact_no_topic_match_for_excluded_refrigerator_coverage() -> None:
    runner = _runner()
    fixture = next(
        case
        for case in runner._load_fixtures(
            _REPOSITORY_ROOT
            / "apps"
            / "api"
            / "tests"
            / "fixtures"
            / "classifier-60.json"
        )
        if case.fixture_id == "C-18"
    )
    catalog = runner._build_current_test_catalog()
    waste_general = catalog.find("KB-WASTE-01")

    assert waste_general is not None
    assert "전용 수거" in waste_general.coverage.coverage_label
    assert "제외" in waste_general.coverage.coverage_label
    assert fixture.expected_code == ClassifierRoute.NO_TOPIC_MATCH.value
    assert fixture.expected_intent == Intent.BULKY_WASTE.value
    assert fixture.fixture_id not in runner._EXPECTED_SUPPORTED_TOPIC_COVERAGE
    assert runner._EXPECTED_NEGATIVE_COVERAGE_DECISIONS == {
        "C-18": (
            ClassifierRoute.NO_TOPIC_MATCH,
            Intent.BULKY_WASTE,
            None,
            None,
        )
    }


def test_c18_rejects_supported_pair_and_matches_closed_negative_decision() -> None:
    runner = _runner()
    fixture = next(
        case
        for case in runner._load_fixtures(
            _REPOSITORY_ROOT
            / "apps"
            / "api"
            / "tests"
            / "fixtures"
            / "classifier-60.json"
        )
        if case.fixture_id == "C-18"
    )
    forced_supported = ClassifierDecision(
        route=ClassifierRoute.SUPPORTED,
        intent=Intent.BULKY_WASTE,
        topic_id="KB-WASTE-01",
        coverage_id="GENERAL_BULKY_DISPOSAL",
        pending_slot=None,
    )
    closed_negative = ClassifierDecision(
        route=ClassifierRoute.NO_TOPIC_MATCH,
        intent=Intent.BULKY_WASTE,
        topic_id=None,
        coverage_id=None,
        pending_slot=None,
    )

    assert runner._decision_matches(fixture, forced_supported) is False
    assert runner._decision_matches(fixture, closed_negative) is True


def test_explicit_negative_coverage_cases_have_no_forced_supported_pair() -> None:
    runner = _runner()
    fixtures = runner._load_fixtures(
        _REPOSITORY_ROOT
        / "apps"
        / "api"
        / "tests"
        / "fixtures"
        / "classifier-60.json"
    )
    excluded_markers = ("냉장고", "세율", "감면", "면제")
    explicit_negative_cases = tuple(
        case
        for case in fixtures
        if any(marker in case.question for marker in excluded_markers)
    )

    assert tuple(case.fixture_id for case in explicit_negative_cases) == ("C-18",)
    assert all(
        case.fixture_id not in runner._EXPECTED_SUPPORTED_TOPIC_COVERAGE
        for case in explicit_negative_cases
    )


def test_actual_classifier_passes_current_catalog_through_real_adapter_offline() -> None:
    runner = _runner()
    fixtures = runner._load_fixtures(
        _REPOSITORY_ROOT
        / "apps"
        / "api"
        / "tests"
        / "fixtures"
        / "classifier-60.json"
    )
    fixture = next(case for case in fixtures if case.fixture_id == "C-11")
    topic_id, coverage_id = runner._EXPECTED_SUPPORTED_TOPIC_COVERAGE[fixture.fixture_id]
    settings = UpstageClassifierSettings(
        api_key="historical-test-key-not-a-real-secret"
    )
    catalog = runner._build_current_test_catalog()
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": json.dumps(
                                {
                                    "route": "SUPPORTED",
                                    "intent": fixture.expected_intent,
                                    "topic_id": topic_id,
                                    "coverage_id": coverage_id,
                                    "pending_slot": None,
                                }
                            )
                        },
                    }
                ],
                "usage": {"prompt_tokens": 20, "completion_tokens": 10},
            },
        )

    async def exercise() -> ClassifierDecision | None:
        recorder = runner._UsageRecorder()
        ledger = runner._build_historical_ledger(settings)
        async with httpx.AsyncClient(
            base_url=settings.base_url,
            transport=httpx.MockTransport(handler),
            event_hooks={"response": [recorder.capture]},
        ) as client:
            actual = runner._ActualClassifier(
                classifier=QuestionClassifier(
                    settings=settings,
                    client=client,
                    ledger=ledger,
                ),
                ledger=ledger,
                recorder=recorder,
                settings=settings,
                catalog=catalog,
            )
            decision = await actual.classify(
                SafeQuestion(redact_question(fixture.question))
            )
            assert actual.outbound_attempt_count == 1
            assert actual.usage_response_count == 1
            return decision

    decision = asyncio.run(exercise())

    assert calls == 1
    assert decision is not None
    assert runner._decision_matches(fixture, decision) is True


def test_report_contains_aggregates_only_and_no_payload() -> None:
    runner = _runner()
    report = runner._build_report(
        source_sha="a" * 40,
        model="solar-pro3",
        cases_total=60,
        deterministic_count=40,
        provider_case_count=20,
        correct_count=60,
        skip_count=0,
        invalid_count=0,
        policy_privacy_outbound_count=0,
        outbound_attempt_count=20,
        usage=TokenUsage(400, 0, 100),
        estimated_cost=Decimal("0.000132"),
        cost_cap=Decimal("0.05"),
        elapsed_ms=1234,
    )
    markdown = runner._report_to_markdown(report)

    assert tuple(report) == runner._REPORT_FIELDS
    assert report["estimated_cost_usd_including_vat"] == "0.000132"
    assert report["acceptance"] == "PASS"
    for forbidden in (
        "question",
        "masked_question",
        "response",
        "prompt",
        "api_key",
        "합성 질문",
    ):
        assert forbidden not in markdown.casefold()


def test_exact_classifier_profile_and_conservative_cost_are_required() -> None:
    runner = _runner()
    settings = UpstageClassifierSettings(api_key="not-a-real-secret")

    runner._validate_settings(settings, provider_case_count=20)

    with pytest.raises(runner._ConfigurationInvalid):
        runner._validate_settings(
            UpstageClassifierSettings(
                api_key="not-a-real-secret",
                classifier_attempt_cap=19,
            ),
            provider_case_count=20,
        )


def test_cli_rejects_noncanonical_paths_before_network(tmp_path: Path) -> None:
    runner = _runner()

    with pytest.raises(runner._ArgumentsInvalid):
        runner._parse_args(
            [
                "--fixture",
                str(tmp_path / "other.json"),
                "--report",
                str(tmp_path / "other.md"),
            ]
        )
