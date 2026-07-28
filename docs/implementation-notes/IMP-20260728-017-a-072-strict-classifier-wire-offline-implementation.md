# IMP-20260728-017 — A-072 strict classifier wire offline implementation

- Date/Time (KST): 2026-07-28T23:13:12+09:00
- Task ID: A-072-CLASSIFIER-EXACT-KEY-CORRECTION
- Type: implementation-provider-offline
- Status: Done — Tasks 1~4 offline implementation; Task 5/D-117 pending
- Author/Agent: Codex main controller + task-scoped implementer/reviewer agents
- Branch: `codex/a-072-strict-classifier-wire`
- Base commit: `5c2d2be70215e528561825cd762bed9932a5c9fd`
- Pre-documentation implementation head: `9c0abb4`
- Related plan/ADR/RFP:
  [approved specification](../superpowers/specs/2026-07-28-upstage-classifier-strict-five-key-wire-design.md),
  [approved plan](../superpowers/plans/2026-07-28-upstage-classifier-strict-five-key-wire.md),
  [ADR-0027](../adr/0027-active-topic-catalog-and-coverage-grounding.md),
  [RFP matrix](../source-of-truth/RFP_MATRIX.md), D-111~D-116

## 1. 사용자 요청과 완료 기준

### 요청

사용자는 `계획 승인, 1번으로 구현 시작`으로 승인된 A-072 Tasks 1~5 중 offline 구현을
Subagent-Driven 방식으로 시작하도록 승인했다. Task 6 실제 Upstage 호출은 별도 exact 승인 전
실행하지 않는다.

### Acceptance Criteria

- provider wire는 정확히 다섯 required string key와 `additionalProperties=false`를 사용한다.
- nullable 4필드의 exact `NONE`만 provider 경계에서 내부 `None`으로 바꾼다.
- canonical JSON-null parser와 server enum/shape/current-catalog 권위를 유지한다.
- prompt는 canonical field names와 `NONE`을 4,096자 guard 안에서 표현한다.
- offline area·controlled-double runner·Ruff·Mypy·문서·secret·diff gate가 통과한다.
- public API/contracts, DB/data, dependency/package/lockfile은 바꾸지 않는다.
- provider/network actual 호출 0, 비용 USD 0을 유지한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 인간 결정자 사용자, Codex controller, Task 1~3 구현 agent, 독립 spec/quality reviewer |
| When — 언제 | 2026-07-28 KST, D-116 승인 뒤 Tasks 1~4 offline 구현 |
| Where — 어디서 | 격리 worktree의 `apps/api` LLM parser/prompt/transport와 authority/version 문서 |
| What — 무엇을 | exact five-key strict schema, provider-only `NONE` normalization, bounded canonical prompt, 회귀·버전·권위 통합 |
| Why — 왜 | D-111 actual의 HTTP 2xx 9건이 `KEY_SET_REJECTED` 9/9로 끝난 exact wire mismatch를 단일 교정하기 위해 |
| How — 어떻게 | TDD RED→GREEN, fresh worker→독립 review→bounded fix loop, controlled doubles와 value-free offline gates |
| How much — 어느 정도 | production 3파일, test 4파일, authority/version/note 문서; area 333 + runner 24 PASS; provider call 0, USD 0 |

## 3. 시작 전 상태

- 관련 파일:
  `classifier_contracts.py`, `classifier_prompt.py`, `upstage_classifier.py`와 각 focused test,
  A-072 spec/plan, ADR-0027, manifest와 source-of-truth.
- 기존 동작: provider request는 loose `json_object`였고 canonical parser는 JSON null을
  기대했다. D-111 actual은 HTTP 2xx/usage 9를 얻었지만 exact key set에서 9/9 거절됐다.
- 발견한 충돌/부채: 첫 area run에서 `tests/test_local.py`의 controlled provider fixture만
  과거 JSON null을 반환해 `332 passed, 1 failed`였다. production 결함이 아니라 stale test
  fixture였고 Task 3 owner가 exact string `NONE`으로 교정했다.
- Git 상태: clean base `5c2d2be`; 격리 branch/worktree에서만 변경했다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| D-116 | 인간 승인 | Tasks 1~5 계획과 Subagent-Driven 구현 시작 | 승인됨 | offline code/test/docs 허용 |
| D-117 | 인간 승인 | fixed 20 corrective actual exactly once | 아직 승인되지 않음 | provider/network 호출 0 유지 |
| Internal-1 | 내부 정합 | plan의 미래 actual 결정 ID가 D-116으로 중복됨 | D-116은 plan 승인, future actual은 D-117로 clerical correction | 동작·계약 영향 0 |

