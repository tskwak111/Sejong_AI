# Local Demo Readiness and Performance Smoke Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provision the local context-token secret without exposing it, run a non-destructive provider-disabled final demo rehearsal, and prepare the separately gated 100-user performance smoke.

**Architecture:** A fixed-target Python provisioner resolves the primary checkout through Git common-dir, confirms `apps/api/.env` is ignored, and reuses the existing atomic env-assignment helper. Rehearsal evidence combines a bounded actual API/DB probe with the existing fixture-isolated browser suite. PERF-001 stays separate from this closeout and does not execute a chat load until its DB-write gate is explicitly approved.

**Tech Stack:** Python 3.12, `uv` 0.11.28, FastAPI/TestClient, local Supabase PostgreSQL, Node 24.12.0, pnpm 11.13.0, Playwright 1.61.1

## Global Constraints

- Local/private only; public/remote/deploy remains prohibited.
- External provider calls are zero; both Upstage modes are false for the rehearsal.
- No reset, seed, migration, purge, official-data mutation, or current-event KPI claim.
- No new production dependency.
- Secret, DSN, question, answer, provider body, and official record values must not appear in stdout, stderr, tracked files, Git diff, or implementation notes.
- `[db.seed].enabled=false` and immutable `0.1.0-initial.2` remain unchanged.

---

### Task 1: Safe local context-secret provisioner

**Files:**
- Create: `scripts/provision_local_context_secret.py`
- Create: `scripts/tests/test_provision_local_context_secret.py`
- Modify: `scripts/README.md`
- Modify: `docs/runbooks/LLM-003-LOCAL-GROUNDED-CHAT.md`

**Interfaces:**
- Consumes: `scripts.provision_local_database_login.update_env_assignment(path, key, value)`
- Produces: `resolve_primary_env_path() -> Path`, `provision_context_secret(path: Path) -> None`, `main() -> int`

- [ ] **Step 1: Write the failing fixed-target and preservation tests**

Create tests that import the script by file path, inject a synthetic Git common directory, and assert:

```python
assert runner.resolve_primary_env_path(common_git_dir) == root / "apps/api/.env"
assert other_assignment_bytes_are_unchanged
assert stored_secret != synthetic_old_secret
assert len(stored_secret.encode("utf-8")) >= 32
```

Also assert that a non-ignored target and a short/newline-bearing generated value fail before a
write, and that captured output contains neither old nor generated secret sentinels.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
.\.tools\uv\uv.exe run --project apps/api --frozen pytest `
  scripts/tests/test_provision_local_context_secret.py -q -p no:cacheprovider
```

Expected: collection or assertion failure because `scripts/provision_local_context_secret.py` does
not exist.

- [ ] **Step 3: Implement the minimal fixed-target provisioner**

Implement a no-argument command that:

```python
common_git_dir = resolve_git_common_dir()
env_path = resolve_primary_env_path(common_git_dir)
assert_target_is_gitignored(common_git_dir.parent, env_path)
secret = secrets.token_urlsafe(32)
validate_secret(secret)
update_env_assignment(env_path, "CONTEXT_TOKEN_SECRET", secret)
```

Use `subprocess.run` without `shell=True`, fixed Git arguments, suppressed ignore-check output, and
bounded exception-to-status mapping. Never return or print `secret`.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Task 1 focused command again.

Expected: all tests pass with no warning and no secret sentinel in output.

- [ ] **Step 5: Update the two runbooks**

Document only this value-free command:

```powershell
.\.tools\uv\uv.exe run --project apps/api --frozen python `
  scripts/provision_local_context_secret.py
```

State that it always targets the primary checkout's ignored `apps/api/.env` and accepts no supplied
secret or alternate path.

### Task 2: Apply and validate the local secret

**Files:**
- Modify outside Git: primary checkout `apps/api/.env` only
- Test: `apps/api/tests/test_local.py`
- Test: `scripts/tests/test_provision_local_context_secret.py`

**Interfaces:**
- Consumes: Task 1 command and the current ignored local DB URL
- Produces: a valid `LocalSettings` configuration without exposing field values

- [ ] **Step 1: Run the provisioner**

Run the Task 1 command from the isolated worktree. Expected stdout is exactly:

```text
[PASS] step=PROVISION-LOCAL-CONTEXT-SECRET
```

- [ ] **Step 2: Validate only presence and policy**

Load the primary `.env` through `load_local_settings(env_path=...)` and print only:

```text
LOCAL_SETTINGS_VALID=YES
CONTEXT_SECRET_MIN_BYTES=YES
```

Do not render the settings object or environment assignments.

- [ ] **Step 3: Verify Git isolation**

Run `git status --short` in the primary checkout and isolated worktree. The `.env` change must not
appear in either status or diff.

### Task 3: Provider-disabled final local rehearsal

**Files:**
- Create: `docs/test-reports/FINAL-LOCAL-DEMO-REHEARSAL.md`
- Modify: `TASKS.md`

**Interfaces:**
- Consumes: valid local settings, healthy existing ACTIVE 20 database, merged office route
- Produces: aggregate-only API/DB and browser evidence; no provider or destructive DB action

- [ ] **Step 1: Run focused provider-disabled API tests**

Run:

```powershell
.\.tools\uv\uv.exe run --project apps/api --frozen pytest `
  apps/api/tests/test_local.py `
  apps/api/tests/test_chat_route.py `
  apps/api/tests/test_offices_route.py `
  apps/api/tests/llm/test_architecture.py -q -p no:cacheprovider
