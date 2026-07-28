# A-074 DeepSeek Classifier Provider Discovery Audit

- Task ID: `A-074-DEEPSEEK-CLASSIFIER-PROVIDER`
- Date: 2026-07-29 KST
- Formal A-074 baseline after A-073 closure:
  `50aab6e` (`docs(llm): close A-073 scoped review`)
- Earlier read-only audit start:
  `a362c191aa57a968a9264a2926610b57ca7c9588`
- Human decision: `Q-LLM-PROVIDER-001=A`
- Status: Complete — no unresolved implementation blocker

## 1. Purpose and scope

This audit checks whether DeepSeek can be added as a local/private question-classification
provider without weakening the existing safety, storage, API, grounding, or source-binding
boundaries. It does not authorize public deployment, remote DB use, real citizen free-input,
provider-generated facts, or a change to the final citizen-answer provider.

The preceding A-073 result is historical evidence and is not retried by A-074:

- A-073 root wrapper: `NOT VERIFIED/FAIL`
- invocation: 1
- rerun: 0
- A-073 Upstage corrective actual: 0
- existing Upstage actual rerun: 0

## 2. Authorities read

- `AGENTS.md`
- `docs/00_SOURCE_OF_TRUTH.md`
- `docs/source-of-truth/TEAM_DECISIONS.md`
- `docs/source-of-truth/PROJECT_PLAN.md`
- `docs/source-of-truth/RFP_MATRIX.md`
- ADR-0005, ADR-0023, ADR-0025, ADR-0026, ADR-0027
- current classifier contracts, prompt, Upstage adapter, local composition, limits and cost code
- A-073 specification, plan, implementation note and immutable evidence

`legacy/` was not treated as authority.

## 3. Current implementation boundary

The repository already provides:

1. deterministic policy, privacy, clear non-civic and clear supported-question gates;
2. a masked `SafeQuestion` boundary before provider use;
3. provider-neutral `QuestionClassifierPort`;
4. a bounded provider prompt built from a request-local ACTIVE/OFFICIAL catalog;
5. an exact five-key/all-string parser with exact uppercase `NONE`;
6. enum, identifier, route-shape and request-local catalog validation;
7. deterministic fail-closed fallback;
8. server-owned facts, sources and office binding;
9. `httpx` as an existing production dependency.

The current provider-specific coupling is limited to:

- Upstage settings and HTTP request shape;
- Upstage-specific local runtime construction;
- an Upstage-specific cost estimator embedded in the shared attempt reservation;
- the Upstage-specific actual runner and report.

## 4. Source-of-truth and implementation gaps

| Area | Current state | A-074 required state | Impact |
|---|---|---|---|
| Provider selection | Classifier wiring is Upstage-specific | Explicit `disabled`, `upstage`, or `deepseek` selector | Internal runtime configuration |
| DeepSeek transport | Absent | Separate classifier-only adapter using existing `httpx` | Backend/AI |
| Trust boundary | Exact parser exists | Same parser must validate DeepSeek `json_object` output | Security/data quality |
| Cost | Shared reservation uses Upstage pricing | Provider-specific conservative estimator | Cost acceptance |
| Usage | Upstage-compatible usage fields | Validate DeepSeek prompt/output/cache usage without retaining body | Cost/security |
| Actual evidence | Upstage runner/report/lock | Separate one-shot A-074 runner/report/lock | QA/audit |
| Offline evidence | A-073 wrapper already consumed | New A-074-only wrapper, invoked exactly once | QA/audit |
| Active docs | Classifier described as Upstage-only | Upstage/DeepSeek selectable; final generation still Upstage | Documentation |

No public API field, DB migration, official-data release, Web contract, package or lockfile change
is necessary.

## 5. Official provider facts verified

The following official DeepSeek documentation was checked on 2026-07-29:

- model list: <https://api-docs.deepseek.com/api/list-models>
- chat completion and `json_object` request shape:
  <https://api-docs.deepseek.com/api/create-chat-completion>
- JSON output guidance: <https://api-docs.deepseek.com/guides/json_mode/>
- thinking-mode controls: <https://api-docs.deepseek.com/guides/thinking_mode>
- current pricing: <https://api-docs.deepseek.com/quick_start/pricing/?article_id=article_1779470751466_8>
- context caching: <https://api-docs.deepseek.com/guides/kv_cache>

Verified implementation inputs:

