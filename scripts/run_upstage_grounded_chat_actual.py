#!/usr/bin/env python3
"""Run aggregate-only local actual evidence through ``/api/v1/chat``."""

from __future__ import annotations

import asyncio
import json
import sys
import warnings
from collections.abc import Mapping, Sequence
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import fields, is_dataclass, replace
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any, cast

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_API_SOURCE = _REPOSITORY_ROOT / "apps" / "api" / "src"
_FIXTURE_PATH = _REPOSITORY_ROOT / "data" / "evaluation" / "sample_questions_20.csv"
_EXPECTED_CASES = 10

if str(_API_SOURCE) not in sys.path:
    sys.path.insert(0, str(_API_SOURCE))

warnings.filterwarnings(
    "ignore",
    message=r"Using `httpx` with `starlette\.testclient` is deprecated.*",
)
from fastapi.testclient import TestClient  # noqa: E402
from sejong_ai_api.db.models import (  # noqa: E402
    AnswerStatus,
    Intent,
    InteractionWrite,
    InteractionWriteResult,
    KnowledgeRecord,
)
from sejong_ai_api.llm.chat_contracts import (  # noqa: E402
    GroundedAnswerGenerator,
    GroundedChatOutcomeCode,
    GroundedChatRequest,
    GroundedChatResult,
)
from sejong_ai_api.llm.contracts import TokenUsage  # noqa: E402
from sejong_ai_api.llm.cost import RUN_COST_CAP_USD, estimate_cost_usd  # noqa: E402
from sejong_ai_api.llm.fixtures import SyntheticFixture, load_allowed_fixtures  # noqa: E402
from sejong_ai_api.llm.limits import AttemptBudget  # noqa: E402
from sejong_ai_api.llm.settings import (  # noqa: E402
    UpstageChatSettings,
    load_upstage_chat_settings,
)
from sejong_ai_api.llm.upstage_chat import (  # noqa: E402
    GroundedChatRuntime,
    UpstageChatGenerator,
    create_upstage_chat_client,
)

_REPORT_FIELDS = (
    "cases_total",
    "generated_count",
    "template_count",
    "source_present_count",
    "official_fact_mismatch_count",
    "pii_or_secret_persistence_count",
    "outbound_attempt_count",
    "input_token_total",
    "output_token_total",
    "estimated_cost_usd",
)


class _ConfigurationInvalid(RuntimeError):
    """The exact local DB/provider profile is unavailable."""


class _RuntimeFailed(RuntimeError):
    """The local actual run could not prove its bounded invariants."""


class _AcceptanceFailed(RuntimeError):
    """The run completed but did not satisfy the approved aggregate gate."""

    def __init__(self, report: dict[str, object]) -> None:
        super().__init__("GROUNDED_CHAT_ACTUAL_ACCEPTANCE_FAILED")
        self.report = report


class _DiscardOutput:
    """Drop dependency output without retaining text in memory."""

    encoding = "utf-8"

    def write(self, value: str) -> int:
        return len(value)

    def flush(self) -> None:
        return None

    def isatty(self) -> bool:
        return False


class _EvidenceGenerator:
    """Count content-free usage while allowing one non-network timeout probe."""

    def __init__(
        self,
        inner: GroundedAnswerGenerator,
        *,
        attempt_counter: Any | None = None,
    ) -> None:
        self._inner = inner
        self._attempt_counter = attempt_counter
        self._delegated_count = 0
        self._usage_reported_count = 0
        self._usage = TokenUsage(0, 0, 0)
        self._force_timeout = False
        self._forced_timeout_consumed_count = 0

    @property
    def outbound_attempt_count(self) -> int:
        if self._attempt_counter is None:
            return self._delegated_count
        value = self._attempt_counter()
        if type(value) is not int or value < 0:
            raise _RuntimeFailed
        return value

    @property
    def usage(self) -> TokenUsage:
        return self._usage

    @property
    def usage_reported_count(self) -> int:
        return self._usage_reported_count

    @property
    def forced_timeout_consumed_count(self) -> int:
        return self._forced_timeout_consumed_count

    def force_timeout_once(self) -> None:
        if self._force_timeout:
            raise _RuntimeFailed
        self._force_timeout = True

    async def generate(self, request: GroundedChatRequest) -> GroundedChatResult:
        if self._force_timeout:
            self._force_timeout = False
            self._forced_timeout_consumed_count += 1
            return GroundedChatResult(code=GroundedChatOutcomeCode.TIMEOUT)
        result = await self._inner.generate(request)
        if type(result) is not GroundedChatResult:
            raise _RuntimeFailed
        self._delegated_count += 1
        if result.usage.input_tokens > 0:
            self._usage_reported_count += 1
        self._usage = TokenUsage(
            input_tokens=self._usage.input_tokens + result.usage.input_tokens,
            cached_input_tokens=self._usage.cached_input_tokens
            + result.usage.cached_input_tokens,
            output_tokens=self._usage.output_tokens + result.usage.output_tokens,
        )
        return result


