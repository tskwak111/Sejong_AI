# A-076 DeepSeek Network-Recovery Actual Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve A-075 and produce one separate aggregate-only DeepSeek result after confirmed
network recovery.

**Architecture:** Reuse the hardened evaluator through a new immutable `EvidenceIdentity`. Add thin
A-076 actual and offline entry points, prove their isolation with controlled tests, commit a clean
source, then consume offline/readiness/actual exactly once.

**Tech Stack:** Python 3.12, PowerShell 5.1, existing `httpx`, pytest, Ruff and Mypy.

## Global Constraints

- Never modify, delete or rerun A-074/A-075 evidence or leases.
- A-076 offline and actual each run at most once; retry and rerun remain zero.
- Use `deepseek-v4-flash`, timeout 3 seconds, concurrency 1, output 128, temperature 0 and
  conservative USD 0.20 cap.
- Fixed synthetic fixture only; retain no question, provider body, invalid value, secret or DSN.
- No product/API/DB/data/Web/dependency/public/remote/free-input change and no automatic merge.

---

### Task 1: A-076 evidence identity

**Files:**
- Create: `scripts/run_deepseek_classifier_network_recovery_actual.py`
- Create: `scripts/tests/test_run_deepseek_classifier_network_recovery_actual.py`

**Interfaces:**
- Consumes: `run_deepseek_classifier_actual.EvidenceIdentity` and `main`.
- Produces: `A076_EVIDENCE_IDENTITY` and `main(argv)` bound to A-076 paths.

- [x] Write identity/readiness/drift tests and observe RED because the A-076 module is absent.
- [x] Implement the thin A-076 entry point with no classifier/parser changes.
- [x] Run A-074/A-075/A-076 focused runner tests and observe GREEN.

### Task 2: A-076 offline wrapper

**Files:**
- Create: `scripts/run_a076_offline_gate.ps1`
- Create: `scripts/tests/test_run_a076_offline_gate.py`

**Interfaces:**
- Consumes: `scripts/verify.ps1 -Offline`.
- Produces: one immutable A-076 offline result/log/lease set.

- [x] Write controlled PASS/FAIL/one-shot tests and observe RED because the wrapper is absent.
- [x] Add the A-076 wrapper by changing only identity constants in the reviewed A-075 flow.
- [x] Run A-075/A-076 wrapper tests and PowerShell parser checks.

### Task 3: Clean-source gate

**Files:**
- Modify: source-of-truth, decisions, task, versions and implementation-note files.

- [x] Record the new authority without claiming an unrun result.
- [x] Run focused runner/privacy tests, Ruff, Mypy, docs, secret and diff checks.
- [x] Review and commit a clean source checkpoint.

### Task 4: Exact-one execution and closeout

- [x] Run A-076 offline gate exactly once.
- [x] Run network-free readiness only after offline PASS.
- [x] Run A-076 actual exactly once only after readiness PASS.
- [x] Record aggregate outcome, hashes, retention, retry/rerun and cost.
- [x] Commit/push the evidence and update Draft PR #22 without automatic merge.
