"""Atomic process-run attempt and concurrency limits."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum

from sejong_ai_api.llm.contracts import TokenUsage
from sejong_ai_api.llm.cost import estimate_cost_usd

LOCAL_INTERACTIVE_COST_CAP_USD = Decimal("0.20")


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
    _usage: TokenUsage | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.lane) is not ProviderLane
            or not _valid_positive_decimal(self.worst_case_usd)
        ):
            raise ValueError("PROVIDER_COST_RESERVATION_INVALID")

    def record_usage(self, usage: TokenUsage) -> None:
        if type(usage) is not TokenUsage:
            raise ValueError("TOKEN_USAGE_INVALID")
        if self._usage is not None:
            raise ValueError("PROVIDER_USAGE_ALREADY_RECORDED")
        self._usage = usage

    def _final_cost_usd(self, *, failed: bool) -> Decimal:
        if failed or self._usage is None:
            return self.worst_case_usd
        return estimate_cost_usd(self._usage)


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
        ):
            raise ValueError("PROVIDER_ATTEMPT_LEDGER_INVALID")
        self._classifier_cap = classifier_cap
        self._generator_cap = generator_cap
        self._combined_cap = combined_cap
        self._cost_cap_usd = cost_cap_usd
        self._classifier_worst_case_usd = classifier_worst_case_usd
        self._generator_worst_case_usd = generator_worst_case_usd
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
                )
            try:
                yield reservation
            except BaseException:
                await self._finalize(reservation, failed=True)
                raise
            else:
                await self._finalize(reservation, failed=False)
        finally:
            self._semaphore.release()

    async def _finalize(
        self,
        reservation: ProviderCostReservation,
        *,
        failed: bool,
    ) -> None:
        async with self._state_lock:
            self._actual_cost_usd += reservation._final_cost_usd(failed=failed)


def _valid_positive_decimal(value: object) -> bool:
    return (
        type(value) is Decimal
        and value.is_finite()
        and value > Decimal("0")
    )
