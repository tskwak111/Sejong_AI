# CHANGELOG

## [Unreleased]

### Implemented — A-073 classifier enum-shape correction offline

- Implemented one shared typed decision builder with value-free route, intent, pending-slot,
  identifier and route-shape first-failure stages while retaining the historical generic stage.
- Replaced compact prompt ambiguity with the exact five-field route matrix, literal uppercase
  `NONE`, intent-grouped catalog and request-local same-row topic/coverage example. The governed
  20-topic/256-character prompt is 4,067 characters with a 29-character guard margin; longer
  complete messages fail closed before
  transport without truncation or sampling.
- Offline evidence passed after preserving the initial REDs and final scoped review: classifier/
  Hybrid RAG area `397`,
  controlled-double regressions `38 passed, 1 failed → 39 passed`, API Ruff format/lint and Mypy
  over `115` source files, and direct runner Ruff. The RED was a baseline-stale mock JSON
  `pending_slot: null`; the approved test-only correction uses exact wire string `"NONE"`.
- The final review additionally proved the contiguous four-intent provider vocabulary, all adjacent
  first-failure precedence boundaries and selected-question/provider-body/invalid-value
  non-retention. The scoped re-review found no remaining actionable finding.
- Advanced application `0.12.3→0.12.4-classifier-wire-diagnostics`, prompt
  `0.4.2→0.4.3-explicit-route-matrix`, tests
  `2.1.6→2.1.7-classifier-wire-correction` and documentation `2.30.5→2.30.7`. Public
  API/contracts, Web, DB schema/migration, official/mock data, dependencies, packages and
  lockfiles are unchanged. A-073 provider/network actual calls and cost are `0`; the current
  closure directive leaves Task 6 unexecuted and does not rerun the existing Upstage actual.
- Consumed the Task 5 offline root wrapper exactly once. The shell harness returned timeout
  `124` after 14.056 seconds and did not preserve final stdout/exit, although the detached wrapper
  later exited after observed `TEST-ROOT`, `TEST-DATA-SEED` and `TEST-API` phases. The aggregate is
  therefore `NOT VERIFIED/FAIL`, not PASS, and was not rerun. Independent docs/secret/diff/status
  checks pass, provider calls/cost remain `0`/USD `0`, root invocation/rerun remain exactly `1/0`,
  and D-121 closes the scoped offline review without reclassifying this result.

### Planned — A-073 classifier enum-shape correction

- Approved the A-073 written specification and published a bite-sized TDD implementation plan for
  the shared typed decision builder, five refined value-free stages, explicit route matrix,
  intent-grouped provider catalog, production-wire oracle and offline clean-source gate.
- Preserved configured masked-question max 1,024 and the complete-message 4,096 fail-closed guard.
  The governed 20-topic/256-character actual-eligible prompt must fit without truncation or
  sampling; longer complete messages remain provider-free fallback.
- Advanced documentation `2.30.4→2.30.5`. Runtime, prompt, tests, API/contracts, Web, DB/data,
  dependencies, provider calls and cost remain unchanged. The corrective actual is excluded and
  still needs separate exact human approval.

### Specified — A-073 explicit classifier route matrix and refined diagnostics

- Approved the design direction and published the integrated written specification for review.
- Replaced the ambiguous prompt grammar in the target design with a complete five-field route
  matrix, exact uppercase `NONE`, closed provider intent/pending vocabularies and same-catalog-row
  topic/coverage selection.
- Defined five value-free first-failure aggregate stages for route, intent, pending slot,
  identifier shape and route shape while retaining historical `ENUM_SHAPE_REJECTED` evidence.
- Advanced documentation `2.30.3→2.30.4`. Application, prompt, tests, API/contracts, Web, DB/data,
  dependencies, provider calls and cost are unchanged; a future actual remains separately gated.

### Evaluated — A-072 strict classifier corrective actual

- Executed the separately approved corrective actual exactly once from clean source `efc0b34`.
  The fixed 20-case subset produced 11 provider-free cases and 9 outbound responses with HTTP 2xx,
  accepted usage and one terminal stage each; privacy/policy outbound remained 0.
- The prior `KEY_SET_REJECTED` stage fell from 9 to 0, but all 9 provider responses terminated at
  `ENUM_SHAPE_REJECTED`. Accepted decisions and provider route/topic matches remained 0, so the
  aggregate acceptance is `FAIL`; the command was not rerun.
- Observed and ledger cost reconciled at VAT-inclusive USD 0.002496648 below the USD 0.20 cap,
  with retry 0. Question/provider content, status detail, key and DSN retention remained 0.
- Archived the byte-preserved D-111 report and advanced documentation `2.30.2→2.30.3`.
  Application, prompt, tests, API/contracts, DB/data, dependencies, package and lockfiles are
  unchanged.

### Implemented — A-072 strict classifier wire offline

- Added a provider-boundary parser that accepts exact string `NONE` only for the four nullable
  fields, converts it to the existing internal `None`, and reuses the canonical closed
  enum/shape/current-catalog validator. Canonical JSON-null parsing and the public generic failure
  remain unchanged.
- Replaced the Upstage classifier request's loose `json_object` mode with a fresh strict
  `json_schema`: exactly five required string keys and no additional properties. The bounded
  prompt now uses the same canonical field names and exact sentinel without weakening the
  4,096-character guard.
- Offline evidence passed: classifier/Hybrid RAG area `333`, controlled-double actual-runner `24`,
  Ruff format/lint and Mypy over `115` files. Provider/network calls and cost remained `0`.
- Advanced application `0.12.2→0.12.3-structured-classifier-wire`, prompt
  `0.4.1→0.4.2-exact-five-key-schema` and tests
  `2.1.5→2.1.6-structured-classifier-wire`. API/shared contracts, DB schema, official/mock data,
  dependencies, package and lockfiles are unchanged. Task 5 clean-source review is complete, but
  the root wrapper's single invocation FAILed at environment-only `PREFLIGHT-UV`, was not rerun and
  is not a PASS. Remaining constituents/security/scope checks passed with documented bounded skips;
  provider calls/cost remained `0` at this Tasks 1~5 checkpoint. The exact approval was consumed
  once in the later D-117 evaluation recorded above.
- Advanced documentation `2.30.1→2.30.2` for the Tasks 1~5 implementation/evidence checkpoint;
  all runtime axes remain unchanged.

### Planned — A-072 strict classifier wire

- Approved the written specification and published an exact RED/GREEN implementation plan for
  provider-wire parsing, canonical prompt fields, strict transport schema, area/version integration
  and the root/clean-source gate.
- Kept the one-shot corrective actual outside plan approval; it requires a new exact approval after
  Tasks 1~5 pass.
- Advanced documentation `2.30.0→2.30.1`; runtime, API, DB, data, dependencies, provider calls,
  push and merge remain unchanged.

### Specified — A-072 strict five-key classifier wire

- Approved design section 2 and published the integrated written specification for review.
- Isolated exact `NONE` normalization to the provider wire while preserving canonical JSON-null
  parsing, server-owned enum/shape/catalog validation and fixed-stage fail-closed diagnostics.
- Defined focused/area/root TDD, target application `0.12.3`, prompt `0.4.2`, tests `2.1.6` and a
  separately approved corrective actual after clean-source offline verification.
- Advanced documentation `2.29.10→2.30.0`; runtime, API, DB, data, dependencies and provider calls
  remain unchanged.

### Approved — A-072 wire design section 1

- Approved strict five-key string schema, exact `NONE` normalization for the four nullable
  fields, full canonical field names, server-owned enum/catalog validation and retry-zero
  fail-closed behavior.
- Kept dynamic catalog values out of the provider schema and kept public API, DB, data,
  dependencies and server-bound sources unchanged.
- Advanced documentation `2.29.9→2.29.10`; code and provider calls remain zero pending section 2
  and the written specification.

### Decided — strict five-key classifier wire

- Chose Q-LLM-014=A for A-072: the Upstage provider-only response will use strict `json_schema`
  with exactly five required string fields and a fixed `NONE` sentinel for nullable meaning.
- The server will normalize `NONE` to the existing internal `None` before the unchanged closed
  enum/catalog validation. Public API, DB, data, dependencies and server-bound sources stay
  unchanged.
- Advanced documentation `2.29.8→2.29.9`. Product code and provider calls remain zero until the
  detailed design is approved; a corrective actual remains a separate human gate.

### Implemented — value-free classifier response-stage diagnostics

- Added a closed 13-value terminal-stage enum across the production Upstage response parser and
  strict classifier contract parser. The optional observer receives exactly one enum for each HTTP
  response and receives no question, response body, status detail, exception, key or DSN.
