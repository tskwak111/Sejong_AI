# Upstage Classifier Explicit Route Matrix and Refined Diagnostics — Written Specification

- Task ID: `A-073-CLASSIFIER-ENUM-SHAPE-CORRECTION`
- Status: Approved — implementation plan Review
- Date: 2026-07-29 KST
- Human authority: 사용자의 `ㅇㅋ 진행해`, `명세 승인`
- Decision authority: D-117, D-118, D-119
- Extends: ADR-0025, ADR-0027, A-071 response-stage diagnostics, A-072 strict five-key wire
- Preserves: provider 전 PII 마스킹, ACTIVE/OFFICIAL-only, server-owned validation·facts·sources,
  질문·provider body·잘못된 field value·status detail·key·DSN 비보관, retry 0,
  deterministic fail-closed fallback

## 1. 문제와 검증된 실패 경계

D-117의 fixed 20 actual은 11개 provider-free와 9개 outbound를 정확히 구분했다. 9개
outbound는 모두 HTTP 2xx, accepted usage, exact five-key와 all-string 검증을 통과했고
`KEY_SET_REJECTED`는 0이었다. 그러나 9개 모두 `ENUM_SHAPE_REJECTED`에서 종료해 accepted
decision과 provider match가 0이었으므로 전체 acceptance는 `FAIL`이다.

현재 parser는 다음 서로 다른 오류를 하나의 broad validation boundary에서
`ENUM_SHAPE_REJECTED`로 합친다.

1. `route`, `intent`, `pending_slot`의 closed enum 불일치
2. `topic_id`, `coverage_id` identifier 형식 불일치
3. enum은 유효하지만 route별 required/forbidden field 조합 불일치

provider body와 잘못된 실제 값을 보관하지 않았으므로 D-117을 사후에 더 세분화할 수 없다.
다만 현재 compact prompt의 `NONE=없음`, 전역 `default=NONE`, 축약 route 문법은 exact ASCII
sentinel과 route별 5필드 조합을 충분히 설명하지 못한다. 이는 가장 유력한 가설이며 실제
원인으로 단정하지 않는다. 이번 수직 흐름은 이 ambiguity를 제거하고, 같은 실패가 남으면
값 없이 정확한 검증 계층만 집계한다.

API key 교체는 해결책이 아니다. 현재 key는 9/9 HTTP 2xx와 usage까지 통과했으며 실패는
response semantic validation 이후에만 발생했다.

## 2. 목표와 비목표

### 2.1 목표

1. prompt에 허용 route, provider intent, pending slot과 route별 exact five-field matrix를
   완전하게 명시한다.
2. nullable wire 값은 exact uppercase ASCII `"NONE"`만 사용하도록 명확히 한다.
3. `SUPPORTED`의 `topic_id`와 `coverage_id`가 같은 request-local catalog row에서 선택되도록
   명시한다.
4. 기존 `ENUM_SHAPE_REJECTED` production branch를 value-free first-failure stage 5개로
   세분화한다.
5. HTTP response당 terminal stage exactly one, observer isolation과 aggregate-only evidence를
   유지한다.
6. offline TDD와 clean-source gate 뒤에만 별도 승인된 exact-one actual을 허용한다.

### 2.2 비목표

- provider response body, 잘못된 enum/identifier, 질문, fixture별 stage, exception,
  status detail, key 또는 DSN 저장·출력
- invalid value를 lowercase/번역/trim/lexical guess로 자동 보정
- provider JSON Schema에 enum, pattern, conditional `oneOf` 또는 동적 catalog ID 추가
- approved five-key provider wire 또는 public `ClassifierDecision` 변경
- 시민 API, Web, DB schema/migration, official/mock data 또는 dependency/package/lockfile 변경
- model, base URL, timeout, retry, concurrency, cap 또는 fallback 정책 변경
- public/remote/free-input actual, automatic retry 또는 automatic merge

## 3. 검토한 접근과 선택

### A. Explicit prompt matrix + refined value-free stages — 선택

provider schema는 existing exact five string key를 유지하고 prompt에 full route matrix를
넣는다. parser는 값을 보관하지 않고 first-failure stage만 더 정확히 emit한다.

