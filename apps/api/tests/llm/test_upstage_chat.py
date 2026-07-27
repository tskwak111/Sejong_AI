import json
from collections.abc import Callable
from decimal import Decimal

import httpx
import pytest

from sejong_ai_api.db.models import Intent
from sejong_ai_api.llm.chat_contracts import (
    FactKind,
    GroundedChatOutcomeCode,
    GroundedChatRequest,
    GroundedFact,
)
from sejong_ai_api.llm.chat_prompt import build_grounded_chat_messages
from sejong_ai_api.llm.contracts import TokenUsage
from sejong_ai_api.llm.cost import estimate_cost_usd
from sejong_ai_api.llm.limits import AttemptBudget, ProviderAttemptLedger
from sejong_ai_api.llm.settings import UpstageChatSettings
from sejong_ai_api.llm.upstage_chat import (
    GroundedChatRuntime,
    UpstageChatGenerator,
    build_upstage_chat_runtime,
    create_upstage_chat_client,
)

Handler = Callable[[httpx.Request], httpx.Response]
SECRET = "chat-test-key-not-a-real-secret"
CLASSIFIER_WORST_CASE_USD = estimate_cost_usd(TokenUsage(4096, 0, 128))
GENERATOR_WORST_CASE_USD = estimate_cost_usd(TokenUsage(4096, 0, 1024))


def _ledger(
    *,
    classifier_cap: int = 80,
    generator_cap: int = 100,
    combined_cap: int = 160,
    cost_cap_usd: Decimal = Decimal("0.20"),
) -> ProviderAttemptLedger:
    return ProviderAttemptLedger(
        classifier_cap=classifier_cap,
        generator_cap=generator_cap,
        combined_cap=combined_cap,
        cost_cap_usd=cost_cap_usd,
        classifier_worst_case_usd=CLASSIFIER_WORST_CASE_USD,
        generator_worst_case_usd=GENERATOR_WORST_CASE_USD,
    )


def _request(*, question: str = "전입신고 방법을 알려 주세요.") -> GroundedChatRequest:
    return GroundedChatRequest(
        masked_question=question,
        intent=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        service_name="전입신고",
        approved_summary="전입한 날부터 14일 이내에 전입신고를 합니다.",
        facts=(
            GroundedFact("STEP-01", FactKind.PROCEDURE_STEP, "신고서를 작성합니다."),
            GroundedFact("DOC-01", FactKind.REQUIRED_DOCUMENT, "신분증을 준비합니다."),
            GroundedFact("TIME-01", FactKind.PROCESSING_TIME, "즉시"),
            GroundedFact("FEE-01", FactKind.FEE, "수수료 없음"),
            GroundedFact("DEPT-01", FactKind.DEPARTMENT, "주민등록 담당부서"),
        ),
    )


def _draft_json(**extra: object) -> str:
    payload: dict[str, object] = {
        "summary": "전입신고 안내를 쉽게 정리해 드려요.",
        "procedure_step_ids": ["STEP-01"],
        "required_document_ids": ["DOC-01"],
        "processing_time_id": "TIME-01",
        "fee_id": "FEE-01",
        "department_id": "DEPT-01",
    }
    payload.update(extra)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _provider_response(
    *,
    content: str | None = None,
    finish_reason: str = "stop",
    prompt_tokens: object = 20,
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "choices": [
                {
                    "finish_reason": finish_reason,
                    "message": {"content": _draft_json() if content is None else content},
                }
            ],
            "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": 10},
        },
    )


