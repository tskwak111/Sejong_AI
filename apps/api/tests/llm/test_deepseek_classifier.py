from __future__ import annotations

import asyncio
import gzip
import json
import time
from collections.abc import Callable
from datetime import date
from decimal import Decimal

import httpx
import pytest

from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.topic_catalog import RuntimeTopic, TopicCatalog, TopicCoverage
from sejong_ai_api.db.models import Intent, KnowledgeRecord
from sejong_ai_api.llm.classifier_contracts import ClassifierDecision, ClassifierRoute
from sejong_ai_api.llm.classifier_diagnostics import ClassifierResponseStage
from sejong_ai_api.llm.classifier_prompt import (
    build_classifier_messages,
    estimate_classifier_input_upper_bound,
)
from sejong_ai_api.llm.contracts import TokenUsage
from sejong_ai_api.llm.cost import estimate_cost_usd
from sejong_ai_api.llm.deepseek_classifier import (
    DeepSeekQuestionClassifier,
    DeepSeekResponseObservation,
    create_deepseek_classifier_client,
)
from sejong_ai_api.llm.deepseek_settings import DeepSeekClassifierSettings
from sejong_ai_api.llm.deepseek_usage import estimate_deepseek_cost_usd
from sejong_ai_api.llm.limits import ProviderAttemptLedger
from sejong_ai_api.privacy.redaction import redact_question

