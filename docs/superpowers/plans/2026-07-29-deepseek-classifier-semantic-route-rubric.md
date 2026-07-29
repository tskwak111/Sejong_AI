# A-080 DeepSeek Classifier Semantic Route Rubric Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the fixed DeepSeek classifier oracle result from the historical `6/9` by teaching
the shared bounded prompt the exact five-route semantics, while preserving the existing
privacy-first, server-validated, fail-closed contract.

**Architecture:** Rewrite the provider-neutral system instruction in
`classifier_prompt.py` as a compact semantic rubric instead of adding a provider-specific prompt.
Both Upstage and DeepSeek continue to consume `build_classifier_messages(...)`; the existing parser,
catalog validation, ACTIVE/OFFICIAL grounding, storage policy and deterministic safety gates remain
the trust boundary. New A-080 offline and actual evidence identities are disjoint from immutable
A-074~A-079 evidence.

**Tech Stack:** Python 3.12.13, existing `httpx` 0.28.1, pytest 9.1.1, Ruff 0.15.21,
Mypy 2.3.0, PowerShell 5.1, existing DeepSeek `deepseek-v4-flash` adapter.

## Global Constraints

- A-074~A-079 reports, leases, invocation counts and source bindings are immutable.
- The exact provider wire remains five required strings in this order:
  `route`, `intent`, `topic_id`, `coverage_id`, `pending_slot`.
- Nullable wire values allow exact uppercase `NONE` only.
- Safety/privacy/policy and clearly deterministic questions remain provider-free.
- Only privacy-safe ambiguous questions may make one classifier call.
- The provider cannot create facts, sources, offices, candidate eligibility or storage policy.
- Citizen retrieval remains request-local ACTIVE/OFFICIAL top-1 with server revalidation.
- DeepSeek stays classifier-only; the final citizen-answer provider is unchanged.
- Connect/write/pool timeout stays `3.0s`; read/complete exchange stays `10.0s`.
- Retry `0`, concurrency `1`, output `128`, temperature `0`, cost cap USD `0.20`.
- The 20-topic/256-character complete prompt must stay at or below `4096` conservative characters,
  and the DeepSeek UTF-8 plus framing bound must stay at or below `16384`.
- No new production dependency, public API, DB migration, official data, Web, public/remote or
  real-citizen free-input change.
- No provider call is authorized by plan approval. A-080 actual needs the separate exact approval
  `A-080 DeepSeek actual 1회 실행 승인`.
- No automatic rerun and no automatic merge.

---

### Task 1: Add the semantic rubric with an observed RED/GREEN cycle

**Files:**

- Modify: `apps/api/tests/llm/test_prompt.py`
- Modify: `apps/api/src/sejong_ai_api/llm/classifier_prompt.py`

**Interfaces:**

- Consumes:
  `build_classifier_messages(question: SafeQuestion, catalog: TopicCatalog, *, max_input_chars: int)`.
- Produces: the same `tuple[dict[str, str], ...]` message contract with an expanded semantic system
  instruction.
- Preserves: `_build_grouped_catalog(...)`, user payload keys `ask`, `cat`, `ex`, and all
  validation errors.

- [x] **Step 1: Add one behavior-named failing test**

  Add this test to `apps/api/tests/llm/test_prompt.py`:

  ```python
  def test_classifier_prompt_defines_route_semantics_and_selection_precedence() -> None:
      system = build_classifier_messages(
          _safe_question(),
          _catalog(),
          max_input_chars=1024,
      )[0]["content"]

      for rule in (
          "SUPPORTED=one cat row covers ask",
          "NO_TOPIC_MATCH=supported intent/no row covers asked fact/procedure",
          "CIVIC_SCOPE_GAP=government/admin service outside intents",
          "NON_CIVIC=not government/admin service",
          "NEEDS_FOLLOWUP=missing/ambiguous detail blocks safe choice",
          "pick narrowest covered row",
          "exclusions bind",
      ):
          assert rule in system
  ```

- [x] **Step 2: Run the new test and capture the expected RED**

  Run:

  ```powershell
  Push-Location apps/api
  .\.venv\Scripts\python.exe -m pytest `
    tests/llm/test_prompt.py::test_classifier_prompt_defines_route_semantics_and_selection_precedence `
    -q
  Pop-Location
  ```

  Expected: one failure because the current prompt defines tuple shapes but not these semantic
  meanings or precedence.

