# IMP-20260724-008 — Q PM demo actual persistence and browser evidence

- Date/Time (KST): 2026-07-24T04:15:25+09:00
- Completion (KST): 2026-07-24T11:03:11+09:00
- Task ID: Q-PM-DEMO-001
- Type: implementation-test-data-security
- Status: Done — local/private actual evidence complete / human manual demo·accessibility·PR Pending
- Author/Agent: user decision owner, root coordinator, parallel implementation/review agents
- Branch: `codex/LLM-002-upstage-synthetic-evaluation`
- Base commit: `fcd0f0f`
- Related plan/ADR/RFP: D-058/D-059/D-068, ADR-0020/0021,
  [Q-PM plan](../superpowers/plans/2026-07-24-q-pm-demo-001-actual-evidence.md),
  [MVP plan](../superpowers/plans/2026-07-22-four-day-local-private-core-loop-mvp.md),
  RFP-P0-003/004/005/007/008/012

## 1. 사용자 요청과 완료 기준

### 요청

- 진행 중인 수직 흐름을 다시 시작하지 않고 병렬 에이전트로 계속한다.
- 실제 `/api/v1/chat` 정상·폴백, INSUFFICIENT_GROUNDING의 실제 DB 저장, 관리자
  조회·후보·별도 승인·20번째 ACTIVE, 동일 질문 SUCCESS, Frontend actual API 연동을 완성한다.
- Q-PM-DEMO-001=B에 따라 개인조회 시연과 승인 루프 질문을 분리한다.
- Critical 보안·새 production dependency 외에는 중간 승인 없이 집중 테스트→영역 테스트→최종
  전체 gate 순서로 진행한다.

### Acceptance Criteria

- PERSONAL_LOOKUP는 HTTP 200 FALLBACK, `intent=UNKNOWN`, reason `PERSONAL_LOOKUP`,
  `candidate_eligible=false`이고 `interaction_events`/`failed_questions` delta가 `0/0`이다.
- 별도 INSUFFICIENT_GROUNDING는 두 delta가 `1/1`이고 사유 확정→후보→self-approval 차단→
  `PM-LOCAL-001` 승인→20번째 ACTIVE를 거친다.
- 동일 질문 재질의는 SUCCESS이며 서버가 결합한 공개 `KB-WASTE-03` 출처명·URL을 반환한다.
- actual desktop browser가 Frontend→same-origin API→FastAPI→local DB→actual `/admin` 흐름을
  통과한다.
- final ACTIVE 20, target 1, `/ready=200`; 질문/UUID/DSN/secret을 backend evidence에 출력하지
  않고 provider/remote/public/new dependency 사용 0이다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 Q-PM option B와 기존 구현 승인을 제공했고 root가 공유 계약·DB 실행·통합을 소유했다. 에이전트가 runner/E2E/type fix를 구현하고 다른 에이전트가 독립 리뷰했다. 작성자는 `OPERATOR-LOCAL-001`, 승인자는 `PM-LOCAL-001`이다. |
| When — 언제 | 2026-07-24 KST, LLM offline Task 6 closeout 직후부터 final actual/browser/문서 closeout까지 수행했다. |
| Where — 어디서 | Windows local/private worktree, loopback patched Supabase, FastAPI `127.0.0.1`, Next actual admin mode, `scripts/`, `tools/web-e2e/`, active docs에서 수행했다. |
| What — 무엇을 | count-only actual runner, opt-in actual E2E, 정확한 public/internal identity assertion, strict test typing, actual 19→20 DB evidence와 인수인계 문서를 완성했다. |
| Why — 왜 | 개인조회 무저장과 개선 대상 질문 저장을 한 시연에서 혼동하지 않고, 시민 화면부터 별도 승인과 재질의 개선까지 실제로 증명하기 위해서다. |
| How — 어떻게 | TDD fake runtime→실제 repository count reader→clean seed actual runner→actual browser→read-only final probe→독립 리뷰→full gate 순서로 수행했다. |
| How much — 어느 정도 | backend 고정 PASS 15줄, actual browser 1/1, initial/final ACTIVE 19→20, event/failed delta 0/0과 1/1, target 1, new dependency/provider/network/remote/public 0이다. |

## 3. 시작 전 상태

- 관련 파일: `scripts/verify_actual_mvp_regression.py`, runner tests, chat/admin API와 repository,
  `apps/web/src/app/chat`, `apps/web/src/app/admin`, Playwright E2E, Q-MVP source-of-truth.
- 기존 동작: local core loop와 19→20 backend regression은 있었지만 PERSONAL_LOOKUP의 실제
  두-table 무저장 delta와 Frontend actual 전체 경로가 Q-PM option B 증거로 분리돼 있지 않았다.
