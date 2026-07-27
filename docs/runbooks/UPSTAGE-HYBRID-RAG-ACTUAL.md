# Upstage Hybrid RAG actual selector runbook

## Purpose and boundary

This runbook permits one local/private execution of the approved PII-free
selector subset. It sends neither citizen/free-input questions nor privacy
fixtures, uses no DB or Docker, and creates only aggregate evidence by fixture
ID. It is not a public, remote, or administrator verification procedure.

## Preconditions

- A human has approved this one execution after the offline gate is green.
- The working tree has no intended changes outside the bounded Task 10 scope.
- The ignored local API environment has a key present and the exact combined
  profile. Do not print, copy, or paste the environment file or any value.
- Both provider modes are explicitly enabled for this run only.

The runner fail-closes before client creation unless these settings are exact:

```text
UPSTAGE_CLASSIFIER_MODE=true
UPSTAGE_GROUNDED_CHAT_MODE=true
model=solar-pro3
classifier/generator/combined=80/100/160
concurrency=1
retry=0
cost_cap_usd=0.20
```

It also requires the recorded 48-case offline PASS and a clean repository
secret-pattern scan. The fixture, coverage metadata, immutable `.2` official
projection, release manifest, and offline evidence are bound to reviewed
SHA-256 identities. The release must be schema v2 with exactly 19
`ACTIVE`/`OFFICIAL` records, and protected inputs must have no tracked diff.
The runner reports only whether a key is present; it never prints a key, DSN,
citizen text, provider request, provider response, or exception detail.

## Execute exactly once

Run this command once from the repository root:

```powershell
apps/api/.venv/Scripts/python.exe -B `
  scripts/run_hybrid_rag_actual.py `
  --fixture apps/api/tests/chat/fixtures/hybrid-rag-uat.v1.json `
  --report docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md
```

Before client construction the runner exclusively creates
`CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md.run.lock`. An existing lock or evidence
report blocks the command before any provider operation. This prevents
concurrent launches and makes a second run impossible without explicit human
acknowledgement.

Expected PASS evidence is 20 selected, 0 skipped, 11 prior-offline
deterministic/provider-free cases and 9 fresh provider cases. Only the 9
provider rows are labeled as fresh route/topic matches. Each provider result
must satisfy the closed selector contract and current catalog membership where
a topic is required. The report records safe input identities, fixture ID,
evidence kind, outbound count, strictly parsed aggregate token usage, observed
VAT-inclusive cost, conservative ledger charge, and reconciliation status.

If the process returns nonzero or the report says `FAIL`, stop. Every
controlled failure after argument validation writes bounded FAIL evidence
atomically. A crash or evidence-write failure intentionally leaves the lock.
Do not delete, overwrite, or rename the report/lock; change the fixture; or
bypass the pre-reservation budget without a new human instruction.

An approved rerun is a separate governed action. The human must first review
and archive the prior report, explicitly authorize reset, and then remove the
canonical report and any stale `.run.lock`. The runner never performs this
reset itself.

## Restore and verify

After the process exits, restore both ignored local provider mode settings to
`false` unless a human is immediately starting an explicit foreground demo.
Do not alter tracked files to do this. Verify the tracked tree still contains
no local environment file or key, then run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
git diff --check
```

Record the aggregate report and the restoration result in the implementation
note. A generated report is evidence of this one execution, not authorization
for a second call or for public/remote provider operation.
