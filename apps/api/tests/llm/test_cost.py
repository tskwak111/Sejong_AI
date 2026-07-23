from decimal import Decimal

import pytest

from sejong_ai_api.llm.contracts import TokenUsage
from sejong_ai_api.llm.cost import estimate_cost_usd


def test_cost_uses_decimal_snapshot_and_vat() -> None:
    usage = TokenUsage(input_tokens=4096, cached_input_tokens=0, output_tokens=1024)
    assert estimate_cost_usd(usage) == Decimal("0.0405504")


def test_cost_prices_cached_input_separately() -> None:
    usage = TokenUsage(input_tokens=1_000_000, cached_input_tokens=400_000, output_tokens=1_000_000)
    assert estimate_cost_usd(usage) == Decimal("22.9680")


def test_cost_rejects_non_token_usage_value() -> None:
    with pytest.raises(ValueError, match="TOKEN_USAGE_INVALID"):
        estimate_cost_usd(object())  # type: ignore[arg-type]