- Preserved the public `ClassifierDecision | None` behavior, generic
  `CLASSIFIER_DECISION_INVALID` failure and fail-closed citizen fallback; observer errors cannot
  change an accepted decision.
- Added aggregate-only stage counters and acceptance invariants to the exact-one actual runner.
  Per-fixture stage disclosure, API/DB/data/prompt/dependency changes and provider calls remain zero
  at this clean-source checkpoint.
- Archived D-107 evidence and advanced application
  `0.12.1→0.12.2-response-stage-diagnostics`, tests
  `2.1.4→2.1.5-response-stage-diagnostics` and documentation `2.29.6→2.29.7`.
- Executed the separately approved exact-one actual from clean source `0646db0`: 20 selected,
  0 skipped, 11 provider-free and 9 outbound. All 9 responses were HTTP 2xx with strict usage,
  all 9 terminated at `KEY_SET_REJECTED`, and accepted decisions/matches remained 0, so acceptance
  is FAIL and no retry occurred. Observed/ledger cost reconciled at USD 0.002626503 including VAT.
- Preserved local ignored modes false/false, lock 0 and question/provider body/status detail/key/DSN
  retention 0. Advanced documentation `2.29.7→2.29.8`; a new corrective actual is not authorized.

### Specified — value-free classifier response-stage diagnostics

- Approved the written specification and exact RED/GREEN inline implementation plan. Product code
  and provider calls remain zero at this planning checkpoint.
- Recorded the user-approved production-parser observer design for A-071. The observer can emit
  only one closed stage enum per HTTP response; no question, provider content, exception text,
  status detail, key or DSN may cross the diagnostic boundary.
- Kept citizen behavior, public parser failure, prompt, provider profile, API, DB, official data
  and dependencies unchanged. No provider call is part of this written-spec checkpoint.
- Advanced documentation `2.29.4→2.29.6`; application and test versions advance only after the
  written specification and TDD plan are confirmed and implemented.

### Fixed — explicit JSON-mode instruction for the Hybrid RAG selector

- Restored an explicit `JSON만` instruction in the closed classifier system message without
  changing its request schema, route vocabulary, catalog, provider model, timeout or retry policy.
- Added a RED/GREEN regression test and kept the real 20-topic catalog plus a 256-character
  question within the conservative 4,096-character prompt bound.
- Archived the D-106 aggregate-only 4xx FAIL, then executed the separately approved corrective
  actual exactly once from committed source `4cb42ff`: 20 selected, 0 skipped, 11 provider-free
  and 9 outbound. All 9 responses were HTTP 2xx with accepted usage, proving the prior 4xx request
  rejection was fixed; strict closed decisions and route/topic matches were still 0, so acceptance
  remains FAIL and no retry occurred. Observed and ledger cost reconciled at USD 0.002646303
  including VAT, below the USD 0.20 cap.
- Retained no question, provider body, status detail, key or DSN; ignored local provider modes
  remain false/false. Exact response-validation diagnosis is deferred to A-071.
- Advanced prompt set `0.4.0→0.4.1-json-mode-instruction`, tests
  `2.1.3→2.1.4-json-mode-regression` and documentation `2.29.3→2.29.4`; application, API,
  contracts, DB, data and dependencies are unchanged.

### Diagnosed — value-free Hybrid RAG provider rejection

- Pushed the approved local `main` baseline `d973abc` to the private `origin/main`.
- Preserved the D-105 FAIL report under `docs/test-reports/archive/` and added
  aggregate-only HTTP-family, transport, usage, closed-decision and contract-mismatch diagnostics.
- Executed the separately approved corrective actual exactly once from source `1f337ad`: 20
  selected, 0 skipped, 11 provider-free and 9 outbound. All 9 attempts received 4xx-class
  responses; 2xx, 5xx, no-response/transport, accepted usage, accepted decisions and matches were
  all 0, so acceptance remains FAIL.
- Retained no question, provider body, status detail, key or DSN. Process-scoped overrides ended
  and ignored local provider modes were confirmed false/false. No additional provider run is
  authorized; exact auth/access/request-shape/quota diagnosis remains A-070.
- Advanced tests `2.1.2→2.1.3-value-free-provider-diagnostics` and documentation
  `2.29.2→2.29.3`; runtime, API, contracts, DB, data, prompt and dependency versions are unchanged.

### Integrated — pinned CLI advisory patch into local main

- The user selected local integration, and `main` fast-forwarded from `028053d` to feature commit
  `968d27e` without conflict after confirming exact parity with `origin/main`.
- No remote push, pull request, remote merge, provider call, DB reset/seed or deployment occurred.
- The merged local `main` passed the fresh 31-stage repository gate in 967 seconds.
- The registered worktree and its ignored long-path caches were removed, and the fully merged local
  feature branch was deleted after an explicit ancestry check; other worktrees were untouched.
- Advanced documentation `2.29.1→2.29.2`; all runtime, contract, DB, data, prompt and test versions
  remain unchanged.

### Fixed — pinned Supabase CLI official update advisory

- Kept the pinned, hash-verified Supabase CLI at `2.109.1` while accepting only its exact official
  two-line update advisory on `--version`; arbitrary stderr, version drift, hash drift and nonzero
  exit remain fail-closed.
- Reproduced the time-dependent failure after Supabase published `2.110.0`, added RED/GREEN coverage
  for the exact advisory and a rejected diagnostic, and passed the actual binary verifier plus all
  25 patched-tooling tests.
- Re-ran the post-PR-20 local smoke with provider modes off: `/ready=200`, actual local DB/admin
  transport, Web production build and 27 browser scenarios across 390/430/desktop passed. The
  provider-off smoke intentionally does not claim Hybrid RAG Upstage quality or actual-provider PASS.
- Passed the fresh 31-stage repository gate in 1191.5 seconds, including data release/seed,
  Web/API/contracts, secret and Web-bundle scans, package validation and final diff checks.
- Advanced repository guidance `1.7.9→1.7.10`, tests
  `2.1.1→2.1.2-patched-cli-advisory` and documentation `2.29.0→2.29.1`; application, API, contracts,
  DB, official data and prompt versions are unchanged.

### Implemented — bounded ACTIVE-topic Hybrid RAG

- Added a versioned 20-topic metadata catalog whose runtime view is the request-local
  ACTIVE/OFFICIAL intersection (19 in immutable official `.2`) and a closed
  route/intent/topic/coverage/pending-slot selector with server-side membership and typed grounding.
- Added intent-specific exact follow-ups, bounded structured context, always-visible same-tab region
  selection, the three-choice certificate entry and source-backed related questions.
- Added local interactive provider limits of classifier 80, generator 100, combined 160 and a
  VAT-inclusive USD 0.20 pre-reservation stop; retry remains 0 and failures remain value-free.
- Froze a 48-case synthetic UAT with an independent provider oracle, phone-shaped redaction-to-MOVE
  success, exact follow-up options/pending slots and aggregate-only privacy reporting. Offline
  acceptance passed 91 tests with skip 0; official examples are 57/57 and classifier fixtures 60/60.
- Added a content-pinned, one-run-locked, aggregate-only actual selector runner. Its single approved
  local execution selected 20 with skip 0, kept 11 deterministic cases provider-free and made the
  expected 9 outbound attempts, but accepted 0 strict usage responses and matched 0 provider routes;
  the recorded outcome is FAIL and was not rerun.
- Kept vector/embedding, new dependencies, DB migrations, official `.2` changes, multi-KB synthesis,
  public/remote provider operation and automatic merge out of scope. The actual FAIL does not
  invalidate offline/template behavior, but provider configuration/availability must be diagnosed
  and a new human authorization obtained before any corrective actual rerun.
- Preserved the validated topic in durable SUCCESS and topic-bound REGION FOLLOWUP replay context,
  so a network retry does not break the next short facet or region answer. Generic follow-ups remain
  topic-free.
- Final browser evidence is 27/27. API is 2,357 passed with 8 local-DB skips, shared contracts are
  96/96, Mypy covers 114 files, and secret/bundle/protected-path findings are 0. The one final
  aggregate wrapper is explicitly not PASS: it stopped at formatting after 19 unique prior stages;
  formatter correction and every unrun constituent then passed independently.
- Advanced application `0.11.1→0.12.1`, Web `0.7.0→0.8.0`, prompt set `0.3.1→0.4.0`, tests
  `1.9.2→2.1.1` and documentation `2.26.1→2.29.0`; API/shared/DB/data axes are unchanged.

### Fixed — local hybrid classifier runtime composition

- Wired the approved bounded Upstage classifier into the actual local/private
  `create_local_app()` citizen route instead of leaving it available only to direct adapter tests.
