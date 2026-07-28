# IMP-20260729-005 — A-073 classifier route matrix와 refined diagnostics offline 구현

- Date/Time (KST): 2026-07-29T03:01:55+09:00
- Task ID: A-073-CLASSIFIER-ENUM-SHAPE-CORRECTION
- Type: implementation-provider-offline
- Status: Tasks 1~4 offline Done; Task 5 exact-one root aggregate `NOT VERIFIED/FAIL`,
  rerun 0; final review fix wave 1 implemented, final review pending; Task 6 blocked
- Author/Agent: 사용자 결정자 + Codex controller + Task 1~5 구현 에이전트
- Branch: `codex/a-072-strict-classifier-wire`
- Base commit: `34cc45d1132a5316a1e5e31c2adb3c77d4338aef`
- Implementation commits:
  `7e902584a0d7839baf22beb91ba391a4861d405a`,
  `fcd89d8bc54fb63f445639485915bdf1bac7d5dd`,
  `d6a494d2883e61582398dac805cb53d1a2e1f899`,
  `34cc45d1132a5316a1e5e31c2adb3c77d4338aef`, Task 4 evidence is this note's commit
- Related plan/ADR/RFP:
  [approved specification](../superpowers/specs/2026-07-29-upstage-classifier-explicit-route-matrix-and-refined-diagnostics-design.md),
  [approved plan](../superpowers/plans/2026-07-29-upstage-classifier-explicit-route-matrix-and-refined-diagnostics.md),
  [ADR-0025](../adr/0025-hybrid-bounded-llm-question-classification.md),
  [ADR-0027](../adr/0027-active-topic-catalog-and-coverage-grounding.md),
  [RFP matrix](../source-of-truth/RFP_MATRIX.md), D-117~D-120

## 1. 사용자 요청과 완료 기준

### 요청

사용자는 exact `계획 승인, 1번 Subagent-Driven으로 구현 시작`으로 A-073 Tasks 1~5의
offline 구현을 승인했다. Task 4는 complete classifier/Hybrid RAG area와 controlled-double,
Ruff/Mypy, version/authority/6W1H evidence를 통합한다. 실제 provider/network runner,
API server, manual chat, `.env`·key·DSN 접근은 금지하고 Task 6 actual은 별도 exact 승인
`A-073 corrective actual 1회 실행 승인` 전 실행하지 않는다.

### Acceptance Criteria

- shared typed builder가 route→intent→pending-slot→identifier→route-shape 순서의 closed
  value-free first-failure stage를 사용한다.
- prompt가 exact five-field route matrix, literal uppercase `NONE`, intent-grouped catalog와
  same-row topic/coverage를 4,096-character guard 안에서 표현한다.
- provider five-string schema, public API/contracts, server ACTIVE/OFFICIAL/source authority,
  DB/data/dependency와 fail-closed 정책은 불변이다.
- area, controlled-double, Ruff format/lint, Mypy, docs/secret/diff gate의 실제 결과를 기록한다.
- application/prompt/tests/docs만 승인된 값으로 전진하고 구현 노트와 INDEX를 동기화한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 plan/Subagent-Driven 실행을 승인하고 Codex Task 1~4 에이전트가 구현·검증했다. Task 4 controller가 stale fixture 범위 확장을 승인했다. |
| When — 언제 | 2026-07-29 KST, D-120 승인 뒤 Tasks 1~4 offline 구현·영역/version 통합 |
| Where — 어디서 | 격리 worktree의 `apps/api` LLM parser/prompt/tests, controlled runner tests와 authority/version 문서 |
| What — 무엇을 | five refined stages, shared typed builder, explicit route matrix, bounded grouped catalog, production-wire oracle, version/권위/6W1H evidence |
| Why — 왜 | D-117의 exact five-key 응답 9건이 broad `ENUM_SHAPE_REJECTED`에서 종료한 prompt ambiguity를 제거하고 재발 시 값 없이 실패 계층을 구분하기 위해 |
| How — 어떻게 | Task별 RED→GREEN, controlled doubles, exact area/quality 명령, manifest allowlist와 D-120 authority synchronization |
| How much — 어느 정도 | A-073 cumulative production 3파일, approved tests와 baseline-stale controlled fixture; final review 뒤 area 397, controlled-double 39, Ruff/Mypy 115; Task 5 root wrapper exact-one invocation 1(aggregate NOT VERIFIED/FAIL), review-wave rerun 0, provider/network call 0, USD 0 |

