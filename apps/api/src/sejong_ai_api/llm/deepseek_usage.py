"""Strict DeepSeek usage parsing and conservative fixed-price estimation."""

from decimal import Decimal

from sejong_ai_api.llm.contracts import TokenUsage

DEEPSEEK_PRICING_SOURCE_URL = (
    "https://api-docs.deepseek.com/quick_start/pricing/?article_id=article_1779470751466_8"
)
DEEPSEEK_PRICING_CHECKED_ON = "2026-07-29"
CACHE_HIT_INPUT_PER_MILLION_USD = Decimal("0.0028")
CACHE_MISS_INPUT_PER_MILLION_USD = Decimal("0.14")
OUTPUT_PER_MILLION_USD = Decimal("0.28")
VAT_MULTIPLIER = Decimal("1.10")
ONE_MILLION = Decimal("1000000")


def estimate_deepseek_cost_usd(usage: TokenUsage) -> Decimal:
    """Return the acceptance upper bound, pricing every prompt token as a cache miss."""
    if type(usage) is not TokenUsage:
        raise ValueError("TOKEN_USAGE_INVALID")

    subtotal = (
        Decimal(usage.input_tokens) * CACHE_MISS_INPUT_PER_MILLION_USD / ONE_MILLION
        + Decimal(usage.output_tokens) * OUTPUT_PER_MILLION_USD / ONE_MILLION
    )
    return subtotal * VAT_MULTIPLIER


def parse_deepseek_token_usage(
    value: object,
    *,
    max_input_tokens: int,
    max_output_tokens: int,
) -> TokenUsage | None:
    """Parse one strict DeepSeek usage envelope without retaining provider values on failure."""
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
    total_tokens = value.get("total_tokens")
    if (
        type(prompt_tokens) is not int
        or prompt_tokens < 0
        or prompt_tokens > max_input_tokens
        or type(completion_tokens) is not int
        or completion_tokens < 0
        or completion_tokens > max_output_tokens
        or type(total_tokens) is not int
        or total_tokens < 0
        or total_tokens != prompt_tokens + completion_tokens
    ):
        return None

    has_cache_hit = "prompt_cache_hit_tokens" in value
    has_cache_miss = "prompt_cache_miss_tokens" in value
    if has_cache_hit is not has_cache_miss:
        return None
    if not has_cache_hit:
        return TokenUsage(prompt_tokens, 0, completion_tokens)

    cache_hit_tokens = value["prompt_cache_hit_tokens"]
    cache_miss_tokens = value["prompt_cache_miss_tokens"]
    if (
        type(cache_hit_tokens) is not int
        or cache_hit_tokens < 0
        or type(cache_miss_tokens) is not int
        or cache_miss_tokens < 0
        or cache_hit_tokens + cache_miss_tokens != prompt_tokens
    ):
        return None
    return TokenUsage(prompt_tokens, cache_hit_tokens, completion_tokens)
