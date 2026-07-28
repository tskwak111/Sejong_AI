from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from decimal import Decimal

import httpx
import pytest

import sejong_ai_api.llm.classifier_prompt as classifier_prompt_module
from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.topic_catalog import RuntimeTopic, TopicCatalog, TopicCoverage
from sejong_ai_api.db.models import Intent, KnowledgeRecord
from sejong_ai_api.llm.classifier_contracts import (
    ClassifierDecision,
    ClassifierRoute,
)
from sejong_ai_api.llm.classifier_diagnostics import ClassifierResponseStage
from sejong_ai_api.llm.classifier_prompt import build_classifier_messages
from sejong_ai_api.llm.contracts import TokenUsage
from sejong_ai_api.llm.cost import estimate_cost_usd
from sejong_ai_api.llm.limits import ProviderAttemptLedger
from sejong_ai_api.llm.settings import UpstageClassifierSettings
from sejong_ai_api.llm.upstage_classifier import QuestionClassifier
from sejong_ai_api.privacy.redaction import redact_question

Handler = Callable[[httpx.Request], httpx.Response]
SECRET = "classifier-test-key-not-a-real-secret"
CLASSIFIER_WORST_CASE_USD = estimate_cost_usd(TokenUsage(4096, 0, 128))
GENERATOR_WORST_CASE_USD = estimate_cost_usd(TokenUsage(4096, 0, 1024))


def _question(text: str = "청년 월세 지원 어떻게 해요?") -> SafeQuestion:
    return SafeQuestion(redact_question(text))


def _forged_oversized_safe_question() -> SafeQuestion:
    question = object.__new__(SafeQuestion)
    object.__setattr__(question, "_text", "가" * 1025)
    return question


def _runtime_topic(
    index: int = 1,
    *,
    coverage_label: str = "일반 가구류 배출 절차",
) -> RuntimeTopic:
    topic_id = f"KB-WASTE-{index:02d}"
    intent = Intent.BULKY_WASTE
    return RuntimeTopic(
        record=KnowledgeRecord(
            public_id=topic_id,
            category=intent,
            service_name="대형폐기물 배출신청 절차",
            answer_summary="FACT-SENTINEL",
            procedure_steps=("PROCEDURE-SENTINEL",),
            required_documents=("DOCUMENT-SENTINEL",),
            processing_time="PROCESSING-SENTINEL",
            fee="FEE-SENTINEL",
            department="OFFICE-SENTINEL",
            source_title="SOURCE-SENTINEL",
            source_url="https://example.invalid/source-sentinel",
            last_verified_at=date(2026, 7, 27),
            caution="CAUTION-SENTINEL",
            question_examples=(
                "대형폐기물은 어떻게 신청하나요?",
                "큰 가구는 어떻게 버려요?",
                "provider에 보내면 안 되는 세 번째 예시",
            ),
        ),
        coverage=TopicCoverage(
            topic_id=topic_id,
            intent=intent,
            coverage_id=(
                "GENERAL_BULKY_DISPOSAL" if index == 1 else f"GENERAL_BULKY_DISPOSAL_{index:02d}"
            ),
            coverage_label=coverage_label,
        ),
    )


def _catalog(
    size: int = 1,
    *,
    coverage_label: str = "일반 가구류 배출 절차",
) -> TopicCatalog:
    return TopicCatalog(
        tuple(_runtime_topic(index, coverage_label=coverage_label) for index in range(1, size + 1))
    )


def _provider_response(
    content: str = (
        '{"route":"CIVIC_SCOPE_GAP","intent":"NONE","topic_id":"NONE",'
        '"coverage_id":"NONE","pending_slot":"NONE"}'
    ),
    *,
    finish_reason: str = "stop",
    usage: object = None,
    include_usage: bool = True,
) -> httpx.Response:
    envelope: dict[str, object] = {
        "choices": [
            {
                "finish_reason": finish_reason,
                "message": {"content": content},
            }
        ],
    }
    if include_usage:
        envelope["usage"] = (
            {"prompt_tokens": 20, "completion_tokens": 10} if usage is None else usage
        )
    return httpx.Response(
        200,
        json=envelope,
    )


def _provider_envelope_response(envelope: object) -> httpx.Response:
    return httpx.Response(200, json=envelope)