## 5. 설계 결정과 대안

### 선택

provider transport에만 exact five required string key의 strict `json_schema`를 적용하고,
nullable 의미는 exact uppercase `NONE`으로 표현한다. wire parser가 이를 내부 `None`으로
정규화한 뒤 기존 closed validator를 한 번 사용한다.

### 이유

Upstage의 명시된 string/object/required/additional-properties/strict 범위 안에서 key drift를
방지하고, 지원 불명확한 nullable union으로 새 request 4xx를 만들지 않기 위해서다. public/domain
contract와 source/retention 권위는 바뀌지 않는다.

### 고려했지만 선택하지 않은 대안

- JSON Schema nullable union: provider 지원 근거가 불명확해 기각.
- prompt-only exact example: D-111에서 exact key 9/9 실패해 기각.
- invalid key/null을 느슨하게 수용: server closed contract와 fail-closed 원칙을 깨므로 기각.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `classifier_contracts.py` | provider-wire parser, exact `NONE` normalization, shared validation helper | provider sentinel을 canonical/domain 경계 밖으로 격리 |
| `classifier_prompt.py` | canonical five-key/`NONE` positional grammar와 linked compact catalog | 20-topic+256자 입력도 4,096 guard 통과 |
| `upstage_classifier.py` | per-request fresh strict schema와 provider parser 연결 | exact key/type/no-extra transport 강제 |
| focused/local tests | 모든 valid route/shape, invalid key/type/sentinel/catalog, fresh schema, observer/retry/ledger와 stale fixture 교정 | offline 회귀와 fail-closed 보장 |
| authority/version docs | D-116 plan/implementation, D-117 actual gate, 세 승인 버전 축 | 사람·AI 책임과 재현 기준 동기화 |

### 데이터 흐름/상태 변화

`SafeQuestion → bounded canonical prompt + request-local ACTIVE/OFFICIAL catalog → fresh strict
five-key schema → provider bytes → exact key/all-string check → NONE normalization → existing
enum/shape/catalog validation → ClassifierDecision | None`이다. raw 시민 질문은 Upstage에
전달되지 않으며, 별도로 승인된 provider actual에서만 PII-masked `SafeQuestion`을 in-memory
prompt로 전송한다. 질문·prompt·provider 응답 내용은 저장하거나 logging하지 않고 시민
fact/source/office 결합은 계속 서버가 소유한다.

### 오류·빈 상태·롤백

wrong JSON/key/type/enum/shape/catalog은 기존 fixed value-free terminal stage로 닫히며
observer 오류도 시민 decision/fallback을 바꾸지 않는다. rollback은 아래 feature commits를
역순 revert하고 manifest/authority/note commit을 함께 revert한다. DB/data migration은 없다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Product spec | 2.6.0 | 2.6.0 | 불변 |
| Repository guidance | 1.7.10 | 1.7.10 | 불변 |
| Application | 0.12.2-response-stage-diagnostics | 0.12.3-structured-classifier-wire | strict provider parser/schema runtime |
| Web | 0.8.0-guided-chat | 0.8.0-guided-chat | 불변 |
| API | 4.0.0-draft | 4.0.0-draft | 공개 shape 불변 |
| Shared contracts | 1.0.0 | 1.0.0 | 불변 |
| DB schema | 0.5.0-local | 0.5.0-local | 불변 |
| Official data | 0.1.0-initial.2 | 0.1.0-initial.2 | 불변 |
| Mock data | 0.0.0-not-populated | 0.0.0-not-populated | 불변 |
| Prompt set | 0.4.1-json-mode-instruction | 0.4.2-exact-five-key-schema | canonical bounded five-key grammar |
| Test suite | 2.1.5-response-stage-diagnostics | 2.1.6-structured-classifier-wire | strict wire/area regressions |
| Documentation | 2.30.1 | 2.30.1 | 현재 요청은 승인된 세 runtime/test 축만 전진 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| Task 1 contract TDD/final | PASS | final 61 | Task 1 report/review |
| Task 2 prompt TDD/final | PASS | final 17 | Task 2 report/review |
| Task 3 transport/local focused | PASS | final 181 | Task 3 report/fix evidence |
| complete classifier/Hybrid RAG area pytest | 첫 실행 FAIL, 교정 후 PASS | 332 pass/1 fail → 333 pass | terminal evidence, this note |
| `pytest scripts/tests/test_run_hybrid_rag_actual.py -q` | PASS | 24 in 1.79s | controlled doubles; network 0 |
| `ruff format --check src tests` | PASS | 115 files | terminal evidence |
| `ruff check src tests` | PASS | 115 files | terminal evidence |
| `mypy src tests` | PASS | 115 source files | terminal evidence |
| `python -B scripts/check_repository_docs.py` | PASS | repository documentation check passed | terminal evidence |
| `check_secret_patterns.ps1 -RepositoryRoot .` | PASS | findings 0, value output 0 | terminal evidence |
| `git diff --check` | PASS | whitespace errors 0 | terminal evidence |

