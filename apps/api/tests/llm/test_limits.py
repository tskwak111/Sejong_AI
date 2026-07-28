import asyncio
from decimal import Decimal

import pytest

import sejong_ai_api.llm.limits as limits_module
from sejong_ai_api.llm.contracts import TokenUsage
from sejong_ai_api.llm.cost import estimate_cost_usd
from sejong_ai_api.llm.deepseek_usage import estimate_deepseek_cost_usd
from sejong_ai_api.llm.limits import (
    AttemptBudget,
    AttemptCapReached,
    ProviderAttemptLedger,
)

CLASSIFIER_WORST_CASE_USD = estimate_cost_usd(TokenUsage(4096, 0, 128))
GENERATOR_WORST_CASE_USD = estimate_cost_usd(TokenUsage(4096, 0, 1024))


def _provider_ledger(
    *,
    classifier_cap: int = 80,
    generator_cap: int = 100,
    combined_cap: int = 160,
    cost_cap_usd: Decimal = Decimal("0.20"),
    classifier_worst_case_usd: Decimal = CLASSIFIER_WORST_CASE_USD,
    generator_worst_case_usd: Decimal = GENERATOR_WORST_CASE_USD,
) -> ProviderAttemptLedger:
    return ProviderAttemptLedger(
        classifier_cap=classifier_cap,
        generator_cap=generator_cap,
        combined_cap=combined_cap,
        cost_cap_usd=cost_cap_usd,
        classifier_worst_case_usd=classifier_worst_case_usd,
        generator_worst_case_usd=generator_worst_case_usd,
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
    ledger = _provider_ledger(
        classifier_cap=2,
        generator_cap=2,
        combined_cap=3,
    )

    async with ledger.reserve_classifier():
        pass
    async with ledger.reserve_generator():
        pass
    async with ledger.reserve_classifier():
        pass

    with pytest.raises(AttemptCapReached, match="ATTEMPT_CAP_REACHED"):
        async with ledger.reserve_generator():
            raise AssertionError("combined cap must block the reservation")

    assert ledger.classifier_attempts_used == 2
    assert ledger.generator_attempts_used == 1
    assert ledger.combined_attempts_used == 3


@pytest.mark.asyncio
async def test_provider_ledger_serializes_classifier_and_generator_lanes() -> None:
    ledger = _provider_ledger(
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


@pytest.mark.asyncio
async def test_provider_ledger_enforces_exact_local_interactive_attempt_caps() -> None:
    classifier_ledger = _provider_ledger()
    for _ in range(80):
        async with classifier_ledger.reserve_classifier():
            pass
    with pytest.raises(AttemptCapReached, match="^ATTEMPT_CAP_REACHED$"):
        async with classifier_ledger.reserve_classifier():
            raise AssertionError("classifier attempt 81 must not be reserved")

    generator_ledger = _provider_ledger()
    for _ in range(100):
        async with generator_ledger.reserve_generator():
            pass
    with pytest.raises(AttemptCapReached, match="^ATTEMPT_CAP_REACHED$"):
        async with generator_ledger.reserve_generator():
            raise AssertionError("generator attempt 101 must not be reserved")

    combined_ledger = _provider_ledger()
    for _ in range(80):
        async with combined_ledger.reserve_classifier():
            pass
    for _ in range(80):
        async with combined_ledger.reserve_generator():
            pass
    with pytest.raises(AttemptCapReached, match="^ATTEMPT_CAP_REACHED$"):
        async with combined_ledger.reserve_generator():
            raise AssertionError("combined attempt 161 must not be reserved")

    assert classifier_ledger.classifier_attempts_used == 80
    assert generator_ledger.generator_attempts_used == 100
    assert combined_ledger.combined_attempts_used == 160
    assert getattr(limits_module, "LOCAL_INTERACTIVE_COST_CAP_USD", None) == Decimal("0.20")


@pytest.mark.asyncio
async def test_provider_ledger_charges_valid_actual_usage_exactly_once() -> None:
    ledger = _provider_ledger()
    usage = TokenUsage(20, 0, 10)

    assert ledger.actual_cost_usd == Decimal("0")
    async with ledger.reserve_classifier() as reservation:
        reservation.record_usage(usage)
        with pytest.raises(ValueError, match="^PROVIDER_USAGE_ALREADY_RECORDED$"):
            reservation.record_usage(usage)

    assert ledger.actual_cost_usd == estimate_cost_usd(usage)


@pytest.mark.asyncio
async def test_provider_ledger_uses_injected_deepseek_estimator_and_blocks_cost_cap() -> None:
    deepseek_worst_case_usd = estimate_deepseek_cost_usd(TokenUsage(1024, 0, 128))
    ledger = ProviderAttemptLedger(
        classifier_cap=2,
        generator_cap=1,
        combined_cap=2,
        cost_cap_usd=deepseek_worst_case_usd,
        classifier_worst_case_usd=deepseek_worst_case_usd,
        generator_worst_case_usd=GENERATOR_WORST_CASE_USD,
        classifier_cost_estimator=estimate_deepseek_cost_usd,
    )

    async with ledger.reserve_classifier() as reservation:
        reservation.record_usage(TokenUsage(1024, 512, 128))

    assert ledger.actual_cost_usd == deepseek_worst_case_usd
    with pytest.raises(AttemptCapReached, match="^ATTEMPT_CAP_REACHED$"):
        async with ledger.reserve_classifier():
            raise AssertionError("a second DeepSeek reservation must exceed the cost cap")


@pytest.mark.asyncio
async def test_provider_reservation_reuses_validated_actual_cost_without_reestimating() -> None:
    estimator_calls = 0

    def one_shot_estimator(_usage: TokenUsage) -> Decimal:
        nonlocal estimator_calls
        estimator_calls += 1
        if estimator_calls > 1:
            raise RuntimeError("ESTIMATOR_MUST_NOT_RUN_DURING_FINALIZE")
        return Decimal("0.001")

    ledger = ProviderAttemptLedger(
        classifier_cap=1,
        generator_cap=1,
        combined_cap=1,
        cost_cap_usd=Decimal("0.01"),
        classifier_worst_case_usd=Decimal("0.01"),
        generator_worst_case_usd=GENERATOR_WORST_CASE_USD,
        classifier_cost_estimator=one_shot_estimator,
    )

    async with ledger.reserve_classifier() as reservation:
        reservation.record_usage(TokenUsage(20, 0, 10))

    assert estimator_calls == 1
    assert ledger.actual_cost_usd == Decimal("0.001")


@pytest.mark.asyncio
async def test_provider_ledger_keeps_upstage_estimator_as_default_for_cached_usage() -> None:
    usage = TokenUsage(20, 10, 10)
    ledger = _provider_ledger(cost_cap_usd=CLASSIFIER_WORST_CASE_USD)

    async with ledger.reserve_classifier() as reservation:
        reservation.record_usage(usage)

    assert ledger.actual_cost_usd == estimate_cost_usd(usage)


@pytest.mark.asyncio
async def test_provider_reservation_accepts_exact_lane_maximum_usage() -> None:
    ledger = _provider_ledger(cost_cap_usd=CLASSIFIER_WORST_CASE_USD)
    usage = TokenUsage(4096, 0, 128)

    async with ledger.reserve_classifier() as reservation:
        reservation.record_usage(usage)

    assert ledger.actual_cost_usd == CLASSIFIER_WORST_CASE_USD
    assert ledger.actual_cost_usd <= CLASSIFIER_WORST_CASE_USD


@pytest.mark.asyncio
async def test_provider_reservation_rejects_usage_cost_above_reserved_maximum() -> None:
    ledger = _provider_ledger()

    async with ledger.reserve_classifier() as reservation:
        with pytest.raises(
            ValueError,
            match="^PROVIDER_USAGE_EXCEEDS_RESERVATION$",
        ):
            reservation.record_usage(TokenUsage(4096, 0, 129))

    assert ledger.actual_cost_usd == CLASSIFIER_WORST_CASE_USD


@pytest.mark.asyncio
async def test_provider_ledger_exact_cap_finalization_never_overshoots() -> None:
    ledger = _provider_ledger(cost_cap_usd=CLASSIFIER_WORST_CASE_USD)

    async with ledger.reserve_classifier() as reservation:
        reservation.record_usage(TokenUsage(4096, 0, 128))

    assert ledger.actual_cost_usd == CLASSIFIER_WORST_CASE_USD
    with pytest.raises(AttemptCapReached, match="^ATTEMPT_CAP_REACHED$"):
        async with ledger.reserve_classifier():
            raise AssertionError("cost cap equality must block the next reservation")
    assert ledger.actual_cost_usd <= CLASSIFIER_WORST_CASE_USD


@pytest.mark.asyncio
async def test_provider_ledger_charges_lane_worst_case_for_missing_usage() -> None:
    ledger = _provider_ledger()

    async with ledger.reserve_classifier():
        pass
    async with ledger.reserve_generator():
        pass

    assert ledger.actual_cost_usd == CLASSIFIER_WORST_CASE_USD + GENERATOR_WORST_CASE_USD


@pytest.mark.asyncio
async def test_provider_ledger_keeps_recorded_actual_when_operation_later_fails() -> None:
    ledger = _provider_ledger()
    usage = TokenUsage(20, 0, 10)

    with pytest.raises(RuntimeError, match="^VALUE_FREE_PROVIDER_FAILURE$"):
        async with ledger.reserve_classifier() as reservation:
            reservation.record_usage(usage)
            raise RuntimeError("VALUE_FREE_PROVIDER_FAILURE")

    assert ledger.actual_cost_usd == estimate_cost_usd(usage)


@pytest.mark.asyncio
async def test_provider_ledger_rejects_next_cost_before_reservation() -> None:
    ledger = _provider_ledger(cost_cap_usd=CLASSIFIER_WORST_CASE_USD)
    usage = TokenUsage(20, 0, 10)

    async with ledger.reserve_classifier() as reservation:
        reservation.record_usage(usage)

    with pytest.raises(AttemptCapReached, match="^ATTEMPT_CAP_REACHED$"):
        async with ledger.reserve_classifier():
            raise AssertionError("cost-exceeding reservation must not succeed")

    assert ledger.classifier_attempts_used == 1
    assert ledger.actual_cost_usd == estimate_cost_usd(usage)


def test_provider_ledger_has_no_reset_and_rejects_invalid_limits() -> None:
    ledger = _provider_ledger()
    assert not hasattr(ledger, "reset")

    for caps in (
        (0, 100, 160),
        (80, 0, 160),
        (80, 100, 0),
        (80, 100, 181),
        (True, 100, 160),
    ):
        with pytest.raises(ValueError, match="PROVIDER_ATTEMPT_LEDGER_INVALID"):
            _provider_ledger(
                classifier_cap=caps[0],
                generator_cap=caps[1],
                combined_cap=caps[2],
            )

    for invalid_costs in (
        (Decimal("0"), CLASSIFIER_WORST_CASE_USD, GENERATOR_WORST_CASE_USD),
        (Decimal("-1"), CLASSIFIER_WORST_CASE_USD, GENERATOR_WORST_CASE_USD),
        (Decimal("NaN"), CLASSIFIER_WORST_CASE_USD, GENERATOR_WORST_CASE_USD),
        (Decimal("0.20"), Decimal("0"), GENERATOR_WORST_CASE_USD),
        (Decimal("0.20"), CLASSIFIER_WORST_CASE_USD, Decimal("-1")),
    ):
        with pytest.raises(ValueError, match="PROVIDER_ATTEMPT_LEDGER_INVALID"):
            _provider_ledger(
                cost_cap_usd=invalid_costs[0],
                classifier_worst_case_usd=invalid_costs[1],
                generator_worst_case_usd=invalid_costs[2],
            )

    with pytest.raises(ValueError, match="PROVIDER_ATTEMPT_LEDGER_INVALID"):
        ProviderAttemptLedger(
            classifier_worst_case_usd=CLASSIFIER_WORST_CASE_USD,
            generator_worst_case_usd=GENERATOR_WORST_CASE_USD,
            cost_cap_usd=0.20,  # type: ignore[arg-type]
        )
