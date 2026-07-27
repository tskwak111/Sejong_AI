"""Atomic process-run attempt and concurrency limits."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import Enum


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


class _ProviderLane(Enum):
    CLASSIFIER = "CLASSIFIER"
    GENERATOR = "GENERATOR"


class ProviderAttemptLedger:
    """One non-resettable process ledger shared by classifier and generator."""

    def __init__(
        self,
        *,
        classifier_cap: int,
        generator_cap: int,
        combined_cap: int,
    ) -> None:
        if (
            type(classifier_cap) is not int
            or classifier_cap <= 0
            or type(generator_cap) is not int
            or generator_cap <= 0
            or type(combined_cap) is not int
            or combined_cap <= 0
            or combined_cap > classifier_cap + generator_cap
        ):
            raise ValueError("PROVIDER_ATTEMPT_LEDGER_INVALID")
        self._classifier_cap = classifier_cap
        self._generator_cap = generator_cap
        self._combined_cap = combined_cap
        self._classifier_attempts_used = 0
        self._generator_attempts_used = 0
        self._counter_lock = asyncio.Lock()
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

    @asynccontextmanager
    async def reserve_classifier(self) -> AsyncIterator[int]:
        async with self._reserve(_ProviderLane.CLASSIFIER) as reservation:
            yield reservation

    @asynccontextmanager
    async def reserve_generator(self) -> AsyncIterator[int]:
        async with self._reserve(_ProviderLane.GENERATOR) as reservation:
            yield reservation

    @asynccontextmanager
    async def _reserve(self, lane: _ProviderLane) -> AsyncIterator[int]:
        await self._semaphore.acquire()
        try:
            async with self._counter_lock:
                if self.combined_attempts_used >= self._combined_cap:
                    raise AttemptCapReached("ATTEMPT_CAP_REACHED")
                if lane is _ProviderLane.CLASSIFIER:
                    if self._classifier_attempts_used >= self._classifier_cap:
                        raise AttemptCapReached("ATTEMPT_CAP_REACHED")
                    self._classifier_attempts_used += 1
                    reservation = self._classifier_attempts_used
                else:
                    if self._generator_attempts_used >= self._generator_cap:
                        raise AttemptCapReached("ATTEMPT_CAP_REACHED")
                    self._generator_attempts_used += 1
                    reservation = self._generator_attempts_used
            yield reservation
        finally:
            self._semaphore.release()