- [x] **Step 3: Replace, rather than append to, the compact system instruction**

  Rewrite `_SYSTEM_MESSAGE` in `classifier_prompt.py` to include these compact behavior clauses.
  The compact clauses are the approved meanings, not aliases that may appear in provider output.
  Retain the exact five field names, four intent values plus `NONE`, uppercase-ASCII `NONE`,
  catalog row grammar, same-row rule and every legal route shape:

  ```python
  _SYSTEM_MESSAGE = (
      "JSON only;"
      "keys=route,intent,topic_id,coverage_id,pending_slot;"
      "5 strings;"
      "no extra/prose/MD;"
      "NONE uppercase ASCII;"
      "translation/null/empty forbidden;"
      "intents=MOVE_IN_RESIDENT_REGISTRATION|CERTIFICATE_ISSUANCE|"
      "BULKY_WASTE|LOCAL_TAX_GENERAL|NONE;"
      "cat[intent]=[topic_id,coverage_id,coverage_label,approved_examples];"
      "SUPPORTED=one cat row covers ask;"
      "NO_TOPIC_MATCH=supported intent/no row covers asked fact/procedure;"
      "CIVIC_SCOPE_GAP=government/admin service outside intents;"
      "NON_CIVIC=not government/admin service;"
      "NEEDS_FOLLOWUP=missing/ambiguous detail blocks safe choice;"
      "pick narrowest covered row;"
      "exclusions bind;"
      "SUPPORTED:intent/topic_id/coverage_id=same row,pending_slot=NONE;"
      "NO_TOPIC_MATCH:intent=supported,other3=NONE;"
      "CIVIC_SCOPE_GAP/NON_CIVIC:other4=NONE;"
      "NEEDS_FOLLOWUP:topic_id/coverage_id=NONE;"
      "pairs=NONE:DOMAIN|supported:TOPIC_CHOICE/REGION|"
      "CERTIFICATE_ISSUANCE:CERTIFICATE_KIND|BULKY_WASTE:WASTE_ITEM;"
  )
  ```

  The measured system instruction is `899` characters. Do not expand it past the existing complete
  prompt bound. Do not remove a route meaning, selection precedence, shape, intent or
  uppercase-`NONE` rule.

- [x] **Step 4: Update stale prose assertions without weakening invariants**

  In `test_classifier_prompt_forbids_none_translations_null_and_explanatory_output`, assert the
  compact strict-JSON, five-string, forbidden-null/empty/translation and uppercase-ASCII clauses.
  Update the catalog, same-row and route-shape assertions to their compact equivalents without
  removing any field, intent, route or allowed pending-slot pairing. Do not replace them with
  source-code introspection.

- [x] **Step 5: Run all prompt tests and confirm GREEN**

  Run:

  ```powershell
  Push-Location apps/api
  .\.venv\Scripts\python.exe -m pytest tests/llm/test_prompt.py -q
  Pop-Location
  ```

  Expected: every prompt test passes, including the real 19/20-topic preservation and 4096 bounds.

- [x] **Step 6: Commit the isolated prompt cycle**

  ```powershell
  git add apps/api/src/sejong_ai_api/llm/classifier_prompt.py `
    apps/api/tests/llm/test_prompt.py
  git commit -m "fix(llm): define classifier route semantics"
  ```

### Task 2: Prove both providers consume the same bounded rubric

**Files:**

- Modify: `apps/api/tests/llm/test_deepseek_classifier.py`
- Modify: `apps/api/tests/llm/test_upstage_classifier.py`
- Test: `apps/api/tests/llm/test_prompt.py`

**Interfaces:**

- Consumes: shared `build_classifier_messages(...)`.
- Preserves:
  `DeepSeekQuestionClassifier.classify(...) -> ClassifierDecision | None` and
  `UpstageQuestionClassifier.classify(...) -> ClassifierDecision | None`.
- Produces: request-boundary evidence that neither adapter owns a prompt fork.

- [x] **Step 1: Strengthen the DeepSeek request-boundary test**

  In `test_success_posts_one_exact_deepseek_json_object_request`, retain the complete equality
  against `build_classifier_messages(...)` and add:

  ```python
  system = request_payload["messages"][0]["content"]
  assert "choose the narrowest covering row" in system
  assert "coverage exclusions are binding" in system
  assert request_payload["response_format"] == {"type": "json_object"}
  assert request_payload["thinking"] == {"type": "disabled"}
  assert request_payload["temperature"] == 0
  assert request_payload["max_tokens"] == 128
  ```

- [x] **Step 2: Strengthen the Upstage request-boundary test**

  In the successful strict-schema request test, retain exact message equality and add:

  ```python
  system = request_payload["messages"][0]["content"]
  assert "choose the narrowest covering row" in system
  assert "coverage exclusions are binding" in system
  assert request_payload["temperature"] == 0
  assert request_payload["max_tokens"] == 128
  ```

- [x] **Step 3: Prove prompt data minimization at the actual consumer boundary**

  Assert that neither captured request contains `answer_summary`, `procedure_steps`,
  `required_documents`, `fee`, `source_title`, `source_url`, `last_verified_at`, `department`,
  `caution`, API key or DSN. Keep the existing `httpx.MockTransport`; do not introduce a new mock
  library.

- [x] **Step 4: Run both provider suites**

  ```powershell
  Push-Location apps/api
  .\.venv\Scripts\python.exe -m pytest `
    tests/llm/test_prompt.py `
    tests/llm/test_deepseek_classifier.py `
    tests/llm/test_upstage_classifier.py `
    -q
  Pop-Location
  ```

  Expected: prompt, request shape, parser stages, timeout/fallback and non-retention tests all pass.

- [x] **Step 5: Commit provider-neutral request proof**

  ```powershell
  git add apps/api/tests/llm/test_deepseek_classifier.py `
    apps/api/tests/llm/test_upstage_classifier.py
  git commit -m "test(llm): lock shared classifier rubric"
  ```