- Shared one non-resettable `ProviderAttemptLedger` across classifier and grounded generation in
  the combined profile while preserving deterministic provider-zero safety routes and bounded
  fallback on provider failure.
- Added local factory regression tests for provider startup/probe zero-use, ambiguous classification,
  combined caps, client lifecycle, failure fallback and no-row policy routes.
- Advanced application to `0.11.1-classifier-runtime`, tests to
  `1.9.2-classifier-runtime` and documentation to `2.25.1`; API, contracts, DB and data are unchanged.

### Implemented — natural civic dialogue and governed scope operations

- Added privacy-first hybrid classification, exact certificate follow-up choices, text-free signed
  context v2, contextual follow-ups, direct region selection and an explicit new-conversation reset.
- Added the isolated `CIVIC_SCOPE_GAP` 30-day masked review queue, typed admin API/Web review,
  operator-authored general KB candidates and candidate status history.
- Added property-only `00700` hardening for the ADR-0018 exact 22 functions with matching rollback,
  body/owner/ACL fingerprints and an 11-migration replay gate.
- Added a fixed PII-free 60-case classifier gate. Only 20 ambiguous cases use Upstage; the
  corrective actual run passed 60/60 with policy/privacy outbound 0 and cumulative VAT-inclusive
  cost USD 0.003873210.
- Advanced application to `0.11.0-natural-dialogue`, Web to `0.7.0-natural-dialogue`, API to
  `4.0.0-draft`, shared contracts to `1.0.0`, DB to `0.5.0-local`, prompt set to
  `0.3.1-hybrid-classifier`, tests to `1.9.1-natural-dialogue` and docs to `2.24.1`.
- Local DB hardening, immutable `.2` seed/19→20 and actual Upstage classifier gates pass.
  Remote discovery found no configured application/DB target, credential, origin or saved version;
  migration, seed, deploy and smoke are recorded as `Not executed: target not configured`.
- Final verification passed all 33 root stages, 24 browser scenarios across 390/430/desktop and 135
  focused privacy/classification/followup/admin scenarios. Documentation advanced to `2.25.0`.

### Planned — natural dialogue implementation

- Added the reviewed 18-task TDD plan for PII correction, hybrid classification, context v2,
  scope-gap operations, public hardening, clean DB, actual Upstage and controlled remote evidence.
- Repository discovery found no configured remote target/project, so remote deployment has an
  exact `target not configured` evidence path while all independent work continues.
- Advanced documentation from `2.23.0` to `2.23.1`; runtime, contract, DB, data and provider state
  remain unchanged.

### Approved — integrated natural dialogue specification and actual execution

- Recorded D-091/D-092: the three approved design sections are consolidated into one
  implementation specification with exact routing, context v2, scope-gap DB/API/admin,
  failure, performance, test, rollback and version boundaries.
- Actual PII-free Upstage classification, clean local DB reset and immutable `.2` seed, public
  `00700` hardening and configured remote citizen-route verification are approved. Remote admin
  remains disabled without authentication.
- Advanced product specification from `2.5.0` to `2.6.0` and documentation from `2.22.6` to
  `2.23.0`. Product code, contracts, DB and provider runtime remain unchanged in this documentation
  commit.

### Approved — natural chat design section 2

- Recorded D-090 approval of the `CIVIC_SCOPE_GAP` public reason and separate 30-day masked review
  queue, with NON_CIVIC/policy/privacy no-row boundaries preserved.
- Approved context v2 closed topic/slot/dialog claims, v1 read-only TTL transition and an explicit
  Web new-conversation reset. Exact contract/DB/runtime work remains unimplemented.
- Product/API/DB/provider behavior is unchanged. Advanced documentation from `2.22.5` to `2.22.6`.

### Approved — natural chat design section 1

- Recorded D-089 approval of the privacy-first hybrid request pipeline and 15-minute
  server-issued structured context without raw transcript or citizen profile storage.
- Public response, persistence, error and test details remain in design review; product/API/DB/
  provider behavior is unchanged. Advanced documentation from `2.22.4` to `2.22.5`.

### Decided — realistic civic guidance and operations product target

- Recorded Q-PROD-REAL-001=A/D-088: the product will mature as a realistic official-guidance,
  office-routing and human-governed improvement platform.
- Actual application submission, status lookup, payment and government/internal-system
  transactions remain P2 and must not be claimed as current product behavior.
- Moved CHAT-NATURAL-001 from product-scope interviewing to design review. Product/runtime/API/DB/
  data/provider behavior remains unchanged. Advanced documentation from `2.22.3` to `2.22.4`.

### Audited — natural dialogue and realistic civic-service readiness

- Recorded Q-CLASS-002=A: the classifier is limited to one 3-second attempt, no retry, 1,024 input
  characters, 128 output tokens and process sub-cap 20; grounded generation keeps sub-cap 30 and
  the combined process cap is 40 with a VAT-inclusive USD 0.05 local synthetic stop line.
- Audited current chat, context, retrieval, feedback, admin, source lifecycle, authentication,
  rate-limit, backup, load and accessibility boundaries against active code and source-of-truth.
- Added a P0/P1/P2 roadmap that prioritizes PII false-positive correction, hybrid routing,
  text-free structured context, scope-gap review and general candidate authoring before public
  hardening. Actual application/status/payment integration remains a product-scope decision.
- Product/runtime/API/DB/data/provider/dependency behavior and actual calls remain unchanged.
  Advanced documentation from `2.22.2` to `2.22.3`.

### Decided — hybrid bounded LLM question classification

- Recorded Q-CLASS-001=A and ADR-0025: deterministic PII/policy/high-confidence gates remain,
  while only safely masked ambiguous questions may use a closed-enum Upstage classifier.
- The model cannot decide answers, sources, KB IDs, candidate eligibility, retention or persistence.
- Q-CLASS-002 budget and the written specification remain pending; product/runtime/provider calls
  are unchanged. Advanced documentation from `2.22.1` to `2.22.2`.

### Decided — separate civic scope-gap review queue

- Recorded Q-SCOPE-001=A and ADR-0024: safely masked outside-current-scope civic requests will use
  a separate 30-day scope-expansion review queue rather than the existing KB candidate workflow.
- `NON_CIVIC` remains text/review-row free, and scope-gap rows cannot automatically become ACTIVE.
- This is an accepted future direction only; runtime, OpenAPI, DB, provider and admin code remain
  unchanged. Advanced documentation from `2.22.0` to `2.22.1`.

### Documented — chat classification and PII false-positive gaps

- Reproduced four reported fixture paths without persisting citizen text.
- Isolated two PII contextual-name false positives and the missing distinction between non-civic,
  current-scope gap and supported-intent ambiguity.
- Recorded the recommended hybrid deterministic/bounded-LLM architecture and the separate
  `CIVIC_SCOPE_GAP` retention decision. Product, contract, DB, provider and dependency code remain
  unchanged. Advanced documentation from `2.21.9` to `2.22.0`.

### Changed — certificate follow-up specification approval and TDD plan

- Recorded D-084 approval of the category-aware certificate FOLLOWUP written specification.
- Published a five-task TDD plan covering classifier priority, closed server labels, text-free
  service orchestration, typed Web copy/context, full gates and version evidence.
- Product code, API shape, DB, data, provider, dependencies and tests remain unchanged. Advanced
  documentation only from `2.21.8` to `2.21.9`.

### Changed — certificate category follow-up design approval

- Recorded Q-CHAT-FOLLOWUP-001=A: a generic certificate request will return
  `CERTIFICATE_ISSUANCE + FOLLOWUP` with five exact ACTIVE-KB-bounded certificate options instead
  of repeating the four-category question.
- Preserved unsupported compound certificates as OUT_OF_SCOPE, specific supported queries as
  direct retrieval candidates, text-free FOLLOWUP events and the existing signed context design.
- Published the written specification for review. Product code, API shape, DB, data, provider,
  dependency and tests remain unchanged. Advanced documentation only from `2.21.7` to `2.21.8`.

### Changed — actual chat and admin system audit

- Exercised the actual local chat, admin and office read paths through the browser and UTF-8 API
  requests. Specific supported questions, official source binding, safe fallbacks, 15-minute
  context and responsive routes passed.
- Reproduced three P0 gaps: the generic certificate option loops back to the same four-category
  FOLLOWUP, arbitrary eligible failures cannot be authored into candidates, and the initial
  citizen region selection path is unreachable even though the office endpoint works.
- Confirmed that the apparent missing admin draft is an approved candidate hidden by the
  pending-only view, not an LLM configuration failure. Current policy requires operators—not the
  LLM—to author official answer, fee, department and source fields.
- Product code, API contract, DB, data, provider and tests remain unchanged. Advanced
  documentation only from `2.21.6` to `2.21.7`.

