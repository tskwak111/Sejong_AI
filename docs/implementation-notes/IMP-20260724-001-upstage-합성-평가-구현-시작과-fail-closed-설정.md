# IMP-20260724-001 — Upstage 합성 평가 구현 시작과 fail-closed 설정

- Date/Time (KST): 2026-07-24T00:02:05+09:00
- Task ID: LLM-002
- Type: implementation
- Status: Done — Task 1 / LLM-002 In Progress
- Author/Agent: 사용자(계획 승인), Codex(통합·보안 판정), Task 1 구현/리뷰 subagents
- Branch: codex/LLM-002-upstage-synthetic-evaluation
- Base commit: 9a5e6f5
- Related plan/ADR/RFP:
  - [승인 실행계획](../superpowers/plans/2026-07-23-upstage-solar-pro3-synthetic-evaluation.md)
  - [승인 명세](../superpowers/specs/2026-07-23-upstage-solar-pro3-synthetic-evaluation-design.md)
  - [ADR-0022](../adr/0022-upstage-solar-pro3-synthetic-evaluation.md)
  - [D-065~D-067](../decisions/DECISION_LOG.md)
  - [TASKS LLM-002](../../TASKS.md)

## 1. 사용자 요청과 완료 기준

### 요청

사용자의 연속 `계속 ㄱㄱ` 지시를 승인된 LLM-002 실행계획의 구현 승인으로 반영하고, 사람이
수행해야 할 actual key/call을 제외한 offline 구현을 중단 없이 계속한다.

### Acceptance Criteria

- 실행 승인과 actual 시민/공개 금지 경계를 결정 로그·source-of-truth에 기록한다.
- Task 1을 RED→GREEN으로 구현하고 독립 spec/quality 리뷰까지 통과한다.
- exact Upstage profile만 enable하고 malformed/non-string/disabled 상태는 예외 없이 닫는다.
- API key는 repr/log에 없고 `.env.example`은 disabled 기본이다.
- public chat/API/DB/data/dependency/lockfile/key/network 변화·사용은 0이다.
- focused pytest·Ruff·Mypy와 repository docs/secret/diff 검사를 통과한다.
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 계획 실행을 승인했고, 구현 subagent가 TDD, reviewer가 spec+quality, Codex가 보안·통합 판정을 담당했다. |
| When — 언제 | 2026-07-23~24 KST, plan commit `9a5e6f5` 뒤 Task 1 checkpoint |
| Where — 어디서 | isolated linked worktree, `apps/api/.env.example`, 새 internal `sejong_ai_api.llm.settings`, tests와 거버넌스 문서 |
| What — 무엇을 | exact Upstage synthetic settings loader, disabled example, malformed/non-string fail-closed, D-067 |
| Why — 왜 | provider 호출 전에 enable 조건과 비용 상한을 값/타입 수준에서 닫아 실제 시민·오설정 연결을 차단하기 위해 |
| How — 어떻게 | SDD+TDD, focused tests, independent diff review, Important finding fix/re-review, main verification |
| How much — 어느 정도 | product 3개/테스트 2개/example 1개, 구현+fix 2 commits, focused 6 tests; key/network/DB/data/dependency 0 |

## 3. 시작 전 상태

- 관련 파일: `apps/api/.env.example`, `apps/api/src/sejong_ai_api/llm/`,
  `apps/api/tests/llm/`, LLM-002 design/plan/ADR, actual chat/app factory 경계
- 기존 동작: external provider adapter/package가 없고 deterministic local chat은 provider-free였다.
  `.env.example`에는 구현되지 않은 DeepSeek 선택 값이 남아 있었으며 provider는 연결되지 않았다.
- 발견한 충돌/부채:
  - linked worktree에는 ignored `.\.tools\uv`가 없어 첫 baseline 명령이
    `CommandNotFoundException`으로 실패했다. Git common-dir에서 원본 project-local uv를
    찾는 다운로드 없는 bootstrap으로 계획을 교정했다.
  - 첫 구현은 malformed allowlisted dotenv key를 valid process override와 함께 무시할 수 있었다.
    독립 reviewer가 Important로 발견했고 별도 RED/GREEN fix로 닫았다.
  - runtime Mapping에 비문자 값이 오면 `AttributeError`가 날 수 있음을 controller가 발견해 같은
    fix wave에서 `None` fail-closed로 보정했다.
