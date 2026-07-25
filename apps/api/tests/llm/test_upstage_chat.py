import json
from collections.abc import Callable

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
from sejong_ai_api.llm.limits import AttemptBudget
from sejong_ai_api.llm.settings import UpstageChatSettings
from sejong_ai_api.llm.upstage_chat import (
    GroundedChatRuntime,
    UpstageChatGenerator,
    build_upstage_chat_runtime,
    create_upstage_chat_client,
)

Handler = Callable[[httpx.Request], httpx.Response]
SECRET = "chat-test-key-not-a-real-secret"


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
    assert requests == 1


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