### Changed — certificate category follow-up diagnosis

- Reproduced the generic certificate request as `UNKNOWN + FOLLOWUP` and traced the four-category
  prompt to the classifier's missing generic certificate cue plus the service's UNKNOWN-only
  follow-up branch. The Web renders that server response faithfully.
- Recorded a recommended category-aware FOLLOWUP that stays within the five approved certificate
  KB topics, while leaving the exact option set for human product approval.
- Product code, public contract, Web, DB, data, provider and tests remain unchanged. Advanced
  documentation only from `2.21.5` to `2.21.6`.

### Changed — local Web development dependency recovery

- Diagnosed the Web startup failure as a production-only `node_modules` state followed by Next.js
  attempting to spawn a bare `pnpm` executable that was not present on the user's PATH.
- Restored the already-declared TypeScript development packages from the frozen lockfile through
  Corepack. All 407 packages were reused from the local store, Web typecheck passed, and package
  manifests plus the lockfile remained unchanged.
- No provider, database, secret, API, product or Web source behavior changed. Advanced
  documentation only from `2.21.4` to `2.21.5`.

### Changed — ready 200 and local Web actual setup

- Reconfirmed the user-started API at `/ready=200` without outputting its body.
- Created an ignored, non-secret Web local environment with exact loopback API, actual chat,
  local admin enabled and actual admin transport settings. All four aggregates passed and port
  3000 was free.
- Provider calls and DB query/write/reset/seed remained zero. Advanced documentation only from
  `2.21.3` to `2.21.4`.

### Changed — grounded mode false local verification

- Verified without outputting values that the ignored local environment has exactly one lowercase
  `false` grounded-mode assignment and the runtime loader remains `DISABLED`.
- Confirmed the environment remains ignored and the Docker client/server plus local DB container
  are ready for the next manual API step. No provider call or DB query/write was made.
- Advanced documentation only from `2.21.2` to `2.21.3`.

### Changed — explicit local grounded-mode guidance

- Confirmed without printing values that a missing `UPSTAGE_GROUNDED_CHAT_MODE` leaves the exact
  local grounded profile disabled. The fail-closed loader returned `DISABLED`.
- Recommended one explicit `UPSTAGE_GROUNDED_CHAT_MODE=false` assignment for human-readable local
  intent. Environment, product, provider, DB, data and dependencies were not changed.
- Advanced documentation only from `2.21.1` to `2.21.2`.

### Changed — post-PR #17 human action handoff

- Recorded PR #17 merge authority `c945303` and separated the remaining human-only work from
  Codex-owned implementation: manual display/accessibility/presentation rehearsal, A-052 Phase B
  database selection, and teammate MFA/recovery confirmation.
- Added a value-free Windows local start guide, five-question expected-result checklist, 200% zoom
  and keyboard walkthrough, presentation timing, and a copyable result template.
- Kept the current ACTIVE 20 database immutable for the rehearsal. Reset, seed, deletion, provider
  actual, public/remote work, product/API/DB/data/dependency changes remain prohibited.
- Advanced documentation only from `2.21.0` to `2.21.1`.

### Changed — final local demo readiness and performance smoke plan

- Added a fixed-target local context-secret provisioner that generates a CSPRNG value, updates only
  the primary checkout's ignored `apps/api/.env`, preserves unrelated bytes and never prints the
  secret. Seven focused tests cover target resolution, ignore enforcement, atomic replacement,
  invalid generation and value-free output.
- Completed a provider-disabled latest-main local rehearsal: `/health=200`, `/ready=200`, normal
  chat SUCCESS/TEMPLATE with one server-owned source, PERSONAL_LOOKUP with
  `candidate_eligible=false`, office match/empty, approved admin read and provider attempts 0.
- Re-ran Web lint, typecheck, unit, build and fixture-isolated Playwright; 21/21 browser cases passed
  across 390px, 430px and desktop. Manual 200% zoom, visual contrast/large-text, keyboard-only demo
  and presentation timing remain human Pending.
- Split PERF-001 into a provider-off, DB-write-free 100 VU/60-second Phase A and a cached/fixed chat
  Phase B. Phase B remains HOLD until A-052 chooses a disposable clean DB or explicitly authorizes
  bounded writes to the current non-KPI local DB.
- Advanced repository guidance to `1.7.9`, test suite to `1.8.0-local-demo-readiness` and
  documentation to `2.21.0`. Product/application/Web/API/shared/DB/data/prompt/dependency,
  public/remote scope and official rows are unchanged.

### Changed — OFFICE-API-001 runtime parity

- Implemented the already-declared `GET /api/v1/offices` in the default and local FastAPI
  applications. Required region plus supported intent returns server-mapped OFFICIAL records in
  existing `public_id` order; valid no-match returns exact `200 {"items":[]}`.
- The route is always discoverable in the default app and runtime OpenAPI, while the closed default,
  false readiness and database-unavailable paths return value-free `SERVICE_UNAVAILABLE` with
  `Retry-After: 30`. Missing or unsupported filters return value-free 422 without a repository call.
- Reused one local repository/pool/readiness probe and one shared chat/directory office mapper.
  Public office responses do not expose internal `department_label`, and source/office metadata is
  never generated by an LLM.
- The final-review fix declares the exact runtime OpenAPI 503 `Retry-After` header schema, adds a
  manifest-derived active API-version consistency test, and records D-080 as the execution-plan
  approval and Subagent-Driven implementation authority. PR #15 is merged as `b66e18c`.
- Published API `3.3.0-draft`, strict `OfficeListResponse`, generated shared contracts `0.6.0`, and
  test-suite `1.7.1-office-directory-review-fix`. Application is
  `0.10.0-office-directory-runtime`; documentation is `2.20.10`.
- The aggregate verifier remains **NOT PASS** because it stopped at
  `PREFLIGHT-UV reason=exception code=2` after PowerShell/Node/pnpm preflights. Fresh final-review
  constituent gates passed: API 2,044 passed, 8 DB-only skipped and 5 subtests passed with one
  pre-existing Starlette warning; root 431 passed with 2 skipped; shared contracts 90/90;
  generation, docs, secret and diff checks passed.
- Post-merge bounded read-only Docker/Supabase smoke passed with `/ready=200`, office match
  `200/count=1`, and valid empty `200/count=0`. It used a process-only CSPRNG context secret and the
  existing allowlisted local DB setting; `.env` copy, returned record/DSN/secret output,
  purge/reset/seed/write and provider calls were all zero.
- No DB migration, seed, official/mock data, Web, LLM/provider, production dependency, lockfile,
  public/remote deployment or admin exposure changed. Rollback reverts router/service/model/shared
  mapper, tracked OpenAPI and generated TypeScript together; no data rollback is required.

### Changed — LLM-003 grounded local/private chat generation and actual evidence

- Approved Q-LLM-006=B, Q-LLM-007=A, Q-LLM-009=A, Q-LLM-011=C and Q-LLM-012=B
  for a local/private-only Upstage `solar-pro3` chat path. Q-LLM-008=A summary-only is
  superseded by the later full structured-answer attempt decision.
- Provider calls are limited to safe-masked, supported-intent, ACTIVE/OFFICIAL and sufficiently
  grounded requests. Policy/follow-up/insufficient-grounding paths make zero provider calls.
- The model may propose a bounded summary and server-issued fact IDs only. The server materializes
  official facts and binds sources/offices; timeout, schema, unknown ID or fact drift discards the
  entire model result and uses the deterministic template.
- Fixed the design limits at 8 seconds, one logical attempt, zero hidden retry, concurrency one and
  30 outbound attempts per process. The approved response draft adds
  `answer_mode=GENERATED|TEMPLATE` and accessible Web labels.
- D-073 records written-specification approval and D-074 authorizes the eight-task TDD plan. Tasks
  1~7 now implement the additive SUCCESS `answer_mode`, source-free bounded fact materialization,
  exact disabled-by-default local profile, one-attempt fallback, durable idempotency boundary,
  optional local lifecycle and accessible Web disclosure.
- The provider can only propose a summary and request-scoped fact IDs. The server validates and
  materializes every official fact, source and office; disabled/default, timeout, transport, schema,
  ID or fact-drift failure returns the entire official template rather than a mixed response.
- Same-key concurrency/replay uses the existing safe-response idempotency path so it cannot start a
  duplicate provider call. Only a caller-supplied key can retain the strict final safe response for
  the logical 24-hour TTL.
- Task-scoped offline evidence and independent reviews are recorded in
  `docs/test-reports/LLM-003-GROUNDED-LIVE-CHAT.md`. The final provider-disabled root
  `scripts/verify.ps1 -Offline` PASSed on 2026-07-26 (637.7s, stdout 2006 bytes, stderr 0),
  including root/data/seed/Web/API/contracts/secrets/bundle/package/diff gates.
