# IMP-20260724-003 — Upstage bounded HTTPX transport and attempt budget

- Date/Time (KST): 2026-07-24T00:39:43+09:00
- Task ID: LLM-002
- Type: implementation
- Status: Done — Task 3 / LLM-002 In Progress
- Author/Agent: Codex integration, Task 3 implementation and independent review subagents
- Branch: codex/LLM-002-upstage-synthetic-evaluation
- Base commit: 809dcdc
- Related plan/ADR/RFP:
  - [승인 실행계획](../superpowers/plans/2026-07-23-upstage-solar-pro3-synthetic-evaluation.md)
  - [승인 명세](../superpowers/specs/2026-07-23-upstage-solar-pro3-synthetic-evaluation-design.md)
  - [ADR-0022](../adr/0022-upstage-solar-pro3-synthetic-evaluation.md)
  - [Task 2 checkpoint](IMP-20260724-002-upstage-합성-평가-strict-prompt-output-cost-contracts.md)

## 1. 사용자 요청과 완료 기준

### 요청

승인된 LLM-002 계획을 계속 실행해 실제 provider 호출 없이 atomic attempt budget과 bounded
HTTPX transport를 TDD·독립 검토로 완성하고 다음 grounded evaluator 단계까지 진행한다.

### Acceptance Criteria

- process-run outbound attempt는 30회, 동시성은 1로 원자적으로 제한한다.
- HTTPX hidden retry는 0이고 logical retry는 승인 오류에만 정확히 1회다.
- 401/403·기타 4xx, preflight/provider input overflow, attempt cap은 재시도하지 않는다.
- response body·exception text·secret은 outcome/log/assertion에 노출하지 않는다.
- exact base/model/payload/timeout/output cap을 사용하고 실제 DNS/network는 0이다.
- full failure matrix, Ruff format/check, Mypy와 독립 review를 통과한다.
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 연속 진행을 승인했고 구현 subagent, independent reviewer, Codex가 구현·검토·통합했다. |
| When — 언제 | 2026-07-24 KST, Task 2 review-clean 뒤 Task 3 checkpoint |
| Where — 어디서 | isolated linked worktree의 internal `sejong_ai_api.llm`, HTTPX MockTransport tests |
| What — 무엇을 | non-resettable attempt cap, concurrency semaphore, exact HTTP client factory와 strict failure parser |
| Why — 왜 | 실제 호출 전에 retry 폭주·비용 초과·본문 유출·input overflow를 닫기 위해 |
| How — 어떻게 | RED→GREEN, 23-case failure matrix, static checks, bounded diff independent review |
| How much — 어느 정도 | production 2개/test 2개, 구현 1 commit+format-only 1 commit, actual call/key/DB/data 0 |

## 3. 시작 전 상태

- 관련 파일: Task 1 settings, Task 2 contracts/prompt/cost, existing HTTPX 0.28.1, LLM-002 plan.
- 기존 동작: provider-neutral contract만 있었고 HTTP 예약·전송·retry parser는 없었다.
- 발견한 충돌/부채:
  - Task 3 static gate가 Task 1의 기존 두 파일에 Ruff format 차이를 발견했다. 동작 변경 없이
    `b2849f3`으로 정규화하고 Task 1 tests를 재실행했다.
  - Task 4 사전 감사에서 sync 표기와 실제 async repository/provider, preparation code 결과 타입의
    불일치를 발견해 구현 전 계획을 보정했다.
- Git 상태: 시작 `809dcdc`, Task 3 `854b3b5`, format-only `b2849f3`, independent review Approved.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| ATTEMPT-CAP | 안전/비용 | concurrent reservation 경합 | semaphore 1 + lock + non-resettable count 30 | outbound/비용 상한 |
| RETRY-MATRIX | 안전 | hidden/logical retry 구분 | HTTP transport retries 0; approved failures만 1회 | bounded requests |
| BODY-LEAK | 보안 | provider/exception 내용 노출 | stable enum only, logger 없음 | secret/content 0 |
| TASK4-ASYNC | 내부 | 계획 sync와 실제 async 경계 | async prepare/run + sequential await | evaluator 통합 |
| TASK4-PREP | 내부 | preparation failure 표현 누락 | `OutcomeCode | PreparationCode`, zero usage, fail-closed stop | report 정확성 |

## 5. 설계 결정과 대안

### 선택

- `AttemptBudget.reserve()`가 semaphore를 먼저 획득하고 lock 안에서 count를 증가시키며 cap 도달 시
  transport body 진입 전에 stable exception을 낸다.
- injected `httpx.AsyncClient`로 unit test하고 production factory만 exact Upstage 설정을 만든다.
- timeout/transport/429/5xx/empty/truncated/schema-invalid만 1회 재시도한다.
- prompt preflight는 예약 전, provider prompt usage 4097은 첫 응답 뒤 즉시 INPUT_LIMIT로 끝낸다.

### 이유

retry 계층과 global attempt counter를 분리하면 hidden retry나 concurrent overshoot 없이 실제
outbound 횟수를 보고서와 비용 계산에 일치시킬 수 있다.

### 고려했지만 선택하지 않은 대안

