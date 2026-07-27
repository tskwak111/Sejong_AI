"""Run the fixed, PII-free 60-case Upstage classifier acceptance once."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, NoReturn, Protocol

import httpx

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_API_SOURCE = _REPOSITORY_ROOT / "apps" / "api" / "src"
_FIXTURE_PATH = (
    _REPOSITORY_ROOT / "apps" / "api" / "tests" / "fixtures" / "classifier-60.json"
)
_REPORT_PATH = (
    _REPOSITORY_ROOT / "docs" / "test-reports" / "CHAT-NATURAL-001-UPSTAGE-ACTUAL.md"
)
_OFFICIAL_RECORDS_PATH = (
    _REPOSITORY_ROOT
    / "data"
    / "official"
    / "releases"
    / "0.1.0-initial.2"
    / "kb_records.json"
)
_COVERAGE_PATH = _REPOSITORY_ROOT / "data" / "retrieval" / "topic-coverage.v1.json"
if str(_API_SOURCE) not in sys.path:
    sys.path.insert(0, str(_API_SOURCE))

from sejong_ai_api.chat.classification import (  # noqa: E402
    ClassificationOutcome,
    SafeQuestion,
    classify_question,
)
from sejong_ai_api.chat.topic_catalog import (  # noqa: E402
    TopicCatalog,
    build_topic_catalog,
    load_topic_coverage,
)
from sejong_ai_api.db.models import (  # noqa: E402
    FallbackReason,
    Intent,
    KnowledgeRecord,
)
from sejong_ai_api.llm.classifier_contracts import (  # noqa: E402
    ClassifierDecision,
    ClassifierRoute,
    PendingSlot,
)
from sejong_ai_api.llm.contracts import TokenUsage  # noqa: E402
from sejong_ai_api.llm.cost import RUN_COST_CAP_USD, estimate_cost_usd  # noqa: E402
from sejong_ai_api.llm.limits import ProviderAttemptLedger  # noqa: E402
from sejong_ai_api.llm.settings import (  # noqa: E402
    UPSTAGE_BASE_URL,
    UPSTAGE_CLASSIFIER_ATTEMPT_CAP,
    UPSTAGE_CLASSIFIER_MAX_INPUT_CHARS,
    UPSTAGE_CLASSIFIER_MAX_OUTPUT_TOKENS,
    UPSTAGE_CLASSIFIER_MAX_RETRIES,
    UPSTAGE_CLASSIFIER_TIMEOUT_SECONDS,
    UPSTAGE_COMBINED_ATTEMPT_CAP,
    UPSTAGE_GENERATOR_ATTEMPT_CAP,
    UPSTAGE_MAX_CONCURRENCY,
    UPSTAGE_MAX_INPUT_TOKENS,
    UPSTAGE_MAX_OUTPUT_TOKENS,
    UPSTAGE_MODEL,
    UPSTAGE_PROVIDER,
    UpstageClassifierSettings,
    load_upstage_classifier_settings,
)
from sejong_ai_api.llm.upstage_classifier import QuestionClassifier  # noqa: E402
from sejong_ai_api.privacy.redaction import redact_question  # noqa: E402

_EXPECTED_CASES = 60
_EXPECTED_PROVIDER_CASES = 20
_EXPECTED_DETERMINISTIC_CASES = 40
_EXPECTED_GROUPS = {
    "SUPPORTED": 20,
    "NON_CIVIC": 10,
    "CIVIC_SCOPE_GAP": 10,
    "NEEDS_FOLLOWUP": 10,
    "POLICY_PRIVACY": 10,
}
_EXPECTED_SUPPORTED_TOPIC_COVERAGE = {
    "C-11": ("KB-MOVE-01", "MOVE_IN_OVERVIEW_APPLICATION"),
    "C-12": ("KB-MOVE-02", "MOVE_IN_VISIT_REQUIREMENTS"),
    "C-13": ("KB-MOVE-01", "MOVE_IN_OVERVIEW_APPLICATION"),
    "C-14": ("KB-MOVE-03", "MOVE_IN_ONLINE_APPLICATION"),
    "C-15": ("KB-MOVE-01", "MOVE_IN_OVERVIEW_APPLICATION"),
    "C-16": ("KB-WASTE-01", "GENERAL_BULKY_DISPOSAL"),
    "C-17": ("KB-WASTE-01", "GENERAL_BULKY_DISPOSAL"),
    "C-19": ("KB-WASTE-01", "GENERAL_BULKY_DISPOSAL"),
    "C-20": ("KB-WASTE-01", "GENERAL_BULKY_DISPOSAL"),
}
_EXPECTED_NEGATIVE_COVERAGE_DECISIONS = {
    "C-18": (
        ClassifierRoute.NO_TOPIC_MATCH,
        Intent.BULKY_WASTE,
        None,
        None,
    )
}
_FIXTURE_KEYS = frozenset(
    {
        "id",
        "group",
        "execution",
        "question",
        "expected_code",
        "expected_intent",
        "expected_pending_slot",
    }
)
_EXPECTED_CODES = frozenset(
    {
        *(route.value for route in ClassifierRoute),
        FallbackReason.PERSONAL_LOOKUP.value,
        FallbackReason.LEGAL_JUDGMENT.value,
    }
)
_SENSITIVE_FIXTURE_PATTERN = re.compile(
    r"(?:[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    r"|01[016789][-\s]?\d{3,4}[-\s]?\d{4}"
    r"|\d{6}[-\s]?[1-4]\d{6}"
    r"|(?:sk|up)_[A-Za-z0-9_-]{12,}"
    r"|postgres(?:ql)?://)",
    re.IGNORECASE,
)
_REPORT_FIELDS = (
    "source_sha",
    "model",
    "cases_total",
    "deterministic_count",
    "provider_case_count",
    "correct_count",
    "skip_count",
    "invalid_count",
    "policy_privacy_outbound_count",
    "outbound_attempt_count",
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "estimated_cost_usd_including_vat",
    "cost_cap_usd_including_vat",
    "elapsed_ms",
    "acceptance",
)


class _ArgumentsInvalid(ValueError):
    """The runner accepts only the two canonical repository paths."""


class _ConfigurationInvalid(RuntimeError):
    """The exact approved provider profile is unavailable."""


class _FixturesInvalid(RuntimeError):
    """The frozen fixture is not the approved synthetic corpus."""


class _RuntimeFailed(RuntimeError):
    """The actual run could not produce complete content-free evidence."""


class _AcceptanceFailed(RuntimeError):
    """The run completed but did not satisfy the frozen acceptance."""

    def __init__(self, report: dict[str, object]) -> None:
        super().__init__("CLASSIFIER_ACCEPTANCE_FAILED")
        self.report = report


class _Classifier(Protocol):
    async def classify(self, question: SafeQuestion) -> ClassifierDecision | None: ...


@dataclass(frozen=True, slots=True)
class _RunnerOptions:
    fixture_path: Path
    report_path: Path


@dataclass(frozen=True, slots=True)
class _Fixture:
    fixture_id: str
    group: str
    execution: str
    question: str
    expected_code: str
    expected_intent: str | None
    expected_pending_slot: str | None


@dataclass(frozen=True, slots=True)
class _EvaluationResult:
    cases_total: int
    deterministic_count: int
    provider_case_count: int
    correct_count: int
    skip_count: int
    invalid_count: int
    policy_privacy_outbound_count: int
    outbound_attempt_count: int


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> NoReturn:
        raise _ArgumentsInvalid from None


def _parse_args(argv: Sequence[str] | None = None) -> _RunnerOptions:
    parser = _SafeArgumentParser(add_help=False)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--report", required=True)
    namespace = parser.parse_args(argv)
    fixture_path = _resolve_repository_path(namespace.fixture)
    report_path = _resolve_repository_path(namespace.report)
    if fixture_path != _FIXTURE_PATH.resolve() or report_path != _REPORT_PATH.resolve():
        raise _ArgumentsInvalid
    return _RunnerOptions(fixture_path=fixture_path, report_path=report_path)


def _resolve_repository_path(value: object) -> Path:
    if type(value) is not str or not value or "\x00" in value:
        raise _ArgumentsInvalid
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = _REPOSITORY_ROOT / candidate
    return candidate.resolve()


def _load_fixtures(path: Path) -> tuple[_Fixture, ...]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise _FixturesInvalid from None
    if type(payload) is not list or len(payload) != _EXPECTED_CASES:
        raise _FixturesInvalid

    fixtures: list[_Fixture] = []
    for raw in payload:
        if type(raw) is not dict or frozenset(raw) != _FIXTURE_KEYS:
            raise _FixturesInvalid
        fixture = _parse_fixture(raw)
        _validate_synthetic_question(fixture.question)
        fixtures.append(fixture)

    ids = tuple(fixture.fixture_id for fixture in fixtures)
    if len(set(ids)) != _EXPECTED_CASES or ids != tuple(
        f"C-{index:02d}" for index in range(1, _EXPECTED_CASES + 1)
    ):
        raise _FixturesInvalid
    if Counter(fixture.group for fixture in fixtures) != Counter(_EXPECTED_GROUPS):
        raise _FixturesInvalid
    if (
        sum(fixture.execution == "PROVIDER" for fixture in fixtures)
        != _EXPECTED_PROVIDER_CASES
    ):
        raise _FixturesInvalid
    if (
        sum(fixture.execution == "DETERMINISTIC" for fixture in fixtures)
        != _EXPECTED_DETERMINISTIC_CASES
    ):
        raise _FixturesInvalid
    if any(
        fixture.group == "POLICY_PRIVACY" and fixture.execution != "DETERMINISTIC"
        for fixture in fixtures
    ):
        raise _FixturesInvalid
    supported_provider_ids = {
        fixture.fixture_id
        for fixture in fixtures
        if fixture.execution == "PROVIDER"
        and fixture.expected_code == ClassifierRoute.SUPPORTED.value
    }
    if supported_provider_ids != set(_EXPECTED_SUPPORTED_TOPIC_COVERAGE):
        raise _FixturesInvalid
    return tuple(fixtures)


def _parse_fixture(raw: dict[object, object]) -> _Fixture:
    fixture_id = raw["id"]
    group = raw["group"]
    execution = raw["execution"]
    question = raw["question"]
    expected_code = raw["expected_code"]
    if (
        type(fixture_id) is not str
        or not fixture_id
        or type(group) is not str
        or not group
        or type(execution) is not str
        or not execution
        or type(question) is not str
        or not question
        or type(expected_code) is not str
        or not expected_code
    ):
        raise _FixturesInvalid
    expected_intent = raw["expected_intent"]
    expected_slot = raw["expected_pending_slot"]
    if expected_intent is not None and type(expected_intent) is not str:
        raise _FixturesInvalid
    if expected_slot is not None and type(expected_slot) is not str:
        raise _FixturesInvalid

    fixture = _Fixture(
        fixture_id=fixture_id,
        group=group,
        execution=execution,
        question=question,
        expected_code=expected_code,
        expected_intent=expected_intent,
        expected_pending_slot=expected_slot,
    )
    if (
        fixture.group not in _EXPECTED_GROUPS
        or fixture.execution not in {"DETERMINISTIC", "PROVIDER"}
        or fixture.expected_code not in _EXPECTED_CODES
        or len(fixture.question) > 250
    ):
        raise _FixturesInvalid
    negative_coverage = _EXPECTED_NEGATIVE_COVERAGE_DECISIONS.get(
        fixture.fixture_id
    )
    if negative_coverage is not None:
        expected_route, expected_negative_intent, topic_id, coverage_id = (
            negative_coverage
        )
        if (
            fixture.group != ClassifierRoute.SUPPORTED.value
            or fixture.execution != "PROVIDER"
            or fixture.expected_code != expected_route.value
            or fixture.expected_intent != expected_negative_intent.value
            or fixture.expected_pending_slot is not None
            or topic_id is not None
            or coverage_id is not None
        ):
            raise _FixturesInvalid
    elif fixture.group == "POLICY_PRIVACY":
        if fixture.expected_code not in {
            FallbackReason.PERSONAL_LOOKUP.value,
            FallbackReason.LEGAL_JUDGMENT.value,
        }:
            raise _FixturesInvalid
    elif fixture.expected_code != fixture.group:
        raise _FixturesInvalid
    if fixture.expected_intent is not None:
        try:
            Intent(fixture.expected_intent)
        except ValueError:
            raise _FixturesInvalid from None
    if fixture.expected_pending_slot is not None:
        try:
            PendingSlot(fixture.expected_pending_slot)
        except ValueError:
            raise _FixturesInvalid from None
    return fixture


def _validate_synthetic_question(question: str) -> None:
    if _SENSITIVE_FIXTURE_PATTERN.search(question) is not None:
        raise _FixturesInvalid
    redaction = redact_question(question)
    if (
        redaction.masked_text != question
        or redaction.findings
        or redaction.safe_for_failure_storage is not True
        or redaction.safe_for_synthetic_provider is not True
        or redaction.unresolved_reason is not None
    ):
        raise _FixturesInvalid


async def _evaluate(
    fixtures: tuple[_Fixture, ...],
    *,
    classifier: _Classifier,
    usage: TokenUsage,
    cost_cap: Decimal,
) -> _EvaluationResult:
    if (
        len(fixtures) != _EXPECTED_CASES
        or type(usage) is not TokenUsage
        or type(cost_cap) is not Decimal
        or estimate_cost_usd(usage) > cost_cap
    ):
        raise _RuntimeFailed

    correct_count = 0
    invalid_count = 0
    provider_case_count = 0
    deterministic_count = 0
    policy_privacy_outbound_count = 0
    outbound_attempt_count = 0

    for fixture in fixtures:
        redaction = redact_question(fixture.question)
        try:
            safe = SafeQuestion(redaction)
        except (TypeError, ValueError):
            invalid_count += 1
            continue
        deterministic = classify_question(safe)

        if fixture.execution == "DETERMINISTIC":
            deterministic_count += 1
            if deterministic.needs_provider:
                invalid_count += 1
                continue
            if _outcome_matches(fixture, deterministic):
                correct_count += 1
            continue

        provider_case_count += 1
        if not deterministic.needs_provider:
            invalid_count += 1
            continue
        if fixture.group == "POLICY_PRIVACY":
            policy_privacy_outbound_count += 1
        guard = getattr(classifier, "ensure_next_attempt_within_cost", None)
        if callable(guard):
            guard()
        decision = await classifier.classify(safe)
        outbound_attempt_count += 1
        if decision is None:
            invalid_count += 1
        elif _decision_matches(fixture, decision):
            correct_count += 1

    return _EvaluationResult(
        cases_total=len(fixtures),
        deterministic_count=deterministic_count,
        provider_case_count=provider_case_count,
        correct_count=correct_count,
        skip_count=0,
        invalid_count=invalid_count,
        policy_privacy_outbound_count=policy_privacy_outbound_count,
        outbound_attempt_count=outbound_attempt_count,
    )


def _outcome_matches(fixture: _Fixture, outcome: ClassificationOutcome) -> bool:
    actual_code = (
        outcome.route.value
        if outcome.route is not None
        else outcome.fallback_reason.value
        if outcome.fallback_reason is not None
        else ""
    )
    expected_intent = fixture.expected_intent
    if expected_intent is None:
        expected_intent = (
            Intent.UNKNOWN.value
            if fixture.group == "POLICY_PRIVACY"
            else Intent.OUT_OF_SCOPE.value
        )
    return (
        actual_code == fixture.expected_code
        and outcome.intent.value == expected_intent
        and (outcome.pending_slot.value if outcome.pending_slot is not None else None)
        == fixture.expected_pending_slot
    )


def _decision_matches(fixture: _Fixture, decision: ClassifierDecision) -> bool:
    expected_pair = _EXPECTED_SUPPORTED_TOPIC_COVERAGE.get(fixture.fixture_id)
    negative_coverage = _EXPECTED_NEGATIVE_COVERAGE_DECISIONS.get(
        fixture.fixture_id
    )
    return (
        decision.route.value == fixture.expected_code
        and (decision.intent.value if decision.intent is not None else None)
        == fixture.expected_intent
        and (decision.pending_slot.value if decision.pending_slot is not None else None)
        == fixture.expected_pending_slot
        and (
            (
                decision.route is ClassifierRoute.SUPPORTED
                and expected_pair is not None
                and (decision.topic_id, decision.coverage_id) == expected_pair
            )
            or (
                negative_coverage is not None
                and decision.route is negative_coverage[0]
                and decision.intent is negative_coverage[1]
                and decision.topic_id is negative_coverage[2]
                and decision.coverage_id is negative_coverage[3]
            )
            or (
                negative_coverage is None
                and decision.route is not ClassifierRoute.SUPPORTED
                and expected_pair is None
                and decision.topic_id is None
                and decision.coverage_id is None
            )
        )
    )


def _validate_settings(
    settings: UpstageClassifierSettings,
    *,
    provider_case_count: int,
) -> None:
    if (
        type(settings) is not UpstageClassifierSettings
        or settings.provider != UPSTAGE_PROVIDER
        or settings.model != UPSTAGE_MODEL
        or settings.base_url != UPSTAGE_BASE_URL
        or settings.timeout_seconds != UPSTAGE_CLASSIFIER_TIMEOUT_SECONDS
        or settings.max_retries != UPSTAGE_CLASSIFIER_MAX_RETRIES
        or settings.max_concurrency != UPSTAGE_MAX_CONCURRENCY
        or settings.max_input_chars != UPSTAGE_CLASSIFIER_MAX_INPUT_CHARS
        or settings.max_output_tokens != UPSTAGE_CLASSIFIER_MAX_OUTPUT_TOKENS
        or settings.classifier_attempt_cap != UPSTAGE_CLASSIFIER_ATTEMPT_CAP
        or settings.generator_attempt_cap != UPSTAGE_GENERATOR_ATTEMPT_CAP
        or settings.combined_attempt_cap != UPSTAGE_COMBINED_ATTEMPT_CAP
        or settings.session_cost_cap_usd != RUN_COST_CAP_USD
        or provider_case_count != _EXPECTED_PROVIDER_CASES
        or provider_case_count > settings.classifier_attempt_cap
        or provider_case_count > settings.combined_attempt_cap
    ):
        raise _ConfigurationInvalid
    worst_case = TokenUsage(
        input_tokens=settings.max_input_chars * 4 * provider_case_count,
        cached_input_tokens=0,
        output_tokens=settings.max_output_tokens * provider_case_count,
    )
    if estimate_cost_usd(worst_case) > RUN_COST_CAP_USD:
        raise _ConfigurationInvalid


def _build_historical_ledger(
    settings: UpstageClassifierSettings,
) -> ProviderAttemptLedger:
    return ProviderAttemptLedger(
        classifier_cap=settings.classifier_attempt_cap,
        generator_cap=settings.generator_attempt_cap,
        combined_cap=settings.combined_attempt_cap,
        cost_cap_usd=RUN_COST_CAP_USD,
        classifier_worst_case_usd=estimate_cost_usd(
            TokenUsage(
                input_tokens=UPSTAGE_MAX_INPUT_TOKENS,
                cached_input_tokens=0,
                output_tokens=settings.max_output_tokens,
            )
        ),
        generator_worst_case_usd=estimate_cost_usd(
            TokenUsage(
                input_tokens=UPSTAGE_MAX_INPUT_TOKENS,
                cached_input_tokens=0,
                output_tokens=UPSTAGE_MAX_OUTPUT_TOKENS,
            )
        ),
    )


def _build_current_test_catalog() -> TopicCatalog:
    """Build the immutable governed 20-topic catalog used by current tests."""

    try:
        payload: dict[str, Any] = json.loads(
            _OFFICIAL_RECORDS_PATH.read_text(encoding="utf-8")
        )
        records = tuple(_parse_knowledge_record(item) for item in payload["records"])
        catalog = build_topic_catalog(
            (*records, _canonical_waste_03()),
            load_topic_coverage(_COVERAGE_PATH),
        )
    except (KeyError, OSError, TypeError, UnicodeError, ValueError):
        raise _ConfigurationInvalid from None
    governed_pairs = {
        (topic.record.public_id, topic.coverage.coverage_id)
        for topic in catalog.topics
    }
    if (
        len(catalog.topics) != 20
        or not catalog.provider_eligible
        or not set(_EXPECTED_SUPPORTED_TOPIC_COVERAGE.values()) <= governed_pairs
    ):
        raise _ConfigurationInvalid
    return catalog


def _parse_knowledge_record(raw: dict[str, Any]) -> KnowledgeRecord:
    return KnowledgeRecord(
        public_id=raw["id"],
        category=Intent(raw["category"]),
        service_name=raw["service_name"],
        answer_summary=raw["answer_summary"],
        procedure_steps=tuple(raw["procedure_steps"]),
        required_documents=tuple(raw["required_documents"]),
        processing_time=raw["processing_time"],
        fee=raw["fee"],
        department=raw["department"],
        source_title=raw["source_title"],
        source_url=raw["source_url"],
        last_verified_at=date.fromisoformat(raw["last_verified_at"]),
        caution=raw["caution"],
        question_examples=tuple(raw["question_examples"]),
    )


def _canonical_waste_03() -> KnowledgeRecord:
    return KnowledgeRecord(
        public_id="KB-WASTE-03",
        category=Intent.BULKY_WASTE,
        service_name="침대 프레임 배출 수수료",
        answer_summary=(
            "공식 품목표의 침대 프레임 수수료는 1인용침대 8,000원, "
            "2인용침대 10,000원으로 표시됩니다."
        ),
        procedure_steps=(
            "공식 품목표에서 침대 프레임의 1인용침대 또는 2인용침대 항목을 확인합니다.",
            "해당 수수료로 공식 배출 절차를 진행합니다.",
        ),
        required_documents=(),
        processing_time=None,
        fee="1인용침대 8,000원; 2인용침대 10,000원",
        department="세종특별자치시시설관리공단",
        source_title="배출항목선택",
        source_url=(
            "https://www.sjwaste.kr/wasteApp/appCategoryPopup.do?menuId=MENU00305"
        ),
        last_verified_at=date(2026, 7, 18),
        caution=(
            "공식 품목표의 1인용침대·2인용침대 항목을 그대로 따릅니다. "
            "매트리스 포함 가격이나 실제 규격을 단정하지 않습니다."
        ),
        question_examples=("침대 2인용 프레임 수수료가 얼마예요?",),
    )


class _UsageRecorder:
    def __init__(self) -> None:
        self.input_tokens = 0
        self.output_tokens = 0
        self.complete_response_count = 0

    @property
    def usage(self) -> TokenUsage:
        return TokenUsage(self.input_tokens, 0, self.output_tokens)

    async def capture(self, response: httpx.Response) -> None:
        try:
            await response.aread()
            envelope = response.json()
            if type(envelope) is not dict:
                return
            raw = envelope.get("usage")
            if type(raw) is not dict:
                return
            input_tokens = raw.get("prompt_tokens")
            output_tokens = raw.get("completion_tokens")
            if (
                type(input_tokens) is not int
                or input_tokens < 0
                or type(output_tokens) is not int
                or output_tokens < 0
            ):
                return
        except Exception:
            return
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.complete_response_count += 1


class _ActualClassifier:
    def __init__(
        self,
        *,
        classifier: QuestionClassifier,
        ledger: ProviderAttemptLedger,
        recorder: _UsageRecorder,
        settings: UpstageClassifierSettings,
        catalog: TopicCatalog,
    ) -> None:
        if type(catalog) is not TopicCatalog or not catalog.provider_eligible:
            raise _ConfigurationInvalid
        self._classifier = classifier
        self._ledger = ledger
        self._recorder = recorder
        self._settings = settings
        self._catalog = catalog

    @property
    def usage(self) -> TokenUsage:
        return self._recorder.usage

    @property
    def usage_response_count(self) -> int:
        return self._recorder.complete_response_count

    @property
    def outbound_attempt_count(self) -> int:
        return self._ledger.classifier_attempts_used

    def ensure_next_attempt_within_cost(self) -> None:
        current = self.usage
        conservative_next = TokenUsage(
            input_tokens=current.input_tokens + self._settings.max_input_chars * 4,
            cached_input_tokens=0,
            output_tokens=current.output_tokens + self._settings.max_output_tokens,
        )
        if estimate_cost_usd(conservative_next) > RUN_COST_CAP_USD:
            raise _RuntimeFailed

    async def classify(self, question: SafeQuestion) -> ClassifierDecision | None:
        return await self._classifier.classify(question, self._catalog)


def _build_report(
    *,
    source_sha: str,
    model: str,
    cases_total: int,
    deterministic_count: int,
    provider_case_count: int,
    correct_count: int,
    skip_count: int,
    invalid_count: int,
    policy_privacy_outbound_count: int,
    outbound_attempt_count: int,
    usage: TokenUsage,
    estimated_cost: Decimal,
    cost_cap: Decimal,
    elapsed_ms: int,
) -> dict[str, object]:
    acceptance = (
        cases_total == _EXPECTED_CASES
        and deterministic_count == _EXPECTED_DETERMINISTIC_CASES
        and provider_case_count == _EXPECTED_PROVIDER_CASES
        and correct_count == _EXPECTED_CASES
        and skip_count == 0
        and invalid_count == 0
        and policy_privacy_outbound_count == 0
        and outbound_attempt_count == _EXPECTED_PROVIDER_CASES
        and estimated_cost <= cost_cap
    )
    return {
        "source_sha": source_sha,
        "model": model,
        "cases_total": cases_total,
        "deterministic_count": deterministic_count,
        "provider_case_count": provider_case_count,
        "correct_count": correct_count,
        "skip_count": skip_count,
        "invalid_count": invalid_count,
        "policy_privacy_outbound_count": policy_privacy_outbound_count,
        "outbound_attempt_count": outbound_attempt_count,
        "input_tokens": usage.input_tokens,
        "cached_input_tokens": usage.cached_input_tokens,
        "output_tokens": usage.output_tokens,
        "estimated_cost_usd_including_vat": _decimal_text(estimated_cost),
        "cost_cap_usd_including_vat": _decimal_text(cost_cap),
        "elapsed_ms": elapsed_ms,
        "acceptance": "PASS" if acceptance else "FAIL",
    }


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _report_to_markdown(report: dict[str, object]) -> str:
    lines = [
        "# CHAT-NATURAL-001 Upstage Classifier Actual Evidence",
        "",
        "- Payload retention: `0`",
        "- Tracked secret values: `0`",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    lines.extend(f"| `{field}` | `{report[field]}` |" for field in _REPORT_FIELDS)
    lines.extend(
        [
            "",
            "The artifact contains aggregate execution evidence only.",
            "",
        ]
    )
    return "\n".join(lines)


def _source_sha() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        value = completed.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise _RuntimeFailed from None
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise _RuntimeFailed
    return value


def _atomic_write_report(path: Path, report: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(
            _report_to_markdown(report), encoding="utf-8", newline="\n"
        )
        os.replace(temporary, path)
    except OSError:
        raise _RuntimeFailed from None
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


async def _execute_actual(options: _RunnerOptions) -> dict[str, object]:
    fixtures = _load_fixtures(options.fixture_path)
    settings = load_upstage_classifier_settings()
    if settings is None:
        raise _ConfigurationInvalid
    provider_case_count = sum(case.execution == "PROVIDER" for case in fixtures)
    _validate_settings(settings, provider_case_count=provider_case_count)

    catalog = _build_current_test_catalog()
    ledger = _build_historical_ledger(settings)
    recorder = _UsageRecorder()
    timeout = httpx.Timeout(
        settings.timeout_seconds,
        connect=settings.timeout_seconds,
        read=settings.timeout_seconds,
        write=settings.timeout_seconds,
        pool=settings.timeout_seconds,
    )
    started = time.perf_counter()
    async with httpx.AsyncClient(
        base_url=settings.base_url,
        headers={
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        },
        timeout=timeout,
        transport=httpx.AsyncHTTPTransport(retries=0),
        event_hooks={"response": [recorder.capture]},
    ) as client:
        actual = _ActualClassifier(
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
        result = await _evaluate(
            fixtures,
            classifier=actual,
            usage=TokenUsage(0, 0, 0),
            cost_cap=RUN_COST_CAP_USD,
        )
    elapsed_ms = max(0, round((time.perf_counter() - started) * 1000))
    if (
        actual.outbound_attempt_count != _EXPECTED_PROVIDER_CASES
        or actual.usage_response_count != actual.outbound_attempt_count
        or result.outbound_attempt_count != actual.outbound_attempt_count
    ):
        raise _RuntimeFailed
    estimated_cost = estimate_cost_usd(actual.usage)
    if estimated_cost > RUN_COST_CAP_USD:
        raise _RuntimeFailed
    report = _build_report(
        source_sha=_source_sha(),
        model=settings.model,
        cases_total=result.cases_total,
        deterministic_count=result.deterministic_count,
        provider_case_count=result.provider_case_count,
        correct_count=result.correct_count,
        skip_count=result.skip_count,
        invalid_count=result.invalid_count,
        policy_privacy_outbound_count=result.policy_privacy_outbound_count,
        outbound_attempt_count=result.outbound_attempt_count,
        usage=actual.usage,
        estimated_cost=estimated_cost,
        cost_cap=RUN_COST_CAP_USD,
        elapsed_ms=elapsed_ms,
    )
    _atomic_write_report(options.report_path, report)
    if report["acceptance"] != "PASS":
        raise _AcceptanceFailed(report)
    return report


def _configure_event_loop_policy(platform: str) -> None:
    if platform != "win32":
        return
    policy_factory = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if not callable(policy_factory):
        raise _ConfigurationInvalid
    asyncio.set_event_loop_policy(policy_factory())


def main(argv: Sequence[str] | None = None) -> int:
    try:
        options = _parse_args(argv)
        _configure_event_loop_policy(sys.platform)
        report = asyncio.run(_execute_actual(options))
    except _ArgumentsInvalid:
        print("UPSTAGE_CLASSIFIER_ARGUMENTS_INVALID", file=sys.stderr)
        return 2
    except _ConfigurationInvalid:
        print("UPSTAGE_CLASSIFIER_CONFIGURATION_INVALID", file=sys.stderr)
        return 2
    except _AcceptanceFailed as error:
        print(json.dumps(error.report, ensure_ascii=True, separators=(",", ":")))
        return 1
    except Exception:
        print("UPSTAGE_CLASSIFIER_RUNTIME_FAILED", file=sys.stderr)
        return 3
    print(json.dumps(report, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
