# 4일 local/private 핵심 개선 루프 MVP 실행계획

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` for
> independent code tasks and `superpowers:test-driven-development` for every behavior change.

- Plan ID: MVP-001-PLAN
- Status: **Review — Q-PM backend runner와 actual browser PASS; human manual demo·accessibility pending**
- Window: 2026-07-22 02:10 KST ~ 2026-07-25
- Goal: local/private 19→20 ACTIVE 개선 루프와 시민/admin 최소 UI 완주
- Design: `docs/superpowers/specs/2026-07-22-four-day-local-private-core-loop-mvp-design.md`

## Global constraints

- Start base is fetched `origin/main` merge commit `9044ddb`.
- Never edit immutable `.1`, existing migrations `00100~00600`, raw approved facts, or `legacy/`.
- No actual citizen/provider call, remote DB, public deploy, secret output, volume deletion or new production dependency.
- Do not weaken raw-question 0, ACTIVE-only, server-bound source, self-approval, official/mock, keyboard/contrast gates.
- Every task: RED → minimal GREEN → focused test → full relevant gate → diff review → note/version update.
- Frontend collaborator never edits contract/package/lockfile/backend/DB/data/security paths.
- A human-only action is kept pending without stopping safe independent tasks.

## Date and role schedule

| Date | Owner / Backend·Data·Security | Frontend collaborator | PM/QA | Exit gate |
|---|---|---|---|---|
| 7/22 Wed | PR #5 post-merge baseline repair, PR #4 correction support, DATA-SEED-002 Tasks 1~5 | PR #4 `012→014`, then fixture-only `/chat` states | Q-MVP docs review, no new decision | canonical staging/release checks green; `.2` independently reviewable |
| 7/23 Thu | DATA actual cycle, 19 ACTIVE, PII/chat contract freeze, pure chat core/context | fixture UI complete; typed client prep after owner contract | verify 19 official rows and contract copy | DATA actual PASS; contract drift 0; chat core unit/privacy green |
| 7/24 Fri | `/api/v1/chat`, events, admin read/write API, 20th candidate backend | actual `/chat` integration, minimal `/admin` | author/reviewer role rehearsal | chat E2E + candidate submit/review atomic tests green |
| 7/25 Sat | final integration, security/sample/demo fixes | 390/430/desktop/accessibility fixes | sample 20, regression 1, final rehearsal | 20 ACTIVE, all local gates green, deferred items explicitly listed |

## Dependency graph

```text
Task 0 baseline/PR4
  -> Task 1 DATA-SEED-002 -> Task 2 19-row readiness
  -> Task 3 contract freeze -> Task 4 chat core -> Task 5 API chat