### Task 3: Create disjoint A-080 one-shot evidence identities

**Files:**

- Create: `scripts/run_deepseek_classifier_quality_actual.py`
- Create: `scripts/tests/test_run_deepseek_classifier_quality_actual.py`
- Create: `scripts/run_a080_offline_gate.ps1`
- Create: `scripts/tests/test_run_a080_offline_gate.py`

**Interfaces:**

- Consumes: existing `run_deepseek_classifier_actual.EvidenceIdentity` and the reviewed A-079
  wrappers.
- Produces: `A080_EVIDENCE_IDENTITY`, a fresh offline wrapper and a readiness-capable actual entry
  point.
- Does not produce: a provider call, lease or permanent report during this task.

- [ ] **Step 1: Add failing identity tests**

  Require exactly:

  ```python
  assert identity.report_path.name == (
      "CHAT-HYBRID-RAG-001-DEEPSEEK-A080-ACTUAL.md"
  )
  assert identity.offline_gate == "A-080-OFFLINE"
  assert identity.offline_lease_text == "A-080-OFFLINE-GATE one-shot lease\n"
  assert identity.actual_lease_text == "A-080-DEEPSEEK-CLASSIFIER one-shot lease\n"
  assert identity.actual_run_deadline_seconds == 100
  ```

  Also compare the A-080 report/result/lock/stdout/stderr paths against A-074~A-079 and assert every
  path differs.

