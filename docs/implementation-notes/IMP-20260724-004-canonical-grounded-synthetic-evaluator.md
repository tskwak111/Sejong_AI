# IMP-20260724-004 — Canonical grounded synthetic evaluator

- Date/Time (KST): 2026-07-24T01:07:23+09:00
- Task ID: LLM-002
- Type: implementation
- Status: Done — Task 4 / LLM-002 In Progress
- Author/Agent: Codex integration, Task 4 implementation/review and Task 5 preflight subagents
- Branch: codex/LLM-002-upstage-synthetic-evaluation
- Base commit: 092b348
- Related plan/ADR/RFP:
  - [승인 실행계획](../superpowers/plans/2026-07-23-upstage-solar-pro3-synthetic-evaluation.md)
  - [승인 명세](../superpowers/specs/2026-07-23-upstage-solar-pro3-synthetic-evaluation-design.md)
  - [ADR-0022](../adr/0022-upstage-solar-pro3-synthetic-evaluation.md)
  - [Task 3 checkpoint](IMP-20260724-003-upstage-bounded-httpx-transport-and-attempt-budget.md)

## 1. 사용자 요청과 완료 기준

### 요청

승인된 LLM-002의 canonical T-01~T-10 allowlist와 기존 deterministic
마스킹→분류→ACTIVE/OFFICIAL 검색→근거 판정을 실제 provider 전 단계에 결합하고, actual
key/network 없이 안전한 sequential evaluator를 완성한다.

### Acceptance Criteria

- exact CSV header와 T-01~T-10 raw projection SHA-256 drift를 provider 구성 전에 차단한다.
- 각 generation 직전에 privacy/classification/expected intent/ACTIVE retrieval/ranking/grounding을
  다시 통과해야 한다.
- 준비 실패는 정확한 `PreparationCode`, zero metrics/source/provider call로 기록하고 중단한다.
- provider 실패는 서버 공식 record의 deterministic template fallback을 만들되 저장하지 않는다.
- source는 서버 record ID이고 첫 valid review text만 memory에 유지한다.
- focused/full LLM/Ruff/Mypy와 independent re-review를 통과한다.
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자 승인 아래 구현/review/preflight subagents와 Codex가 구현·검토·통합했다. |
| When — 언제 | 2026-07-24 KST, Task 3 review-clean 뒤 Task 4 checkpoint |
| Where — 어디서 | isolated worktree, canonical CSV read-only, internal LLM evaluator/fake repository tests |
| What — 무엇을 | hash-bound fixture loader, async grounded preparation, sequential evaluation/fallback/review sample |
| Why — 왜 | 임의 자유 입력·비ACTIVE KB·오래된 grounding이 provider 호출로 이어지지 않게 하기 위해 |
| How — 어떻게 | TDD, stateful repository regression, independent fix/re-review, main 61-test verification |
| How much — 어느 정도 | production 2개/test 2개, 15 focused/61 full LLM, 2 commits; DB/network/key 0 |

## 3. 시작 전 상태

- 관련 파일: canonical sample CSV, privacy redaction, classification, retrieval, grounding, response,
  DB repository projection, Tasks 1~3 LLM modules.
- 기존 동작: transport는 grounded fixture를 받았지만 canonical fixture load와 deterministic gate
  composition/run loop는 없었다.
- 발견한 충돌/부채:
  - 계획 sync 표기와 실제 async repository/provider가 불일치해 async contract로 보정했다.
  - preparation failure를 provider outcome으로 오표기할 위험을 union result로 닫았다.
  - 첫 구현은 fixture당 한 번만 grounding해 반복 사이 ACTIVE drift를 놓쳤고 reviewer Important로
    발견해 generation마다 재검증하도록 수정했다.
  - Task 5 preflight에서 명세 §6.2 per-attempt count를 위한 content-free trace 누락을 발견했다.
- Git 상태: 시작 `092b348`, 구현 `968fdbb`, freshness fix `4ab5277`, re-review Approved.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| FIXTURE-HASH | 데이터 품질 | allowlist wording drift | raw 5-field canonical JSON SHA-256 literal | provider preflight |
| ASYNC-GATE | 내부 | sync plan vs async repo/provider | async prepare/run, sequential await | correct composition |
| PREPARATION-RESULT | 안전 | pre-provider failure 표현 | exact PreparationCode union, zero metrics, run stop | honest report |
| GROUNDING-FRESHNESS | 데이터 품질 | repetition 사이 ACTIVE drift | every generation re-prepares | stale record 차단 |
| ATTEMPT-TRACE | 증거 | retry 첫 outcome 유실 | Task 4.5 content-free enum trace | Task 5 aggregate |

## 5. 설계 결정과 대안

### 선택

- T-01~T-10의 `test_id/질문/기대 intent/기대 상태/PII 포함` raw projection hash를 literal로 pin한다.
- 실제 repository의 ACTIVE/OFFICIAL projection을 신뢰하되 provider 직전마다 다시 query/rank/ground한다.
- preparation/provider terminal failure는 in-memory typed case로만 기록한다.
- template answer는 existing `build_success_response()`로 만들고 `record_interaction`은 호출하지 않는다.

### 이유

canonical server-loaded fixture와 official record만 provider에 전달해 임의 입력·출처 생성·질문 원문
DB 저장 경계를 유지하고, run 중 KB 상태 변화도 다음 call 전에 반영한다.

