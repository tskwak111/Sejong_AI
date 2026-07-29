# A-075 DeepSeek Corrective Actual Discovery Audit

- Task ID: `A-075-DEEPSEEK-CORRECTIVE-ACTUAL`
- Date: 2026-07-29 KST
- Baseline: `67fe37c1bbc6dcda028fbf65f3694380ba399e2c`
- Human authority: `변수명 수정 완료, A-075 DeepSeek actual 1회 실행 승인`
- Status: Complete — no unresolved implementation blocker

## Purpose

Run one new local/private, fixed-synthetic DeepSeek classifier acceptance without changing product
behavior or rewriting A-074 evidence. This is a corrective evidence task after A-074's immutable
offline FAIL. It does not retroactively change A-074.

## Authorities and current state

The audit follows `AGENTS.md`, the active source-of-truth set, D-122/D-123, ADR-0028, the A-074
specification/plan/runbook and IMP-20260729-006. `legacy/` is not authority.

- PR #21 is merged to remote `main` at `67fe37c...`.
- The current branch was created directly from that remote commit; the user's divergent local
  `main` was not reset, rebased or merged.
- A-074 wrapper/result/report/lease are not invoked, deleted, copied or overwritten.
- The A-074 actual remains invocation/rerun `0/0`.
- The ignored local DeepSeek profile has the required key assignment and exact non-secret model,
  base URL and false mode values. The missing non-secret selector was added locally without
  reading or printing the key.

## Gap table

| Area | Existing A-074 state | A-075 requirement | Disposition |
|---|---|---|---|
| Offline identity | Consumed immutable FAIL 1/0 | New A-075 result/log/lease | Separate paths and gate name |
| Actual identity | A-074 unexecuted 0/0 | New A-075 report/lease, exactly one | Separate runner entry point |
| Provider implementation | Reviewed and merged | Reuse unchanged | No product-code change |
| Trust boundary | Exact five-string/`NONE` | Preserve | Shared parser and catalog |
| Fixed cases | 20/0, 11 deterministic, 9 provider | Preserve | Same immutable fixture hashes |
| Privacy | Aggregate-only | Preserve | No question/body/value/secret retention |
| Cost | USD 0.20 cap | Preserve | Retry 0, concurrency 1 |

## Options considered

1. **Minimal evidence-profile adapter — selected.** Keep the reviewed A-074 evaluator and
   transport, add one explicit gate-name seam, and bind A-075-only paths in a small runner.
   This minimizes duplicated security logic while keeping evidence files independent.
2. Copy the entire 1,473-line actual runner. This isolates identity but creates a large duplicate
   that can drift from security fixes.
3. Refactor the runner into a broad generic framework. This is cleaner long-term but too invasive
   for a one-shot corrective task.

## Safety and failure boundaries

- A-075 offline wrapper runs once. PASS or FAIL is immutable and rerun remains zero.
- Actual readiness is network-free and does not consume the actual lease.
- Actual runs once only after clean-source offline PASS.
- The first actual lease is permanent even after timeout, crash or FAIL.
- The runner retains aggregates only and caps execution at 32 seconds and USD 0.20.
- No automatic retry, provider cascade, public/remote operation or real citizen input is allowed.

## Ambiguity disposition

| ID | Priority | Decision | Status |
|---|---|---|---|
| `A-075-ACTUAL` | A | New identity and exact one DeepSeek actual | Resolved by user |
| Local main divergence | B | Preserve local main; branch from `origin/main` | Resolved internally |
| Evidence adapter shape | C | Minimal profile adapter | Defaulted |
| File split and helper names | D | TDD-driven internal choice | Internal |

No A/Blocker remains.