- [ ] **Step 2: Run the identity tests and observe RED**

  ```powershell
  apps/api/.venv/Scripts/python.exe -m pytest `
    scripts/tests/test_run_deepseek_classifier_quality_actual.py `
    scripts/tests/test_run_a080_offline_gate.py `
    -q
  ```

  Expected: import/file-not-found failure because the A-080 wrappers do not exist.

- [ ] **Step 3: Implement the thin A-080 actual wrapper**

  Define `_OFFLINE_DIRECTORY` as
  `.superpowers/sdd/2026-07-29-deepseek-classifier-quality` and create:

  ```python
  A080_EVIDENCE_IDENTITY = _core.EvidenceIdentity(
      report_path=(
          _REPOSITORY_ROOT
          / "docs"
          / "test-reports"
          / "CHAT-HYBRID-RAG-001-DEEPSEEK-A080-ACTUAL.md"
      ),
      offline_result_path=_OFFLINE_DIRECTORY / "a080-offline-gate-result.json",
      offline_lock_path=(
          _OFFLINE_DIRECTORY / "a080-offline-gate-result.json.run.lock"
      ),
      offline_stdout_path=_OFFLINE_DIRECTORY / "a080-offline-gate.stdout.log",
      offline_stderr_path=_OFFLINE_DIRECTORY / "a080-offline-gate.stderr.log",
      offline_gate="A-080-OFFLINE",
      offline_lease_text="A-080-OFFLINE-GATE one-shot lease\n",
      actual_lease_text="A-080-DEEPSEEK-CLASSIFIER one-shot lease\n",
      actual_run_deadline_seconds=100,
      pre_actual_check=None,
  )
  ```

  The wrapper delegates to `_core.main(..., evidence_identity=A080_EVIDENCE_IDENTITY)`. It must not
  read or print the API key. No probe is added: A-079 already proved transport/wire and A-080 is a
  quality-only successor.

- [ ] **Step 4: Mechanically clone the hardened offline wrapper under A-080 identity**

  Preserve the A-079 implementation and change only:

  ```powershell
  $ResultRelativePath = ".superpowers\sdd\2026-07-29-deepseek-classifier-quality\a080-offline-gate-result.json"
  $LockRelativePath = ".superpowers\sdd\2026-07-29-deepseek-classifier-quality\a080-offline-gate-result.json.run.lock"
  $StdoutRelativePath = ".superpowers\sdd\2026-07-29-deepseek-classifier-quality\a080-offline-gate.stdout.log"
  $StderrRelativePath = ".superpowers\sdd\2026-07-29-deepseek-classifier-quality\a080-offline-gate.stderr.log"
  $LeaseText = "A-080-OFFLINE-GATE one-shot lease`n"
  ```

  The result JSON gate must be `A-080-OFFLINE`, and console terminals must be
  `A080_OFFLINE_GATE_PASS`, `A080_OFFLINE_GATE_FAIL` and the corresponding bounded error names.

- [ ] **Step 5: Test exact-LF, one-shot and failure behavior**

  The controlled repository tests must prove:

  - lease bytes are exactly `b"A-080-OFFLINE-GATE one-shot lease\n"`;
  - second invocation is rejected;
  - source dirtiness, timeout and non-zero root verification close FAIL;
  - no provider endpoint or secret is used;
  - actual readiness rejects absent/wrong offline evidence and an existing actual report.

- [ ] **Step 6: Run controlled wrapper tests and parser check**

  ```powershell
  apps/api/.venv/Scripts/python.exe -m pytest `
    scripts/tests/test_run_deepseek_classifier_quality_actual.py `
    scripts/tests/test_run_a080_offline_gate.py `
    -q
  [void][ScriptBlock]::Create((Get-Content -Raw scripts/run_a080_offline_gate.ps1))
  ```

  Expected: all tests pass and the PowerShell parser raises no exception. This step does not run the
  real A-080 offline gate or provider.

- [ ] **Step 7: Commit the evidence harness**

  ```powershell
  git add scripts/run_deepseek_classifier_quality_actual.py `
    scripts/tests/test_run_deepseek_classifier_quality_actual.py `
    scripts/run_a080_offline_gate.ps1 `
    scripts/tests/test_run_a080_offline_gate.py
  git commit -m "test(llm): isolate A-080 quality evidence"
  ```

### Task 4: Synchronize versions and implementation authority

**Files:**

- Modify: `versions/manifest.json`
- Modify: `docs/source-of-truth/TEAM_DECISIONS.md`
- Modify: `docs/source-of-truth/PROJECT_PLAN.md`
- Modify: `docs/source-of-truth/RFP_MATRIX.md`
- Modify: `docs/decisions/DECISION_LOG.md`
- Modify: `docs/adr/0028-selectable-deepseek-classifier-provider.md`
- Modify: `docs/11_AMBIGUITY_REGISTER.md`
- Modify: `TASKS.md`
- Modify: `CHANGELOG.md`
- Create: `docs/implementation-notes/IMP-20260729-013-a-080-semantic-route-rubric-offline.md`
- Modify: `docs/implementation-notes/INDEX.md`

**Interfaces:**

- Produces versions:
  application `0.13.3-classifier-semantic-rubric`,
  prompt `0.4.4-semantic-route-rubric`,
  tests `2.2.9-a080-quality`,
  documentation `2.32.3-a080-quality-offline`.
- Preserves API `4.0.0-draft`, shared contracts `1.0.0`, DB `0.5.0-local`, Web
  `0.8.0-guided-chat`, official data `0.1.0-initial.2`.

- [ ] **Step 1: Record implementation truth without claiming actual quality**

  Add D-135 only after Tasks 1~3 pass. It must say the rubric and new evidence identities are
  implemented provider-offline, while A-080 actual remains unexecuted and requires a separate
  approval.

- [ ] **Step 2: Update the ADR, task and requirement status**

  Mark the A-080 specification and plan Approved, implementation Offline Review, and keep
  `SFR-002` at “A-079 transport/wire verified; quality FAIL 6/9” until a new actual proves otherwise.

- [ ] **Step 3: Write the implementation note**

  Generate it with:

  ```powershell
  apps/api/.venv/Scripts/python.exe -B scripts/new_implementation_note.py `
    --title "A-080 semantic route rubric offline 구현" `
    --task-id A-080-DEEPSEEK-CLASSIFIER-QUALITY `
    --type implementation-provider-offline
  ```

  Fill 6W1H, RED/GREEN evidence, changed interfaces, exact commands/results, version before/after,
  privacy/security/cost effect, no official/mock data change, rollback, handoff and the separate
  actual approval gate. Append exactly one INDEX row.

