import asyncio

import pytest

from sejong_ai_api.llm.limits import AttemptBudget, AttemptCapReached


@pytest.mark.asyncio
async def test_attempt_31_is_blocked_before_transport() -> None:
    budget = AttemptBudget(cap=30, concurrency=1)

    for expected in range(1, 31):
        async with budget.reserve() as actual:
            assert actual == expected

    with pytest.raises(AttemptCapReached, match="ATTEMPT_CAP_REACHED"):
        async with budget.reserve():
            raise AssertionError("reservation must not succeed")

    assert budget.attempts_used == 30


@pytest.mark.asyncio
async def test_attempt_budget_serializes_reservations() -> None:
    budget = AttemptBudget(cap=2, concurrency=1)
    first_entered = asyncio.Event()
    release_first = asyncio.Event()
    second_entered = asyncio.Event()

    async def first() -> None:
        async with budget.reserve():
            first_entered.set()
            await release_first.wait()

    async def second() -> None:
        await first_entered.wait()
        async with budget.reserve():
            second_entered.set()

    first_task = asyncio.create_task(first())
    second_task = asyncio.create_task(second())
    await first_entered.wait()
    await asyncio.sleep(0)

    assert not second_entered.is_set()

    release_first.set()
    await asyncio.gather(first_task, second_task)
    assert second_entered.is_set()
    assert budget.attempts_used == 2


def test_attempt_budget_rejects_invalid_limits() -> None:
    for cap, concurrency in (
        (0, 1),
        (-1, 1),
        (1, 0),
        (1, -1),
        (1, 2),
        (True, 1),
        (1, True),
    ):
        with pytest.raises(ValueError, match="ATTEMPT_BUDGET_INVALID"):
            AttemptBudget(cap=cap, concurrency=concurrency)


def test_attempt_count_is_read_only() -> None:
    budget = AttemptBudget(cap=30, concurrency=1)
    with pytest.raises(AttributeError):
        budget.attempts_used = 1  # type: ignore[misc]
