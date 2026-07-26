# IMP-20260726-010 — OFFICE API 설계 승인과 written specification

- Date/Time (KST): 2026-07-26T14:55:41+09:00
- Task ID: OFFICE-API-001-SPEC
- Type: decision-design-spec
- Status: Decision-only Done / Written specification Review
- Author/Agent: repository owner / Codex
- Branch: codex/OFFICE-API-001-design
- Base commit: 8ebc66b
- Related plan/ADR/RFP: D-078, ADR-0009/0011, SFR-004, OFFICE-API-001

## 1. 사용자 요청과 완료 기준

### 요청

- `Q-API-OFFICES-001=A / 설계 승인`을 반영한다.
- PR #14 병합을 확인하고 최신 `origin/main`에서 다음 작업을 계속한다.

### Acceptance Criteria

- PR #14의 실제 merge SHA를 확인한다.
- 최신 main 기반의 isolated worktree에서 작업한다.
- 기존 OpenAPI·DB function·repository와 runtime gap을 대조한다.
- 승인된 A안을 모호함 없는 written specification으로 작성하고 자체 리뷰한다.
- decision log, ambiguity register, TASKS, version, 구현 노트를 동기화한다.
- 제품 코드·공개 계약·DB·data·Web·LLM·dependency는 명세 검토 승인 전 변경하지 않는다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | repository owner가 설계를 승인하고 Codex가 명세·기준선·문서 정합을 담당한다. |
| When — 언제 | 2026-07-26 14:48~15:05 KST |
| Where — 어디서 | private Sejong_AI, linked worktree `.worktrees/office-api-001-design` |
| What — 무엇을 | existing offices endpoint 존치·runtime 구현 설계를 서면 계약으로 고정한다. |
| Why — 왜 | tracked OpenAPI/DB에는 endpoint가 있지만 FastAPI가 404를 반환하는 drift를 제거하기 위해서다. |
| How — 어떻게 | active authority 검토, A/B/C 비교의 A 승인 반영, fail-closed architecture와 TDD 인수 기준 문서화 |
| How much — 어느 정도 | spec 1개, 결정 1개, ambiguity 1개 해결, 제품/DB/data/provider mutation 0 |

## 3. 시작 전 상태

- 관련 파일: `contracts/openapi-v1.yaml`, `apps/api/src/sejong_ai_api/main.py`,
  `apps/api/src/sejong_ai_api/local.py`, repository adapter, `app_api.list_offices`
- 기존 동작:
  - OpenAPI는 required region+intent와 200 items를 선언한다.
  - DB function은 OFFICIAL-only와 public-id order, valid empty를 구현한다.
  - FastAPI에는 router가 없어 default/local에서 404다.
- 발견한 충돌/부채: runtime contract parity 부재. standalone endpoint는 current Web 미사용이다.
- Git 상태: PR #14 merge SHA `8ebc66b`, 새 branch/worktree는 해당 `origin/main`에서 clean 시작했다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-051/Q-API-OFFICES-001 | B / High | endpoint 존치 또는 제거 | A 존치·runtime 구현 | API router, contract error response, tests |
| 기존 query/empty 동작 | Resolved by authority | required/enum/empty/OFFICIAL/order | OpenAPI·DB function을 그대로 사용 | 새 인간 질문 없음 |
| public/remote exposure | Out of scope | local/private 이후 공개 여부 | 계속 금지 | 배포/CORS/auth 불변 |

## 5. 설계 결정과 대안

### 선택

- route를 default/local FastAPI에 항상 등록한다.
- default는 closed dependency로 503, local은 existing repository+readiness를 주입한다.
- valid no-match는 200 empty, DB/readiness 불능은 ADR-0009 safe 503이다.
- DB function, migration, seed는 변경하지 않는다.

### 이유

- existing public draft와 DB capability를 가장 작은 변경으로 정렬한다.
- default app에서 route/OpenAPI를 숨기지 않으면서 실제 dependency가 없을 때 false empty를
  반환하지 않는다.
- source와 office metadata는 서버 소유 record만 사용한다.

### 고려했지만 선택하지 않은 대안

- contract 제거: 생성 타입과 SFR-004 확장성을 줄여 기각했다.
- 선언만 유지: 404 contract drift라 기각했다.
- dependency 없음에 200 empty: 장애와 정상 no-match를 혼동시켜 기각했다.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| OFFICE API written spec | architecture, wire, error, tests, version, rollback | implementation authority |
| DECISION_LOG | D-078 추가 | 인간 결정 추적 |
| ambiguity register | A-051 Resolved | 미결정 제거 |
| TASKS | Design Approved / spec Review | 현재 상태 정합 |
| version docs/manifest | docs 2.20.5→2.20.6 | written spec snapshot |
| 이 노트와 INDEX | 명령·증거·인수인계 | 재현 |

### 데이터 흐름/상태 변화

- 이번 단계의 runtime/data 흐름 변화 없음.
- 구현 목표 흐름은 typed query→readiness→existing repository/DB function→server-owned Office다.

### 오류·빈 상태·롤백

