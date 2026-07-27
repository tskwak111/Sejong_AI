#!/usr/bin/env python3
"""Run one identity-pinned, PII-free Hybrid RAG selector acceptance."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, NoReturn, Protocol, cast

import httpx

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_API_SOURCE = _REPOSITORY_ROOT / "apps" / "api" / "src"
_FIXTURE_PATH = (
    _API_SOURCE.parent / "tests" / "chat" / "fixtures" / "hybrid-rag-uat.v1.json"
)
_REPORT_PATH = (
    _REPOSITORY_ROOT / "docs" / "test-reports" / "CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md"
)
_OFFLINE_REPORT_PATH = (
    _REPOSITORY_ROOT / "docs" / "test-reports" / "CHAT-HYBRID-RAG-001-OFFLINE-UAT.md"
)
_OFFICIAL_RELEASE_ROOT = (
    _REPOSITORY_ROOT / "data" / "official" / "releases" / "0.1.0-initial.2"
)
_OFFICIAL_RECORDS_PATH = _OFFICIAL_RELEASE_ROOT / "kb_records.json"
_RELEASE_MANIFEST_PATH = _OFFICIAL_RELEASE_ROOT / "release_manifest.json"
_COVERAGE_PATH = _REPOSITORY_ROOT / "data" / "retrieval" / "topic-coverage.v1.json"

_EXPECTED_FIXTURE_SHA256 = (
    "4c6bf8cad6a00c94775f36b3731e7878a10722a2031e97e2a49fb8cb2141351d"
)
_EXPECTED_COVERAGE_SHA256 = (
    "94b856bf87723893cbce9b29bf4c7125828a1624b79f6419c58d45b6bb5eb663"
)
_EXPECTED_OFFICIAL_RECORDS_SHA256 = (
    "1c4c303d8f0057d285023ba18a3d2829fcf856c1140baa270456aaf061c0fdaf"
)
_EXPECTED_RELEASE_MANIFEST_SHA256 = (
    "0ccf3326616fdf0d9d96622f560e30da75d457c8295fc8bf37d2a601829a11a9"
)
_EXPECTED_OFFLINE_SHA256 = (
    "e699315d87cce99ad9a1e46e80cc18b6194db5b2cf251f57ad02e5acdc4042fe"
)
_EXPECTED_RELEASE_VERSION = "0.1.0-initial.2"
_EXPECTED_RELEASE_ID = "sejong-official-0.1.0-initial.2"
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
_EXPECTED_DETERMINISTIC_CASES = 11
_SENSITIVE_PATTERN = re.compile(
    r"(?:[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    r"|01[016789][-\s]?\d{3,4}[-\s]?\d{4}"
    r"|\d{6}[-\s]?[1-4]\d{6}"
    r"|(?:sk|up)_[A-Za-z0-9_-]{12,}"
    r"|postgres(?:ql)?://)",
    re.IGNORECASE,
)
_PROTECTED_INPUTS = (
    _FIXTURE_PATH,
    _COVERAGE_PATH,
    _OFFICIAL_RECORDS_PATH,
    _RELEASE_MANIFEST_PATH,
    _OFFLINE_REPORT_PATH,
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
from sejong_ai_api.llm.classifier_contracts import (  # noqa: E402
    ClassifierDecision,
    ClassifierRoute,
)
from sejong_ai_api.llm.contracts import TokenUsage  # noqa: E402
from sejong_ai_api.llm.cost import estimate_cost_usd  # noqa: E402
from sejong_ai_api.llm.limits import (  # noqa: E402
    LOCAL_INTERACTIVE_COST_CAP_USD,
    ProviderAttemptLedger,
    parse_provider_token_usage,
)
from sejong_ai_api.llm.settings import (  # noqa: E402
    UPSTAGE_BASE_URL,
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
    UPSTAGE_PROVIDER,
    UpstageClassifierSettings,
    load_upstage_classifier_settings,
)
from sejong_ai_api.llm.upstage_classifier import (  # noqa: E402
    QuestionClassifier,
    create_upstage_classifier_client,
)
from sejong_ai_api.privacy.redaction import redact_question  # noqa: E402

_REPORT_FIELDS = (
    "source_sha",
    "fixture_sha256",
    "coverage_sha256",
    "official_records_sha256",
    "release_manifest_sha256",
    "offline_evidence_sha256",
    "release_version",
    "protected_inputs_clean",
    "key_present",
    "model",
    "cases_total",
    "selected_count",
    "skip_count",
    "prior_offline_deterministic_provider_free_count",
    "provider_case_count",
    "provider_route_topic_match_count",
    "policy_privacy_outbound_count",
    "outbound_attempt_count",
    "observed_usage_response_count",
    "conservative_charged_attempt_count",
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "observed_usage_cost_usd_including_vat",
    "ledger_charged_cost_usd_including_vat",
    "cost_reconciled",
    "cost_cap_usd_including_vat",
    "elapsed_ms",
    "acceptance",
)


class _ArgumentsInvalid(ValueError):
    """Only the canonical input and report paths are accepted."""


class _ConfigurationInvalid(RuntimeError):
    """A pre-network gate failed without carrying values to output."""


class _FixturesInvalid(RuntimeError):
    """The frozen corpus is not exactly the reviewed corpus."""


class _RuntimeFailed(RuntimeError):
    """A controlled execution invariant failed."""


class _AcceptanceFailed(RuntimeError):
    """The completed one-shot run did not satisfy acceptance."""


class _RunAlreadyExists(RuntimeError):
    """A concurrent run or unacknowledged evidence blocks execution."""


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
class _InputIdentities:
    fixture_sha256: str
    coverage_sha256: str
    official_records_sha256: str
    release_manifest_sha256: str
    offline_evidence_sha256: str
    release_version: str


@dataclass(frozen=True, slots=True)
class _CaseResult:
    fixture_id: str
    evidence_kind: str
    provider_route_topic_match: bool | None
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


@dataclass(slots=True)
class _RunEvidence:
    source_sha: str = "NOT_VERIFIED"
    identities: _InputIdentities | None = None
    protected_inputs_clean: bool = False
    key_present: bool = False
    selected_count: int = 0
    prior_offline_deterministic_provider_free_count: int = 0
    provider_case_count: int = 0
    provider_route_topic_match_count: int = 0
    policy_privacy_outbound_count: int = 0
    cases: list[_CaseResult] = field(default_factory=list)
    recorder: _UsageRecorder | None = None
    ledger: ProviderAttemptLedger | None = None
    elapsed_ms: int = 0


@dataclass(slots=True)
class _RunLease:
    lock_path: Path
    descriptor: int | None

    @classmethod
    def acquire(cls, report_path: Path) -> _RunLease:
        if report_path.exists():
            raise _RunAlreadyExists
        lock_path = report_path.with_name(f"{report_path.name}.run.lock")
        try:
            descriptor = os.open(
                lock_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            os.write(descriptor, b"CHAT-HYBRID-RAG-001 one-run lease\n")
            os.fsync(descriptor)
        except FileExistsError:
            raise _RunAlreadyExists from None
        except OSError:
            raise _ConfigurationInvalid from None
        return cls(lock_path=lock_path, descriptor=descriptor)

    def release(self, *, report_written: bool) -> None:
        if self.descriptor is not None:
            try:
                os.close(self.descriptor)
            except OSError:
                pass
            self.descriptor = None
        if report_written:
            try:
                self.lock_path.unlink()
            except OSError:
                pass


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
    return (
        value_path if value_path.is_absolute() else _REPOSITORY_ROOT / value_path
    ).resolve()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    except OSError:
        raise _ConfigurationInvalid from None
    return digest.hexdigest()


def _require_exact_sha(path: Path, expected: str) -> str:
    actual = _sha256_file(path)
    if actual != expected:
        raise _ConfigurationInvalid
    return actual


def _require_offline_gate() -> str:
    """Bind acceptance to the reviewed report bytes, not prose parsing."""

    return _require_exact_sha(_OFFLINE_REPORT_PATH, _EXPECTED_OFFLINE_SHA256)


def _require_protected_inputs_clean() -> None:
    relative_paths = tuple(
        str(path.relative_to(_REPOSITORY_ROOT)) for path in _PROTECTED_INPUTS
    )
    try:
        completed = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", *relative_paths],
            cwd=_REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        raise _ConfigurationInvalid from None
    if completed.returncode != 0:
        raise _ConfigurationInvalid


def _load_fixtures(path: Path) -> tuple[_Fixture, ...]:
    if path.resolve() != _FIXTURE_PATH.resolve():
        raise _FixturesInvalid
    _require_exact_sha(path, _EXPECTED_FIXTURE_SHA256)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        raw_cases = document["cases"]
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        raise _FixturesInvalid from None
    if (
        type(document) is not dict
        or frozenset(document) != {"schema_version", "data_kind", "cases"}
        or document["schema_version"] != 1
        or document["data_kind"] != "SYNTHETIC_CHAT_UAT"
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
            or (
                fixture.expected_topic_id is not None
                and type(fixture.expected_topic_id) is not str
            )
            or type(fixture.expected_provider_use) is not int
            or fixture.expected_provider_use not in (0, 1)
            or type(fixture.actual_subset) is not bool
            or (
                fixture.actual_subset
                and _SENSITIVE_PATTERN.search(fixture.question) is not None
            )
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
        or any(
            not case.safe_for_provider or case.group == "PRIVACY_POLICY"
            for case in selected
        )
        or sum(case.expected_provider_use for case in selected)
        != _EXPECTED_PROVIDER_CASES
    ):
        raise _FixturesInvalid
    return tuple(fixtures)


def _load_pinned_inputs() -> tuple[_InputIdentities, TopicCatalog]:
    fixture_sha = _require_exact_sha(_FIXTURE_PATH, _EXPECTED_FIXTURE_SHA256)
    coverage_sha = _require_exact_sha(_COVERAGE_PATH, _EXPECTED_COVERAGE_SHA256)
    official_sha = _require_exact_sha(
        _OFFICIAL_RECORDS_PATH,
        _EXPECTED_OFFICIAL_RECORDS_SHA256,
    )
    manifest_sha = _require_exact_sha(
        _RELEASE_MANIFEST_PATH,
        _EXPECTED_RELEASE_MANIFEST_SHA256,
    )
    offline_sha = _require_offline_gate()
    try:
        manifest = json.loads(_RELEASE_MANIFEST_PATH.read_text(encoding="utf-8"))
        release = json.loads(_OFFICIAL_RECORDS_PATH.read_text(encoding="utf-8"))
        raw_records = release["records"]
        artifacts = manifest["artifacts"]
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        raise _ConfigurationInvalid from None
    if (
        type(manifest) is not dict
        or manifest.get("schema_version") != 2
        or manifest.get("release_id") != _EXPECTED_RELEASE_ID
        or manifest.get("release_version") != _EXPECTED_RELEASE_VERSION
        or manifest.get("projection")
        != {
            "kb": 19,
            "mapping": 10,
            "mock": 0,
            "office": 3,
            "rejected_mapping": 2,
            "withheld_kb": 1,
        }
        or type(artifacts) is not list
        or not any(
            type(artifact) is dict
            and artifact.get("path") == "kb_records.json"
            and artifact.get("record_count") == 19
            and artifact.get("sha256") == _EXPECTED_OFFICIAL_RECORDS_SHA256
            for artifact in artifacts
        )
        or type(release) is not dict
        or frozenset(release) != {"schema_version", "release_version", "records"}
        or release["schema_version"] != 2
        or release["release_version"] != _EXPECTED_RELEASE_VERSION
        or type(raw_records) is not list
        or len(raw_records) != 19
        or any(
            type(raw) is not dict
            or raw.get("status") != "ACTIVE"
            or raw.get("data_origin") != "OFFICIAL"
            for raw in raw_records
        )
    ):
        raise _ConfigurationInvalid
    try:
        records = tuple(_parse_knowledge_record(raw) for raw in raw_records)
        catalog = build_topic_catalog(records, load_topic_coverage(_COVERAGE_PATH))
    except (KeyError, TypeError, ValueError):
        raise _ConfigurationInvalid from None
    if (
        len(catalog.topics) != 19
        or not catalog.provider_eligible
        or len({topic.record.public_id for topic in catalog.topics}) != 19
    ):
        raise _ConfigurationInvalid
    return (
        _InputIdentities(
            fixture_sha256=fixture_sha,
            coverage_sha256=coverage_sha,
            official_records_sha256=official_sha,
            release_manifest_sha256=manifest_sha,
            offline_evidence_sha256=offline_sha,
            release_version=_EXPECTED_RELEASE_VERSION,
        ),
        catalog,
    )


def _build_current_test_catalog() -> TopicCatalog:
    return _load_pinned_inputs()[1]


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
        or settings.provider != UPSTAGE_PROVIDER
        or settings.model != UPSTAGE_MODEL
        or settings.base_url != UPSTAGE_BASE_URL
        or settings.timeout_seconds != UPSTAGE_CLASSIFIER_TIMEOUT_SECONDS
        or settings.max_retries != UPSTAGE_CLASSIFIER_MAX_RETRIES
        or settings.max_concurrency != UPSTAGE_MAX_CONCURRENCY
        or settings.max_input_chars != UPSTAGE_CLASSIFIER_MAX_INPUT_CHARS
        or settings.max_output_tokens != UPSTAGE_CLASSIFIER_MAX_OUTPUT_TOKENS
        or settings.classifier_attempt_cap
        != UPSTAGE_LOCAL_INTERACTIVE_CLASSIFIER_ATTEMPT_CAP
        or settings.generator_attempt_cap
        != UPSTAGE_LOCAL_INTERACTIVE_GENERATOR_ATTEMPT_CAP
        or settings.combined_attempt_cap
        != UPSTAGE_LOCAL_INTERACTIVE_COMBINED_ATTEMPT_CAP
        or settings.session_cost_cap_usd != LOCAL_INTERACTIVE_COST_CAP_USD
    ):
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
            command,
            cwd=_REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        raise _ConfigurationInvalid from None
    if completed.returncode != 0:
        raise _ConfigurationInvalid


def _source_sha() -> str:
    try:
        value = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise _ConfigurationInvalid from None
    if re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise _ConfigurationInvalid
    return value


def _decision_matches(
    case: _Fixture,
    decision: ClassifierDecision,
    catalog: TopicCatalog,
) -> bool:
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
    return (
        decision.intent is None
        and decision.topic_id is None
        and decision.coverage_id is None
    )


def _worst_case_selector_cost() -> Decimal:
    return estimate_cost_usd(
        TokenUsage(
            UPSTAGE_MAX_INPUT_TOKENS,
            0,
            UPSTAGE_CLASSIFIER_MAX_OUTPUT_TOKENS,
        )
    )


async def _evaluate_selected(
    selected: tuple[_Fixture, ...],
    *,
    selector: _Selector,
    usage: TokenUsage,
    cost_cap: Decimal,
    catalog: TopicCatalog | None = None,
    evidence: _RunEvidence | None = None,
) -> _EvaluationResult:
    if (
        len(selected) != len(_EXPECTED_IDS)
        or tuple(case.fixture_id for case in selected) != _EXPECTED_IDS
        or type(usage) is not TokenUsage
        or type(cost_cap) is not Decimal
        or estimate_cost_usd(usage)
        + _EXPECTED_PROVIDER_CASES * _worst_case_selector_cost()
        > cost_cap
    ):
        raise _RuntimeFailed
    selected_catalog = _build_current_test_catalog() if catalog is None else catalog
    state = _RunEvidence() if evidence is None else evidence
    state.selected_count = len(selected)
    cases: list[_CaseResult] = []
    deterministic_count = 0
    provider_case_count = 0
    provider_matches = 0

    for case in selected:
        try:
            safe_question = SafeQuestion(redact_question(case.question))
        except (TypeError, ValueError):
            raise _RuntimeFailed from None
        outcome = classify_question(safe_question)
        if case.expected_provider_use == 0:
            if outcome.needs_provider:
                raise _RuntimeFailed
            deterministic_count += 1
            result = _CaseResult(
                fixture_id=case.fixture_id,
                evidence_kind="PRIOR_OFFLINE_PROVIDER_FREE",
                provider_route_topic_match=None,
                outbound_count=0,
            )
            cases.append(result)
            state.cases.append(result)
            state.prior_offline_deterministic_provider_free_count += 1
            continue

        if not outcome.needs_provider:
            raise _RuntimeFailed
        provider_case_count += 1
        state.provider_case_count += 1
        attempts_before = (
            0 if state.ledger is None else state.ledger.classifier_attempts_used
        )
        decision = await selector.classify(safe_question)
        outbound_count = (
            1
            if state.ledger is None
            else state.ledger.classifier_attempts_used - attempts_before
        )
        matched = decision is not None and _decision_matches(
            case, decision, selected_catalog
        )
        provider_matches += int(matched)
        state.provider_route_topic_match_count += int(matched)
        result = _CaseResult(
            fixture_id=case.fixture_id,
            evidence_kind="ACTUAL_PROVIDER_SELECTOR",
            provider_route_topic_match=matched,
            outbound_count=outbound_count,
        )
        cases.append(result)
        state.cases.append(result)

    outbound = (
        state.ledger.classifier_attempts_used
        if state.ledger is not None
        else provider_case_count
    )
    return _EvaluationResult(
        cases_total=len(selected),
        deterministic_count=deterministic_count,
        provider_case_count=provider_case_count,
        route_topic_match_count=provider_matches,
        policy_privacy_outbound_count=0,
        outbound_attempt_count=outbound,
        cases=tuple(cases),
    )


class _UsageRecorder:
    """Aggregate only usage accepted by the same strict production parser."""

    def __init__(self) -> None:
        self._usage = TokenUsage(0, 0, 0)
        self.complete_response_count = 0
        self.rejected_response_count = 0

    @property
    def usage(self) -> TokenUsage:
        return self._usage

    async def capture(self, response: httpx.Response) -> None:
        try:
            await response.aread()
            if not 200 <= response.status_code < 300:
                self.rejected_response_count += 1
                return
            envelope = response.json()
            if type(envelope) is not dict:
                self.rejected_response_count += 1
                return
            usage = parse_provider_token_usage(
                envelope.get("usage"),
                max_input_tokens=UPSTAGE_MAX_INPUT_TOKENS,
                max_output_tokens=UPSTAGE_CLASSIFIER_MAX_OUTPUT_TOKENS,
            )
            if usage is None:
                self.rejected_response_count += 1
                return
        except Exception:
            self.rejected_response_count += 1
            return
        self._usage = TokenUsage(
            input_tokens=self._usage.input_tokens + usage.input_tokens,
            cached_input_tokens=(
                self._usage.cached_input_tokens + usage.cached_input_tokens
            ),
            output_tokens=self._usage.output_tokens + usage.output_tokens,
        )
        self.complete_response_count += 1


def _build_ledger(settings: UpstageClassifierSettings) -> ProviderAttemptLedger:
    return ProviderAttemptLedger(
        classifier_cap=settings.classifier_attempt_cap,
        generator_cap=settings.generator_attempt_cap,
        combined_cap=settings.combined_attempt_cap,
        cost_cap_usd=settings.session_cost_cap_usd,
        classifier_worst_case_usd=_worst_case_selector_cost(),
        generator_worst_case_usd=estimate_cost_usd(
            TokenUsage(
                UPSTAGE_MAX_INPUT_TOKENS,
                0,
                UPSTAGE_MAX_OUTPUT_TOKENS,
            )
        ),
    )


def _create_selector(
    settings: UpstageClassifierSettings,
    client: object,
    ledger: ProviderAttemptLedger,
    catalog: TopicCatalog,
    recorder: _UsageRecorder,
) -> _Selector:
    del recorder
    if not isinstance(client, httpx.AsyncClient):
        raise _ConfigurationInvalid
    return _ActualSelector(
        QuestionClassifier(settings=settings, client=client, ledger=ledger),
        catalog,
    )


class _ActualSelector:
    def __init__(self, classifier: QuestionClassifier, catalog: TopicCatalog) -> None:
        self._classifier = classifier
        self._catalog = catalog

    async def classify(self, question: SafeQuestion) -> ClassifierDecision | None:
        return await self._classifier.classify(question, self._catalog)


def _cost_evidence(
    evidence: _RunEvidence,
) -> tuple[TokenUsage, Decimal, Decimal, int, bool]:
    recorder = evidence.recorder
    ledger = evidence.ledger
    usage = TokenUsage(0, 0, 0) if recorder is None else recorder.usage
    observed_cost = estimate_cost_usd(usage)
    if ledger is None:
        return usage, observed_cost, observed_cost, 0, True
    attempts = ledger.classifier_attempts_used
    observed_responses = 0 if recorder is None else recorder.complete_response_count
    conservative_attempts = max(0, attempts - observed_responses)
    expected_ledger_cost = (
        observed_cost + Decimal(conservative_attempts) * _worst_case_selector_cost()
    )
    return (
        usage,
        observed_cost,
        ledger.actual_cost_usd,
        conservative_attempts,
        ledger.actual_cost_usd == expected_ledger_cost,
    )


def _build_evidence_report(
    evidence: _RunEvidence,
    *,
    acceptance: str,
) -> dict[str, object]:
    identities = evidence.identities
    usage, observed_cost, ledger_cost, conservative_attempts, reconciled = (
        _cost_evidence(evidence)
    )
    attempts = (
        0 if evidence.ledger is None else evidence.ledger.classifier_attempts_used
    )
    usage_responses = (
        0 if evidence.recorder is None else evidence.recorder.complete_response_count
    )
    return {
        "source_sha": evidence.source_sha,
        "fixture_sha256": (
            "NOT_VERIFIED" if identities is None else identities.fixture_sha256
        ),
        "coverage_sha256": (
            "NOT_VERIFIED" if identities is None else identities.coverage_sha256
        ),
        "official_records_sha256": (
            "NOT_VERIFIED" if identities is None else identities.official_records_sha256
        ),
        "release_manifest_sha256": (
            "NOT_VERIFIED" if identities is None else identities.release_manifest_sha256
        ),
        "offline_evidence_sha256": (
            "NOT_VERIFIED" if identities is None else identities.offline_evidence_sha256
        ),
        "release_version": (
            "NOT_VERIFIED" if identities is None else identities.release_version
        ),
        "protected_inputs_clean": evidence.protected_inputs_clean,
        "key_present": evidence.key_present,
        "model": UPSTAGE_MODEL,
        "cases_total": len(evidence.cases),
        "selected_count": evidence.selected_count,
        "skip_count": 0,
        "prior_offline_deterministic_provider_free_count": (
            evidence.prior_offline_deterministic_provider_free_count
        ),
        "provider_case_count": evidence.provider_case_count,
        "provider_route_topic_match_count": (evidence.provider_route_topic_match_count),
        "policy_privacy_outbound_count": evidence.policy_privacy_outbound_count,
        "outbound_attempt_count": attempts,
        "observed_usage_response_count": usage_responses,
        "conservative_charged_attempt_count": conservative_attempts,
        "input_tokens": usage.input_tokens,
        "cached_input_tokens": usage.cached_input_tokens,
        "output_tokens": usage.output_tokens,
        "observed_usage_cost_usd_including_vat": _decimal_text(observed_cost),
        "ledger_charged_cost_usd_including_vat": _decimal_text(ledger_cost),
        "cost_reconciled": reconciled,
        "cost_cap_usd_including_vat": _decimal_text(LOCAL_INTERACTIVE_COST_CAP_USD),
        "elapsed_ms": evidence.elapsed_ms,
        "acceptance": acceptance,
        "cases": tuple(evidence.cases),
    }


def _build_report(
    *,
    result: _EvaluationResult,
    usage: TokenUsage,
    key_present: bool,
    source_sha: str,
    elapsed_ms: int = 0,
) -> dict[str, object]:
    evidence = _RunEvidence(
        source_sha=source_sha,
        key_present=key_present,
        selected_count=result.cases_total,
        prior_offline_deterministic_provider_free_count=result.deterministic_count,
        provider_case_count=result.provider_case_count,
        provider_route_topic_match_count=result.route_topic_match_count,
        policy_privacy_outbound_count=result.policy_privacy_outbound_count,
        cases=list(result.cases),
        elapsed_ms=elapsed_ms,
    )
    recorder = _UsageRecorder()
    recorder._usage = usage
    recorder.complete_response_count = result.provider_case_count
    evidence.recorder = recorder
    acceptance = (
        "PASS"
        if (
            result.cases_total == 20
            and result.deterministic_count == _EXPECTED_DETERMINISTIC_CASES
            and result.provider_case_count == _EXPECTED_PROVIDER_CASES
            and result.route_topic_match_count == _EXPECTED_PROVIDER_CASES
            and result.policy_privacy_outbound_count == 0
            and result.outbound_attempt_count == _EXPECTED_PROVIDER_CASES
            and estimate_cost_usd(usage) <= LOCAL_INTERACTIVE_COST_CAP_USD
        )
        else "FAIL"
    )
    return _build_evidence_report(evidence, acceptance=acceptance)


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _report_to_markdown(report: dict[str, object]) -> str:
    lines = [
        "# CHAT-HYBRID-RAG-001 Upstage Actual Selector Evidence",
        "",
        "- Provider content retention: `0`",
        "- Key presence only: `true` or `false`",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    lines.extend(f"| `{field}` | `{report[field]}` |" for field in _REPORT_FIELDS)
    lines.extend(
        [
            "",
            "| Fixture ID | Evidence kind | Actual provider route/topic match | Outbound |",
            "|---|---|---:|---:|",
        ]
    )
    for case in cast(tuple[object, ...], report["cases"]):
        if type(case) is not _CaseResult:
            raise _RuntimeFailed
        match = (
            "not-applicable"
            if case.provider_route_topic_match is None
            else str(case.provider_route_topic_match).lower()
        )
        lines.append(
            f"| `{case.fixture_id}` | `{case.evidence_kind}` | `{match}` | "
            f"`{case.outbound_count}` |"
        )
    lines.extend(
        [
            "",
            "This artifact contains bounded aggregate evidence only.",
            "",
        ]
    )
    return "\n".join(lines)


def _atomic_write_text(path: Path, text: str) -> None:
    descriptor: int | None = None
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            descriptor = None
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
    except OSError:
        raise _RuntimeFailed from None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass


def _atomic_write_report(path: Path, report: dict[str, object]) -> None:
    _atomic_write_text(path, _report_to_markdown(report))


async def _execute_actual(
    options: _RunnerOptions,
    evidence: _RunEvidence | None = None,
) -> dict[str, object]:
    state = _RunEvidence() if evidence is None else evidence
    started = time.perf_counter()
    fixtures = _load_fixtures(options.fixture_path)
    selected = tuple(case for case in fixtures if case.actual_subset)
    state.selected_count = len(selected)
    _require_offline_gate()
    _require_clean_secret_scan()
    _require_protected_inputs_clean()
    state.protected_inputs_clean = True
    settings = load_upstage_classifier_settings()
    if settings is None:
        raise _ConfigurationInvalid
    state.key_present = True
    _validate_settings(settings)
    identities, catalog = _load_pinned_inputs()
    state.identities = identities
    state.source_sha = _source_sha()
    recorder = _UsageRecorder()
    ledger = _build_ledger(settings)
    state.recorder = recorder
    state.ledger = ledger

    client = create_upstage_classifier_client(settings)
    if isinstance(client, httpx.AsyncClient):
        client.event_hooks.setdefault("response", []).append(recorder.capture)
    try:
        async with client:
            selector = _create_selector(
                settings,
                client,
                ledger,
                catalog,
                recorder,
            )
            result = await _evaluate_selected(
                selected,
                selector=selector,
                usage=TokenUsage(0, 0, 0),
                cost_cap=settings.session_cost_cap_usd,
                catalog=catalog,
                evidence=state,
            )
    finally:
        state.elapsed_ms = max(
            0,
            round((time.perf_counter() - started) * 1000),
        )

    _, observed_cost, ledger_cost, conservative_attempts, reconciled = _cost_evidence(
        state
    )
    accepted = (
        result.cases_total == 20
        and result.deterministic_count == _EXPECTED_DETERMINISTIC_CASES
        and result.provider_case_count == _EXPECTED_PROVIDER_CASES
        and result.route_topic_match_count == _EXPECTED_PROVIDER_CASES
        and result.policy_privacy_outbound_count == 0
        and ledger.classifier_attempts_used == _EXPECTED_PROVIDER_CASES
        and recorder.complete_response_count == _EXPECTED_PROVIDER_CASES
        and conservative_attempts == 0
        and reconciled
        and observed_cost == ledger_cost
        and ledger_cost <= settings.session_cost_cap_usd
    )
    report = _build_evidence_report(
        state,
        acceptance="PASS" if accepted else "FAIL",
    )
    if not accepted:
        raise _AcceptanceFailed
    return report


def _safe_console_report(report: dict[str, object]) -> str:
    safe_fields = {
        field: report[field]
        for field in _REPORT_FIELDS
        if field
        not in {
            "source_sha",
            "fixture_sha256",
            "coverage_sha256",
            "official_records_sha256",
            "release_manifest_sha256",
            "offline_evidence_sha256",
        }
    }
    return json.dumps(
        safe_fields,
        ensure_ascii=True,
        separators=(",", ":"),
    )


def _failure_exit_code(error: Exception) -> int:
    if isinstance(error, (_ConfigurationInvalid, _FixturesInvalid)):
        return 2
    if isinstance(error, _AcceptanceFailed):
        return 1
    return 3


def main(argv: Sequence[str] | None = None) -> int:
    try:
        options = _parse_args(argv)
    except Exception:
        print("HYBRID_RAG_ACTUAL_ARGUMENTS_INVALID", file=sys.stderr)
        return 2
    try:
        lease = _RunLease.acquire(options.report_path)
    except _RunAlreadyExists:
        print("HYBRID_RAG_ACTUAL_RUN_ALREADY_RECORDED", file=sys.stderr)
        return 2
    except Exception:
        print("HYBRID_RAG_ACTUAL_CONFIGURATION_INVALID", file=sys.stderr)
        return 2

    evidence = _RunEvidence()
    report_written = False
    try:
        try:
            report = asyncio.run(_execute_actual(options, evidence))
        except Exception as error:
            try:
                report = _build_evidence_report(evidence, acceptance="FAIL")
                _atomic_write_report(options.report_path, report)
                report_written = True
            except Exception:
                print(
                    "HYBRID_RAG_ACTUAL_EVIDENCE_WRITE_FAILED",
                    file=sys.stderr,
                )
                return 3
            exit_code = _failure_exit_code(error)
            message = (
                "HYBRID_RAG_ACTUAL_CONFIGURATION_INVALID"
                if exit_code == 2
                else "HYBRID_RAG_ACTUAL_ACCEPTANCE_FAILED"
                if exit_code == 1
                else "HYBRID_RAG_ACTUAL_RUNTIME_FAILED"
            )
            print(message, file=sys.stderr)
            return exit_code

        try:
            _atomic_write_report(options.report_path, report)
            report_written = True
        except Exception:
            print("HYBRID_RAG_ACTUAL_EVIDENCE_WRITE_FAILED", file=sys.stderr)
            return 3
        print(_safe_console_report(report))
        return 0
    finally:
        lease.release(report_written=report_written)


if __name__ == "__main__":
    raise SystemExit(main())
