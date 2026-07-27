"""One-attempt Upstage transport for source-free question classification."""

from __future__ import annotations

from typing import Any

import httpx

from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.topic_catalog import TopicCatalog
from sejong_ai_api.llm.classifier_contracts import (
    ClassifierDecision,
    parse_classifier_decision,
)
from sejong_ai_api.llm.classifier_prompt import (
    build_classifier_messages,
    estimate_classifier_input_upper_bound,
)
from sejong_ai_api.llm.limits import AttemptCapReached, ProviderAttemptLedger
from sejong_ai_api.llm.settings import UpstageClassifierSettings

_CHAT_COMPLETIONS_PATH = "/chat/completions"
_MAX_INPUT_ESTIMATE = 4096


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
    ) -> None:
        if type(settings) is not UpstageClassifierSettings:
            raise ValueError("UPSTAGE_CLASSIFIER_SETTINGS_INVALID")
        if not isinstance(client, httpx.AsyncClient):
            raise ValueError("UPSTAGE_CLASSIFIER_CLIENT_INVALID")
        if type(ledger) is not ProviderAttemptLedger:
            raise ValueError("PROVIDER_ATTEMPT_LEDGER_INVALID")
        self._settings = settings
        self._client = client
        self._ledger = ledger

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
            if estimate_classifier_input_upper_bound(messages) > _MAX_INPUT_ESTIMATE:
                return None
            payload = {
                "model": self._settings.model,
                "messages": list(messages),
                "stream": False,
                "temperature": 0,
                "max_tokens": self._settings.max_output_tokens,
                "response_format": {"type": "json_object"},
            }
            async with self._ledger.reserve_classifier():
                response = await self._client.post(
                    _CHAT_COMPLETIONS_PATH,
                    json=payload,
                )
        except (
            AttemptCapReached,
            httpx.TimeoutException,
            httpx.TransportError,
            TypeError,
            ValueError,
        ):
            return None
        except Exception:
            # No provider exception, prompt content, or response body crosses this boundary.
            return None
        return _parse_response(response, catalog)


def _parse_response(
    response: httpx.Response,
    catalog: TopicCatalog,
) -> ClassifierDecision | None:
    if response.status_code < 200 or response.status_code >= 300:
        return None
    try:
        envelope = response.json()
    except (TypeError, ValueError):
        return None
    if type(envelope) is not dict:
        return None
    choice = _first_choice(envelope.get("choices"))
    if choice is None or choice.get("finish_reason") != "stop":
        return None
    message = choice.get("message")
    if type(message) is not dict:
        return None
    content = message.get("content")
    if type(content) is not str or not content.strip():
        return None
    try:
        return parse_classifier_decision(content.encode("utf-8"), catalog)
    except (UnicodeEncodeError, ValueError):
        return None


def _first_choice(value: object) -> dict[str, Any] | None:
    if type(value) is not list or not value:
        return None
    choice = value[0]
    return choice if type(choice) is dict else None


__all__ = ["QuestionClassifier", "create_upstage_classifier_client"]
