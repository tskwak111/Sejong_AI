from decimal import Decimal

import pytest

from sejong_ai_api.llm.contracts import TokenUsage
from sejong_ai_api.llm.deepseek_usage import (
    estimate_deepseek_cost_usd,
    parse_deepseek_token_usage,
)


def test_deepseek_usage_accepts_consistent_cache_pair_and_prices_all_prompt_as_miss() -> None:
    usage = parse_deepseek_token_usage(
        {
            "prompt_tokens": 1000,
            "completion_tokens": 100,
            "total_tokens": 1100,
            "prompt_cache_hit_tokens": 250,
            "prompt_cache_miss_tokens": 750,
        },
        max_input_tokens=1024,
        max_output_tokens=128,
    )

    assert usage == TokenUsage(1000, 250, 100)
    assert estimate_deepseek_cost_usd(usage) == Decimal("0.0001848")


def test_deepseek_usage_without_cache_details_is_priced_as_all_cache_miss() -> None:
    usage = parse_deepseek_token_usage(
        {
            "prompt_tokens": 1000,
            "completion_tokens": 100,
            "total_tokens": 1100,
        },
        max_input_tokens=1024,
        max_output_tokens=128,
    )

    assert usage == TokenUsage(1000, 0, 100)
    assert estimate_deepseek_cost_usd(usage) == Decimal("0.0001848")


@pytest.mark.parametrize(
    "usage",
    (
        {"prompt_tokens": -1, "completion_tokens": 0, "total_tokens": -1},
        {"prompt_tokens": 1, "completion_tokens": -1, "total_tokens": 0},
        {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 1},
        {
            "prompt_tokens": 1,
            "completion_tokens": 0,
            "total_tokens": 1,
            "prompt_cache_hit_tokens": 1,
        },
        {
            "prompt_tokens": 1,
            "completion_tokens": 0,
            "total_tokens": 1,
            "prompt_cache_hit_tokens": 1,
            "prompt_cache_miss_tokens": 1,
        },
        {
            "prompt_tokens": 1,
            "completion_tokens": 0,
            "total_tokens": 1,
            "prompt_cache_hit_tokens": True,
            "prompt_cache_miss_tokens": 0,
        },
    ),
)
def test_deepseek_usage_rejects_negative_or_inconsistent_values(usage: object) -> None:
    assert parse_deepseek_token_usage(usage, max_input_tokens=1024, max_output_tokens=128) is None