- D-075 local actual PASSed through the real local `/api/v1/chat` path: 10 cases,
  GENERATED 4/TEMPLATE 6, source 10/10, official mismatch 0, typed write-boundary forbidden-value
  violations 0 for the PII-free fixtures, outbound 10,
  legacy-reported input/output tokens 4183/954 and VAT-inclusive USD 0.001319835 lower bound.
  The configured 10-call maximum is USD 0.0135168 including VAT, below the USD 0.05 cap. A separate
  forced timeout returned TEMPLATE with no extra outbound. The final stdout was one aggregate JSON
  object only.
- The actual harness now retains content-free provider token usage, rejects usage above the exact
  1,024 output-token boundary, labels future interaction writes `is_test=true`, and fails before a
  forbidden-value DB write. It also requires usage-bearing results for all 10 provider attempts;
  this hardening is future-only and does not retroactively upgrade the legacy aggregate. Existing
  local DB login rotation now verifies the exact safe role and sole `sejong_backend` membership.
- The two pre-fix successful runs inserted 22 metadata-only rows as `is_test=false`; they must be
  excluded from KPI evidence. Safe cleanup requires a separately approved local DB reset or
  bounded deletion because this branch cannot uniquely distinguish those rows from other events.
- D-076 records the user's exact acknowledgement of the corrective second 10-call governance
  incident and authorization to merge PR #13, resolving A-049. It does not approve future provider
  reruns, deletion of the 22 rows, public/remote use or automatic merge.
- Public/remote use, real-institution operation, new production dependencies, DB migration,
  official/mock-data mutation and automatic merge remain prohibited or Pending under their
  existing gates.
- Clarified the pre-existing idempotency exception: only a caller-supplied key may retain the
  strictly validated final safe response for the existing logical 24-hour TTL. Raw/masked question,
  prompt/provider body, context/correlation and new DB migration remain prohibited.
- Closeout axes are application `0.9.1-grounded-local-chat-evidence`, Web `0.6.0-answer-mode`, API
  `3.2.0-draft`, shared contracts `0.5.0`, prompt `0.2.0-grounded-live-chat`, tests
  `1.6.1-grounded-actual`, documentation `2.20.2`. DB `0.4.0-local`, official data
  `0.1.0-initial.2`, mock data `0.0.0-not-populated`, dependencies and lockfiles are unchanged.

### Changed — LLM-002 Upstage local actual evaluation

- Ran the approved local/private canonical `T-01`~`T-10` Upstage exact `solar-pro3` evaluation
  once after a fail-closed local configuration repair. The initial configuration-only exit made
  zero provider calls and no artifact.
- The actual run consumed 30 outbound attempts: 27 strict-schema successes and three
  `SCHEMA_INVALID` attempt outcomes. It completed 29 generation cases, produced two deterministic
  fallbacks, and failed the mandatory 30/30 JSON criterion.
- Human PM review covered the nine fixtures with a valid first result: mean
  `4.844444444444444444444444444`, minimum dimension 4, `OK=9`, critical fact errors 0. Estimated
  cost was USD 0.004654815 including VAT against the USD 0.05 cap.
- Overall verdict is FAIL. Upstage citizen/free-input/public/remote option B is not approved;
  provider-disabled ACTIVE-KB template behavior remains authoritative. No product/API/DB schema,
  official data, dependency, lockfile or public behavior changed.
- Documentation `2.17.0→2.18.0`; all other version axes are unchanged.

### Changed — POST-MVP-001 private main stabilization

- Adopted Frontend PR #10's exact `allowedDevOrigins: ["127.0.0.1"]` change on an owner-reviewed
  branch without widening the collaborator config allowlist or public CORS/deployment scope.
- Added an exact config regression and a Next development-server Playwright gate. The current main
  failed RED with an undefined origin list; the owner change passed GREEN, Web 49/49, lint,
  typecheck, production build and the hydrated 127-origin resource probe.
- Synchronized the active product name to `세종 민원이음`, recorded PR #9 as merged, and kept
  historical plans/implementation evidence unchanged. The formal local seed sequence and
  `[db.seed].enabled=false` were rechecked and required no change.
- Versions: product specification `2.4.1`, repository guidance `1.7.8`, application
  `0.8.1-main-stabilization`, Web `0.5.1-local-dev-origin`, tests
  `1.5.1-local-dev-origin`, documentation `2.17.0`; API, contracts, DB, official/mock data and
  prompt set are unchanged.

### Changed — Frontend PR #8 owner integration and current actual Web evidence

- Integrated human-merged Frontend PR #8 at owner merge commit `c15f61b`, normalized its colliding
  implementation-note IDs to `009`/`010`, and preserved contracts, API, DB migrations, official data,
  provider prompt and dependencies unchanged.
- Closed the critical actual/fixture draft regression: actual `/admin` can create the reserved
  `KB-WASTE-03` candidate only from the exact PM-approved canonical question and OFFICIAL fields;
  unrelated or unconfirmed failures fail closed instead of promoting demo fixture content.
- The actual browser UI now requires different approver, OFFICIAL origin, non-empty review comment
  and checklist 3/3 before it submits activation. The service/DB continue to enforce different
  approver, OFFICIAL and comment; checklist evidence is not yet a public API/DB invariant. Added
  feedback dialog initial focus, dynamic radio-aware focus trap, Escape close and opener focus
  restoration.
- Replaced the excluded stale browser scenario with the current `*.actual.spec.ts` path. A fresh
  disposable `db reset` with automatic seed still disabled, separate immutable `.2`
  `seed-cycle → verify-final → provision`, and current PR #8 UI passed PERSONAL zero persistence,
  separate IG `+1`, reason/candidate/approval, same-query SUCCESS and exact server source. Final
  read-only evidence is ACTIVE 20, `KB-WASTE-03` exactly once and `/ready=200`.
- Web unit 48/48, lint, typecheck and production build passed; fixture Playwright passed 18/18 at
  390/430/desktop and actual Playwright passed 1/1. The final repository-wide offline gate passed
  root/data/Web/API/contracts/secret/bundle/package/diff through `verification=complete`.
- Kept `ADMIN_UI_ENABLED=false` while synchronizing the root security test with PR #8's explicit
  `CHAT_UI_MODE=actual` and `ADMIN_UI_MODE=actual` defaults. Hidden feedback radios now expose a
  visible `focus-within` ring on their chip labels.
- `supabase/config.toml` remains `[db.seed].enabled=false`; the runbook now separates migration reset
  from the formal immutable seed stage. `allowedDevOrigins: ["127.0.0.1"]` remains a separate
  Frontend PR task and is not part of this owner PR. Public admin, remote DB, provider actual,
  deployment and auto-merge remain blocked.
- Versions: application `0.8.0-pr8-frontend-baseline`, Web
  `0.5.0-pr8-citizen-admin-baseline`, tests `1.5.0-pr8-web-baseline`, documentation `2.16.0`,
  repository guidance `1.7.7`; API, contracts, DB, official/mock data and prompt are unchanged.

### Changed — Q-PM-DEMO-001 actual persistence and browser evidence

- Q-PM-DEMO-001=B keeps the product policy unchanged while proving two separate local/private paths:
  PERSONAL_LOOKUP returns the exact safe policy fallback with `interaction_events` and
  `failed_questions` delta `0/0`; a distinct INSUFFICIENT_GROUNDING request produces delta `1/1`.
- The actual backend runner starts at immutable `.2` ACTIVE 19, preserves idempotent fallback replay,
  confirms reason/candidate submit, blocks same-writer approval, accepts `PM-LOCAL-001`, re-queries to
  exact public source `KB-WASTE-03`, and ends at ACTIVE 20 with four categories × five.
- Historical pre-`c15f61b` evidence: the former opt-in desktop browser passed the old
  Frontend→same-origin Web API→FastAPI→local DB→actual `/admin`→same-query SUCCESS path. Candidate
  activation UUID remains internal; the current PR #8 UI rerun is recorded in the newer section
  above.
- Final read-only evidence is ACTIVE 20, target once and `/ready=200`. The immutable `.2`, public API,
  DB schema/migrations, product runtime, dependencies and provider prompt are unchanged. Upstage
  key/network/provider, remote DB, public admin/deploy and auto-merge use is zero.
- Versions: tests `1.4.0-q-pm-actual-evidence`, documentation `2.15.0`; application, Web, API,
  contracts, DB, official/mock data and prompt remain unchanged.

### Changed — LLM-002 Upstage synthetic evaluation design and plan