## 3. 시작 전 상태

- 관련 파일: `classifier_diagnostics.py`, `classifier_contracts.py`, `classifier_prompt.py`,
  세 focused test, `scripts/tests/test_run_hybrid_rag_actual.py`, authority/version documents.
- 기존 동작: D-117은 strict five-string key/type을 통과했지만 9/9가 broad
  `ENUM_SHAPE_REJECTED`였고 accepted/match는 0이었다.
- 발견한 충돌/부채:
  Task 4 첫 controlled-double run에서 baseline `32344a5`부터 존재한 evaluation mock 한 건이
  provider-wire `pending_slot`을 JSON null로 반환해 `38 passed, 1 failed`였다. A-072 이후 wire는
  exact string `"NONE"`만 허용하므로 production은 의도대로 fail closed했다.
- Git 상태: clean base `34cc45d1132a5316a1e5e31c2adb3c77d4338aef`에서 Task 4를 시작했다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| D-120 | 인간 승인 | Tasks 1~5 plan과 Subagent-Driven 구현 시작 | 승인됨 | offline code/test/docs 허용 |
| T4-SCOPE-001 | 내부 범위 | controlled evaluation mock이 plan allowlist에 없었음 | controller가 test-only `null→"NONE"` 한 줄을 승인 | production/schema 동작 영향 0, cumulative scope에 test 파일 1개 추가 |
| A-073-ACTUAL | 인간 승인 | Task 6 corrective actual exactly once | 미승인 | provider/network/API actual 0 유지 |
| Internal-guard | 구현 가정 | governed 20 topic + 256-char prompt가 complete guard 안이어야 함 | final review correction 뒤 실제 4,067, margin 29 | 확장 시 재예산 필요 |

## 5. 설계 결정과 대안

### 선택

provider schema는 exact five required strings로 유지하고, 하나의 shared builder가 canonical과
provider wire의 typed validation authority가 되게 했다. prompt에 complete route matrix와
literal `NONE`, grouped catalog를 넣고 diagnostics는 값 없는 fixed stage만 observer/report에
전달한다.

### 이유

provider request shape를 다시 확장하지 않고 D-117의 가장 유력한 semantic ambiguity만 제거한다.
응답이 계속 실패해도 body나 잘못된 실제 값을 보관하지 않고 route/intent/pending/identifier/
route-shape 계층만 aggregate할 수 있다.

### 고려했지만 선택하지 않은 대안

- provider schema enum/pattern/conditional: 지원 근거와 4xx 위험이 불명확해 보류.
- single `choice_id`: 승인된 five-key wire를 교체하는 architecture 변경이라 기각.
- invalid value 자동 trim/번역/보정: fail-closed와 closed vocabulary를 훼손하므로 기각.
- stale mock 수용을 위한 production JSON-null 허용: exact provider wire를 약화하므로 기각.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `classifier_diagnostics.py` | five refined terminal stages 추가, legacy generic stage 보존 | historical compatibility와 value-free 원인 계층화 |
| `classifier_contracts.py` | shared typed builder와 fixed validation precedence | canonical/provider parser의 단일 권위 |
| `classifier_prompt.py` | explicit route matrix, literal `NONE`, grouped catalog, dynamic same-row example | D-117 semantic ambiguity 제거와 4,096 guard 보존 |
| approved focused/runner tests | parser precedence, prompt grammar/bounds, nine production-wire oracles, aggregate order/non-retention | offline 회귀 |
| `test_upstage_classifier_evaluation.py` | baseline-stale mock의 `pending_slot: null`을 exact `"NONE"`으로 한 줄 교정 | current provider wire와 controlled double 일치 |
| version/authority/docs | D-120, A-073 status, four approved version axes와 6W1H evidence | 활성 문서 충돌 제거와 재현성 |