def _ledger(
    *,
    classifier_cap: int = 20,
    cost_cap_usd: Decimal = Decimal("0.05"),
) -> ProviderAttemptLedger:
    return ProviderAttemptLedger(
        classifier_cap=classifier_cap,
        generator_cap=30,
        combined_cap=min(40, classifier_cap + 30),
        cost_cap_usd=cost_cap_usd,
        classifier_worst_case_usd=CLASSIFIER_WORST_CASE_USD,
        generator_worst_case_usd=GENERATOR_WORST_CASE_USD,
    )


def test_prompt_defines_supported_boundary_and_closed_route_meanings() -> None:
    messages = build_classifier_messages(
        _question(),
        _catalog(),
        max_input_chars=1024,
    )
    system = messages[0]["content"]

    for required in (
        "keys: route,intent,topic_id,coverage_id,pending_slot",
        "all five values are strings",
        "no extra key, prose or Markdown",
        "NONE is exact uppercase ASCII; 없음/none/null/empty are forbidden",
        "cat={intent:[[topic_id,coverage_id,coverage_label,approved_examples]]}",
        "SUPPORTED intent=cat group key; topic_id/coverage_id=same row",
    ):
        assert required in system


def test_prompt_defines_all_closed_pending_slots_and_route_shapes() -> None:
    messages = build_classifier_messages(
        _question(),
        _catalog(),
        max_input_chars=1024,
    )
    system = messages[0]["content"]

    for pending_slot in (
        "DOMAIN",
        "TOPIC_CHOICE",
        "CERTIFICATE_KIND",
        "REGION",
        "WASTE_ITEM",
    ):
        assert pending_slot in system
    for output_key in (
        "route",
        "intent",
        "topic_id",
        "coverage_id",
        "pending_slot",
    ):
        assert output_key in system

    for row in (
        "SUPPORTED|catalog intent|same-row topic_id|same-row coverage_id|NONE",
        "NO_TOPIC_MATCH|supported intent|NONE|NONE|NONE",
        "CIVIC_SCOPE_GAP|NONE|NONE|NONE|NONE",
        "NON_CIVIC|NONE|NONE|NONE|NONE",
        "NEEDS_FOLLOWUP|NONE|NONE|NONE|DOMAIN",
        "NEEDS_FOLLOWUP|supported intent|NONE|NONE|TOPIC_CHOICE",
        "NEEDS_FOLLOWUP|CERTIFICATE_ISSUANCE|NONE|NONE|CERTIFICATE_KIND",
        "NEEDS_FOLLOWUP|supported intent|NONE|NONE|REGION",
        "NEEDS_FOLLOWUP|BULKY_WASTE|NONE|NONE|WASTE_ITEM",
    ):
        assert row in system
    for obsolete in (
        "NONE=없음",
        "default=NONE",
        "NO_TOPIC_MATCH=지원",
        "DOMAIN?NONE:지원,,,",
    ):
        assert obsolete not in system


