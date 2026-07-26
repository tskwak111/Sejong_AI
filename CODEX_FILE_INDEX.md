# Codex 파일 인덱스

## 반드시 Codex가 자동/초기에 읽는 파일

| 파일 | 목적 |
|---|---|
| `AGENTS.md` | 매 작업 공통 규칙, 범위, 안전, 구현 노트 의무 |
| `apps/web/AGENTS.md` | 프론트 로컬 규칙 |
| `apps/api/AGENTS.md` | 백엔드 로컬 규칙 |
| `data/AGENTS.md` | 공식/mock/평가 데이터 규칙 |
| `contracts/AGENTS.md` | 공개 계약 변경 규칙 |

## 사용자가 첫 세션에 입력할 파일

| 파일 | 목적 |
|---|---|
| `CODEX_START_PROMPT.md` | 발견 감사, 모호성 탐색, 우선순위 인터뷰, 계획 승인 요구 |
| `FIRST_RUN_CHECKLIST.md` | 첫 실행 누락 방지 |

## Codex가 계획과 작업을 관리하는 파일

| 파일 | 목적 |
|---|---|
| `PLANS.md` | 긴 작업 실행계획 규약 |
| `TASKS.md` | 현재 P0/P1 백로그와 의존성 |
| `docs/11_AMBIGUITY_REGISTER.md` | 미지의 영역·질문 상태 |
| `docs/decisions/DECISION_LOG.md` | 사용자 결정 로그 |
| `docs/adr/` | 장기 아키텍처 결정 |
| `docs/discovery/INTERVIEW_ANSWERS.md` | 인터뷰 답변 원문·해석·해결 상태 |
| `docs/superpowers/specs/` | 구현계획 전에 사용자가 검토하는 기능·아키텍처 서면 설계 |
| `docs/superpowers/plans/` | 승인된 명세를 TDD 실행 단위·명령·검증·commit으로 분해한 구현계획 |
| `docs/plans/PLAN-20260714-001-foundation-and-governed-chat.md` | 승인된 전체 실행계획과 단계별 gate |
| `docs/superpowers/plans/2026-07-16-db-001-layered-enforcement.md` | 승인된 DB-001 상세 실행계획; Tasks 0~10와 bounded child-tree remediation·final-code DB gate 완료, final docs reviews 진행 중 |
| `docs/superpowers/specs/2026-07-17-q-sec-006-patched-supabase-cli-design.md` | local에서 구현·검증된 exact source·Go·patch·binary hash·actual loopback 공급망 명세 |
| `docs/superpowers/plans/2026-07-17-q-sec-006-patched-supabase-cli.md` | 수정 계획 승인 뒤 Tasks 1~5 local gate와 code remediation까지 수행한 계획; final docs reviews 진행 중 |
| `docs/superpowers/specs/2026-07-18-data-001-staged-official-data-design.md` | DATA-001 staging JSON·hash-bound PM 검수 경계; AI scope complete / Review (PM pending) |
| `docs/superpowers/plans/2026-07-18-data-001-staging-and-review-package.md` | DATA-001 DRAFT 20/3/12·validator·PM handoff와 Remediation 3 full-root verification 기록; official release/seed는 별도 DATA-SEED-001 |
| `docs/superpowers/specs/2026-07-20-github-codex-cloud-collaboration-design.md` | 승인된 private GitHub·Frontend 소유권·Cloud Draft-PR-only 협업 경계 |
| `docs/superpowers/plans/2026-07-20-github-codex-cloud-collaboration-transition.md` | Tasks 1~4 complete; Task 5 partial; App scope와 secret-free Cloud environment 저장 완료, docs-only Draft-PR/manual-merge와 teammate onboarding rehearsals pending |
| `docs/discovery/MVP_001_FOUR_DAY_LOCAL_PRIVATE_AUDIT.md` | 7월 25일 local/private 핵심 루프의 권위·현재 코드/데이터 gap과 통합 회귀 감사 |
| `docs/superpowers/specs/2026-07-22-four-day-local-private-core-loop-mvp-design.md` | Q-MVP-001=A로 승인된 19→20 ACTIVE 시민·관리자 수직 흐름과 defer 경계 |
| `docs/superpowers/plans/2026-07-22-four-day-local-private-core-loop-mvp.md` | 날짜별·역할별 4일 TDD 실행계획과 일일 exit gate |
| `docs/superpowers/specs/2026-07-25-grounded-live-chat-generation-design.md` | D-073으로 승인된 local/private Upstage fact-ID·server-bound source 서면 명세 |
| `docs/superpowers/plans/2026-07-25-grounded-live-chat-generation.md` | LLM-003 계약→validator→transport→ChatService→local/Web→최종 gate 8-task TDD 계획; offline·final root·D-075 local actual 완료 |
| `docs/test-reports/LLM-003-GROUNDED-LIVE-CHAT.md` | LLM-003 offline/final root와 aggregate-only local actual PASS 증거 |
| `docs/implementation-notes/IMP-20260725-005-llm-003-grounded-live-chat-implementation.md` | LLM-003 offline 6W1H 구현·버전·rollback·인수인계; 당시 actual Pending인 역사 증거 |
| `docs/implementation-notes/IMP-20260726-002-llm-003-local-actual-실행과-aggregate-증거.md` | LLM-003 local actual 실행·비용·보안·rollback 6W1H 증거 |
| `docs/runbooks/LLM-003-LOCAL-GROUNDED-CHAT.md` | disabled-first local/private grounded chat·고정 actual runner·rollback runbook |
| `scripts/run_upstage_grounded_chat_actual.py` | 실제 `/api/v1/chat` 10건과 forced timeout의 aggregate-only local actual runner |
| `scripts/tests/test_run_upstage_grounded_chat_actual.py` | actual runner의 hash/source/cost/output/timeout 보안 경계 회귀 |