### 미실행 검증과 이유

- `scripts/run_hybrid_rag_actual.py` 실제 runner 실행: D-117 별도 exact 승인 전 금지.
- public/remote/DB reset/seed/deploy: A-072 범위 밖이며 변경도 없다.
- Task 5 root `verify.ps1`: Task 4 commit 뒤 clean-source gate가 별도로 소유한다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: PII masking 순서를 바꾸지 않았고 질문/provider body/status detail/exception/key/DSN
  저장·출력을 추가하지 않았다. provider actual 0이다.
- Security: exact keys, all-string types, no extra properties와 server current-catalog 재검증으로
  trust boundary를 강화했다. secret value를 읽거나 출력하지 않았다.
- Accessibility: public response/Web UI가 바뀌지 않아 영향 0이다.
- Performance/cost: timeout 3초, max output 128, retry 0, concurrency 1, attempt/cost ledger와
  4,096 prompt guard를 보존했다. 이번 실행 provider/network call 0, 비용 USD 0.

## 10. 데이터와 출처 영향

- 공식 데이터: `0.1.0-initial.2` 불변, 파일/DB write 0.
- mock/AI 생성: mock data 불변, provider 생성물 저장 0.
- schema/lineage: DB/API/shared schema와 lineage 불변.
- verified date: 2026-07-28 KST.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- Tasks 1~4는 offline GREEN이지만 실제 Upstage 품질 PASS 증거가 아니다.
- Task 5 root/clean-source gate 완료 뒤에도 actual은 exact 문구
  `A-072 corrective actual 1회 실행 승인`을 받아 D-117로 기록해야 한다.
- 새 dependency, 공개/remote, DB/data, push/merge 권한은 이 작업에 포함되지 않았다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- `_EXPECTED_KEYS`와 `_CLASSIFIER_FIELDS`가 parser와 schema 내부 drift를 막는다.
- schema builder는 호출마다 새 nested object를 만들어 mutable request 오염을 막는다.
- prompt는 `cat` key와 six-column row를 직접 연결하고 fixed 4,096 estimator를 유지한다.
- stale local controlled fixture 교정은 production behavior를 바꾸지 않는다.

## 13. 인수인계·재현·롤백

### 재현

1. branch `codex/a-072-strict-classifier-wire`, base `5c2d2be`에서 시작한다.
2. `apps/api`에서 area pytest, Ruff format/lint, Mypy를 실행한다.
3. repository root에서 controlled-double actual-runner pytest와 docs/secret/diff gate를 실행한다.
4. provider mode/key를 활성화하거나 actual runner를 직접 실행하지 않는다.

### 롤백

Tasks 1~4 feature/docs commits를 최신부터 역순으로 `git revert`한다. DB rollback, data restore,
secret rotation과 dependency reinstall은 필요 없다. 실제 호출이 없으므로 provider-side 복구도 없다.

### 다음 개발자 시작점

Task 5는 committed clean source에서 root `scripts/verify.ps1`, secret/scope review와 full SHA
기록만 수행한다. 성공하면 멈추고 D-117 exact-one actual 승인을 요청한다.

## 14. 남은 위험·미해결 질문·다음 단계

- strict schema가 actual `solar-pro3`에서 exact five-key를 9/9 반환하는지는 아직 검증되지 않았다.
- Task 5 root wrapper 및 final whole-branch independent review가 남았다.
- D-117 승인 후에도 actual은 정확히 1회만 실행하고 어떤 결과든 즉시 재시도하지 않는다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