Handler = Callable[[httpx.Request], httpx.Response]
SECRET = "deepseek-test-key-not-a-real-secret"
DSN_SENTINEL = "postgresql://forbidden-dsn.invalid/database"
DEEPSEEK_WORST_CASE_USD = estimate_deepseek_cost_usd(TokenUsage(16384, 0, 128))
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
    return RuntimeTopic(
        record=KnowledgeRecord(
            public_id=topic_id,
            category=Intent.BULKY_WASTE,
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
            ),
        ),
        coverage=TopicCoverage(
            topic_id=topic_id,
            intent=Intent.BULKY_WASTE,
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


def _usage() -> dict[str, int]:
    return {
        "prompt_tokens": 20,
        "completion_tokens": 10,
        "total_tokens": 30,
        "prompt_cache_hit_tokens": 5,
        "prompt_cache_miss_tokens": 15,
    }


def _provider_response(
    content: object = (
        '{"route":"CIVIC_SCOPE_GAP","intent":"NONE","topic_id":"NONE",'
        '"coverage_id":"NONE","pending_slot":"NONE"}'
    ),
    *,
    finish_reason: object = "stop",
    choices: object | None = None,
    usage: object | None = None,
    include_usage: bool = True,
) -> httpx.Response:
    envelope: dict[str, object] = {
        "choices": (
            [
                {
                    "finish_reason": finish_reason,
                    "message": {"content": content},
                }
            ]
            if choices is None
            else choices
        ),
    }
    if include_usage:
        envelope["usage"] = _usage() if usage is None else usage
    return httpx.Response(
        200,
        headers={"Content-Type": "application/json"},
        stream=httpx.ByteStream(
            json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ),
    )


def _envelope_response(envelope: object) -> httpx.Response:
    return httpx.Response(
        200,
        headers={"Content-Type": "application/json"},
        stream=httpx.ByteStream(
            json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ),
    )


class _ChunkedResponseStream(httpx.AsyncByteStream):
    def __init__(
        self,
        chunks: tuple[bytes, ...],
        *,
        delay_seconds: float = 0,
    ) -> None:
        self.chunks = chunks
        self.delay_seconds = delay_seconds
        self.yielded = 0
        self.closed = False

    async def __aiter__(self):  # type: ignore[no-untyped-def]
        for chunk in self.chunks:
            if self.delay_seconds:
                await asyncio.sleep(self.delay_seconds)
            self.yielded += 1
            yield chunk

    async def aclose(self) -> None:
        self.closed = True


def _ledger(
    *,
    classifier_cap: int = 80,
    cost_cap_usd: Decimal = Decimal("0.20"),
) -> ProviderAttemptLedger:
    return ProviderAttemptLedger(
        classifier_cap=classifier_cap,
        generator_cap=100,
        combined_cap=min(160, classifier_cap + 100),
        cost_cap_usd=cost_cap_usd,
        classifier_worst_case_usd=DEEPSEEK_WORST_CASE_USD,
        generator_worst_case_usd=GENERATOR_WORST_CASE_USD,
        classifier_cost_estimator=estimate_deepseek_cost_usd,
    )


@pytest.mark.asyncio
async def test_client_factory_separates_connect_and_complete_response_budgets() -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)
    client = create_deepseek_classifier_client(settings)

    try:
        assert str(client.base_url) == "https://api.deepseek.com"
        assert client.headers["Authorization"] == f"Bearer {SECRET}"
        assert client.headers["Content-Type"] == "application/json"
        assert client.timeout.connect == 3.0
        assert client.timeout.read == 10.0
        assert client.timeout.write == 3.0
        assert client.timeout.pool == 3.0
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_client_factory_pins_zero_transport_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)
    object.__setattr__(settings, "max_retries", 7)
    constructed_retries: list[int] = []
    original_transport = httpx.AsyncHTTPTransport

    def capturing_transport(*, retries: int = 0) -> httpx.AsyncHTTPTransport:
        constructed_retries.append(retries)
        return original_transport(retries=retries)

    monkeypatch.setattr(httpx, "AsyncHTTPTransport", capturing_transport)
    client = create_deepseek_classifier_client(settings)

    try:
        assert constructed_retries == [0]
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_success_posts_one_exact_deepseek_json_object_request() -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)
    safe = _question()
    catalog = _catalog()
    seen: list[httpx.Request] = []
    ledger = _ledger()

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await DeepSeekQuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
        ).classify(safe, catalog)

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
    assert str(request.url) == "https://api.deepseek.com/chat/completions"
    assert request.headers["Accept-Encoding"] == "identity"
    assert json.loads(request.content) == {
        "model": "deepseek-v4-flash",
        "messages": list(
            build_classifier_messages(
                safe,
                catalog,
                max_input_chars=1024,
            )
        ),
        "response_format": {"type": "json_object"},
        "thinking": {"type": "disabled"},
        "temperature": 0,
        "max_tokens": 128,
        "n": 1,
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
    assert ledger.actual_cost_usd == estimate_deepseek_cost_usd(TokenUsage(20, 5, 10))


@pytest.mark.asyncio
async def test_injected_client_base_cannot_redirect_the_exact_provider_endpoint() -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return _provider_response()

    async with httpx.AsyncClient(
        base_url="https://wrong-provider.example.invalid",
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await DeepSeekQuestionClassifier(
            settings=settings,
            client=client,
            ledger=_ledger(),
        ).classify(_question(), _catalog())

    assert decision is not None
    assert seen_urls == ["https://api.deepseek.com/chat/completions"]


@pytest.mark.asyncio
async def test_real_redaction_flow_sends_only_masked_safe_question() -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)
    raw_email = "test@example.invalid"
    raw = f"메일 {raw_email} FAQ 확인"
    redaction = redact_question(raw)
    safe = SafeQuestion(redaction)
    seen_bodies: list[str] = []

    assert redaction.masked_text == "메일 [이메일] FAQ 확인"

    def handler(request: httpx.Request) -> httpx.Response:
        seen_bodies.append(request.content.decode("utf-8"))
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await DeepSeekQuestionClassifier(
            settings=settings,
            client=client,
            ledger=_ledger(),
        ).classify(safe, _catalog())

    assert decision is not None
    assert len(seen_bodies) == 1
    assert raw_email not in seen_bodies[0]
    assert "[이메일]" in seen_bodies[0]


@pytest.mark.asyncio
async def test_multibyte_byte_and_framing_overflow_is_rejected_before_reservation() -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)
    safe = _question()
    catalog = _catalog(coverage_label="가" * 3800)
    messages = build_classifier_messages(
        safe,
        catalog,
        max_input_chars=settings.max_input_chars,
    )
    request_utf8_bytes = sum(
        len(message["role"].encode("utf-8")) + len(message["content"].encode("utf-8"))
        for message in messages
    )
    calls = 0
    ledger = _ledger()

    assert estimate_classifier_input_upper_bound(messages) <= settings.max_input_usage_tokens
    assert request_utf8_bytes <= settings.max_input_usage_tokens
    assert request_utf8_bytes + 4096 > settings.max_input_usage_tokens

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await DeepSeekQuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
        ).classify(safe, catalog)

    assert decision is None
    assert calls == 0
    assert ledger.classifier_attempts_used == 0
    assert ledger.actual_cost_usd == Decimal("0")