- [ ] **Step 4: Commit authority synchronization**

  ```powershell
  git add versions/manifest.json docs TASKS.md CHANGELOG.md
  git commit -m "docs(llm): record A-080 offline implementation"
  ```

### Task 5: Run area verification and independent reviews

**Files:**

- Review only: all files changed by Tasks 1~4.

**Interfaces:**

- Produces: a clean, reviewable source candidate.
- Does not consume: provider quota, API key, DB, Docker or remote infrastructure.

- [ ] **Step 1: Run the complete related-area tests once**

  ```powershell
  Push-Location apps/api
  .\.venv\Scripts\python.exe -m pytest `
    tests/llm `
    ../../scripts/tests/test_run_deepseek_classifier_actual.py `
    ../../scripts/tests/test_run_deepseek_classifier_network_retry_actual.py `
    ../../scripts/tests/test_run_deepseek_classifier_quality_actual.py `
    ../../scripts/tests/test_run_a080_offline_gate.py `
    -q
  Pop-Location
  ```

  Expected: zero failures. Record exact pass/skip counts rather than copying counts from this plan.
  The existing controlled-double runner cases must still prove selected/skip `20/0`,
  provider-free/provider `11/9`, policy/privacy outbound `0` and accepted/oracle `9/9`.

- [ ] **Step 2: Run static checks**

  ```powershell
  Push-Location apps/api
  .\.venv\Scripts\python.exe -m ruff format --check src tests
  .\.venv\Scripts\python.exe -m ruff check src tests
  .\.venv\Scripts\python.exe -m mypy src tests
  Pop-Location
  ```

- [ ] **Step 3: Run repository documentation, secret and diff checks**

  ```powershell
  apps/api/.venv/Scripts/python.exe -B scripts/check_repository_docs.py
  powershell -NoProfile -ExecutionPolicy Bypass `
    -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
  git diff --check
  git status --short
  ```

- [ ] **Step 4: Review spec compliance**

  The reviewer must report counts for Critical/Important/Minor and explicitly verify:

  - all five route meanings and precedence are present;
  - both providers use the same messages;
  - exact wire/parser/fail-closed behavior is unchanged;
  - A-079 artifacts are untouched;
  - actual/provider call count is zero.

- [ ] **Step 5: Review privacy and evidence safety**

  The reviewer must verify no question, masked question, provider body, invalid field value, API
  key, DSN or exception detail is written by the new wrappers and that no source/official fact is
  accepted from the provider.

- [ ] **Step 6: Fix findings with focused RED/GREEN tests**

  Any Critical or Important finding blocks the clean-source checkpoint. Add a failing regression
  test, observe RED, make the minimum fix and rerun only the affected suite before repeating the
  scoped review.

### Task 6: Create and consume the A-080 offline gate exactly once

**Files:**

- Runtime evidence only:
  `.superpowers/sdd/2026-07-29-deepseek-classifier-quality/`
- Modify after result: no tracked file until the separate actual decision is resolved.

**Interfaces:**

- Consumes: a committed clean source with no tracked changes.
- Produces: immutable `a080-offline-gate-result.json`, stdout/stderr hashes and exact one-shot lease.
- Does not produce: network/provider calls or an actual report.

- [ ] **Step 1: Commit all reviewed source and record the full SHA**

  ```powershell
  git status --short
  git rev-parse HEAD
  ```

  `git status --short` must be empty before the gate. Record the full SHA in the implementation
  note.

- [ ] **Step 2: Execute the A-080 offline wrapper once**

  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_a080_offline_gate.ps1
  ```

  Expected: one `A080_OFFLINE_GATE_PASS`. Whether PASS or FAIL, do not rerun the wrapper.

