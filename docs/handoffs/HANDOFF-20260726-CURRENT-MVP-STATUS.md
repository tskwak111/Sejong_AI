# Handoff — 2026-07-26 current local/private MVP status

- Date: 2026-07-26 KST
- Branch/commit at audit start:
  `codex/LLM-003-metadata-explanation` / `9fe9aa1`
- Remote source authority: `origin/main=be7387f7e7ddf3e0cca6b7ccef76dd1b1f507d6b`
- Versions: product `2.5.0`, application `0.9.1-grounded-local-chat-evidence`,
  Web `0.6.0-answer-mode`, API `3.2.0-draft`, DB `0.4.0-local`,
  official data `0.1.0-initial.2`, documentation `2.20.4`

## Repository/collaboration state

- Source remote: private `tskwak111/Sejong_AI`.
- `git fetch --prune origin` 뒤 remote main은 PR #13 merge SHA `be7387f`다.
- PR #11은 SHA `257c35f`로, PR #13은 SHA `be7387f`로 MERGED다.
- audit 시점 GitHub open PR은 0개다.
- current main hosted Collaboration policy와 Frontend CI는 각각 SUCCESS다.
- GitHub/Cloud/Frontend PR-only rehearsal은 완료됐고 collaborator MFA/recovery 확인만
  human Pending이다.
- 현재 docs decision/status branch는 remote에 push하지 않았다. `origin/main`보다
  Q-DB-CLEANUP 설명·결정 commit 2개와 이 status closeout commit만 앞서게 된다.
- 기본 worktree의 local `main=f5c3a1d`는 current `origin/main`보다 뒤이므로 그대로 새
  작업 기준으로 사용하지 않는다.
- source code의 publish/merge는 별도 사용자 요청 전 수행하지 않는다.

## 진행률 해석

진행률은 코드 줄 수가 아니라 실행 가능한 인수 기준을 기준으로 산정한다.

| 관점 | 공학적 추정 | 근거 |
|---|---:|---|
| local/private 평가·데모 MVP | 약 90% | 핵심 시민 흐름, local DB 19→20, 관리자 승인 루프, Upstage 선택형 생성·template fallback, 자동 테스트와 actual evidence 완료. 수동 접근성·데모와 일부 contract parity가 남음 |
| 원래 확정한 P0/P1 전체 | 약 75% | top-level TASK 39개 중 Done 27, Review/In Progress 3, Pending/Deferred/Blocked 9. partial task를 일부 반영한 결과 |
| public/production 운영 준비 | 약 35~45% | public admin auth, `00700`, remote DB/deploy, CORS/secret/logging 운영, clean KPI, 부하, backup/restore가 미완료 |

이 숫자는 일정 약속이 아니라 범위별 readiness를 이해하기 위한 추정치다. local MVP와 public
서비스는 같은 완료율로 보지 않는다.

## 완료된 실제 제품

### 시민 Web

- `/`: 제품 소개, 4개 지원 분야, `/chat` 진입
- `/chat`: 현재 탭 대화, same-origin typed API client, FOLLOWUP, 안전 폴백, 공식 출처,
  공식 기관 카드, `GENERATED|TEMPLATE` 표시
- 390px·430px·desktop responsive E2E와 keyboard-focused automated gate

### 관리자 Web

- `/admin`, `/admin/failures`, `/admin/kb-candidates`
- local/private demo actor 전환, 실패 질문 조회·사유 확정, 후보 작성·제출·별도 승인자 검수
- fixture KPI는 `시연 데이터`로 표시하고 actual quality summary는 미제공 안내
- public 인증이 아니며 외부 공개 금지

### Backend

- `/health`, `/ready`, `/api/v1/chat`
- local/private admin 실패 질문·후보·제출·검수 route
- PII fail-closed 마스킹, deterministic 분류, ACTIVE/OFFICIAL 검색, grounding gate
- optional Upstage `solar-pro3` one-attempt 생성, server-owned fact/source 결합, 모든 오류에서
  complete TEMPLATE fallback
- signed client-carried context, durable UUID idempotency, metadata-only interaction write
- PERSONAL_LOOKUP/LEGAL_JUDGMENT/PRIVACY_UNRESOLVED의 승인된 무저장 경계

### DB·데이터

- versioned SQL migration 9개와 matching local verification/rollback lineage
- immutable official `.2` seed
- 2026-07-26 read-only actual 확인:
  - ACTIVE/OFFICIAL KB 20
  - OFFICIAL office 3
  - office-service mapping 10
- 실패 질문 30일 text purge, candidate workflow, same-writer approval 차단, audit metadata
- Q-DB-CLEANUP-001=A에 따라 오표시 22행은 유지하고 current event count는 평가 KPI로
  사용하지 않는다.

