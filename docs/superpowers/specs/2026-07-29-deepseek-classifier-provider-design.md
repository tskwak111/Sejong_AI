# Selectable DeepSeek Classifier Provider — Written Specification

- Task ID: `A-074-DEEPSEEK-CLASSIFIER-PROVIDER`
- Status: Approved
- Date: 2026-07-29 KST
- Human authority: `Q-LLM-PROVIDER-001=A` and the explicit instruction to continue through one
  offline gate, one actual, final review, commit, push and Draft PR
- Decision authority: D-121, D-122, ADR-0028
- Discovery: `docs/discovery/A_074_DEEPSEEK_CLASSIFIER_PROVIDER_AUDIT.md`

## 1. Goal

Add DeepSeek `deepseek-v4-flash` as an explicit question-classifier provider for the local/private
MVP while preserving the selectable Upstage classifier and the separate Upstage grounded
citizen-answer generator. DeepSeek is classifier-only in A-074.

## 2. Non-goals

- changing the final citizen-answer provider;
- public deployment, remote DB or real citizen free-input;
- changing the public API, DB, official data, Web contract or five-string classifier wire;
- provider-generated facts, sources, offices or storage decisions;
- embeddings, vector DB, multi-KB synthesis or a new production dependency;
- automatic provider cascade, actual retry, PR merge or report overwrite.

## 3. Configuration contract

### 3.1 Selector

`CLASSIFIER_PROVIDER` accepts exactly:

```text
disabled
upstage
deepseek
```

Missing, empty, unknown or conflicting configuration is fail-closed. The tracked default is
`disabled`. There is no automatic fallback from DeepSeek to Upstage; runtime falls back to the
existing deterministic classifier behavior.

### 3.2 DeepSeek profile