### 고려했지만 선택하지 않은 대안

- ID만 allowlist: 질문/label drift를 못 잡아 제외.
- CSV 전체 hash: T-11 이후 비허용 row 변화가 합성 allowlist를 불필요하게 막으므로 projection hash 선택.
- fixture당 grounding 1회: stale ACTIVE reuse 때문에 폐기.
- parallel gather: concurrency 1과 fail-closed stop 순서를 흐려 제외.
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `llm/fixtures.py` | exact header/ID/order/raw projection hash와 typed fixture/preparation code | canonical allowlist |
| `llm/evaluation.py` | async per-generation deterministic gate, sequential run, fallback/review samples | safe composition |
| `test_fixtures.py` | canonical/hash/header/order/drift/malformed cases | data quality regression |
| `test_evaluation.py` | privacy/classification/grounding/source/fallback/order/terminal/freshness | safety regression |
| plan/version/note | Task 4 완료와 Task 4.5/Task 5 preflight correction | durable handoff |

### 데이터 흐름/상태 변화

canonical CSV→hash-bound `SyntheticFixture`→redaction→SafeQuestion→classification/expected intent→
repository ACTIVE/OFFICIAL→ranking→grounding→`GroundedFixture`→provider→in-memory case/review sample.
이 흐름은 각 repetition 직전에 다시 실행된다.

### 오류·빈 상태·롤백

privacy/non-deterministic/no-grounding은 exact preparation case를 남기고 provider 0으로 중단한다.
ATTEMPT_CAP/INPUT_LIMIT도 다음 fixture를 시작하지 않는다. 파일 추가만 있어 revert 가능하다.
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
- documentation: 2.13.4

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.6.0-local-core-loop | 동일 | Task 6 gate 전 유지 |
| Web | 0.4.0-chat-admin-local-integration | 동일 | 변경 0 |
| API | 3.1.0-draft | 동일 | public contract 0 |
| DB schema | 0.4.0-local | 동일 | fake repo만 사용 |
| Official data | 0.1.0-initial.2 | 동일 | canonical CSV/KB 변경 0 |
| Mock data | 0.0.0-not-populated | 동일 | test fakes만 사용 |
| Prompt set | 0.0.3-upstage-solar-pro3-synthetic-selected | 동일 | 변경 0 |
| Test suite | 1.2.1-core-loop-closeout | 동일 | Task 6에서 승격 |
| Docs | 2.13.4 | 2.13.5 | Task 4/review/Task 5 preflight |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| initial RED | expected fixture/evaluation import errors | 2 errors | ignored task report |
| initial GREEN | PASS | 13 tests | task report |
| extra expected-intent/template TDD | expected RED then GREEN | 2 regressions | task report |
| first independent review | Important stale grounding reuse | Needs fixes | bounded diff |
| freshness fix RED | repetition2 incorrectly called provider | 1 failed | task report |
| freshness fix GREEN | focused 15/full LLM 61; Ruff/Mypy PASS | 61 tests | task report |
| independent re-review | Spec ✅, findings 0, Quality Approved | `092b348..4ab5277` | bounded diff |
| main LLM/Ruff/Mypy | PASS | 61 tests, 19 files | terminal |

### 미실행 검증과 이유

실 DB/provider/key/network, report/runner/PM review는 Tasks 5~7 범위다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: provider receives masked safe question only; raw canonical question is in-memory review only.
- Security: source metadata/model text persistence 0, provider/key/network/DB 0.
- Accessibility: UI 변화 0.
- Performance/cost: sequential concurrency 1; repository gate repeats per generation by safety design.

## 10. 데이터와 출처 영향

- 공식 데이터: file/database immutable; literal projection hash는 base `b318375`와 현재가 동일.
- mock/AI 생성: typed fake repository/provider only; actual generation 0.
- schema/lineage: DB/public API/data lineage 변경 0.
- verified date: 2026-07-24.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- Task 4는 실제 모델 품질 PASS가 아니라 canonical/grounding offline gate 완료다.
- actual key/network/PM scoring은 Task 7 human local gate다.
- Task 4.5 trace와 Task 5 report/runner가 끝나기 전 actual 실행 금지다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- async protocol/test fake/UUID/clock injection은 내부 세부다.
- canonical T-09와 transport-only T-09 fixture가 다르므로 Task 4 canonical tests는 T-01을 쓴다.

## 13. 인수인계·재현·롤백

### 재현

1. `git show 968fdbb`와 `git show 4ab5277` 확인.
2. common-dir uv로 focused Task 4와 전체 `apps/api/tests/llm` 실행.
3. Ruff format/check, Mypy 실행.
4. canonical CSV를 임의 복사해 allowed row 한 글자 변경 시 fail-closed 확인.

### 롤백

`git revert 4ab5277`, `git revert 968fdbb`. DB/data/key/network가 없어 restore/revoke는 없다.

### 다음 개발자 시작점

Task 4.5에서 `GenerationOutcome`과 `EvaluationCaseResult`에 content-free attempt outcomes를
추가한 뒤 Task 5 report/runner로 간다.
## 14. 남은 위험·미해결 질문·다음 단계

- Tasks 4.5~6 offline report/runner/gates가 남았다.
- Task 7 official price/policy recheck, key, actual run, PM scoring은 인간 local 작업이다.
- Task 5는 Windows selector policy/readiness-before-provider/exact ten-score/safe parser를 지킨다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
