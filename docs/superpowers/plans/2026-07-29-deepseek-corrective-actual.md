# A-075 DeepSeek Corrective Actual Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce one isolated, aggregate-only A-075 DeepSeek classifier actual result without
rewriting A-074 evidence or changing product behavior.

**Architecture:** Reuse the reviewed A-074 evaluator and network adapter through a narrow,
fail-closed evidence-profile binding seam. Add separate A-075 offline and actual entry points,
paths, gate name, lease payloads and report.

**Tech Stack:** Python 3.12, PowerShell 5.1, existing `httpx`, pytest/unittest, Ruff, Mypy.

## Global Constraints

- A-073/A-074 wrapper, result, log, report and lease are never rerun or modified.
- A-075 offline and actual each run at most once; rerun is zero.
- DeepSeek actual uses `deepseek-v4-flash`, 3 seconds, retry 0, concurrency 1, output 128,
  temperature 0, thinking disabled and USD 0.20 cap.
- Fixed synthetic input only; question/body/value/key/DSN retention is zero.
- No public/remote/free-input operation, production dependency, API/DB/data change or auto merge.

---

### Task 1: Evidence-profile seam and A-075 actual entry point

**Files:**
- Modify: `scripts/run_deepseek_classifier_actual.py`
- Create: `scripts/run_deepseek_classifier_corrective_actual.py`
- Create: `scripts/tests/test_run_deepseek_classifier_corrective_actual.py`

**Interfaces:**
- Consumes: existing A-074 evaluator `main(argv)` and immutable fixture/catalog hashes.
- Produces: A-075 runner bound to its own report, offline paths, gate and lease payloads.

- [x] Write tests that prove every A-075 identity differs from A-074, unexpected core-default
      drift fails before readiness and no A-074 file is touched.
- [x] Run the new focused tests and observe expected RED because the profile seam/runner is absent.
- [x] Add the smallest explicit profile-binding seam and thin A-075 entry point.
- [x] Run focused A-074+A-075 runner tests and observe GREEN.
- [x] Run Ruff and Mypy for the changed Python files.

### Task 2: A-075 offline wrapper

**Files:**
- Create: `scripts/run_a075_offline_gate.ps1`
- Create: `scripts/tests/test_run_a075_offline_gate.py`

**Interfaces:**
- Consumes: repository `scripts/verify.ps1 -Offline`.
- Produces: permanent A-075 lock/log/result with gate `A-075-OFFLINE`.

- [x] Write controlled-repository tests for one invocation, PASS/FAIL preservation, timeout and
      A-074 path denial.
- [x] Run them and observe RED because the wrapper is absent.
- [x] Implement the isolated wrapper by preserving the reviewed A-074 control flow with only
      A-075 identity substitutions and denial of all actual runners.
- [x] Run both A-074 and A-075 wrapper tests and observe GREEN.

### Task 3: Authority and version checkpoint

**Files:**
- Modify: `docs/decisions/DECISION_LOG.md`
- Modify: `docs/11_AMBIGUITY_REGISTER.md`
- Modify: `docs/source-of-truth/TEAM_DECISIONS.md`
- Modify: `TASKS.md`
- Modify: `versions/manifest.json`
- Modify: `docs/implementation-notes/IMP-20260729-007-a-075-deepseek-corrective-actual.md`
- Modify: `docs/implementation-notes/INDEX.md`

- [x] Record the new approval and distinct identity without claiming an unrun result.
- [x] Increment only test/documentation versions before the offline gate.
- [x] Run documentation and secret checks.

### Task 4: Pre-gate verification and source commit

- [x] Run focused runner/transport/parser/privacy tests.
- [x] Run the complete relevant API/script area.
- [x] Run Ruff, Mypy, documentation, secret and diff checks.
- [x] Review the exact diff for Critical/Important findings.
- [x] Commit a clean source checkpoint and record its SHA.

### Task 5: One-shot execution and closeout

- [x] Confirm all A-075 artifacts are absent and run `run_a075_offline_gate.ps1` exactly once.
- [x] If and only if offline PASS, run network-free A-075 readiness.
- [x] If and only if readiness PASS, run A-075 actual exactly once.
- [x] Record aggregate result, source SHA, invocation/rerun and cost without provider content.
- [x] Synchronize decisions, task, versions, report links, implementation note and INDEX.
- [x] Run final documentation/secret/diff checks, commit, push and create a Draft PR.
- [x] Do not auto merge.
