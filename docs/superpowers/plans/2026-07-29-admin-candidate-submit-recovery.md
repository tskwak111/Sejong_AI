# Admin Candidate Submit Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** KB 후보 create와 submit 실패를 구분하고 남은 DRAFTED 후보를 중복 생성 없이 재제출한다.

**Architecture:** 기존 API/DB 상태 머신은 유지하고 Web transport가 stable error code를 보존한다. 실패 질문 목록은 candidate status/id map으로 DRAFTED 재제출 액션을 복원한다.

**Tech Stack:** React 19, Next.js 16, generated OpenAPI TypeScript, Vitest.

**Status:** 구현 완료. 최종 검증 결과는 `IMP-20260729-020`에 기록한다.

## Global Constraints

- API/DB migration과 후보 상태 머신은 변경하지 않는다.
- server exception/message/body 값을 UI·로그에 노출하지 않는다.
- OPERATOR만 create/submit 액션을 수행한다.
- 새 production dependency를 추가하지 않는다.
- 사용자 소유 `apps/web/next-env.d.ts` 변경을 건드리지 않는다.

---

### Task 1: Stable admin transport errors

**Files:**
- Modify: `apps/web/src/lib/admin-api.ts`
- Modify: `apps/web/src/lib/admin-api.test.ts`

**Interfaces:**
- Produces: `AdminTransportError.code: AdminErrorCode | null`, status, retryable.

- [ ] **Step 1: Write RED**

422/409/403 JSON envelope에서 exact stable code만 보존하고 malformed/non-JSON body는 null로 닫는
transport behavior를 테스트한다.

- [ ] **Step 2: Verify RED**

Run: `corepack.cmd pnpm --filter @sejong-ai/web test -- admin-api`
Expected: FAIL because code is discarded.

- [ ] **Step 3: Implement safe parser**

`error.code` allowlist만 파싱하며 message와 unknown fields는 버린다.

- [ ] **Step 4: Verify GREEN**

Run the Step 2 command.
Expected: PASS.

### Task 2: Create/submit phase-specific recovery

**Files:**
- Modify: `apps/web/src/app/admin/failures/page.tsx`
- Modify: `apps/web/src/components/admin/FailureTable.tsx`
- Modify: `apps/web/src/components/admin/CandidateAuthoringForm.tsx`
- Modify: `apps/web/src/app/admin/admin-flow.test.tsx`

**Interfaces:**
- Produces: candidate map, `onSubmitDraft(candidateId)`, phase-specific alert copy.

- [ ] **Step 1: Write RED**

create 422 no-submit, submit 503 leaves DRAFTED retry, reload DRAFTED retry, retry success and no duplicate
create를 테스트한다.

- [ ] **Step 2: Verify RED**

Run: `corepack.cmd pnpm --filter @sejong-ai/web test -- admin-flow`
Expected: FAIL because generic toast and disabled “초안 생성됨” are current behavior.

- [ ] **Step 3: Implement minimal recovery UI**

DRAFTED에는 `승인 요청 다시 시도`, PENDING_APPROVAL 이상에는 `승인 요청됨`을 표시한다.
phase/status/code별 값 비노출 안내와 allowed official host 안내를 추가한다.

- [ ] **Step 4: Verify GREEN**

Run the Step 2 command.
Expected: PASS.

### Task 3: Accessibility and integration verification

**Files:**
- Modify: `docs/implementation-notes/IMP-20260729-020-kb-후보-제출과-시민-피드백-저장-동작-감사.md`
- Modify: `docs/implementation-notes/INDEX.md`

- [ ] **Step 1: Run Web area gate**

Run Web tests, lint, typecheck and build once after integration.
Expected: PASS with alert/focus/button accessible names.

- [ ] **Step 2: Review diff**

Confirm contracts/DB candidate workflow unchanged and `next-env.d.ts` excluded.

- [ ] **Step 3: Record evidence**

Update the implementation note with exact phase behavior, tests, rollback and handoff.
