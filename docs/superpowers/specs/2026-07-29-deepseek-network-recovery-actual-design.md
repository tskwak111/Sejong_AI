# A-076 DeepSeek Network-Recovery Actual — Written Specification

- Task ID: `A-076-DEEPSEEK-NETWORK-RECOVERY-ACTUAL`
- Status: Approved
- Date: 2026-07-29 KST
- Human authority: `아 지금 딥시크 네트워크 때문에 안된듯, 다시 진행해봐`
- Predecessor: D-124/D-125, A-075 immutable `transport_no_response` FAIL

## Goal

After a value-free DNS/TCP/TLS/HTTP probe confirms that the DeepSeek network path responds again,
run the unchanged approved synthetic classifier evaluation exactly once under a new A-076 evidence
identity.

## Scope and authority

A-075 report, offline artifacts, invocation `1`, retry `0` and rerun `0` remain immutable. A-076
uses the same fixed 20 cases, model, parser, catalog, prompt, timeout, cost and retention boundaries
as A-075. This work changes evidence tooling and documentation only; it does not activate public,
remote or real-citizen traffic and does not change API, DB, official data, Web or dependencies.

## Required identity

```text
offline wrapper: scripts/run_a076_offline_gate.ps1
offline directory: .superpowers/sdd/2026-07-29-deepseek-network-recovery-actual
offline gate: A-076-OFFLINE
actual runner: scripts/run_deepseek_classifier_network_recovery_actual.py
report: docs/test-reports/CHAT-HYBRID-RAG-001-DEEPSEEK-A076-ACTUAL.md
lease: docs/test-reports/CHAT-HYBRID-RAG-001-DEEPSEEK-A076-ACTUAL.md.run.lock
```

All paths and lease payloads are disjoint from A-074 and A-075. The existing fail-closed evidence
binding seam is reused without changing classifier, transport or parser behavior.

## Preconditions and acceptance

- Value-free probe: DNS, TCP 443 and TLS/HTTP response all succeed; unauthenticated HTTP 4xx is an
  acceptable connectivity result.
- Offline gate: clean committed source, invocation/rerun `1/0`, exit `0`, no timeout and preserved
  stdout/stderr hashes.
- Readiness: exact A-076 paths, approved ignored environment profile, absent report/lease.
- Actual: selected/skipped `20/0`, deterministic/provider `11/9`, privacy/policy outbound `0`,
  outbound/HTTP 2xx/parse/accepted/oracle `9/9/9/9/9`, retry/rerun/concurrency `0/0/1`, retained
  question/body/value/secret all `0`, conservative cost at most USD `0.20`.

## Failure and rollback

Any offline or readiness failure blocks the actual. Once the A-076 actual lease exists, no
automatic rerun is allowed regardless of result. Output and reports remain aggregate-only. Before
actual, evidence-only commits can be reverted; after actual, report and local permanent lease are
never deleted to manufacture another retry.
