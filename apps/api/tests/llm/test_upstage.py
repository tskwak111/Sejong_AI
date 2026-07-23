import json
from collections.abc import Callable

import httpx
import pytest

from sejong_ai_api.llm.contracts import OutcomeCode
from sejong_ai_api.llm.limits import AttemptBudget
from sejong_ai_api.llm.prompt import build_upstage_messages
from sejong_ai_api.llm.settings import UpstageSyntheticSettings
from sejong_ai_api.llm.upstage import UpstageProvider, create_upstage_client

Handler = Callable[[httpx.Request], httpx.Response]


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


def _provider_response(
    *,
    content: str | None = None,
    finish_reason: str = "stop",
    prompt_tokens: object = 20,
    completion_tokens: object = 10,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "finish_reason": finish_reason,
                    "message": {"content": _answer_json() if content is None else content},
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            },
        },
    )


@pytest.mark.asyncio
async def test_success_uses_exact_request_and_parses_only_answer_and_usage(
    grounded_fixture,
    exact_settings,
) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=exact_settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        outcome = await UpstageProvider(
            settings=exact_settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(grounded_fixture)

    assert outcome.code is OutcomeCode.SUCCESS
    assert outcome.answer is not None
    assert outcome.answer.summary == "안내"
    assert outcome.usage.input_tokens == 20
    assert outcome.usage.cached_input_tokens == 0
    assert outcome.usage.output_tokens == 10
    assert outcome.attempts_used == 1
    assert len(seen) == 1
    request = seen[0]
    assert request.method == "POST"
    assert request.url.path == "/v1/chat/completions"
    assert json.loads(request.content) == {
        "model": "solar-pro3",
        "messages": list(build_upstage_messages(grounded_fixture)),
        "stream": False,
        "temperature": 0.1,
        "max_tokens": 1024,
    }


@pytest.mark.asyncio
async def test_rate_limit_retries_once_and_never_uses_hidden_retry(
    grounded_fixture,
    exact_settings,
) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if len(seen) == 1:
            return httpx.Response(429, json={"error": {"message": "bounded"}})
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=exact_settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        outcome = await UpstageProvider(
            settings=exact_settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(grounded_fixture)

    assert outcome.code is OutcomeCode.SUCCESS
    assert outcome.attempts_used == 2
    assert len(seen) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (401, OutcomeCode.AUTH),
        (403, OutcomeCode.AUTH),
        (400, OutcomeCode.HTTP_ERROR),
        (404, OutcomeCode.HTTP_ERROR),
    ],
)
async def test_non_retryable_http_errors_make_one_request(
    grounded_fixture,
    exact_settings,
    status_code: int,
    expected_code: OutcomeCode,
) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(status_code, content=b"provider-body-must-not-escape")

    async with httpx.AsyncClient(
        base_url=exact_settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        outcome = await UpstageProvider(
            settings=exact_settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(grounded_fixture)

    assert outcome.code is expected_code
    assert outcome.attempts_used == 1
    assert requests == 1
    assert "provider-body-must-not-escape" not in repr(outcome)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response_factory", "expected_code"),
    [
        (lambda: httpx.Response(500), OutcomeCode.HTTP_ERROR),
        (lambda: httpx.Response(503), OutcomeCode.HTTP_ERROR),
        (lambda: _provider_response(content=""), OutcomeCode.EMPTY),
        (
            lambda: _provider_response(finish_reason="length"),
            OutcomeCode.TRUNCATED,
        ),
        (lambda: _provider_response(content="{not-json"), OutcomeCode.SCHEMA_INVALID),
        (
            lambda: _provider_response(content=_answer_json(source_url="https://example.invalid")),
            OutcomeCode.SCHEMA_INVALID,
        ),
    ],
)
async def test_retryable_provider_failures_retry_exactly_once(
    grounded_fixture,
    exact_settings,
    response_factory: Callable[[], httpx.Response],
    expected_code: OutcomeCode,
) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return response_factory()

    async with httpx.AsyncClient(
        base_url=exact_settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        outcome = await UpstageProvider(
            settings=exact_settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(grounded_fixture)

    assert outcome.code is expected_code
    assert outcome.attempts_used == 2
    assert requests == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exception_factory", "expected_code"),
    [
        (
            lambda request: httpx.ReadTimeout(
                "private-timeout-text",
                request=request,
            ),
            OutcomeCode.TIMEOUT,
        ),
        (
            lambda request: httpx.ConnectError("private-transport-text", request=request),
            OutcomeCode.TRANSPORT,
        ),
    ],
)
async def test_transport_failures_retry_exactly_once_without_exception_text(
    grounded_fixture,
    exact_settings,
    exception_factory: Callable[[httpx.Request], httpx.TransportError],
    expected_code: OutcomeCode,
) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        raise exception_factory(request)

    async with httpx.AsyncClient(
        base_url=exact_settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        outcome = await UpstageProvider(
            settings=exact_settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(grounded_fixture)

    assert outcome.code is expected_code
    assert outcome.attempts_used == 2
    assert requests == 2
    assert "private-" not in repr(outcome)


@pytest.mark.asyncio
async def test_usage_is_summed_only_from_valid_integer_fields(
    grounded_fixture,
    exact_settings,
) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        if requests == 1:
            return _provider_response(
                finish_reason="length",
                prompt_tokens=5,
                completion_tokens=True,
            )
        return _provider_response(prompt_tokens=20, completion_tokens=10)

    async with httpx.AsyncClient(
        base_url=exact_settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        outcome = await UpstageProvider(
            settings=exact_settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(grounded_fixture)

    assert outcome.code is OutcomeCode.SUCCESS
    assert outcome.usage.input_tokens == 25
    assert outcome.usage.cached_input_tokens == 0
    assert outcome.usage.output_tokens == 10
    assert outcome.attempts_used == 2


@pytest.mark.asyncio
async def test_conservative_input_overflow_returns_without_request(
    grounded_fixture,
    exact_settings,
) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return _provider_response()

    constrained = UpstageSyntheticSettings(
        api_key=exact_settings.api_key,
        max_input_tokens=1,
    )
    async with httpx.AsyncClient(
        base_url=constrained.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        outcome = await UpstageProvider(
            settings=constrained,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(grounded_fixture)

    assert outcome.code is OutcomeCode.INPUT_LIMIT
    assert outcome.attempts_used == 0
    assert requests == 0


@pytest.mark.asyncio
async def test_provider_reported_input_overflow_returns_without_retry(
    grounded_fixture,
    exact_settings,
) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return _provider_response(prompt_tokens=4097)

    async with httpx.AsyncClient(
        base_url=exact_settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        outcome = await UpstageProvider(
            settings=exact_settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(grounded_fixture)

    assert outcome.code is OutcomeCode.INPUT_LIMIT
    assert outcome.usage.input_tokens == 4097
    assert outcome.attempts_used == 1
    assert requests == 1


@pytest.mark.asyncio
async def test_cap_reached_returns_without_request(
    grounded_fixture,
    exact_settings,
) -> None:
    requests = 0
    budget = AttemptBudget(cap=1, concurrency=1)
    async with budget.reserve():
        pass

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=exact_settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        outcome = await UpstageProvider(
            settings=exact_settings,
            client=client,
            budget=budget,
        ).generate(grounded_fixture)

    assert outcome.code is OutcomeCode.ATTEMPT_CAP
    assert outcome.attempts_used == 0
    assert requests == 0


def test_production_client_uses_exact_profile(exact_settings, monkeypatch) -> None:
    captured: dict[str, object] = {}

    class CapturingTransport:
        def __init__(self, *, retries: int) -> None:
            captured["retries"] = retries

    class CapturingClient:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(httpx, "AsyncHTTPTransport", CapturingTransport)
    monkeypatch.setattr(httpx, "AsyncClient", CapturingClient)

    client = create_upstage_client(exact_settings)

    assert isinstance(client, CapturingClient)
    assert captured["base_url"] == "https://api.upstage.ai/v1"
    assert captured["headers"] == {
        "Authorization": "Bearer synthetic-test-key-not-a-real-secret",
        "Content-Type": "application/json",
    }
    timeout = captured["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect == 5.0
    assert timeout.read == 15.0
    assert timeout.write == 15.0
    assert timeout.pool == 15.0
    assert captured["retries"] == 0