```text
CLASSIFIER_PROVIDER=deepseek
DEEPSEEK_API_KEY
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

Fixed runtime limits:

```text
timeout_seconds=3
retry_count=0
concurrency=1
max_output_tokens=128
temperature=0
thinking=disabled
actual_cost_cap_usd=0.20
```

The settings loader validates every non-secret exact value before accessing the key. It does not
log, expose in `repr`, return in a diagnostic, or copy the key.

### 3.3 Upstage preservation

`CLASSIFIER_PROVIDER=upstage` selects the existing classifier adapter. Optional Upstage grounded
generation remains controlled by its existing separate mode. The DeepSeek actual forces all
Upstage modes off so the result and cost are classifier-only; this does not delete or alter the
Upstage generator implementation.

## 4. Request and response trust boundaries

### 4.1 Provider-free paths

These paths remain deterministic and make zero classifier outbound calls:

- policy and legal-safety prohibitions;
- privacy/personal lookup;
- obvious `NON_CIVIC`;
- obvious supported questions resolved with sufficient deterministic confidence.

Only an ambiguous question that has passed masking and safety checks may become a `SafeQuestion`
and reach DeepSeek.

### 4.2 DeepSeek request

The adapter uses existing provider-neutral bounded messages and current request-local
ACTIVE/OFFICIAL catalog. It sends:

- `model=deepseek-v4-flash`;
- `response_format={"type":"json_object"}`;
- `thinking={"type":"disabled"}`;
- `temperature=0`;
- `max_tokens=128`;
- one bounded chat completion request.

The request body is process-memory-only and must never be logged or reported.

### 4.3 Exact response wire

The only accepted object has exactly these keys and string values:

```json
{
  "route": "SUPPORTED",
  "intent": "MOVE_IN_RESIDENT_REGISTRATION",
  "topic_id": "TOPIC-ID",
  "coverage_id": "COVERAGE-ID",
  "pending_slot": "NONE"
}
```

Nullable values must be exact uppercase string `NONE`. JSON `null`, lowercase, whitespace,
additional keys, missing keys, non-string values, invalid enums, invalid identifiers, invalid
route shape and catalog mismatch are rejected. DeepSeek `json_object` is never treated as schema
validation.

The existing shared parser and typed decision builder remain the only authority. The adapter
returns `None` on every rejected response so the existing deterministic fallback runs.

## 5. HTTP envelope and usage

Upstage and DeepSeek may share value-free envelope utilities where their response semantics are
identical, but provider request construction stays separate. Accepted DeepSeek usage requires
non-negative integer prompt, completion and total tokens with a consistent total. Cache hit/miss
fields are accepted only as a consistent pair. Absence of cache detail is conservatively priced as
all cache miss. Usage or envelope errors fail closed without retaining actual values beyond
aggregate token/cost counters.

## 6. Cost authority

The shared attempt ledger accepts an estimator per provider lane:

- Upstage lanes retain the current estimator;
- DeepSeek classification uses its own frozen estimator;
- the request-wide attempt and USD caps remain shared.

For acceptance, all DeepSeek prompt tokens are priced at the checked cache-miss input rate even if
the provider reports a hit; output uses the checked output rate; a 10% VAT safety multiplier is
applied. This is an upper bound, not a claim about final provider billing. The source URL and
checked date are versioned. Missing price authority or cost over USD 0.20 blocks actual before a
second request can occur.

## 7. Retention and observability

Permitted aggregate evidence:

- selected/skipped/provider-free/outbound counts;
- HTTP 2xx, exact parse, accepted and oracle-match counts;
- closed value-free failure-stage counts;
- aggregate token counts and conservative USD upper bound;
- invocation, retry, rerun and retention counters;
- source SHA, fixture hash, report hash and timestamp.

Forbidden:

- question or masked question;
- request/response body;
- invalid field value;
- fixture-to-stage mapping;
- API key, DSN or environment dump;
- raw exception, status body or provider diagnostic.

Application DB, access logs and error reporting retain none of the forbidden data.

## 8. Failure behavior

The adapter fails closed on:

- invalid or incomplete settings;
- timeout, connection or HTTP failure;
- empty/multiple/non-text content;
- invalid JSON or exact-wire failure;
- invalid usage, finish reason or cost reservation;
- request-local catalog mismatch.

It performs retry 0. The citizen path uses the current deterministic fallback. It does not attempt
Upstage as a provider cascade.

## 9. Offline acceptance

Before actual:

1. focused tests prove settings, transport, parser, usage, cost and local composition;
2. first-failure and non-retention tests stay green;
3. policy/privacy, obvious non-civic and obvious supported probes have outbound 0;
4. fixed synthetic 20 predicts selected 20, skip 0, deterministic 11, outbound 9;
5. Ruff, Mypy, docs, secret and diff checks pass;
6. one new A-074 offline wrapper runs exactly once with continuous output preservation and a
   sufficiently long timeout;
7. an independent review has zero Critical or Important findings;
8. the tree is clean and the exact source SHA is recorded.

The consumed A-073 root wrapper and Upstage actual are not rerun.

## 10. Actual acceptance

The one-shot runner first executes a network-free readiness check. Readiness failure does not
consume the actual. Once the actual lease is acquired, the run is invocation 1 and can never be
rerun regardless of PASS or FAIL.

Required PASS aggregate:

| Metric | Required |
|---|---:|
| selected | 20 |
| skipped | 0 |
| deterministic/provider-free | 11 |
| DeepSeek outbound | 9 |
| policy/privacy probes outbound | 0 |
| HTTP 2xx | 9 |
| exact five-field parse | 9 |
| server decision accepted | 9 |
| expected route/intent/topic match | 9 |
| retained question/body/invalid/secret | 0 |
| retry | 0 |
| rerun | 0 |
| conservative cost upper bound | `<= USD 0.20` |

Any deviation records aggregate `FAIL` and ends A-074 actual with rerun 0.

## 11. Version impact

Target after offline implementation:

| Axis | Before | Target |
|---|---|---|
| Application | `0.12.4-classifier-wire-diagnostics` | `0.13.0-selectable-classifier-provider` |
| Test suite | `2.1.7-classifier-wire-correction` | `2.2.0-deepseek-classifier-provider` |
| Documentation | `2.30.7` | `2.31.0-deepseek-classifier-provider` |
| Prompt | `0.4.3-explicit-route-matrix` | unchanged if message bytes are unchanged |
| Product/API/contracts/Web/DB/data/dependencies | current | unchanged |

## 12. Rollback and handoff

Immediate rollback is `CLASSIFIER_PROVIDER=disabled`. `upstage` remains an explicit alternative.
Code rollback removes DeepSeek-only files and provider-neutral composition changes; Upstage
generator remains untouched. No migration or data recovery is required. A new developer starts
with the provider-neutral port, the exact parser, ADR-0028 and the one-shot runbook; they must not
reuse A-073's root wrapper, report or actual lock.