- Git 상태: 시작 `9a5e6f5` clean, 구현 `9318f7f`, fix `4bdc68d`, task re-review Approved.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| PLAN-APPROVAL | 인간 | 연속 continue가 실행 승인인가 | D-067: 명시적 진행과 동등한 승인 | product implementation 시작 |
| TOOL-PATH | 내부 | linked worktree에서 ignored uv 위치 | Git common-dir parent의 `.tools/uv/uv.exe`, 없으면 bounded error | 재현 가능한 offline tests |
| DOTENV-MALFORMED | 보안 | override가 있어도 malformed allowlisted line을 거부할지 | 항상 `None`; unrelated app keys만 무시 | fail-closed enable gate |
| ACTUAL-GATE | 인간 | key/actual call 시점 | Tasks 1~6 뒤 local human gate | 현재 key/network 0 |

## 5. 설계 결정과 대안

### 선택

- exact provider/model/base/timeout/retry/concurrency/input/output/attempt/synthetic-mode 11개를 모두
  만족할 때만 immutable settings를 반환한다.
- process mapping이 우선이고 dotenv는 결손을 채우되, 파일 안 malformed allowlisted assignment는
  override 여부와 무관하게 전체 profile을 닫는다.
- secret field는 dataclass repr에서 제외하고 loader는 값/오류를 logging하지 않는다.

### 이유

부분 설정이나 오래된 DeepSeek 값, URL 변형, unicode numeral, whitespace/quote, duplicate/malformed
dotenv, runtime type violation이 provider enable로 이어지지 않게 한다.

### 고려했지만 선택하지 않은 대안

- generic provider/URL/model: 현재 승인 범위를 넓히므로 제외.
- SDK/새 dotenv dependency: 기존 표준 라이브러리로 충분하고 새 production dependency 금지.
- malformed 줄 무시: override와 결합하면 fail-open 가능하므로 제외.
- public app settings에 통합: startup/health/chat network 경계를 흐리므로 internal evaluator에 격리.
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `apps/api/src/sejong_ai_api/llm/settings.py` | exact constants, immutable secret-redacted settings, allowlisted dotenv/process loader, malformed/type fail-closed | provider enable 권위 |
| `apps/api/src/sejong_ai_api/llm/__init__.py` | internal package 생성 | 후속 evaluator 전용 namespace |
| `apps/api/tests/llm/test_settings.py` | exact/invalid/malformed/duplicate/non-string 6 tests | TDD·review regression |
| `apps/api/tests/llm/__init__.py` | test package | focused discovery |
| `apps/api/.env.example` | Upstage exact profile + disabled/synthetic false; obsolete DeepSeek example 제거 | 안전한 local setup |
| LLM-002 plan | linked-worktree-safe uv command, Task 1 checked, D-067 progress | 실행 재현·durable progress |
| 결정/TASKS/source/version/note | D-067, In Progress/Task 1 complete, docs 2.13.2 | 거버넌스·계보 |

### 데이터 흐름/상태 변화

process values→allowlisted dotenv validation/fill→safe/exact comparison→immutable settings 또는
`None`. 이 단계는 HTTP client/provider/repository/chat route를 만들거나 호출하지 않는다.

### 오류·빈 상태·롤백

파일 없음은 빈 dotenv로 처리하고 exact process profile만 있으면 동작한다. unreadable/invalid
UTF-8, duplicate, missing separator의 allowlisted key, whitespace key, empty key/value, quote,
NUL/CR/LF, non-ASCII/non-string, non-exact 값은 logging 없이 `None`이다.
## 7. 버전 전후

### 생성 시 매니페스트