## 모든 작업 후 갱신할 파일

| 파일 | 목적 |
|---|---|
| `docs/implementation-notes/` | 6W1H 구현·결정 기록 |
| `versions/manifest.json` | 코드/API/DB/데이터/프롬프트/테스트/문서 버전 |
| `CHANGELOG.md` | 외부에 설명할 변경 요약 |
| 관련 계약/계보/테스트 리포트 | 실제 동작과 문서 정합 |

## 구현 계약과 설계

| 위치 | 목적 |
|---|---|
| `contracts/` | OpenAPI 3.2.0-draft와 동기화 JSON Schema |
| `supabase/migrations/`, `supabase/tests/database/` | DB-001 timestamp 실행 권위와 pgTAP |
| `database/` | verified `0.4.0-local` 논리 projection, 역순 disposable-local 보상, absence proof; 실행 권위는 timestamp migration |
| `docs/test-reports/DB-001-LOCAL-BASELINE.md` | patched-only runtime의 fresh exact loopback·pgTAP 282·integration 8/8·cleanup local 검증 보고서 |
| `docs/handoffs/HANDOFF-20260717-DB-001-LOCAL-BASELINE.md` | 완료된 local/private DB 기준선의 재현·rollback/recovery와 별도 public-release blocker 인수인계 |
| `docs/handoffs/HANDOFF-20260720-FRONTEND-COLLABORATOR.md` | Frontend 전체 수직 흐름의 허용 경로·작업 순서·검증·자가 병합 인수인계 |
| `docs/03_ARCHITECTURE.md` | 시스템 경계와 장애 전략 |
| `docs/04_DOMAIN_AND_STATE_MODEL.md` | enum·상태·불변조건 |
| `docs/05_API_AND_CONTRACTS.md` | API 관리 규칙 |
| `docs/07_SECURITY_PRIVACY.md` | 구현 보안 기준 |
| `docs/08_TEST_STRATEGY.md` | 검증 전략 |
| `data/schemas/data-001/v1/approved-source-matrix.json` | DATA-001 canonical content·registry·출처·기관 공개 연락처·audit hash 신뢰 기준 |
| `docs/data-lineage/source-audits/` | 개인정보 없는 tracked 공식 출처 감사 요약 4개와 재현 근거 |

## source-of-truth와 legacy

| 위치 | 목적 |
|---|---|
| `docs/source-of-truth/` | 최종 확정 제품·RFP·정책 |
| `legacy/uploaded-project/` | 사용자가 올린 초기 프로젝트 원본(full package에만 포함) |
| `docs/02_CURRENT_REPO_AUDIT.md` | 초기 프로젝트와 최종 기준 충돌표 |

## 자동화 도구

| 파일 | 목적 |
|---|---|
| `scripts/new_implementation_note.py` | 노트와 INDEX 생성 |
| `scripts/capture_repo_state.py` | Git/버전 상태 캡처 |
| `scripts/check_scope_drift.py` | 오래된 범위의 활성 복귀 탐지 |
| `scripts/validate_codex_package.py` | 필수 파일과 지침 검증 |
| `scripts/check_git_history_secrets.py` | 모든 reachable Git object의 값 비노출 secret/actual-question 검사; local 통합·독립 review·fresh pre-push PASS 완료 |
| `scripts/check_secret_patterns.ps1` | 현재 repository 또는 `-RepositoryRoot` candidate의 tracked/untracked nonignored regular file 값 비노출 검사 |
| `scripts/check_collaboration_scope.py` | full base/head SHA·PR author·configured Frontend login으로 self-merge/owner-review JSON 분류 |
| `scripts/check_collaboration_note_append.py` | scope classifier 내부에서 신규 web 구현 노트와 INDEX 마지막 한 행의 add-only diff 검증 |
| `scripts/check_repository_docs.py` | tracked active Markdown local target·strict JSON을 Git blob 기준으로 bounded 검증 |
| `.github/workflows/collaboration-policy.yml` | trusted-base scope/docs/secret/contract policy와 항상 보이는 summary; hosted 실행은 remote 생성 뒤 검증 |
| `.github/workflows/frontend-ci.yml` | read-only frozen frontend/contract/build/bundle/E2E gate와 항상 보이는 summary; Docker/DeepSeek/배포 없음 |
