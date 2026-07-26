# IMP-20260726-009 — 상태 문서 Draft PR 게시와 OFFICE API 설계 진입

- Date/Time (KST): 2026-07-26T14:37:34+09:00
- Task ID: STATUS-PUBLISH-OFFICE-API
- Type: git-design-gate
- Status: Done
- Author/Agent: repository owner / Codex
- Branch: codex/LLM-003-metadata-explanation
- Base commit: 4d3317c
- Related plan/ADR/RFP: `docs/handoffs/HANDOFF-20260726-CURRENT-MVP-STATUS.md`, `TASKS.md`, PR #14

## 1. 사용자 요청과 완료 기준

### 요청

- 현재 완료 상태에서 멈추거나 다시 시작하지 말고 다음 작업을 계속한다.
- 먼저 이미 검증된 결정·상태 문서 branch를 Draft PR로 게시한다.
- 이어서 다음 P1 후보인 OFFICE API 계약/runtime 정합 작업을 설계 단계로 진입한다.

### Acceptance Criteria

- 현재 branch의 실제 변경 범위를 확인하고 문서 전용인지 검증한다.
- secret scan, 문서 검사, manifest JSON 검사, diff whitespace 검사를 통과한다.
- `main`에 직접 push하거나 자동 merge하지 않고 Draft PR만 만든다.
- OFFICE API는 공개 계약 선택을 인간이 승인하기 전 제품 코드를 변경하지 않는다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | repository owner가 계속 진행을 승인하고 Codex가 범위 검증·게시·설계 진입을 수행한다. |
| When — 언제 | 2026-07-26 14:37~14:45 KST |
| Where — 어디서 | isolated linked worktree, private `tskwak111/Sejong_AI`, Draft PR #14 |
| What — 무엇을 | metadata 유지 결정, current MVP handoff와 상태 문서를 Draft PR로 게시하고 OFFICE API 설계 gate를 연다. |
| Why — 왜 | 이미 끝난 LLM actual slice와 다음 기능을 분리하고, 현재 local 통계를 잘못된 평가 KPI로 쓰지 않도록 하기 위해서다. |
| How — 어떻게 | Git 범위 확인, 문서·secret·JSON·diff 검사, branch push, Draft PR 생성, 공개 계약 변경 전 설계 승인 gate 유지 |
| How much — 어느 정도 | 제품/API/DB/data/provider mutation 0, dependency 0, Draft PR 1개 |

## 3. 시작 전 상태

- 관련 파일: `TASKS.md`, current handoff, source-of-truth/decision/version 문서,
  implementation notes 006~008
- 기존 동작: `origin/main=be7387f`; local branch는 문서 commit 3개가 앞선 상태였다.
- 발견한 충돌/부채: tracked OpenAPI의 `/api/v1/offices`가 current FastAPI runtime에 없지만,
  이 branch는 해당 제품 gap을 구현하지 않는다.
- Git 상태: `codex/LLM-003-metadata-explanation`, 제품 코드 변경 없이 문서 변경만 존재했다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-API-OFFICES-001 | High | existing standalone office endpoint를 존치·구현할지 계약에서 제거할지 | 존치·구현을 추천하고 인간 승인 전 제품 코드는 바꾸지 않는다. | OpenAPI, API runtime, repository adapter, API tests |
| Q-DB-CLEANUP-001 | Resolved | 오표시 metadata 22행 처리 | A 유지, 현재 local event 수치는 평가 KPI에서 제외 | local evidence와 향후 clean benchmark |

## 5. 설계 결정과 대안

### 선택

- 이번 branch는 문서/status 전용 Draft PR로 닫는다.
- OFFICE API 구현은 다음 branch에서 설계 승인→written spec→계획→TDD 순서로 분리한다.

### 이유

- 이미 병합된 LLM actual 기능과 다음 API 기능을 한 PR에 섞지 않는다.
- `/api/v1/offices`의 required `region`·`intent`, enum, `items: []`, OFFICIAL-only와
  public-id 정렬은 active OpenAPI와 DB read function에 이미 확정돼 있다. 남은 제품 결정은
  이 endpoint의 존치·runtime 구현 여부다.

### 고려했지만 선택하지 않은 대안

- 현재 branch에 OFFICE API 코드를 함께 추가: 리뷰 범위와 rollback 경계가 섞여 제외했다.
- 현재 local event metadata를 즉시 삭제/reset: Q-DB-CLEANUP-001=A와 충돌하므로 제외했다.
- Draft PR 자동 merge: 저장소 협업 정책상 금지했다.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| GitHub PR #14 | current docs/status commit을 Draft PR로 게시 | 인간 review/merge boundary 유지 |
| 이 구현 노트와 INDEX | 요청·검증·게시·다음 설계 gate 기록 | 재현과 인수인계 |
| version docs/manifest | documentation `2.20.4→2.20.5` | 문서 snapshot 식별 |