- [ ] **Step 3: Run readiness-only against the same source**

  ```powershell
  apps/api/.venv/Scripts/python.exe -B `
    scripts/run_deepseek_classifier_quality_actual.py --readiness-only
  ```

  Expected on offline PASS: `DEEPSEEK_CLASSIFIER_ACTUAL_READY`. This command does not acquire the
  actual lease or call DeepSeek.

- [ ] **Step 4: Record aggregate-only evidence without changing the source SHA**

  Record gate, source SHA, outcome, exit code, timed-out flag, invocation/rerun `1/0`, log byte
  counts/hashes and provider call/cost `0/0` in this plan's gitignored SDD ledger. Do not copy
  stdout/stderr contents into tracked docs and do not modify any tracked file before the actual
  decision. This preserves the same committed source required by actual readiness.

- [ ] **Step 5: Stop on offline failure**

  If the immutable gate is FAIL or readiness fails, record the exact bounded stage/reason and open
  no actual approval request. In that failure branch, update tracked closeout documents only after
  the same-source actual path has been abandoned. A successor identity requires a new design
  decision; A-080 is not rerun.

### Task 7: Human gate for one live A-080 quality evaluation

**Files:**

- No source edit before the decision.

**Interfaces:**

- Requires exact user authority: `A-080 DeepSeek actual 1회 실행 승인`.
- Does not infer authority from plan approval, a configured key, network recovery or a green
  offline gate.

- [ ] **Step 1: Present the immutable preflight evidence**

  Report the clean source SHA, A-080 offline PASS, readiness PASS, expected 20 selected/0 skipped,
  11 provider-free/9 provider, policy/privacy outbound `0`, retry/rerun `0/0`, concurrency `1`,
  output `128` and USD `0.20` cap.

- [ ] **Step 2: Wait for the exact separate approval**

  If approval is absent, stop with actual status `Pending`; provider call/cost remain `0/0`.

### Task 8: Execute the approved actual once and close the branch

**Files:**

- Create on execution:
  `docs/test-reports/CHAT-HYBRID-RAG-001-DEEPSEEK-A080-ACTUAL.md`
- Modify: A-080 implementation note, INDEX, versions, decision/ADR/task/RFP/changelog documents.

**Interfaces:**

- Consumes: the same clean source and A-080 offline evidence.
- Produces: one immutable aggregate-only actual report.
- Acceptance requires: selected/skip `20/0`, provider-free/provider `11/9`, policy/privacy outbound
  `0`, responses/2xx/strict/accepted/oracle `9/9/9/9/9`, retry/rerun `0/0`, all retention counters
  `0`, runtime failures `0`, cost at or below USD `0.20`.

- [ ] **Step 1: Re-run readiness-only**

  ```powershell
  apps/api/.venv/Scripts/python.exe -B `
    scripts/run_deepseek_classifier_quality_actual.py --readiness-only
  ```

  Expected: ready on the exact clean source. Do not proceed on any mismatch.

- [ ] **Step 2: Execute the one live run**

  ```powershell
  apps/api/.venv/Scripts/python.exe -B `
    scripts/run_deepseek_classifier_quality_actual.py
  ```

  Run exactly once. PASS or FAIL consumes A-080; never rerun it.

- [ ] **Step 3: Record only aggregates**

  Preserve selected/skip, provider-free/provider, outbound/response/2xx/parse/accepted/oracle,
  response-stage counts, usage, conservative cost, retry/rerun/runtime and six retention counters.
  Do not record per-fixture outcomes, questions, request/response bodies, invalid values, key, DSN,
  status detail or exception text.

- [ ] **Step 4: Keep runtime fail-closed unless every gate passes**

  A result below oracle `9/9` is FAIL. Do not promote DeepSeek to a new production/public default;
  keep the current deterministic fallback and local/private boundary.

- [ ] **Step 5: Run final scoped verification**

  Run the Task 5 area/static/docs/secret/diff commands once against final tracked files. Obtain an
  independent final review with Critical/Important/Minor counts.

- [ ] **Step 6: Commit and push without merging**

  If PR #24 is already merged, update from `origin/main`, resolve documentation INDEX changes, and
  verify the source diff before pushing this branch. If PR #24 remains open, keep A-080 stacked and
  do not create a misleading main-based PR.

  ```powershell
  git add apps/api scripts docs TASKS.md CHANGELOG.md versions/manifest.json
  git commit -m "fix(llm): improve DeepSeek classifier route quality"
  git push -u origin codex/a-080-deepseek-classifier-quality
  ```

  Create a Draft PR only after its correct base is confirmed. Never auto-merge it.
