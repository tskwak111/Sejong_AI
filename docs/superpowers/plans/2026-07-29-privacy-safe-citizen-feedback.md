# Privacy-safe Citizen Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 시민 만족/불만족과 선택적 상세 의견을 개인정보 안전하게 저장하고 local/private 관리자 집계에서 확인한다.

**Architecture:** 공개 feedback router는 strict request/service/repository 경계로 구성하고 기본 앱에서는 fail closed한다. local composition만 fixed DB capability adapter를 주입하며 Web actual transport가 응답 request ID와 폐쇄형 분류를 전송한다.

**Tech Stack:** FastAPI, Pydantic v2, psycopg 3, PostgreSQL 17/pgTAP, OpenAPI 3.1, React 19, Next.js 16, Vitest.

**Status:** 구현 완료. 최종 검증 결과는 `IMP-20260729-020`에 기록한다.

## Global Constraints

- 새 production dependency를 추가하지 않는다.
- raw 상세, 질문, 답변, provider body, secret, DSN을 저장하거나 출력하지 않는다.
- 상세는 기존 서버 마스킹 후 최대 30일만 보관한다.
- 외부 LLM, public deploy, remote DB를 사용하지 않는다.
- applied migration을 수정하지 않고 `20260729000710` forward/rollback으로 추가한다.
- 사용자 소유 `apps/web/next-env.d.ts` 변경을 건드리지 않는다.

---

### Task 1: OpenAPI and generated shared contract

**Files:**
- Modify: `contracts/openapi-v1.yaml`
- Modify generated: `packages/shared-contracts/src/generated/api.ts`
- Test: `scripts/check_contracts.py`

**Interfaces:**
- Produces: `FeedbackCreateRequest`, `FeedbackCreateResponse`, `FeedbackSummaryResponse`와 두 route.

- [ ] **Step 1: Write the failing contract/API tests**

`apps/api/tests/feedback/test_api.py`에 만족 shape, OTHER 상세 필수, 값 비노출 422/503,
`apps/api/tests/admin/test_api.py`에 local admin summary route를 추가한다.

- [ ] **Step 2: Verify RED**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/feedback/test_api.py apps/api/tests/admin/test_api.py -q`
Expected: FAIL because feedback contracts/routes do not exist.

- [ ] **Step 3: Add exact schemas and generate TypeScript**

`POST /api/v1/feedback`와 `GET /api/v1/admin/feedback-summary` 및 enum/shape를 OpenAPI에 추가하고
`corepack.cmd pnpm contracts:generate`를 실행한다.

- [ ] **Step 4: Verify contract generation**

Run: `corepack.cmd pnpm contracts:check`
Expected: PASS with generated TypeScript matching OpenAPI.

### Task 2: Forward migration, rollback, and pgTAP capability gate

**Files:**
- Create: `supabase/migrations/20260729000710_citizen_feedback.sql`
- Create: `database/rollbacks/20260729000710_citizen_feedback.rollback.sql`
- Create: `supabase/tests/database/012_citizen_feedback_test.sql`
- Test: `scripts/check_migrations.py`

**Interfaces:**
- Produces: `record_citizen_feedback`, `list_citizen_feedback`,
  `summarize_citizen_feedback`, `purge_expired_citizen_feedback_detail`.

- [ ] **Step 1: Write pgTAP RED**

12번 test에 exact private columns, forbidden columns 0, 4개 fixed function signature, owner/fixed
search_path/ACL, rating shape, idempotent same payload, conflict payload, 30일 파기를 명시한다.

- [ ] **Step 2: Verify migration RED**

Run: `python -B scripts/check_migrations.py`
Expected: FAIL because migration/rollback capability is absent.

- [ ] **Step 3: Implement minimal forward and rollback**

RLS/owner/check/index와 fixed capability 4개를 추가하고 backend EXECUTE만 허용한다. rollback은
grant→function→table 역순으로 제거한다.

- [ ] **Step 4: Run local DB test**

Run: approved patched Supabase database test command from `docs/runbooks/LOCAL_DEMO_RUNBOOK.md`.
Expected: all pgTAP files including `012` PASS; if Docker is unavailable record Pending without
claiming DB PASS.

### Task 3: Repository and privacy service

**Files:**
- Create: `apps/api/src/sejong_ai_api/contracts/feedback.py`
- Create: `apps/api/src/sejong_ai_api/feedback/service.py`
- Create: `apps/api/src/sejong_ai_api/feedback/__init__.py`
- Modify: `apps/api/src/sejong_ai_api/db/models.py`
- Modify: `apps/api/src/sejong_ai_api/db/repository.py`
- Test: `apps/api/tests/feedback/test_service.py`
- Test: `apps/api/tests/db/test_repository.py`

**Interfaces:**
- Produces: `FeedbackService.record(payload)`, repository record/list/purge methods.

- [ ] **Step 1: Write service and repository RED**

테스트는 raw detail이 repository에 전달되지 않음, phone masking, unresolved no-write, exact SQL,
malformed row fail closed, purge tuple mapping을 검증한다.

- [ ] **Step 2: Verify RED**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/feedback/test_service.py apps/api/tests/db/test_repository.py -q`
Expected: FAIL on missing feedback service/repository methods.

- [ ] **Step 3: Implement minimal service/adapter**