- 발견한 충돌/부채: 개인조회와 근거 부족 질문을 같은 데모 질문으로 볼 위험, Next route
  announcer를 앱 오류로 보는 E2E 오탐, admin `activated_kb_id` 내부 UUID를 공개 KB ID로 오해한
  assertion, LLM tests 14건 strict Mypy 부채가 있었다.
- Git 상태: `fcd0f0f` 이후 runner/E2E/type-only commits를 쌓았고 기존 사용자/LLM 변경을
  보존했다. official `.2`, migration, contracts, package/lockfile는 건드리지 않았다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-PM-DEMO-001 | B / High | 개인조회 무저장과 승인 개선을 같은 질문으로 시연할지 | 사용자 B: #4 PERSONAL, #5 별도 INSUFFICIENT_GROUNDING | runner 순서, DB delta, demo story |
| A-045 | Resolved | option B actual 증거가 없음 | backend count delta와 browser flow를 분리해 PASS | ambiguity/SOT/plan |
| INTERNAL-ID | Internal | candidate ACTIVE 표시가 public ID인지 | OpenAPI의 UUID를 internal identity로 해석, public ID는 chat source에서 검증 | E2E assertion |
| HUMAN-MANUAL | Pending | 사람이 직접 하는 demo/a11y와 owner PR | 자동 evidence와 분리해 Pending 유지 | MVP Review 상태 |

## 5. 설계 결정과 대안

### 선택

- 기존 제품 정책과 공개 계약을 바꾸지 않고 test/evidence runner에 count-only snapshot을 추가했다.
- PERSONAL 직전/직후와 별도 INSUFFICIENT_GROUNDING 직전/직후를 각각 비교했다.
- actual browser는 environment opt-in 및 desktop 단일 실행으로 제한하고 network route mocking을
  금지했다.
- backend runner가 persistence delta를, browser가 actual UI/API workflow를 증명하도록 책임을
  분리했다.

### 이유

UI가 질문을 화면에 표시하는 사실과 DB 무저장을 혼동하지 않으며, state-changing 19→20 시나리오를
viewport마다 중복 실행하지 않기 위해서다. public ID는 시민 답변 source contract에 있고 admin
activation field는 internal UUID이므로 각 identity를 맞는 경계에서 검증해야 한다.

### 고려했지만 선택하지 않은 대안

- PERSONAL_LOOKUP 자체를 candidate로 승격: D-059와 개인정보 정책 위반이라 제외했다.
- 모든 DB table 무변화 주장: 실제 인수 기준은 `interaction_events`와 `failed_questions` 두 table
  이므로 과장이라 제외했다.
- E2E route intercept/mock: actual transport 증거가 아니므로 제외했다.
- candidate card에서 `KB-WASTE-03` literal 검증: OpenAPI UUID 계약과 충돌해 제거했다.
- 새 dependency/provider 연결: 승인 범위 밖이라 0으로 유지했다.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `scripts/verify_actual_mvp_regression.py` | count-only persistence reader, PERSONAL exact response/delta 0, 별도 IG delta 1과 기존 19→20 흐름 | backend actual 정책·저장 증거 |
| `scripts/tests/test_verify_actual_mvp_regression.py` | RED/GREEN fake runtime, fixed 15-line allowlist, failure/no-content cases | mutation 전 계약 고정 |
| `tools/web-e2e/e2e/actual-local-core-loop.spec.ts` | opt-in actual desktop 시민→관리자→재질의 E2E | Frontend actual integration 증거 |
| `apps/api/tests/llm/test_prompt.py`, `test_report.py`, `test_upstage.py` | exact fixture/callback annotation과 obsolete ignore 제거 | root strict Mypy 복구, product behavior 불변 |
| `apps/api/tests/llm/test_fixtures.py` | `__file__` 기준 repository root에서 canonical CSV를 찾도록 교정 | `uv --directory apps/api` cwd와 무관한 API full gate |
| decision/SOT/MVP/Q-PM docs | D-068/A-045, 책임 분리, actual PASS, internal/public identity, manual Pending | 단일 기준 동기화 |
| `scripts/README.md`, lineage, `TASKS.md`, `CHANGELOG.md`, manifest | runner 재현·rollback·실제 결과·버전 | 새 개발자 인수인계 |

### 데이터 흐름/상태 변화

```text
clean immutable .2 projection ACTIVE 19
  -> PERSONAL_LOOKUP FALLBACK
     -> interaction_events +0 / failed_questions +0
  -> separate INSUFFICIENT_GROUNDING FALLBACK
     -> interaction_events +1 / failed_questions +1
  -> reason confirmed -> candidate created/submitted
  -> same writer blocked -> PM-LOCAL-001 approved
  -> runtime ACTIVE 20, target exactly once
  -> same question SUCCESS + server-bound official source
```

backend actual stdout은 다음 15줄로 제한됐다.