@pytest.mark.asyncio
async def test_approved_twenty_topic_prompt_remains_within_byte_and_framing_bound(
    governed_catalog_20: TopicCatalog,
) -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)
    safe = _question(("How do I get general public service guidance? " * 10)[:256])
    messages = build_classifier_messages(
        safe,
        governed_catalog_20,
        max_input_chars=settings.max_input_chars,
    )
    request_utf8_bytes = sum(
        len(message["role"].encode("utf-8")) + len(message["content"].encode("utf-8"))
        for message in messages
    )
    calls = 0
    ledger = _ledger()

    assert request_utf8_bytes + 4096 <= settings.max_input_usage_tokens

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await DeepSeekQuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
        ).classify(safe, governed_catalog_20)

    assert decision is not None
    assert calls == 1
    assert ledger.classifier_attempts_used == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "expected_stage", "decision_expected"),
    [
        (httpx.Response(429), ClassifierResponseStage.HTTP_REJECTED, False),
        (
            httpx.Response(200, stream=httpx.ByteStream(b"not-json")),
            ClassifierResponseStage.ENVELOPE_REJECTED,
            False,
        ),
        (
            _envelope_response([]),
            ClassifierResponseStage.ENVELOPE_REJECTED,
            False,
        ),
        (
            _provider_response(include_usage=False),
            ClassifierResponseStage.USAGE_REJECTED,
            False,
        ),
        (
            _provider_response(
                usage={
                    "prompt_tokens": 20,
                    "completion_tokens": 10,
                    "total_tokens": 30,
                    "prompt_cache_hit_tokens": 20,
                }
            ),
            ClassifierResponseStage.USAGE_REJECTED,
            False,
        ),
        (
            _provider_response(choices=[]),
            ClassifierResponseStage.CHOICE_REJECTED,
            False,
        ),
        (
            _provider_response(
                choices=[
                    {"finish_reason": "stop", "message": {"content": "{}"}},
                    {"finish_reason": "stop", "message": {"content": "{}"}},
                ]
            ),
            ClassifierResponseStage.CHOICE_REJECTED,
            False,
        ),
        (
            _provider_response(choices=[[]]),
            ClassifierResponseStage.CHOICE_REJECTED,
            False,
        ),
        (
            _provider_response(finish_reason="length"),
            ClassifierResponseStage.FINISH_REASON_REJECTED,
            False,
        ),
        (
            _provider_response(choices=[{"finish_reason": "stop", "message": []}]),
            ClassifierResponseStage.MESSAGE_REJECTED,
            False,
        ),
        (
            _provider_response(content=[]),
            ClassifierResponseStage.CONTENT_REJECTED,
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
            ClassifierResponseStage.ROUTE_ENUM_REJECTED,
            False,
        ),
        (
            _provider_response(
                content=(
                    '{"route":"CIVIC_SCOPE_GAP","intent":"LOCAL_TAX_GENERAL",'
                    '"topic_id":"NONE","coverage_id":"NONE","pending_slot":"NONE"}'
                )
            ),
            ClassifierResponseStage.ROUTE_SHAPE_REJECTED,
            False,
        ),
        (
            _provider_response(
                content=(
                    '{"route":"SUPPORTED","intent":"BULKY_WASTE",'
                    '"topic_id":"KB-WASTE-01","coverage_id":"WRONG_COVERAGE",'
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
async def test_response_emits_one_value_free_terminal_stage(
    response: httpx.Response,
    expected_stage: ClassifierResponseStage,
    decision_expected: bool,
) -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)
    observed: list[ClassifierResponseStage] = []

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(lambda _request: response),
    ) as client:
        decision = await DeepSeekQuestionClassifier(
            settings=settings,
            client=client,
            ledger=_ledger(),
            response_stage_observer=observed.append,
        ).classify(_question(), _catalog())

    assert (decision is not None) is decision_expected
    assert observed == [expected_stage]
    assert all(type(stage) is ClassifierResponseStage for stage in observed)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    (
        b'{"choices":[],"choices":[],"usage":{"prompt_tokens":0,'
        b'"completion_tokens":0,"total_tokens":0}}',
        b'{"choices":[],"usage":{"prompt_tokens":0,"prompt_tokens":0,'
        b'"completion_tokens":0,"total_tokens":0}}',
        b'{"choices":[{"finish_reason":"stop","message":{"content":"{}",'
        b'"content":"{}"}}],"usage":{"prompt_tokens":0,'
        b'"completion_tokens":0,"total_tokens":0}}',
    ),
    ids=("duplicate-envelope", "duplicate-usage", "duplicate-nested-message"),
)
async def test_duplicate_deepseek_envelope_keys_fail_before_usage_or_decision(
    body: bytes,
) -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)
    stages: list[ClassifierResponseStage] = []
    observations: list[DeepSeekResponseObservation] = []
    ledger = _ledger()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(200, stream=httpx.ByteStream(body))
        ),
    ) as client:
        decision = await DeepSeekQuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
            response_stage_observer=stages.append,
            response_observer=observations.append,
        ).classify(_question(), _catalog())

    assert decision is None
    assert stages == [ClassifierResponseStage.ENVELOPE_REJECTED]
    assert len(observations) == 1
    assert observations[0].http_2xx is True
    assert observations[0].usage is None
    assert ledger.actual_cost_usd == DEEPSEEK_WORST_CASE_USD