- 장점: 가장 가능성 높은 prompt ambiguity를 최소 변경으로 제거한다.
- 장점: 새 provider request-shape 기능을 추가하지 않아 4xx 회귀 위험이 가장 낮다.
- 장점: 실패가 남아도 한 번의 bounded actual로 다음 원인 계층을 알 수 있다.
- 단점: provider가 prompt를 위반할 가능성 자체는 server validation으로 계속 닫아야 한다.

A-072가 기각한 prompt-only exact-key 방식과 다르다. exact key/type은 이미 strict schema가
강제하며, A-073 prompt는 그 내부 enum과 cross-field 의미만 명확히 하는 후속 교정이다.

### B. Provider JSON Schema enum/pattern 추가 — 보류

고정 route/intent/pending 값은 provider 단계에서 더 강하게 제한할 수 있지만, 현재 확인된
Upstage 문서는 required string object와 strict structured output을 뒷받침할 뿐 이번에 필요한
enum·conditional 조합의 exact 지원 범위를 확정하지 못했다. 또한 enum만으로 route별 cross-field
조합과 동적 catalog membership을 완전하게 강제할 수 없다. 이번 단일 교정에 넣지 않는다.

### C. Single `choice_id` wire로 재설계 — 기각

서버가 한 ID를 complete decision으로 매핑하면 cross-field inconsistency가 줄지만 승인된
five-key wire와 parser를 교체하는 큰 변경이다. A안이 실패하더라도 별도 architecture decision
없이는 채택하지 않는다.

## 4. Prompt wire semantics

### 4.1 Closed values

`route`는 다음 다섯 값 중 하나다.

```text
SUPPORTED
NO_TOPIC_MATCH
CIVIC_SCOPE_GAP
NON_CIVIC
NEEDS_FOLLOWUP
```

provider `intent`는 다음 네 supported intent 또는 exact `"NONE"`만 허용한다.

```text
MOVE_IN_RESIDENT_REGISTRATION
CERTIFICATE_ISSUANCE
BULKY_WASTE
LOCAL_TAX_GENERAL
NONE
```

내부/public `UNKNOWN`과 `OUT_OF_SCOPE`는 provider wire intent가 아니다.
`CIVIC_SCOPE_GAP`과 `NON_CIVIC`은 `intent="NONE"`을 사용한다. 시민 응답/fixture의
`OUT_OF_SCOPE`은 provider 출력이 아니라 검증된 route에 대한 서버 후처리 결과다.

`pending_slot`은 다음 다섯 값 또는 exact `"NONE"`만 허용한다.

```text
DOMAIN
TOPIC_CHOICE
CERTIFICATE_KIND
REGION
WASTE_ITEM
NONE
```

`"NONE"`은 영어 단어의 설명이 아니라 exact uppercase ASCII wire token이다.
`없음`, `none`, `null`, `NULL`, 빈 문자열, 공백이 붙은 값과 JSON `null`은 금지한다.
전역 `default=NONE` 문구를 제거하고 각 route row가 모든 필드 값을 직접 지정한다.

### 4.2 Exact five-field route matrix

Prompt는 다음 순서와 의미를 그대로 사용한다.

| Route | `intent` | `topic_id` | `coverage_id` | `pending_slot` |
|---|---|---|---|---|
| `SUPPORTED` | supported intent | same catalog row topic | same catalog row coverage | `NONE` |
| `NO_TOPIC_MATCH` | supported intent | `NONE` | `NONE` | `NONE` |
| `CIVIC_SCOPE_GAP` | `NONE` | `NONE` | `NONE` | `NONE` |
| `NON_CIVIC` | `NONE` | `NONE` | `NONE` | `NONE` |
| `NEEDS_FOLLOWUP` / domain unknown | `NONE` | `NONE` | `NONE` | `DOMAIN` |
| `NEEDS_FOLLOWUP` / topic choice | supported intent | `NONE` | `NONE` | `TOPIC_CHOICE` |
| `NEEDS_FOLLOWUP` / certificate kind | `CERTIFICATE_ISSUANCE` | `NONE` | `NONE` | `CERTIFICATE_KIND` |
| `NEEDS_FOLLOWUP` / region | supported intent | `NONE` | `NONE` | `REGION` |
| `NEEDS_FOLLOWUP` / waste item | `BULKY_WASTE` | `NONE` | `NONE` | `WASTE_ITEM` |

