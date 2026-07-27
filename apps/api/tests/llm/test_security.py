from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from collections import Counter
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

import sejong_ai_api.llm.evaluation as evaluation_module
from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.grounding import GroundingDecision, evaluate_grounding
from sejong_ai_api.chat.retrieval import (
    GroundingEvidenceKind,
    TopicSelection,
    validate_semantic_selection,
)
from sejong_ai_api.chat.topic_catalog import TopicCatalog
from sejong_ai_api.db.models import AnswerStatus, Intent, KnowledgeRecord
from sejong_ai_api.llm.classifier_contracts import ClassifierDecision
from sejong_ai_api.llm.contracts import (
    GeneratedAnswer,
    GenerationOutcome,
    GroundedFixture,
    OutcomeCode,
    TokenUsage,
)
from sejong_ai_api.llm.evaluation import (
    EvaluationCaseResult,
    EvaluationRun,
    SyntheticEvaluationService,
)
from sejong_ai_api.llm.fixtures import SyntheticFixture, load_allowed_fixtures
from sejong_ai_api.llm.limits import AttemptBudget
from sejong_ai_api.llm.prompt import build_upstage_messages
from sejong_ai_api.llm.report import build_aggregate_report
from sejong_ai_api.llm.settings import UpstageSyntheticSettings
from sejong_ai_api.llm.upstage import UpstageProvider, create_upstage_client
from sejong_ai_api.main import create_app

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
SAMPLE_PATH = REPOSITORY_ROOT / "data" / "evaluation" / "sample_questions_20.csv"
OFFICIAL_KB_PATH = (
    REPOSITORY_ROOT / "data" / "official" / "releases" / "0.1.0-initial.2" / "kb_records.json"
)
RUNNER_PATH = REPOSITORY_ROOT / "scripts" / "run_upstage_synthetic_evaluation.py"
RAW_PHONE = "010-1234-5678"
KEY_SENTINEL = "task6-header-only-key-sentinel"
PROMPT_CONTENT_SENTINEL = "task6-prompt-content-sentinel"
PROVIDER_CONTENT_SENTINEL = "task6-provider-content-sentinel"
_BASE_LOG_RECORD_KEYS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__)


class _Repository:
    def __init__(self, records: Sequence[KnowledgeRecord]) -> None:
        self._records = tuple(records)

    async def list_active_kb(self, intent: Intent) -> tuple[KnowledgeRecord, ...]:
        return tuple(record for record in self._records if record.category is intent)


class _CaptureProvider:
    def __init__(self) -> None:
        self.fixtures: list[GroundedFixture] = []

    async def generate(self, fixture: GroundedFixture) -> GenerationOutcome:
        self.fixtures.append(fixture)
        return GenerationOutcome(
            code=OutcomeCode.SUCCESS,
            answer=_answer(),
            usage=TokenUsage(20, 0, 10),
            attempts_used=1,
            attempt_outcomes=(OutcomeCode.SUCCESS,),
        )


def _answer_json(**extra: object) -> str:
    payload: dict[str, object] = {
        "summary": "안내",
        "procedure_steps": [],
        "required_documents": [],
        "processing_time": None,
        "fee": None,
        "department": None,
    }
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _provider_response(*, content: str | None = None) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": _answer_json() if content is None else content},
                }
            ],
            "usage": {"prompt_tokens": 20, "completion_tokens": 10},
        },
    )


def _answer() -> GeneratedAnswer:
    return GeneratedAnswer(
        summary="전입신고 절차를 안내합니다.",
        procedure_steps=["정부24 또는 행정복지센터에서 신고합니다."],
        required_documents=["신분증"],
        processing_time="즉시",
        fee="없음",
        department="주민등록 담당부서",
    )


def _move_in_record() -> KnowledgeRecord:
    return KnowledgeRecord(
        public_id="KB-MOVE-TASK6",
        category=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        service_name="전입신고",
        answer_summary="이사한 날부터 14일 이내에 전입신고를 합니다.",
        procedure_steps=("정부24 또는 새 주소지 행정복지센터에서 신고합니다.",),
        required_documents=("신분증",),
        processing_time="즉시",
        fee="없음",
        department="주민등록 담당부서",
        source_title="정부24 전입신고 안내",
        source_url="https://www.gov.kr/",
        last_verified_at=date(2026, 7, 20),
        caution=None,
        question_examples=(
            "이사했는데 전입신고 어떻게 해요?",
            "전입신고에 필요한 서류가 뭐예요?",
        ),
    )