@pytest.mark.asyncio
async def test_streaming_response_cap_rejects_cap_plus_one_without_reading_tail() -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)
    stream = _ChunkedResponseStream(
        (
            b"{" + (b" " * 65534),
            b"x",
            b"synthetic-provider-body-marker-must-not-be-read",
        )
    )
    stages: list[ClassifierResponseStage] = []
    observations: list[DeepSeekResponseObservation] = []
    ledger = _ledger()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(lambda _request: httpx.Response(200, stream=stream)),
    ) as client:
        decision = await DeepSeekQuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
            response_stage_observer=stages.append,
            response_observer=observations.append,
        ).classify(_question(), _catalog())

    assert decision is None
    assert stream.yielded == 2
    assert stream.closed is True
    assert stages == [ClassifierResponseStage.ENVELOPE_REJECTED]
    assert len(observations) == 1
    assert observations[0].http_2xx is True
    assert observations[0].usage is None
    assert ledger.actual_cost_usd == DEEPSEEK_WORST_CASE_USD


@pytest.mark.asyncio
async def test_compressed_response_is_rejected_before_decoding_or_body_read(
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)
    expanded = b'{"synthetic-provider-body-marker":"' + (b"x" * 70000) + b'"}'
    compressed = gzip.compress(expanded)
    stream = _ChunkedResponseStream(
        (
            compressed,
            b"synthetic-provider-body-tail-must-not-be-read",
        )
    )
    calls = 0
    accept_encodings: list[str] = []
    stages: list[ClassifierResponseStage] = []
    observations: list[DeepSeekResponseObservation] = []
    ledger = _ledger()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        accept_encodings.append(request.headers["Accept-Encoding"])
        return httpx.Response(
            200,
            headers={"Content-Encoding": "gzip"},
            stream=stream,
        )

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        classifier = DeepSeekQuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
            response_stage_observer=stages.append,
            response_observer=observations.append,
        )
        decision = await classifier.classify(_question(), _catalog())

    assert decision is None
    assert calls == 1
    assert accept_encodings == ["identity"]
    assert stream.yielded == 0
    assert stream.closed is True
    assert stages == [ClassifierResponseStage.ENVELOPE_REJECTED]
    assert observations == [DeepSeekResponseObservation(http_2xx=True, usage=None)]
    assert ledger.classifier_attempts_used == 1
    assert ledger.actual_cost_usd == DEEPSEEK_WORST_CASE_USD
    exposed = caplog.text + repr(classifier)
    assert "synthetic-provider-body-marker" not in exposed
    assert "synthetic-provider-body-tail-must-not-be-read" not in exposed


@pytest.mark.asyncio
async def test_complete_exchange_has_strict_wall_clock_not_slow_drip_timeout() -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)
    object.__setattr__(settings, "timeout_seconds", 0.01)
    response_body = json.dumps(
        {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": (
                            '{"route":"CIVIC_SCOPE_GAP","intent":"NONE",'
                            '"topic_id":"NONE","coverage_id":"NONE",'
                            '"pending_slot":"NONE"}'
                        ),
                    },
                }
            ],
            "usage": _usage(),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    stream = _ChunkedResponseStream(
        (response_body,),
        delay_seconds=0.05,
    )
    calls = 0
    ledger = _ledger()
    observations: list[DeepSeekResponseObservation] = []

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, stream=stream)

    started = time.monotonic()
    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
        timeout=None,
    ) as client:
        decision = await DeepSeekQuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
            response_observer=observations.append,
        ).classify(_question(), _catalog())
    elapsed = time.monotonic() - started

    assert decision is None
    assert calls == 1
    assert elapsed < 0.04
    assert len(observations) == 1
    assert observations[0].http_2xx is True
    assert observations[0].usage is None
    assert ledger.classifier_attempts_used == 1
    assert ledger.actual_cost_usd == DEEPSEEK_WORST_CASE_USD


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_kind", ["timeout", "http", "invalid-usage"])
async def test_reserved_transport_or_usage_failure_charges_one_worst_case(
    failure_kind: str,
) -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)
    calls = 0
    ledger = _ledger()

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if failure_kind == "timeout":
            raise httpx.ReadTimeout("VALUE_FREE_TIMEOUT", request=request)
        if failure_kind == "http":
            return httpx.Response(503)
        return _provider_response(usage={"prompt_tokens": -1})

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        decision = await DeepSeekQuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
        ).classify(_question(), _catalog())

    assert decision is None
    assert calls == 1
    assert ledger.classifier_attempts_used == 1
    assert ledger.actual_cost_usd == DEEPSEEK_WORST_CASE_USD


