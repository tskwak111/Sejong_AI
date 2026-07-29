#!/usr/bin/env python3
"""Run the one-shot, aggregate-only DeepSeek classifier acceptance."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, NoReturn, Protocol

import httpx

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_API_SOURCE = _REPOSITORY_ROOT / "apps" / "api" / "src"
_FIXTURE_PATH = (
    _REPOSITORY_ROOT
    / "apps"
    / "api"
    / "tests"
    / "chat"
    / "fixtures"
    / "hybrid-rag-uat.v1.json"
)
_REPORT_PATH = (
    _REPOSITORY_ROOT
    / "docs"
    / "test-reports"
    / "CHAT-HYBRID-RAG-001-DEEPSEEK-ACTUAL.md"
)
_OFFLINE_DIRECTORY = (
    _REPOSITORY_ROOT
    / ".superpowers"
    / "sdd"
    / "2026-07-29-deepseek-classifier-provider"
)
_OFFLINE_RESULT_PATH = _OFFLINE_DIRECTORY / "a074-offline-gate-result.json"
_OFFLINE_LOCK_PATH = _OFFLINE_DIRECTORY / "a074-offline-gate-result.json.run.lock"
_OFFLINE_STDOUT_PATH = _OFFLINE_DIRECTORY / "a074-offline-gate.stdout.log"
_OFFLINE_STDERR_PATH = _OFFLINE_DIRECTORY / "a074-offline-gate.stderr.log"
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
_EXPECTED_RELEASE_VERSION = "0.1.0-initial.2"
_EXPECTED_RELEASE_ID = "sejong-official-0.1.0-initial.2"
_EXPECTED_SELECTED_IDS = (
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
_EXPECTED_SELECTED_GROUPS = Counter(
    {
        "PARAPHRASE_SUCCESS": 8,
        "TOPIC_DISTINCTION": 4,
        "NO_TOPIC_GROUNDING": 4,
        "SCOPE_OR_NON_CIVIC": 4,
    }
)
_POLICY_PRIVACY_IDS = ("HR-045", "HR-046", "HR-047", "HR-048")
_EXPECTED_SELECTED_COUNT = 20
_EXPECTED_SKIP_COUNT = 0
_EXPECTED_DETERMINISTIC_COUNT = 11
_EXPECTED_PROVIDER_COUNT = 9
_EXPECTED_POLICY_PRIVACY_PROBE_COUNT = 4
_ACTUAL_COST_CAP_USD = Decimal("0.20")
_ACTUAL_INVOCATION_COUNT = 1
_ACTUAL_RETRY_COUNT = 0
_ACTUAL_RERUN_COUNT = 0
_ACTUAL_RUN_DEADLINE_SECONDS = 32
_FIXTURE_MAX_BYTES = 1024 * 1024
_COVERAGE_MAX_BYTES = 1024 * 1024
_OFFICIAL_RECORDS_MAX_BYTES = 4 * 1024 * 1024
_RELEASE_MANIFEST_MAX_BYTES = 256 * 1024
_OFFLINE_RESULT_MAX_BYTES = 64 * 1024
_OFFLINE_LOG_MAX_BYTES = 64 * 1024 * 1024
_OFFLINE_LEASE_TEXT = "A-074-OFFLINE-GATE one-shot lease\n"
_ACTUAL_LEASE_TEXT = "A-074-DEEPSEEK-CLASSIFIER one-shot lease\n"
_UPSTAGE_MODE_KEYS = (
    "UPSTAGE_SYNTHETIC_EVALUATION_MODE",
    "UPSTAGE_CLASSIFIER_MODE",
    "UPSTAGE_GROUNDED_CHAT_MODE",
)
_SENSITIVE_PATTERN = re.compile(
    r"(?:[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    r"|01[016789][-\s]?\d{3,4}[-\s]?\d{4}"
    r"|\d{6}[-\s]?[1-4]\d{6}"
    r"|(?:sk|up)_[A-Za-z0-9_-]{12,}"
    r"|postgres(?:ql)?://)",
    re.IGNORECASE,
)
_OFFLINE_RESULT_FIELDS = frozenset(
    {
        "schema_version",
        "gate",
        "source_sha",
        "outcome",
        "exit_code",
        "timed_out",
        "invocation_count",
        "rerun_count",
        "stdout_sha256",
        "stdout_bytes",
        "stderr_sha256",
        "stderr_bytes",
    }
)

if str(_API_SOURCE) not in sys.path:
    sys.path.insert(0, str(_API_SOURCE))

from sejong_ai_api.chat.classification import SafeQuestion, classify_question  # noqa: E402
from sejong_ai_api.chat.topic_catalog import (  # noqa: E402
    TopicCatalog,
    TopicCoverage,
    build_topic_catalog,
)
from sejong_ai_api.db.models import Intent, KnowledgeRecord  # noqa: E402
from sejong_ai_api.llm.classifier_contracts import (  # noqa: E402
    ClassifierDecision,
    ClassifierRoute,
)
from sejong_ai_api.llm.classifier_diagnostics import (  # noqa: E402
    ClassifierResponseStage,
)
from sejong_ai_api.llm.contracts import TokenUsage  # noqa: E402
from sejong_ai_api.llm.deepseek_classifier import (  # noqa: E402
    DeepSeekQuestionClassifier,
    DeepSeekResponseObservation,
    create_deepseek_classifier_client,
)
from sejong_ai_api.llm.deepseek_settings import (  # noqa: E402
    DEEPSEEK_BASE_URL,
    DEEPSEEK_CLASSIFIER_ATTEMPT_CAP,
    DEEPSEEK_COMBINED_ATTEMPT_CAP,
    DEEPSEEK_GENERATOR_ATTEMPT_CAP,
    DEEPSEEK_MAX_CONCURRENCY,
    DEEPSEEK_MAX_INPUT_CHARS,
    DEEPSEEK_MAX_INPUT_USAGE_TOKENS,
    DEEPSEEK_MAX_OUTPUT_TOKENS,
    DEEPSEEK_MAX_RETRIES,
    DEEPSEEK_MODEL,
    DEEPSEEK_PROVIDER,
    DEEPSEEK_TEMPERATURE,
    DEEPSEEK_THINKING_ENABLED,
    DEEPSEEK_TIMEOUT_SECONDS,
    DeepSeekClassifierSettings,
    load_deepseek_classifier_settings,
)
from sejong_ai_api.llm.deepseek_usage import (  # noqa: E402
    DEEPSEEK_PRICING_CHECKED_ON,
    DEEPSEEK_PRICING_SOURCE_URL,
    estimate_deepseek_cost_usd,
)
from sejong_ai_api.llm.limits import ProviderAttemptLedger  # noqa: E402
from sejong_ai_api.llm.strict_json import load_strict_json_bytes  # noqa: E402
from sejong_ai_api.privacy.redaction import redact_question  # noqa: E402


class _ArgumentsInvalid(ValueError):
    """Only the canonical runner paths and fixed mode are accepted."""


class _ConfigurationInvalid(RuntimeError):
    """A network-free readiness invariant failed."""


class _FixturesInvalid(RuntimeError):
    """The canonical fixture is not the approved corpus."""


class _RuntimeFailed(RuntimeError):
    """A post-lease runtime invariant failed."""


class _EvidenceWriteFailed(RuntimeError):
    """The immutable aggregate report could not be written."""


class _RunAlreadyExists(RuntimeError):
    """A permanent lease or immutable report already exists."""


class _Classifier(Protocol):
    async def classify(
        self,
        question: SafeQuestion,
        catalog: TopicCatalog,
    ) -> ClassifierDecision | None: ...


@dataclass(frozen=True, slots=True)
class _RunnerOptions:
    fixture_path: Path
    report_path: Path
    readiness_only: bool = False


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
class _ActualSelection:
    selected: tuple[_Fixture, ...]
    selected_count: int
    skip_count: int
    deterministic_provider_free_count: int
    provider_case_count: int


@dataclass(frozen=True, slots=True)
class _PolicyProbeResult:
    probe_count: int
    outbound_count: int


@dataclass(frozen=True, slots=True)
class _InputIdentities:
    fixture_sha256: str
    coverage_sha256: str
    official_records_sha256: str
    release_manifest_sha256: str
    offline_result_sha256: str
    release_version: str


@dataclass(frozen=True, slots=True)
class _PreparedRun:
    source_sha: str
    settings: DeepSeekClassifierSettings
    fixtures: tuple[_Fixture, ...]
    selection: _ActualSelection
    catalog: TopicCatalog
    identities: _InputIdentities
    report_path: Path


@dataclass(frozen=True, slots=True)
class _EvaluationResult:
    selected_count: int
    skip_count: int
    deterministic_provider_free_count: int
    provider_case_count: int
    outbound_attempt_count: int
    server_decision_accepted_count: int
    oracle_match_count: int


@dataclass(slots=True)
class _RunEvidence:
    source_sha: str
    identities: _InputIdentities
    model: str
    selected_count: int = 0
    skip_count: int = 0
    deterministic_provider_free_count: int = 0
    provider_case_count: int = 0
    policy_privacy_probe_count: int = 0
    policy_privacy_outbound_count: int = 0
    outbound_attempt_count: int = 0
    provider_response_count: int = 0
    http_2xx_count: int = 0
    http_rejected_count: int = 0
    transport_no_response_count: int = 0
    strict_parse_count: int = 0
    server_decision_accepted_count: int = 0
    oracle_match_count: int = 0
    usage_accepted_count: int = 0
    usage_rejected_count: int = 0
    response_stage_counts: Counter[ClassifierResponseStage] = field(
        default_factory=Counter
    )
    usage: TokenUsage = field(default_factory=lambda: TokenUsage(0, 0, 0))
    conservative_cost_usd: Decimal = Decimal("0")
    runtime_failure_count: int = 0
    invocation_count: int = _ACTUAL_INVOCATION_COUNT
    retry_count: int = _ACTUAL_RETRY_COUNT
    rerun_count: int = _ACTUAL_RERUN_COUNT
    concurrency: int = DEEPSEEK_MAX_CONCURRENCY
    max_output_tokens: int = DEEPSEEK_MAX_OUTPUT_TOKENS
    retained_question_count: int = 0
    retained_masked_question_count: int = 0
    retained_request_body_count: int = 0
    retained_response_body_count: int = 0
    retained_invalid_value_count: int = 0
    retained_secret_count: int = 0


@dataclass(frozen=True, slots=True)
class _RunLease:
    lock_path: Path

    @classmethod
    def acquire(cls, report_path: Path) -> _RunLease:
        _require_actual_absent(report_path)
        lock_path = _lease_path(report_path)
        descriptor: int | None = None
        try:
            descriptor = os.open(
                lock_path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            os.write(descriptor, _ACTUAL_LEASE_TEXT.encode("ascii"))
            os.fsync(descriptor)
        except FileExistsError:
            raise _RunAlreadyExists from None
        except OSError:
            # A created lease is intentionally never removed, including I/O failure.
            raise _ConfigurationInvalid from None
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        return cls(lock_path)


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> NoReturn:
        raise _ArgumentsInvalid from None


class _UsageRecorder:
    """Keep only aggregate HTTP class and strict DeepSeek usage totals."""

    def __init__(self) -> None:
        self.response_count = 0
        self.http_2xx_count = 0
        self.http_rejected_count = 0
        self.usage_accepted_count = 0
        self.usage_rejected_count = 0
        self.usage = TokenUsage(0, 0, 0)

    def capture(self, observation: DeepSeekResponseObservation) -> None:
        if type(observation) is not DeepSeekResponseObservation:
            raise ValueError("DEEPSEEK_RESPONSE_OBSERVATION_INVALID")
        self.response_count += 1
        if observation.http_2xx:
            self.http_2xx_count += 1
        else:
            self.http_rejected_count += 1
            return
        usage = observation.usage
        if usage is None:
            self.usage_rejected_count += 1
            return
        self.usage = TokenUsage(
            self.usage.input_tokens + usage.input_tokens,
            self.usage.cached_input_tokens + usage.cached_input_tokens,
            self.usage.output_tokens + usage.output_tokens,
        )
        self.usage_accepted_count += 1


class _ResponseStageRecorder:
    """Keep only a closed terminal enum aggregate."""

    def __init__(self) -> None:
        self.counts: Counter[ClassifierResponseStage] = Counter()

    def capture(self, stage: ClassifierResponseStage) -> None:
        if type(stage) is not ClassifierResponseStage:
            raise ValueError("CLASSIFIER_RESPONSE_STAGE_INVALID")
        self.counts[stage] += 1


def _parse_args(argv: Sequence[str] | None = None) -> _RunnerOptions:
    parser = _SafeArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--readiness-only", action="store_true")
    values = parser.parse_args(argv)
    fixture_path = _resolve_repository_path(values.fixture)
    report_path = _resolve_repository_path(values.report)
    if fixture_path != _FIXTURE_PATH.resolve() or report_path != _REPORT_PATH.resolve():
        raise _ArgumentsInvalid
    return _RunnerOptions(
        fixture_path=fixture_path,
        report_path=report_path,
        readiness_only=bool(values.readiness_only),
    )


def _resolve_repository_path(value: object) -> Path:
    if type(value) is not str or not value or "\x00" in value:
        raise _ArgumentsInvalid
    path = Path(value)
    return (path if path.is_absolute() else _REPOSITORY_ROOT / path).resolve()


def _read_bounded_file_once(path: Path, *, max_bytes: int) -> bytes:
    if not isinstance(path, Path) or type(max_bytes) is not int or max_bytes <= 0:
        raise _ConfigurationInvalid
    try:
        with path.open("rb") as stream:
            payload = stream.read(max_bytes + 1)
    except OSError:
        raise _ConfigurationInvalid from None
    if len(payload) > max_bytes:
        raise _ConfigurationInvalid
    return payload


def _sha256_bytes(payload: bytes) -> str:
    if type(payload) is not bytes:
        raise _ConfigurationInvalid
    return hashlib.sha256(payload).hexdigest()


def _require_exact_bytes(path: Path, expected: str, *, max_bytes: int) -> bytes:
    payload = _read_bounded_file_once(path, max_bytes=max_bytes)
    actual = _sha256_bytes(payload)
    if actual != expected:
        raise _ConfigurationInvalid
    return payload


def _load_fixtures(path: Path) -> tuple[_Fixture, ...]:
    if path.resolve() != _FIXTURE_PATH.resolve():
        raise _FixturesInvalid
    try:
        payload = _require_exact_bytes(
            path,
            _EXPECTED_FIXTURE_SHA256,
            max_bytes=_FIXTURE_MAX_BYTES,
        )
        document = load_strict_json_bytes(payload)
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
    required_keys = frozenset(
        {
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
    )
    followup_keys = frozenset(
        {
            "expected_followup_options",
            "expected_pending_slot",
        }
    )
    for raw in raw_cases:
        if (
            type(raw) is not dict
            or not required_keys.issubset(raw)
            or frozenset(raw) - required_keys not in (frozenset(), followup_keys)
        ):
            raise _FixturesInvalid
        fixture_id = raw["id"]
        group = raw["group"]
        question = raw["question"]
        expected_route = raw["expected_route"]
        expected_intent = raw["expected_intent"]
        expected_topic_id = raw["expected_topic_id"]
        expected_provider_use = raw["expected_provider_use"]
        actual_subset = raw["actual_subset"]
        if (
            type(fixture_id) is not str
            or type(group) is not str
            or type(question) is not str
            or type(expected_route) is not str
            or type(expected_intent) is not str
            or (expected_topic_id is not None and type(expected_topic_id) is not str)
            or type(expected_provider_use) is not int
            or expected_provider_use not in (0, 1)
            or type(actual_subset) is not bool
        ):
            raise _FixturesInvalid
        redaction = redact_question(question)
        safe_for_provider = (
            redaction.masked_text == question
            and not redaction.findings
            and redaction.safe_for_synthetic_provider is True
            and redaction.unresolved_reason is None
            and _SENSITIVE_PATTERN.search(question) is None
        )
        fixtures.append(
            _Fixture(
                fixture_id=fixture_id,
                group=group,
                question=question,
                expected_route=expected_route,
                expected_intent=expected_intent,
                expected_topic_id=expected_topic_id,
                expected_provider_use=expected_provider_use,
                actual_subset=actual_subset,
                safe_for_provider=safe_for_provider,
            )
        )
    if len(fixtures) != 48:
        raise _FixturesInvalid
    return tuple(fixtures)


def _select_actual_cases(fixtures: tuple[_Fixture, ...]) -> _ActualSelection:
    selected = tuple(case for case in fixtures if case.actual_subset)
    deterministic_count = sum(case.expected_provider_use == 0 for case in selected)
    provider_count = sum(case.expected_provider_use == 1 for case in selected)
    if (
        tuple(case.fixture_id for case in selected) != _EXPECTED_SELECTED_IDS
        or Counter(case.group for case in selected) != _EXPECTED_SELECTED_GROUPS
        or len(selected) != _EXPECTED_SELECTED_COUNT
        or deterministic_count != _EXPECTED_DETERMINISTIC_COUNT
        or provider_count != _EXPECTED_PROVIDER_COUNT
        or any(
            not case.safe_for_provider or case.group == "PRIVACY_POLICY"
            for case in selected
        )
    ):
        raise _FixturesInvalid
    return _ActualSelection(
        selected=selected,
        selected_count=len(selected),
        skip_count=_EXPECTED_SKIP_COUNT,
        deterministic_provider_free_count=deterministic_count,
        provider_case_count=provider_count,
    )


def _evaluate_policy_privacy_probes(
    fixtures: tuple[_Fixture, ...],
) -> _PolicyProbeResult:
    probes = tuple(case for case in fixtures if case.fixture_id in _POLICY_PRIVACY_IDS)
    if tuple(case.fixture_id for case in probes) != _POLICY_PRIVACY_IDS or any(
        case.group != "PRIVACY_POLICY"
        or case.actual_subset
        or case.expected_provider_use != 0
        for case in probes
    ):
        raise _FixturesInvalid
    for case in probes:
        try:
            safe_question = SafeQuestion(redact_question(case.question))
            outcome = classify_question(safe_question)
        except (TypeError, ValueError):
            raise _FixturesInvalid from None
        if outcome.needs_provider:
            raise _FixturesInvalid
    return _PolicyProbeResult(probe_count=len(probes), outbound_count=0)


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


def _parse_topic_coverage_bytes(payload: bytes) -> tuple[TopicCoverage, ...]:
    try:
        document = load_strict_json_bytes(payload)
    except (UnicodeError, TypeError, ValueError):
        raise _ConfigurationInvalid from None
    if (
        type(document) is not dict
        or frozenset(document) != {"schema_version", "data_kind", "topics"}
        or document["schema_version"] != 1
        or document["data_kind"] != "NON_FACTUAL_RETRIEVAL_METADATA"
        or type(document["topics"]) is not list
    ):
        raise _ConfigurationInvalid
    coverage: list[TopicCoverage] = []
    try:
        for raw in document["topics"]:
            if type(raw) is not dict or frozenset(raw) != {
                "topic_id",
                "intent",
                "coverage_id",
                "coverage_label",
            }:
                raise _ConfigurationInvalid
            coverage.append(
                TopicCoverage(
                    topic_id=raw["topic_id"],
                    intent=Intent(raw["intent"]),
                    coverage_id=raw["coverage_id"],
                    coverage_label=raw["coverage_label"],
                )
            )
    except (KeyError, TypeError, ValueError):
        raise _ConfigurationInvalid from None
    if len({item.topic_id for item in coverage}) != len(coverage):
        raise _ConfigurationInvalid
    return tuple(sorted(coverage, key=lambda item: item.topic_id))


def _load_pinned_catalog() -> TopicCatalog:
    coverage_payload = _require_exact_bytes(
        _COVERAGE_PATH,
        _EXPECTED_COVERAGE_SHA256,
        max_bytes=_COVERAGE_MAX_BYTES,
    )
    records_payload = _require_exact_bytes(
        _OFFICIAL_RECORDS_PATH,
        _EXPECTED_OFFICIAL_RECORDS_SHA256,
        max_bytes=_OFFICIAL_RECORDS_MAX_BYTES,
    )
    manifest_payload = _require_exact_bytes(
        _RELEASE_MANIFEST_PATH,
        _EXPECTED_RELEASE_MANIFEST_SHA256,
        max_bytes=_RELEASE_MANIFEST_MAX_BYTES,
    )
    try:
        manifest = load_strict_json_bytes(manifest_payload)
        release = load_strict_json_bytes(records_payload)
        raw_records = release["records"]
        artifacts = manifest["artifacts"]
    except (OSError, UnicodeError, ValueError, KeyError, TypeError):
        raise _ConfigurationInvalid from None
    if (
        type(manifest) is not dict
        or manifest.get("schema_version") != 2
        or manifest.get("release_id") != _EXPECTED_RELEASE_ID
        or manifest.get("release_version") != _EXPECTED_RELEASE_VERSION
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
        coverage = _parse_topic_coverage_bytes(coverage_payload)
        catalog = build_topic_catalog(records, coverage)
    except (KeyError, TypeError, ValueError):
        raise _ConfigurationInvalid from None
    if (
        len(catalog.topics) != 19
        or not catalog.provider_eligible
        or len({topic.record.public_id for topic in catalog.topics}) != 19
    ):
        raise _ConfigurationInvalid
    return catalog


def _source_sha(repository_root: Path = _REPOSITORY_ROOT) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        raise _ConfigurationInvalid from None
    value = completed.stdout.strip()
    if completed.returncode != 0 or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise _ConfigurationInvalid
    return value


def _require_clean_worktree(repository_root: Path = _REPOSITORY_ROOT) -> None:
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=repository_root,
            check=False,
            capture_output=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        raise _ConfigurationInvalid from None
    if completed.returncode != 0 or completed.stdout != b"":
        raise _ConfigurationInvalid


def _strict_nonnegative_int(value: object) -> bool:
    return type(value) is int and value >= 0


def _require_offline_gate(source_sha: str) -> str:
    if re.fullmatch(r"[0-9a-f]{40}", source_sha) is None:
        raise _ConfigurationInvalid
    try:
        lock_payload = _read_bounded_file_once(
            _OFFLINE_LOCK_PATH,
            max_bytes=1024,
        )
        if lock_payload != _OFFLINE_LEASE_TEXT.encode("ascii"):
            raise _ConfigurationInvalid
        result_payload = _read_bounded_file_once(
            _OFFLINE_RESULT_PATH,
            max_bytes=_OFFLINE_RESULT_MAX_BYTES,
        )
        document = load_strict_json_bytes(result_payload)
        stdout_payload = _read_bounded_file_once(
            _OFFLINE_STDOUT_PATH,
            max_bytes=_OFFLINE_LOG_MAX_BYTES,
        )
        stderr_payload = _read_bounded_file_once(
            _OFFLINE_STDERR_PATH,
            max_bytes=_OFFLINE_LOG_MAX_BYTES,
        )
    except (UnicodeError, ValueError, TypeError):
        raise _ConfigurationInvalid from None
    if (
        type(document) is not dict
        or frozenset(document) != _OFFLINE_RESULT_FIELDS
        or document["schema_version"] != 1
        or document["gate"] != "A-074-OFFLINE"
        or document["source_sha"] != source_sha
        or document["outcome"] != "PASS"
        or document["exit_code"] != 0
        or document["timed_out"] is not False
        or document["invocation_count"] != 1
        or document["rerun_count"] != 0
        or not _strict_nonnegative_int(document["stdout_bytes"])
        or not _strict_nonnegative_int(document["stderr_bytes"])
        or type(document["stdout_sha256"]) is not str
        or type(document["stderr_sha256"]) is not str
    ):
        raise _ConfigurationInvalid
    stdout_hash = _sha256_bytes(stdout_payload)
    stderr_hash = _sha256_bytes(stderr_payload)
    stdout_bytes = len(stdout_payload)
    stderr_bytes = len(stderr_payload)
    if (
        document["stdout_sha256"] != stdout_hash
        or document["stdout_bytes"] != stdout_bytes
        or document["stderr_sha256"] != stderr_hash
        or document["stderr_bytes"] != stderr_bytes
    ):
        raise _ConfigurationInvalid
    return _sha256_bytes(result_payload)


def _validate_settings(settings: DeepSeekClassifierSettings) -> None:
    if (
        type(settings) is not DeepSeekClassifierSettings
        or settings.provider != DEEPSEEK_PROVIDER
        or settings.model != DEEPSEEK_MODEL
        or settings.base_url != DEEPSEEK_BASE_URL
        or settings.timeout_seconds != DEEPSEEK_TIMEOUT_SECONDS
        or settings.max_retries != DEEPSEEK_MAX_RETRIES
        or settings.max_concurrency != DEEPSEEK_MAX_CONCURRENCY
        or settings.max_input_chars != DEEPSEEK_MAX_INPUT_CHARS
        or settings.max_input_usage_tokens != DEEPSEEK_MAX_INPUT_USAGE_TOKENS
        or settings.max_output_tokens != DEEPSEEK_MAX_OUTPUT_TOKENS
        or settings.temperature != DEEPSEEK_TEMPERATURE
        or settings.thinking_enabled is not DEEPSEEK_THINKING_ENABLED
        or settings.classifier_attempt_cap != DEEPSEEK_CLASSIFIER_ATTEMPT_CAP
        or settings.generator_attempt_cap != DEEPSEEK_GENERATOR_ATTEMPT_CAP
        or settings.combined_attempt_cap != DEEPSEEK_COMBINED_ATTEMPT_CAP
        or settings.session_cost_cap_usd != _ACTUAL_COST_CAP_USD
    ):
        raise _ConfigurationInvalid


def _lease_path(report_path: Path) -> Path:
    return report_path.with_name(f"{report_path.name}.run.lock")


def _require_actual_absent(report_path: Path) -> None:
    if report_path.exists() or _lease_path(report_path).exists():
        raise _RunAlreadyExists


@contextmanager
def _force_upstage_modes_off() -> Iterator[None]:
    missing = object()
    previous: dict[str, object] = {
        key: os.environ.get(key, missing) for key in _UPSTAGE_MODE_KEYS
    }
    try:
        for key in _UPSTAGE_MODE_KEYS:
            os.environ[key] = "false"
        yield
    finally:
        for key, value in previous.items():
            if value is missing:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(value)


def _perform_readiness(options: _RunnerOptions) -> _PreparedRun:
    if (
        type(options) is not _RunnerOptions
        or options.fixture_path.resolve() != _FIXTURE_PATH.resolve()
        or options.report_path.resolve() != _REPORT_PATH.resolve()
    ):
        raise _ConfigurationInvalid
    _require_actual_absent(options.report_path)
    fixtures = _load_fixtures(options.fixture_path)
    selection = _select_actual_cases(fixtures)
    probes = _evaluate_policy_privacy_probes(fixtures)
    if (
        probes.probe_count != _EXPECTED_POLICY_PRIVACY_PROBE_COUNT
        or probes.outbound_count != 0
    ):
        raise _ConfigurationInvalid
    source_sha = _source_sha()
    _require_clean_worktree()
    offline_result_sha = _require_offline_gate(source_sha)
    settings = load_deepseek_classifier_settings()
    if settings is None:
        raise _ConfigurationInvalid
    _validate_settings(settings)
    if _EXPECTED_PROVIDER_COUNT * _worst_case_classifier_cost() > _ACTUAL_COST_CAP_USD:
        raise _ConfigurationInvalid
    catalog = _load_pinned_catalog()
    identities = _InputIdentities(
        fixture_sha256=_EXPECTED_FIXTURE_SHA256,
        coverage_sha256=_EXPECTED_COVERAGE_SHA256,
        official_records_sha256=_EXPECTED_OFFICIAL_RECORDS_SHA256,
        release_manifest_sha256=_EXPECTED_RELEASE_MANIFEST_SHA256,
        offline_result_sha256=offline_result_sha,
        release_version=_EXPECTED_RELEASE_VERSION,
    )
    return _PreparedRun(
        source_sha=source_sha,
        settings=settings,
        fixtures=fixtures,
        selection=selection,
        catalog=catalog,
        identities=identities,
        report_path=options.report_path,
    )


def _revalidate_prepared_run(prepared: _PreparedRun) -> None:
    """Recheck the prepared source and every pinned identity immediately pre-lease."""

    if type(prepared) is not _PreparedRun:
        raise _ConfigurationInvalid
    if _source_sha() != prepared.source_sha:
        raise _ConfigurationInvalid
    _require_clean_worktree()
    identities = prepared.identities
    if (
        _sha256_bytes(
            _read_bounded_file_once(
                _FIXTURE_PATH,
                max_bytes=_FIXTURE_MAX_BYTES,
            )
        )
        != identities.fixture_sha256
        or _sha256_bytes(
            _read_bounded_file_once(
                _COVERAGE_PATH,
                max_bytes=_COVERAGE_MAX_BYTES,
            )
        )
        != identities.coverage_sha256
        or _sha256_bytes(
            _read_bounded_file_once(
                _OFFICIAL_RECORDS_PATH,
                max_bytes=_OFFICIAL_RECORDS_MAX_BYTES,
            )
        )
        != identities.official_records_sha256
        or _sha256_bytes(
            _read_bounded_file_once(
                _RELEASE_MANIFEST_PATH,
                max_bytes=_RELEASE_MANIFEST_MAX_BYTES,
            )
        )
        != identities.release_manifest_sha256
        or _require_offline_gate(prepared.source_sha)
        != identities.offline_result_sha256
    ):
        raise _ConfigurationInvalid
    current_settings = load_deepseek_classifier_settings()
    if current_settings is None:
        raise _ConfigurationInvalid
    _validate_settings(current_settings)
    if current_settings != prepared.settings:
        raise _ConfigurationInvalid
    _require_actual_absent(prepared.report_path)


def _worst_case_classifier_cost() -> Decimal:
    return estimate_deepseek_cost_usd(
        TokenUsage(
            DEEPSEEK_MAX_INPUT_USAGE_TOKENS,
            0,
            DEEPSEEK_MAX_OUTPUT_TOKENS,
        )
    )


def _build_ledger(settings: DeepSeekClassifierSettings) -> ProviderAttemptLedger:
    _validate_settings(settings)
    worst_case = _worst_case_classifier_cost()
    return ProviderAttemptLedger(
        classifier_cap=settings.classifier_attempt_cap,
        generator_cap=settings.generator_attempt_cap,
        combined_cap=settings.combined_attempt_cap,
        cost_cap_usd=settings.session_cost_cap_usd,
        classifier_worst_case_usd=worst_case,
        generator_worst_case_usd=worst_case,
        classifier_cost_estimator=estimate_deepseek_cost_usd,
        generator_cost_estimator=estimate_deepseek_cost_usd,
    )


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


async def _evaluate_selected(
    selected: tuple[_Fixture, ...],
    *,
    classifier: _Classifier,
    catalog: TopicCatalog,
    ledger: ProviderAttemptLedger,
    evidence: _RunEvidence,
) -> _EvaluationResult:
    if (
        len(selected) != _EXPECTED_SELECTED_COUNT
        or type(catalog) is not TopicCatalog
        or type(ledger) is not ProviderAttemptLedger
        or type(evidence) is not _RunEvidence
    ):
        raise _RuntimeFailed
    deterministic_count = 0
    provider_count = 0
    accepted_count = 0
    oracle_match_count = 0
    for case in selected:
        try:
            safe_question = SafeQuestion(redact_question(case.question))
            outcome = classify_question(safe_question)
        except (TypeError, ValueError):
            raise _RuntimeFailed from None
        if case.expected_provider_use == 0:
            if outcome.needs_provider:
                raise _RuntimeFailed
            deterministic_count += 1
            continue
        if not outcome.needs_provider:
            raise _RuntimeFailed
        provider_count += 1
        decision = await classifier.classify(safe_question, catalog)
        if decision is not None:
            accepted_count += 1
            oracle_match_count += int(_decision_matches(case, decision, catalog))

    outbound_count = ledger.classifier_attempts_used
    result = _EvaluationResult(
        selected_count=len(selected),
        skip_count=_EXPECTED_SKIP_COUNT,
        deterministic_provider_free_count=deterministic_count,
        provider_case_count=provider_count,
        outbound_attempt_count=outbound_count,
        server_decision_accepted_count=accepted_count,
        oracle_match_count=oracle_match_count,
    )
    evidence.selected_count = result.selected_count
    evidence.skip_count = result.skip_count
    evidence.deterministic_provider_free_count = (
        result.deterministic_provider_free_count
    )
    evidence.provider_case_count = result.provider_case_count
    evidence.outbound_attempt_count = result.outbound_attempt_count
    evidence.strict_parse_count = result.server_decision_accepted_count
    evidence.server_decision_accepted_count = result.server_decision_accepted_count
    evidence.oracle_match_count = result.oracle_match_count
    return result


def _new_evidence(prepared: _PreparedRun) -> _RunEvidence:
    if type(prepared) is not _PreparedRun:
        raise _RuntimeFailed
    probes = _evaluate_policy_privacy_probes(prepared.fixtures)
    return _RunEvidence(
        source_sha=prepared.source_sha,
        identities=prepared.identities,
        model=prepared.settings.model,
        selected_count=prepared.selection.selected_count,
        skip_count=prepared.selection.skip_count,
        policy_privacy_probe_count=probes.probe_count,
        policy_privacy_outbound_count=probes.outbound_count,
    )


async def _execute_actual(
    prepared: _PreparedRun,
    evidence: _RunEvidence,
) -> None:
    ledger = _build_ledger(prepared.settings)
    usage_recorder = _UsageRecorder()
    stage_recorder = _ResponseStageRecorder()
    client = create_deepseek_classifier_client(prepared.settings)
    if not isinstance(client, httpx.AsyncClient):
        raise _RuntimeFailed
    try:
        async with client:
            classifier = DeepSeekQuestionClassifier(
                settings=prepared.settings,
                client=client,
                ledger=ledger,
                response_stage_observer=stage_recorder.capture,
                response_observer=usage_recorder.capture,
            )
            await _evaluate_selected(
                prepared.selection.selected,
                classifier=classifier,
                catalog=prepared.catalog,
                ledger=ledger,
                evidence=evidence,
            )
    finally:
        evidence.outbound_attempt_count = ledger.classifier_attempts_used
        evidence.provider_response_count = usage_recorder.response_count
        evidence.http_2xx_count = usage_recorder.http_2xx_count
        evidence.http_rejected_count = usage_recorder.http_rejected_count
        evidence.transport_no_response_count = max(
            0,
            ledger.classifier_attempts_used - usage_recorder.response_count,
        )
        evidence.usage_accepted_count = usage_recorder.usage_accepted_count
        evidence.usage_rejected_count = usage_recorder.usage_rejected_count
        evidence.usage = usage_recorder.usage
        evidence.response_stage_counts = Counter(stage_recorder.counts)
        evidence.conservative_cost_usd = ledger.actual_cost_usd


async def _execute_actual_with_deadline(
    prepared: _PreparedRun,
    evidence: _RunEvidence,
) -> None:
    async with asyncio.timeout(_ACTUAL_RUN_DEADLINE_SECONDS):
        await _execute_actual(prepared, evidence)


def _all_response_stages_are_accepted(evidence: _RunEvidence) -> bool:
    return (
        sum(evidence.response_stage_counts.values()) == _EXPECTED_PROVIDER_COUNT
        and evidence.response_stage_counts[ClassifierResponseStage.ACCEPTED]
        == _EXPECTED_PROVIDER_COUNT
        and all(
            count == 0
            for stage, count in evidence.response_stage_counts.items()
            if stage is not ClassifierResponseStage.ACCEPTED
        )
    )


def _acceptance_passes(evidence: _RunEvidence) -> bool:
    expected_cost = estimate_deepseek_cost_usd(evidence.usage)
    return (
        evidence.selected_count == _EXPECTED_SELECTED_COUNT
        and evidence.skip_count == _EXPECTED_SKIP_COUNT
        and evidence.deterministic_provider_free_count == _EXPECTED_DETERMINISTIC_COUNT
        and evidence.provider_case_count == _EXPECTED_PROVIDER_COUNT
        and evidence.policy_privacy_probe_count == _EXPECTED_POLICY_PRIVACY_PROBE_COUNT
        and evidence.policy_privacy_outbound_count == 0
        and evidence.outbound_attempt_count == _EXPECTED_PROVIDER_COUNT
        and evidence.provider_response_count == _EXPECTED_PROVIDER_COUNT
        and evidence.http_2xx_count == _EXPECTED_PROVIDER_COUNT
        and evidence.http_rejected_count == 0
        and evidence.transport_no_response_count == 0
        and evidence.strict_parse_count == _EXPECTED_PROVIDER_COUNT
        and evidence.server_decision_accepted_count == _EXPECTED_PROVIDER_COUNT
        and evidence.oracle_match_count == _EXPECTED_PROVIDER_COUNT
        and evidence.usage_accepted_count == _EXPECTED_PROVIDER_COUNT
        and evidence.usage_rejected_count == 0
        and _all_response_stages_are_accepted(evidence)
        and evidence.conservative_cost_usd == expected_cost
        and evidence.conservative_cost_usd <= _ACTUAL_COST_CAP_USD
        and evidence.runtime_failure_count == 0
        and evidence.invocation_count == _ACTUAL_INVOCATION_COUNT
        and evidence.retry_count == _ACTUAL_RETRY_COUNT
        and evidence.rerun_count == _ACTUAL_RERUN_COUNT
        and evidence.concurrency == DEEPSEEK_MAX_CONCURRENCY
        and evidence.max_output_tokens == DEEPSEEK_MAX_OUTPUT_TOKENS
        and evidence.retained_question_count == 0
        and evidence.retained_masked_question_count == 0
        and evidence.retained_request_body_count == 0
        and evidence.retained_response_body_count == 0
        and evidence.retained_invalid_value_count == 0
        and evidence.retained_secret_count == 0
    )


_REPORT_FIELDS = (
    "source_sha",
    "fixture_sha256",
    "coverage_sha256",
    "official_records_sha256",
    "release_manifest_sha256",
    "offline_result_sha256",
    "release_version",
    "model",
    "pricing_source_url",
    "pricing_checked_on",
    "selected_count",
    "skip_count",
    "deterministic_provider_free_count",
    "provider_case_count",
    "policy_privacy_probe_count",
    "policy_privacy_outbound_count",
    "outbound_attempt_count",
    "provider_response_count",
    "http_2xx_count",
    "http_rejected_count",
    "transport_no_response_count",
    "strict_parse_count",
    "server_decision_accepted_count",
    "oracle_match_count",
    "usage_accepted_count",
    "usage_rejected_count",
    "provider_response_stage_total",
    *(
        f"provider_stage_{stage.value.casefold()}_count"
        for stage in ClassifierResponseStage
    ),
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "conservative_all_miss_cost_usd_including_vat",
    "cost_cap_usd_including_vat",
    "runtime_failure_count",
    "invocation_count",
    "retry_count",
    "rerun_count",
    "concurrency",
    "max_output_tokens",
    "retained_question_count",
    "retained_masked_question_count",
    "retained_request_body_count",
    "retained_response_body_count",
    "retained_invalid_value_count",
    "retained_secret_count",
    "acceptance",
)


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _build_report(evidence: _RunEvidence) -> dict[str, object]:
    if type(evidence) is not _RunEvidence:
        raise _RuntimeFailed
    report: dict[str, object] = {
        "source_sha": evidence.source_sha,
        "fixture_sha256": evidence.identities.fixture_sha256,
        "coverage_sha256": evidence.identities.coverage_sha256,
        "official_records_sha256": evidence.identities.official_records_sha256,
        "release_manifest_sha256": evidence.identities.release_manifest_sha256,
        "offline_result_sha256": evidence.identities.offline_result_sha256,
        "release_version": evidence.identities.release_version,
        "model": evidence.model,
        "pricing_source_url": DEEPSEEK_PRICING_SOURCE_URL,
        "pricing_checked_on": DEEPSEEK_PRICING_CHECKED_ON,
        "selected_count": evidence.selected_count,
        "skip_count": evidence.skip_count,
        "deterministic_provider_free_count": (
            evidence.deterministic_provider_free_count
        ),
        "provider_case_count": evidence.provider_case_count,
        "policy_privacy_probe_count": evidence.policy_privacy_probe_count,
        "policy_privacy_outbound_count": evidence.policy_privacy_outbound_count,
        "outbound_attempt_count": evidence.outbound_attempt_count,
        "provider_response_count": evidence.provider_response_count,
        "http_2xx_count": evidence.http_2xx_count,
        "http_rejected_count": evidence.http_rejected_count,
        "transport_no_response_count": evidence.transport_no_response_count,
        "strict_parse_count": evidence.strict_parse_count,
        "server_decision_accepted_count": evidence.server_decision_accepted_count,
        "oracle_match_count": evidence.oracle_match_count,
        "usage_accepted_count": evidence.usage_accepted_count,
        "usage_rejected_count": evidence.usage_rejected_count,
        "provider_response_stage_total": sum(evidence.response_stage_counts.values()),
        "input_tokens": evidence.usage.input_tokens,
        "cached_input_tokens": evidence.usage.cached_input_tokens,
        "output_tokens": evidence.usage.output_tokens,
        "conservative_all_miss_cost_usd_including_vat": _decimal_text(
            evidence.conservative_cost_usd
        ),
        "cost_cap_usd_including_vat": _decimal_text(_ACTUAL_COST_CAP_USD),
        "runtime_failure_count": evidence.runtime_failure_count,
        "invocation_count": evidence.invocation_count,
        "retry_count": evidence.retry_count,
        "rerun_count": evidence.rerun_count,
        "concurrency": evidence.concurrency,
        "max_output_tokens": evidence.max_output_tokens,
        "retained_question_count": evidence.retained_question_count,
        "retained_masked_question_count": evidence.retained_masked_question_count,
        "retained_request_body_count": evidence.retained_request_body_count,
        "retained_response_body_count": evidence.retained_response_body_count,
        "retained_invalid_value_count": evidence.retained_invalid_value_count,
        "retained_secret_count": evidence.retained_secret_count,
        "acceptance": "PASS" if _acceptance_passes(evidence) else "FAIL",
    }
    for stage in ClassifierResponseStage:
        report[f"provider_stage_{stage.value.casefold()}_count"] = (
            evidence.response_stage_counts[stage]
        )
    return report


def _report_to_markdown(report: Mapping[str, object]) -> str:
    if type(report) is not dict or frozenset(report) != frozenset(_REPORT_FIELDS):
        raise _RuntimeFailed
    lines = [
        "# CHAT-HYBRID-RAG-001 DeepSeek Classifier Actual Evidence",
        "",
        "This immutable artifact contains aggregate evidence only.",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    lines.extend(f"| `{field}` | `{report[field]}` |" for field in _REPORT_FIELDS)
    lines.append("")
    return "\n".join(lines)


def _safe_console_report(report: Mapping[str, object]) -> str:
    fields = (
        "selected_count",
        "skip_count",
        "deterministic_provider_free_count",
        "provider_case_count",
        "policy_privacy_outbound_count",
        "outbound_attempt_count",
        "http_2xx_count",
        "strict_parse_count",
        "server_decision_accepted_count",
        "oracle_match_count",
        "conservative_all_miss_cost_usd_including_vat",
        "invocation_count",
        "retry_count",
        "rerun_count",
        "acceptance",
    )
    try:
        safe = {field: report[field] for field in fields}
    except (KeyError, TypeError):
        raise _RuntimeFailed from None
    return json.dumps(safe, ensure_ascii=True, separators=(",", ":"))


def _write_report_once(path: Path, report: Mapping[str, object]) -> None:
    descriptor: int | None = None
    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        payload = _report_to_markdown(report).encode("utf-8")
        offset = 0
        while offset < len(payload):
            written = os.write(descriptor, payload[offset:])
            if written <= 0:
                raise OSError
            offset += written
        os.fsync(descriptor)
    except FileExistsError:
        raise _RunAlreadyExists from None
    except OSError:
        raise _EvidenceWriteFailed from None
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass


def main(argv: Sequence[str] | None = None) -> int:
    try:
        options = _parse_args(argv)
    except Exception:
        print("DEEPSEEK_CLASSIFIER_ACTUAL_ARGUMENTS_INVALID", file=sys.stderr)
        return 2

    with _force_upstage_modes_off():
        try:
            prepared = _perform_readiness(options)
        except _RunAlreadyExists:
            print(
                "DEEPSEEK_CLASSIFIER_ACTUAL_RUN_ALREADY_RECORDED",
                file=sys.stderr,
            )
            return 2
        except Exception:
            print(
                "DEEPSEEK_CLASSIFIER_ACTUAL_READINESS_INVALID",
                file=sys.stderr,
            )
            return 2

        if options.readiness_only:
            print("DEEPSEEK_CLASSIFIER_ACTUAL_READY")
            return 0

        try:
            evidence = _new_evidence(prepared)
            _revalidate_prepared_run(prepared)
        except Exception:
            print(
                "DEEPSEEK_CLASSIFIER_ACTUAL_READINESS_INVALID",
                file=sys.stderr,
            )
            return 2

        try:
            _RunLease.acquire(options.report_path)
        except _RunAlreadyExists:
            print(
                "DEEPSEEK_CLASSIFIER_ACTUAL_RUN_ALREADY_RECORDED",
                file=sys.stderr,
            )
            return 2
        except Exception:
            print(
                "DEEPSEEK_CLASSIFIER_ACTUAL_LEASE_FAILED",
                file=sys.stderr,
            )
            return 2

        execution_failed = False
        try:
            asyncio.run(_execute_actual_with_deadline(prepared, evidence))
        except Exception:
            execution_failed = True
            evidence.runtime_failure_count = 1

        try:
            report = _build_report(evidence)
            _write_report_once(options.report_path, report)
        except Exception:
            print(
                "DEEPSEEK_CLASSIFIER_ACTUAL_EVIDENCE_WRITE_FAILED",
                file=sys.stderr,
            )
            return 3

        if execution_failed:
            print(
                "DEEPSEEK_CLASSIFIER_ACTUAL_RUNTIME_FAILED",
                file=sys.stderr,
            )
            return 3
        if report["acceptance"] != "PASS":
            print(
                "DEEPSEEK_CLASSIFIER_ACTUAL_ACCEPTANCE_FAILED",
                file=sys.stderr,
            )
            return 1
        print(_safe_console_report(report))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
