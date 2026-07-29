"""Atomic process-run attempt and concurrency limits."""

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from sejong_ai_api.llm.contracts import TokenUsage
from sejong_ai_api.llm.cost import estimate_cost_usd

LOCAL_INTERACTIVE_COST_CAP_USD = Decimal("0.20")
CostEstimator = Callable[[TokenUsage], Decimal]


class AttemptCapReached(RuntimeError):
    """Raised before transport when the process-run attempt cap is exhausted."""


class AttemptBudget:
    """A non-resettable process-run attempt counter with exact concurrency one."""

    def __init__(self, *, cap: int, concurrency: int) -> None:
        if type(cap) is not int or cap <= 0 or type(concurrency) is not int or concurrency != 1:
            raise ValueError("ATTEMPT_BUDGET_INVALID")
        self._cap = cap
        self._attempts_used = 0
        self._counter_lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(1)

    @property
    def attempts_used(self) -> int:
        return self._attempts_used

    @asynccontextmanager
    async def reserve(self) -> AsyncIterator[int]:
        await self._semaphore.acquire()
        try:
            async with self._counter_lock:
                if self._attempts_used >= self._cap:
                    raise AttemptCapReached("ATTEMPT_CAP_REACHED")
                self._attempts_used += 1
                reservation = self._attempts_used
            yield reservation
        finally:
            self._semaphore.release()


class ProviderLane(Enum):
    CLASSIFIER = "CLASSIFIER"
    GENERATOR = "GENERATOR"


@dataclass(slots=True)
class ProviderCostReservation:
    """One lane reservation finalized as actual usage or a conservative maximum."""

    lane: ProviderLane
    worst_case_usd: Decimal
    cost_estimator: CostEstimator = field(default=estimate_cost_usd, repr=False)
    _usage: TokenUsage | None = field(default=None, init=False, repr=False)
    _actual_cost_usd: Decimal | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.lane) is not ProviderLane
            or not _valid_positive_decimal(self.worst_case_usd)
            or not callable(self.cost_estimator)
        ):
            raise ValueError("PROVIDER_COST_RESERVATION_INVALID")

    def record_usage(self, usage: TokenUsage) -> None:
        if type(usage) is not TokenUsage:
            raise ValueError("TOKEN_USAGE_INVALID")
        if self._usage is not None:
            raise ValueError("PROVIDER_USAGE_ALREADY_RECORDED")
        actual_cost_usd = self._estimate_cost_usd(usage)
        if actual_cost_usd > self.worst_case_usd:
            raise ValueError("PROVIDER_USAGE_EXCEEDS_RESERVATION")
        self._usage = usage
        self._actual_cost_usd = actual_cost_usd

    def _final_cost_usd(self) -> Decimal:
        if self._actual_cost_usd is None:
            return self.worst_case_usd
        return self._actual_cost_usd

    def _estimate_cost_usd(self, usage: TokenUsage) -> Decimal:
        try:
            estimated_cost_usd = self.cost_estimator(usage)
        except Exception:
            raise ValueError("PROVIDER_COST_ESTIMATE_INVALID") from None
        if not _valid_nonnegative_decimal(estimated_cost_usd):
            raise ValueError("PROVIDER_COST_ESTIMATE_INVALID")
        return estimated_cost_usd


