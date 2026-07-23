"""Bounded HTTPX transport for the approved local Upstage synthetic evaluator."""

from dataclasses import dataclass
from typing import Any

import httpx

from sejong_ai_api.llm.contracts import (
    GeneratedAnswer,
    GenerationOutcome,
    GroundedFixture,
    OutcomeCode,
    TokenUsage,
)
from sejong_ai_api.llm.limits import AttemptBudget, AttemptCapReached
from sejong_ai_api.llm.prompt import (
    build_upstage_messages,
    estimate_input_token_upper_bound,
)
from sejong_ai_api.llm.settings import (
    UPSTAGE_BASE_URL,
    UPSTAGE_MAX_OUTPUT_TOKENS,
    UPSTAGE_MAX_RETRIES,
    UPSTAGE_MODEL,
    UPSTAGE_TIMEOUT_SECONDS,
    UpstageSyntheticSettings,
)

_CHAT_COMPLETIONS_PATH = "/chat/completions"


@dataclass(frozen=True, slots=True)
class _ParsedResponse:
    code: OutcomeCode
    answer: GeneratedAnswer | None
    usage: TokenUsage
    retryable: bool


def create_upstage_client(settings: UpstageSyntheticSettings) -> httpx.AsyncClient:
    """Create the exact no-hidden-retry client for a local synthetic run."""
    if type(settings) is not UpstageSyntheticSettings:
        raise ValueError("UPSTAGE_SETTINGS_INVALID")
    timeout = httpx.Timeout(
        UPSTAGE_TIMEOUT_SECONDS,
        connect=5.0,
        read=15.0,
        write=15.0,
        pool=15.0,
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


class UpstageProvider:
    """Generate one source-free answer within the approved retry and run caps."""

    def __init__(
        self,
        *,
        settings: UpstageSyntheticSettings,
        client: httpx.AsyncClient,
        budget: AttemptBudget,
    ) -> None:
        if type(settings) is not UpstageSyntheticSettings:
            raise ValueError("UPSTAGE_SETTINGS_INVALID")
        if not isinstance(client, httpx.AsyncClient):
            raise ValueError("UPSTAGE_CLIENT_INVALID")
        if type(budget) is not AttemptBudget:
            raise ValueError("ATTEMPT_BUDGET_INVALID")
        self._settings = settings
        self._client = client
        self._budget = budget

    async def generate(self, fixture: GroundedFixture) -> GenerationOutcome:
        messages = build_upstage_messages(fixture)
        if estimate_input_token_upper_bound(messages) > self._settings.max_input_tokens:
            return _outcome(OutcomeCode.INPUT_LIMIT)

        payload = {
            "model": UPSTAGE_MODEL,
            "messages": list(messages),
            "stream": False,
            "temperature": 0.1,
            "max_tokens": UPSTAGE_MAX_OUTPUT_TOKENS,
        }
        attempts_used = 0
        total_input_tokens = 0
        total_output_tokens = 0

        for retry_index in range(UPSTAGE_MAX_RETRIES + 1):
            try:
                async with self._budget.reserve():
                    attempts_used += 1
                    response = await self._client.post(
                        _CHAT_COMPLETIONS_PATH,
                        json=payload,
                    )
            except AttemptCapReached:
                return _outcome(
                    OutcomeCode.ATTEMPT_CAP,
                    attempts_used=attempts_used,
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                )
            except httpx.TimeoutException:
                parsed = _transport_failure(OutcomeCode.TIMEOUT)
            except httpx.TransportError:
                parsed = _transport_failure(OutcomeCode.TRANSPORT)
            else:
                parsed = _parse_response(
                    response,
                    max_input_tokens=self._settings.max_input_tokens,
                )

            total_input_tokens += parsed.usage.input_tokens
            total_output_tokens += parsed.usage.output_tokens
            if parsed.code is OutcomeCode.SUCCESS:
                return _outcome(
                    OutcomeCode.SUCCESS,
                    answer=parsed.answer,
                    attempts_used=attempts_used,
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                )
            if parsed.code is OutcomeCode.INPUT_LIMIT:
                return _outcome(
                    OutcomeCode.INPUT_LIMIT,
                    attempts_used=attempts_used,
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                )
            if not parsed.retryable or retry_index == UPSTAGE_MAX_RETRIES:
                return _outcome(
                    parsed.code,
                    attempts_used=attempts_used,
                    input_tokens=total_input_tokens,
                    output_tokens=total_output_tokens,
                )

        raise AssertionError("UPSTAGE_RETRY_STATE_INVALID")


def _parse_response(
    response: httpx.Response,
    *,
    max_input_tokens: int,
) -> _ParsedResponse:
    status_code = response.status_code
    if status_code in (401, 403):
        return _failure(OutcomeCode.AUTH, retryable=False)
    if status_code == 429:
        return _failure(OutcomeCode.RATE_LIMIT, retryable=True)
    if 500 <= status_code <= 599:
        return _failure(OutcomeCode.HTTP_ERROR, retryable=True)
    if status_code < 200 or status_code >= 300:
        return _failure(OutcomeCode.HTTP_ERROR, retryable=False)

    try:
        envelope = response.json()
    except (TypeError, ValueError):
        return _failure(OutcomeCode.SCHEMA_INVALID, retryable=True)
    if type(envelope) is not dict:
        return _failure(OutcomeCode.SCHEMA_INVALID, retryable=True)

    usage = _parse_usage(envelope.get("usage"))
    if usage.input_tokens > max_input_tokens:
        return _ParsedResponse(
            code=OutcomeCode.INPUT_LIMIT,
            answer=None,
            usage=usage,
            retryable=False,
        )

    choice = _first_choice(envelope.get("choices"))
    if choice is None:
        return _failure(OutcomeCode.SCHEMA_INVALID, retryable=True, usage=usage)
    if choice.get("finish_reason") != "stop":
        return _failure(OutcomeCode.TRUNCATED, retryable=True, usage=usage)

    message = choice.get("message")
    if type(message) is not dict:
        return _failure(OutcomeCode.SCHEMA_INVALID, retryable=True, usage=usage)
    content = message.get("content")
    if type(content) is not str:
        return _failure(OutcomeCode.SCHEMA_INVALID, retryable=True, usage=usage)
    if not content.strip():
        return _failure(OutcomeCode.EMPTY, retryable=True, usage=usage)

    try:
        answer = GeneratedAnswer.model_validate_json(content)
    except ValueError:
        return _failure(OutcomeCode.SCHEMA_INVALID, retryable=True, usage=usage)
    return _ParsedResponse(
        code=OutcomeCode.SUCCESS,
        answer=answer,
        usage=usage,
        retryable=False,
    )


def _first_choice(value: object) -> dict[str, Any] | None:
    if type(value) is not list or not value:
        return None
    choice = value[0]
    return choice if type(choice) is dict else None


def _parse_usage(value: object) -> TokenUsage:
    if type(value) is not dict:
        return TokenUsage(0, 0, 0)
    return TokenUsage(
        input_tokens=_valid_token_count(value.get("prompt_tokens")),
        cached_input_tokens=0,
        output_tokens=_valid_token_count(value.get("completion_tokens")),
    )


def _valid_token_count(value: object) -> int:
    return value if type(value) is int and value >= 0 else 0


def _transport_failure(code: OutcomeCode) -> _ParsedResponse:
    return _failure(code, retryable=True)


def _failure(
    code: OutcomeCode,
    *,
    retryable: bool,
    usage: TokenUsage | None = None,
) -> _ParsedResponse:
    return _ParsedResponse(
        code=code,
        answer=None,
        usage=usage if usage is not None else TokenUsage(0, 0, 0),
        retryable=retryable,
    )


def _outcome(
    code: OutcomeCode,
    *,
    answer: GeneratedAnswer | None = None,
    attempts_used: int = 0,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> GenerationOutcome:
    return GenerationOutcome(
        code=code,
        answer=answer,
        usage=TokenUsage(
            input_tokens=input_tokens,
            cached_input_tokens=0,
            output_tokens=output_tokens,
        ),
        attempts_used=attempts_used,
    )
