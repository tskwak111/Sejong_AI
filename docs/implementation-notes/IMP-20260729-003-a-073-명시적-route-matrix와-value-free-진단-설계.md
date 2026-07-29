# IMP-20260729-003 — A-073 명시적 route matrix와 value-free 진단 설계

- Date/Time (KST): 2026-07-29T01:22:26+09:00
- Task ID: A-073-CLASSIFIER-ENUM-SHAPE-CORRECTION
- Type: decision-design-spec
- Status: Decision-only — Done; written specification Approved, implementation plan Review
- Author/Agent: Codex `/root`, 병렬 read-only reviewers
- Branch: codex/a-072-strict-classifier-wire
- Base commit: 178750b
- Related plan/ADR/RFP: ADR-0025, ADR-0027, A-071/A-072 specs, A-073 written specification

## 1. 사용자 요청과 완료 기준

### 요청

- 사용자는 API key 교체보다 현재 classifier failure를 실제 원인에 맞게 해결하라고 지시했다.
- 조사 결과를 바탕으로 제시한 추천 A, 즉 explicit route matrix와 refined value-free
  diagnostics를 사용자가 `ㅇㅋ 진행해`로 승인했다.

### Acceptance Criteria

- D-117의 9/9 `ENUM_SHAPE_REJECTED` 경계를 근거로 원인 가설과 최소 교정을 명세한다.
- 기존 five-key schema, privacy/fail-closed/API/DB/data/dependency 경계를 유지한다.
- written specification을 작성하고 권위 문서·버전·INDEX를 동기화한다.
- 이 checkpoint에서는 제품 코드와 provider/network actual을 실행하지 않는다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자 결정자, Codex `/root`, 병렬 read-only code/docs/security reviewers |
| When — 언제 | 2026-07-29 KST, D-117 actual 및 API key 교체 불필요 진단 직후 |
| Where — 어디서 | `codex/a-072-strict-classifier-wire` worktree의 classifier 설계·권위·버전 문서 |
| What — 무엇을 | A-073 explicit prompt matrix와 value-free refined diagnostics written specification |
| Why — 왜 | exact five-key/all-string은 통과했지만 enum/shape 9/9 거절 원인이 prompt ambiguity와 broad stage에 묻혀 있기 때문 |
| How — 어떻게 | 생산 parser 추적, D-117 aggregate 대조, 3개 접근 비교, 추천 A 승인, 문서-only integration |
| How much — 어느 정도 | documentation 1축 전진; code/provider/DB/data/dependency/actual call 0 |

## 3. 시작 전 상태

- 관련 파일: classifier contracts/prompt/transport와 A-071/A-072 specs, D-117 report,
  `DECISION_LOG`, `TEAM_DECISIONS`, ambiguity/task/version/change documents.
- 기존 동작: strict schema는 exact 5 key와 string type만 강제한다. server는 nullable
  4필드의 exact `NONE`을 정규화한 뒤 enum, identifier, route shape, catalog를 검증한다.
- 발견한 충돌/부채: compact prompt의 `default=NONE`, `NONE=없음`, incomplete route grammar와
  broad `ENUM_SHAPE_REJECTED`가 actual correction과 diagnosis를 방해한다.
- Git 상태: 시작 HEAD `178750b`, clean tracked tree, branch
  `codex/a-072-strict-classifier-wire`.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-073 | B / High | enum/shape 9/9의 bounded 교정 | D-118 추천 A 승인 | prompt·internal diagnostics·tests; actual separate gate |

## 5. 설계 결정과 대안

### 선택

- prompt에 route별 exact five-field matrix, closed provider vocabulary, literal `NONE`,
  same-row topic/coverage를 명시한다.
- production observer는 existing enum-only signature를 유지하면서 route/intent/pending/
  identifier/route-shape first-failure stage만 aggregate한다.

### 이유

- 현재 key와 transport는 9/9 HTTP 2xx·usage·JSON key/type까지 통과했다.
- prompt ambiguity를 제거하는 것이 가장 작은 single correction이며 새 schema feature 4xx
  위험을 피한다.
- 값 없는 stage refinement는 실패가 남아도 raw response 없이 다음 원인 계층을 판별한다.

### 고려했지만 선택하지 않은 대안

- provider schema enum/pattern: Upstage exact subset compatibility가 검증되지 않았고
  cross-field/catalog를 완전히 강제하지 못해 보류.
- single `choice_id`: five-key contract를 교체하는 큰 architecture change라 기각.
- API key 교체: current key가 semantic parser 직전까지 성공하므로 무관.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| A-073 written specification | architecture, exact matrix, diagnostics, TDD, actual gate | 구현 권위 |
| decisions/source-of-truth/ambiguity/tasks | D-118과 Review 상태 동기화 | 중복 사실 drift 방지 |
| changelog/manifest | docs-only checkpoint `2.30.4` | version lineage |
| implementation note/INDEX | 6W1H·재현·인수인계 | 저장소 DoD |

### 데이터 흐름/상태 변화