def _official_records() -> tuple[KnowledgeRecord, ...]:
    payload = json.loads(OFFICIAL_KB_PATH.read_text(encoding="utf-8"))
    return tuple(
        KnowledgeRecord(
            public_id=item["id"],
            category=Intent(item["category"]),
            service_name=item["service_name"],
            answer_summary=item["answer_summary"],
            procedure_steps=tuple(item["procedure_steps"]),
            required_documents=tuple(item["required_documents"]),
            processing_time=item["processing_time"],
            fee=item["fee"],
            department=item["department"],
            source_title=item["source_title"],
            source_url=item["source_url"],
            last_verified_at=date.fromisoformat(item["last_verified_at"]),
            caution=item["caution"],
            question_examples=tuple(item["question_examples"]),
        )
        for item in payload["records"]
    )


def _fixture() -> SyntheticFixture:
    return SyntheticFixture(
        fixture_id="T-01",
        question="이사했는데 전입신고 어떻게 해요?",
        expected_intent=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        expected_status=AnswerStatus.SUCCESS,
        contains_pii=False,
    )


def _non_provider_fixture(*, question: str) -> SyntheticFixture:
    return SyntheticFixture(
        fixture_id="T-01",
        question=question,
        expected_intent=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        expected_status=AnswerStatus.SUCCESS,
        contains_pii=False,
    )


def _log_record_representations(record: logging.LogRecord) -> tuple[str, ...]:
    extras = tuple(
        f"{key}={value!r}"
        for key, value in record.__dict__.items()
        if key not in _BASE_LOG_RECORD_KEYS
    )
    return (
        record.getMessage(),
        repr(record.msg),
        repr(record.args),
        repr(record.exc_info),
        repr(record.exc_text),
        repr(record.stack_info),
        *extras,
    )