질문 마스커와 고정 개인정보 탐지·치환을 공유하는 `redact_feedback_detail()` 결과만 typed DB
write로 만들고 DB exceptions를 stable feedback errors로 변환한다. 전용 프로필은 일반 피드백
산문을 허용하되 이름·상세주소·고위험 숫자·비정상 유니코드는 계속 fail closed한다.

- [ ] **Step 4: Verify GREEN**

Run the Step 2 command.
Expected: PASS.

### Task 4: Public feedback and local/private admin routes

**Files:**
- Create: `apps/api/src/sejong_ai_api/api/feedback.py`
- Modify: `apps/api/src/sejong_ai_api/api/admin.py`
- Modify: `apps/api/src/sejong_ai_api/admin/service.py`
- Modify: `apps/api/src/sejong_ai_api/main.py`
- Modify: `apps/api/src/sejong_ai_api/local.py`
- Test: `apps/api/tests/feedback/test_api.py`
- Test: `apps/api/tests/test_local.py`
- Test: `apps/api/tests/admin/test_api.py`

**Interfaces:**
- Produces: fail-closed default feedback route, injected local recorder, admin summary route, purge lifecycle.

- [ ] **Step 1: Complete route/lifecycle RED**

기본 앱 503, local injection 201, admin default 403, startup/periodic purge 실패 readiness closed를
테스트한다.

- [ ] **Step 2: Verify RED**

Run: `apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/feedback/test_api.py apps/api/tests/test_local.py apps/api/tests/admin/test_api.py -q`
Expected: FAIL at missing route/dependency/purge call.

- [ ] **Step 3: Implement route and composition**

public validation handler는 feedback stable envelope를 반환하고 local app은 같은 repository로
FeedbackService와 AdminService를 구성한다.

- [ ] **Step 4: Verify GREEN**

Run the Step 2 command.
Expected: PASS.

### Task 5: Citizen Web actual feedback flow

**Files:**
- Create: `apps/web/src/lib/feedback-api.ts`
- Create: `apps/web/src/lib/feedback-api.test.ts`
- Create: `apps/web/src/components/citizen/FeedbackButtons.test.tsx`
- Modify: `apps/web/src/components/citizen/FeedbackButtons.tsx`
- Modify: `apps/web/src/components/citizen/FeedbackReasonSheet.tsx`
- Modify: `apps/web/src/components/citizen/FeedbackReasonSheet.test.tsx`
- Modify: `apps/web/src/app/chat/chat-screen.tsx`
- Modify: `apps/web/src/components/citizen/AnswerCard.tsx`
- Modify: `apps/web/src/components/citizen/FollowupCard.tsx`
- Modify: `apps/web/src/components/citizen/FallbackCard.tsx`

**Interfaces:**
- Produces: `FeedbackTransport.record(request)`, request ID propagation, OTHER/detail UI and retry behavior.

- [ ] **Step 1: Write Web RED**

실제 POST body, satisfied success-after-network, failure retry, OTHER category/reason, OTHER detail required,
300 char, request ID propagation을 observable UI/API behavior로 테스트한다.

- [ ] **Step 2: Verify RED**

Run: `corepack.cmd pnpm --filter @sejong-ai/web test -- FeedbackButtons FeedbackReasonSheet feedback-api`
Expected: FAIL because transport/OTHER/detail is absent.

- [ ] **Step 3: Implement minimal Web flow**

actual transport는 `/api/v1/feedback`만 호출하며 error body를 저장/출력하지 않는다. fixture transport는
메모리 상태만 성공 처리한다.

- [ ] **Step 4: Verify GREEN**

Run the Step 2 command.
Expected: PASS.

### Task 6: Admin feedback dashboard

**Files:**
- Modify: `apps/web/src/lib/admin-api.ts`
- Modify: `apps/web/src/lib/admin-api.test.ts`
- Modify: `apps/web/src/app/admin/page.tsx`
- Modify/Test: `apps/web/src/app/admin/admin-flow.test.tsx`

**Interfaces:**
- Consumes: `FeedbackSummaryResponse`.
- Produces: aggregate cards and recent masked feedback list.

- [ ] **Step 1: Write dashboard RED**

fixture/actual summary fetch, 만족률, OTHER 분류, 파기된 상세 대체 문구를 테스트한다.

- [ ] **Step 2: Verify RED**

Run: `corepack.cmd pnpm --filter @sejong-ai/web test -- admin-api admin-flow`
Expected: FAIL because summary transport/panel is absent.

- [ ] **Step 3: Implement dashboard summary**

관리자 gate와 기존 empty/error patterns를 재사용하고 원문 복원 UI는 만들지 않는다.

- [ ] **Step 4: Verify GREEN**

Run the Step 2 command.
Expected: PASS.

### Task 7: Integrated verification and documentation

**Files:**
- Modify: source-of-truth, version manifest, implementation note and INDEX.

- [ ] **Step 1: Run area gates**

Run API feedback/admin/db tests, Web unit/typecheck/lint/build, migration/contract/docs/secret scans.
Expected: all available gates PASS; local DB-only unavailable checks explicitly Pending.

- [ ] **Step 2: Run diff review**

Run: `git diff --check` and inspect `git status --short`.
Expected: no secret/generated drift; pre-existing `apps/web/next-env.d.ts` remains unmodified by this task.

- [ ] **Step 3: Update implementation evidence**

Record exact commands/results, versions, privacy/rollback and remaining public abuse gate in
`IMP-20260729-020`.