@pytest.mark.asyncio
async def test_success_makes_one_exact_source_free_request_and_strictly_parses_draft() -> None:
    settings = UpstageChatSettings(api_key=SECRET)
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await UpstageChatGenerator(
            settings=settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(_request())

    assert result.code is GroundedChatOutcomeCode.SUCCESS
    assert result.draft is not None
    assert result.draft.summary == "전입신고 안내를 쉽게 정리해 드려요."
    assert result.usage == TokenUsage(20, 0, 10)
    assert len(seen) == 1
    request = seen[0]
    assert request.method == "POST"
    assert request.url.path == "/v1/chat/completions"
    payload = json.loads(request.content)
    assert payload == {
        "model": "solar-pro3",
        "messages": list(build_grounded_chat_messages(_request())),
        "stream": False,
        "temperature": 0.1,
        "max_tokens": 1024,
    }
    serialized = request.content.decode("utf-8")
    for forbidden in (
        SECRET,
        "https://source-sentinel.invalid/private",
        "KB-PRIVATE-SENTINEL",
        "CAUTION-SENTINEL",
        "EXAMPLE-SENTINEL",
        "CONTEXT-SENTINEL",
        "OFFICE-SENTINEL",
    ):
        assert forbidden not in serialized


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (401, GroundedChatOutcomeCode.AUTH),
        (403, GroundedChatOutcomeCode.AUTH),
        (429, GroundedChatOutcomeCode.RATE_LIMIT),
        (500, GroundedChatOutcomeCode.HTTP_ERROR),
        (503, GroundedChatOutcomeCode.HTTP_ERROR),
        (400, GroundedChatOutcomeCode.HTTP_ERROR),
        (404, GroundedChatOutcomeCode.HTTP_ERROR),
    ],
)
async def test_every_http_failure_makes_one_request_and_discards_provider_body(
    status_code: int,
    expected_code: GroundedChatOutcomeCode,
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = UpstageChatSettings(api_key=SECRET)
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(status_code, content=b"PROVIDER-BODY-SENTINEL")

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await UpstageChatGenerator(
            settings=settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(_request())

    assert result.code is expected_code
    assert result.draft is None
    assert requests == 1
    assert "PROVIDER-BODY-SENTINEL" not in repr(result)
    assert "PROVIDER-BODY-SENTINEL" not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("exception_factory", "expected_code"),
    [
        (
            lambda request: httpx.ReadTimeout("PRIVATE-TIMEOUT-SENTINEL", request=request),
            GroundedChatOutcomeCode.TIMEOUT,
        ),
        (
            lambda request: httpx.ConnectError("PRIVATE-TRANSPORT-SENTINEL", request=request),
            GroundedChatOutcomeCode.TRANSPORT,
        ),
    ],
)
async def test_transport_failure_makes_one_request_without_raising_or_logging_exception_text(
    exception_factory: Callable[[httpx.Request], httpx.TransportError],
    expected_code: GroundedChatOutcomeCode,
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = UpstageChatSettings(api_key=SECRET)
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        raise exception_factory(request)

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await UpstageChatGenerator(
            settings=settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(_request())

    assert result.code is expected_code
    assert requests == 1
    assert "PRIVATE-" not in repr(result)
    assert "PRIVATE-" not in caplog.text


@pytest.mark.asyncio
async def test_unexpected_transport_exception_is_content_free_and_never_retried(
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = UpstageChatSettings(api_key=SECRET)
    question_marker = "QUESTION-MARKER"
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        raise RuntimeError(f"{question_marker} {SECRET}")

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await UpstageChatGenerator(
            settings=settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(_request(question=question_marker))

    assert result.code is GroundedChatOutcomeCode.TRANSPORT
    assert result.draft is None
    assert requests == 1
    assert question_marker not in repr(result)
    assert SECRET not in repr(result)
    assert question_marker not in caplog.text
    assert SECRET not in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response_factory", "expected_code"),
    [
        (lambda: _provider_response(content=""), GroundedChatOutcomeCode.EMPTY),
        (lambda: _provider_response(content="   "), GroundedChatOutcomeCode.EMPTY),
        (
            lambda: _provider_response(finish_reason="length"),
            GroundedChatOutcomeCode.TRUNCATED,
        ),
        (
            lambda: _provider_response(content="{not-json"),
            GroundedChatOutcomeCode.SCHEMA_INVALID,
        ),
        (
            lambda: _provider_response(content=_draft_json(source_url="https://provider.invalid")),
            GroundedChatOutcomeCode.SCHEMA_INVALID,
        ),
        (
            lambda: _provider_response(
                content=json.dumps(
                    {
                        "summary": "전입신고 안내입니다.",
                        "procedure_step_ids": ["STEP-01"],
                    }
                )
            ),
            GroundedChatOutcomeCode.SCHEMA_INVALID,
        ),
    ],
)
async def test_malformed_or_truncated_output_fails_closed_after_one_request(
    response_factory: Callable[[], httpx.Response],
    expected_code: GroundedChatOutcomeCode,
) -> None:
    settings = UpstageChatSettings(api_key=SECRET)
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return response_factory()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await UpstageChatGenerator(
            settings=settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(_request())

    assert result.code is expected_code
    assert result.draft is None
    assert result.usage == TokenUsage(20, 0, 10)
    assert requests == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("usage", "include_usage", "expected_code", "expected_usage"),
    [
        (None, False, GroundedChatOutcomeCode.SCHEMA_INVALID, TokenUsage(0, 0, 0)),
        ([], True, GroundedChatOutcomeCode.SCHEMA_INVALID, TokenUsage(0, 0, 0)),
        ({}, True, GroundedChatOutcomeCode.SCHEMA_INVALID, TokenUsage(0, 0, 0)),
        (
            {"prompt_tokens": True},
            True,
            GroundedChatOutcomeCode.SCHEMA_INVALID,
            TokenUsage(0, 0, 0),
        ),
        (
            {"prompt_tokens": 1.0},
            True,
            GroundedChatOutcomeCode.SCHEMA_INVALID,
            TokenUsage(0, 0, 0),
        ),
        (
            {"prompt_tokens": -1},
            True,
            GroundedChatOutcomeCode.SCHEMA_INVALID,
            TokenUsage(0, 0, 0),
        ),
        (
            {"prompt_tokens": 0, "completion_tokens": 0},
            True,
            GroundedChatOutcomeCode.SUCCESS,
            TokenUsage(0, 0, 0),
        ),
        (
            {"prompt_tokens": 4096, "completion_tokens": 10},
            True,
            GroundedChatOutcomeCode.SUCCESS,
            TokenUsage(4096, 0, 10),
        ),
        (
            {"prompt_tokens": 4097, "completion_tokens": 10},
            True,
            GroundedChatOutcomeCode.INPUT_LIMIT,
            TokenUsage(4097, 0, 10),
        ),
        (
            {"prompt_tokens": 20, "completion_tokens": 1024},
            True,
            GroundedChatOutcomeCode.SUCCESS,
            TokenUsage(20, 0, 1024),
        ),
        (
            {"prompt_tokens": 20, "completion_tokens": 1025},
            True,
            GroundedChatOutcomeCode.TRUNCATED,
            TokenUsage(20, 0, 1025),
        ),
        (
            {"prompt_tokens": 20, "completion_tokens": True},
            True,
            GroundedChatOutcomeCode.SCHEMA_INVALID,
            TokenUsage(0, 0, 0),
        ),
        (
            {"prompt_tokens": 20, "completion_tokens": -1},
            True,
            GroundedChatOutcomeCode.SCHEMA_INVALID,
            TokenUsage(0, 0, 0),
        ),
    ],
)
async def test_provider_usage_is_strict_and_fails_closed_after_one_request(
    usage: object,
    include_usage: bool,
    expected_code: GroundedChatOutcomeCode,
    expected_usage: TokenUsage,
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = UpstageChatSettings(api_key=SECRET)
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        envelope: dict[str, object] = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"content": _draft_json()},
                }
            ],
            "provider_private_error": "PRIVATE-USAGE-BODY-SENTINEL",
        }
        if include_usage:
            envelope["usage"] = usage
        return httpx.Response(200, json=envelope)

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await UpstageChatGenerator(
            settings=settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(_request())

    assert result.code is expected_code
    assert result.usage == expected_usage
    assert requests == 1
    assert "PRIVATE-USAGE-BODY-SENTINEL" not in repr(result)
    assert "PRIVATE-USAGE-BODY-SENTINEL" not in caplog.text


@pytest.mark.asyncio
async def test_conservative_input_overflow_returns_without_request() -> None:
    settings = UpstageChatSettings(api_key=SECRET, max_input_tokens=1)
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await UpstageChatGenerator(
            settings=settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(_request())

    assert result.code is GroundedChatOutcomeCode.INPUT_LIMIT
    assert result.draft is None
    assert requests == 0


@pytest.mark.asyncio
async def test_provider_reported_input_overflow_fails_closed_after_one_request() -> None:
    settings = UpstageChatSettings(api_key=SECRET)
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return _provider_response(prompt_tokens=4097)

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await UpstageChatGenerator(
            settings=settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(_request())

    assert result.code is GroundedChatOutcomeCode.INPUT_LIMIT
    assert result.draft is None
    assert requests == 1


@pytest.mark.asyncio
async def test_exhausted_attempt_cap_returns_without_request() -> None:
    settings = UpstageChatSettings(api_key=SECRET)
    budget = AttemptBudget(cap=1, concurrency=1)
    async with budget.reserve():
        pass
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await UpstageChatGenerator(
            settings=settings,
            client=client,
            budget=budget,
        ).generate(_request())

    assert result.code is GroundedChatOutcomeCode.ATTEMPT_CAP
    assert result.draft is None
    assert requests == 0


@pytest.mark.asyncio
async def test_generator_honors_combined_attempt_cap_shared_with_classifier() -> None:
    settings = UpstageChatSettings(api_key=SECRET)
    ledger = _ledger(
        classifier_cap=1,
        generator_cap=1,
        combined_cap=1,
    )
    async with ledger.reserve_classifier():
        pass
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await UpstageChatGenerator(
            settings=settings,
            client=client,
            budget=ledger,
        ).generate(_request())

    assert result.code is GroundedChatOutcomeCode.ATTEMPT_CAP
    assert requests == 0
    assert ledger.classifier_attempts_used == 1
    assert ledger.generator_attempts_used == 0


@pytest.mark.asyncio
async def test_runtime_uses_supplied_shared_attempt_ledger(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = _ledger()
    post_calls = 0

    async def generate_once(
        _client: httpx.AsyncClient,
        *_args: object,
        **_kwargs: object,
    ) -> httpx.Response:
        nonlocal post_calls
        post_calls += 1
        return _provider_response()

    monkeypatch.setattr(httpx.AsyncClient, "post", generate_once)
    runtime = build_upstage_chat_runtime(
        UpstageChatSettings(api_key=SECRET),
        ledger=ledger,
    )

    result = await runtime.generator.generate(_request())
    await runtime.aclose()

    assert result.code is GroundedChatOutcomeCode.SUCCESS
    assert post_calls == 1
    assert ledger.classifier_attempts_used == 0
    assert ledger.generator_attempts_used == 1
    assert ledger.actual_cost_usd == estimate_cost_usd(TokenUsage(20, 0, 10))


@pytest.mark.asyncio
async def test_shared_ledger_charges_generator_worst_case_for_invalid_usage() -> None:
    settings = UpstageChatSettings(api_key=SECRET)
    ledger = _ledger()

    def handler(_request: httpx.Request) -> httpx.Response:
        return _provider_response(prompt_tokens=True)

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await UpstageChatGenerator(
            settings=settings,
            client=client,
            budget=ledger,
        ).generate(_request())

    assert result.code is GroundedChatOutcomeCode.SCHEMA_INVALID
    assert ledger.actual_cost_usd == GENERATOR_WORST_CASE_USD


@pytest.mark.asyncio
async def test_shared_ledger_charges_generator_worst_case_for_parser_failure() -> None:
    settings = UpstageChatSettings(api_key=SECRET)
    ledger = _ledger()

    def handler(_request: httpx.Request) -> httpx.Response:
        return _provider_response(content="{not-json")

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await UpstageChatGenerator(
            settings=settings,
            client=client,
            budget=ledger,
        ).generate(_request())

    assert result.code is GroundedChatOutcomeCode.SCHEMA_INVALID
    assert ledger.actual_cost_usd == GENERATOR_WORST_CASE_USD


@pytest.mark.asyncio
async def test_shared_ledger_charges_generator_worst_case_for_timeout() -> None:
    settings = UpstageChatSettings(api_key=SECRET)
    ledger = _ledger()

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("PRIVATE-TIMEOUT-SENTINEL", request=request)

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = await UpstageChatGenerator(
            settings=settings,
            client=client,
            budget=ledger,
        ).generate(_request())

    assert result.code is GroundedChatOutcomeCode.TIMEOUT
    assert ledger.actual_cost_usd == GENERATOR_WORST_CASE_USD


@pytest.mark.asyncio
async def test_shared_ledger_cost_cap_blocks_next_generator_before_transport() -> None:
    settings = UpstageChatSettings(api_key=SECRET)
    ledger = _ledger(cost_cap_usd=GENERATOR_WORST_CASE_USD)
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        generator = UpstageChatGenerator(
            settings=settings,
            client=client,
            budget=ledger,
        )
        first = await generator.generate(_request())
        second = await generator.generate(_request())

    assert first.code is GroundedChatOutcomeCode.SUCCESS
    assert second.code is GroundedChatOutcomeCode.ATTEMPT_CAP
    assert calls == 1
    assert ledger.generator_attempts_used == 1


def test_production_client_uses_exact_chat_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class CapturingTransport:
        def __init__(self, *, retries: int) -> None:
            captured["retries"] = retries

    class CapturingClient:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

    monkeypatch.setattr(httpx, "AsyncHTTPTransport", CapturingTransport)
    monkeypatch.setattr(httpx, "AsyncClient", CapturingClient)

    client = create_upstage_chat_client(UpstageChatSettings(api_key=SECRET))

    assert isinstance(client, CapturingClient)
    assert captured["base_url"] == "https://api.upstage.ai/v1"
    assert captured["headers"] == {
        "Authorization": f"Bearer {SECRET}",
        "Content-Type": "application/json",
    }
    timeout = captured["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect == 5.0
    assert timeout.read == 8.0
    assert timeout.write == 8.0
    assert timeout.pool == 8.0
    assert captured["retries"] == 0


@pytest.mark.asyncio
async def test_runtime_owns_and_closes_its_client() -> None:
    runtime = build_upstage_chat_runtime(UpstageChatSettings(api_key=SECRET))

    assert isinstance(runtime, GroundedChatRuntime)
    assert isinstance(runtime.generator, UpstageChatGenerator)
    assert not runtime.client.is_closed

    await runtime.aclose()

    assert runtime.client.is_closed