### 데이터 흐름/상태 변화

`SafeQuestion → request-local ACTIVE/OFFICIAL catalog → explicit bounded prompt + existing
five-string schema → provider bytes(process memory only) → exact key/type/NONE normalization →
shared typed builder → catalog check → ClassifierDecision 또는 deterministic fail-closed`다.
질문·provider body·잘못된 value·status detail·exception·key·DSN은 observer/report/DB에 전달하지
않는다. 공식 fact/source/office와 저장 여부는 계속 서버가 소유한다.

### 오류·빈 상태·롤백

invalid route, intent, pending slot, identifier, route combination은 precedence상 첫 fixed stage
하나만 emit한다. observer 오류는 accepted decision/fallback을 바꾸지 않는다. empty/ineligible
catalog와 4,096 초과 complete prompt는 transport/ledger 전에 fail closed한다. rollback은
Task 4 evidence commit과 Tasks 3→1 commits를 역순 revert하고 manifest를
`0.12.3/0.4.2/2.1.6/2.30.5`로 복원한다. DB/data rollback은 없다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Product spec | 2.6.0 | 2.6.0 | 불변 |
| Repository guidance | 1.7.10 | 1.7.10 | 불변 |
| Application | 0.12.3-structured-classifier-wire | 0.12.4-classifier-wire-diagnostics | shared builder와 refined runtime stages |
| Web | 0.8.0-guided-chat | 0.8.0-guided-chat | 불변 |
| API | 4.0.0-draft | 4.0.0-draft | 공개 shape 불변 |
| Shared contracts | 1.0.0 | 1.0.0 | 불변 |
| DB schema | 0.5.0-local | 0.5.0-local | 불변 |
| Official data | 0.1.0-initial.2 | 0.1.0-initial.2 | 불변 |
| Mock data | 0.0.0-not-populated | 0.0.0-not-populated | 불변 |
| Prompt set | 0.4.2-exact-five-key-schema | 0.4.3-explicit-route-matrix | complete route/cross-field grammar |
| Test suite | 2.1.6-structured-classifier-wire | 2.1.7-classifier-wire-correction | refined-stage/prompt/wire regressions |
| Documentation | 2.30.5 | 2.30.6 | D-120와 offline evidence checkpoint |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| Task 1 contracts RED→GREEN | PASS | collection RED → 77 passed in 0.13s | Task 1 report, commit `7e90258` |
| Task 2 prompt RED→GREEN | PASS | 11 fail/12 pass RED → 24 passed final; governed 20+256 = 4,064 | Task 2 report, commits `fcd89d8`/`d6a494d` |
| Task 3 transport/runner | PASS | 61 + 26 passed | Task 3 report, commit `34cc45d` |
| complete classifier/Hybrid RAG area command | PASS | final 386 in 3.97s, skip 0, known Starlette warning 1 | terminal evidence |
| controlled-double command — initial | expected RED | 38 passed, 1 failed in 1.29s | baseline-stale JSON-null mock |
| controlled-double command — after minimal fixture fix | PASS | final 39 in 1.52s, skip 0 | exact `"NONE"`, provider/network 0 |
| API Ruff format/lint/Mypy + direct runner Ruff — initial | mixed FAIL/PASS | format 1 file FAIL; lint import order 1 FAIL; Mypy 115 PASS; direct checks PASS | terminal evidence |
| brief-prescribed formatter + import-only Ruff fix | PASS | formatter 1 file; import error 1 fixed | terminal evidence |
| final API Ruff format/lint/Mypy + direct runner Ruff | PASS | 115 formatted/lint clean; Mypy 115; direct file 1 | terminal evidence |
| `python -B scripts/check_repository_docs.py` | PASS | repository documentation check passed | terminal evidence |
| `check_secret_patterns.ps1 -RepositoryRoot .` | PASS | exit 0; findings/value output 0 | terminal evidence |
| `git diff --check` | PASS | whitespace errors 0; working-copy line-ending warning 1 | terminal evidence |
| final review exact vocabulary focused RED→GREEN | PASS | expected RED 1 failed → 4 passed; complete prompt 4,067, margin 29 | final review terminal evidence |
| final review temporary precedence mutation | PASS | expected RED 2 failed/8 passed → restore GREEN 10 passed | mutation uncommitted, production order restored |
| final review runner non-retention focused | PASS | 2 passed | selected 20 questions, exact case-table columns, forbidden markers |
| final review classifier/Hybrid RAG area | PASS | 397 passed, skip 0, known Starlette warning 1, 3.96s | final review terminal evidence |
| final review controlled-double | PASS | 39 passed, skip 0, 1.51s | provider/network call 0 |
| final review Ruff/Mypy | PASS | API 115 formatted/lint clean; Mypy 115; direct runner test format/lint clean | final review terminal evidence |