def _require_complete_usage(generator: _EvidenceGenerator) -> None:
    if (
        generator.outbound_attempt_count != _EXPECTED_CASES
        or generator.usage_reported_count != generator.outbound_attempt_count
    ):
        raise _RuntimeFailed


def _forced_timeout_probe_passes(
    payload: object,
    *,
    generator: _EvidenceGenerator,
    outbound_before_timeout: int,
) -> bool:
    return (
        type(payload) is dict
        and payload.get("answer_status") == "SUCCESS"
        and payload.get("answer_mode") == "TEMPLATE"
        and generator.outbound_attempt_count == outbound_before_timeout
        and generator.forced_timeout_consumed_count == 1
    )


class _CapturingRepository:
    """Delegate to the actual DB while retaining only official rows and boolean evidence."""

    def __init__(self, delegate: Any, forbidden_values: tuple[str, ...]) -> None:
        self._delegate = delegate
        self._forbidden_values = forbidden_values
        self.active_by_intent: dict[Intent, tuple[KnowledgeRecord, ...]] = {}
        self.persistence_violation_count = 0
        self.successful_interaction_writes = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    async def list_active_kb(self, intent: Intent) -> tuple[KnowledgeRecord, ...]:
        values = await self._delegate.list_active_kb(intent)
        records = tuple(values)
        if any(type(record) is not KnowledgeRecord for record in records):
            raise _RuntimeFailed
        self.active_by_intent[intent] = records
        return records

    async def record_interaction(
        self, event: InteractionWrite
    ) -> InteractionWriteResult:
        evaluation_event = replace(event, is_test=True)
        if (
            type(evaluation_event) is not InteractionWrite
            or evaluation_event.answer_status is not AnswerStatus.SUCCESS
            or evaluation_event.is_test is not True
            or evaluation_event.masked_question is not None
            or _contains_forbidden(evaluation_event, self._forbidden_values)
        ):
            self.persistence_violation_count += 1
            raise _RuntimeFailed
        result = await self._delegate.record_interaction(evaluation_event)
        if type(result) is not InteractionWriteResult:
            raise _RuntimeFailed
        self.successful_interaction_writes += 1
        return result


class _ActualState:
    repository: _CapturingRepository | None = None
    generator: _EvidenceGenerator | None = None


def _contains_forbidden(value: object, forbidden_values: tuple[str, ...]) -> bool:
    if type(value) is str:
        return any(marker and marker in value for marker in forbidden_values)
    if isinstance(value, Enum):
        return _contains_forbidden(value.value, forbidden_values)
    if is_dataclass(value) and not isinstance(value, type):
        return any(
            _contains_forbidden(getattr(value, field.name), forbidden_values)
            for field in fields(value)
        )
    if type(value) in (tuple, list, set, frozenset):
        return any(
            _contains_forbidden(item, forbidden_values) for item in cast(Any, value)
        )
    if type(value) is dict:
        return any(
            _contains_forbidden(key, forbidden_values)
            or _contains_forbidden(item, forbidden_values)
            for key, item in cast(Any, value).items()
        )
    return False


def _official_response_matches(
    response: Mapping[str, object],
    active_records: tuple[KnowledgeRecord, ...],
) -> bool:
    if (
        type(response) is not dict
        or response.get("answer_status") != "SUCCESS"
        or response.get("answer_mode") not in {"GENERATED", "TEMPLATE"}
    ):
        return False
    sources = response.get("sources")
    if type(sources) is not list or len(sources) != 1 or type(sources[0]) is not dict:
        return False
    source = sources[0]
    source_id = source.get("source_id")
    matching = tuple(
        record for record in active_records if record.public_id == source_id
    )
    if len(matching) != 1:
        return False
    record = matching[0]
    expected_used_fields = ["answer_summary"]
    if record.procedure_steps:
        expected_used_fields.append("procedure_steps")
    if record.required_documents:
        expected_used_fields.append("required_documents")
    if record.processing_time is not None:
        expected_used_fields.append("processing_time")
    if record.fee is not None:
        expected_used_fields.append("fee")
    expected_used_fields.append("department")
    return (
        response.get("intent") == record.category.value
        and response.get("procedure_steps") == list(record.procedure_steps)
        and response.get("required_documents") == list(record.required_documents)
        and response.get("processing_time") == record.processing_time
        and response.get("fee") == record.fee
        and response.get("department") == record.department
        and source.get("title") == record.source_title
        and source.get("url") == record.source_url
        and source.get("last_verified_at") == record.last_verified_at.isoformat()
        and source.get("used_fields") == expected_used_fields
    )


