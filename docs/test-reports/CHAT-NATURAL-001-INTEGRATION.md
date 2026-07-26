# CHAT-NATURAL-001 Integration Gate Report

- Date: 2026-07-27 KST
- Branch: `codex/ACTUAL-P0-UX-GAPS-001`
- Baseline commit: `c9b9794`
- Scope: Slice 1~3, API/Web/contracts, DB 00100~00700, repository/root security gates
- Provider calls: 0
- Secret/DSN/raw citizen question output: 0

## Environment

| Runtime | Actual |
|---|---|
| Node.js | v24.12.0 |
| pnpm | 11.13.0 |
| Python | 3.12.13 |
| uv | 0.11.28 |
| Docker Engine | 29.2.1 |
| patched Supabase CLI | 2.109.1 |

## Final results

| Gate | Result | Evidence |
|---|---|---|
| API pytest | PASS | 2,137 passed, 8 local-DB-only skipped, 5 subtests passed |
| API Ruff | PASS | 110 files formatted; lint 0 |
| API Mypy | PASS | 110 source/test files, 0 issues |
| Shared contracts | PASS | 94/94; generated TypeScript drift 0 |
| Web | PASS | 60/60 unit; lint/typecheck/build PASS |
| Local DB | PASS | 11 pgTAP files, 385 tests, 11-stage rollback/absence/reapply and integration |
| Root | PASS | 433 discovered root cases; every declared runner stage PASS in 644.5s |
| Documentation/package | PASS | repository links/package manifest valid |
| Repository secret scan | PASS | finding 0; browser sentinel scan PASS |
| Diff | PASS | `git diff --check` |

The eight API skips are exactly the tests marked `local DB gate only`; the separate local DB runner
executed those integration boundaries against PostgreSQL.

## Failures found and corrected

1. The local database container had the correct project label and `127.0.0.1:54322` binding but the
   wrong default Supabase network. The gate rejected it before reset. The approved disposable runtime
   was stopped with the pinned patched CLI, recreated on `sejong-ai-local-loopback`, and the full DB
   gate passed.
2. Three current markers still described API `3.3.0-draft`. README, contract index and active API docs
   now match manifest/OpenAPI `4.0.0-draft`; the scaffold regression passes.
3. The security environment fixture omitted the eight approved classifier/shared-ledger variables.
   Exact safe defaults were added to the allowlist regression; secrets remain blank.
4. Ruff identified 13 files with formatting drift. The pinned formatter made mechanical changes;
   format/lint/tests pass.
5. One chat test accessed an optional fallback without narrowing. Explicit non-null assertions make
   the strict test typecheck pass without changing runtime behavior.

## Boundaries

- No production dependency was added.
- Official data release `0.1.0-initial.2` was not modified or formally imported in this gate.
- This report does not claim the 19→20 actual workflow, an actual Upstage aggregate, or remote/public
  deployment; those are separate approved tasks.
- Remote admin remains disabled until production authentication is separately designed and verified.

## Final closeout verification

The following fresh evidence was collected after the local DB actual, Upstage actual and remote
discovery commits:

| Gate | Final result |
|---|---|
| `scripts/verify.ps1` | exit `0`; 33 PASS stages, 0 FAIL, 668.1s |
| Web Playwright | 24/24 across 390, 430 and desktop |
| reported Korean/privacy/classification/followup/admin focus | 135/135 |
| local DB actual | `.2` 19/3/10 → separate approval ACTIVE 20 PASS |
| Upstage classifier actual | deterministic 40/provider 20, policy/privacy outbound 0, 60/60 PASS |
| remote/public | `Not executed: target not configured`; remote writes/requests 0 |

Final gate source before this documentation-only closeout was
`e4b8257f5d8e5fc9f9cf481ec41bfc9bb58b1f3c`. The root gate included Web lint/typecheck/unit/build,
API format/lint/typecheck/full tests, contracts generation/drift/tests, data/seed gates, package,
repository secret scan, browser bundle scan and diff check.

## Reproduction

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify_database.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1
```