### 미실행 검증과 이유

- `scripts/run_hybrid_rag_actual.py`, provider/network/API server/manual chat: Task 6 exact-one
  approval이 없고 Task 4 범위 밖이라 실행 0.
- `.env`, key, DSN, provider report: 접근·수정·생성 0.
- DB reset/seed/migration, official/mock data, public/remote/deploy: 변경도 권한도 없어 미실행.
- Task 5 `scripts/verify.ps1 -Offline` root wrapper: 별도 Task 5의 exact one-shot gate이므로
  Task 4에서 실행하지 않았다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: PII masking 선행과 raw 질문 DB/로그 비보관을 유지했다. 질문/provider body/invalid
  value/status detail/exception/key/DSN 저장·출력 추가 0.
- Security: closed enum/identifier/route invariant와 current catalog 검증을 약화하지 않았고
  observer/report는 fixed enum aggregate만 받는다.
- Accessibility: public response와 Web UI 변경 0.
- Performance/cost: timeout 3초, retry 0, concurrency 1, max output 128, attempt/cost ledger와
  4,096 guard 불변. provider/network actual call 0, 비용 USD 0.

## 10. 데이터와 출처 영향

- 공식 데이터: `0.1.0-initial.2` 불변, 파일/DB write 0.
- mock/AI 생성: mock version 불변, provider 생성물·report 0.
- schema/lineage: API/shared/DB schema와 source/office binding 불변.
- verified date: 2026-07-29 KST.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- A-073 code/prompt/test/area integration은 offline 완료됐지만 실제 Upstage 품질 PASS 증거가
  아니다. Task 5 root wrapper는 정확히 한 번 호출했지만 실행 도구가 14.056초에 timeout 124를
  반환해 최종 stdout과 wrapper exit code를 회수하지 못했다. detached PID가 이후 종료된 것은
  확인했으나 aggregate는 `NOT VERIFIED/FAIL`이며 PASS로 승격하지 않는다.
- Task 6은 현재 root aggregate가 green이 아니므로 blocked다. 이 차이를 별도 인간 결정으로
  해결한 뒤에도 exact `A-073 corrective actual 1회 실행 승인` 없이는 provider call 0이어야 한다.
- controlled-double 첫 RED는 production 결함이 아니라 baseline-stale provider-wire mock이었다.
  current exact string contract를 약화하지 않고 test fixture 한 줄만 교정했다.
- 20-topic/256-character prompt의 final review correction 뒤 margin이 29자이므로 future
  prompt/catalog 증가는 재예산이 필요하다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- `_build_classifier_decision_with_stage`가 enum coercion과 `ClassifierDecision` constructor를
  연결하며 별도 route-matrix validator를 복제하지 않는다.
- dynamic supported example은 request-local 첫 catalog row를 사용하고 provider catalog는
  intent별 four-column row로 stable하게 직렬화한다.
- legacy `ENUM_SHAPE_REJECTED`는 historical reports용으로 남지만 new parser path는 refined
  stage를 emit한다.

## 13. 인수인계·재현·롤백

### 재현

