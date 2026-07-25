# LLM-003 Grounded Live Chat — Offline Evidence Report

- Report status: Offline implementation, task-scoped evidence and provider-disabled final repository gate complete; local actual Pending human gate.
- Scope: D-072~D-074 / local-private only.
- Design and plan: [design](../superpowers/specs/2026-07-25-grounded-live-chat-generation-design.md), [plan](../superpowers/plans/2026-07-25-grounded-live-chat-generation.md), [ADR-0023](../adr/0023-grounded-upstage-local-chat-generation.md).
- Evidence inputs: task reports and independent reviews in `.superpowers/sdd/2026-07-25-grounded-live-chat-generation/`.

## Result summary

The implemented offline path adds SUCCESS-only `answer_mode`, request-local fact-ID validation,
disabled-by-default grounded-chat configuration, a bounded one-attempt adapter, deterministic full
template fallback, idempotency coordination, local composition and visible Web disclosure. The
provider does not own policy, official fact text, source or office metadata. Task-scoped reviews
closed their reported Important findings before the following task proceeded.

The task-scoped results below are distinct from the final repository PASS. The latter was run with
provider disabled and key unset; no provider key was read and no network call was made for closeout.

| Task | Evidence / final task result | Review result |
|---|---|---|
| 1 — contract | shared-contract tests `89 passed`; API response/service/fixture tests `76 passed`; OpenAPI/FastAPI draft `3.2.0-draft` | Approved |
| 2 — facts | focused `43 passed in 0.14s`; LLM suite `184 passed, 1 warning in 5.46s` | Initial Important findings fixed; re-review Approved |
| 3 — settings | settings + synthetic-runner `31 passed, 6 subtests passed` | Approved after bounded parser fix |
| 4 — adapter | changed/existing focused `115 passed`; all LLM tests `229 passed, 1 existing warning` | Approved after fail-closed exception/usage fix |
| 5 — service/idempotency | chat `189 passed`; facts/prompt/adapter/repository validator `96 passed`; focused post-fix generated test `26 passed` | Approved after retained-claim fix |
| 6 — local runtime | API suite `1,923 passed`, `8` explicit local-DB-only skips, `5` subtests, `10.14s` | Approved |
| 7 — Web disclosure | Web lint/typecheck/build passed; Vitest `12 files / 56 tests` after source fail-closed fix | Initial P1 fixed; re-review Approved |

The warnings above are the recorded existing Starlette/httpx TestClient deprecation warning. No
new dependency was added to silence it.

## Security and behavior evidence

Task 8 security integration commits `767c2fc` and `3b13930` were independently re-reviewed with
`C0/I0/M0`. The final focused gates passed: security `85`, chat `202`, DB `168` with `8` DB-only
skips, provenance `57`, controller `115`, retrieval/static `5`; Ruff and Mypy also passed.

- Provider default remains disabled. Public import, startup, `/health` and `/ready` have no provider
  settings/prompt/transport/key use or outbound request.
- A call is eligible only after safe masking, supported deterministic intent, ACTIVE/OFFICIAL
  retrieval and grounding. FOLLOWUP, policy fallback, `PRIVACY_UNRESOLVED` and insufficient
  grounding make zero calls.
- Prompt input is bounded to the masked current question, minimum official facts and server-issued
  fact IDs. CANDIDATE/staging/mock/non-official data, source metadata, context/transcript,
  IDs and secrets are excluded.
- Strict fact-ID/summary validation materializes official fields and server-owned source/office.
  Timeout, transport, schema, ID or fact drift discards the entire draft and returns `TEMPLATE`.
- Existing idempotency is the sole persistence exception: with a caller-supplied key, a strictly
  validated final safe response may be replayed for the logical 24-hour TTL. Raw/masked question,
  prompt/provider body, context/correlation ID and secret remain forbidden.
- No DB migration, official/mock-data mutation, dependency or lockfile update belongs to LLM-003.

## Recorded commands and results

These are the actual task report results, not an inferred aggregate rerun.

| Area | Command/result |
|---|---|
| Contract | `pnpm --filter @sejong-ai/shared-contracts generate`, `generate:check`, and test passed; focused API pytest passed `76` tests. |
| API/runtime | `uv run --project apps/api --frozen pytest apps/api/tests -q` passed `1,923`, with `8` explicit local-DB-only skips and `5` subtests in `10.14s`; Task 6 Ruff, Mypy, docs check, secret scan and diff checks passed. |
| LLM service | `pytest apps/api/tests/chat -q` passed `189`; relevant fact/prompt/adapter/DB validator tests passed `96`; full API strict Mypy/Ruff/secret/diff gates passed in the Task 5 report. |
| Web | `corepack pnpm --filter @sejong-ai/web lint`, `typecheck`, `test`, and `build` passed; final Vitest result was `12 files / 56 tests`. |
| Web browser | Initial focused run was 9/12 with three failures solely from strict locator ambiguity at `home-chat-shell.spec.ts:70`; commit `7dd74f0` changed the locator to exact. Rerun `corepack pnpm --dir tools/web-e2e exec playwright test e2e/home-chat-shell.spec.ts` passed `12/12` across 390px/430px/desktop. |

## Final controller gate — PASS

Provider-disabled/unset-key execution:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1 -Offline
```

Started `2026-07-26T02:39:05+09:00`, completed `2026-07-26T02:49:42+09:00`, duration `637.7s`,
stdout `2006` bytes, stderr `0`. All listed verify steps PASSed: root, data, seed, Web, API,
contracts, secrets, bundle, package and diff. The stale environment-template assertion was corrected
in `scripts/tests/test_security_boundaries.py`; its exact targeted test PASSed and the root gate was
run afterward.

## Local actual — Pending human gate

No key was read and no provider network request was made while preparing this evidence. If a human
chooses to run the ignored local profile after the final offline gate, output only these approved
aggregate fields: `cases_total`, `generated_count`, `template_count`, `source_present_count`,
`official_fact_mismatch_count`, `pii_or_secret_persistence_count`, `outbound_attempt_count`,
`input_token_total`, `output_token_total`, `estimated_cost_usd`. A forced timeout must return
`TEMPLATE`. This is local demo evidence only, not public/remote or real-institution approval.

## Version and reproducibility boundary

The actual closeout axes are application `0.9.0-grounded-local-chat`, Web `0.6.0-answer-mode`, API
`3.2.0-draft`, shared contracts `0.5.0`, prompt set `0.2.0-grounded-live-chat`, test suite
`1.6.0-grounded-live-chat` and documentation `2.20.0`. `versions/manifest.json`, shared package
metadata `0.5.0` and the implementation-note INDEX are integrated.
Unchanged axes are product spec `2.5.0`, repo guidance `1.7.8`, database schema `0.4.0-local`,
official data `0.1.0-initial.2` and mock data `0.0.0-not-populated`.

Rollback is disable-first: set `UPSTAGE_GROUNDED_CHAT_MODE=false`, use the disabled provider profile,
remove the ignored local key, restart and verify deterministic `TEMPLATE`; see the
[local runbook](../runbooks/LLM-003-LOCAL-GROUNDED-CHAT.md).