class ProviderAttemptLedger:
    """One non-resettable process ledger shared by classifier and generator."""

    def __init__(
        self,
        *,
        classifier_cap: int = 80,
        generator_cap: int = 100,
        combined_cap: int = 160,
        cost_cap_usd: Decimal = LOCAL_INTERACTIVE_COST_CAP_USD,
        classifier_worst_case_usd: Decimal,
        generator_worst_case_usd: Decimal,
        classifier_cost_estimator: CostEstimator = estimate_cost_usd,
        generator_cost_estimator: CostEstimator = estimate_cost_usd,
    ) -> None:
        if (
            type(classifier_cap) is not int
            or classifier_cap <= 0
            or type(generator_cap) is not int
            or generator_cap <= 0
            or type(combined_cap) is not int
            or combined_cap <= 0
            or combined_cap > classifier_cap + generator_cap
            or not _valid_positive_decimal(cost_cap_usd)
            or not _valid_positive_decimal(classifier_worst_case_usd)
            or not _valid_positive_decimal(generator_worst_case_usd)
            or not callable(classifier_cost_estimator)
            or not callable(generator_cost_estimator)
        ):
            raise ValueError("PROVIDER_ATTEMPT_LEDGER_INVALID")
        self._classifier_cap = classifier_cap
        self._generator_cap = generator_cap
        self._combined_cap = combined_cap
        self._cost_cap_usd = cost_cap_usd
        self._classifier_worst_case_usd = classifier_worst_case_usd
        self._generator_worst_case_usd = generator_worst_case_usd
        self._classifier_cost_estimator = classifier_cost_estimator
        self._generator_cost_estimator = generator_cost_estimator
        self._classifier_attempts_used = 0
        self._generator_attempts_used = 0
        self._actual_cost_usd = Decimal("0")
        self._state_lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(1)

    @property
    def classifier_attempts_used(self) -> int:
        return self._classifier_attempts_used

    @property
    def generator_attempts_used(self) -> int:
        return self._generator_attempts_used

    @property
    def combined_attempts_used(self) -> int:
        return self._classifier_attempts_used + self._generator_attempts_used

    @property
    def actual_cost_usd(self) -> Decimal:
        return self._actual_cost_usd

    @asynccontextmanager
    async def reserve_classifier(self) -> AsyncIterator[ProviderCostReservation]:
        async with self._reserve(ProviderLane.CLASSIFIER) as reservation:
            yield reservation

    @asynccontextmanager
    async def reserve_generator(self) -> AsyncIterator[ProviderCostReservation]:
        async with self._reserve(ProviderLane.GENERATOR) as reservation:
            yield reservation

    @asynccontextmanager
    async def _reserve(
        self,
        lane: ProviderLane,
    ) -> AsyncIterator[ProviderCostReservation]:
        await self._semaphore.acquire()
        try:
            worst_case_usd = (
                self._classifier_worst_case_usd
                if lane is ProviderLane.CLASSIFIER
                else self._generator_worst_case_usd
            )
            cost_estimator = (
                self._classifier_cost_estimator
                if lane is ProviderLane.CLASSIFIER
                else self._generator_cost_estimator
            )
            async with self._state_lock:
                if self.combined_attempts_used >= self._combined_cap:
                    raise AttemptCapReached("ATTEMPT_CAP_REACHED")
                if self._actual_cost_usd + worst_case_usd > self._cost_cap_usd:
                    raise AttemptCapReached("ATTEMPT_CAP_REACHED")
                if lane is ProviderLane.CLASSIFIER:
                    if self._classifier_attempts_used >= self._classifier_cap:
                        raise AttemptCapReached("ATTEMPT_CAP_REACHED")
                    self._classifier_attempts_used += 1
                else:
                    if self._generator_attempts_used >= self._generator_cap:
                        raise AttemptCapReached("ATTEMPT_CAP_REACHED")
                    self._generator_attempts_used += 1
                reservation = ProviderCostReservation(
                    lane=lane,
                    worst_case_usd=worst_case_usd,
                    cost_estimator=cost_estimator,
                )
            try:
                yield reservation
            except BaseException:
                await self._finalize(reservation)
                raise
            else:
                await self._finalize(reservation)
        finally:
            self._semaphore.release()

    async def _finalize(
        self,
        reservation: ProviderCostReservation,
    ) -> None:
        async with self._state_lock:
            self._actual_cost_usd += reservation._final_cost_usd()


def _valid_positive_decimal(value: object) -> bool:
    return type(value) is Decimal and value.is_finite() and value > Decimal("0")


def _valid_nonnegative_decimal(value: object) -> bool:
    return type(value) is Decimal and value.is_finite() and value >= Decimal("0")


def parse_provider_token_usage(
    value: object,
    *,
    max_input_tokens: int,
    max_output_tokens: int,
) -> TokenUsage | None:
    """Parse one bounded provider usage envelope without coercion."""

    if (
        type(value) is not dict
        or type(max_input_tokens) is not int
        or max_input_tokens < 0
        or type(max_output_tokens) is not int
        or max_output_tokens < 0
    ):
        return None
    prompt_tokens = value.get("prompt_tokens")
    completion_tokens = value.get("completion_tokens")
    if (
        type(prompt_tokens) is not int
        or prompt_tokens < 0
        or prompt_tokens > max_input_tokens
        or type(completion_tokens) is not int
        or completion_tokens < 0
        or completion_tokens > max_output_tokens
    ):
        return None

    if "total_tokens" in value:
        total_tokens = value["total_tokens"]
        if (
            type(total_tokens) is not int
            or total_tokens < 0
            or total_tokens != prompt_tokens + completion_tokens
        ):
            return None

    reported_cached_tokens: int | None = None
    if "cached_tokens" in value:
        cached_tokens = value["cached_tokens"]
        if type(cached_tokens) is not int or cached_tokens < 0 or cached_tokens > prompt_tokens:
            return None
        reported_cached_tokens = cached_tokens

    if "prompt_tokens_details" in value:
        details = value["prompt_tokens_details"]
        if type(details) is not dict or "cached_tokens" not in details:
            return None
        cached_tokens = details["cached_tokens"]
        if type(cached_tokens) is not int or cached_tokens < 0 or cached_tokens > prompt_tokens:
            return None
        if reported_cached_tokens is not None and reported_cached_tokens != cached_tokens:
            return None
        reported_cached_tokens = cached_tokens

    return TokenUsage(
        input_tokens=prompt_tokens,
        cached_input_tokens=(0 if reported_cached_tokens is None else reported_cached_tokens),
        output_tokens=completion_tokens,
    )
