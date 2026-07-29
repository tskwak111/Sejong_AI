"""One-attempt DeepSeek transport for source-free question classification."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.topic_catalog import TopicCatalog
from sejong_ai_api.llm.classifier_contracts import (
    ClassifierDecision,
    parse_classifier_wire_decision_with_stage,
)
from sejong_ai_api.llm.classifier_diagnostics import ClassifierResponseStage
from sejong_ai_api.llm.classifier_prompt import build_classifier_messages
from sejong_ai_api.llm.contracts import TokenUsage
from sejong_ai_api.llm.deepseek_settings import DeepSeekClassifierSettings
from sejong_ai_api.llm.deepseek_usage import parse_deepseek_token_usage
from sejong_ai_api.llm.limits import (
    AttemptCapReached,
    ProviderAttemptLedger,
    ProviderCostReservation,
)
from sejong_ai_api.llm.strict_json import load_strict_json_bytes

_CHAT_COMPLETIONS_PATH = "/chat/completions"
# UTF-8 byte fallback bounds role/content at no more than one token per byte. An additional
# 4,096-token allowance is intentionally generous for provider chat framing and special tokens,
# while leaving the approved roughly 6.5-KiB 20-topic request well inside the 16,384-token cap.
_DEEPSEEK_CHAT_FRAMING_SPECIAL_TOKEN_MARGIN = 4096
_DEEPSEEK_RESPONSE_MAX_BYTES = (64 * 1024) - 1
_DEEPSEEK_RESPONSE_STREAM_CHUNK_BYTES = 4096
ResponseStageObserver = Callable[[ClassifierResponseStage], None]


class _ClassifierResponseRejected(RuntimeError):
    """Value-free control flow for a reserved provider response failure."""


class _ClassifierResponseTooLarge(RuntimeError):
    """Value-free control flow for a response crossing the fixed byte cap."""


@dataclass(frozen=True, slots=True)
class DeepSeekResponseObservation:
    """Only aggregate-safe HTTP class and validated usage cross this boundary."""

    http_2xx: bool
    usage: TokenUsage | None

    def __post_init__(self) -> None:
        if type(self.http_2xx) is not bool or (
            self.usage is not None and type(self.usage) is not TokenUsage
        ):
            raise ValueError("DEEPSEEK_RESPONSE_OBSERVATION_INVALID")


ResponseObserver = Callable[[DeepSeekResponseObservation], None]


@dataclass(frozen=True, slots=True)
class _ClassifierResponseResult:
    decision: ClassifierDecision | None
    stage: ClassifierResponseStage
    usage: TokenUsage | None = None


def create_deepseek_classifier_client(
    settings: DeepSeekClassifierSettings,
) -> httpx.AsyncClient:
    """Create the exact no-retry client for the approved DeepSeek profile."""

    if type(settings) is not DeepSeekClassifierSettings:
        raise ValueError("DEEPSEEK_CLASSIFIER_SETTINGS_INVALID")
    timeout = httpx.Timeout(
        settings.timeout_seconds,
        connect=settings.connect_timeout_seconds,
        read=settings.timeout_seconds,
        write=settings.connect_timeout_seconds,
        pool=settings.connect_timeout_seconds,
    )
    return httpx.AsyncClient(
        base_url=settings.base_url,
        headers={
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        },
        timeout=timeout,
        transport=httpx.AsyncHTTPTransport(retries=0),
    )


class DeepSeekQuestionClassifier:
    """Return one server-validated decision, or ``None`` on every failure."""

    __slots__ = (
        "_chat_completions_url",
        "_client",
        "_ledger",
        "_max_input_chars",
        "_max_input_usage_tokens",
        "_max_output_tokens",
        "_model",
        "_response_observer",
        "_response_stage_observer",
        "_timeout_seconds",
    )

    def __init__(
        self,
        *,
        settings: DeepSeekClassifierSettings,
        client: httpx.AsyncClient,
        ledger: ProviderAttemptLedger,
        response_stage_observer: ResponseStageObserver | None = None,
        response_observer: ResponseObserver | None = None,
    ) -> None:
        if type(settings) is not DeepSeekClassifierSettings:
            raise ValueError("DEEPSEEK_CLASSIFIER_SETTINGS_INVALID")
        if not isinstance(client, httpx.AsyncClient):
            raise ValueError("DEEPSEEK_CLASSIFIER_CLIENT_INVALID")
        if type(ledger) is not ProviderAttemptLedger:
            raise ValueError("PROVIDER_ATTEMPT_LEDGER_INVALID")
        if response_stage_observer is not None and not callable(response_stage_observer):
            raise ValueError("CLASSIFIER_RESPONSE_STAGE_OBSERVER_INVALID")
        if response_observer is not None and not callable(response_observer):
            raise ValueError("DEEPSEEK_RESPONSE_OBSERVER_INVALID")
        self._chat_completions_url = f"{settings.base_url}{_CHAT_COMPLETIONS_PATH}"
        self._client = client
        self._ledger = ledger
        self._max_input_chars = settings.max_input_chars
        self._max_input_usage_tokens = settings.max_input_usage_tokens
        self._max_output_tokens = settings.max_output_tokens
        self._model = settings.model
        self._response_observer = response_observer
        self._response_stage_observer = response_stage_observer
        self._timeout_seconds = settings.timeout_seconds

    async def classify(
        self,
        question: SafeQuestion,
        catalog: TopicCatalog,
    ) -> ClassifierDecision | None:
        try:
            messages = build_classifier_messages(
                question,
                catalog,
                max_input_chars=self._max_input_chars,
            )
            if (
                _estimate_deepseek_request_token_upper_bound(messages)
                > self._max_input_usage_tokens
            ):
                return None
            payload = {
                "model": self._model,
                "messages": list(messages),
                "response_format": {"type": "json_object"},
                "thinking": {"type": "disabled"},
                "temperature": 0,
                "max_tokens": self._max_output_tokens,
                "n": 1,
            }
            async with self._ledger.reserve_classifier() as reservation:
                async with asyncio.timeout(self._timeout_seconds):
                    result, observation = await self._exchange(
                        payload=payload,
                        catalog=catalog,
                        reservation=reservation,
                    )
                self._observe_response(observation)
                self._observe_response_stage(result.stage)
                if result.decision is None:
                    raise _ClassifierResponseRejected("PROVIDER_RESPONSE_REJECTED")
                return result.decision
        except (
            AttemptCapReached,
            _ClassifierResponseRejected,
            httpx.TimeoutException,
            httpx.TransportError,
            TimeoutError,
            TypeError,
            ValueError,
        ):
            return None
        except Exception:
            # No provider exception, prompt content, or response body crosses this boundary.
            return None

    async def _exchange(
        self,
        *,
        payload: dict[str, object],
        catalog: TopicCatalog,
        reservation: ProviderCostReservation,
    ) -> tuple[_ClassifierResponseResult, DeepSeekResponseObservation]:
        async with self._client.stream(
            "POST",
            self._chat_completions_url,
            json=payload,
            headers={"Accept-Encoding": "identity"},
        ) as response:
            http_2xx = 200 <= response.status_code < 300
            if not http_2xx:
                result = _ClassifierResponseResult(
                    None,
                    ClassifierResponseStage.HTTP_REJECTED,
                )
                return result, DeepSeekResponseObservation(False, None)
            if not _content_encoding_is_identity(response):
                result = _ClassifierResponseResult(
                    None,
                    ClassifierResponseStage.ENVELOPE_REJECTED,
                )
                return result, DeepSeekResponseObservation(True, None)
            try:
                response_bytes = await _read_bounded_response(response)
            except _ClassifierResponseTooLarge:
                result = _ClassifierResponseResult(
                    None,
                    ClassifierResponseStage.ENVELOPE_REJECTED,
                )
                return result, DeepSeekResponseObservation(True, None)
            except (asyncio.CancelledError, httpx.TimeoutException, httpx.TransportError):
                self._observe_response(DeepSeekResponseObservation(True, None))
                raise
            except Exception:
                self._observe_response(DeepSeekResponseObservation(True, None))
                raise
            result = _parse_response_bytes(
                response_bytes,
                catalog,
                reservation,
                max_input_tokens=self._max_input_usage_tokens,
                max_output_tokens=self._max_output_tokens,
            )
            return result, DeepSeekResponseObservation(True, result.usage)

    def _observe_response_stage(self, stage: ClassifierResponseStage) -> None:
        observer = self._response_stage_observer
        if observer is None:
            return
        try:
            observer(stage)
        except Exception:
            # Diagnostics must never change the citizen decision or fallback.
            return

    def _observe_response(self, observation: DeepSeekResponseObservation) -> None:
        observer = self._response_observer
        if observer is None:
            return
        try:
            observer(observation)
        except Exception:
            # Aggregate diagnostics must never change the citizen decision or fallback.
            return


def _estimate_deepseek_request_token_upper_bound(
    messages: tuple[dict[str, str], ...],
) -> int:
    return _DEEPSEEK_CHAT_FRAMING_SPECIAL_TOKEN_MARGIN + sum(
        len(message["role"].encode("utf-8")) + len(message["content"].encode("utf-8"))
        for message in messages
    )


async def _read_bounded_response(response: httpx.Response) -> bytes:
    payload = bytearray()
    async for chunk in response.aiter_raw(chunk_size=_DEEPSEEK_RESPONSE_STREAM_CHUNK_BYTES):
        remaining = _DEEPSEEK_RESPONSE_MAX_BYTES - len(payload)
        if len(chunk) > remaining:
            raise _ClassifierResponseTooLarge("PROVIDER_RESPONSE_TOO_LARGE")
        payload.extend(chunk)
    return bytes(payload)


def _content_encoding_is_identity(response: httpx.Response) -> bool:
    value = response.headers.get("Content-Encoding")
    return value is None or value.strip(" \t").casefold() == "identity"


def _parse_response_bytes(
    response_bytes: bytes,
    catalog: TopicCatalog,
    reservation: ProviderCostReservation,
    *,
    max_input_tokens: int,
    max_output_tokens: int,
) -> _ClassifierResponseResult:
    try:
        envelope = load_strict_json_bytes(response_bytes)
    except (UnicodeDecodeError, TypeError, ValueError):
        return _ClassifierResponseResult(None, ClassifierResponseStage.ENVELOPE_REJECTED)
    if type(envelope) is not dict:
        return _ClassifierResponseResult(None, ClassifierResponseStage.ENVELOPE_REJECTED)

    usage = parse_deepseek_token_usage(
        envelope.get("usage"),
        max_input_tokens=max_input_tokens,
        max_output_tokens=max_output_tokens,
    )
    if usage is None:
        return _ClassifierResponseResult(None, ClassifierResponseStage.USAGE_REJECTED)
    try:
        reservation.record_usage(usage)
    except Exception:
        return _ClassifierResponseResult(None, ClassifierResponseStage.USAGE_REJECTED)

    choices = envelope.get("choices")
    if type(choices) is not list or len(choices) != 1 or type(choices[0]) is not dict:
        return _ClassifierResponseResult(
            None,
            ClassifierResponseStage.CHOICE_REJECTED,
            usage,
        )
    choice = choices[0]
    if choice.get("finish_reason") != "stop":
        return _ClassifierResponseResult(
            None,
            ClassifierResponseStage.FINISH_REASON_REJECTED,
            usage,
        )
    message = choice.get("message")
    if type(message) is not dict:
        return _ClassifierResponseResult(
            None,
            ClassifierResponseStage.MESSAGE_REJECTED,
            usage,
        )
    content = message.get("content")
    if type(content) is not str or not content.strip():
        return _ClassifierResponseResult(
            None,
            ClassifierResponseStage.CONTENT_REJECTED,
            usage,
        )
    try:
        payload = content.encode("utf-8")
    except UnicodeEncodeError:
        return _ClassifierResponseResult(
            None,
            ClassifierResponseStage.CONTENT_REJECTED,
            usage,
        )

    parsed = parse_classifier_wire_decision_with_stage(payload, catalog)
    return _ClassifierResponseResult(parsed.decision, parsed.stage, usage)


__all__ = [
    "DeepSeekQuestionClassifier",
    "DeepSeekResponseObservation",
    "ResponseObserver",
    "ResponseStageObserver",
    "create_deepseek_classifier_client",
]