- base URL: `https://api.deepseek.com`
- endpoint: `/chat/completions`
- model: `deepseek-v4-flash`
- output mode: `response_format={"type":"json_object"}`
- thinking must be explicitly disabled for this deterministic classifier lane;
- `json_object` helps produce JSON syntax but does not replace server schema validation;
- provider-side context caching exists, so only masked, synthetic, local/private fixed-fixture
  actual input is approved; real citizen/public input is prohibited.

Pricing is mutable external information. A-074 freezes the checked rates in versioned code and
uses a conservative cache-miss upper-bound estimator plus the existing 10% VAT safety multiplier.
The actual report must identify the rate source and checked date without storing request content.

The rates checked at `2026-07-29T05:14:21+09:00` are:

- cache-hit input: USD `0.0028` per million tokens;
- cache-miss input: USD `0.14` per million tokens;
- output: USD `0.28` per million tokens.

Acceptance prices every prompt token at the cache-miss rate and applies a 10% VAT safety
multiplier. With the internal pre-reservation ceiling of 16,384 prompt tokens and 128 output
tokens, the configured nine-call upper bound is USD `0.02306304`, below USD `0.20`.

## 6. Security and privacy audit

The implementation must prove:

- raw input is never sent to DeepSeek;
- policy/privacy, obvious non-civic and obvious supported questions make zero outbound calls;
- only masked ambiguous input reaches the adapter;
- raw question, request/response body, invalid value, exception detail, API key and DSN are absent
  from DB, logs, exceptions and reports;
- DeepSeek output cannot choose sources, offices, official facts or storage eligibility;
- provider failure returns the existing deterministic fallback;
- actual evidence is aggregate-only and immutable after its first run.

The ordinary public `sejong_ai_api.main` composition remains provider-free. DeepSeek construction
exists only in `sejong_ai_api.local.create_local_app`, and the approved runner binds loopback
`127.0.0.1`, disables proxy headers and access logging, and uses one local worker. This is the
technical local/private boundary. It permits owner-entered local MVP/UAT questions; it does not
authorize exposing that process to real citizens. Public deployment or remote/free-input
operation requires a new decision and architecture gate.

The fixed actual subset is synthetic and PII-free. Four policy/privacy probes run before the
selected 20 and must demonstrate outbound 0 without becoming selected fixtures or stored evidence.

## 7. Cost and failure audit

The current cost reservation is Upstage-specific and is the main implementation risk. A-074 must
inject an estimator per provider lane while preserving the shared process-lifetime budget of
classifier 80, generator 100 and combined 160. DeepSeek prompt
tokens are conservatively priced as cache misses; cache-hit discounts are not required to pass the
cap. Missing, inconsistent or negative usage fails closed.

Execution limits remain:

- timeout 3 seconds
- retry 0
- concurrency 1
- max output 128
- temperature 0
- thinking disabled
- total actual upper-bound cost at most USD 0.20

An HTTP failure, empty response, invalid JSON, contract violation, catalog mismatch, invalid usage
or cost-cap failure records only a bounded aggregate failure and is never automatically retried.

## 8. Ambiguity disposition

| ID | Priority | Decision | Status |
|---|---|---|---|
| `Q-LLM-PROVIDER-001` | A / Blocker | A — add DeepSeek classifier-only provider | Resolved |
| Provider selector | C | Exact selector; default disabled; no automatic provider cascade | Defaulted |
| Mixed final generator | C | Runtime may retain separately enabled Upstage grounded generation; A-074 actual disables it | Defaulted |
| Cache pricing | C | Conservative cache-miss upper bound, 10% VAT multiplier | Defaulted |
| File/helper split | D | Separate settings, cost, adapter and one-shot runner | Internal |

No A/Blocker remains. The user's current instruction explicitly approves design, specification,
plan, offline execution and exactly one DeepSeek actual on a clean reviewed source.

## 9. Recommended implementation sequence

1. provider-neutral cost/usage boundary;
2. strict selector and DeepSeek settings;
3. DeepSeek adapter reusing the exact parser;
4. provider-neutral local wiring;
5. one-shot controlled runner and retention tests;
6. focused and area tests;
7. new A-074 offline wrapper exactly once;
8. clean-source review;
9. DeepSeek actual exactly once;
10. aggregate evidence, versions, implementation note and Draft PR.

## 10. Rollback

Set `CLASSIFIER_PROVIDER=disabled` to stop classifier provider use immediately. A code rollback
removes the DeepSeek adapter, settings, estimator and runner while leaving the existing Upstage
classifier and grounded-answer generator intact. No API, DB, data or migration rollback is needed.
Never read, print, copy or delete a user's ignored `.env`; the human removes or rotates a key in
the provider dashboard or local environment.
