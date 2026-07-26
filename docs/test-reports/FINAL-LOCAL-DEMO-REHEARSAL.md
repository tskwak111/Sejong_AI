# Final Local Demo Rehearsal

- Date/Time: 2026-07-26T19:15:47+09:00
- Source baseline: `bcaf39cdd8d7e903fa35705cda6f7d6c7fb433d7`
- Scope: local/private, provider-disabled, existing ACTIVE 20 database
- Result: Automated rehearsal PASS; human manual accessibility walkthrough Pending

## Boundaries

- Upstage synthetic and grounded-chat modes were both forced off in the rehearsal process.
- External provider runtime factory calls: `0`.
- Database reset, seed, migration, compensation, purge and delete: `0`.
- The existing official release `0.1.0-initial.2` and current ACTIVE 20 projection were not changed.
- A single supported synthetic evaluation request exercised the normal metadata-only citizen event
  path. The current local event rows remain non-authoritative for KPI under D-077.
- No question, answer, provider payload, secret, DSN, official record, address, phone or URL value
  was printed or written to this report.

## Local configuration and runtime

| Check | Result |
|---|---|
| Context secret fixed-target provisioner | PASS; value output 0 |
| `load_local_settings` | `LOCAL_SETTINGS_VALID=YES` |
| Context secret minimum | `CONTEXT_SECRET_MIN_BYTES=YES` |
| Docker client/server | `29.2.1` / `29.2.1` |
| Docker context | `desktop-linux` |
| Local database container | healthy |
| Database port | exact `127.0.0.1:54322` |
| Pinned patched Supabase verify | PASS from primary checkout |

The first patched-binary verification from the linked worktree stopped with
`VERIFY-PATCHED-SUPABASE-BINARY reason=missing code=2`. Root cause was path scope: the verifier
resolves `.tools` under the executing checkout, while `.tools` intentionally exists only in the
primary checkout and is not copied into worktrees. The same tracked verifier passed from the
primary checkout. No tool or secret was copied.

## Actual API/DB rehearsal

| Evidence | Actual |
|---|---:|
| `HEALTH_STATUS` | 200 |
| `READY_STATUS` | 200 |
| `CHAT_STATUS` | 200 |
| `CHAT_ANSWER_STATUS` | SUCCESS |
| `CHAT_ANSWER_MODE` | TEMPLATE |
| `CHAT_SOURCE_COUNT` | 1 |
| `PERSONAL_STATUS` | 200 |
| `PERSONAL_REASON` | PERSONAL_LOOKUP |
| `PERSONAL_CANDIDATE_ELIGIBLE` | false |
| `OFFICE_MATCH_STATUS` | 200 |
| `OFFICE_MATCH_COUNT` | 1 |
| `OFFICE_EMPTY_STATUS` | 200 |
| `OFFICE_EMPTY_COUNT` | 0 |
| `ADMIN_APPROVED_STATUS` | 200 |
| `ADMIN_APPROVED_COUNT` | 1 |
| `PROVIDER_ATTEMPTS` | 0 |

This run checks the PERSONAL response policy but is not a new post-read database forensic proof of
its no-event/no-failed-row invariant. The existing governed actual 19-to-20 report remains the
authority for exact PERSONAL persistence delta `0/0`.

## Automated test evidence

| Command area | Result |
|---|---|
| Context provisioner RED | expected 7 failures because the provisioner was missing |
| Context provisioner GREEN | 7 passed in 1.27s |
| Provider-disabled local/chat/office/LLM architecture | 64 passed in 2.20s; pre-existing Starlette warning 1 |
| Web lint | PASS |
| Web typecheck | PASS |
| Web unit | 12 files / 56 tests passed |
| Web production build | PASS |
| Web Playwright fixture-isolated | 21/21 passed across 390, 430 and desktop |

Next build/serve emitted the known nested-worktree multiple-lockfile root-inference warning. Build
and all browser projects passed. No lockfile or dependency changed.

## Final repository closeout

| Gate | Result |
|---|---|
| Aggregate `scripts/verify.ps1 -Offline` | **NOT PASS** — stopped at `PREFLIGHT-UV reason=exception code=2` because the isolated worktree intentionally has no ignored `.tools/uv` |
| Provisioner format/lint/focused test | PASS — 2 files formatted, Ruff PASS, 7/7 in 1.06s |
| API full format/lint/type/test | PASS — 105 files formatted, Ruff PASS, MyPy PASS, 2,044 passed, 8 DB-only skipped, 5 subtests passed, pre-existing Starlette warning 1 |
| Root worktree suite | 429 passed, 2 skipped; exactly 2 environment failures because `.tools/supabase.exe` is absent in the isolated worktree |
| Exact failed root checks from primary tool checkout | PASS — test/runtime-manifest source SHA-256 matched the worktree, 2/2 passed in 1.793s |
| Shared contracts | PASS — generated drift check and 90/90 tests |
| Documentation / secret / package / diff | PASS |

The two worktree root failures do not indicate a product or tracked-code regression, but the
aggregate verifier is still recorded as **NOT PASS**. No `.tools` directory, binary, junction or
secret was copied into the worktree to manufacture a green result.

## Human manual Pending

- Browser zoom 200% with no clipped primary action.
- Visual contrast and large-text judgment on the user's display.
- Keyboard-only walkthrough of the five-question demo and feedback dialog focus return.
- Final presentation timing and spoken explanation.

These manual checks cannot be replaced by the automated PASS above.