### 계약·테스트 증거

- OpenAPI, JSON Schema, Pydantic, generated TypeScript contract
- deterministic sample T-01~T-20: 20/20, skip 0
- 승인 전 fallback→별도 승인자→20번째 ACTIVE→동일 질문 SUCCESS 회귀
- last publication offline gate: provider-disabled full root PASS
- LLM-003 local actual: 10개 중 GENERATED 4/TEMPLATE 6, source 10/10,
  official mismatch 0, outbound 10
- Web final evidence: 12 files/56 unit tests와 390/430/desktop browser 12/12

## 현재 실행 상태

- Docker engine: `29.2.1`
- `supabase_db_sejong-ai-local`: healthy
- read-only DB projection: ACTIVE 20 / office 3 / mapping 10
- `127.0.0.1:8000` API: 현재 실행 중 아님
- `127.0.0.1:3000` Web: 현재 실행 중 아님
- future Upstage actual rerun: 새 인간 승인 전 금지
- remote/public deployment: 승인·구현 전

## 확인된 간극

1. **Runtime/contract parity**
   - tracked OpenAPI에는 `GET /api/v1/offices`가 있으나 current default/local FastAPI
     OpenAPI에는 route가 없다.
   - P0 chat response의 server-bound office card는 동작하므로 시민 대표 흐름은 막지 않지만,
     공개 계약 정합성은 해결해야 한다.
2. **Quality summary**
   - tracked OpenAPI에는 `/api/v1/admin/quality-summary`가 선언돼 있지만 200 schema와
     FastAPI runtime route가 없다.
   - actual admin UI는 이를 정직하게 “연동 준비 중”으로 표시한다.
   - D-077 때문에 current dirty event snapshot으로 KPI를 만들면 안 된다.
3. **Hosted backend CI**
   - GitHub Actions는 collaboration policy와 Frontend CI만 실행한다.
   - API/Python/DB 전체 gate는 현재 local evidence에 의존한다.
4. **Human-only closeout**
   - manual large-text/contrast/keyboard/demo walkthrough
   - collaborator MFA/recovery 확인
5. **P1 operations**
   - 100-user smoke, clean KPI, backup/restore, final operations handoff
6. **Public readiness**
   - `00700` privileged-function hardening, real admin authentication/authorization,
     remote DB/deploy/CORS/secret/log retention/rollback

## 권장 다음 실행 순서

### Slice 0 — Git·문서 기준선 닫기

1. current docs/status branch를 최종 검토한다.
2. 사용자 요청이 있으면 push하고 Draft PR을 만든다.
3. 사람이 merge한 뒤 모든 새 작업은 latest `origin/main`에서 새 branch로 시작한다.

Acceptance:

- source-of-truth, TASKS, decision D-077, handoff와 manifest 정합
- hosted checks green
- local stale `main`을 작업 기준으로 사용하지 않음

### Slice 1 — local MVP contract/runtime stabilization

1. `GET /api/v1/offices`의 필요성을 existing contract 기준으로 확정하고 구현 또는
   breaking-contract 절차로 정리한다. 권고는 기존 contract를 만족하는 read-only 구현이다.
2. quality-summary는 지금 fake actual 값을 만들지 않는다. B reset 전까지 actual UI
   미제공을 유지하고 별도 schema 설계를 준비한다.
3. API/Web를 provider-disabled로 실행해 5개 대표 demo와 `/ready=200`을 다시 확인한다.
4. 사람이 large text·contrast·keyboard·focus·responsive demo checklist를 확인한다.

예상: 0.5~1.5 집중 개발일 + 사람 검수 1~2시간.

### Slice 2 — clean quality and operations

1. 정식 KPI가 실제로 필요하다는 인간 판단 시 Q-DB-CLEANUP-001=B 승인
2. disposable local reset→migration→immutable `.2` seed→필요한 19→20 승인 재현
3. quality-summary schema/API/Web actual 연동
4. 100-user limited smoke
5. backup/dump→restore→retention drill

예상: 2~4 집중 개발일. B 승인과 local runtime 안정성에 따라 달라진다.

### Slice 3 — public demo가 정말 필요한 경우에만

1. `00700` security hardening
2. real admin auth/RBAC와 public route policy
3. remote DB/provider/deploy 공급자·예산·quota 승인
4. CORS, secret rotation, infra logs, backup, rollback
5. public security/load/rehearsal

예상: 추가 3~7일 이상. 공급자 계정·권한과 공개 수준에 따라 크게 달라진다.

## 실행/테스트 명령

Provider-disabled local 기준:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/bootstrap_patched_supabase.ps1 -VerifyOnly

powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/verify.ps1 -Offline

