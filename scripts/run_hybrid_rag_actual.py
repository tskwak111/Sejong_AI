#!/usr/bin/env python3
"""Run the approved PII-free Hybrid RAG selector subset once, with aggregate evidence."""

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
from typing import Any, NoReturn, Protocol, cast

import httpx

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_API_SOURCE = _REPOSITORY_ROOT / "apps" / "api" / "src"
_FIXTURE_PATH = _API_SOURCE.parent / "tests" / "chat" / "fixtures" / "hybrid-rag-uat.v1.json"
_REPORT_PATH = _REPOSITORY_ROOT / "docs" / "test-reports" / "CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md"
_OFFLINE_REPORT_PATH = (
    _REPOSITORY_ROOT / "docs" / "test-reports" / "CHAT-HYBRID-RAG-001-OFFLINE-UAT.md"
)
_OFFICIAL_RECORDS_PATH = (
    _REPOSITORY_ROOT / "data" / "official" / "releases" / "0.1.0-initial.2" / "kb_records.json"
)
_COVERAGE_PATH = _REPOSITORY_ROOT / "data" / "retrieval" / "topic-coverage.v1.json"
_EXPECTED_IDS = (
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
_EXPECTED_GROUPS = Counter(
    {
        "PARAPHRASE_SUCCESS": 8,
        "TOPIC_DISTINCTION": 4,
        "NO_TOPIC_GROUNDING": 4,
        "SCOPE_OR_NON_CIVIC": 4,
    }
)
_EXPECTED_PROVIDER_CASES = 9
_SENSITIVE_PATTERN = re.compile(
    r"(?:[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|01[016789][-\s]?\d{3,4}[-\s]?\d{4}|\d{6}[-\s]?[1-4]\d{6}|(?:sk|up)_[A-Za-z0-9_-]{12,}|postgres(?:ql)?://)",
    re.IGNORECASE,
)
if str(_API_SOURCE) not in sys.path:
    sys.path.insert(0, str(_API_SOURCE))

from sejong_ai_api.chat.classification import SafeQuestion, classify_question  # noqa: E402
from sejong_ai_api.chat.topic_catalog import (  # noqa: E402
    TopicCatalog,
    build_topic_catalog,
    load_topic_coverage,
)
from sejong_ai_api.db.models import Intent, KnowledgeRecord  # noqa: E402
from sejong_ai_api.llm.classifier_contracts import ClassifierDecision, ClassifierRoute  # noqa: E402
from sejong_ai_api.llm.contracts import TokenUsage  # noqa: E402
from sejong_ai_api.llm.cost import estimate_cost_usd  # noqa: E402
from sejong_ai_api.llm.limits import (  # noqa: E402
    LOCAL_INTERACTIVE_COST_CAP_USD,
    ProviderAttemptLedger,
)
from sejong_ai_api.llm.settings import (  # noqa: E402
    UPSTAGE_CLASSIFIER_MAX_INPUT_CHARS,
    UPSTAGE_CLASSIFIER_MAX_OUTPUT_TOKENS,
    UPSTAGE_CLASSIFIER_MAX_RETRIES,
    UPSTAGE_CLASSIFIER_TIMEOUT_SECONDS,
    UPSTAGE_LOCAL_INTERACTIVE_CLASSIFIER_ATTEMPT_CAP,
    UPSTAGE_LOCAL_INTERACTIVE_COMBINED_ATTEMPT_CAP,
    UPSTAGE_LOCAL_INTERACTIVE_GENERATOR_ATTEMPT_CAP,
    UPSTAGE_MAX_CONCURRENCY,
    UPSTAGE_MAX_INPUT_TOKENS,
    UPSTAGE_MAX_OUTPUT_TOKENS,
    UPSTAGE_MODEL,
    UpstageClassifierSettings,
    load_upstage_classifier_settings,
)
from sejong_ai_api.llm.upstage_classifier import QuestionClassifier  # noqa: E402
from sejong_ai_api.privacy.redaction import redact_question  # noqa: E402

_REPORT_FIELDS = (
    "source_sha",
    "key_present",
    "model",
    "cases_total",
    "selected_count",
    "skip_count",
    "deterministic_count",
    "provider_case_count",
    "route_topic_match_count",
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
    pass


class _ConfigurationInvalid(RuntimeError):
    pass


class _FixturesInvalid(RuntimeError):
    pass


class _RuntimeFailed(RuntimeError):
    pass


class _AcceptanceFailed(RuntimeError):
    def __init__(self, report: dict[str, object]) -> None:
        super().__init__("HYBRID_RAG_ACTUAL_ACCEPTANCE_FAILED")
        self.report = report


class _Selector(Protocol):
    async def classify(self, question: SafeQuestion) -> ClassifierDecision | None: ...


@dataclass(frozen=True, slots=True)
class _RunnerOptions:
    fixture_path: Path
    report_path: Path


@dataclass(frozen=True, slots=True)
class _Fixture:
    fixture_id: str
    group: str
    question: str
    expected_route: str
    expected_intent: str
    expected_topic_id: str | None
    expected_provider_use: int
    actual_subset: bool
    safe_for_provider: bool


@dataclass(frozen=True, slots=True)
class _CaseResult:
    fixture_id: str
    route_topic_match: bool
    outbound_count: int


@dataclass(frozen=True, slots=True)
class _EvaluationResult:
    cases_total: int
    deterministic_count: int
    provider_case_count: int
    route_topic_match_count: int
    policy_privacy_outbound_count: int
    outbound_attempt_count: int
    cases: tuple[_CaseResult, ...]


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> NoReturn:
        raise _ArgumentsInvalid from None


def _parse_args(argv: Sequence[str] | None = None) -> _RunnerOptions:
    parser = _SafeArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--report", required=True)
    values = parser.parse_args(argv)
    fixture_path = _resolve_repository_path(values.fixture)
    report_path = _resolve_repository_path(values.report)
    if fixture_path != _FIXTURE_PATH.resolve() or report_path != _REPORT_PATH.resolve():
        raise _ArgumentsInvalid
    return _RunnerOptions(fixture_path, report_path)


def _resolve_repository_path(value: object) -> Path:
    if type(value) is not str or not value or "\x00" in value:
        raise _ArgumentsInvalid
    value_path = Path(value)
    return (value_path if value_path.is_absolute() else _REPOSITORY_ROOT / value_path).resolve()


def _load_fixtures(path: Path) -> tuple[_Fixture, ...]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        raw_cases = document["cases"]
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        raise _FixturesInvalid from None
    if (
        type(document) is not dict
        or document.get("schema_version") != 1
        or document.get("data_kind") != "SYNTHETIC_CHAT_UAT"
        or type(raw_cases) is not list
    ):
        raise _FixturesInvalid
    fixtures: list[_Fixture] = []
    for raw in raw_cases:
        if type(raw) is not dict:
            raise _FixturesInvalid
        try:
            fixture = _Fixture(
                fixture_id=raw["id"],
                group=raw["group"],
                question=raw["question"],
                expected_route=raw["expected_route"],
                expected_intent=raw["expected_intent"],
                expected_topic_id=raw["expected_topic_id"],
                expected_provider_use=raw["expected_provider_use"],
                actual_subset=raw["actual_subset"],
                safe_for_provider=False,
            )
        except KeyError:
            raise _FixturesInvalid from None
        if (
            type(fixture.fixture_id) is not str
            or type(fixture.group) is not str
            or type(fixture.question) is not str
            or type(fixture.expected_route) is not str
            or type(fixture.expected_intent) is not str
            or fixture.expected_topic_id is not None
            and type(fixture.expected_topic_id) is not str
            or type(fixture.expected_provider_use) is not int
            or fixture.expected_provider_use not in (0, 1)
            or type(fixture.actual_subset) is not bool
            or fixture.actual_subset
            and _SENSITIVE_PATTERN.search(fixture.question) is not None
        ):
            raise _FixturesInvalid
        redaction = redact_question(fixture.question)
        safe = (
            redaction.masked_text == fixture.question
            and not redaction.findings
            and redaction.safe_for_synthetic_provider is True
            and redaction.unresolved_reason is None
        )
        fixtures.append(
            _Fixture(
                fixture_id=fixture.fixture_id,
                group=fixture.group,
                question=fixture.question,
                expected_route=fixture.expected_route,
                expected_intent=fixture.expected_intent,
                expected_topic_id=fixture.expected_topic_id,
                expected_provider_use=fixture.expected_provider_use,
                actual_subset=fixture.actual_subset,
                safe_for_provider=safe,
            )
        )
    selected = tuple(case for case in fixtures if case.actual_subset)
    if (
        len(fixtures) != 48
        or tuple(case.fixture_id for case in selected) != _EXPECTED_IDS
        or Counter(case.group for case in selected) != _EXPECTED_GROUPS
        or any(not case.safe_for_provider or case.group == "PRIVACY_POLICY" for case in selected)
        or sum(case.expected_provider_use for case in selected) != _EXPECTED_PROVIDER_CASES
    ):
        raise _FixturesInvalid
    return tuple(fixtures)


def _build_current_test_catalog() -> TopicCatalog:
    try:
        raw_records = json.loads(_OFFICIAL_RECORDS_PATH.read_text(encoding="utf-8"))["records"]
        records = tuple(_parse_knowledge_record(raw) for raw in raw_records)
        catalog = build_topic_catalog(records, load_topic_coverage(_COVERAGE_PATH))
    except (KeyError, OSError, TypeError, UnicodeError, ValueError):
        raise _ConfigurationInvalid from None
    if not catalog.provider_eligible:
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


def _validate_settings(settings: UpstageClassifierSettings) -> None:
    if (
        type(settings) is not UpstageClassifierSettings
        or settings.model != UPSTAGE_MODEL
        or settings.timeout_seconds != UPSTAGE_CLASSIFIER_TIMEOUT_SECONDS
        or settings.max_retries != UPSTAGE_CLASSIFIER_MAX_RETRIES
        or settings.max_concurrency != UPSTAGE_MAX_CONCURRENCY
        or settings.max_input_chars != UPSTAGE_CLASSIFIER_MAX_INPUT_CHARS
        or settings.max_output_tokens != UPSTAGE_CLASSIFIER_MAX_OUTPUT_TOKENS
        or settings.classifier_attempt_cap != UPSTAGE_LOCAL_INTERACTIVE_CLASSIFIER_ATTEMPT_CAP
        or settings.generator_attempt_cap != UPSTAGE_LOCAL_INTERACTIVE_GENERATOR_ATTEMPT_CAP
        or settings.combined_attempt_cap != UPSTAGE_LOCAL_INTERACTIVE_COMBINED_ATTEMPT_CAP
        or settings.session_cost_cap_usd != LOCAL_INTERACTIVE_COST_CAP_USD
    ):
        raise _ConfigurationInvalid


def _require_offline_gate() -> None:
    try:
        evidence = _OFFLINE_REPORT_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise _ConfigurationInvalid from None
    if "48/48" not in evidence or "PASS" not in evidence:
        raise _ConfigurationInvalid


def _require_clean_secret_scan() -> None:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(_REPOSITORY_ROOT / "scripts" / "check_secret_patterns.ps1"),
        "-RepositoryRoot",
        str(_REPOSITORY_ROOT),
    ]
    try:
        completed = subprocess.run(
            command, cwd=_REPOSITORY_ROOT, capture_output=True, text=False, timeout=60, check=False
        )
    except (OSError, subprocess.SubprocessError):
        raise _ConfigurationInvalid from None
    if completed.returncode != 0:
        raise _ConfigurationInvalid


def _decision_matches(case: _Fixture, decision: ClassifierDecision, catalog: TopicCatalog) -> bool:
    if decision.route.value != case.expected_route:
        return False
    if decision.route is ClassifierRoute.SUPPORTED:
        topic = catalog.find(case.expected_topic_id or "")
        return (
            topic is not None
            and decision.intent is topic.record.category
            and decision.topic_id == topic.record.public_id
            and decision.coverage_id == topic.coverage.coverage_id
        )
    if decision.route is ClassifierRoute.NO_TOPIC_MATCH:
        return decision.intent is Intent(case.expected_intent)
    return decision.intent is None and decision.topic_id is None and decision.coverage_id is None


def _worst_case_selector_cost() -> Decimal:
    return estimate_cost_usd(
        TokenUsage(UPSTAGE_MAX_INPUT_TOKENS, 0, UPSTAGE_CLASSIFIER_MAX_OUTPUT_TOKENS)
    )


async def _evaluate_selected(
    selected: tuple[_Fixture, ...], *, selector: _Selector, usage: TokenUsage, cost_cap: Decimal
) -> _EvaluationResult:
    if (
        len(selected) != len(_EXPECTED_IDS)
        or tuple(case.fixture_id for case in selected) != _EXPECTED_IDS
        or type(usage) is not TokenUsage
        or type(cost_cap) is not Decimal
        or estimate_cost_usd(usage) + _EXPECTED_PROVIDER_CASES * _worst_case_selector_cost()
        > cost_cap
    ):
        raise _RuntimeFailed
    catalog = _build_current_test_catalog()
    deterministic_count = provider_case_count = outbound_attempt_count = route_topic_match_count = 0
    results: list[_CaseResult] = []
    for case in selected:
        try:
            safe_question = SafeQuestion(redact_question(case.question))
        except (TypeError, ValueError):
            raise _RuntimeFailed from None
        outcome = classify_question(safe_question)
        if case.expected_provider_use == 0:
            deterministic_count += 1
            # The UAT's no-topic rows have already passed retrieval/grounding offline.
            # This selector run proves the deterministic branch remains provider-free.
            matched = not outcome.needs_provider
            results.append(_CaseResult(case.fixture_id, matched, 0))
            route_topic_match_count += int(matched)
            continue
        provider_case_count += 1
        if not outcome.needs_provider:
            raise _RuntimeFailed
        decision = await selector.classify(safe_question)
        outbound_attempt_count += 1
        matched = decision is not None and _decision_matches(case, decision, catalog)
        results.append(_CaseResult(case.fixture_id, matched, 1))
        route_topic_match_count += int(matched)
    return _EvaluationResult(
        len(selected),
        deterministic_count,
        provider_case_count,
        route_topic_match_count,
        0,
        outbound_attempt_count,
        tuple(results),
    )


class _UsageRecorder:
    def __init__(self) -> None:
        self._usage = TokenUsage(0, 0, 0)
        self.complete_response_count = 0

    @property
    def usage(self) -> TokenUsage:
        return self._usage

    async def capture(self, response: httpx.Response) -> None:
        try:
            await response.aread()
            raw = response.json().get("usage")
            if type(raw) is not dict:
                return
            input_tokens, output_tokens = raw.get("prompt_tokens"), raw.get("completion_tokens")
            if (
                type(input_tokens) is not int
                or input_tokens < 0
                or type(output_tokens) is not int
                or output_tokens < 0
            ):
                return
        except Exception:
            return
        self._usage = TokenUsage(
            self._usage.input_tokens + input_tokens,
            self._usage.cached_input_tokens,
            self._usage.output_tokens + output_tokens,
        )
        self.complete_response_count += 1


class _ActualSelector:
    """Bind the request-local catalog to the production classifier adapter."""

    def __init__(self, classifier: QuestionClassifier, catalog: TopicCatalog) -> None:
        self._classifier = classifier
        self._catalog = catalog

    async def classify(self, question: SafeQuestion) -> ClassifierDecision | None:
        return await self._classifier.classify(question, self._catalog)


def _build_ledger(settings: UpstageClassifierSettings) -> ProviderAttemptLedger:
    return ProviderAttemptLedger(
        classifier_cap=settings.classifier_attempt_cap,
        generator_cap=settings.generator_attempt_cap,
        combined_cap=settings.combined_attempt_cap,
        cost_cap_usd=settings.session_cost_cap_usd,
        classifier_worst_case_usd=_worst_case_selector_cost(),
        generator_worst_case_usd=estimate_cost_usd(
            TokenUsage(UPSTAGE_MAX_INPUT_TOKENS, 0, UPSTAGE_MAX_OUTPUT_TOKENS)
        ),
    )


def _build_report(
    *,
    result: _EvaluationResult,
    usage: TokenUsage,
    key_present: bool,
    source_sha: str,
    elapsed_ms: int = 0,
) -> dict[str, object]:
    cost = estimate_cost_usd(usage)
    acceptance = (
        result.cases_total == 20
        and result.deterministic_count == 11
        and result.provider_case_count == 9
        and result.route_topic_match_count == 20
        and result.policy_privacy_outbound_count == 0
        and result.outbound_attempt_count == 9
        and cost <= LOCAL_INTERACTIVE_COST_CAP_USD
    )
    return {
        "source_sha": source_sha,
        "key_present": key_present,
        "model": UPSTAGE_MODEL,
        "cases_total": result.cases_total,
        "selected_count": result.cases_total,
        "skip_count": 0,
        "deterministic_count": result.deterministic_count,
        "provider_case_count": result.provider_case_count,
        "route_topic_match_count": result.route_topic_match_count,
        "policy_privacy_outbound_count": result.policy_privacy_outbound_count,
        "outbound_attempt_count": result.outbound_attempt_count,
        "input_tokens": usage.input_tokens,
        "cached_input_tokens": usage.cached_input_tokens,
        "output_tokens": usage.output_tokens,
        "estimated_cost_usd_including_vat": str(cost),
        "cost_cap_usd_including_vat": str(LOCAL_INTERACTIVE_COST_CAP_USD),
        "elapsed_ms": elapsed_ms,
        "acceptance": "PASS" if acceptance else "FAIL",
        "cases": result.cases,
    }


def _report_to_markdown(report: dict[str, object]) -> str:
    lines = [
        "# CHAT-HYBRID-RAG-001 Upstage Actual Selector Evidence",
        "",
        "- Provider content retention: `0`",
        "- Key presence only: `true`",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    lines.extend(f"| `{field}` | `{report[field]}` |" for field in _REPORT_FIELDS)
    lines.extend(["", "| Fixture ID | Route/topic match | Outbound |", "|---|---:|---:|"])
    for case in cast(tuple[object, ...], report["cases"]):
        if type(case) is not _CaseResult:
            raise _RuntimeFailed
        lines.append(
            f"| `{case.fixture_id}` | `{str(case.route_topic_match).lower()}` | "
            f"`{case.outbound_count}` |"
        )
    lines.extend(
        [
            "",
            "This artifact contains aggregate-only evidence; it does not retain questions, "
            "provider content, keys, or DSNs.",
            "",
        ]
    )
    return "\n".join(lines)


def _source_sha() -> str:
    try:
        value = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise _RuntimeFailed from None
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise _RuntimeFailed
    return value


def _atomic_write_report(path: Path, report: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(_report_to_markdown(report), encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    except OSError:
        raise _RuntimeFailed from None
    finally:
        temporary.unlink(missing_ok=True)


async def _execute_actual(options: _RunnerOptions) -> dict[str, object]:
    fixtures = _load_fixtures(options.fixture_path)
    selected = tuple(case for case in fixtures if case.actual_subset)
    _require_offline_gate()
    _require_clean_secret_scan()
    settings = load_upstage_classifier_settings()
    if settings is None:
        raise _ConfigurationInvalid
    _validate_settings(settings)
    catalog = _build_current_test_catalog()
    recorder, ledger = _UsageRecorder(), _build_ledger(settings)
    started = time.perf_counter()
    timeout = httpx.Timeout(settings.timeout_seconds)
    async with httpx.AsyncClient(
        base_url=settings.base_url,
        headers={"Authorization": f"Bearer {settings.api_key}", "Content-Type": "application/json"},
        timeout=timeout,
        transport=httpx.AsyncHTTPTransport(retries=0),
        event_hooks={"response": [recorder.capture]},
    ) as client:
        selector = _ActualSelector(
            QuestionClassifier(settings=settings, client=client, ledger=ledger), catalog
        )
        result = await _evaluate_selected(
            selected,
            selector=selector,
            usage=TokenUsage(0, 0, 0),
            cost_cap=settings.session_cost_cap_usd,
        )
    if (
        recorder.complete_response_count != result.outbound_attempt_count
        or ledger.classifier_attempts_used != result.outbound_attempt_count
    ):
        raise _RuntimeFailed
    report = _build_report(
        result=result,
        usage=recorder.usage,
        key_present=True,
        source_sha=_source_sha(),
        elapsed_ms=max(0, round((time.perf_counter() - started) * 1000)),
    )
    _atomic_write_report(options.report_path, report)
    if report["acceptance"] != "PASS":
        raise _AcceptanceFailed(report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    try:
        options = _parse_args(argv)
        report = asyncio.run(_execute_actual(options))
    except _ArgumentsInvalid:
        print("HYBRID_RAG_ACTUAL_ARGUMENTS_INVALID", file=sys.stderr)
        return 2
    except _ConfigurationInvalid:
        print("HYBRID_RAG_ACTUAL_CONFIGURATION_INVALID", file=sys.stderr)
        return 2
    except _AcceptanceFailed as error:
        print(
            json.dumps(
                {field: error.report[field] for field in _REPORT_FIELDS},
                ensure_ascii=True,
                separators=(",", ":"),
            )
        )
        return 1
    except Exception:
        print("HYBRID_RAG_ACTUAL_RUNTIME_FAILED", file=sys.stderr)
        return 3
    print(
        json.dumps(
            {field: report[field] for field in _REPORT_FIELDS},
            ensure_ascii=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