@pytest.mark.asyncio
async def test_attempt_cap_blocks_second_transport_without_provider_cascade() -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)
    calls = 0
    ledger = _ledger(classifier_cap=1)

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _provider_response()

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        classifier = DeepSeekQuestionClassifier(
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
async def test_worst_case_cost_cap_blocks_second_transport() -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)
    calls = 0
    ledger = _ledger(cost_cap_usd=DEEPSEEK_WORST_CASE_USD)

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _provider_response(usage={"prompt_tokens": -1})

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        classifier = DeepSeekQuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
        )
        first = await classifier.classify(_question(), _catalog())
        second = await classifier.classify(_question(), _catalog())

    assert first is None
    assert second is None
    assert calls == 1
    assert ledger.classifier_attempts_used == 1
    assert ledger.actual_cost_usd == DEEPSEEK_WORST_CASE_USD


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("question", "catalog"),
    [
        (object(), _catalog()),
        (_question(), object()),
        (_forged_oversized_safe_question(), _catalog()),
        (_question(), _catalog(0)),
        (_question(), _catalog(21)),
        (_question(), _catalog(coverage_label="가" * 17000)),
    ],
    ids=[
        "invalid-safe-question-type",
        "invalid-catalog-type",
        "oversized-safe-question",
        "empty-catalog",
        "catalog-over-20",
        "oversized-complete-message",
    ],
)
async def test_invalid_typed_or_bounded_input_uses_zero_calls_and_reservations(
    question: object,
    catalog: object,
) -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)
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
        decision = await DeepSeekQuestionClassifier(
            settings=settings,
            client=client,
            ledger=ledger,
        ).classify(
            question,  # type: ignore[arg-type]
            catalog,  # type: ignore[arg-type]
        )

    assert decision is None
    assert calls == 0
    assert ledger.classifier_attempts_used == 0
    assert ledger.actual_cost_usd == Decimal("0")


@pytest.mark.asyncio
async def test_failure_does_not_expose_or_retain_question_body_value_exception_key_or_dsn(
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)
    raw_question = "민감질문-보관금지"
    invalid_value = "INVALID-VALUE-MUST-NOT-BE-RETAINED"
    exception_detail = f"{raw_question}|{invalid_value}|{SECRET}|{DSN_SENTINEL}"

    def handler(_request: httpx.Request) -> httpx.Response:
        raise RuntimeError(exception_detail)

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        classifier = DeepSeekQuestionClassifier(
            settings=settings,
            client=client,
            ledger=_ledger(),
        )
        decision = await classifier.classify(_question(raw_question), _catalog())

    assert decision is None
    exposed = caplog.text + repr(classifier)
    for forbidden in (
        raw_question,
        invalid_value,
        exception_detail,
        SECRET,
        DSN_SENTINEL,
    ):
        assert forbidden not in exposed
    assert not hasattr(classifier, "__dict__")


@pytest.mark.asyncio
async def test_observer_failure_cannot_change_an_accepted_decision() -> None:
    settings = DeepSeekClassifierSettings(api_key=SECRET)

    def failing_observer(_stage: ClassifierResponseStage) -> None:
        raise RuntimeError("OBSERVER-DETAIL-MUST-NOT-ESCAPE")

    def failing_response_observer(_observation: object) -> None:
        raise RuntimeError("RESPONSE-OBSERVER-DETAIL-MUST-NOT-ESCAPE")

    async with httpx.AsyncClient(
        base_url=settings.base_url,
        transport=httpx.MockTransport(lambda _request: _provider_response()),
    ) as client:
        decision = await DeepSeekQuestionClassifier(
            settings=settings,
            client=client,
            ledger=_ledger(),
            response_stage_observer=failing_observer,
            response_observer=failing_response_observer,
        ).classify(_question(), _catalog())

    assert decision is not None
    assert decision.route is ClassifierRoute.CIVIC_SCOPE_GAP
