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
secret-pattern scan. The runner reports only whether a key is present; it never
prints a key, DSN, question, provider request, or provider response.

## Execute exactly once

Run this command once from the repository root:

```powershell
apps/api/.venv/Scripts/python.exe -B `
  scripts/run_hybrid_rag_actual.py `
  --fixture apps/api/tests/chat/fixtures/hybrid-rag-uat.v1.json `
  --report docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md
```

Expected PASS evidence is 20 selected, 0 skipped, 11 deterministic and 9
provider cases. Each provider result must satisfy the closed selector contract
and current catalog membership where a topic is required. The report records
fixture ID, route/topic match, outbound count, aggregate tokens, and
VAT-inclusive Decimal cost only.

If the process returns nonzero or the report says `FAIL`, stop. The bounded
FAIL evidence is intentional: do not rerun, change the fixture, or bypass the
pre-reservation budget without a new human instruction.

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