```

Expected: zero failures; DB-only skips remain explicitly reported if applicable.

- [ ] **Step 2: Run the bounded actual API/DB probe**

Use the primary ignored env path, force both Upstage modes false in the process, and call the actual
local app through `TestClient`. Assert:

```text
HEALTH_STATUS=200
READY_STATUS=200
CHAT_STATUS=200
CHAT_ANSWER_STATUS=SUCCESS
CHAT_ANSWER_MODE=TEMPLATE
CHAT_SOURCE_COUNT>=1
PERSONAL_STATUS=200
PERSONAL_REASON=PERSONAL_LOOKUP
PERSONAL_CANDIDATE_ELIGIBLE=false
OFFICE_MATCH_STATUS=200
OFFICE_MATCH_COUNT=1
OFFICE_EMPTY_STATUS=200
OFFICE_EMPTY_COUNT=0
PROVIDER_ATTEMPTS=0
```

Print only these aggregate fields. Do not print request or response bodies.

- [ ] **Step 3: Run Web area gates once**

Run:

```powershell
corepack.cmd pnpm --filter @sejong-ai/web lint
corepack.cmd pnpm --filter @sejong-ai/web typecheck
corepack.cmd pnpm --filter @sejong-ai/web test
corepack.cmd pnpm --filter @sejong-ai/web build
corepack.cmd pnpm --dir tools/web-e2e test
```

Expected: lint, typecheck, unit, build, and all fixture-isolated 390/430/desktop projects pass.

- [ ] **Step 4: Record the rehearsal report**

Record source SHA, local-only boundary, aggregate results, test counts, warning/skip counts,
provider calls zero, reset/seed/purge zero, and the remaining human manual contrast/200%-zoom
walkthrough. Do not record fixture question text or any environment value.

### Task 4: PERF-001 executable plan and gate

**Files:**
- Modify: `TASKS.md`
- Modify: `docs/11_AMBIGUITY_REGISTER.md`
- Modify: `docs/source-of-truth/PROJECT_PLAN.md`
- Modify: `docs/source-of-truth/RFP_MATRIX.md`

**Interfaces:**
- Consumes: existing PER-001/PER-002 thresholds and D-077 non-KPI decision
- Produces: separate next-slice acceptance criteria without executing load

- [ ] **Step 1: Split read-only harness preflight from chat load**

Record fixed Phase A targets `/health` and one official office query, 100 virtual users, 60 seconds,
loopback-only destination, provider zero, aggregate-only output, and no DB write.

- [ ] **Step 2: Keep chat load behind a human DB-write gate**

Record that Phase B uses only a synthetic PII-free fixed question, provider-disabled TEMPLATE mode,
and cached/durable idempotency behavior. Require a separate approval selecting a disposable clean
database or accepting bounded writes to the current non-KPI local database.

- [ ] **Step 3: Freeze result fields and pass/fail rules**

Require request count, success count, error count/rate, p50, p95, max, average, duration, target
route identifier, source SHA, and provider-attempt count. Pass requires error rate below 1% and
average at or below 3 seconds; p95 is recorded without inventing an unapproved threshold.

### Task 5: Documentation, verification, and publication

**Files:**
- Modify: `docs/decisions/DECISION_LOG.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/12_VERSIONING_AND_RELEASES.md`
- Modify: `versions/manifest.json`
- Create: `docs/implementation-notes/IMP-20260726-014-local-demo-readiness-and-performance-plan.md`
- Modify: `docs/implementation-notes/INDEX.md`

**Interfaces:**
- Consumes: actual Task 1-4 evidence
- Produces: reproducible closeout and a human-reviewed Draft PR

- [ ] **Step 1: Generate and fill the implementation note**

Run:

```powershell
.\.tools\uv\uv.exe run --project apps/api --frozen python `
  scripts/new_implementation_note.py `
  --title "local demo readiness and performance plan" `
  --task-id DEMO-001-PERF-001 `
  --type implementation-verification-plan
```

Fill every applicable 6W1H, before/after version, security/privacy/data, exact command/result,
rollback, handoff, and human/AI boundary section. The generated identifier must be
`IMP-20260726-014`; stop on a collision rather than overwriting another note.

- [ ] **Step 2: Run final repository gates**

Run the full applicable provider-disabled repository gate once, plus:

```powershell
python -B scripts/check_repository_docs.py
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
git diff --check
git status --short
```

If the historical aggregate verifier still fails only at its recorded UV preflight, preserve the
failure and list every freshly passing constituent gate. Do not relabel it PASS.

- [ ] **Step 3: Review and publish**

Review the complete diff for secret values, runtime/contract changes, data mutations, dependency
changes, placeholders, and stale Pending statements. Commit, push
`codex/FINAL-DEMO-PERF-PLAN-001`, and create a Draft PR. Do not merge it.
