"""Atomic process-run attempt and concurrency limits."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


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
