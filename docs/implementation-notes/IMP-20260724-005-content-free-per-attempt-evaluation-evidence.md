# IMP-20260724-005 — Content-free per-attempt evaluation evidence

- Date/Time (KST): 2026-07-24T01:29:01+09:00
- Task ID: LLM-002
- Type: implementation
- Status: Done — Task 4.5 / LLM-002 In Progress
- Author/Agent: Codex integration, Task 4.5 implementation/review and Task 6 preflight subagents
- Branch: codex/LLM-002-upstage-synthetic-evaluation
- Base commit: c2e0fb8
- Related plan/ADR/RFP:
  - [승인 실행계획](../superpowers/plans/2026-07-23-upstage-solar-pro3-synthetic-evaluation.md)
  - [승인 명세 §6.2](../superpowers/specs/2026-07-23-upstage-solar-pro3-synthetic-evaluation-design.md)
  - [Task 4 checkpoint](IMP-20260724-004-canonical-grounded-synthetic-evaluator.md)

## 1. 사용자 요청과 완료 기준

### 요청

Tasks 1~4를 계속 구현하고, 승인 명세가 요구한 retry/timeout/429/empty/truncated/schema-invalid
시도별 집계를 response body 없이 보존할 수 있도록 internal evidence contract를 보강한다.

### Acceptance Criteria

- outbound request마다 exact `OutcomeCode` 하나를 immutable tuple에 남긴다.
- trace 길이와 attempts가 일치하고 SUCCESS는 마지막 code가 SUCCESS다.
- preflight/cap-before-request/preparation failure는 빈 trace다.
- preparation case는 모든 evidence가 zero/none/false이고 provider case는 source/fallback과 일치한다.
- 질문·답변·본문·exception text·자유 문자열은 trace에 없다.
- full LLM/Ruff/Mypy와 independent re-review를 통과한다.
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 구현/review/preflight subagents와 Codex가 구현·독립 검토·통합했다. |
| When — 언제 | 2026-07-24 KST, Task 4 review-clean 뒤 Task 5 preflight blocker correction |
| Where — 어디서 | internal contracts/transport/evaluator와 LLM tests, actual provider/DB 밖 |
| What — 무엇을 | content-free per-attempt enum trace와 strict aggregate evidence invariants |
| Why — 왜 | retry 뒤 SUCCESS가 첫 실패를 지워 자동 지표·비용·fallback 증거를 왜곡하지 않게 하기 위해 |
| How — 어떻게 | RED→GREEN, independent Important fix/re-review, main 93-test verification |
| How much — 어느 정도 | production 3개/test 3개, 2 commits, 93 LLM tests; network/key/DB/data 0 |

## 3. 시작 전 상태

- 관련 파일: `contracts.py`, `upstage.py`, `evaluation.py`, Task 5 report schema, design §6.2.
- 기존 동작: 최종 case code/aggregate usage/attempt count만 있어 retry 첫 결과가 유실됐다.
- 발견한 충돌/부채:
  - Task 5 preflight가 per-attempt metric 증거 누락을 Critical로 발견했다.
  - 첫 trace 구현 뒤 reviewer가 preparation case에 조작된 token/latency/source/fallback을 넣을 수
    있는 Important를 발견했다.
  - Task 6 plan은 system Python 3.14, working-tree-only diff와 literal import 검색을 사용해
    별도로 보정했다.
- Git 상태: 시작 `c2e0fb8`, trace `0e04901`, invariant fix `b8e32ae`, re-review Approved.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| ATTEMPT-EVIDENCE | 안전/측정 | retry 첫 code 유실 | exact enum tuple per reservation | automatic metrics |
| PREP-EVIDENCE | 무결성 | preparation aggregate 조작 가능 | zero/empty/none/false only | report/cost/source |
| PROVIDER-EVIDENCE | 무결성 | source/fallback/trace 불일치 | exact types and final-code invariants | PASS gate |
| TASK6-RUNTIME | 재현 | system 3.14 사용 위험 | common-dir uv Python 3.12.13 offline | regression evidence |

## 5. 설계 결정과 대안

### 선택

- `GenerationOutcome`과 `EvaluationCaseResult`에 required
  `attempt_outcomes: tuple[OutcomeCode, ...]`를 추가한다.
- provider는 reservation 하나마다 parsed stable enum 하나만 append한다.
- preparation과 provider result의 수치·source·fallback 일관성을 dataclass 생성 시 강제한다.

### 이유

