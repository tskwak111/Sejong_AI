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
   retry 0, concurrency 1 and maximum output 128. D-128 amends the original all-3-second timeout:
   connect/write/pool remain 3 seconds while read and the complete exchange are 10 seconds.
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
- connect/write/pool timeout 3, read/complete-exchange timeout 10, retry 0, concurrency 1,
  output 128, deterministic sampling;
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

## 2026-07-29 amendment — D-128 / A-077

A-075 and A-076 each produced nine pre-response failures in approximately nine times the
three-second complete-exchange budget, while a value-free connectivity probe reached DeepSeek.
Q-LLM-015=A therefore approves a local/private split-timeout diagnostic: 3-second
connect/write/pool, 10-second read and complete exchange, retry 0. A separate one-call synthetic
probe must receive HTTP 2xx before the new A-077 nine-provider-case actual may run. Both runs use
new permanent evidence identities and keep every A-074/A-075/A-076 artifact immutable.

## 2026-07-29 second amendment — D-129 / A-078

The A-077 offline gate passed once on source `675eef4de38ecead70af6f74c2493c115bcad0c2`,
but no provider probe or actual was consumed. Independent review found that the conditional actual
accepted a probe report without proving the exact probe lease and did not repeat the same-source
probe check after clean-source revalidation immediately before the actual lease.

A-077 evidence therefore remains immutable historical evidence and provider execution moves to a
disjoint A-078 successor under the unchanged D-128 authority. A-078 validates bounded strict probe
JSON plus exact lease bytes and repeats that same-source acceptance check after source
revalidation, performs one final source/input/settings revalidation before consuming the actual
lease, and revalidates source/evidence after the probe response before publishing probe PASS. This
correction adds no provider call, retry, cost, public scope, dependency or product behavior.

## 2026-07-29 third amendment — D-130/D-131 / A-079

A-078 source `844e53be97be3f70b398f20737a248d55271d551` passed offline once, but its
one-call probe received no HTTP response and closed `FAIL`; the conditional actual did not run.
The Windows probe lease also exposed a separate text-mode CRLF translation defect. It did not
cause the transport failure, but would have made exact-LF validation fail closed.

The lease/report writers now use binary-open flags. The user's explicit network-retry instruction
authorizes one disjoint A-079 probe call and, only after HTTP 2xx, one actual run containing exactly
nine provider calls. A-078 evidence remains immutable. Timeout, retry, cost, retention,
local/private scope and every product/provider boundary remain unchanged.

Source `a2d617cd10c729e7e415301ad48dcf19ec135ed2` then passed offline and the
one-call probe received HTTP 2xx with strict parse and accepted usage. The conditional actual
received nine HTTP 2xx responses and accepted all nine exact wire decisions. Oracle agreement was
six of nine, so overall acceptance is `FAIL` on classification quality, not transport or contract
shape. No automatic rerun is allowed; a quality-correction run requires a new human decision.

## 2026-07-29 fourth amendment — D-133 / A-080 quality design

The user approved option A for the `6/9` quality follow-up. Because the literal
`Q-LLM-015` label was already used by D-128, D-133 preserves history and assigns the canonical
alias `Q-LLM-016-QUALITY`.

A-080 will keep one provider-neutral prompt and add compact semantics for all five routes, require
the narrowest covered catalog row and treat coverage exclusions as binding. Exact wire, parser,
PII, storage, ACTIVE/OFFICIAL grounding, provider limits, final-answer provider, public API, DB,
data and deployment remain unchanged. This amendment approves the written design only. Product
code and A-080 provider calls remain unapproved.

## 2026-07-29 fifth amendment — D-134 / A-080 specification approval

The user approved the integrated A-080 written specification. The published TDD plan keeps the
semantic rubric provider-neutral, preserves the exact five-string parser and all server-owned
privacy, storage and grounding boundaries, and creates only disjoint A-080 evidence identities.

Plan approval may authorize provider-free Tasks 1 through 6. It does not authorize a DeepSeek
provider call. A live A-080 evaluation requires the separate exact approval
`A-080 DeepSeek actual 1회 실행 승인`, uses 20 selected/0 skipped and 11 provider-free/9 provider
cases, and can run only once on a clean source after the immutable offline gate passes.

## 2026-07-29 sixth amendment — D-135 / A-080 provider-free implementation

The A-080 specification and plan are Approved implementation authority. Provider-free Tasks 1~3
implemented the shared semantic route rubric and disjoint evidence identities: the prompt system
length is 896, prompt tests are 22 PASS, the DeepSeek framing bound is 1 PASS, provider suites are
133 PASS, and controlled-wrapper tests are 9 PASS with a clean PowerShell parser and Ruff. Scoped
task reviews are clean.

This checkpoint does not consume the A-080 offline gate, readiness, or actual lease: all are 0;
provider calls and cost are 0. It changes neither the exact five-string wire/parser nor
fail-closed/server-owned privacy, storage, ACTIVE/OFFICIAL grounding and source boundaries. It
also does not alter API, shared contracts, Web, DB, official/mock data, dependencies, public/remote
scope or the final-answer provider. A-079 remains transport/wire verified and quality `FAIL 6/9`.
The A-080 actual may run only after the separate exact approval `A-080 DeepSeek actual 1회 실행 승인`.

## 2026-07-29 seventh amendment — D-136 / A-080 exact-one quality actual

After the exact human approval, source
`f2c3aec50c6b615cbbaf989a9d7bf5760d1436c4` passed the A-080 immutable offline gate once and
readiness. The live actual consumed its permanent lease once: all nine provider cases received HTTP
2xx responses, passed strict parsing and were accepted by the server. Oracle agreement was eight of
nine, so the strict `9/9` acceptance target was not met and the overall result is `FAIL`.

This result verifies DeepSeek transport, the exact five-string wire and the server parser, and
improves the bounded oracle agreement from A-079's `6/9` to `8/9`; it does not prove full quality.
Policy/privacy outbound and all six retention counters are zero, retry/rerun/runtime failure are
zero, and conservative VAT-inclusive cost is USD `0.002961266`, below the USD `0.20` cap. The
provider is not promoted to the citizen runtime default. Deterministic fallback, server-owned
ACTIVE/OFFICIAL grounding, local/private scope and every API/DB/data/Web/dependency/public boundary
remain unchanged. A-080 is immutable and must not be rerun; any successor requires a new decision
and evidence identity.

## 2026-07-29 eighth amendment — D-137 / A-080 final review correction

The immutable actual remains bound to original source `f2c3aec50c6b615cbbaf989a9d7bf5760d1436c4`.
Before any post-actual source edit, rebased checkpoint `6a44201` had the identical Git tree
`9ad169344c8b115d5d943c6118af213683fdd940`; the final publication branch preserves the original
executed commit in its ancestry.

Final review then found that the approved exact route shape named `intent=supported`, while runtime
and tests used the undefined abbreviation `I=supported`. TDD changes this to the exact field name.
This correction happened after the one-shot actual and therefore has no live quality claim. The
A-080 report, lease and `8/9 FAIL` remain immutable and the provider is not rerun or promoted.
Only application, prompt, tests and documentation versions advance; API, contracts, Web, DB,
official/mock data, dependencies, server-owned grounding and local/private boundaries do not.