Task 3 -> Task 6 frontend fixture -> Task 7 frontend actual
Task 5 -> Task 8 event/admin -> Task 9 20th ACTIVE regression
Task 7 + Task 9 -> Task 10 sample/security/demo closeout
```

### Task 0: Restore the integrated main baseline and correct PR #4

**Files:**
- Modify: `scripts/check_collaboration_scope.py`
- Modify: `scripts/tests/test_collaboration_scope.py`
- Modify only if needed: staging validator focused tests
- Remote teammate branch: rename note `IMP-20260721-012-*` to `IMP-20260721-014-*` and matching INDEX row

- [x] Add a RED test proving policy literals/test fixtures cannot make canonical DATA staging invalid,
  while a real runtime import/path use still fails.
- [x] Change the collaboration policy representation so it does not contain an active staging path token;
  do not weaken the staging scanner allow/deny rules.
- [x] Confirm the earlier `jsonschema` finding was false: the repository already uses its strict validator,
  so no dependency or replacement was required.
- [x] Run focused collaboration/staging validation, `.1` release/dispatcher, docs and secret checks.
  The broad `scripts/tests` discovery remains a later root closeout gate because the initial environment run
  exceeded the task window and mixed unrelated local-runtime prerequisites.
- [x] Rebase/correct PR #4 note ID and verify its exact two-file docs-only scope. Head `37dfc8b`,
  CLEAN/MERGEABLE, hosted summaries green; human/team member merge remains pending.

### Task 1: Execute approved DATA-SEED-002 Tasks 1~5

**Files:** exactly those listed in
`docs/superpowers/plans/2026-07-20-data-seed-002-successor-release-correction.md` Tasks 1~5.

- [x] Freeze `.1`/v1 byte fingerprints and add dual closed release profiles.
- [x] Add successor three-`EXISTS` SQL/verifier semantics and align one pgTAP predicate.
- [x] Add strict v2 schemas and `.2`-only create/activate state machine.
- [x] Bind root/DB runners to `.2` while preserving cleanup/output allowlists.
- [x] Generate twice, independent reviewer Critical/Important 0, publish create-once `.2`, activate dispatcher.
- [x] Focused Python tests and protected-path fingerprint checks pass.

### Task 2: Run the disposable actual DB cycle and promote 19 ACTIVE

**Files:** DATA-SEED-002 Task 6 report/lineage/docs/version files only.

- [x] Bootstrap and verify the pinned patched Supabase runtime without revealing network credentials.
- [x] Run exactly `scripts/verify_data_seed.ps1 -ReleaseVersion 0.1.0-initial.2` from absent owned runtime.
- [x] Require pgTAP/integration/replay/compensation/19-3-10/cleanup PASS.
- [x] On complete PASS set only `official_data=0.1.0-initial.2`; keep `/ready=503` until application probe Task 5.
- [x] Historical failure was retained in lineage; the supported continuation passed without promotion on failure.

### Task 3: Freeze PII consumer, chat, and minimal admin contracts

**Files:**
- Modify: `contracts/openapi-v1.yaml`, `contracts/chat-response.schema.json`
- Modify/generated: `packages/shared-contracts/**`
- Modify: `apps/api/src/sejong_ai_api/contracts/**`, matching fixtures/tests
- Modify: `versions/manifest.json`, ADR/design/note

- [x] Write RED contract fixtures for `PRIVACY_UNRESOLVED`, admin list/detail/create/submit/review envelopes,
  exhaustive generated TS and strict Pydantic parity.
- [x] Add the response enum and exact no-source/no-context/no-office/candidate-false invariants.
- [x] Complete admin response schemas without changing path names.
- [x] Initial consumer freeze bumped API to `3.0.0-draft`/shared `0.3.0`; the approved idempotency
  continuation updates them to API `3.1.0-draft`/shared `0.4.0` in the same contract change.
- [x] No DB migration in this milestone for privacy metadata; reserved public `00700` remains untouched.

### Task 4: Implement the pure deterministic chat domain

**Files:**
- Create: `apps/api/src/sejong_ai_api/chat/{classification,retrieval,grounding,response,context,service}.py`
- Create: matching `apps/api/tests/chat/**` fixtures/tests
- Modify only for ports: DB repository protocol/fakes

- [x] RED tests for all 6 intents, ambiguous FOLLOWUP, 5 fallback reasons, lexical ranking and stable ties.
- [x] RED privacy spies: raw sentinel reaches no classifier/retriever/repository/provider/log/error.
- [x] Implement ACTIVE/OFFICIAL-only retrieval and server-bound source/office conversion.
- [x] Implement template SUCCESS and high-risk field omission; no provider SDK.
- [x] Implement 900-second signed context with value-free claims and silent invalid reset.
- [x] Validate sample 20 expectations at pure-service level with skip 0. Q-MVP-002=A로 T-16~T-18 구현 승인.

### Task 5: Implement `/api/v1/chat` and readiness

**Files:**
- Create: `apps/api/src/sejong_ai_api/api/chat.py`
- Modify: `apps/api/src/sejong_ai_api/main.py` and dependency composition/config
- Create/modify: route, contract, privacy, logging and DB integration tests

- [x] RED route tests for SUCCESS/FOLLOWUP/FALLBACK/PRIVACY/503/idempotency. Q-API-002=A에 따라 optional UUID header와 durable replay를 구현한다.
- [x] Connect redactor → service → repository and metadata event matrix.
- [x] Map DB unavailable to 503 only when no safe template/snapshot exists.
- [x] Enable `/ready=200` only when DB responds and required 19 ACTIVE+office projection exists. dedicated
  Windows `run_local_api` actual run에서 final local DB의 `/ready=200`을 확인했다. import-safe/default
  앱은 의도대로 계속 503이며 public readiness 주장이 아니다.
- [x] Ensure request body/raw question and context token are absent from access/error logs.
- [x] Re-check repository readiness on each `/ready` and guarded chat request; startup state is not treated as permanent.

### Task 6: Frontend fixture-first `/chat` in parallel

**Owner:** Frontend collaborator. **Allowed paths:** current collaboration allowlist only.

- [x] Build controlled fixture states for SUCCESS/FOLLOWUP/all fallback including privacy, empty office, 503.
- [x] Implement input, region, transcript, source/office cards, retry/duplicate-submit prevention.
- [x] Keep all transcript/token state in memory; browser storage/cookie/analytics 0.
- [x] Unit/E2E at 390/430/desktop, keyboard/focus/contrast/no-horizontal-overflow.
- [x] Owner integration branch owns this implementation; teammate PR #4 remains a separate docs-only human merge gate.

### Task 7: Connect actual typed frontend client

**Files:** owner prepares shared-contract package boundary; collaborator changes web/E2E only.

- [x] Owner exposes generated shared types with frozen workspace/lockfile change and review.
- [x] Frontend uses typed same-origin fetch while preserving test transport injection.
- [x] Treat 200 policy outcomes separately from 503; do not display stale transcript as sent.
- [x] Render source metadata byte-for-value; never synthesize URLs/dates.

### Task 8: Implement event/admin minimum

**Files:** API admin contracts/routes/services/repository reads and `apps/web/src/app/admin/**`.

- [x] RED tests for failed list/detail/expired text/filters and role gate.
- [x] RED tests for reason confirm, candidate PII recheck, submit, self-approval rejection, approve/reject.
- [x] Add typed repository read methods and minimal admin routes; public mode router disabled.
- [x] Add local role switch UI with explicit demo-only label and audit metadata view. default는 fixture이며
  명시적 `ADMIN_UI_MODE=actual`에서 actual same-origin API를 사용한다. opt-in actual browser가
  Frontend→API→DB 승인 루프를 PASS했다.
- [x] Confirm OUT_OF_SCOPE/FOLLOWUP/PRIVACY failed row 0 and 30-day failed-question text purge behavior.
  Service/DB gates cover row-zero and clean disposable API DB integration 8/8 proves actual purge/FK behavior.

### Task 9: Promote the 20th ACTIVE KB through the product loop

**Data:** `KB-WASTE-03`, existing PM-approved official source only.

- [x] Start from the canonical bed-frame question and record one `INSUFFICIENT_GROUNDING` masked failure.
- [x] OPERATOR confirms reason and authors candidate; same writer approval은 차단되고 다른 `PM-LOCAL-001`
  APPROVER가 승인했다.
- [x] Transactionally create exactly one ACTIVE/OFFICIAL 20th KB; audit snapshot text 0.
- [x] Re-run same question and require SUCCESS, expected fee/source, source count >=1 (`KB-WASTE-03`).
- [x] Record runtime lineage separately from immutable initial `.2` artifact.

### Task 10: Saturday acceptance and closeout

**Files:** evaluation report, security report, demo runbook, version/task/source-of-truth/note updates.

- [x] Run all 20 sample questions and publish numerator/denominator for success/fallback/followup/privacy.
  Deterministic pure-service report: total 20/20, SUCCESS 10/10, FOLLOWUP 2/2, FALLBACK 8/8.
- [x] Run regression 1, ACTIVE-only/DRAFT-hidden and raw-question/no-snapshot boundaries in the clean actual
  local regression. secret/history/browser-bundle gates also passed in the final root offline closeout.
- [x] Run API lint/type/full tests, web lint/type/unit/build/E2E, DB pgTAP/integration and root offline verify.
  API 1,640+5 subtests(8 DB-only skip), Ruff/Mypy 64, Web 48/lint/type/build/E2E 15, contracts 89,
  clean DB pgTAP 9/356·API integration 8/8와 `verify.ps1 -Offline` PASS.
- [x] Rehearse provider-off local demo from clean start through admin improvement.
- [x] Record 100-user, automatic backup, DeepSeek tuning, advanced UI, public deploy as deferred—not passed.
- [x] Independent spec and code/data/security review reports Critical 0, Important 0. Atomic idempotency,
  admin race, scanner and adapter final reviews are `0/0/0`.

## 2026-07-22 owner checkpoint

- 계약/PII/chat pure core/`/api/v1/chat`/same-origin `/chat`/disabled-by-default admin API와 fixture
  `/admin`까지 구현했다. API 전체 `1516 passed, 11 skipped`, contracts `87/87`, Web
  `29/29`, Playwright `12/12`, Ruff/Mypy/ESLint/TypeScript/Next build가 통과했다.
- 독립 리뷰의 Critical 0/Important 7 중 임의 demo actor·optional header, public `/admin`, stale
  readiness, optional office URL 직렬화와 무동작 쉬운말 UI를 교정했다. 정책 표본은 Q-MVP-002,
  durable 재시도는 Q-API-002, 실제 admin read는 Q-DB-004 결정 전 Pending이다.
- DATA-SEED actual continuation은 19/3/10 initial projection과 cleanup까지 PASS했다. `/ready=200`,
  actual admin 20번째 ACTIVE와 application-level requery는 여전히 별도 gate다.
- Q-MVP-002, Q-DB-004, Q-API-002를 사람 결정으로 열었다. 답 전에는 T-16~T-18, admin read migration,
  durable retry, 19→20 actual regression만 Pending이고 나머지 안전한 closeout은 계속한다.
- `/admin` fixture의 `MOCK` 후보는 ACTIVE 승인 불가, 반려만 가능하도록 UI와 transport 양쪽에서
  차단했다. 실제 OFFICIAL 승인 흐름은 local DB 연결 뒤에만 증명한다.

## 2026-07-22 fast-MVP approval checkpoint

- Q-MVP-002=A, Q-DB-004=A, Q-API-002=A를 D-059~D-061로 확정했다. 인터뷰 blocker는 없다.
- migration 번호는 `00650=local admin read`, `00660=chat idempotency`로 main owner가 고정했다.
- API 3.1.0-draft는 optional `Idempotency-Key`를 추가하고 policy fallback intent를 UNKNOWN으로 동결한다.
- DATA-SEED-002 historical fourth run은 concurrency B에서 중단됐으나 observer 수정 뒤 지원 actual
  continuation은 concurrency A/B·seed·replay·compensation·final 19/3/10·cleanup까지 PASS했다.
- actual data blocker와 독립적인 API/DB migration/Web/admin transport 구현은 세 lane으로 계속한다.

## 2026-07-24 Q-PM-DEMO-001=B actual evidence checkpoint

- D-059의 제품 동작은 변경하지 않았다. backend actual runner가 데모 #4 PERSONAL_LOOKUP의
  `UNKNOWN/PERSONAL_LOOKUP/candidate=false`와 interaction event/failed row delta 0을 증명했다.
- 같은 runner가 별도 INSUFFICIENT_GROUNDING 질문의 event+failed delta 1, reason confirm,
  candidate submit, same-writer block, PM-LOCAL-001 승인, 20번째 ACTIVE와 requery SUCCESS를 증명했다.
- opt-in actual browser는 real `/chat`→same-origin API→local DB→actual `/admin`→PM 승인→동일 질문
  SUCCESS와 서버 결합 공개 source ID·공식 출처 링크를 별도로 증명했다. 관리자 candidate의
  `activated_kb_id`는 내부 UUID이며 공개 `KB-WASTE-03` 증거가 아니다.
- 상세 실행·출력 안전 경계는
  [Q-PM-DEMO-001 plan](2026-07-24-q-pm-demo-001-actual-evidence.md)이 소유한다.

## Daily stop conditions

- Raw question, secret, DSN, token or PII appears in output/storage/provider: stop and security review.
- `.1`/v1 byte changes or official fact drift: stop; never regenerate in place.
- New architecture/public/remote/dependency decision: keep that lane pending and continue safe lanes.
- DATA actual failure: preserve evidence and continue contract/frontend fixtures; do not claim 19 ACTIVE.
- Contract changes after frontend actual integration: stop merging UI until generated drift is green.

## Plan self-review

- Every user priority 1~8 maps to Tasks 0~10.
- Human account/PM gates are separated from AI-executable work.
- Deferred items remain in the final project backlog and are not counted as Saturday PASS.
- No `TBD`, placeholder acceptance criterion, secret, private URL, raw question corpus or unapproved dependency.