text-free closed enum만으로 명세의 aggregate failure count를 재현하면서 질문·답변·provider body
저장 금지를 유지한다.

### 고려했지만 선택하지 않은 대안

- final outcome만 사용: retry history 유실.
- HTTP status/body trace: 개인정보·provider content 노출 위험.
- report에서 attempts 차이 추정: failure 종류를 복원할 수 없어 제외.
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `llm/contracts.py` | required trace와 length/SUCCESS invariant | provider outcome 권위 |
| `llm/upstage.py` | reservation별 stable code append/cap preservation | exact attempt history |
| `llm/evaluation.py` | trace copy와 strict preparation/provider evidence | honest report input |
| contract/upstage/evaluation tests | retry/cap/input/preparation/type/source/fallback matrix | regression |
| plan/version/note | Task 4.5/Task 5~6 correction과 docs 2.13.6 | durable handoff |

### 데이터 흐름/상태 변화

각 reserved HTTP attempt의 bounded enum→GenerationOutcome immutable tuple→EvaluationCaseResult
immutable tuple→Task 5 aggregate count. content는 이 흐름에 들어오지 않는다.

### 오류·빈 상태·롤백

inconsistent type/length/source/fallback/preparation evidence는 stable ValueError로 생성 단계에서
거부한다. contract 확장이므로 코드 revert만 필요하고 DB/data restore는 없다.
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
- documentation: 2.13.5

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.6.0-local-core-loop | 동일 | Task 6 gate 전 유지 |
| Web | 0.4.0-chat-admin-local-integration | 동일 | 0 |
| API | 3.1.0-draft | 동일 | public contract 0 |
| DB schema | 0.4.0-local | 동일 | 0 |
| Official data | 0.1.0-initial.2 | 동일 | 0 |
| Mock data | 0.0.0-not-populated | 동일 | 0 |
| Prompt set | 0.0.3-upstage-solar-pro3-synthetic-selected | 동일 | 0 |
| Test suite | 1.2.1-core-loop-closeout | 동일 | Task 6에서 승격 |
| Docs | 2.13.5 | 2.13.6 | Task 4.5·Task 6 preflight |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| initial trace RED | 33 failed, 12 passed; evaluator invariant 4 failed | expected | ignored task report |
| initial GREEN | focused 51/full 72, Ruff/Mypy PASS | 72 tests | task report |
| first review | Important preparation evidence corruption | Needs fixes | bounded diff |
| invariant RED | 19 failed, 2 passed | expected | task report |
| invariant GREEN | focused 25/evaluator 36/full 93, Ruff/Mypy PASS | 93 tests | task report |
| independent re-review | Spec ✅, findings 0, Quality Approved | `c2e0fb8..b8e32ae` | bounded diff |
| main LLM/Ruff/Mypy | PASS | 93 tests, 19 files | terminal |

### 미실행 검증과 이유

Task 5 report/runner, full API/root/Web offline Task 6와 actual Task 7은 아직 미실행이다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: trace는 closed enum뿐이며 질문/답변/provider body/exception text 0.
- Security: actual key/network/DB 0, public route/dependency 0.
- Accessibility: UI 0.
- Performance/cost: trace는 최대 30 enum; actual cost 0.

## 10. 데이터와 출처 영향

- 공식 데이터/mock/schema/lineage: 모두 불변·미접근.
- verified date: 2026-07-24.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- Task 4.5는 actual 모델 품질 PASS가 아니다.
- Task 5~6 offline gate 뒤에도 actual key/network/PM review는 Task 7 human local gate다.
- public/free-input option B는 계속 미승인이다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- enum append/helper/test parametrization은 내부 구현 세부다.
- Task 5는 `outcome_counts`와 `attempt_outcome_counts`를 분리한다.

## 13. 인수인계·재현·롤백

### 재현

1. `git show 0e04901`, `git show b8e32ae`.
2. common-dir uv로 `pytest apps/api/tests/llm -q`.
3. Ruff format/check, Mypy.
4. RATE_LIMIT→SUCCESS trace가 두 enum이고 content sentinel이 없는지 확인.

### 롤백

`git revert b8e32ae`, `git revert 0e04901`. DB/key/network 복구 없음.

### 다음 개발자 시작점

Task 5 brief와 corrected report/runner gates를 읽고 text-free aggregate/CLI를 TDD로 구현한다.
## 14. 남은 위험·미해결 질문·다음 단계

- Tasks 5~6 offline, Task 7 human actual이 남았다.
- Task 6은 common-dir uv 3.12.13 offline 및 base-protected diff를 사용한다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