Prompt는 JSON object 하나만 반환하고 explanatory prose, Markdown, 추가 key를 금지한다.
최소 두 예시는 `SUPPORTED`와 all-`NONE` route의 의미를 보여준다.

`SUPPORTED` example은 고정 ID를 넣지 않는다. 매 request의 eligible `TopicCatalog`를 stable
public-id order로 정렬해 첫 행을 선택하고, 그 한 행의 exact `intent`, `topic_id`,
`coverage_id`로 동적으로 구성한다. 따라서 example과 selectable catalog가 drift하지 않는다.
empty 또는 부적격 catalog에서는 example을 만들거나 provider를 호출하지 않고 fail closed한다.

```json
{
  "route": "CIVIC_SCOPE_GAP",
  "intent": "NONE",
  "topic_id": "NONE",
  "coverage_id": "NONE",
  "pending_slot": "NONE"
}
```

두 번째 exact JSON은 `CIVIC_SCOPE_GAP`의 all-`NONE` 조합을 보여준다. production prompt의
dynamic `SUPPORTED` example도 same-row membership와 4,096 guard 검증 대상이다. prompt에
새 행정 사실이나 source를 추가하지 않는다.

### 4.3 Bound and failure

- configured masked-question max 1,024와 governed catalog max 20, approved example max 2를
  유지한다.
- provider-only catalog는 exact intent별로 묶고 각 row에
  `topic_id`, `coverage_id`, `coverage_label`, approved example 최대 2개를 보존한다.
  이 표현에서 중복되는 `service_name`만 생략하며 public record와 공식 데이터는 바꾸지 않는다.
- actual-eligible 경계인 governed 20-topic catalog와 256-character safe question의 complete
  prompt는 기존 4,096-character upper bound를 통과해야 한다.
- configured question max 안이더라도 complete message가 4,096을 넘으면 기존 guard가
  provider 호출 전에 fail closed한다. 질문이나 catalog를 자르거나 축약해 통과시키지 않는다.
- rule matrix와 catalog를 절단·샘플링하지 않는다.
- bound를 만족하지 못하면 provider를 호출하지 않고 기존 deterministic fallback으로 닫는다.

## 5. Refined value-free diagnostics

### 5.1 Closed terminal stages

`ClassifierResponseStage`에 다음 fixed enum을 추가한다.

```text
ROUTE_ENUM_REJECTED
INTENT_ENUM_REJECTED
PENDING_SLOT_ENUM_REJECTED
IDENTIFIER_SHAPE_REJECTED
ROUTE_SHAPE_REJECTED
```

historical report compatibility를 위해 `ENUM_SHAPE_REJECTED` enum과 과거 count는 유지한다.
새 parser path는 generic stage 대신 위 refined stage 중 하나를 emit한다.

### 5.2 First-failure precedence

exact five-key/all-string과 exact `NONE` normalization 뒤 다음 순서로 검사한다.

1. route enum
2. provider intent vocabulary
3. pending-slot enum
4. non-null topic/coverage identifier syntax
5. route별 field combination과 slot/intent compatibility
6. request-local catalog membership
7. accepted

하나의 response에 여러 오류가 있어도 가장 먼저 실패한 closed stage 하나만 emit한다.
observer signature는 계속 `Callable[[ClassifierResponseStage], None]`이며 값, subreason,
exception 또는 payload를 받지 않는다.

### 5.3 External failure contract and evidence

- public `parse_classifier_decision()` 실패는 계속
  `ValueError("CLASSIFIER_DECISION_INVALID")` 하나다.
- `QuestionClassifier.classify()` 반환은 계속 `ClassifierDecision | None`이다.
- observer failure는 accepted decision과 시민 fallback을 바꾸지 않는다.
- runner/report/stdout은 stage별 aggregate count만 기록한다.
- fixture ID와 stage, 질문과 stage, provider value와 stage를 연결해 저장하지 않는다.
- D-117 current report와 archived historical reports는 수정하지 않는다.

### 5.4 Single validation authority

canonical parser와 provider wire parser는 wire representation만 각각 검사·정규화하고,
그 다음에는 하나의 shared typed decision-builder를 사용한다.