```text
PASS ready
PASS initial-active count=19
PASS personal-lookup persistence event_delta=0 failed_delta=0
PASS initial-fallback
PASS business-replay
PASS insufficient-grounding event_delta=1 failed_delta=1
PASS failed-new count=1
PASS reason-confirmed
PASS candidate-created
PASS candidate-submitted
PASS self-approval-blocked
PASS candidate-approved
PASS improved-requery public_id=KB-WASTE-03
PASS old-replay
PASS final-active total=20 categories=4 count_each=5
```

### 오류·빈 상태·롤백

- 첫 local reset wrapper는 정상 Supabase stderr를 PowerShell terminating error로 해석해 seed 전에
  중단됐다. native exit code를 직접 판정하는 방식으로 재실행해 PASS했다.
- 첫 browser run은 Next route announcer가 app `<main>` 밖의 `role=alert`라서 오탐했다. app
  main으로 범위를 제한해 실제 admin error panel 검출은 유지했다.
- 두 번째 browser run은 승인까지 성공한 뒤 candidate internal UUID에 public literal을 기대해
  실패했다. contract를 확인하고 그 한 assertion만 제거했으며 최종 chat public source 검증은 유지했다.
- final clean 19에서 세 번째 browser run 1/1이 PASS했고 DB는 intentional final20이다.
- 첫 root gate는 worktree에 Git-ignored patched Supabase binary가 없어 root test 2건이 실패했다.
  tracked manifest와 SHA-256이 같은 main workspace binary를 worktree `.tools`에 복구한 뒤 PASS했다.
- 다음 root gate는 strict Mypy 14건을 발견해 test-only exact annotation commit `8e5bee5`로
  보정했다. 이후 API full test는 cwd-relative canonical CSV 때문에 4건만 실패했고, `2d95538`이
  test file 위치에서 repository root를 계산하도록 보정했다. direct API full은 1,782 PASS였다.
- rollback은 disposable local `db reset --local`→immutable `.2` `seed-cycle`→local login 회전이다.
  `.1`/`.2` bytes나 migration을 되돌리거나 삭제하지 않는다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | `0.7.0-local-synthetic-evaluator` | 동일 | product runtime behavior 불변 |
| Web | `0.4.0-chat-admin-local-integration` | 동일 | opt-in E2E만 추가 |
| API | `3.1.0-draft` | 동일 | 공개 wire contract 불변 |
| Shared contracts | `0.4.0` | 동일 | OpenAPI/generated diff 0 |
| DB schema | `0.4.0-local` | 동일 | migration/rollback 불변 |
| Official data | `0.1.0-initial.2` | 동일 | immutable release 불변, 20번째는 runtime lineage |
| Mock data | `0.0.0-not-populated` | 동일 | mock 미사용 |
| Prompt set | `0.1.0-upstage-solar-pro3-synthetic` | 동일 | provider actual 0 |
| Test suite | `1.3.0-upstage-synthetic-evaluator` | `1.4.0-q-pm-actual-evidence` | actual runner/browser evidence |
| Docs | `2.14.0` | `2.15.0` | Q-PM closeout와 재현 문서 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| runner focused tests | PASS | 24 tests | terminal / commits `a18fa1c`~`e65900a` |
| chat/admin/runner area pytest | PASS | 235 passed, warning 1 | terminal |
| Ruff runner/API focused | PASS | 28 files | terminal |
| backend actual runner | PASS | fixed 15 lines, 19→20 | Q-PM plan / terminal |
| opt-in Playwright actual desktop | PASS | 1/1, 9.6s | commit `d3eed0d` / terminal |
| final read-only DB/ready probe | PASS | ACTIVE 20, target 1, ready 200 | terminal |
| LLM strict typing remediation | PASS | LLM 141; Mypy 87 files; review no findings | commit `8e5bee5` |
| canonical fixture path remediation | PASS | root/apps-api cwd 4/4; LLM 141; review no findings | commit `2d95538` |
| independent runner/E2E reviews | PASS | no findings after fixes | agent review messages |
| `scripts/check_repository_docs.py`, `git diff --check` | PASS before closeout | structural docs/diff | terminal |
| API full after final path fix | PASS | 1,782 passed, 8 approved DB-only skips, warning 1, subtests 5 | terminal |
| root `verify.ps1 -Offline` | PASS | root/data/Web/API/contracts/scanners/package/diff complete | terminal |

### 미실행 검증과 이유

- Upstage actual/model-quality Task 7: 별도 local human gate이며 이 시나리오는 provider-off다.
- 100-user, automatic backup, public deployment, public admin auth/RBAC, `00700`: MVP 이후 deferred다.
- remote DB와 실제 시민/free-input provider: 명시적 금지 범위다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: PERSONAL 무저장은 정확히 `interaction_events`/`failed_questions` delta 0이다. 별도 IG만
  masked failed row를 만든다. backend evidence에 질문/UUID/DSN/secret을 출력하지 않았다.