@pytest.mark.asyncio
async def test_success_makes_one_exact_closed_source_free_request() -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)
    seen: list[httpx.Request] = []
    safe = _question()
    ledger = _ledger()

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await QuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
        ).classify(safe, _catalog())

    assert decision == ClassifierDecision(
        route=ClassifierRoute.CIVIC_SCOPE_GAP,
        intent=None,
        topic_id=None,
        coverage_id=None,
        pending_slot=None,
    )
    assert len(seen) == 1
    request = seen[0]
    assert request.method == "POST"
    assert str(request.url) == "https://api.upstage.ai/v1/chat/completions"
    assert json.loads(request.content) == {
        "model": "solar-pro3",
        "messages": list(
            build_classifier_messages(
                safe,
                _catalog(),
                max_input_chars=1024,
            )
        ),
        "stream": False,
        "temperature": 0,
        "max_tokens": 128,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "sejong_classifier_decision",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "route": {"type": "string"},
                        "intent": {"type": "string"},
                        "topic_id": {"type": "string"},
                        "coverage_id": {"type": "string"},
                        "pending_slot": {"type": "string"},
                    },
                    "required": [
                        "route",
                        "intent",
                        "topic_id",
                        "coverage_id",
                        "pending_slot",
                    ],
                    "additionalProperties": False,
                },
            },
        },
    }
    serialized = request.content.decode("utf-8")
    for forbidden in (
        SECRET,
        "answer",
        "source_url",
        "source_title",
        "candidate_eligible",
        "FACT-SENTINEL",
        "OFFICE-SENTINEL",
        "FEE-SENTINEL",
        "CAUTION-SENTINEL",
    ):
        assert forbidden not in serialized
    response_schema = json.loads(request.content)["response_format"]["json_schema"]["schema"]
    assert "enum" not in json.dumps(response_schema)
    assert safe.text not in json.dumps(response_schema, ensure_ascii=False)
    for forbidden_schema_value in (
        "KB-WASTE-01",
        "GENERAL_BULKY_DISPOSAL",
        "SOURCE-SENTINEL",
        "OFFICE-SENTINEL",
    ):
        assert forbidden_schema_value not in json.dumps(response_schema)
    assert ledger.actual_cost_usd == estimate_cost_usd(TokenUsage(20, 0, 10))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("usage", "include_usage"),
    [
        (None, False),
        ([], True),
        ({}, True),
        ({"prompt_tokens": True, "completion_tokens": 10}, True),
        ({"prompt_tokens": 20.0, "completion_tokens": 10}, True),
        ({"prompt_tokens": -1, "completion_tokens": 10}, True),
        ({"prompt_tokens": 4097, "completion_tokens": 10}, True),
        ({"prompt_tokens": 20, "completion_tokens": True}, True),
        ({"prompt_tokens": 20, "completion_tokens": 10.0}, True),
        ({"prompt_tokens": 20, "completion_tokens": -1}, True),
        ({"prompt_tokens": 20, "completion_tokens": 129}, True),
        (
            {
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "total_tokens": True,
            },
            True,
        ),
        (
            {
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "total_tokens": 30.0,
            },
            True,
        ),
        (
            {
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "total_tokens": -1,
            },
            True,
        ),
        (
            {
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "total_tokens": 31,
            },
            True,
        ),
        (
            {
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "prompt_tokens_details": [],
            },
            True,
        ),
        (
            {
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "prompt_tokens_details": {"cached_tokens": True},
            },
            True,
        ),
        (
            {
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "prompt_tokens_details": {"cached_tokens": 1.0},
            },
            True,
        ),
        (
            {
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "prompt_tokens_details": {"cached_tokens": -1},
            },
            True,
        ),
        (
            {
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "prompt_tokens_details": {"cached_tokens": 21},
            },
            True,
        ),
        (
            {
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "cached_tokens": 2,
                "prompt_tokens_details": {"cached_tokens": 1},
            },
            True,
        ),
    ],
)
async def test_classifier_usage_is_strict_and_invalid_usage_charges_worst_case(
    usage: object,
    include_usage: bool,
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)
    ledger = _ledger()

    def handler(_request: httpx.Request) -> httpx.Response:
        return _provider_response(
            usage=usage,
            include_usage=include_usage,
        )

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await QuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
        ).classify(_question(), _catalog())

    assert decision is None
    assert ledger.actual_cost_usd == CLASSIFIER_WORST_CASE_USD
    assert SECRET not in caplog.text


@pytest.mark.asyncio
async def test_classifier_accepts_exact_usage_maxima_and_metered_details() -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)
    ledger = _ledger()
    usage = {
        "prompt_tokens": 4096,
        "completion_tokens": 128,
        "total_tokens": 4224,
        "cached_tokens": 1024,
        "prompt_tokens_details": {"cached_tokens": 1024},
    }

    def handler(_request: httpx.Request) -> httpx.Response:
        return _provider_response(usage=usage)

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await QuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
        ).classify(_question(), _catalog())

    assert decision is not None
    assert decision.route is ClassifierRoute.CIVIC_SCOPE_GAP
    assert ledger.actual_cost_usd == estimate_cost_usd(TokenUsage(4096, 1024, 128))
    assert ledger.actual_cost_usd <= CLASSIFIER_WORST_CASE_USD


@pytest.mark.asyncio
async def test_classifier_parser_failure_after_valid_usage_charges_actual_once() -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)
    ledger = _ledger()

    def handler(_request: httpx.Request) -> httpx.Response:
        return _provider_response(content="not-json")

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await QuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
        ).classify(_question(), _catalog())

    assert decision is None
    assert ledger.actual_cost_usd == estimate_cost_usd(TokenUsage(20, 0, 10))


@pytest.mark.asyncio
async def test_classifier_cost_cap_blocks_next_request_before_transport() -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)
    ledger = _ledger(cost_cap_usd=CLASSIFIER_WORST_CASE_USD)
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        classifier = QuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
        )
        first = await classifier.classify(_question(), _catalog())
        second = await classifier.classify(_question(), _catalog())

    assert first is not None
    assert second is None
    assert calls == 1
    assert ledger.classifier_attempts_used == 1