1. base `34cc45d1132a5316a1e5e31c2adb3c77d4338aef`에서 Task 4 diff를 적용한다.
2. `apps/api`에서 brief의 eight-file area pytest와 Ruff format/lint/Mypy를 실행한다.
3. repository root에서 두 controlled-double pytest와 direct runner Ruff를 실행한다.
4. docs/secret/diff gate와 `git diff --name-status 32344a5...HEAD` scope를 확인한다.
5. provider mode/key를 활성화하거나 actual runner를 실행하지 않는다.

### 롤백

Task 4 evidence commit을 revert한 뒤 `34cc45d`, `d6a494d`, `fcd89d8`, `7e90258`을 역순
revert한다. stale fixture correction만 되돌리려면
`scripts/tests/test_upstage_classifier_evaluation.py`의 `"NONE"`을 기존 JSON null로 복원하되,
그러면 current controlled-double gate가 다시 RED가 됨을 기록한다. DB/data/secret/dependency
rollback은 필요 없다.

### 다음 개발자 시작점

Task 5의 root wrapper one-shot은 이미 소비됐으므로 현재 plan 아래 재실행하지 않는다.
final review fix wave 1은 구현됐지만 final review가 아직 pending이다. root aggregate capture
gap은 인간이 별도로 결정한다. 사용자의 exact Task 6 승인과 root-gate 해소 전에는 D-117
report archive/delete나 provider readiness/actual을 실행하지 않는다.

## 14. 남은 위험·미해결 질문·다음 단계

- 실제 provider가 explicit matrix를 준수하는지는 아직 검증되지 않았다.
- Task 5 root wrapper는 exact-one invocation을 소비했지만 timeout 124로 aggregate가
  `NOT VERIFIED/FAIL`이다. rerun은 0이며 final review와 root-gate capture gap의 인간 결정이
  남아 있다.
- actual에서 rejection이 남으면 refined aggregate만 기록하며 provider body/value를 열람하거나
  자동 재실행하지 않는다.
- current D-117 report와 ADR-0027은 변경하지 않았다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신

## 16. Task 4 review correction round 1

- Review base: `c04804c854997472b1fb107bf5b6c9044e4c1f3a`
- Finding 1: `TEAM_DECISIONS.md`의 D-120 요약이 application/prompt/tests 축의 짧은 값만
  기록하고 documentation `2.30.6`을 누락했다.
- Correction: advanced axes를 manifest와 같은 full labels로 통일했다:
  application `0.12.4-classifier-wire-diagnostics`, prompt_set
  `0.4.3-explicit-route-matrix`, test_suite `2.1.7-classifier-wire-correction`,
  documentation `2.30.6`. 다른 version axis는 수정하지 않았다.
- Finding 2: specification과 이 노트 status가 pending actual의 task number를 생략했다.
- Correction: 둘 다 `Task 5 root/clean-source gate and Task 6 actual pending`을 명시했다.
- Scope: 위 세 문서만 변경했다. D-117, ADR-0027, provider reports, code/contracts/DB/data/
  dependencies는 변경하지 않았고 provider/network/API server/manual chat은 실행하지 않았다.
- Verification:
  `python -B scripts/check_repository_docs.py` PASS,
  `check_secret_patterns.ps1 -RepositoryRoot .` exit 0/findings 0,
  `git diff --check` whitespace errors 0,
  `git status --short`는 위 세 expected document만 modified로 표시했다.
- Rollback: review correction commit 하나를 revert하면 되며 DB/data/secret/dependency rollback은
  필요 없다.

## 17. Task 5 exact-one offline root gate evidence