- Security: 작성자≠승인자, ACTIVE-only, official source server binding, mock approval 차단,
  provider/public/remote 0을 유지했다. process-only admin DSN/context secret은 출력하지 않았다.
- Accessibility: actual browser가 semantic roles와 실제 admin/chat path를 통과했지만 사람의 키보드,
  screen reader, 대비 수동 검수는 Pending이다.
- Performance/cost: browser actual 1회와 local DB만 사용했다. provider 비용 0이며 100-user 보증은 없다.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `0.1.0-initial.2` 19개를 seed로 사용했고 파일·승인 metadata를 변경하지
  않았다. PM-approved withheld `KB-WASTE-03`만 governed runtime candidate로 ACTIVE가 됐다.
- mock/AI 생성: mock 0. 고정 질문은 테스트용 비식별 fixture이며 공식 사실이 아니다.
- schema/lineage: DB schema/migration 불변. runtime 19→20을
  `MVP-001-KB-WASTE-03-LOCAL-WORKFLOW.md`에 append-only 기록했다.
- verified date: source의 기존 PM-approved 확인일을 서버 metadata에서 사용했고 LLM이 생성하지 않았다.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- local/private 자동 actual evidence는 완료됐지만 public 운영 준비나 실제 인증/RBAC가 아니다.
- 사용자는 사람이 직접 하는 데모와 390/430/desktop 키보드·screen reader·대비 검수, owner branch
  리뷰/PR/merge를 별도로 수행해야 한다.
- Upstage 실제 합성 호출은 아직 0이며 Task 7의 key/network/model-quality/cost gate가 별도다.
- final local DB는 데모 편의를 위해 ACTIVE 20을 유지한다. 다시 runner/E2E를 실행하기 전에는
  반드시 disposable reset+`.2` seed로 19를 복구해야 한다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- count reader는 두 fixed aggregate query의 정수만 반환하고 content를 runner로 가져오지 않는다.
- E2E는 desktop에서만 state-changing test를 실행하고 mobile projects는 skip한다.
- `activated_kb_id`는 generated/OpenAPI UUID이며 public ID 검증을 chat source로 이동했다.
- test-only Mypy annotation은 pytest fixture와 HTTPX callback의 실제 callable type을 좁혔고 config를
  완화하거나 broad `Any`를 추가하지 않았다.

## 13. 인수인계·재현·롤백

### 재현

1. Docker Desktop과 patched loopback Supabase가 local/private로만 실행 중인지 확인한다.
2. disposable DB를 reset하고 immutable `.2` `seed-cycle`/`verify-final`로 exact 19/3/10을 만든다.
3. `provision_local_database_login.py`로 ignored `.env`의 DATABASE_URL만 회전한다.
4. process-only context/admin secret을 준비하고 `verify_actual_mvp_regression.py`를 정확히 한 번 실행해
   고정 15줄을 확인한다.
5. browser evidence가 필요하면 다시 clean19로 reset한 뒤 `scripts/README.md`의
   `Opt-in actual desktop browser` 명령대로 process-only context secret, local API,
   `ADMIN_UI_ENABLED=true`, `ADMIN_UI_MODE=actual`,
   `API_INTERNAL_BASE_URL=http://127.0.0.1:8000`, `SEJONG_ACTUAL_LOCAL_E2E=true`를 설정하고
   Web build와 desktop spec을 한 번 실행한다.
6. final read-only probe로 ACTIVE 20, target 1, `/ready=200`을 확인하고 서버를 종료한다.

### 롤백

- runtime demo row rollback은 disposable reset+immutable `.2` seed다.
- 코드 rollback은 commits `a18fa1c`~`2d95538`을 역순 revert하되 migration/data release를 수정하지 않는다.
- docs rollback은 D-068 결정 기록을 삭제하지 않고 새 superseding decision/note로 보정한다.

### 다음 개발자 시작점

- `scripts/README.md`의 Q-PM runner와 Q-PM plan 안전 중단 조건을 먼저 읽는다.
- final20 DB에서 runner를 재실행하지 않는다.
- provider actual은 LLM-002 Task 7, public auth/deploy는 별도 계획으로 진행한다.

## 14. 남은 위험·미해결 질문·다음 단계

- 인간 manual demo/accessibility와 owner PR review/merge.
- Upstage actual 합성 품질·strict JSON·비용 증거.
- public admin authentication/RBAC, `00700`, remote/public deploy, backup/100-user 성능.
- browser failure trace는 Git-ignored local artifact다. 실제 PII를 사용하지 않았고 필요 시 안전하게
  local test-results를 정리한다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 최종 전체 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] backend evidence 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
