from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.db.models import Intent
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


def _provider_response(
    content: str = (
        '{"route":"CIVIC_SCOPE_GAP","intent":null,"topic_id":null,"pending_slot":null}'
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
        ).classify(safe)

    assert decision == ClassifierDecision(
        route=ClassifierRoute.CIVIC_SCOPE_GAP,
        intent=None,
        topic_id=None,
        pending_slot=None,
    )
    assert len(seen) == 1
    request = seen[0]
    assert request.method == "POST"
    assert str(request.url) == "https://api.upstage.ai/v1/chat/completions"
    assert json.loads(request.content) == {
        "model": "solar-pro3",
        "messages": list(build_classifier_messages(safe, max_input_chars=1024)),
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
    ):
        assert forbidden not in serialized


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
        ).classify(_question())

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
        ).classify(_question(sensitive_question))

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
        ).classify(_question())

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
                '{"route":"SUPPORTED","intent":"LOCAL_TAX_GENERAL",'
                '"topic_id":null,"pending_slot":null}'
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
        first = await classifier.classify(_question("자동차세 납부 방법"))
        second = await classifier.classify(_question("재산세 납부 방법"))

    assert first is not None
    assert first.intent is Intent.LOCAL_TAX_GENERAL
    assert second is None
    assert calls == 1
    assert ledger.classifier_attempts_used == 1


@pytest.mark.asyncio
async def test_prompt_truncates_masked_question_to_exact_character_cap() -> None:
    settings = UpstageClassifierSettings(api_key=SECRET, max_input_chars=8)
    question = "청년 월세 지원 방법 알려주세요"
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        await QuestionClassifier(
            settings=settings,
            client=client,
            ledger=_ledger(),
        ).classify(_question(question))

    body = json.loads(seen[0].content)
    request_body = body
    user_message = request_body["messages"][1]["content"]
    user_payload = json.loads(user_message)
    assert user_payload["masked_question"] == question[:8]
    assert question[8:] not in user_message
    assert body["max_tokens"] == 128
