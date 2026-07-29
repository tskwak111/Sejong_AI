# ADR-0028 — Selectable DeepSeek classifier provider

- Status: Accepted
- Date: 2026-07-29
- Decision: `Q-LLM-PROVIDER-001=A`, D-122
- Amends: ADR-0025 and ADR-0027 only for classifier-provider selection
- Preserves: ADR-0023 Upstage grounded citizen-answer generation
- Historical only: ADR-0005 remains superseded and is not reactivated

## Context

The local/private Hybrid RAG path already separates deterministic safety routing, a bounded
question-classifier port, server validation, ACTIVE/OFFICIAL grounding and optional grounded
answer generation. The classifier implementation is currently wired only to Upstage. The project
needs a second classifier provider for a fixed local comparison while keeping the exact existing
wire contract and all server-owned safety decisions.

DeepSeek's `json_object` output mode constrains JSON syntax, not the project's exact five keys,
strings, enums, route shape or current catalog membership. Provider output therefore remains
untrusted.

## Decision

1. Add `CLASSIFIER_PROVIDER` with exact values `disabled`, `upstage`, and `deepseek`.
   The default is `disabled`.
2. Do not automatically cascade from one provider to another. Invalid, incomplete or conflicting
   configuration disables the classifier and retains the deterministic fallback.
3. Keep the existing Upstage classifier as a selectable implementation.
4. Add DeepSeek `deepseek-v4-flash` for question classification only.
5. Keep ADR-0023's optional Upstage grounded citizen-answer generation unchanged and separately
   configured. The A-074 DeepSeek actual disables that generator so its evidence is classifier-only.
   DeepSeek is composed only by `sejong_ai_api.local.create_local_app`; the public
   `sejong_ai_api.main` application remains provider-free. The approved local runner binds only
   `127.0.0.1`. This allows owner-operated local MVP/UAT and does not authorize a real-citizen
   service.
6. Keep the provider wire byte-for-byte compatible:
   `route`, `intent`, `topic_id`, `coverage_id`, `pending_slot`; every value is a JSON string and
   every nullable value is exact uppercase `NONE`.
7. DeepSeek uses `/chat/completions`, `json_object`, explicit thinking disabled, temperature 0,
   timeout 3 seconds, retry 0, concurrency 1 and maximum output 128.
8. The existing server parser is the sole decision trust boundary. It checks exact keys and types,
   closed enums, identifier syntax, route shape and request-local catalog membership.
9. Deterministic policy/privacy, obvious non-civic and obvious supported-question routing remains
   provider-free. Only a masked safe ambiguous question may be sent.
10. The model never creates facts, sources, offices, storage eligibility or candidate eligibility.
    The server binds facts and sources from the current ACTIVE/OFFICIAL KB.
11. No question, request/response body, invalid field value, API key, DSN or exception detail may
    cross the log, DB, report or public-error boundary.
12. On timeout, empty content, HTTP error, JSON error, usage error, contract violation, catalog
    mismatch or budget failure, use the existing deterministic fail-closed fallback.
13. Generalize the process-lifetime 80/100/160 internal cost reservation to accept a
    provider-specific estimator. Preserve the Upstage estimator and add a conservative DeepSeek
    cache-miss upper-bound estimator based on the official rates checked at
    `2026-07-29T05:14:21+09:00`: hit input USD 0.0028/M, miss input USD 0.14/M and output
    USD 0.28/M, with a 10% VAT safety multiplier. Nine reservations at 16,384 input and 128 output
    tokens have a configured upper bound of USD 0.02306304.
14. Actual evidence is local/private, fixed-fixture, aggregate-only and one-shot. The DeepSeek
    actual cap is USD 0.20. It may run once after the new A-074 offline gate and clean-source
    review; failure is final for this run and is not automatically retried.

## Exact actual acceptance

- selected 20, skipped 0;
- deterministic/provider-free 11;
- DeepSeek outbound 9;
- policy/privacy outbound 0;
- HTTP 2xx, exact parse, server acceptance and expected route/intent/topic match all 9;
- retained question/body/invalid value/secret counts all 0;
- timeout 3, retry 0, concurrency 1, output 128, deterministic sampling;
- conservative cost upper bound at or below USD 0.20.

## Scope boundary

Approved:

- local/private classifier implementation;
- offline controlled-double verification;
- exactly one fixed, synthetic, PII-free DeepSeek actual.

Not approved:

- public deployment or remote DB;
- real citizen free-input provider use;
- final citizen-answer provider change;
- provider-generated facts or sources;
- new production dependency;
- automatic merge or automatic actual rerun.

## Consequences

Positive:

- classifier providers can be compared behind one exact server authority;
- provider syntax or model drift cannot bypass grounding and catalog checks;
- Upstage classifier and grounded generator remain available;
- rollback is configuration-only in the common case.

Trade-offs:

- an explicit selector is required, so old local environments must add it;
- DeepSeek may cache masked provider context externally, so its approved use remains synthetic and
  local/private;
- the conservative cost estimate may overstate billed cost;
- one-shot evidence cannot be retried merely to obtain a pass.

## Rollback

Set `CLASSIFIER_PROVIDER=disabled` or explicitly select `upstage`. Revert the DeepSeek adapter,
settings, estimator, runner and composition commit if code rollback is required. No API, DB,
migration, official-data or Web rollback is required. Remove or rotate the key outside Git without
reading or printing its value.

## Revisit triggers

A new human decision and ADR amendment are required before public/remote/free-input use, a final
answer-provider change, provider fallback cascade, a new production dependency, altered public
wire, or a changed retention policy.
