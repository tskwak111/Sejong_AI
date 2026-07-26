# LLM-003 Grounded Live Chat — Local/Private Evidence Report

- Report status: Offline implementation, provider-disabled final repository gate and D-075
  local/private actual acceptance complete; public/remote use remains prohibited.
- Scope: D-072~D-075 / local-private only.
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
`C0/I0/M0`. A later frozen whole-branch review at `1c32c1c` found that the two independent Python
replay validators still accepted camelCase/separator credential and conversation aliases in
forward-compatible Office extras. The final fix wave added focused RED tests, then canonicalized
every recursive mapping key independently at the claim and repository boundaries before comparison.
It also synchronized the stale authority status and removed the duplicated human actual-gate bullet.

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
  prompt/provider body, context/correlation ID and secret remain forbidden, including camelCase and
  non-alphanumeric separator variants of the canonical aliases.
- No DB migration, official/mock-data mutation, dependency or lockfile update belongs to LLM-003.

## Final review fix wave

| Gate | Exact result |
|---|---|
| Clean baseline | claim/repository validator test files `85 passed in 0.48s` |
| TDD RED | canonical-alias regressions `54 failed, 85 deselected in 0.96s`; failures were the expected missing exceptions |
| Focused GREEN | new regressions `54 passed, 85 deselected in 0.52s`; both complete validator files `139 passed in 0.69s` |
| Chat | final fresh run `220 passed in 0.81s` |
| Repository | final fresh run `120 passed in 0.74s` |
| Security | final fresh run `19 passed, 1 skipped, 8 subtests passed in 21.87s`; the skip is the existing environment-only gate |
| Static | Ruff format/check and Mypy passed for the four touched Python source/test files |
| Repository hygiene | documentation checker, secret scan and `git diff --check` passed |

No provider key, provider network, DB actual, dependency, lockfile, migration or official/mock data
was used or changed in this wave. The immutable `00660` migration was not edited.

## Recorded commands and results

These are the actual task report results, not an inferred aggregate rerun.

| Area | Command/result |
|---|---|
| Contract | `pnpm --filter @sejong-ai/shared-contracts generate`, `generate:check`, and test passed; focused API pytest passed `76` tests. |
| API/runtime | `uv run --project apps/api --frozen pytest apps/api/tests -q` passed `1,923`, with `8` explicit local-DB-only skips and `5` subtests in `10.14s`; Task 6 Ruff, Mypy, docs check, secret scan and diff checks passed. |
| LLM service | `pytest apps/api/tests/chat -q` passed `189`; relevant fact/prompt/adapter/DB validator tests passed `96`; full API strict Mypy/Ruff/secret/diff gates passed in the Task 5 report. |
| Final replay fix | Focused claim/repository RED→GREEN passed as recorded above; final chat `220`, repository `120`, security `19 + 1 skip + 8 subtests`, Ruff and Mypy passed. |
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

Final review then found and closed the replay-key canonicalization gap in commit `aaf67fe`. At that
exact HEAD, the controller reran the same provider-disabled/unset-key command from a clean worktree:
exit `0` after `728.7s`. PREFLIGHT, package/API sync, root/data/seed, Web lint/typecheck/test/build,
API format/lint/typecheck/test, generated contracts, repository secret scan, Web bundle scan,
package validation and diff verification all PASSed. This post-fix run is the publication gate.

## Local actual — PASS

D-075 authorized one local/private acceptance gate after the offline publication gate. The final
run used the ignored local key and exact Upstage `solar-pro3` profile through the real
`/api/v1/chat` path and local DB. Its stdout was exactly one aggregate JSON object:

```json
{"cases_total":10,"generated_count":4,"template_count":6,"source_present_count":10,"official_fact_mismatch_count":0,"pii_or_secret_persistence_count":0,"outbound_attempt_count":10,"input_token_total":4183,"output_token_total":954,"estimated_cost_usd":"0.001319835"}
```

