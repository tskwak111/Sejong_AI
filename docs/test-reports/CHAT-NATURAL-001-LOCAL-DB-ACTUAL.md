# CHAT-NATURAL-001 Local DB Actual Report

- Date: 2026-07-27 KST
- Source commit: `7c96a0a`
- Target: approved disposable local PostgreSQL at exact loopback port
- Release: `0.1.0-initial.2`
- Provider calls/cost: 0 / USD 0
- Raw question, DSN, generated password and context secret output: 0

## Preflight

| Check | Result |
|---|---|
| Worktree | clean, isolated feature branch |
| `[db.seed].enabled` | `false` |
| Existing project runtime/listener | stopped to exact 0/0 before formal seed |
| Patched CLI | 2.109.1 |
| Runtime network after restart | exact `sejong-ai-local-loopback` |

## Formal immutable `.2` cycle

The supported runner completed in 122.2 seconds.

| Phase | Result |
|---|---|
| identity | exact |
| failure rollback | tables 8, partial 0 |
| concurrency A | capability-before-lock, seed rows 0, capability rows 1 |
| concurrency B | lock-before-capability, seed complete 1, capability rows 1 |
| seed-cycle | KB 19, office 3, mapping 10, replay 1 |
| guards | second seed blocked, compensation guard blocked |
| final | KB 19, office 3, mapping 10, citizen 19, exclusions 0, operational 0 |
| cleanup | PASS |
| semantic SHA-256 | `c838a4aa5eb1675d93fbaebd99b63d823490eb172c64cc356c5f72114cc1e4eb` |

## Governed 19→20 regression

| Phase | Result |
|---|---|
| `/ready` | 200 |
| initial ACTIVE | 19 |
| PERSONAL_LOOKUP persistence | event delta 0, failed delta 0 |
| initial grounding fallback | PASS |
| durable replay | PASS |
| eligible insufficient grounding | event delta 1, failed delta 1 |
| NEW failed queue | count 1 |
| reason confirmation | PASS |
| candidate create/submit | PASS |
| same-writer approval | blocked |
| different approver | approved |
| improved requery | SUCCESS, server-bound source `KB-WASTE-03` |
| old idempotent replay | preserved |
| final ACTIVE | 20, four supported categories × five |

## Privacy and lineage

- The runner emitted only its fixed bounded result lines.
- The PERSONAL_LOOKUP case produced no event or failed-question row.
- The eligible grounding failure was the only question-bearing workflow row.
- The author and approver were distinct.
- Official release bytes did not change; the twentieth ACTIVE row is governed local runtime lineage,
  not a mutation of release `.2`.

## Current state and rollback

The local DB intentionally remains at ACTIVE 20 with the safe loopback container running. To return
to the approved 19 baseline, stop the patched local runtime, run the supported clean DB verifier, and
then rerun the immutable `.2` seed runner. Do not run the 19→20 harness twice on the same state.