### 데이터 흐름/상태 변화

- 애플리케이션·DB·provider 데이터 흐름 변화 없음.
- 원문 질문, 답변, event row, secret를 읽거나 쓰지 않았다.

### 오류·빈 상태·롤백

- push/PR 생성 실패 시 branch를 보존하고 `main`을 변경하지 않는 것이 기본 rollback이다.
- PR을 취소하려면 PR #14를 merge하지 않고 close한다. 원격 branch 삭제는 인간 확인 후 수행한다.

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
- documentation: 2.20.4

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.9.1-grounded-local-chat-evidence | same | 제품 변경 없음 |
| Web | 0.6.0-answer-mode | same | Web 변경 없음 |
| API | 3.2.0-draft | same | API 변경 없음 |
| DB schema | 0.4.0-local | same | migration/actual DB 변경 없음 |
| Official data | 0.1.0-initial.2 | same | seed/data 변경 없음 |
| Mock data | 0.0.0-not-populated | same | mock 변경 없음 |
| Prompt set | 0.2.0-grounded-live-chat | same | provider/prompt 변경 없음 |
| Test suite | 1.6.1-grounded-actual | same | 테스트 코드 변경 없음 |
| Docs | 2.20.4 | 2.20.5 | 게시·설계 gate 구현 노트 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| `git status -sb`, `git diff --name-status origin/main...HEAD` | PASS; 게시 전 committed scope는 문서 13개 | 1회 | terminal evidence |
| `gh auth status`, `gh repo view` | PASS; `tskwak111/Sejong_AI`, default `main` | 1회 | terminal evidence |
| `python -B scripts/check_repository_docs.py` | PASS | 최종 1회 | terminal evidence |
| `powershell.exe ... scripts/check_secret_patterns.ps1` | PASS | 최종 1회 | terminal evidence |
| `python -m json.tool versions/manifest.json` | PASS | 최종 1회 | terminal evidence |
| `git diff --check origin/main...HEAD` | PASS | 최종 1회 | terminal evidence |
| `git push -u origin codex/LLM-003-metadata-explanation` | PASS | branch 1개 | origin branch |
| `gh pr create --draft ...` | PASS | Draft PR 1개 | https://github.com/tskwak111/Sejong_AI/pull/14 |

### 미실행 검증과 이유

- API/Web/DB 전체 테스트·빌드: 제품 코드, 계약, DB, dependency를 바꾸지 않은 문서-only 게시라
  실행하지 않았다. OFFICE API 구현 수직 흐름에서 해당 영역 검증을 수행한다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문 원문·PII·event row 접근 및 저장 0
- Security: secret/provider/DSN 출력·변경 0; secret pattern scan 수행
- Accessibility: UI 동작 변경 없음
- Performance/cost: runtime 호출과 외부 LLM 호출 0, 비용 0

## 10. 데이터와 출처 영향

- 공식 데이터: 변경 없음
- mock/AI 생성: 변경 없음
- schema/lineage: 변경 없음
- verified date: 이 작업은 공식 데이터 재검증 작업이 아니다.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- PR #14는 Draft이며 사람이 리뷰·merge해야 한다. Codex는 자동 merge하지 않는다.
- 다음 OFFICE API는 기존 계약을 존치·runtime에 구현할지, 미사용 endpoint를 계약에서
  제거할지 선택해야 하므로 `Q-API-OFFICES-001` 승인 전 제품 코드를 작성하지 않는다.
- current local DB event 통계는 계속 평가 KPI로 사용하지 않는다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- branch upstream 설정, Markdown/JSON/whitespace 검사, PR body 작성은 같은 승인 범위 안의
  내부 Git/documentation 처리다.

## 13. 인수인계·재현·롤백

### 재현

- `git fetch origin`
- `git diff --name-status origin/main...origin/codex/LLM-003-metadata-explanation`
- PR #14의 Files changed와 checks를 확인한다.

### 롤백

- PR #14를 merge하지 않고 close한다. `main`에는 자동 변경이 없다.

### 다음 개발자 시작점

- PR #14와 current MVP handoff를 검토한다.
- `Q-API-OFFICES-001`이 승인되면 최신 `origin/main`에서 새 `codex/` branch/worktree를 만들고
  written spec과 TDD 계획부터 시작한다.

## 14. 남은 위험·미해결 질문·다음 단계

- OFFICE API의 required query와 empty list semantics는 existing contract에 확정돼 있다.
  endpoint 존치·runtime 구현 여부만 `Q-API-OFFICES-001`로 남아 있다.
- `/api/v1/admin/quality-summary`, clean KPI reset, hosted backend CI, public deploy는 이 작업
  승인 범위 밖이며 계속 Pending이다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