이 checkpoint는 문서-only다. target runtime은 masked question과 ACTIVE/OFFICIAL catalog를
explicit prompt에 전달하고, response를 exact key/type→NONE→refined enum/shape→catalog
순서로 검증한 뒤 기존 decision 또는 fail-closed fallback을 반환한다.

### 오류·빈 상태·롤백

- malformed provider value는 자동 보정하지 않는다.
- D-117 current/archive evidence는 immutable 보존한다.
- 이 문서 commit을 revert하면 version `2.30.3` 상태로 돌아가며 DB/data rollback은 없다.

## 7. 버전 전후

### 생성 시 매니페스트
- product_spec: 2.6.0
- repo_guidance: 1.7.10
- application: 0.12.3-structured-classifier-wire
- web: 0.8.0-guided-chat
- api: 4.0.0-draft
- shared_contracts: 1.0.0
- database_schema: 0.5.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.4.2-exact-five-key-schema
- test_suite: 2.1.6-structured-classifier-wire
- documentation: 2.30.3

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.12.3-structured-classifier-wire | unchanged | design-only |
| Web | 0.8.0-guided-chat | unchanged | out of scope |
| API | 4.0.0-draft | unchanged | public contract preserved |
| DB schema | 0.5.0-local | unchanged | no migration |
| Official data | 0.1.0-initial.2 | unchanged | no factual change |
| Mock data | 0.0.0-not-populated | unchanged | no mock |
| Prompt set | 0.4.2-exact-five-key-schema | unchanged | target only, no code yet |
| Test suite | 2.1.6-structured-classifier-wire | unchanged | target only, no tests yet |
| Docs | 2.30.3 | 2.30.4 | approved design written spec |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| `git status --short; git branch --show-current; git log -3 --oneline` | clean start, expected branch/HEAD | 3 commits inspected | terminal |
| parser/prompt/spec read-only trace | D-117 failure boundary confirmed | 3 independent lanes | A-073 spec/reviewer reports |
| focused classifier baseline | PASS | 142 passed in 1.16s | read-only reviewer terminal |
| written spec independent red-team | 3 findings fixed inline | report/archive, shared authority, dynamic example | A-073 written spec |
| `python -B scripts/check_repository_docs.py` | PASS | repository documentation check passed | terminal |
| `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/check_secret_patterns.ps1 -RepositoryRoot .` | PASS | exit 0, findings 0 | terminal |
| `git diff --check` | PASS | exit 0; INDEX line-ending warning only | terminal |
| exact placeholder scan | PASS | `TBD`, `TODO`, template status 0 | terminal |

### 미실행 검증과 이유

- 제품 테스트·lint/typecheck: 제품 코드 변경 전 design checkpoint이므로 미실행.
- Upstage actual: 별도 exact 인간 승인 전 금지, call/cost 0.
- DB/Web: 변경 없음.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문·provider body·wrong value·fixture별 stage 비보관. observer는 closed enum만 전달.
- Security: key/DSN/status detail/exception 비노출, existing PII-before-provider 유지.
- Accessibility: UI 변경 없음.
- Performance/cost: design-only call/cost 0. target prompt는 4,096 guard를 반드시 통과한다.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `.2`와 ACTIVE/OFFICIAL projection 변경 0.
- mock/AI 생성: synthetic fixture는 test-only; 행정 사실 생성 없음.
- schema/lineage: DB/schema/provider five-key wire 불변; documentation lineage only.
- verified date: 2026-07-29 KST.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 현재 API key는 교체할 근거가 없다.
- 이 명세 승인은 제품 구현 또는 Upstage actual 승인이 아니다.
- 구현 목표는 prompt `0.4.3`, application `0.12.4`, tests `2.1.7`이며 plan 승인 뒤에만
  변경한다.
- 실제 provider correction은 offline/clean-source 이후 별도 exact-one 승인 대상이다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- parser first-failure precedence, helper 분리와 test fixture 구성은 public behavior를 바꾸지
  않는 내부 구현 세부다.
- legacy generic stage를 삭제하지 않고 historical compatibility를 유지한다.

## 13. 인수인계·재현·롤백

### 재현

1. D-117 report에서 HTTP 2xx/usage/key/type 통과와 enum/shape 9를 확인한다.
2. A-072 prompt와 classifier contracts의 route shape를 대조한다.
3. A-073 spec의 route matrix, diagnostics precedence와 actual gate를 검토한다.
4. repository docs/diff checks를 실행한다.

### 롤백

- 이 design commit을 revert한다. 제품 코드, provider state, DB/data rollback은 없다.

### 다음 개발자 시작점

- D-119에서 승인된 written specification과 Review 상태의 TDD plan을 대조한다. plan 승인
  뒤 Tasks 1~5만 실행하며 Task 6 actual은 별도 exact 인간 승인 전 시작하지 않는다.

## 14. 남은 위험·미해결 질문·다음 단계

- prompt가 길어져 4,096 guard를 위반할 가능성은 implementation RED test로 먼저 검증한다.
- prompt-only correction이 actual에서 실패할 수 있으므로 refined aggregate를 함께 구현한다.
- Upstage schema enum 지원을 추측해 동시 변경하지 않는다.
- future actual 전 D-117 byte-preserving archive/hash/absence preflight를 구현·검증한다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
