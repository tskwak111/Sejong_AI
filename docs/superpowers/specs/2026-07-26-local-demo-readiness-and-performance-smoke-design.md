# Local Demo Readiness and Performance Smoke Design

- Status: Approved by the user's `CONTEXT_TOKEN_SECRET` generation/application and final local rehearsal instruction
- Date: 2026-07-26
- Scope: local/private only
- Related: D-077, ADR-0020, ADR-0023, DEMO-001, PERF-001

## 1. Goal

Close the remaining machine-local configuration gap without exposing a secret, run a
provider-disabled and non-destructive final local rehearsal from the merged PR #16 baseline, and
turn the deferred 100-user requirement into an executable plan without starting an unapproved
database-writing load run.

## 2. Non-goals and fixed boundaries

- Do not call Upstage or any other external provider.
- Do not reset, reseed, migrate, purge, or delete the current local database.
- Do not treat the current local event rows as evaluation KPI.
- Do not expose the admin UI publicly or enable a remote database.
- Do not add a production dependency or change the API, DB, official data, prompt, or Web contract.
- Do not print or commit the context secret, database URL, provider key, question text, answer text,
  provider body, or returned official records.

## 3. Local context-secret provisioning

Add a standard-library local provisioning command at
`scripts/provision_local_context_secret.py`. It resolves the shared primary checkout through
Git's absolute common directory, targets only `apps/api/.env`, confirms that exact path is ignored,
generates 32 random bytes with `secrets.token_urlsafe(32)`, and reuses the existing atomic
`update_env_assignment` helper. The command accepts no target path or secret value.

The successful output is exactly one bounded status line:

```text
[PASS] step=PROVISION-LOCAL-CONTEXT-SECRET
```

Any Git, path, ignore, random-generation, encoding, or filesystem failure returns a value-free
bounded failure line. Existing `.env` bytes other than the `CONTEXT_TOKEN_SECRET` assignment remain
unchanged. A failed write leaves the previous file intact.

## 4. Final local rehearsal

The rehearsal uses the latest merged `origin/main` source, the existing ignored local database
configuration, and the newly provisioned context secret. It forces both Upstage modes off for the
rehearsal process and makes no provider request.

The automated evidence is split deliberately:

1. API/DB actual probe: confirm Docker/Supabase health, `/health=200`, `/ready=200`, one supported
   provider-disabled chat result with `answer_mode=TEMPLATE` and at least one server-bound source,
   one `PERSONAL_LOOKUP` policy result with no eligible candidate, office match count one, and valid
   office empty count zero. Output only status, enum, mode, source count, and item counts.
2. Web browser gate: run the existing fixture-isolated 390/430/desktop Playwright suite. This
   validates navigation, responsive states, keyboard/focus behavior, retry identity, safe error
   rendering, and the demo admin UI without repeating the destructive 19-to-20 workflow.
3. Existing actual approval-loop evidence remains authoritative for the completed 19-to-20
   transition. The current ACTIVE 20 database is not reset merely to replay it.

The single supported chat probe may add approved metadata-only local event/idempotency rows. It uses
a fixed non-personal synthetic evaluation question, and the result is not counted as quality KPI.
`PERSONAL_LOOKUP` must preserve its no-event/no-failed-row policy.

## 5. Performance-smoke design boundary

PERF-001 remains a separate implementation slice. Its final acceptance targets remain those already
approved in source-of-truth:

- 100 virtual users;
- 60 seconds;
- error rate below 1%;
- average response time target at or below 3 seconds;
- record p50, p95, maximum, request count, and error count;
- local/private structural smoke only, not production capacity evidence.

The implementation plan has two phases:

1. A provider-disabled, read-only HTTP preflight against `/health` and the official office query to
   validate the load harness, loopback-only target guard, bounded duration, aggregate-only output,
   and zero secret/question/body logging.
2. A cached/fixed chat-response run only after a separate human approval for its bounded local DB
   metadata/idempotency writes. It must use a synthetic PII-free fixture, provider call zero, a
   disposable or explicitly accepted non-KPI local dataset, and post-run row-count evidence rather
   than response-body logs.

No k6, Locust, or other dependency is added. The later harness should use the already locked Python
runtime and existing `httpx` dependency, with concurrency and duration fixed by code rather than
free-form CLI flags.

## 6. Error handling

- Missing/invalid Git common directory: stop before generating a secret.
- Non-ignored or unexpected target: stop before reading or writing `.env`.
- Generated value shorter than 32 UTF-8 bytes or containing a line break: stop without writing.
- Invalid local settings after provisioning: report only `LOCAL_CONFIGURATION_INVALID`.
- API readiness or invariant failure: stop the rehearsal, shut down local child processes, and
  report the exact bounded stage and status/count mismatch.
- Browser failure: preserve only the existing ignored Playwright trace/screenshot behavior and do
  not copy artifacts into tracked paths.

## 7. Verification

- RED/GREEN unit tests for target resolution, ignored-path refusal, byte preservation, minimum
  entropy length, atomic failure behavior, and value-free output.
- Existing local settings tests and secret scanners.
- Provider-disabled API focused tests.
- Actual bounded API/DB rehearsal described above.
- Existing Web lint, typecheck, test, build, and 390/430/desktop Playwright gate.
- Repository documentation, package, secret, protected-diff, and `git diff --check` gates before
  publication.
