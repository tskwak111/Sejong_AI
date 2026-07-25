"""One-attempt Upstage transport boundary for grounded citizen chat."""

from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import ValidationError

from sejong_ai_api.llm.chat_contracts import (
    GeneratedChatDraft,
    GroundedAnswerGenerator,
    GroundedChatOutcomeCode,
    GroundedChatRequest,
    GroundedChatResult,
)
from sejong_ai_api.llm.chat_prompt import (
    build_grounded_chat_messages,
    estimate_grounded_input_upper_bound,
)
from sejong_ai_api.llm.limits import AttemptBudget, AttemptCapReached
from sejong_ai_api.llm.settings import (
    UPSTAGE_BASE_URL,
    UPSTAGE_CHAT_TIMEOUT_SECONDS,
    UPSTAGE_MAX_OUTPUT_TOKENS,
    UPSTAGE_MODEL,
    UpstageChatSettings,
)

_CHAT_COMPLETIONS_PATH = "/chat/completions"


def create_upstage_chat_client(settings: UpstageChatSettings) -> httpx.AsyncClient:
    """Create the exact no-hidden-retry client for local grounded chat."""
    if type(settings) is not UpstageChatSettings:
        raise ValueError("UPSTAGE_CHAT_SETTINGS_INVALID")
    timeout = httpx.Timeout(
        UPSTAGE_CHAT_TIMEOUT_SECONDS,
        connect=5.0,
        read=8.0,
        write=8.0,
        pool=8.0,
    )
    transport = httpx.AsyncHTTPTransport(retries=0)
    return httpx.AsyncClient(
        base_url=UPSTAGE_BASE_URL,
        headers={
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        },
        timeout=timeout,
        transport=transport,
    )


class UpstageChatGenerator:
    def __init__(
        self,
        *,
        settings: UpstageChatSettings,
        client: httpx.AsyncClient,
        budget: AttemptBudget,
    ) -> None:
        if type(settings) is not UpstageChatSettings:
            raise ValueError("UPSTAGE_CHAT_SETTINGS_INVALID")
        if not isinstance(client, httpx.AsyncClient):
            raise ValueError("UPSTAGE_CHAT_CLIENT_INVALID")
        if type(budget) is not AttemptBudget:
            raise ValueError("ATTEMPT_BUDGET_INVALID")
        self._settings = settings
        self._client = client
        self._budget = budget

    async def generate(self, request: GroundedChatRequest) -> GroundedChatResult:
        try:
            messages = build_grounded_chat_messages(request)
        except (AttributeError, TypeError, ValueError):
            return _failure(GroundedChatOutcomeCode.SCHEMA_INVALID)
        if estimate_grounded_input_upper_bound(messages) > self._settings.max_input_tokens:
            return _failure(GroundedChatOutcomeCode.INPUT_LIMIT)

        payload = {
            "model": UPSTAGE_MODEL,
            "messages": list(messages),
            "stream": False,
            "temperature": 0.1,
            "max_tokens": UPSTAGE_MAX_OUTPUT_TOKENS,
        }
        try:
            async with self._budget.reserve():
                response = await self._client.post(
                    _CHAT_COMPLETIONS_PATH,
                    json=payload,
                )
        except AttemptCapReached:
            return _failure(GroundedChatOutcomeCode.ATTEMPT_CAP)
        except httpx.TimeoutException:
            return _failure(GroundedChatOutcomeCode.TIMEOUT)
        except httpx.TransportError:
            return _failure(GroundedChatOutcomeCode.TRANSPORT)
        except Exception:
            # Provider/transport failures cross this boundary only as a content-free enum.
            # Cancellation and other BaseException subclasses intentionally remain unhandled.
            return _failure(GroundedChatOutcomeCode.TRANSPORT)
        return _parse_response(response, max_input_tokens=self._settings.max_input_tokens)


@dataclass(frozen=True, slots=True)
class GroundedChatRuntime:
    generator: GroundedAnswerGenerator
    client: httpx.AsyncClient

    async def aclose(self) -> None:
        await self.client.aclose()


def build_upstage_chat_runtime(settings: UpstageChatSettings) -> GroundedChatRuntime:
    """Build one process-scoped generator, attempt budget and owned client."""
    if type(settings) is not UpstageChatSettings:
        raise ValueError("UPSTAGE_CHAT_SETTINGS_INVALID")
    client = create_upstage_chat_client(settings)
    generator = UpstageChatGenerator(
        settings=settings,
        client=client,
        budget=AttemptBudget(
            cap=settings.run_attempt_cap,
            concurrency=settings.max_concurrency,
        ),
    )
    return GroundedChatRuntime(generator=generator, client=client)


def _parse_response(
    response: httpx.Response,
    *,
    max_input_tokens: int,
) -> GroundedChatResult:
    status_code = response.status_code
    if status_code in (401, 403):
        return _failure(GroundedChatOutcomeCode.AUTH)
    if status_code == 429:
        return _failure(GroundedChatOutcomeCode.RATE_LIMIT)
    if status_code < 200 or status_code >= 300:
        return _failure(GroundedChatOutcomeCode.HTTP_ERROR)

    try:
        envelope = response.json()
    except (TypeError, ValueError):
        return _failure(GroundedChatOutcomeCode.SCHEMA_INVALID)
    if type(envelope) is not dict:
        return _failure(GroundedChatOutcomeCode.SCHEMA_INVALID)

    reported_input_tokens = _reported_input_tokens(envelope.get("usage"))
    if reported_input_tokens is None:
        return _failure(GroundedChatOutcomeCode.SCHEMA_INVALID)
    if reported_input_tokens > max_input_tokens:
        return _failure(GroundedChatOutcomeCode.INPUT_LIMIT)

    choice = _first_choice(envelope.get("choices"))
    if choice is None:
        return _failure(GroundedChatOutcomeCode.SCHEMA_INVALID)
    if choice.get("finish_reason") != "stop":
        return _failure(GroundedChatOutcomeCode.TRUNCATED)

    message = choice.get("message")
    if type(message) is not dict:
        return _failure(GroundedChatOutcomeCode.SCHEMA_INVALID)
    content = message.get("content")
    if type(content) is not str:
        return _failure(GroundedChatOutcomeCode.SCHEMA_INVALID)
    if not content.strip():
        return _failure(GroundedChatOutcomeCode.EMPTY)

    try:
        draft = GeneratedChatDraft.model_validate_json(content)
    except (ValidationError, ValueError):
        return _failure(GroundedChatOutcomeCode.SCHEMA_INVALID)
    return GroundedChatResult(
        code=GroundedChatOutcomeCode.SUCCESS,
        draft=draft,
    )


def _first_choice(value: object) -> dict[str, Any] | None:
    if type(value) is not list or not value:
        return None
    choice = value[0]
    return choice if type(choice) is dict else None


def _reported_input_tokens(value: object) -> int | None:
    if type(value) is not dict:
        return None
    prompt_tokens = value.get("prompt_tokens")
    return prompt_tokens if type(prompt_tokens) is int and prompt_tokens >= 0 else None


def _failure(code: GroundedChatOutcomeCode) -> GroundedChatResult:
    return GroundedChatResult(code=code)