def _build_report(
    *,
    cases_total: int,
    generated_count: int,
    template_count: int,
    source_present_count: int,
    official_fact_mismatch_count: int,
    pii_or_secret_persistence_count: int,
    outbound_attempt_count: int,
    usage: TokenUsage,
) -> dict[str, object]:
    report: dict[str, object] = {
        "cases_total": cases_total,
        "generated_count": generated_count,
        "template_count": template_count,
        "source_present_count": source_present_count,
        "official_fact_mismatch_count": official_fact_mismatch_count,
        "pii_or_secret_persistence_count": pii_or_secret_persistence_count,
        "outbound_attempt_count": outbound_attempt_count,
        "input_token_total": usage.input_tokens,
        "output_token_total": usage.output_tokens,
        "estimated_cost_usd": format(estimate_cost_usd(usage).normalize(), "f"),
    }
    if tuple(report) != _REPORT_FIELDS:
        raise _RuntimeFailed
    return report


def _acceptance_passes(
    report: Mapping[str, object],
    *,
    forced_timeout_template: bool,
) -> bool:
    try:
        estimated_cost = Decimal(cast(str, report["estimated_cost_usd"]))
    except (KeyError, ArithmeticError, ValueError):
        return False
    values = tuple(report.get(field) for field in _REPORT_FIELDS[:-1])
    if any(type(value) is not int or value < 0 for value in values):
        return False
    return (
        report.get("cases_total") == _EXPECTED_CASES
        and cast(int, report.get("generated_count")) >= 1
        and cast(int, report.get("generated_count"))
        + cast(int, report.get("template_count"))
        == _EXPECTED_CASES
        and report.get("source_present_count") == _EXPECTED_CASES
        and report.get("official_fact_mismatch_count") == 0
        and report.get("pii_or_secret_persistence_count") == 0
        and report.get("outbound_attempt_count") == _EXPECTED_CASES
        and estimated_cost <= RUN_COST_CAP_USD
        and forced_timeout_template
    )


def _load_required_fixtures() -> tuple[SyntheticFixture, ...]:
    try:
        fixtures = load_allowed_fixtures(_FIXTURE_PATH)
    except Exception:
        raise _ConfigurationInvalid from None
    if len(fixtures) != _EXPECTED_CASES or any(
        fixture.expected_status is not AnswerStatus.SUCCESS or fixture.contains_pii
        for fixture in fixtures
    ):
        raise _ConfigurationInvalid
    return fixtures


def _build_app(
    *,
    settings: UpstageChatSettings,
    fixtures: tuple[SyntheticFixture, ...],
    local_forbidden_values: tuple[str, ...],
    state: _ActualState,
) -> Any:
    from sejong_ai_api.db.repository import PsycopgSejongRepository
    from sejong_ai_api.local import create_local_app

    forbidden_values = (
        settings.api_key,
        *local_forbidden_values,
        *(fixture.question for fixture in fixtures),
    )

    def repository_factory(pool: object) -> _CapturingRepository:
        repository = _CapturingRepository(
            PsycopgSejongRepository(cast(Any, pool)), forbidden_values
        )
        state.repository = repository
        return repository

    def runtime_factory(runtime_settings: UpstageChatSettings) -> GroundedChatRuntime:
        client = create_upstage_chat_client(runtime_settings)
        budget = AttemptBudget(
            cap=runtime_settings.run_attempt_cap,
            concurrency=runtime_settings.max_concurrency,
        )
        inner = UpstageChatGenerator(
            settings=runtime_settings,
            client=client,
            budget=budget,
        )
        generator = _EvidenceGenerator(
            inner,
            attempt_counter=lambda: budget.attempts_used,
        )
        state.generator = generator
        return GroundedChatRuntime(generator=generator, client=client)

    return create_local_app(
        repository_factory=repository_factory,
        grounded_chat_runtime_factory=runtime_factory,
        purge_interval_seconds=3600.0,
    )