- SDK/자동 retry: 횟수와 body logging을 통제하기 어려워 제외.
- global budget reset: 동일 process run cap을 우회하므로 제외.
- 오류 본문/exception 메시지 전달: 개인정보·provider body 유출 위험으로 제외.
- actual integration test: Tasks 1~6 offline 이후 Task 7 human gate 전 금지.
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `llm/limits.py` | atomic cap/concurrency reservation과 read-only usage | process-run 권위 |
| `llm/upstage.py` | exact client/payload, retry parser, strict outcome/usage aggregation | bounded provider adapter |
| `test_limits.py` | validation, 30/31, concurrency serialization, exception release | race/cap regression |
| `test_upstage.py` | request/factory와 retry/non-retry/failure/input/cap matrix | network-free transport proof |
| Task 1 settings/tests | Ruff format only | package-wide format gate |
| plan/version/note | Task 3 완료와 Task 4 async/preparation-code 보정 | 재현·계보 |

### 데이터 흐름/상태 변화

GroundedFixture → source-free messages → byte preflight → atomic reservation → injected HTTPX POST →
bounded envelope parse → strict GeneratedAnswer/TokenUsage/OutcomeCode. Tests는 모두 MockTransport다.

### 오류·빈 상태·롤백

preflight overflow와 cap은 request 0, provider usage overflow는 retry 0이다. AUTH/other 4xx는 retry
0, retryable failures는 최대 2 attempts 후 stable code로 종료한다. 모듈 추가만 있어 revert 가능하다.
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
- documentation: 2.13.3

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.6.0-local-core-loop | 동일 | 전체 Task 6 gate 전 유지 |
| Web | 0.4.0-chat-admin-local-integration | 동일 | 변경 0 |
| API | 3.1.0-draft | 동일 | public route/OpenAPI 변경 0 |
| DB schema | 0.4.0-local | 동일 | migration/DB 사용 0 |
| Official data | 0.1.0-initial.2 | 동일 | record/lineage 0 |
| Mock data | 0.0.0-not-populated | 동일 | HTTP MockTransport는 manifest mock data가 아님 |
| Prompt set | 0.0.3-upstage-solar-pro3-synthetic-selected | 동일 | exact selected prompt 사용 |
| Test suite | 1.2.1-core-loop-closeout | 동일 | 전체 evaluator gate Task 6에서 승격 |
| Docs | 2.13.3 | 2.13.4 | Task 3·review·Task 4 preflight |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| Task 3 RED | expected imports missing | collection 2 errors | ignored task report |
| Task 3 GREEN | PASS | 23 tests | ignored task report |
| Ruff/Mypy | PASS | 15 source files | task report |
| independent review | Spec ✅, Critical/Important/Minor 0, Quality Approved | `809dcdc..854b3b5` | bounded review |
| main all LLM pytest | PASS | 46 tests in 0.31s | terminal |
| package Ruff check/Mypy | PASS | 15 source files | terminal |
| initial Ruff format check | expected fail: older Task 1 files 2 | 2 paths | terminal |
| post-format Task 1 pytest + format/check/Mypy | PASS | 6 tests; 15 formatted | terminal |
| Task 4 read-only preflight | existing pipeline 22 tests PASS; Important 3 resolved in plan | file/network 0 | agent evidence |

### 미실행 검증과 이유

Actual Upstage, DB/Docker, Web/E2E, PM scoring은 Task 3 범위가 아니며 Tasks 1~6 offline gate 전
실행하지 않는다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: masked grounded fixture 외 raw question을 받지 않고 content persistence/logging은 0.
- Security: key repr/log 0, response/exception text 0, actual DNS/network 0, public imports 0.
- Accessibility: UI 변경 0.
- Performance/cost: concurrency 1, logical retry≤1, process attempts≤30; actual token/cost 0.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `.2`/DB 미접근·불변.
- mock/AI 생성: HTTPX MockTransport test envelope만 사용; official/mock dataset 변화 0.
- schema/lineage: public API/DB/data schema 0.
- verified date: 2026-07-24; provider mutable fact는 Task 7 직전 재확인.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- production client factory 구현은 실제 모델 연결·품질 PASS나 public 연결을 뜻하지 않는다.
- actual key 입력/network 실행/PM scoring은 여전히 Task 7 human local gate다.
- 시민/free-input/public/remote provider option B는 미승인이다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- parser/helper/test parametrization과 Ruff formatting은 같은 승인 계약 안의 내부 세부다.
- Task 4는 corrected async/typed preparation failure 계약으로 이어간다.
- ignored SDD brief/report/review package는 commit하지 않는다.

## 13. 인수인계·재현·롤백

### 재현

1. `git show 854b3b5`와 `git show b2849f3`를 확인한다.
2. common-dir project uv로 `pytest apps/api/tests/llm -q`를 실행한다.
3. 같은 package에 `ruff format --check`, `ruff check`, `mypy`를 실행한다.
4. tests가 MockTransport만 사용하고 `seen` request count가 matrix와 일치하는지 확인한다.

### 롤백

`git revert b2849f3`, `git revert 854b3b5` 순으로 실행한다. actual key/network/DB/data가 없어
revoke/migration/restore는 없다.

### 다음 개발자 시작점

Task 4의 canonical hash `26a60e4d3c0e349beabec7c26206f3ffca2d7c46006309a09b3711ac6f61148a`,
async repository/provider 인터페이스와 `OutcomeCode | PreparationCode` 보정을 먼저 읽는다.
## 14. 남은 위험·미해결 질문·다음 단계

- Tasks 4~6 offline evaluator/report/gate가 남았다.
- Task 7 actual은 공식 가격/policy 재확인, ignored local key와 PM review가 필요하다.
- run-wide INPUT_LIMIT/ATTEMPT_CAP stop은 Task 4 evaluator 책임이다.
- canonical Task 4 tests는 transport-only T-09 fixture를 재사용하지 않는다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
