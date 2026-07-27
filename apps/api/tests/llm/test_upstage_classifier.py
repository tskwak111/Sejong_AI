from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date

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
from sejong_ai_api.llm.classifier_prompt import build_classifier_messages
from sejong_ai_api.llm.limits import ProviderAttemptLedger
from sejong_ai_api.llm.settings import UpstageClassifierSettings
from sejong_ai_api.llm.upstage_classifier import QuestionClassifier
from sejong_ai_api.privacy.redaction import redact_question

Handler = Callable[[httpx.Request], httpx.Response]
SECRET = "classifier-test-key-not-a-real-secret"


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
                "GENERAL_BULKY_DISPOSAL"
                if index == 1
                else f"GENERAL_BULKY_DISPOSAL_{index:02d}"
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
        tuple(
            _runtime_topic(index, coverage_label=coverage_label)
            for index in range(1, size + 1)
        )
    )


def _provider_response(
    content: str = (
        '{"route":"CIVIC_SCOPE_GAP","intent":null,"topic_id":null,'
        '"coverage_id":null,"pending_slot":null}'
    ),
    *,
    finish_reason: str = "stop",
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "finish_reason": finish_reason,
                    "message": {"content": content},
                }
            ]
        },
    )


def _ledger(*, classifier_cap: int = 20) -> ProviderAttemptLedger:
    return ProviderAttemptLedger(
        classifier_cap=classifier_cap,
        generator_cap=30,
        combined_cap=min(40, classifier_cap + 30),
    )


def test_prompt_defines_supported_boundary_and_closed_route_meanings() -> None:
    messages = build_classifier_messages(
        _question(),
        _catalog(),
        max_input_chars=1024,
    )
    system = messages[0]["content"]

    for required in (
        "CIVIC_SCOPE_GAP",
        "NON_CIVIC",
        "NEEDS_FOLLOWUP",
        "NO_TOPIC_MATCH",
        "topic_id",
        "coverage_id",
    ):
        assert required in system


@pytest.mark.asyncio
async def test_success_makes_one_exact_closed_source_free_request() -> None:
    settings = UpstageClassifierSettings(api_key=SECRET)
    seen: list[httpx.Request] = []
    safe = _question()

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
            ledger=_ledger(),
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
        "response_format": {"type": "json_object"},
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
        ).classify(_question(sensitive_question), _catalog())

    assert decision is None
    assert calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"not-json"),
        _provider_response(content="not-json"),
        _provider_response(
            content=('{"route":"UNBOUNDED","intent":null,"topic_id":null,"pending_slot":null}')
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
                '"topic_id":null,"coverage_id":null,"pending_slot":null}'
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
                '"pending_slot":null}'
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