def _execute_actual() -> dict[str, object]:
    from sejong_ai_api.local import load_local_settings

    local_settings = load_local_settings()
    chat_settings = load_upstage_chat_settings()
    if local_settings is None or chat_settings is None:
        raise _ConfigurationInvalid
    fixtures = _load_required_fixtures()
    state = _ActualState()
    application = _build_app(
        settings=chat_settings,
        fixtures=fixtures,
        local_forbidden_values=(
            local_settings.database_url,
            local_settings.context_token_secret.decode("utf-8"),
        ),
        state=state,
    )
    if state.repository is None or state.generator is None:
        raise _ConfigurationInvalid

    generated_count = 0
    template_count = 0
    source_present_count = 0
    mismatch_count = 0
    forced_timeout_template = False

    try:
        with TestClient(application, base_url="http://127.0.0.1") as client:
            if client.get("/ready").status_code != 200:
                raise _RuntimeFailed
            for fixture in fixtures:
                response = client.post(
                    "/api/v1/chat",
                    json={
                        "question": fixture.question,
                        "context_token": None,
                        "selected_region": None,
                        "simple_language": False,
                    },
                )
                if response.status_code != 200:
                    raise _RuntimeFailed
                payload = response.json()
                if type(payload) is not dict:
                    raise _RuntimeFailed
                answer_mode = payload.get("answer_mode")
                generated_count += int(answer_mode == "GENERATED")
                template_count += int(answer_mode == "TEMPLATE")
                sources = payload.get("sources")
                source_present_count += int(type(sources) is list and len(sources) > 0)
                records = state.repository.active_by_intent.get(
                    fixture.expected_intent, ()
                )
                mismatch_count += int(not _official_response_matches(payload, records))

            outbound_before_timeout = state.generator.outbound_attempt_count
            state.generator.force_timeout_once()
            forced = client.post(
                "/api/v1/chat",
                json={
                    "question": fixtures[0].question,
                    "context_token": None,
                    "selected_region": None,
                    "simple_language": False,
                },
            )
            if forced.status_code != 200:
                raise _RuntimeFailed
            forced_payload = forced.json()
            forced_timeout_template = _forced_timeout_probe_passes(
                forced_payload,
                generator=state.generator,
                outbound_before_timeout=outbound_before_timeout,
            )
    except _RuntimeFailed:
        raise
    except Exception:
        raise _RuntimeFailed from None

    if state.repository.successful_interaction_writes != _EXPECTED_CASES + 1:
        raise _RuntimeFailed
    _require_complete_usage(state.generator)
    report = _build_report(
        cases_total=_EXPECTED_CASES,
        generated_count=generated_count,
        template_count=template_count,
        source_present_count=source_present_count,
        official_fact_mismatch_count=mismatch_count,
        pii_or_secret_persistence_count=state.repository.persistence_violation_count,
        outbound_attempt_count=state.generator.outbound_attempt_count,
        usage=state.generator.usage,
    )
    if not _acceptance_passes(report, forced_timeout_template=forced_timeout_template):
        raise _AcceptanceFailed(report)
    return report


def _reject_arguments(argv: Sequence[str] | None) -> None:
    selected = sys.argv[1:] if argv is None else argv
    if selected:
        raise _ConfigurationInvalid


def _configure_event_loop_policy(platform: str) -> None:
    if platform != "win32":
        return
    policy_factory = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if not callable(policy_factory):
        raise _ConfigurationInvalid
    asyncio.set_event_loop_policy(policy_factory())


def main(argv: Sequence[str] | None = None) -> int:
    try:
        _reject_arguments(argv)
        _configure_event_loop_policy(sys.platform)
        with redirect_stdout(_DiscardOutput()), redirect_stderr(_DiscardOutput()):
            report = _execute_actual()
    except _AcceptanceFailed as exc:
        print(json.dumps(exc.report, ensure_ascii=True, separators=(",", ":")))
        return 1
    except _ConfigurationInvalid:
        print("GROUNDED_CHAT_ACTUAL_CONFIGURATION_INVALID", file=sys.stderr)
        return 2
    except Exception:
        print("GROUNDED_CHAT_ACTUAL_RUNTIME_FAILED", file=sys.stderr)
        return 3

    print(json.dumps(report, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
