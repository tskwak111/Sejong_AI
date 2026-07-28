"""One-attempt DeepSeek transport for source-free question classification."""

from __future__ import annotations

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
from sejong_ai_api.llm.deepseek_settings import DeepSeekClassifierSettings
from sejong_ai_api.llm.deepseek_usage import parse_deepseek_token_usage
from sejong_ai_api.llm.limits import (
    AttemptCapReached,
    ProviderAttemptLedger,
    ProviderCostReservation,
)

_CHAT_COMPLETIONS_PATH = "/chat/completions"
# UTF-8 byte fallback bounds role/content at no more than one token per byte. An additional
# 4,096-token allowance is intentionally generous for provider chat framing and special tokens,
# while leaving the approved roughly 6.5-KiB 20-topic request well inside the 16,384-token cap.
_DEEPSEEK_CHAT_FRAMING_SPECIAL_TOKEN_MARGIN = 4096
ResponseStageObserver = Callable[[ClassifierResponseStage], None]


class _ClassifierResponseRejected(RuntimeError):
    """Value-free control flow for a reserved provider response failure."""


@dataclass(frozen=True, slots=True)
class _ClassifierResponseResult:
    decision: ClassifierDecision | None
    stage: ClassifierResponseStage


def create_deepseek_classifier_client(
    settings: DeepSeekClassifierSettings,
) -> httpx.AsyncClient:
    """Create the exact no-retry client for the approved DeepSeek profile."""

    if type(settings) is not DeepSeekClassifierSettings:
        raise ValueError("DEEPSEEK_CLASSIFIER_SETTINGS_INVALID")
    timeout = httpx.Timeout(
        settings.timeout_seconds,
        connect=settings.timeout_seconds,
        read=settings.timeout_seconds,
        write=settings.timeout_seconds,
        pool=settings.timeout_seconds,
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
        "_response_stage_observer",
    )

    def __init__(
        self,
        *,
        settings: DeepSeekClassifierSettings,
        client: httpx.AsyncClient,
        ledger: ProviderAttemptLedger,
        response_stage_observer: ResponseStageObserver | None = None,
    ) -> None:
        if type(settings) is not DeepSeekClassifierSettings:
            raise ValueError("DEEPSEEK_CLASSIFIER_SETTINGS_INVALID")
        if not isinstance(client, httpx.AsyncClient):
            raise ValueError("DEEPSEEK_CLASSIFIER_CLIENT_INVALID")
        if type(ledger) is not ProviderAttemptLedger:
            raise ValueError("PROVIDER_ATTEMPT_LEDGER_INVALID")
        if response_stage_observer is not None and not callable(response_stage_observer):
            raise ValueError("CLASSIFIER_RESPONSE_STAGE_OBSERVER_INVALID")
        self._chat_completions_url = f"{settings.base_url}{_CHAT_COMPLETIONS_PATH}"
        self._client = client
        self._ledger = ledger
        self._max_input_chars = settings.max_input_chars
        self._max_input_usage_tokens = settings.max_input_usage_tokens
        self._max_output_tokens = settings.max_output_tokens
        self._model = settings.model
        self._response_stage_observer = response_stage_observer

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
                response = await self._client.post(
                    self._chat_completions_url,
                    json=payload,
                )
                result = _parse_response(
                    response,
                    catalog,
                    reservation,
                    max_input_tokens=self._max_input_usage_tokens,
                    max_output_tokens=self._max_output_tokens,
                )
                self._observe_response_stage(result.stage)
                if result.decision is None:
                    raise _ClassifierResponseRejected("PROVIDER_RESPONSE_REJECTED")
                return result.decision
        except (
            AttemptCapReached,
            _ClassifierResponseRejected,
            httpx.TimeoutException,
            httpx.TransportError,
            TypeError,
            ValueError,
        ):
            return None
        except Exception:
            # No provider exception, prompt content, or response body crosses this boundary.
            return None

    def _observe_response_stage(self, stage: ClassifierResponseStage) -> None:
        observer = self._response_stage_observer
        if observer is None:
            return
        try:
            observer(stage)
        except Exception:
            # Diagnostics must never change the citizen decision or fallback.
            return


def _estimate_deepseek_request_token_upper_bound(
    messages: tuple[dict[str, str], ...],
) -> int:
    return _DEEPSEEK_CHAT_FRAMING_SPECIAL_TOKEN_MARGIN + sum(
        len(message["role"].encode("utf-8")) + len(message["content"].encode("utf-8"))
        for message in messages
    )


def _parse_response(
    response: httpx.Response,
    catalog: TopicCatalog,
    reservation: ProviderCostReservation,
    *,
    max_input_tokens: int,
    max_output_tokens: int,
) -> _ClassifierResponseResult:
    if response.status_code < 200 or response.status_code >= 300:
        return _ClassifierResponseResult(None, ClassifierResponseStage.HTTP_REJECTED)
    try:
        envelope = response.json()
    except (TypeError, ValueError):
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
        return _ClassifierResponseResult(None, ClassifierResponseStage.CHOICE_REJECTED)
    choice = choices[0]
    if choice.get("finish_reason") != "stop":
        return _ClassifierResponseResult(None, ClassifierResponseStage.FINISH_REASON_REJECTED)
    message = choice.get("message")
    if type(message) is not dict:
        return _ClassifierResponseResult(None, ClassifierResponseStage.MESSAGE_REJECTED)
    content = message.get("content")
    if type(content) is not str or not content.strip():
        return _ClassifierResponseResult(None, ClassifierResponseStage.CONTENT_REJECTED)
    try:
        payload = content.encode("utf-8")
    except UnicodeEncodeError:
        return _ClassifierResponseResult(None, ClassifierResponseStage.CONTENT_REJECTED)

    parsed = parse_classifier_wire_decision_with_stage(payload, catalog)
    return _ClassifierResponseResult(parsed.decision, parsed.stage)


__all__ = [
    "DeepSeekQuestionClassifier",
    "ResponseStageObserver",
    "create_deepseek_classifier_client",
]
