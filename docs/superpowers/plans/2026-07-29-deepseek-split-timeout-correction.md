# A-077 DeepSeek Split-Timeout Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate the DeepSeek connect and response budgets, harden the probe-to-actual evidence
chain, then run one gated probe and at most one fixed actual under new immutable identities.

**Architecture:** Extend immutable DeepSeek settings with a `3.0` second connection budget and a
`10.0` second complete-response budget. Reuse the hardened evaluator with an identity-owned
aggregate deadline, add a separate one-call probe that emits aggregate evidence only, and preserve
all predecessor evidence.

**Tech Stack:** Python 3.12, existing `httpx`, asyncio, pytest, Ruff, Mypy, PowerShell 5.1.

## Global Constraints

- A-074/A-075/A-076 evidence, leases and invocation/rerun counts are immutable.
- DeepSeek connect/write/pool `3.0s`; read and complete exchange `10.0s`.
- Retry `0`, concurrency `1`, output `128`, temperature `0`, cost cap USD `0.20`.
- Probe is exactly one synthetic provider call; actual runs only after probe HTTP 2xx PASS.
- No question/body/invalid value/exception detail/key/DSN retention.
- No public/API/DB/data/Web/dependency/final-answer-provider change and no automatic merge.
- A-077 offline PASS `1/0` is historical and immutable; provider execution uses only A-078.

---

### Task 1: Split the transport budget

**Files:**
- Modify: `apps/api/tests/llm/test_deepseek_settings.py`
- Modify: `apps/api/tests/llm/test_deepseek_classifier.py`
- Modify: `apps/api/src/sejong_ai_api/llm/deepseek_settings.py`
- Modify: `apps/api/src/sejong_ai_api/llm/deepseek_classifier.py`

**Interfaces:**
- Produces: immutable `connect_timeout_seconds=3.0` and `timeout_seconds=10.0`.
- Preserves: `DeepSeekQuestionClassifier.classify(...) -> ClassifierDecision | None`.

- [x] Add behavior tests that require connect/write/pool `3.0`, read `10.0`, complete-exchange
  wall clock `10.0`, and retry `0`.
- [x] Run the focused tests and confirm RED on the old all-`3.0` profile.
- [x] Add the connect setting and map the two budgets to `httpx.Timeout` and `asyncio.timeout`.
- [x] Run the focused tests and confirm GREEN.

### Task 2: Give each evidence identity its own aggregate deadline

**Files:**
- Modify: `scripts/tests/test_run_deepseek_classifier_actual.py`
- Modify: `scripts/run_deepseek_classifier_actual.py`
- Create: `scripts/tests/test_run_deepseek_classifier_split_timeout_actual.py`
- Create: `scripts/run_deepseek_classifier_split_timeout_actual.py`

**Interfaces:**
- Extends: `EvidenceIdentity.actual_run_deadline_seconds`.
- Produces: `A077_EVIDENCE_IDENTITY` with a `100` second aggregate deadline.

- [x] Add tests proving A-074/A-075/A-076 keep `32` seconds and A-077 binds/restores `100`.
- [x] Run the runner tests and confirm RED because the identity deadline and A-077 entry point are
  absent.
- [x] Implement identity-owned binding and the thin disjoint A-077 entry point.
- [x] Run A-074 through A-077 identity tests and confirm GREEN.

### Task 3: Add the aggregate-only one-call probe

**Files:**
- Create: `scripts/tests/test_run_deepseek_classifier_a077_probe.py`
- Create: `scripts/run_deepseek_classifier_a077_probe.py`

**Interfaces:**
- Consumes: A-077 clean-source/offline identity, current approved fixture/catalog/settings.
- Produces: one immutable probe report and lease; exit `0` only for one HTTP 2xx response.

- [x] Add controlled-double tests for readiness, exact one outbound, 2xx PASS, no-response FAIL,
  one-shot lease, aggregate-only report and zero retained sensitive values.
- [x] Run the probe tests and confirm RED because the module is absent.
- [x] Implement the smallest dedicated probe around the existing settings, classifier, catalog,
  cost ledger and closed response observers.