- Q-LLM-005=A/D-065/ADR-0022 supersedes the unimplemented DeepSeek provider/model choice with
  Upstage exact `solar-pro3` for a local/private, server-allowlisted synthetic evaluation only.
- The approved design evaluates canonical `T-01`~`T-10` up to three times each under a 30-attempt,
  concurrency-one, one-retry and USD 0.05 run boundary. Strict JSON, server-bound source metadata,
  deterministic fallback and no-content logging remain mandatory.
- Product code, API/DB/data, dependencies, secrets and network calls remain unchanged. Actual citizen,
  free-input, public or remote provider use requires separate option B approval after evidence review.
- D-066 records the user's written-specification approval and publishes the TDD execution plan for
  Review. The plan adds fail-closed input/output/attempt/cost limits and keeps implementation gated on
  a separate plan approval.
- D-067 records execution approval. Task 1 adds the disabled-by-default exact Upstage settings gate;
  focused 6 tests, Ruff, Mypy and independent re-review passed after malformed dotenv and non-string
  runtime values were proven RED then fixed. No key, network, public route, DB/data, dependency or
  lockfile was used or changed.
- Task 2 adds strict source-free output/prompt/outcome contracts, canonical UTF-8 input preflight and
  exact Decimal pricing. Independent review caught and closed aggregate-cost double multiplication
  and zero-attempt SUCCESS; focused 17 tests, Ruff and Mypy passed with key/network use still zero.
- Task 3 adds the atomic 30-attempt/concurrency-one budget and exact zero-hidden-retry HTTPX
  transport. Its 23-case MockTransport failure matrix and independent review passed; no key, DNS or
  provider network call occurred.
- Task 4 hash-binds canonical T-01~T-10 and reuses the deterministic privacy/classification/
  ACTIVE-only retrieval/grounding path before every generation. Independent review caught and
  closed stale grounding reuse between repetitions. Task 5 preflight added a required content-free
  attempt trace and local runner/report integrity gates before actual use.
- Task 4.5 preserves one content-free enum per outbound attempt and strictly reconciles preparation
  and provider evidence. Independent review caught and closed mutable aggregate evidence that could
  corrupt cost/source/fallback metrics; full LLM 93 tests passed.
- Task 5 adds the explicit text-free aggregate and a Windows-safe, readiness-before-provider local
  runner. Independent review caught and closed human FAIL, per-case trace and forged token PASS
  paths; report 30, runner 14 and full LLM 123 tests passed with actual DB/key/network use zero.
- Task 6 locked public-import isolation, provider-key/log/PII/source boundaries, strict attempt caps
  and safe `/api/v1/chat` failure behavior. At that historical offline checkpoint, actual evidence
  was Pending; the later D-071 run produced the recorded strict-schema 27/30 FAIL and superseded that
  checkpoint status.
- Versions: application `0.7.0-local-synthetic-evaluator`, prompt
  `0.1.0-upstage-solar-pro3-synthetic`, tests `1.3.0-upstage-synthetic-evaluator`, documentation
  `2.14.0`; public API, DB, official data and Web remain unchanged.

### Changed — MVP-001 local/private closeout

- Promoted application to `0.6.0-local-core-loop`, tests to `1.2.1-core-loop-closeout` and docs to
  `2.12.2` after final API 1,640, Web 48/lint/type/build, E2E 15, contracts 89, sample T-01~T-20
  20/20, clean DB pgTAP 9/356·API integration 8/8 and root offline PASS.
- Restored final local ACTIVE 20 after clean reset/seed/19→20 requery. Atomic idempotency and admin
  race fixes passed independent `0/0/0` reviews. MVP-001 is Review/local-private AI scope complete,
  not public-ready; human Draft PR/manual demo·accessibility and all provider/public/deferred gates remain.

### Added

- 2026-07-22 local/private core-loop integration: API `3.1.0-draft`, shared contracts `0.4.0`,
  application `0.6.0-local-core-loop-partial`, Web `0.4.0-chat-admin-local-integration` and DB
  `0.4.0-local`. The optional UUID `Idempotency-Key` is durable and separate from correlation IDs;
  HMAC digest, independent claim token, 5-minute lease, exact 24-hour TTL and startup/60-second
  purge remain local/private only. No provider, remote DB or public deployment was activated.
- DATA-SEED-002 supported actual continuation after the concurrency observer fix: baseline/identity,
  forced rollback `tables=8 partial=0`, concurrency A/B, seed 19/3/10, replay 1, second-seed and
  compensation guards, final citizen 19/exclusions 0/operational 0 and cleanup all PASSed. `.2` stays
  immutable and `official_data=0.1.0-initial.2`. That seed evidence alone does not claim application
  readiness; the later closeout above separately proves local `/ready=200` and final ACTIVE 20.
- Local admin actual transport is explicitly gated; default Web stays fixture and default/public admin
  remains disabled. Approved candidate source URLs use a six-host official allowlist with encoded-PII
  protection. Personal/legal policy fallbacks create no text, event, failed row or candidate in this MVP.
- DATA-SEED-002 immutable `0.1.0-initial.2` release, strict v2 schemas, independently reviewed
  create-once publication, byte-identical local dispatcher and exact predecessor/successor lineage.
  Three supported actual local runs reached concurrency A; the bounded diagnostic isolated
  concurrency B as `CAPABILITY_WRITE_DID_NOT_BLOCK`, cleanup passed, and no DB/READY/official-data
  promotion was claimed. Commit `eb74ac8` passed independent 0/0/0 review for the relation
  OID-equality observer correction. This historical failure record is superseded by the supported
  actual PASS continuation above; it remains for audit lineage.
- Q-MVP-001 four-day local/private milestone: D-058/ADR-0020, 2026-07-25 19→20 ACTIVE core-loop
  scope, date/role plan, DATA-SEED-002 execution approval and explicit post-Saturday deferrals
- Cloud exact runtime evidence: Node `v24.12.0`, Python `3.12.13`, pnpm `11.13.0`, uv `0.11.28`,
  clean tree/docs PASS and zero file/commit/PR/secret/provider/DB/Docker/deployment use; COLLAB Task 6 complete
- Post-COLLAB sequencing evidence: hold the existing teammate onboarding branch until its colliding note `012`
  is synchronized and renamed to reserved `014`; run Cloud runtime evidence and approved DATA-SEED-002 in parallel
- Corrected Cloud rehearsal 002 integration evidence: PR #3 exact two-document scope, explicit Cloud-internal
  versus GitHub publication identities, manual merge commit `d54fd6f`, and green PR/post-merge hosted checks
- PR #2 merge/post-merge evidence: remote `main` advanced to merge commit `b61f676`, hosted collaboration
  and frontend summaries passed, and the next Cloud action is corrected rehearsal 002 rather than the
  held/unpublished rehearsal 001 result
- Cloud rehearsal result triage: the first agent run produced an internal two-file commit and truthful
  missing-scanner failure, but independent GitHub evidence shows no remote branch or Draft PR; the run
  is held from publication because its generated note ID collides with the local integration branch,
  and the next run must use the actual PowerShell current-tree scanner after local docs integration
- Frontend owner-to-teammate kickoff handoff with a copy/paste security preflight, GitHub clone,
  exact Node/pnpm/uv/Python provisioning, full frontend baseline, two-file onboarding PR/self-merge
  gate and structured completion report; remote `main`/local pre-merge divergence is now recorded
  truthfully and product coding waits for the shared-contract consumption boundary
- Codex Cloud runtime fallback for the selector's actual Node `22 / 20 / 18` limit: use Python `3.12`
  and temporary Node `22`, then persist exact Node `24.12.0`/Python `3.12.13` with nvm/pyenv before
  frozen pnpm/uv installs; screenshot evidence confirms universal/manual setup, empty env/secrets, enabled
  cache and the visible nvm/pyenv prefix; the `sejong-ai-cloud-docs` environment is now saved with agent
  internet Off, and the first rehearsal starts from `main` while writing only to its requested `codex/*`
  task branch; first-task setup execution and Draft-PR evidence remain pending
- D-057 COLLAB-001 post-merge evidence: user-confirmed `Only select repositories / Sejong_AI`, PR #1
  merge commit and green post-merge collaboration/frontend Actions; App scope is complete while Cloud
  Draft-PR and teammate MFA/onboarding evidence remain pending
- COLLAB-001 owner/teammate execution checklist for GitHub App UI confirmation, MFA/recovery,
  bootstrap PR merge, no-secret Codex Cloud Draft-PR rehearsal, Frontend clone/baseline/self-merge and
  forbidden-scope close-without-merge rehearsal; D-056 corrects the earlier inference that public
  repository visibility proves an over-broad App installation