This is the legacy runner's emitted aggregate. Because that revision did not require a positive
usage observation on every outbound result, 4183/954 and USD 0.001319835 are a reported lower bound,
not a complete billing proof. The configured worst case for ten calls is
`10 × (4096 × $0.15/M + 1024 × $0.60/M) × 1.10 = $0.0135168`, still below the USD 0.05 cap.
The current runner requires usage-bearing results for all ten attempts, but it has not been used for
another actual network run.

All ten SUCCESS responses retained a server-owned official source. Four provider drafts passed the
strict fact gate; six were discarded and returned the deterministic official TEMPLATE. A separate
historical forced probe observed TEMPLATE without an eleventh provider call. The current runner
additionally requires proof that the injection was consumed; that guard is future-only. No question, answer,
provider body, key or DSN was printed. The reported
`pii_or_secret_persistence_count=0` is a typed `InteractionWrite` pre-write check over PII-free
fixtures (raw fixture/API key absent, `masked_question=None`), not a post-read DB forensic scan;
schema and repository tests separately enforce the no-content persistence shape.

The first semantically passing run produced GENERATED 6/TEMPLATE 4 at USD 0.001315875 but a
dependency emitted safe request metadata after the JSON. The harness was corrected and rerun so the
final evidence above satisfies the aggregate-only output contract. Therefore the two successful
bounded runs used 20 provider calls and reported a lower-bound USD 0.002635710 including VAT;
the configured 20-call upper bound is USD 0.0270336. This evidence
is local/private only; Cloud/CI, public/remote and real-institution operation remain unapproved.
D-075/runbook authorized one 10-call gate. The corrective second 10-call run did not receive a
separate explicit human approval, so it is recorded as a governance incident requiring A-049 human
acknowledgement before Draft PR merge; it is not used to broaden future network authority.

After the run, process-only profile values were removed. A disabled-profile verification returned
`/ready=200` and `answer_mode=TEMPLATE`.

### Final review correction

The two successful runs predated the final review correction and therefore wrote 22 metadata-only
interaction rows with `is_test=false`. Those rows contain no question, answer or provider payload,
but their label is incorrect and they must be excluded from EVENT/KPI evidence. The final runner
forces all future evaluation writes to `is_test=true` and raises before delegating any detected
forbidden-value write. Because the 22 rows have no unique evaluation marker, this branch does not
delete them: a disposable local DB reset or a separately bounded cleanup requires explicit human
DB-data deletion approval.

## Current-slice publication gate — PASS

Final review added current-runner usage completeness, forced-timeout consumption, evaluation-row
labelling, forbidden-value pre-write checks and exact local database role/membership drift guards.
Focused verification passed: actual runner `10`, local DB provision `11` with `14` subtests, LLM
contract/adapter `40`, native Ruff lint/format for the changed files and strict mypy for four source
files.

The first current-slice `scripts/verify.ps1 -Offline` attempt stopped at `TEST-ROOT` because the
worktree did not contain the Git-ignored pinned patched Supabase binary. The binary in the local
source workspace was accepted only after its SHA-256 matched the tracked runtime manifest, then was
copied to the worktree's ignored `.tools` path. Both previously failing runtime artifact tests
passed in isolation. A fresh controller run then exited `0` after `749.9s`; every root, data, seed,
Web, API, contract, repository secret, Web bundle, package and diff step passed. This was
provider-disabled and made no Upstage actual call.

## Version and reproducibility boundary

The actual-evidence closeout axes are application `0.9.1-grounded-local-chat-evidence`, Web
`0.6.0-answer-mode`, API
`3.2.0-draft`, shared contracts `0.5.0`, prompt set `0.2.0-grounded-live-chat`, test suite
`1.6.1-grounded-actual` and documentation `2.20.1`. `versions/manifest.json`, shared package
metadata `0.5.0` and the implementation-note INDEX are integrated.
Unchanged axes are product spec `2.5.0`, repo guidance `1.7.8`, database schema `0.4.0-local`,
official data `0.1.0-initial.2` and mock data `0.0.0-not-populated`.

Rollback is disable-first: set `UPSTAGE_GROUNDED_CHAT_MODE=false`, use the disabled provider profile,
remove the ignored local key, restart and verify deterministic `TEMPLATE`; see the
[local runbook](../runbooks/LLM-003-LOCAL-GROUNDED-CHAT.md).
