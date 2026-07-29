# A-077 DeepSeek Split-Timeout Correction — Written Specification

- Task ID: `A-077-DEEPSEEK-SPLIT-TIMEOUT`
- Status: Approved
- Date: 2026-07-29 KST
- Human authority: `A로 ㄱㄱ`
- Predecessor: D-126/D-127 and immutable A-074/A-075/A-076 evidence

## Goal

Test the strongest A-076 failure hypothesis by separating the DeepSeek classifier's short
connection budget from its response budget. Confirm the corrected transport with one
aggregate-only synthetic call before spending the approved fixed nine-call evaluation.

## Scope and authority

The local/private DeepSeek classifier keeps its exact five-string wire contract, fixed model,
retry `0`, concurrency `1`, output cap `128`, deterministic sampling and fail-closed server parser.
Only its timeout profile changes:

- connect, write and pool timeout: `3.0` seconds;
- response read timeout: `10.0` seconds;
- complete classifier exchange wall clock: `10.0` seconds.

The A-077 fixed nine-provider-case evaluator gets a separate `100` second aggregate deadline.
Every A-074/A-075/A-076 report, lease, stdout/stderr identity and invocation/rerun count remains
immutable. This work does not change public API, DB schema/data, official data, Web behavior,
final-answer provider, dependencies or deployment.

## Architecture and data flow

`DeepSeekClassifierSettings` owns both timeout values. The HTTP client uses the short connection
budget for connect/write/pool and the response budget for read. `DeepSeekQuestionClassifier`
continues to wrap the entire request/response exchange in the response budget, so slow-drip bodies
cannot extend the call indefinitely.

The evidence flow is:

1. commit a clean A-077 source checkpoint;
2. consume the new `A-077-OFFLINE` gate once;
3. run network-free A-077 readiness;
4. consume one A-077 latency-probe lease and send one preselected masked synthetic provider case;
5. write only aggregate counts and accept the probe only for one HTTP 2xx response;
6. only after probe PASS, consume the separate A-077 actual lease and run the fixed 20-case
   selection with 11 deterministic/provider-free and 9 provider cases.

## Trust, privacy and failure boundary

- The probe and actual use only the approved synthetic fixture and current bounded catalog.
- The raw or masked question, request/response body, invalid field value, exception detail,
  API key and DSN are never written to DB, logs, reports or console.
- DeepSeek JSON remains untrusted. Exact keys/types/enums/route shape/catalog membership are
  revalidated by the existing server parser.
- Provider facts and sources remain forbidden; the server continues to bind ACTIVE/OFFICIAL
  knowledge.
- Timeout, transport, HTTP, body, usage, JSON, contract or catalog failure returns the existing
  deterministic fallback. There is no DeepSeek-to-Upstage cascade and no retry.
- A non-2xx or no-response probe writes its immutable FAIL report and blocks the nine-call actual.
- No lease or report is deleted to manufacture another run.

## Required evidence identities

```text
offline wrapper: scripts/run_a077_offline_gate.ps1
offline directory: .superpowers/sdd/2026-07-29-deepseek-split-timeout-correction
offline gate: A-077-OFFLINE
probe runner: scripts/run_deepseek_classifier_a077_probe.py
local probe report: .superpowers/sdd/2026-07-29-deepseek-split-timeout-correction/a077-probe-result.json
tracked closeout summary: docs/test-reports/CHAT-HYBRID-RAG-001-DEEPSEEK-A077-PROBE.md
actual runner: scripts/run_deepseek_classifier_split_timeout_actual.py
actual report: docs/test-reports/CHAT-HYBRID-RAG-001-DEEPSEEK-A077-ACTUAL.md
```

Probe and actual leases are separate. The machine-readable probe result stays in the ignored local
evidence directory so the committed source remains clean for the actual; its aggregate values are
copied to the tracked closeout summary only after the provider run. All A-077 paths and sentinel
payloads are disjoint from A-074/A-075/A-076.

## Acceptance

### Offline and probe

- offline exit `0`, no timeout, invocation/rerun `1/0`, preserved stdout/stderr hashes;
- readiness exact profile and absent A-077 probe/actual report and leases;
- probe invocation/outbound `1/1`, retry/rerun `0/0`;
- probe provider response/HTTP 2xx `1/1`, transport-no-response `0`;
- all retained question/body/value/secret counters `0`;
- conservative cost at most USD `0.20`.

The probe does not require a matching classification decision; it verifies authenticated
response transport after the timeout correction. The normal parser still processes the response
and records only a closed response-stage counter.

### Fixed actual

- selected/skipped `20/0`;
- deterministic/provider-free `11`, DeepSeek provider `9`;
- privacy/policy outbound `0`;
- outbound/HTTP 2xx/exact parse/server accepted/oracle match `9/9/9/9/9`;
- retry/rerun/concurrency `0/0/1`;
- retained question/masked question/request body/response body/invalid value/secret all `0`;
- conservative cost at most USD `0.20`.

## Rollback and revisit triggers

Before external evidence is consumed, revert the A-077 timeout and evidence-tooling commit.
After a probe or actual lease exists, preserve its report/lease and make any further change under a
new human decision and evidence identity. Set `CLASSIFIER_PROVIDER=disabled` for runtime rollback.

Public/remote/free-input use, a final-answer-provider change, retries, a new dependency, a different
model or another actual run requires a new explicit decision.