python -B scripts/check_repository_docs.py
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
```

API와 Web 기동은 [LLM-003 local runbook](../runbooks/LLM-003-LOCAL-GROUNDED-CHAT.md) 및
각 app README를 따른다. 현재 status audit에서는 서비스를 시작하거나 provider를 호출하지 않았다.

## 환경변수 이름(값 제외)

Backend/local:

- `APP_ENV`
- `LOG_LEVEL`
- `CORS_ORIGINS`
- `DATABASE_URL`
- `CONTEXT_TOKEN_SECRET`
- `CONTEXT_TOKEN_TTL_SECONDS`
- `PII_RETENTION_DAYS`
- `DEMO_OPERATOR_ID`
- `DEMO_APPROVER_ID`
- `ENABLE_EMBEDDINGS`
- `ENABLE_DEMO_ROLE_SWITCH`
- `ENABLE_LOAD_TEST_ENDPOINT`
- `LLM_PROVIDER`
- `LLM_MODEL`
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_TIMEOUT_SECONDS`
- `LLM_MAX_RETRIES`
- `LLM_MAX_CONCURRENCY`
- `LLM_MAX_INPUT_TOKENS`
- `LLM_MAX_OUTPUT_TOKENS`
- `LLM_RUN_ATTEMPT_CAP`
- `UPSTAGE_SYNTHETIC_EVALUATION_MODE`
- `UPSTAGE_GROUNDED_CHAT_MODE`

Web/local:

- `API_INTERNAL_BASE_URL`
- `CHAT_UI_MODE`
- `ADMIN_UI_ENABLED`
- `ADMIN_UI_MODE`

값은 이 handoff, Git, PR, CI 또는 채팅에 기록하지 않는다.

## DB migrate/seed/rollback

- `[db.seed].enabled=false`를 유지한다.
- reset은 migration replay일 뿐 official seed가 아니다.
- 빈 disposable DB에서만 immutable `.2` `seed-cycle`을 실행한다.
- 현재 DB는 ACTIVE 20이므로 A 결정 아래 reset/seed를 다시 실행하지 않는다.
- B 승인 시 reset 뒤 `.2` 19개를 seed하고 필요하면 별도 승인 흐름으로 20번째를 재현한다.
- LLM runtime rollback은 grounded mode false, provider disabled, ignored key 제거 후
  TEMPLATE와 `/ready=200` 확인이다.

## 알려진 문제와 위험

- current local DB의 raw event count는 평가 KPI가 아니다.
- default API는 admin router를 포함하지 않고 local composition만 opt-in한다.
- `/offices` 및 `quality-summary`의 tracked/runtime parity가 미완료다.
- public admin auth가 없으므로 `/admin`은 local/private 시연 전용이다.
- GitHub hosted green은 API/DB 전체 검증을 의미하지 않는다.
- final clean-clone backup/restore와 manual a11y evidence는 아직 없다.

## 인간이 알아야 하는 결정

- 지금 기능 개발을 계속하는 데 DB reset은 필요 없다.
- 가장 가까운 인간 작업은 manual demo/a11y와 collaborator MFA/recovery 확인이다.
- hosted backend CI는 Actions quota/비용과 범위를 승인한 뒤 추가한다.
- clean KPI가 필요할 때만 B를 승인한다.
- public demo가 필요 없다면 Slice 3을 시작하지 않는다.

## 다음 작업 Acceptance Criteria

가장 가까운 권고 작업은 Slice 1이다.

- OpenAPI/runtime path gap이 명시적으로 해결되거나 승인된 deferred 상태
- provider-disabled `/health=200`, `/ready=200`
- 5개 대표 질문/개선 흐름에서 공식 출처와 안전 폴백 확인
- current event count를 KPI로 사용하지 않음
- manual accessibility/demo checklist 기록
- 관련 test/lint/typecheck/build, 문서, version, implementation note 동기화

## 최근 구현 노트/ADR/계획 링크

- [Q-DB-CLEANUP 설명](../implementation-notes/IMP-20260726-006-오표시-metadata-22행과-cleanup-선택지-설명.md)
- [Q-DB-CLEANUP 결정](../implementation-notes/IMP-20260726-007-q-db-cleanup-001-a-결정-확정.md)
- [LLM-003 actual evidence](../implementation-notes/IMP-20260726-002-llm-003-local-actual-실행과-aggregate-증거.md)
- [ADR-0023](../adr/0023-grounded-upstage-local-chat-generation.md)
- [LLM-003 plan](../superpowers/plans/2026-07-25-grounded-live-chat-generation.md)
- [MVP plan](../superpowers/plans/2026-07-22-four-day-local-private-core-loop-mvp.md)