1. shared builder가 route enum → provider intent vocabulary → pending enum → identifier syntax를
   fixed precedence로 변환한다.
2. 성공한 typed values로 기존 `ClassifierDecision(...)`을 생성한다.
3. `ClassifierDecision`의 기존 invariant가 route별 field combination과 slot/intent compatibility의
   단일 runtime authority다. 생성 실패만 `ROUTE_SHAPE_REJECTED`로 매핑한다.
4. canonical stage parser와 provider wire stage parser는 같은 refined stages와 builder를 쓴다.
   public canonical wrapper는 기존 generic exception만 노출한다.

route matrix를 별도 production validator에 복제하지 않는다. direct
`ClassifierDecision(...)` invalid-combination rejection과 두 parser의 같은 stage 결과를
회귀 테스트한다.

## 6. Runtime data flow

```text
raw citizen question
→ deterministic policy/PII gate
→ masked SafeQuestion
→ request-local ACTIVE/OFFICIAL catalog
→ explicit route-matrix prompt + existing strict five-string schema
→ Upstage response content (process memory only)
→ exact key/type check
→ exact NONE normalization
→ refined first-failure enum/identifier/route-shape validation
→ current catalog validation
→ ClassifierDecision 또는 None
→ existing grounding/source binding 또는 deterministic storage-safe fallback
```

모델은 답변 사실, source, office, 저장 여부, candidate eligibility를 결정하지 않는다.
실패 stage가 더 자세해져도 시민 응답이나 DB 저장 정책은 바뀌지 않는다.

## 7. TDD와 검증

### 7.1 Prompt RED/GREEN

1. 전역 `default=NONE`, 한국어 sentinel 번역과 ambiguous shorthand가 없다.
2. exact route, provider intent, pending-slot vocabulary가 모두 존재한다.
3. matrix의 각 row가 five fields를 완전하게 지정한다.
4. `CIVIC_SCOPE_GAP`/`NON_CIVIC`은 nullable 네 필드 모두 `NONE`이다.
5. `SUPPORTED`는 same catalog row의 topic/coverage와 pending `NONE`을 사용한다.
6. 9개 actual subset oracle을 provider wire JSON으로 직렬화해 production parser가 수용한다.
7. public/fixture `OUT_OF_SCOPE` semantics가 provider wire
   `CIVIC_SCOPE_GAP + intent NONE`을 거쳐 server 후처리되는 경계를 검증한다.
8. actual-eligible 20-topic/256-character prompt가 4,096 guard를 통과하고, 이를 넘는 complete
   message는 provider 호출 전에 fail closed한다.

### 7.2 Parser/observer RED/GREEN

1. invalid route, intent, pending slot이 서로 다른 closed stage를 emit한다.
2. invalid topic/coverage identifier는 value reflection 없이 identifier stage를 emit한다.
3. valid enum의 invalid route combination은 route-shape stage를 emit한다.
4. fixed precedence와 HTTP response당 exactly-one을 검증한다.
5. public generic exception과 fail-closed return을 회귀 검증한다.
6. observer에는 closed enum 외 value가 도달하지 않는다.
7. legacy `ENUM_SHAPE_REJECTED`는 historical compatibility를 유지하지만 새 parser에서
   emit되지 않는다.
8. canonical/provider parser가 shared builder를 사용하고 direct constructor의 invariant가
   유지되는지 검증한다.

### 7.3 Runner and area gate

- report field order와 refined aggregate counters
- fixture/question/provider body/status/secret/value non-retention
- request-local deterministic example row의 same-row membership와 empty-catalog fail-closed
- classifier contracts, prompt, Upstage transport, diagnostics와 actual-runner focused tests
- Hybrid RAG synthetic UAT 48, official example 57, classifier fixture 60
- relevant service/local composition tests
- Ruff format/lint, Mypy
- repository docs, secret-pattern, protected-input, bundle and diff checks

DB, Web, migration, official data와 dependency가 바뀌지 않으므로 해당 제품 파일을 수정하지
않는다. 최종 integration 전에 root gate를 한 번 실행하고, environment-only failure는 PASS로
바꾸지 않고 정확히 기록한다.

