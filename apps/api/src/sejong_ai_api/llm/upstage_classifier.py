"""One-attempt Upstage transport for source-free question classification."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.topic_catalog import TopicCatalog
from sejong_ai_api.llm.classifier_contracts import (
    ClassifierDecision,
    parse_classifier_decision_with_stage,
)
from sejong_ai_api.llm.classifier_diagnostics import ClassifierResponseStage
from sejong_ai_api.llm.classifier_prompt import (
    build_classifier_messages,
    estimate_classifier_input_upper_bound,
)
from sejong_ai_api.llm.limits import (
    AttemptCapReached,
    ProviderAttemptLedger,
    ProviderCostReservation,
    parse_provider_token_usage,
)
from sejong_ai_api.llm.settings import (
    UPSTAGE_MAX_INPUT_TOKENS,
    UpstageClassifierSettings,
)

_CHAT_COMPLETIONS_PATH = "/chat/completions"
ResponseStageObserver = Callable[[ClassifierResponseStage], None]


class _ClassifierResponseRejected(RuntimeError):
    """Value-free control flow for a reserved provider response failure."""


@dataclass(frozen=True, slots=True)
class _ClassifierResponseResult:
    decision: ClassifierDecision | None
    stage: ClassifierResponseStage


def create_upstage_classifier_client(
    settings: UpstageClassifierSettings,
) -> httpx.AsyncClient:
    """Create an exact no-retry client for the classifier profile."""

    if type(settings) is not UpstageClassifierSettings:
        raise ValueError("UPSTAGE_CLASSIFIER_SETTINGS_INVALID")
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


class QuestionClassifier:
    """Return a validated closed decision, or ``None`` on every provider failure."""

    def __init__(
        self,
        *,
        settings: UpstageClassifierSettings,
        client: httpx.AsyncClient,
        ledger: ProviderAttemptLedger,
        response_stage_observer: ResponseStageObserver | None = None,
    ) -> None:
        if type(settings) is not UpstageClassifierSettings:
            raise ValueError("UPSTAGE_CLASSIFIER_SETTINGS_INVALID")
        if not isinstance(client, httpx.AsyncClient):
            raise ValueError("UPSTAGE_CLASSIFIER_CLIENT_INVALID")
        if type(ledger) is not ProviderAttemptLedger:
            raise ValueError("PROVIDER_ATTEMPT_LEDGER_INVALID")
        if response_stage_observer is not None and not callable(response_stage_observer):
            raise ValueError("CLASSIFIER_RESPONSE_STAGE_OBSERVER_INVALID")
        self._settings = settings
        self._client = client
        self._ledger = ledger
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
                max_input_chars=self._settings.max_input_chars,
            )
            if estimate_classifier_input_upper_bound(messages) > UPSTAGE_MAX_INPUT_TOKENS:
                return None
            payload = {
                "model": self._settings.model,
                "messages": list(messages),
                "stream": False,
                "temperature": 0,
                "max_tokens": self._settings.max_output_tokens,
                "response_format": {"type": "json_object"},
            }
            async with self._ledger.reserve_classifier() as reservation:
                response = await self._client.post(
                    _CHAT_COMPLETIONS_PATH,
                    json=payload,
                )
                result = _parse_response(
                    response,
                    catalog,
                    reservation,
                    max_output_tokens=self._settings.max_output_tokens,
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


def _parse_response(
    response: httpx.Response,
    catalog: TopicCatalog,
    reservation: ProviderCostReservation,
    *,
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
    usage = parse_provider_token_usage(
        envelope.get("usage"),
        max_input_tokens=UPSTAGE_MAX_INPUT_TOKENS,
        max_output_tokens=max_output_tokens,
    )
    if usage is None:
        return _ClassifierResponseResult(None, ClassifierResponseStage.USAGE_REJECTED)
    try:
        reservation.record_usage(usage)
    except Exception:
        return _ClassifierResponseResult(None, ClassifierResponseStage.USAGE_REJECTED)
    choice = _first_choice(envelope.get("choices"))
    if choice is None:
        return _ClassifierResponseResult(None, ClassifierResponseStage.CHOICE_REJECTED)
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
    parsed = parse_classifier_decision_with_stage(payload, catalog)
    return _ClassifierResponseResult(parsed.decision, parsed.stage)


def _first_choice(value: object) -> dict[str, Any] | None:
    if type(value) is not list or not value:
        return None
    choice = value[0]
    return choice if type(choice) is dict else None


__all__ = [
    "QuestionClassifier",
    "ResponseStageObserver",
    "create_upstage_classifier_client",
]
