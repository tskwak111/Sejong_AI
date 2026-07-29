# A-077 DeepSeek Split-Timeout Correction — Written Specification

- Task ID: `A-077-DEEPSEEK-SPLIT-TIMEOUT`
- Status: Approved
- Date: 2026-07-29 KST
- Human authority: `A로 ㄱㄱ`
- Predecessor: D-126/D-127 and immutable A-074/A-075/A-076 evidence

> D-129 security amendment: A-077 source `675eef4de38ecead70af6f74c2493c115bcad0c2`
> consumed offline PASS `1/0` only. Provider probe/actual remained `0/0`. Independent review kept
> it from provider execution and transferred the unchanged D-128 authority to the disjoint A-078
> identity below.

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

The final evidence flow is:

1. preserve the historical A-077 offline PASS without rerunning it;
2. commit a clean A-078 source checkpoint;
3. consume the new `A-078-OFFLINE` gate once;
4. run network-free A-078 readiness;
5. consume one A-078 latency-probe lease and send one preselected masked synthetic provider case;
6. revalidate source/evidence after the provider response before publishing aggregate probe PASS;
7. bind a bounded strict probe report to the exact lease bytes and source SHA;
8. re-check that binding after clean-source revalidation, then perform final source/input/settings
   revalidation immediately before the actual lease;
9. consume the separate A-078 actual lease only when every check passes;
10. run the fixed 20-case selection with 11 deterministic/provider-free and 9 provider cases.

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
offline wrapper: scripts/run_a078_offline_gate.ps1
offline directory: .superpowers/sdd/2026-07-29-deepseek-prelease-hardening
offline gate: A-078-OFFLINE
probe runner: scripts/run_deepseek_classifier_a078_probe.py
local probe report: .superpowers/sdd/2026-07-29-deepseek-prelease-hardening/a078-probe-result.json
tracked closeout summary: docs/test-reports/CHAT-HYBRID-RAG-001-DEEPSEEK-A078-PROBE.md
actual runner: scripts/run_deepseek_classifier_prelease_hardened_actual.py
actual report: docs/test-reports/CHAT-HYBRID-RAG-001-DEEPSEEK-A078-ACTUAL.md
```

Probe and actual leases are separate. The machine-readable probe result stays in the ignored local
evidence directory so the committed source remains clean for the actual; its aggregate values are
copied to the tracked closeout summary only after the provider run. All A-078 paths and sentinel
payloads are disjoint from A-074/A-075/A-076/A-077.

## Acceptance

### Offline and probe

- offline exit `0`, no timeout, invocation/rerun `1/0`, preserved stdout/stderr hashes;
- readiness exact profile and absent A-078 probe/actual report and leases;
- probe invocation/outbound `1/1`, retry/rerun `0/0`;
- probe provider response/HTTP 2xx `1/1`, transport-no-response `0`;
- all retained question/body/value/secret counters `0`;
- conservative cost at most USD `0.20`.

The probe does not require a matching classification decision; it verifies authenticated
response transport after the timeout correction. The normal parser still processes the response,
but the probe retains no response content or parser-stage detail. The fixed actual owns the
closed response-stage acceptance evidence.

### Fixed actual

- selected/skipped `20/0`;
- deterministic/provider-free `11`, DeepSeek provider `9`;
- privacy/policy outbound `0`;
- outbound/HTTP 2xx/exact parse/server accepted/oracle match `9/9/9/9/9`;
- retry/rerun/concurrency `0/0/1`;
- retained question/masked question/request body/response body/invalid value/secret all `0`;
- conservative cost at most USD `0.20`.

## Rollback and revisit triggers

Before external evidence is consumed, revert the A-077 timeout commit and the A-078 evidence-chain
hardening commit together.
After a probe or actual lease exists, preserve its report/lease and make any further change under a
new human decision and evidence identity. Set `CLASSIFIER_PROVIDER=disabled` for runtime rollback.

Public/remote/free-input use, a final-answer-provider change, retries, a new dependency, a different
model or another actual run requires a new explicit decision.

## D-130/D-131 A-079 retry amendment

A-078 source `844e53be97be3f70b398f20737a248d55271d551` passed offline once. Its
exact-one probe closed FAIL with outbound1, response/2xx0 and transport-no-response1, so its actual
was not run. A Windows CRLF translation in the exclusive lease writer is fixed with binary-open
flags for successor evidence; A-078 remains immutable.

The user explicitly approved one retry. A-079 uses disjoint offline/probe/actual identities in
`.superpowers/sdd/2026-07-29-deepseek-network-retry`, runner names ending in `a079_probe` and
`network_retry_actual`, and report names ending in `A079`. It may send exactly one probe call and,
only after HTTP 2xx, one actual run containing exactly nine provider calls. Every other acceptance,
privacy, timeout, retry, cost and scope condition in this specification remains unchanged.