## 8. Corrective actual gate

이번 설계 승인과 이후 offline implementation 승인은 provider actual 승인이 아니다.
다음 조건을 모두 충족한 뒤 사용자의 exact-one 승인을 별도로 받는다.

- approved implementation plan 완료
- focused/area/root gate 결과 기록
- clean committed source SHA
- D-117 current report를 byte-preserving dated archive로 복사하고 source/archive SHA-256
  일치를 확인
- archive 확인 뒤 standard current report path가 absent인 상태에서만 network 허용
- fixed content-pinned 20, selected 20, skip 0
- expected provider-free 11, outbound 최대 9
- privacy/policy outbound 0
- retry 0, concurrency 1, VAT 포함 USD 0.20 pre-reservation cap
- question/provider body/status detail/key/DSN/wrong value retention 0

성공 기준은 outbound 9개의 HTTP 2xx, usage, terminal stage reconciliation과 accepted
decision/provider match 9다. 실패하면 refined aggregate를 기록하고 자동 재실행하지 않는다.
새 report는 성공·실패와 관계없이 덮어쓰지 않는다.

## 9. 버전과 계약 영향

현재 written-spec checkpoint:

| Axis | Before | After |
|---|---|---|
| Documentation | `2.30.3` | `2.30.4` |
| Application | `0.12.3-structured-classifier-wire` | unchanged |
| Prompt | `0.4.2-exact-five-key-schema` | unchanged |
| Tests | `2.1.6-structured-classifier-wire` | unchanged |
| API/contracts/Web/DB/data/dependencies | current | unchanged |

승인된 plan 구현 목표:

| Axis | Before | Target |
|---|---|---|
| Application | `0.12.3-structured-classifier-wire` | `0.12.4-classifier-wire-diagnostics` |
| Prompt | `0.4.2-exact-five-key-schema` | `0.4.3-explicit-route-matrix` |
| Tests | `2.1.6-structured-classifier-wire` | `2.1.7-classifier-wire-correction` |

target version은 written specification 승인과 implementation plan에서 다시 대조한다.
public API, shared contract, DB schema, official/mock data와 dependency axis는 바뀌지 않는다.
written specification 승인과 implementation plan Review publication은 documentation
`2.30.5`이며 runtime 목표값은 아직 적용하지 않는다.

## 10. 인수 기준

1. prompt가 exact route matrix와 literal `NONE`을 모호성 없이 제공한다.
2. approved five-key all-string provider schema와 public parser contract는 유지된다.
3. malformed response를 자동 보정하거나 성공으로 승격하지 않는다.
4. five refined stage가 값 없이 fixed precedence와 exactly-once로 집계된다.
5. 시민 fallback, PII/retention, ACTIVE/OFFICIAL과 server-owned source 경계가 유지된다.
6. focused/area/root verification과 self-review가 기록된다.
7. code/network/provider actual은 written spec과 plan 승인 전 0이다.
8. actual은 별도 exact 인간 승인 없이는 실행하지 않는다.

## 11. 롤백과 복구

- prompt correction과 refined diagnostics implementation commit만 revert하면
  `0.12.3/0.4.2/2.1.6` runtime으로 복귀한다.
- DB/data migration 또는 seed rollback은 존재하지 않는다.
- refined stage를 추가해도 historical D-117 report와 legacy enum은 삭제하지 않는다.
- local provider mode를 비활성화하면 기존 deterministic/template fallback만 사용한다.
- 실제 correction이 실패해도 자동으로 schema B나 single-choice C로 전환하지 않는다.

## 12. References

- D-117, D-118, A-073
- D-119
- ADR-0025, ADR-0027
- `docs/superpowers/plans/2026-07-29-upstage-classifier-explicit-route-matrix-and-refined-diagnostics.md`
- `docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md`
- `docs/superpowers/specs/2026-07-28-upstage-classifier-strict-five-key-wire-design.md`
- `docs/superpowers/specs/2026-07-28-upstage-classifier-value-free-response-stage-diagnostics-design.md`
- `docs/implementation-notes/IMP-20260729-001-a-072-corrective-actual-evidence-closeout.md`
- `docs/implementation-notes/IMP-20260729-002-a-072-api-key-replacement-diagnosis.md`