- 명세 변경은 이 branch commit revert로 되돌린다.
- product code/DB/data가 없으므로 runtime/data rollback은 없다.
- pnpm setup이 자동 추가한 `sharp` placeholder 한 줄은 즉시 원상복구해 dependency 정책에
  포함하지 않았다.

## 7. 버전 전후

### 생성 시 매니페스트

- product_spec: 2.5.0
- repo_guidance: 1.7.8
- application: 0.9.1-grounded-local-chat-evidence
- web: 0.6.0-answer-mode
- api: 3.2.0-draft
- shared_contracts: 0.5.0
- database_schema: 0.4.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.2.0-grounded-live-chat
- test_suite: 1.6.1-grounded-actual
- documentation: 2.20.5

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.9.1-grounded-local-chat-evidence | same | 제품 구현 전 |
| Web | 0.6.0-answer-mode | same | Web scope 아님 |
| API | 3.2.0-draft | same | 구현 전; 목표 3.3.0-draft |
| Shared contracts | 0.5.0 | same | 구현 전; 목표 0.6.0 |
| DB schema | 0.4.0-local | same | migration 없음 |
| Official data | 0.1.0-initial.2 | same | seed/data 없음 |
| Mock data | 0.0.0-not-populated | same | mock 없음 |
| Prompt set | 0.2.0-grounded-live-chat | same | LLM 없음 |
| Test suite | 1.6.1-grounded-actual | same | 테스트 코드 구현 전 |
| Docs | 2.20.5 | 2.20.6 | design approval와 written spec |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| `gh pr view 14 ...`, `git fetch origin main` | PASS; merged `8ebc66b` | 1회 | terminal evidence |
| `git worktree add ... origin/main` | PASS; new clean branch | 1개 | linked worktree |
| `node --version`, `corepack pnpm --version` | PASS; v24.12.0, 11.13.0 | 1회 | terminal evidence |
| pinned venv Python/package check | PASS; Python 3.12.13, FastAPI 0.139.0, Pydantic 2.13.4, pytest 9.1.1 | 1회 | adjacent verified venv |
| `node packages/shared-contracts/scripts/generate-api.mjs --check` | PASS | baseline 1회 | terminal evidence |
| pinned Python `-m pytest -q` in `apps/api` | PASS; 2023 passed, 8 local DB skipped, 5 subtests | 22.43s | terminal evidence |
| `python -B scripts/check_repository_docs.py` | PASS | final 1회 | terminal evidence |
| secret pattern scan | PASS | final 1회 | terminal evidence |
| manifest JSON, placeholder, link/diff checks | PASS | final 1회 | terminal evidence |

### 미실행 검증과 이유

- actual local DB endpoint smoke: 제품 route가 아직 없어 구현 closeout에서 수행한다.
- Web tests/build: Web 변경 없음.
- `uv sync --frozen`: current shell에 uv가 없어 미실행했다. verified adjacent pinned venv의 exact
  package set으로 API baseline을 대체했다.
- `corepack pnpm install --frozen-lockfile`: 기존 `allowBuilds` placeholder 때문에
  `ERR_PNPM_IGNORED_BUILDS`로 중단됐다. lock/dependency를 바꾸지 않고 direct contract check로
  대체했다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문 text·PII·event/failed row 접근·저장 0
- Security: secret/DSN/provider 출력·사용 0; future route는 value-free 422/503
- Accessibility: UI 변경 없음
- Performance/cost: 외부 호출 0, 비용 0; future DB read는 existing indexed function

## 10. 데이터와 출처 영향

- 공식 데이터: 변경 없음; future endpoint도 OFFICIAL-only DB function 사용
- mock/AI 생성: 변경 없음
- schema/lineage: migration·seed 변경 없음
- verified date: 공식 record 자체를 재검수하지 않은 설계 단계

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- Q-API-OFFICES-001=A는 endpoint 존치·runtime 구현 설계 승인이다.
- written spec에는 unavailable 503과 API draft 3.3 minor 계획이 포함된다.
- 지금은 제품 코드가 없으며 사용자가 written specification을 검토·승인해야 실행계획을 작성한다.
- public/remote/실제 기관 운영·자동 merge는 승인되지 않았다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- module/helper 분리, dependency override, fixture naming은 spec의 wire와 안전 경계를 지키는
  범위에서 계획 단계에 상세화한다.

## 13. 인수인계·재현·롤백

### 재현

1. `git fetch origin main`
2. source commit이 `8ebc66b`인지 확인한다.
3. written spec, D-078, A-051, TASKS, manifest와 INDEX를 함께 읽는다.
4. pinned Python으로 API baseline `2023 passed, 8 skipped`를 재현한다.

### 롤백

- 이 spec commit을 revert한다. DB/runtime/data 변화는 없다.

### 다음 개발자 시작점

- 사용자의 `명세 승인`을 받은 뒤 `superpowers:writing-plans`로 exact TDD 실행계획을 작성한다.
- 계획 전에는 contracts/API product files를 수정하지 않는다.

## 14. 남은 위험·미해결 질문·다음 단계

- written specification 사용자 review Pending
- plan approval와 product implementation Pending
- actual DB smoke는 implementation closeout Pending
- `/api/v1/admin/quality-summary`, clean KPI, hosted backend CI, public deploy는 별도 backlog

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