- 시작 source: `4d4d6ddabf30c3e61c7462a724479b4821aeada7`, 시작 tree clean.
- exact invocation count: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File
  scripts/verify.ps1 -Offline` 1회.
- command transport result: 14.056초 뒤 timeout, exit `124`, captured stdout 0.
- detached process evidence: 원래 wrapper PID `37544`가 계속 실행된 뒤 종료된 것을 확인했다.
  child command line으로 `TEST-ROOT`, `TEST-DATA-SEED`, Web dependency boundary와 `TEST-API`
  진입을 관찰했고 generated contract timestamp도 후속 단계 진입을 보였다. 그러나 최종 stdout과
  wrapper exit code는 회수할 수 없으므로 constituent/aggregate PASS로 해석하지 않는다.
- aggregate result: `NOT VERIFIED / FAIL — execution harness timeout 124`; rerun 0.
- Step 2 immutable checks:
  `python -B scripts/check_repository_docs.py` PASS,
  `check_secret_patterns.ps1 -RepositoryRoot .` exit 0/findings 0,
  `git diff --check` errors 0,
  `git status --short` output 0 before evidence edits.
- provider/network/API server/manual chat/actual runner invocation 0, cost USD 0. D-117 report와
  archives, ADR-0027, product code/tests/contracts/DB/data/dependencies/version axes는 불변이다.
- final independent review는 pending이다. Task 6은 blocked이며, root gate가 별도 인간
  결정으로 해소된 뒤에도 exact future approval
  `A-073 corrective actual 1회 실행 승인`이 필요하다.

## 18. Final review fix wave 1

### 범위와 원인

- final review에서 production prompt의 contiguous provider-intent declaration이
  `MOVE_IN_RESIDENT_REGISTRATION|LOCAL_TAX_GENERAL`만 열거하고
  `CERTIFICATE_ISSUANCE|BULKY_WASTE`를 special follow-up row에만 흩어 둔 결함을 확인했다.
- parser production precedence 자체는
  route→intent→pending-slot→identifier→route-shape→catalog 순서로 이미 맞았다. 기존
  compound coverage가 route-first 한 건뿐이어서 adjacent boundary를 mutation-proof하게
  보강했다.
- controlled runner production report shape는 바꾸지 않고 test-only non-retention 검증만
  모든 selected fixture 질문과 exact approved case-table column으로 확장했다.

### RED/GREEN 증거

| 검증 | 결과 | 의미 |
|---|---|---|
| exact contiguous provider-intent focused RED | expected RED: 1 failed | unchanged production에서 exact vocabulary count가 0임을 확인 |
| minimal prompt correction focused GREEN | 4 passed | prompt vocabulary와 governed 20-topic/256-character transport guard 통과 |
| temporary identifier-before-pending mutation | expected RED: 2 failed, 8 passed | parser와 real `QuestionClassifier` observer가 같은 adjacent precedence break를 검출 |
| mutation restore 뒤 focused precedence | GREEN: 10 passed | production order 복원, five adjacent boundary와 enum-only exactly-once observer 통과 |
| runner aggregate/non-retention focused | GREEN: 2 passed | selected 20개 질문 전수 비보관, exact five case-table columns, forbidden privacy markers 비노출 |

temporary wrong-order mutation은 commit/stage하지 않고 `apply_patch`로 즉시 원복했다.
`classifier_contracts.py`는 final review diff에 포함되지 않는다. final governed
20-topic + 256-character complete-message 길이는 정확히 4,067자, 4,096 guard margin은
29자다. route/topic/coverage/label/approved-example/same-row/exact `NONE`/five-string schema
semantics는 삭제하거나 절단·샘플링하지 않았다.

### Gate와 권한

- Task 5 exact-one root wrapper invocation count는 이미 1로 소비됐고 aggregate는
  `NOT VERIFIED/FAIL`; 이 review wave의 root rerun은 0이다.
- Task 6은 root-gate resolution과 exact
  `A-073 corrective actual 1회 실행 승인` 전까지 blocked다.
- provider/network/API server/manual chat/actual runner 호출 0, 비용 USD 0이다.
- D-117 report, ADR-0027, `.env`, key, DSN, public contracts, Web, DB/migration,
  official/mock data, dependency/package/lockfile와 모든 version axis는 불변이다.
- final review fix 구현은 완료했지만 final independent review는 pending이다.
- final area suite는 397 passed/skip 0(known Starlette warning 1), controlled-double suite는
  39 passed/skip 0이다. API `src tests` Ruff format/check와 Mypy 115, direct runner-test Ruff
  format/check가 PASS했다. 첫 Ruff format check가 changed test 2개를 식별한 뒤 해당 changed
  files만 format하고 final check를 재실행했다.