- product_spec: 2.4.0
- repo_guidance: 1.7.6
- application: 0.6.0-local-core-loop
- web: 0.4.0-chat-admin-local-integration
- api: 3.1.0-draft
- shared_contracts: 0.4.0
- database_schema: 0.4.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.0.3-upstage-solar-pro3-synthetic-selected
- test_suite: 1.2.1-core-loop-closeout
- documentation: 2.13.1

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.6.0-local-core-loop | 동일 | 전체 evaluator gate인 Task 6 전까지 manifest 축 유지 |
| Web | 0.4.0-chat-admin-local-integration | 동일 | 변경 0 |
| API | 3.1.0-draft | 동일 | route/OpenAPI 변경 0 |
| DB schema | 0.4.0-local | 동일 | migration/DB 사용 0 |
| Official data | 0.1.0-initial.2 | 동일 | record/lineage 0 |
| Mock data | 0.0.0-not-populated | 동일 | mock 0 |
| Prompt set | 0.0.3-upstage-solar-pro3-synthetic-selected | 동일 | prompt 구현은 Task 2 |
| Test suite | 1.2.1-core-loop-closeout | 동일 | 전체 evaluator gate인 Task 6에서 승격 |
| Docs | 2.13.1 | 2.13.2 | 실행 승인·Task 1·리뷰 증거 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| 첫 `.\.tools\uv\uv.exe ... pytest apps/api/tests -q` | 실패: linked worktree에 command 없음; product test 미실행 | bounded tool-path failure | plan command correction |
| common-dir uv로 API baseline | PASS `1640 passed, 8 skipped, 1 warning, 5 subtests passed` | 17.82s | terminal |
| 최초 Task 1 RED | expected import error: `sejong_ai_api.llm` 없음 | 1 error | `.superpowers/sdd/task-1-report.md` |
| 최초 focused GREEN | PASS `4 passed`; Ruff/Mypy PASS | 4 tests | task report |
| review-fix RED | expected `2 failed, 4 passed`: malformed bypass + non-string exception | 6 tests | task report |
| review-fix GREEN | PASS `6 passed`; Ruff/Mypy PASS | 6 tests | task report |
| independent task re-review | Spec ✅, Critical/Important/Minor 0, quality Approved | base `9a5e6f5`..head `4bdc68d` | SDD review package/result |
| main focused pytest/Ruff/Mypy 재검증 | PASS `6 passed in 0.11s`, Ruff all checks, Mypy 4 files | 6 tests | terminal |
| docs/current-secret/whitespace gate | PASS, docs message·secret match 0·diff error 0 | exit 0 | terminal |
| forbidden protected-path diff from `9a5e6f5` | PASS, contracts/DB/data/lock/package/public app+chat diff 0 | exit 0 | terminal |

### 미실행 검증과 이유

실제 Upstage call/price/token/PM quality, DB/Docker/Web/E2E는 Task 1 범위가 아니다. key와 network는
Tasks 1~6 offline gate 전 사용 금지다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문·답변·PII 입력 0. real ignored `.env`는 수정하지 않았고 secret value는 test sentinel뿐이다.
- Security: API key repr/log 0, malformed/type error fail-closed, provider disabled default, network 0.
- Accessibility: UI 변화 0.
- Performance/cost: actual call/비용 0. settings에 input 4096/output 1024/concurrency 1/retry
  1/attempt 30을 exact 고정했다.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `.2`, local DB 모두 미접근·불변.
- mock/AI 생성: 실제 생성 답변 0; test sentinel key는 real secret이 아니다.
- schema/lineage: public API/DB/data schema·lineage 0.
- verified date: 2026-07-24; provider mutable facts는 actual Task 7 직전 공식 페이지 재확인.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 실행계획은 D-067로 승인돼 Task 1이 완료됐고 Task 2로 이어간다.
- 실제 Upstage key 입력, actual 합성 실행, 10개 결과 PM 채점은 여전히 인간 local gate다.
- 실제 시민/free-input/public/remote provider 연결 option B는 승인되지 않았다.
- Task 1 완료는 모델 연결·품질 검증 완료를 뜻하지 않는다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- helper/parser 분리, fixture와 test 이름은 같은 계약 안에서 AI가 자율 처리한다.
- Task 1 reviewer Important는 모두 fix/re-review했고 open finding은 없다.
- `.superpowers/sdd` brief/report/review package/ledger는 ignored 작업 증거이며 commit 대상이 아니다.

## 13. 인수인계·재현·롤백

### 재현

1. `git show 9318f7f`와 `git show 4bdc68d`를 확인한다.
2. Git common-dir parent의 `.tools/uv/uv.exe`를 `$uv`에 resolve한다.
3. `& $uv run --project apps/api --frozen pytest apps/api/tests/llm/test_settings.py -q`
4. 같은 package에 Ruff와 Mypy를 실행한다.
5. `LLM_PROVIDER=disabled`, `UPSTAGE_SYNTHETIC_EVALUATION_MODE=false` 기본을 확인한다.

### 롤백

역순으로 `git revert 4bdc68d`, `git revert 9318f7f`한다. `.env.example`과 internal package가
원복되며 DB/data migration/restore는 필요 없다. actual key/network가 없으므로 revoke도 없다.

### 다음 개발자 시작점

Task 2 brief를 읽고 `contracts.py`, `prompt.py`, `cost.py`, shared test fixtures를 TDD로 구현한다.
public chat/app imports와 dependency/lockfile을 건드리지 않는다.
## 14. 남은 위험·미해결 질문·다음 단계

- Tasks 2~6 offline evaluator가 남아 있다.
- Task 7은 official mutable fact recheck, local key, actual call, PM 채점이 필요하다.
- Python process environment는 외부 mutable state이므로 실제 runner는 exact loader 반환만 신뢰한다.
- full API baseline에는 기존 Starlette deprecation warning 1건과 승인된 DB-only skip 8건이 있다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증 — main focused/docs/secret/protected-path/diff 재검증 PASS
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