@pytest.mark.asyncio
async def test_api_key_is_header_only_and_absent_from_outcome_report_repr_and_logs(
    grounded_fixture: GroundedFixture,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _provider_response()

    def transport_factory(*, retries: int) -> httpx.MockTransport:
        assert retries == 0
        return httpx.MockTransport(handler)

    monkeypatch.setattr(httpx, "AsyncHTTPTransport", transport_factory)
    settings = UpstageSyntheticSettings(api_key=KEY_SENTINEL)
    caplog.set_level(logging.DEBUG)
    async with create_upstage_client(settings) as client:
        outcome = await UpstageProvider(
            settings=settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(grounded_fixture)

    case = EvaluationCaseResult(
        fixture_id=grounded_fixture.fixture_id,
        repetition=1,
        outcome_code=outcome.code,
        attempts_used=outcome.attempts_used,
        attempt_outcomes=outcome.attempt_outcomes,
        usage=outcome.usage,
        latency_ms=1,
        source_id=grounded_fixture.record.public_id,
        used_template_fallback=False,
    )
    report = build_aggregate_report(
        EvaluationRun(planned_generations=1, cases=(case,), review_samples=()),
        (),
    )

    assert len(seen) == 1
    request = seen[0]
    assert request.headers.get_list("Authorization") == [f"Bearer {KEY_SENTINEL}"]
    assert KEY_SENTINEL not in str(request.url)
    assert KEY_SENTINEL.encode() not in request.content
    assert all(
        KEY_SENTINEL not in value
        for name, value in request.headers.multi_items()
        if name.casefold() != "authorization"
    )
    safe_evidence = "\n".join(
        (
            repr(settings),
            repr(outcome),
            json.dumps(report, ensure_ascii=False),
            caplog.text,
        )
    )
    assert KEY_SENTINEL not in safe_evidence
    assert all(
        KEY_SENTINEL not in representation
        for record in caplog.records
        for representation in _log_record_representations(record)
    )


@pytest.mark.asyncio
async def test_noncanonical_raw_pii_never_reaches_provider_or_logs(
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = _CaptureProvider()
    service = SyntheticEvaluationService(
        fixtures=(
            _non_provider_fixture(question=f"전입신고 어떻게 해요? 연락처 {RAW_PHONE}"),
        ),
        repository=_Repository((_move_in_record(),)),
        provider=provider,
    )
    caplog.set_level(logging.DEBUG)

    with pytest.raises(ValueError, match="^SYNTHETIC_FIXTURE_NOT_ALLOWED$") as error:
        await service.run(repetitions=1)

    assert str(error.value) == "SYNTHETIC_FIXTURE_NOT_ALLOWED"
    assert provider.fixtures == []
    assert RAW_PHONE not in caplog.text
    assert all(
        RAW_PHONE not in representation
        for record in caplog.records
        for representation in _log_record_representations(record)
    )


@pytest.mark.asyncio
async def test_provider_body_and_content_never_reach_python_logs(
    grounded_fixture: GroundedFixture,
    exact_settings: UpstageSyntheticSettings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    prompt_fixture = GroundedFixture(
        fixture_id=grounded_fixture.fixture_id,
        masked_question=f"{grounded_fixture.masked_question} {PROMPT_CONTENT_SENTINEL}",
        intent=grounded_fixture.intent,
        record=grounded_fixture.record,
    )
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _provider_response(
            content=_answer_json(
                summary=PROVIDER_CONTENT_SENTINEL,
                source_url=f"https://example.invalid/{PROVIDER_CONTENT_SENTINEL}",
            )
        )

    caplog.set_level(logging.DEBUG)
    async with httpx.AsyncClient(
        base_url=exact_settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        outcome = await UpstageProvider(
            settings=exact_settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(prompt_fixture)

    assert outcome.code is OutcomeCode.SCHEMA_INVALID
    assert len(seen) == 2
    assert all(PROMPT_CONTENT_SENTINEL.encode() in request.content for request in seen)
    forbidden_content = (PROMPT_CONTENT_SENTINEL, PROVIDER_CONTENT_SENTINEL)
    assert all(sentinel not in caplog.text for sentinel in forbidden_content)
    assert all(
        sentinel not in representation
        for record in caplog.records
        for representation in _log_record_representations(record)
        for sentinel in forbidden_content
    )


@pytest.mark.parametrize(
    "option",
    ("--is-test", "--question", "--model", "--base-url", "--attempt-cap"),
)
def test_runner_rejects_all_client_supplied_evaluator_overrides(option: str) -> None:
    environment = os.environ.copy()
    environment["LLM_PROVIDER"] = "disabled"
    environment["UPSTAGE_SYNTHETIC_EVALUATION_MODE"] = "false"
    for key in ("SEJONG_DB_TEST_URL", "SEJONG_ADMIN_DATABASE_URL", "DATABASE_URL"):
        environment.pop(key, None)

    completed = subprocess.run(
        [sys.executable, str(RUNNER_PATH), option, "untrusted-client-value"],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert completed.stdout == ""
    assert completed.stderr == "LLM_EVALUATION_ARGUMENTS_INVALID\n"
    assert "untrusted-client-value" not in completed.stderr


@pytest.mark.asyncio
async def test_t11_through_t20_have_zero_provider_calls() -> None:
    fixtures = load_allowed_fixtures(SAMPLE_PATH)
    provider = _CaptureProvider()
    service = SyntheticEvaluationService(
        fixtures=fixtures,
        repository=_Repository(_official_records()),
        provider=provider,
    )

    run = await service.run(repetitions=1)

    loaded_ids = {fixture.fixture_id for fixture in provider.fixtures}
    excluded_ids = {f"T-{number:02d}" for number in range(11, 21)}
    assert loaded_ids == {f"T-{number:02d}" for number in range(1, 11)}
    assert loaded_ids.isdisjoint(excluded_ids)
    assert len(run.cases) == 10
    assert sum(fixture.fixture_id in excluded_ids for fixture in provider.fixtures) == 0


@pytest.mark.asyncio
async def test_frozen_generation_fixtures_use_exact_typed_topics_once_without_logging(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fixtures = load_allowed_fixtures(SAMPLE_PATH)
    provider = _CaptureProvider()
    selections: list[TopicSelection | None] = []

    def capture_selection(
        question: SafeQuestion,
        intent: Intent,
        selection: TopicSelection | None,
    ) -> GroundingDecision:
        selections.append(selection)
        return evaluate_grounding(question, intent, selection)

    monkeypatch.setattr(evaluation_module, "evaluate_grounding", capture_selection)
    caplog.set_level(logging.DEBUG)
    service = SyntheticEvaluationService(
        fixtures=fixtures,
        repository=_Repository(_official_records()),
        provider=provider,
    )

    run = await service.run(repetitions=1)

    allowed_ids = tuple(f"T-{number:02d}" for number in range(1, 11))
    excluded_ids = tuple(f"T-{number:02d}" for number in range(11, 21))
    expected_sources = {
        "T-01": "KB-MOVE-01",
        "T-02": "KB-MOVE-02",
        "T-03": "KB-MOVE-03",
        "T-04": "KB-CERT-02",
        "T-05": "KB-CERT-01",
        "T-06": "KB-CERT-05",
        "T-07": "KB-WASTE-01",
        "T-08": "KB-WASTE-02",
        "T-09": "KB-TAX-02",
        "T-10": "KB-TAX-03",
    }

    call_counts = Counter(fixture.fixture_id for fixture in provider.fixtures)
    assert call_counts == Counter({fixture_id: 1 for fixture_id in allowed_ids})
    assert all(call_counts[fixture_id] == 0 for fixture_id in excluded_ids)
    assert tuple(case.fixture_id for case in run.cases) == allowed_ids
    assert tuple(case.source_id for case in run.cases) == tuple(
        expected_sources[fixture_id] for fixture_id in allowed_ids
    )
    assert all(type(selection) is TopicSelection for selection in selections)
    semantic_fixture_ids = {
        fixture_id
        for fixture_id, selection in zip(allowed_ids, selections, strict=True)
        if selection is not None
        and selection.evidence.kind
        is GroundingEvidenceKind.VALIDATED_SEMANTIC_COVERAGE
    }
    assert semantic_fixture_ids == {"T-02", "T-07", "T-08"}

    forbidden_content = tuple(fixture.question for fixture in fixtures) + (
        _answer().summary,
        *_answer().procedure_steps,
        *_answer().required_documents,
    )
    assert all(value not in caplog.text for value in forbidden_content)
    assert all(
        value not in representation
        for record in caplog.records
        for representation in _log_record_representations(record)
        for value in forbidden_content
    )


@pytest.mark.asyncio
async def test_caller_semantic_topic_input_cannot_reach_selection_or_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _CaptureProvider()
    semantic_calls = 0
    fixture_values: dict[str, object] = {
        "fixture_id": "T-99",
        "question": "전입신고에 필요한 서류가 뭐예요?",
        "expected_intent": Intent.MOVE_IN_RESIDENT_REGISTRATION,
        "expected_status": AnswerStatus.SUCCESS,
        "contains_pii": False,
        "expected_topic_id": "KB-MOVE-02",
    }

    def capture_semantic_selection(
        decision: ClassifierDecision,
        catalog: TopicCatalog,
    ) -> TopicSelection | None:
        nonlocal semantic_calls
        semantic_calls += 1
        return validate_semantic_selection(decision, catalog)

    monkeypatch.setattr(
        evaluation_module,
        "validate_semantic_selection",
        capture_semantic_selection,
    )

    with pytest.raises((TypeError, ValueError), match="expected_topic_id"):
        fixture = SyntheticFixture(**fixture_values)  # type: ignore[arg-type]
        service = SyntheticEvaluationService(
            fixtures=(fixture,),
            repository=_Repository(_official_records()),
            provider=provider,
        )
        await service.run(repetitions=1)

    assert semantic_calls == 0
    assert provider.fixtures == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("fixture_id", "question"),
    (
        ("T-99", "전입신고에 필요한 서류가 뭐예요?"),
        ("T-02", "전입신고에 필요한 서류가 뭐예요? "),
    ),
)
async def test_noncanonical_fixture_fails_value_free_before_provider(
    fixture_id: str,
    question: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = _CaptureProvider()
    fixture = SyntheticFixture(
        fixture_id=fixture_id,
        question=question,
        expected_intent=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        expected_status=AnswerStatus.SUCCESS,
        contains_pii=False,
    )
    service = SyntheticEvaluationService(
        fixtures=(fixture,),
        repository=_Repository(_official_records()),
        provider=provider,
    )
    caplog.set_level(logging.DEBUG)

    with pytest.raises(ValueError, match="^SYNTHETIC_FIXTURE_NOT_ALLOWED$") as error:
        await service.run(repetitions=1)

    assert str(error.value) == "SYNTHETIC_FIXTURE_NOT_ALLOWED"
    assert provider.fixtures == []
    assert fixture_id not in caplog.text
    assert question not in caplog.text
    assert all(
        value not in representation
        for record in caplog.records
        for representation in _log_record_representations(record)
        for value in (fixture_id, question)
    )


def test_modified_t01_projection_fails_before_provider_construction(tmp_path: Path) -> None:
    modified_path = tmp_path / "modified-sample.csv"
    original = SAMPLE_PATH.read_text(encoding="utf-8-sig")
    modified_path.write_text(
        original.replace(
            "T-01,이사했는데 전입신고 어떻게 해요?",
            "T-01,변경된 전입신고 질문",
            1,
        ),
        encoding="utf-8-sig",
    )
    provider_factory_calls = 0

    def construct_provider(_fixtures: tuple[SyntheticFixture, ...]) -> _CaptureProvider:
        nonlocal provider_factory_calls
        provider_factory_calls += 1
        return _CaptureProvider()

    with pytest.raises(ValueError, match="SYNTHETIC_FIXTURE_SET_INVALID"):
        construct_provider(load_allowed_fixtures(modified_path))

    assert provider_factory_calls == 0


def test_prompt_and_model_schema_exclude_server_owned_source_metadata(
    grounded_fixture: GroundedFixture,
) -> None:
    messages = build_upstage_messages(grounded_fixture)
    serialized = json.dumps(messages, ensure_ascii=False)
    record = grounded_fixture.record

    for server_owned_value in (
        record.public_id,
        record.source_title,
        record.source_url,
        record.last_verified_at.isoformat(),
    ):
        assert server_owned_value not in serialized
    assert set(GeneratedAnswer.model_fields) == {
        "summary",
        "procedure_steps",
        "required_documents",
        "processing_time",
        "fee",
        "department",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "forbidden_extra",
    (
        {"source": {"url": "https://example.invalid/"}},
        {"status": "SUCCESS"},
        {"intent": "MOVE_IN_RESIDENT_REGISTRATION"},
    ),
)
async def test_provider_source_status_or_intent_extra_triggers_template_fallback(
    exact_settings: UpstageSyntheticSettings,
    forbidden_extra: dict[str, object],
) -> None:
    transport_calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal transport_calls
        transport_calls += 1
        return _provider_response(content=_answer_json(**forbidden_extra))

    async with httpx.AsyncClient(
        base_url=exact_settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        provider = UpstageProvider(
            settings=exact_settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        )
        service = SyntheticEvaluationService(
            fixtures=(_fixture(),),
            repository=_Repository((_move_in_record(),)),
            provider=provider,
            monotonic_ns=iter((0, 1_000_000)).__next__,
        )
        run = await service.run(repetitions=1)

    assert transport_calls == 2
    assert run.review_samples == ()
    assert len(run.cases) == 1
    assert run.cases[0].outcome_code is OutcomeCode.SCHEMA_INVALID
    assert run.cases[0].used_template_fallback is True
    assert run.cases[0].source_id == "KB-MOVE-TASK6"


@pytest.mark.asyncio
async def test_thirtieth_attempt_executes_and_thirty_first_never_reaches_transport(
    grounded_fixture: GroundedFixture,
    exact_settings: UpstageSyntheticSettings,
) -> None:
    transport_calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal transport_calls
        transport_calls += 1
        return _provider_response()

    budget = AttemptBudget(cap=30, concurrency=1)
    outcomes: list[GenerationOutcome] = []
    async with httpx.AsyncClient(
        base_url=exact_settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        provider = UpstageProvider(settings=exact_settings, client=client, budget=budget)
        for _ in range(31):
            outcomes.append(await provider.generate(grounded_fixture))

    assert transport_calls == 30
    assert budget.attempts_used == 30
    assert outcomes[29].code is OutcomeCode.SUCCESS
    assert outcomes[30].code is OutcomeCode.ATTEMPT_CAP
    assert outcomes[30].attempts_used == 0
    assert outcomes[30].attempt_outcomes == ()


def test_default_health_readiness_and_chat_never_construct_provider_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async_client_constructions = 0

    class _ForbiddenAsyncClient:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            nonlocal async_client_constructions
            async_client_constructions += 1
            raise AssertionError("PUBLIC_APP_PROVIDER_CLIENT_FORBIDDEN")

    monkeypatch.setattr(httpx, "AsyncClient", _ForbiddenAsyncClient)
    with TestClient(create_app()) as client:
        health = client.get("/health")
        ready = client.get("/ready")
        invalid_override_chat = client.post(
            "/api/v1/chat",
            json={
                "question": "전입신고는 어떻게 하나요?",
                "is_test": True,
                "model": "untrusted",
                "base_url": "https://example.invalid/",
                "attempt_cap": 999,
            },
        )
        valid_default_chat = client.post(
            "/api/v1/chat",
            json={"question": "전입신고는 어떻게 하나요?"},
        )

    assert health.status_code == 200
    assert ready.status_code == 503
    assert invalid_override_chat.status_code == 422
    assert valid_default_chat.status_code == 503
    assert async_client_constructions == 0