- COLLAB-001 local Tasks 1~3 automation: an integrated value-redacting full reachable-history scanner,
  exact base/head PR author/path scope
  classifier, add-only web implementation-note/INDEX validator, tracked active Markdown/JSON checker,
  candidate-tree secret scan mode, pinned read-only GitHub policy/frontend workflows, PR/Issue/ownership
  templates and cross-platform production Playwright startup; independent review closed Critical/
  Important findings at 0 after bounding candidate Git stdout/stderr/time and per-file/aggregate reads
- D-054: 사용자의 `COLLAB-001 계획 승인, 구현 시작`으로 협업 전환 실행계획을 승인하고 로컬
  history-secret/scope/docs 검사기와 GitHub workflow/template 구현을 시작; account 인증이 필요한
  remote·invite·Codex App·rehearsal은 실제 외부 증거 전까지 pending
- Q-GIT-001/Q-OWN-001/Q-GIT-002/Q-GIT-003/Q-CLOUD-001/Q-COLLAB-001과 ADR-0019:
  개인 GitHub private 단일 저장소, 인간 Frontend 팀원의 전체 UI 수직 흐름과 제한적 self-merge,
  사용자 검토가 필요한 contract/backend/DB/data/security/dependency 경계, Codex Cloud
  Draft-PR-only, local-only Docker/Supabase/DeepSeek actual gate를 승인된 협업 명세·Frontend
  handoff·Review 실행계획으로 기록; pre-push content secret 0, remote/CI/invite/App 설정과 제품
  코드는 아직 변경하지 않음
- Q-GIT-004=A/D-053: 기존 author/committer email이 사용자 본인이며 private Frontend
  collaborator에게 보여도 괜찮음을 확인해 현재 history·SHA 보존과 noreply rewrite 0을 확정;
  당시 COLLAB-001을 Review로 전환했고, 이후 D-054 실행 승인 전까지 remote/commit/push/CI/invite/App
  변경 0
- Q-SEED-002=A/D-044 and ADR-0017 successor correction execution: preserve immutable `.1`, publish
  reviewed `.2` with the PostgreSQL 17 effective membership-option union, and require the full
  disposable-local cycle before official-data promotion; `.2` is published while actual DB import
  remains blocked before seed-cycle completion
- Q-PII-002=A/D-045 privacy-safe public behavior: future HTTP 200 `PRIVACY_UNRESOLVED` rephrase
  outcome with no text/failed row/provider/source/context; active contract and DB remain unchanged
  pending a separate consumer specification and forward-migration approval
- Q-SEC-003=A/D-046 and ADR-0018 exact 22-signature `search_path=pg_catalog, pg_temp` direction;
  `00700` implementation is explicitly deferred until public preparation and public paths stay blocked
- AI-001A standard-library fail-closed PII masking core with 13 closed categories, five unresolved
  reasons, immutable value-free findings, Unicode normalization/control rejection, deterministic
  overlap selection, conservative contextual ambiguity closure, and a frozen 74-case exact oracle;
  representative/service phones, repeated whitespace separators, Hangul explicit values, and
  fixed-token trailing-raw bypasses fail closed; irregular numeric/vehicle/email splitting, health
  modifiers, phone extensions, generated-token tail composition, and value-less inquiry controls are
  covered by direct regressions and positive value-evidence grammars; a 254-case category-gap suite
  plus independent actual/safe/insertion/Unicode/separator matrices found no raw fail-open or safe
  false positive at the final frozen source; this pure core has no route, DB, provider,
  official-data, or public API activation
- User-approved Q-PII-003=A public-number masking policy and AI-001A execution plan: citizen-provided “official” labels are untrusted, all phone-shaped input values are masked, and approved official contacts remain server-combined KB/office metadata cards
- User-approved AI-001 PII written specification and AI-001A TDD plan for an isolated standard-library core, frozen exact-output synthetic v1 evaluation set, Unicode/overlap/residual/bypass gates, and no route/DB/provider activation; its former A-032 gate is resolved by Q-PII-003=A/D-043
- User-approved AI-001 fail-closed PII masking core design and written specification: standard-library deterministic typed rules, value-free fixed tokens/findings, unsafe result with no text, metadata-only event allowance, and no route/DB/provider implementation yet
- Immutable filesystem official release `0.1.0-initial.1` with approved 19 KB·3 offices·10
  mappings, approval/artifact/semantic hashes, excluded KB 1 and rejected mappings 2, deterministic
  seed/compensation SQL, and a byte-identical local dispatcher while `[db.seed].enabled=false`
- DATA-SEED active-release-compatible no-Docker root stages for focused unit/static tests,
  `verify-release`, and `verify-local-seed`; Task 7A root and independent review passed
- DATA-SEED `.1` lineage with the Task 5 publication evidence, Task 6 actual attempts/fixes/blocker,
  cleanup boundary, immutable correction policy, and A-030/Q-SEED-002 successor decision gate
- WEB-HOME-001 static `/chat` preparation shell, navigable home CTA, explicit no-input/no-storage/request allowlist browser guard, 390/430/desktop accessibility checks, and actual Chrome UI 200% zoom verification
- Standalone exact-locked `tools/web-e2e` Playwright test project and a permanent production dependency/deploy gate that keeps Playwright out of the citizen Web runtime graph
- DATA-001 internal staging schemas, dependency-free fail-closed validator, canonical DRAFT KB 20·office 3·mapping 12, hash-bound `PENDING_PM_REVIEW` manifest, deterministic validation report, lineage, and PM review packet; all remain non-ACTIVE and outside citizen reads, seed, and readiness
- Codex repository guidance, first-run interview prompt, source-of-truth hierarchy
- ADR, implementation-note, handoff, ambiguity-audit workflows
- Draft API contracts and DB schema aligned with final scope
- Legacy project quarantine and current-repo audit
- Initial discovery report, interview answer ledger, and Interviewing execution plan
- ADR-0007 local/private admin security boundary
- ADR-0008 Supabase CLI versioned SQL migration boundary
- ADR-0009 HTTP 503 service-unavailable boundary
- ADR-0010 server-session-free signed client-carried chat context
- Dependency-free root pnpm workspace contract with exact Node 24.12.0, pnpm 11.13.0, Python 3.12.13, and uv 0.11.28 pins
- Standard-library repository scaffold contract tests for runtime, workspace, package-manager, credential, and ignored-path invariants
- FastAPI 0.1.0 scaffold with import-safe app factory, exact `/health`, pre-DB `/ready=503`, typed readiness probe, strict public models, tests, and a frozen uv lock
- Next.js 16.2.10 static `/` shell with truthful development limits, four approved service areas, semantic landmarks, mobile-first accessible styles, four render tests, and a frozen pnpm lock
- Service-scoped Web/API environment templates, metadata-only FastAPI request logging, Uvicorn unsafe-log hardening, and standard-library repository/browser artifact secret scanners
- Strict shared-contract validator with 17 synthetic fixtures, 27 fixture validations, and six OpenAPI structure/reference guards
- Deterministic OpenAPI TypeScript generation/check commands and strict Pydantic raw-JSON consumers for the same 17 contract fixtures
- PowerShell 5.1-compatible 24-stage local verification gate with exact runtime preflight, frozen/default and warm-offline modes, fail-fast exit preservation, scoped synthetic Web secret checks, and metadata-only diagnostics
- DB-001 executable-schema discovery report covering migration lineage, atomic approval, retention, ACTIVE-only access, provenance, permissions, rollback, and database test gaps
- ADR-0011 and a written DB-001 design for private schemas, capability functions, atomic approval, retention, and layered DB/backend enforcement
- User-approved DB-001 written specification and an execution-gated TDD plan covering pinned local tooling, five migrations/compensations, pgTAP, lazy FastAPI DB boundaries, concurrency, and rollback/replay
- D-026/D-027 refinements for fail-closed non-superuser role verification, separate failed-question reason confirmation, immutable event classification, candidate gating, and required approval comments
- DB-001 candidate-stage lineage: six immutable timestamp forward migrations and six disposable-local
  compensations for private schema, invariants, capability/RLS, candidate workflow,
  ACTIVE+OFFICIAL reads, and deferred validator posture. Promotion was blocked at that stage until the
  later patched-runtime and actual-loopback gates produced the verified `0.3.0-local` baseline below
- Six-file pgTAP 282 assertions, real backend integration 8/8, exact
  `006→005→004→003→002→001` compensation/absence/reset/replay gate, and local DB handoff/report
- Checksum-pinned Supabase CLI v2.109.1 source, Go 1.25.11 toolchain, 1,824-byte two-file
  loopback patch, reproducible runtime SHA-256, and patched-only DB runner with no stock/PATH fallback