- [x] Run probe and privacy tests and confirm GREEN.

### Task 4: Add the A-077 offline gate

**Files:**
- Create: `scripts/tests/test_run_a077_offline_gate.py`
- Create: `scripts/run_a077_offline_gate.ps1`

**Interfaces:**
- Consumes: `scripts/verify.ps1 -Offline`.
- Produces: one immutable A-077 offline result/log/lease set.

- [x] Copy the controlled A-076 wrapper tests and change every path/gate/sentinel to A-077.
- [x] Confirm RED because the wrapper is absent.
- [x] Add the A-077 wrapper by mechanically changing only identity constants in the reviewed flow.
- [x] Run the wrapper tests and PowerShell parser check.

### Task 5: Clean source and exact-one execution

**Files:**
- Modify: authority, ADR, task, version, changelog and implementation-note documents.
- Create conditionally: A-078 probe and actual aggregate reports.

- [x] Record D-128 and the ADR-0028 timeout amendment without claiming unrun evidence.
- [x] Run the first focused and related-area tests, Ruff, Mypy, documentation, secret and diff checks.
- [x] Commit the clean A-077 source checkpoint.
- [x] Run A-077 offline exactly once: PASS `1/0`; do not rerun.
- [x] Run the A-078 one-call probe exactly once: transport-no-response FAIL.
- [x] Do not run the nine-provider-case actual because the probe did not return HTTP 2xx.
- [x] Record A-078 aggregate result, retention, retry/rerun and conservative cost.
- [x] Run A-078 final scoped review and commit; PR closeout continues only in Task 7/A-079.

### Task 6: Independent-review security correction and A-078 successor

**Files:**
- Modify: `scripts/run_deepseek_classifier_actual.py`
- Create: `scripts/run_deepseek_classifier_a078_probe.py`
- Create: `scripts/run_deepseek_classifier_prelease_hardened_actual.py`
- Create: `scripts/run_a078_offline_gate.ps1`
- Modify/create: focused tests and authority documents

**Interfaces:**
- Consumes: unchanged D-128 probe 1-call + conditional actual run 1회 containing exactly 9
  provider calls.
- Produces: exact probe lease/report/source binding, one final source revalidation before the
  actual lease, and post-probe revalidation before publishing PASS.

- [x] Preserve the reviewer result Critical 0 / Important 3 / Minor 2 and provider call count 0.
- [x] Observe RED for wrong/missing/oversized lease and missing pre-lease recheck.
- [x] Implement bounded exact-lease validation and identity-owned pre-actual callback.
- [x] Create disjoint A-078 probe/actual/offline identities and controlled wrapper tests.
- [x] Observe second RED for callback-following final revalidation and probe post-execution drift.
- [x] Fail closed before actual lease and before probe PASS publication on those drifts.
- [x] Format, run full relevant gates and independent re-review Critical0/Important0/Minor0.
- [x] Commit clean A-078 source `844e53b...`.
- [x] Consume A-078 offline and probe exactly once; probe FAIL blocked the conditional actual,
  which was not run. Never rerun A-078.

### Task 7: Close A-078 and execute the approved A-079 retry

**Files:**
- Create: `docs/test-reports/CHAT-HYBRID-RAG-001-DEEPSEEK-A078-PROBE.md`
- Create: A-079 probe/actual/offline runners and controlled tests
- Modify: binary evidence writers, authority, versions and implementation notes

- [x] Preserve A-078 offline PASS and probe transport-no-response FAIL; actual remains 0.
- [x] Observe Windows exact-lease RED and fix writers with binary-open flags.
- [x] Create disjoint A-079 identities and pass focused runner/wrapper tests.
- [x] Run related checks and independent scoped review Critical0/Important0/Minor0.
- [x] Commit clean A-079 source `a2d617c...`.
- [x] Consume A-079 offline/readiness/probe once and conditional actual once.
- [x] Record probe PASS and actual transport/wire PASS, oracle quality FAIL 6/9.
- [x] Run final closeout checks/review and prepare the closeout commit; push updates Draft PR
  #22 without merging.