@pytest.mark.asyncio
async def test_real_governed_20_catalog_reaches_transport_and_ledger(
    governed_catalog_20: TopicCatalog,
) -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)
    calls = 0
    ledger = _ledger()

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await QuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
        ).classify(_question("안전한 질문"), governed_catalog_20)

    assert decision == ClassifierDecision(
        route=ClassifierRoute.CIVIC_SCOPE_GAP,
        intent=None,
        topic_id=None,
        coverage_id=None,
        pending_slot=None,
    )
    assert calls == 1
    assert ledger.classifier_attempts_used == 1


@pytest.mark.asyncio
async def test_real_governed_20_catalog_with_256_chars_reaches_transport_and_ledger(
    governed_catalog_20: TopicCatalog,
) -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)
    safe = _question(("How do I get general public service guidance? " * 10)[:256])
    messages = build_classifier_messages(
        safe,
        governed_catalog_20,
        max_input_chars=1024,
    )
    calls = 0
    ledger = _ledger()

    assert len(safe.text) == 256
    assert classifier_prompt_module.estimate_classifier_input_upper_bound(messages) <= 4096

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await QuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
        ).classify(safe, governed_catalog_20)

    assert decision is not None
    assert calls == 1
    assert ledger.classifier_attempts_used == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [429, 500])
async def test_http_failures_return_none_without_retry(
    status_code: int,
) -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status_code)

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await QuestionClassifier(
            settings=settings,
            client=client,
            ledger=_ledger(),
        ).classify(_question(), _catalog())

    assert decision is None
    assert calls == 1


@pytest.mark.asyncio
async def test_timeout_returns_none_without_retry_or_content_exception() -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)
    calls = 0
    observed: list[ClassifierResponseStage] = []
    sensitive_question = "장학금 신청 어떻게 해요?"

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout(sensitive_question, request=request)

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await QuestionClassifier(
            settings=settings,
            client=client,
            ledger=_ledger(),
            response_stage_observer=observed.append,
        ).classify(_question(sensitive_question), _catalog())

    assert decision is None
    assert calls == 1
    assert observed == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected_stage", "decision_expected"),
    [
        (httpx.Response(429), ClassifierResponseStage.HTTP_REJECTED, False),
        (
            httpx.Response(200, content=b"not-json"),
            ClassifierResponseStage.ENVELOPE_REJECTED,
            False,
        ),
        (
            _provider_envelope_response([]),
            ClassifierResponseStage.ENVELOPE_REJECTED,
            False,
        ),
        (
            _provider_response(include_usage=False),
            ClassifierResponseStage.USAGE_REJECTED,
            False,
        ),
        (
            _provider_envelope_response(
                {
                    "usage": {"prompt_tokens": 20, "completion_tokens": 10},
                    "choices": [],
                }
            ),
            ClassifierResponseStage.CHOICE_REJECTED,
            False,
        ),
        (
            _provider_response(finish_reason="length"),
            ClassifierResponseStage.FINISH_REASON_REJECTED,
            False,
        ),
        (
            _provider_envelope_response(
                {
                    "usage": {"prompt_tokens": 20, "completion_tokens": 10},
                    "choices": [{"finish_reason": "stop", "message": []}],
                }
            ),
            ClassifierResponseStage.MESSAGE_REJECTED,
            False,
        ),
        (
            _provider_response(content=" "),
            ClassifierResponseStage.CONTENT_REJECTED,
            False,
        ),
        (
            _provider_response(content="not-json"),
            ClassifierResponseStage.JSON_REJECTED,
            False,
        ),
        (
            _provider_response(content="[]"),
            ClassifierResponseStage.KEY_SET_REJECTED,
            False,
        ),
        (
            _provider_response(
                content=(
                    '{"route":"NON_CIVIC","intent":null,"topic_id":"NONE",'
                    '"coverage_id":"NONE","pending_slot":"NONE"}'
                )
            ),
            ClassifierResponseStage.FIELD_TYPE_REJECTED,
            False,
        ),
        (
            _provider_response(
                content=(
                    '{"route":"UNBOUNDED","intent":"NONE","topic_id":"NONE",'
                    '"coverage_id":"NONE","pending_slot":"NONE"}'
                )
            ),
            ClassifierResponseStage.ENUM_SHAPE_REJECTED,
            False,
        ),
        (
            _provider_response(
                content=(
                    '{"route":"SUPPORTED","intent":"BULKY_WASTE",'
                    '"topic_id":"KB-WASTE-99","coverage_id":"GENERAL_BULKY_DISPOSAL",'
                    '"pending_slot":"NONE"}'
                )
            ),
            ClassifierResponseStage.CATALOG_REJECTED,
            False,
        ),
        (
            _provider_response(),
            ClassifierResponseStage.ACCEPTED,
            True,
        ),
    ],
)
async def test_http_response_emits_one_value_free_terminal_stage(
    response: httpx.Response,
    expected_stage: ClassifierResponseStage,
    decision_expected: bool,
) -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)
    observed: list[ClassifierResponseStage] = []

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(lambda _request: response),
    ) as client:
        decision = await QuestionClassifier(
            settings=settings,
            client=client,
            ledger=_ledger(),
            response_stage_observer=observed.append,
        ).classify(_question(), _catalog())

    assert (decision is not None) is decision_expected
    assert observed == [expected_stage]
    assert all(type(stage) is ClassifierResponseStage for stage in observed)