- Verified disposable `0.3.0-local` baseline: exact single `127.0.0.1:54322`, fresh pgTAP 282,
  backend integration 8/8, six-stage compensation/absence/replay, final container 0/0, volume deletion 0

### Changed

- Recorded D-055 external collaboration evidence and advanced repository guidance to `1.7.1` and
  documentation to `2.9.1`: private `tskwak111/Sejong_AI` bootstrap, matching `main` SHA, ordinary
  initial push, policy and frozen Frontend CI PASS, accepted `koregy` write access, repository variable,
  private visibility, read-only default Actions and direct-push warning. COLLAB-001 remains In Progress:
  Task 5 is partial: teammate MFA/recovery and the first Task 7 PR-only/no-direct-main-push rehearsal,
  repository-limited Codex App, Cloud Draft PR/manual merge and remaining teammate rehearsals are pending;
  no product/application/web/API/contract/DB/data/prompt/dependency behavior changed
- Corrected the AI-001A isolated-worktree handoff to forbid junctioning a worktree `.tools` to the
  main ignored tool directory; require byte-copy/hash verification instead after Windows cleanup was
  observed following the junction target, and reproducibly restored exact uv and patched Supabase runtime
- Completed the isolated AI-001A core and permanent standard-library/no-I/O architecture gate while
  leaving parent AI-001, citizen-visible unresolved-PII behavior, official readiness, DeepSeek
  adapter, and public deployment behind their existing independent blockers
- Resolved A-032 and moved AI-001A from Review to Ready while keeping parent AI-001, official seed/readiness, unresolved-PII consumer behavior, and public deployment blocked by their existing independent gates
- Clarified the source-of-truth privacy boundary: successful masking is necessary but not sufficient for storage or synthetic-provider use; unresolved PII forbids failed-question text/row and provider calls, while actual citizen DeepSeek transmission remains prohibited
- Materialized PM-LOCAL-001's exact 35-record DATA-001 review evidence at `2026-07-19T02:06:19+09:00`: KB approve 19/withhold 1, office approve 3, mapping approve 10/reject 2. Immutable content hashes remain unchanged. Corrected `.2` filesystem release and dispatcher are published/verified, but three actual runs did not pass concurrency B, so DB rows, ACTIVE reads, readiness and `official_data` promotion remain blocked.
- Pinned the approved development baseline to Node 24.x+pnpm and Python 3.12+uv; installation begins in Phase 1 after the user's 2026-07-15 approval
- Clarified local-first/zero-infrastructure-budget as the active target and managed hosting as separately approved future work
- Updated OpenAPI and logical DB drafts to 0.2.0: failed-question text expires after 30 days while metadata and candidate links remain
- Assigned official KB/office authoring to AI/Data·Backend and approval to PM, targeting 2026-07-20
- Pinned local/private synthetic evaluation to `deepseek-v4-flash`, thinking off, max 1024, concurrency 1, one retry, and 30 total outbound attempts per explicit process run
- Selected Supabase CLI versioned SQL migrations; CLI installation and migration execution remain deferred until DB-001
- Chose conservative recall-first name/address masking with a measured, human-approved relaxation gate
- Changed the public API draft to 1.0.0: 200 responses no longer allow SYSTEM_ERROR and unrecoverable service failure uses a stable 503 SERVICE_UNAVAILABLE envelope
- Chose local Git and manual validation gates for the current phase; remote repository and CI are deferred until the user asks to connect Git
- Replaced undefined `session_id` with a 15-minute signed opaque `context_token`, current-tab transcript memory, and no server session/transcript persistence; API draft is now 2.0.0
- Defaulted the disposable local demo to RPO 24h/RTO 60m, daily/pre-risk gitignored dumps, 30-day dump deletion, and restore-before-open retention purge
- Approved the final plan and initial production dependency list; began independent local Git and Phase 1 scaffold work while keeping public/real-user boundaries deferred
- Split Phase 1 into exact runtime, pre-DB health/readiness, Web shell, env/log boundary, contract/generated drift, and clean local verification review units
- Adjusted the approved ESLint development tool from the incompatible 10.7.0 candidate to exact 9.39.5 for the Next 16.2.10 bundled plugin peer range; production dependencies were unchanged
- Tightened the existing API 2.0.0-draft so SUCCESS requires at least one source and aligned nullable optional fallback office validation across OpenAPI and standalone JSON Schema
- Made public Pydantic boundary models reject scalar coercion and preserved optional OpenAPI fields with defaults in generated TypeScript
- Patched the public draft to API 2.0.1-draft: `/health` and ready-state `/ready` 200 bodies are required closed schemas, and FALLBACK extras are rejected consistently across OpenAPI, standalone JSON Schema, and Pydantic
- Scoped pnpm dependency verification/offline and six synthetic Web build environment values with exact restoration, while suppressing child output that could disclose paths or values
- Preserved the local `.pnpm-store/` cache while adding it to the tested transient-path ignore contract so it cannot be committed accidentally
- Updated the database environment record after verifying the local Docker engine, while keeping Supabase CLI installation and migration execution behind written DB design review
- Resolved Q-DB-002 as layered database-and-backend enforcement while keeping remote/public execution deferred
- Approved the DB-001 written specification for planning; migration, Docker, CLI download, and DB mutation remain deferred until the new plan is explicitly approved
- Approved the DB-001 execution plan and completed Tasks 0~5; applied migrations `00100`~`00300` remain immutable, workflow moves to `00400`, and citizen reads move to `00500`
- Completed DB-001 Tasks 0~9 and prepared Task 10 local baseline closeout without changing
  public API, official/mock seed, application version, or readiness; `00100~00500` remain immutable
  and `00600` is the validator-only posture correction
- Prepared the `repo_guidance=1.5.0`, `database_schema=0.3.0-local`,
  `test_suite=0.5.0-db-baseline`, and documentation `2.4.0` candidate closeout, then kept the
  committed manifest axes unchanged after the local port security blocker was reproduced
- Applied the approved Q-SEC-004 Docker Desktop `default-local-port-binding` policy and fully
  restarted the engine; an actual HostIP-omitted probe resolved to IPv4 `127.0.0.1` plus IPv6
  wildcard `::`, while an explicit `127.0.0.1` control resolved to one loopback binding. Both
  disposable probes were removed and no Supabase DB mutation was run
- Applied the approved Q-SEC-005 `local-only-port-binding` policy and restarted Docker Desktop;
  the HostIP-omitted probe still resolved to `127.0.0.1` plus IPv6 wildcard `::`, while the explicit
  `127.0.0.1` control remained single-loopback. Both probes were removed, container count returned to
  zero, and no Supabase DB mutation was run
- Completed Q-SEC-006/A-024 and Q-TOOL-001/A-025 locally with source manifest
  `c293e5ac32bae030eadf383d8d9511dc16eac834e51e996273ae8b7e39616657`, patch
  `109c096480e8185d761e9ce8fba10e93efc55190c42eab978f769a6993833f7d`, and runtime
  `751068e73834c5da58ac7c5287a1d66a82ad356f508637b0478d6531cdb3941c`; DB-001 is Done for
  disposable local/private use only
- Bounded DB child process trees in `73f300b`; focused descendant cleanup 1/1, full runner 50/50,
  patched tooling 24/24, independent review 0/0/0 and final-code DB revalidation PASS
- Recorded DATA-SEED Task 6 as Blocked rather than promoted: the authoritative PostgreSQL 17
  grantor-specific ADMIN/INHERIT/SET effective union conflicts with immutable `.1` seed/compensation
  exactly-one-row membership guards. The runner stopped before writes after two reviewed bounded
  fixes; no role/grant/migration/release byte changed, and cleanup ended at container 0/port listener 0
- Hardened DATA-SEED prepare rollback so any cleanup failure after owned-directory quarantine keeps
  the canonical release absent, leaves any residual only at a noncanonical path, and permits
  a safe retry. Added the exact partial-delete regression and a true post-staging-validation snapshot
  mutation guard; published `.1` bytes, dispatcher, DB, migration, API and official-data version stay
  unchanged

### Pending

- DATA-SEED-002 separate execution decision before any fourth actual run of reviewed relation
  OID-equality correction `eb74ac8`. The last diagnostic reason is
  `CAPABILITY_WRITE_DID_NOT_BLOCK`; the full DB gate remains Blocked while non-DB MVP lanes continue
- Full actual disposable PostgreSQL seed/rollback/concurrency/compensation/replay/citizen-read cycle;
  `official_data` remains `0.0.0-not-populated` until every gate passes
- Deployment accounts and URLs
- Official seed/readiness/chat/admin vertical slices
- Q-SEC-003/A-021 privileged-function search-path hardening before any public release;
  default B keeps remote/public deployment, public admin/API, and public backend DB credentials blocked
