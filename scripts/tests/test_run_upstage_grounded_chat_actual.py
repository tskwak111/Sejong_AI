from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import UUID

import pytest

_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_API_SOURCE = _REPOSITORY_ROOT / "apps" / "api" / "src"
if str(_API_SOURCE) not in sys.path:
    sys.path.insert(0, str(_API_SOURCE))

from sejong_ai_api.db.models import (  # noqa: E402
    AnswerStatus,
    Intent,
    InteractionWrite,
    InteractionWriteResult,
    KnowledgeRecord,
)
from sejong_ai_api.llm.chat_contracts import (  # noqa: E402
    GroundedChatOutcomeCode,
    GroundedChatRequest,
    GroundedChatResult,
)
from sejong_ai_api.llm.contracts import TokenUsage  # noqa: E402

_RUNNER_MODULE_NAME = "_sejong_grounded_chat_actual_runner_test"
_RUNNER_PATH = _REPOSITORY_ROOT / "scripts" / "run_upstage_grounded_chat_actual.py"


def _runner() -> ModuleType:
    cached = sys.modules.get(_RUNNER_MODULE_NAME)
    if cached is not None:
        return cached
    if not _RUNNER_PATH.is_file():
        pytest.fail("the grounded chat actual runner is missing")
    spec = importlib.util.spec_from_file_location(_RUNNER_MODULE_NAME, _RUNNER_PATH)
    if spec is None or spec.loader is None:
        pytest.fail("the grounded chat actual runner cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_RUNNER_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


@dataclass
class _FakeGenerator:
    calls: int = 0

    async def generate(self, _request: GroundedChatRequest) -> GroundedChatResult:
        self.calls += 1
        return GroundedChatResult(
            code=GroundedChatOutcomeCode.TIMEOUT,
            usage=TokenUsage(20, 0, 10),
        )


@dataclass
class _ZeroUsageGenerator:
    calls: int = 0

    async def generate(self, _request: GroundedChatRequest) -> GroundedChatResult:
        self.calls += 1
        return GroundedChatResult(code=GroundedChatOutcomeCode.TRANSPORT)


@dataclass
class _FakeRepository:
    recorded: InteractionWrite | None = None

    async def record_interaction(
        self, event: InteractionWrite
    ) -> InteractionWriteResult:
        self.recorded = event
        return InteractionWriteResult(
            interaction_id=UUID("00000000-0000-4000-8000-000000000001"),
            failed_question_id=None,
        )


def _record() -> KnowledgeRecord:
    return KnowledgeRecord(
        public_id="KB-ACTUAL-01",
        category=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        service_name="전입신고",
        answer_summary="승인 요약",
        procedure_steps=("1단계",),
        required_documents=("신분증",),
        processing_time="즉시",
        fee="무료",
        department="주민등록 담당",
        source_title="공식 출처",
        source_url="https://example.go.kr/official",
        last_verified_at=date(2026, 7, 20),
        caution=None,
        question_examples=("전입신고 방법",),
    )


def _response(
    record: KnowledgeRecord, *, answer_mode: str = "GENERATED"
) -> dict[str, Any]:
    return {
        "answer_status": "SUCCESS",
        "answer_mode": answer_mode,
        "intent": record.category.value,
        "procedure_steps": list(record.procedure_steps),
        "required_documents": list(record.required_documents),
        "processing_time": record.processing_time,
        "fee": record.fee,
        "department": record.department,
        "sources": [
            {
                "source_id": record.public_id,
                "title": record.source_title,
                "url": record.source_url,
                "last_verified_at": record.last_verified_at.isoformat(),
                "used_fields": [
                    "answer_summary",
                    "procedure_steps",
                    "required_documents",
                    "processing_time",
                    "fee",
                    "department",
                ],
            }
        ],
    }


def test_evidence_generator_counts_real_usage_and_forces_timeout_without_outbound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    monkeypatch.setattr(runner, "_EXPECTED_CASES", 1)
    inner = _FakeGenerator()
    generator = runner._EvidenceGenerator(inner)
    request = object()

    first = asyncio.run(generator.generate(request))
    generator.force_timeout_once()
    template_payload = {"answer_status": "SUCCESS", "answer_mode": "TEMPLATE"}
    assert not runner._forced_timeout_probe_passes(
        template_payload,
        generator=generator,
        outbound_before_timeout=1,
    )
    forced = asyncio.run(generator.generate(request))

    assert first.code is GroundedChatOutcomeCode.TIMEOUT
    assert forced == GroundedChatResult(code=GroundedChatOutcomeCode.TIMEOUT)
    assert inner.calls == 1
    assert generator.outbound_attempt_count == 1
    assert generator.usage_reported_count == 1
    assert generator.forced_timeout_consumed_count == 1
    assert generator.usage == TokenUsage(20, 0, 10)
    runner._require_complete_usage(generator)
    assert runner._forced_timeout_probe_passes(
        template_payload,
        generator=generator,
        outbound_before_timeout=1,
    )


def test_incomplete_provider_usage_cannot_satisfy_actual_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    monkeypatch.setattr(runner, "_EXPECTED_CASES", 1)
    generator = runner._EvidenceGenerator(_ZeroUsageGenerator())
    request = object()

    asyncio.run(generator.generate(request))

    assert generator.outbound_attempt_count == 1
    assert generator.usage_reported_count == 0
    with pytest.raises(runner._RuntimeFailed):
        runner._require_complete_usage(generator)


def test_capturing_repository_labels_actual_fixtures_as_evaluation() -> None:
    runner = _runner()
    delegate = _FakeRepository()
    repository = runner._CapturingRepository(delegate, ("forbidden",))
    event = InteractionWrite(
        request_id=UUID("00000000-0000-4000-8000-000000000002"),
        intent=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        answer_status=AnswerStatus.SUCCESS,
        fallback_reason=None,
        used_source_ids=("KB-ACTUAL-01",),
        response_time_ms=1,
        selected_region=None,
        routed_office_public_id=None,
        is_test=False,
        masked_question=None,
    )

    result = asyncio.run(repository.record_interaction(event))

    assert result.interaction_id == UUID("00000000-0000-4000-8000-000000000001")
    assert delegate.recorded is not None
    assert delegate.recorded.is_test is True
    assert repository.successful_interaction_writes == 1
    assert repository.persistence_violation_count == 0


def test_capturing_repository_rejects_forbidden_value_before_delegate_write() -> None:
    runner = _runner()
    delegate = _FakeRepository()
    repository = runner._CapturingRepository(delegate, ("forbidden",))
    event = InteractionWrite(
        request_id=UUID("00000000-0000-4000-8000-000000000003"),
        intent=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        answer_status=AnswerStatus.SUCCESS,
        fallback_reason=None,
        used_source_ids=("forbidden",),
        response_time_ms=1,
        selected_region=None,
        routed_office_public_id=None,
        is_test=False,
        masked_question=None,
    )

    with pytest.raises(runner._RuntimeFailed):
        asyncio.run(repository.record_interaction(event))

    assert delegate.recorded is None
    assert repository.successful_interaction_writes == 0
    assert repository.persistence_violation_count == 1


def test_official_response_match_checks_db_owned_fields_and_source() -> None:
    runner = _runner()
    record = _record()

    assert runner._official_response_matches(_response(record), (record,))
    changed = _response(record)
    changed["fee"] = "provider invented fee"
    assert not runner._official_response_matches(changed, (record,))


def test_report_contains_only_approved_aggregate_fields_and_exact_cost() -> None:
    runner = _runner()

    report = runner._build_report(
        cases_total=10,
        generated_count=7,
        template_count=3,
        source_present_count=10,
        official_fact_mismatch_count=0,
        pii_or_secret_persistence_count=0,
        outbound_attempt_count=10,
        usage=TokenUsage(1000, 0, 500),
    )

    assert tuple(report) == (
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
    assert report["estimated_cost_usd"] == "0.000495"
    assert runner._acceptance_passes(report, forced_timeout_template=True)
    assert not runner._acceptance_passes(report, forced_timeout_template=False)


def test_main_outputs_one_aggregate_json_without_private_content(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    report = runner._build_report(
        cases_total=10,
        generated_count=10,
        template_count=0,
        source_present_count=10,
        official_fact_mismatch_count=0,
        pii_or_secret_persistence_count=0,
        outbound_attempt_count=10,
        usage=TokenUsage(10, 0, 10),
    )
    monkeypatch.setattr(runner, "_execute_actual", lambda: report)

    assert runner.main([]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    assert json.loads(output.out) == report
    assert "question" not in output.out.casefold()
    assert "answer" not in output.out.casefold()
    assert "provider" not in output.out.casefold()


def test_main_installs_windows_selector_policy_before_actual_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = _runner()
    events: list[str] = []
    report = runner._build_report(
        cases_total=10,
        generated_count=10,
        template_count=0,
        source_present_count=10,
        official_fact_mismatch_count=0,
        pii_or_secret_persistence_count=0,
        outbound_attempt_count=10,
        usage=TokenUsage(10, 0, 10),
    )
    monkeypatch.setattr(
        runner,
        "_configure_event_loop_policy",
        lambda platform: events.append(f"policy:{platform}"),
    )
    monkeypatch.setattr(
        runner,
        "_execute_actual",
        lambda: events.append("execute") or report,
    )
    monkeypatch.setattr(runner.sys, "platform", "win32")

    assert runner.main([]) == 0
    assert events == ["policy:win32", "execute"]


def test_main_discards_dependency_output_before_printing_aggregate(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    report = runner._build_report(
        cases_total=10,
        generated_count=10,
        template_count=0,
        source_present_count=10,
        official_fact_mismatch_count=0,
        pii_or_secret_persistence_count=0,
        outbound_attempt_count=10,
        usage=TokenUsage(10, 0, 10),
    )

    def noisy_execute() -> dict[str, object]:
        print("PRIVATE QUESTION ANSWER PROVIDER BODY")
        print("PRIVATE SECRET ERROR", file=sys.stderr)
        return report

    monkeypatch.setattr(runner, "_execute_actual", noisy_execute)

    assert runner.main([]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    assert json.loads(output.out) == report
    assert "PRIVATE" not in output.out


def test_main_failure_is_value_free(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()

    def fail() -> dict[str, object]:
        raise runner._ConfigurationInvalid("SECRET QUESTION PROVIDER BODY")

    monkeypatch.setattr(runner, "_execute_actual", fail)

    assert runner.main([]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err.strip() == "GROUNDED_CHAT_ACTUAL_CONFIGURATION_INVALID"
