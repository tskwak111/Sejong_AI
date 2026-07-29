# A-075 DeepSeek Corrective Actual — Written Specification

- Task ID: `A-075-DEEPSEEK-CORRECTIVE-ACTUAL`
- Status: Approved
- Date: 2026-07-29 KST
- Human authority: `변수명 수정 완료, A-075 DeepSeek actual 1회 실행 승인`
- Predecessor: D-122/D-123, ADR-0028, A-074 immutable offline FAIL

## Goal

Create a new, isolated A-075 evidence identity and run the existing hardened DeepSeek classifier
against the approved fixed synthetic fixture exactly once after a new clean-source offline PASS.

## Non-goals

- changing classifier, chat, source, API, DB, official data, Web or dependency behavior;
- changing the final citizen-answer provider;
- altering or rerunning any A-073/A-074 wrapper, result, report or lease;
- public deployment, remote DB or real citizen free-input;
- retry, automatic provider cascade, automatic merge or evidence overwrite.

## Identity contract

```text
offline wrapper: scripts/run_a075_offline_gate.ps1
offline directory: .superpowers/sdd/2026-07-29-deepseek-corrective-actual
offline gate: A-075-OFFLINE
actual runner: scripts/run_deepseek_classifier_corrective_actual.py
report: docs/test-reports/CHAT-HYBRID-RAG-001-DEEPSEEK-A075-ACTUAL.md
lease: docs/test-reports/CHAT-HYBRID-RAG-001-DEEPSEEK-A075-ACTUAL.md.run.lock
```

Every A-075 path and lease payload must differ from A-074. A-075 may reuse the existing evaluator,
transport, parser and cost logic only through an explicit profile-binding entry point that first
checks the A-074 defaults have not drifted.

## Acceptance

Offline:

- exact current clean source;
- wrapper invocation/rerun `1/0`;
- root offline gate exit `0`, no timeout;
- stdout/stderr hashes and byte counts preserved;
- focused, area, Ruff, Mypy, docs, secret and diff checks pass;
- independent scoped review has Critical 0 and Important 0.

Actual:

| Metric | Required |
|---|---:|
| selected / skipped | `20 / 0` |
| deterministic / DeepSeek provider | `11 / 9` |
| policy/privacy outbound | `0` |
| outbound / HTTP 2xx | `9 / 9` |
| strict parse / accepted / oracle match | `9 / 9 / 9` |
| retained question/body/invalid/secret | all `0` |
| retry / rerun / concurrency | `0 / 0 / 1` |
| conservative cost | `<= USD 0.20` |

## Failure behavior

Offline FAIL blocks actual. Readiness failure consumes no actual lease. Once the A-075 actual lease
exists, no rerun is permitted regardless of PASS, FAIL, timeout or crash. Reports and console
output remain aggregate-only. No provider response body, invalid value, API key, DSN, question or
masked question is inspected or persisted.

## Rollback

Before actual, revert the evidence-only files and set `CLASSIFIER_PROVIDER=disabled`. After actual,
never delete report/lease to create a retry. Product rollback remains the ignored local selector;
there is no API, DB or data rollback.
