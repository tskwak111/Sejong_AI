"""Exact Decimal pricing for the approved synthetic evaluation profile."""

from decimal import Decimal

from sejong_ai_api.llm.contracts import TokenUsage

INPUT_PER_MILLION = Decimal("0.15")
CACHED_INPUT_PER_MILLION = Decimal("0.015")
OUTPUT_PER_MILLION = Decimal("0.60")
VAT_RATE = Decimal("0.10")
ONE_MILLION = Decimal("1000000")
RUN_COST_CAP_USD = Decimal("0.05")
_MAX_RUN_ATTEMPTS = Decimal("30")


def estimate_cost_usd(usage: TokenUsage) -> Decimal:
    """Price non-cached input, cached input, output, then apply ten percent VAT."""
    if type(usage) is not TokenUsage:
        raise ValueError("TOKEN_USAGE_INVALID")

    non_cached_input = usage.input_tokens - usage.cached_input_tokens
    subtotal = (
        Decimal(non_cached_input) * INPUT_PER_MILLION / ONE_MILLION
        + Decimal(usage.cached_input_tokens) * CACHED_INPUT_PER_MILLION / ONE_MILLION
        + Decimal(usage.output_tokens) * OUTPUT_PER_MILLION / ONE_MILLION
    )
    return subtotal * _MAX_RUN_ATTEMPTS * (Decimal(1) + VAT_RATE)