@pytest.mark.asyncio
async def test_response_stage_observer_failure_does_not_change_accepted_decision() -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)

    def failing_observer(_stage: ClassifierResponseStage) -> None:
        raise RuntimeError("OBSERVER_FAILURE_SENTINEL")

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(lambda _request: _provider_response()),
    ) as client:
        decision = await QuestionClassifier(
            settings=settings,
            client=client,
            ledger=_ledger(),
            response_stage_observer=failing_observer,
        ).classify(_question(), _catalog())

    assert decision is not None
    assert decision.route is ClassifierRoute.CIVIC_SCOPE_GAP


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"not-json"),
        _provider_response(content="not-json"),
        _provider_response(
            content=(
                '{"route":"UNBOUNDED","intent":"NONE","topic_id":"NONE","pending_slot":"NONE"}'
            )
        ),
        _provider_response(finish_reason="length"),
    ],
)
async def test_invalid_envelope_or_decision_returns_none(
    response: httpx.Response,
) -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return response

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await QuestionClassifier(
            settings=settings,
            client=client,
            ledger=_ledger(),
        ).classify(_question(), _catalog())

    assert decision is None
    assert calls == 1


@pytest.mark.asyncio
async def test_attempt_cap_blocks_second_transport_and_has_no_retry() -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _provider_response(
            content=(
                '{"route":"NO_TOPIC_MATCH","intent":"LOCAL_TAX_GENERAL",'
                '"topic_id":"NONE","coverage_id":"NONE","pending_slot":"NONE"}'
            )
        )

    ledger = _ledger(classifier_cap=1)
    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        classifier = QuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
        )
        first = await classifier.classify(_question("자동차세 납부 방법"), _catalog())
        second = await classifier.classify(_question("재산세 납부 방법"), _catalog())

    assert first is not None
    assert first.intent is Intent.LOCAL_TAX_GENERAL
    assert second is None
    assert calls == 1
    assert ledger.classifier_attempts_used == 1


@pytest.mark.asyncio
async def test_oversized_question_is_rejected_before_transport_or_ledger_reservation() -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)
    calls = 0
    ledger = _ledger()

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        await QuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
        ).classify(_forged_oversized_safe_question(), _catalog())

    assert calls == 0
    assert ledger.classifier_attempts_used == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("catalog_size", [0, 21])
async def test_ineligible_catalog_is_rejected_before_transport_or_ledger_reservation(
    catalog_size: int,
) -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)
    calls = 0
    ledger = _ledger()

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await QuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
        ).classify(_question(), _catalog(catalog_size))

    assert decision is None
    assert calls == 0
    assert ledger.classifier_attempts_used == 0


@pytest.mark.asyncio
async def test_prompt_over_4096_estimate_is_rejected_before_transport_and_reservation() -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)
    catalog = _catalog(coverage_label="가" * 4096)
    messages = build_classifier_messages(
        _question(),
        catalog,
        max_input_chars=1024,
    )
    assert classifier_prompt_module.estimate_classifier_input_upper_bound(messages) > 4096
    calls = 0
    ledger = _ledger()

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await QuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
        ).classify(_question(), catalog)

    assert decision is None
    assert calls == 0
    assert ledger.classifier_attempts_used == 0


@pytest.mark.asyncio
async def test_provider_topic_and_coverage_must_match_request_catalog() -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)

    def handler(_request: httpx.Request) -> httpx.Response:
        return _provider_response(
            content=(
                '{"route":"SUPPORTED","intent":"BULKY_WASTE",'
                '"topic_id":"KB-WASTE-01","coverage_id":"WRONG_COVERAGE",'
                '"pending_slot":"NONE"}'
            )
        )

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await QuestionClassifier(
            settings=settings,
            client=client,
            ledger=_ledger(),
        ).classify(_question(), _catalog())

    assert decision is None
