import asyncio

import pytest

from sejong_ai_api.llm.limits import (
    AttemptBudget,
    AttemptCapReached,
    ProviderAttemptLedger,
)


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


@pytest.mark.asyncio
async def test_provider_ledger_enforces_lane_and_combined_caps_atomically() -> None:
    ledger = ProviderAttemptLedger(
        classifier_cap=2,
        generator_cap=2,
        combined_cap=3,
    )

    async with ledger.reserve_classifier() as first:
        assert first == 1
    async with ledger.reserve_generator() as first:
        assert first == 1
    async with ledger.reserve_classifier() as second:
        assert second == 2

    with pytest.raises(AttemptCapReached, match="ATTEMPT_CAP_REACHED"):
        async with ledger.reserve_generator():
            raise AssertionError("combined cap must block the reservation")

    assert ledger.classifier_attempts_used == 2
    assert ledger.generator_attempts_used == 1
    assert ledger.combined_attempts_used == 3


@pytest.mark.asyncio
async def test_provider_ledger_serializes_classifier_and_generator_lanes() -> None:
    ledger = ProviderAttemptLedger(
        classifier_cap=1,
        generator_cap=1,
        combined_cap=2,
    )
    classifier_entered = asyncio.Event()
    release_classifier = asyncio.Event()
    generator_entered = asyncio.Event()

    async def classifier() -> None:
        async with ledger.reserve_classifier():
            classifier_entered.set()
            await release_classifier.wait()

    async def generator() -> None:
        await classifier_entered.wait()
        async with ledger.reserve_generator():
            generator_entered.set()

    classifier_task = asyncio.create_task(classifier())
    generator_task = asyncio.create_task(generator())
    await classifier_entered.wait()
    await asyncio.sleep(0)

    assert generator_entered.is_set() is False
    release_classifier.set()
    await asyncio.gather(classifier_task, generator_task)
    assert generator_entered.is_set() is True


def test_provider_ledger_has_no_reset_and_rejects_invalid_caps() -> None:
    ledger = ProviderAttemptLedger(
        classifier_cap=20,
        generator_cap=30,
        combined_cap=40,
    )
    assert not hasattr(ledger, "reset")

    for caps in (
        (0, 30, 40),
        (20, 0, 40),
        (20, 30, 0),
        (20, 30, 51),
        (True, 30, 40),
    ):
        with pytest.raises(ValueError, match="PROVIDER_ATTEMPT_LEDGER_INVALID"):
            ProviderAttemptLedger(
                classifier_cap=caps[0],
                generator_cap=caps[1],
                combined_cap=caps[2],
            )
