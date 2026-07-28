# Upstage Classifier Strict Five-Key Wire — Written Specification

- Task ID: `A-072-CLASSIFIER-EXACT-KEY-CORRECTION`
- Status: Approved / implemented offline Tasks 1~5; provider actual pending D-117
- Date: 2026-07-28 KST
- Human authority: `Q-LLM-014=A`, `설계 1부 승인`, `설계 2부 승인`
- Decision authority: D-111~D-114
- Extends: ADR-0025, ADR-0027, A-071 response-stage diagnostics
- Preserves: provider 전 PII 마스킹, ACTIVE/OFFICIAL-only, server-owned decision validation,
  facts/sources/offices, 질문·provider body·status detail·key·DSN 비보관, retry 0,
  fail-closed fallback

## 1. 문제와 목적

A-071 actual은 fixed 20개 중 deterministic provider-free 11개와 outbound 9개를 정확히
구분했다. outbound 9개는 모두 HTTP 2xx, strict usage와 terminal stage까지 도달했지만 전부
`KEY_SET_REJECTED`로 끝났다. 즉 인증·모델 접근·전송·JSON object 생성은 동작하지만 provider가
서버가 요구하는 다음 exact key set을 반환하지 않았다.

```text
route, intent, topic_id, coverage_id, pending_slot
```

현재 request의 `response_format={"type":"json_object"}`는 JSON object만 보장하고 정확한 key
이름·필수 여부·추가 필드 금지를 강제하지 않는다. 동시에 축약 prompt의 `I`, `T`, `C`, `P`가
출력 key로 해석될 여지가 있다. 서버는 승인된 closed contract를 느슨하게 수용할 수 없으므로
9건 모두 안전하게 폐기했고 시민 경로는 기존 fallback을 사용했다.

이번 수직 흐름은 Upstage provider-only wire가 exact five-key object를 만들도록 official strict
`json_schema`를 사용하고, 공식 지원이 불명확한 nullable union 대신 모든 필드를 string으로
고정한다. nullable 의미는 exact `NONE` sentinel로 표현하고 서버가 기존 내부 `None`으로
정규화한다.

## 2. 목표와 비목표

### 2.1 목표

1. provider request에서 exact five-key, required string, 추가 필드 금지를 강제한다.
2. provider-only `NONE`을 기존 nullable domain value로 정규화한다.
3. canonical provider-neutral parser의 JSON `null` 계약을 유지한다.
4. 기존 route/intent/shape/current catalog validation을 한 권위로 재사용한다.
5. response-stage observer의 fixed enum-only, exactly-once 경계를 유지한다.
6. prompt에서 canonical full field names와 sentinel 규칙을 명확히 한다.
7. TDD와 offline controlled responses로 정상·오류·회귀를 검증한다.
8. clean committed source 뒤 별도 승인받은 경우에만 fixed 20 actual을 한 번 실행한다.

### 2.2 비목표

- 시민 공개 API, shared contract, DB schema/migration 또는 official/mock data 변경
- 모델이 답변·행정 사실·출처·기관·보관·candidate eligibility를 생성하거나 결정
- invalid enum/topic/coverage를 느슨하게 수용
- provider schema에 동적 ACTIVE catalog ID를 enum으로 복제
- vector DB, embedding, 새 production dependency 또는 package/lockfile 변경
- timeout, retry, concurrency, cap, model 또는 base URL 동시 변경
- provider body, 질문, status detail, exception, key 또는 DSN 저장·출력
- public/remote/free-input provider 활성화

## 3. 검토한 접근과 선택

### A. Strict string schema + exact `NONE` sentinel — 선택

Upstage strict `json_schema`로 exact five-key string object를 요구한다. nullable 의미는 exact
`NONE`으로 표현하고 provider-only parser가 기존 내부 `None`으로 바꾼다.

- 장점: 공식 문서가 명시한 string/object/required/additionalProperties/strict 범위 안에서
  exact key를 강제한다.
- 장점: nullable union 지원 여부로 인한 새 4xx 위험을 피한다.
- 장점: public/internal domain contract는 바뀌지 않는다.
- 단점: provider-only normalization 경계와 sentinel regression test가 필요하다.

### B. JSON Schema nullable union — 기각

`["string", "null"]`을 사용하면 wire가 domain shape와 더 비슷하지만 조사한 Upstage 공식
지원 타입 목록에서 null/union이 명확하지 않았다. A-070에서 request-shape 4xx를 경험했으므로
새 unsupported schema 요소를 추가하지 않는다.

### C. Prompt-only exact example — 기각

변경량은 작지만 provider가 exact key를 지키도록 강제할 수 없다. D-111의 prompt-only
`json_object` actual이 exact key set에서 9/9 실패했으므로 acceptance 근거가 없다.

## 4. Provider wire contract

### 4.1 Response format

`QuestionClassifier`는 다음 구조와 동일한 fresh object를 각 request payload에 넣는다.

```json
{
  "type": "json_schema",
  "json_schema": {
    "name": "sejong_classifier_decision",
    "strict": true,
    "schema": {
      "type": "object",
      "properties": {
        "route": {"type": "string"},
        "intent": {"type": "string"},
        "topic_id": {"type": "string"},
        "coverage_id": {"type": "string"},
        "pending_slot": {"type": "string"}
      },
      "required": [
        "route",
        "intent",
        "topic_id",
        "coverage_id",
        "pending_slot"
      ],
      "additionalProperties": false
    }
  }
}
```

규칙:

- schema object는 호출마다 새로 만들어 mutable request 간 오염을 방지한다.
- property와 required field는 canonical five-key 한 집합을 공유해 drift를 막는다.
- schema는 field type과 exact key만 강제한다.
- route/intent/pending-slot enum과 topic/coverage membership은 서버가 검증한다.
- schema에 질문, service name, source, office, official URL 또는 동적 KB ID를 넣지 않는다.

### 4.2 Sentinel

`NONE`은 exact uppercase ASCII 다섯 글자만 sentinel이다.

| Field | `NONE` | Normalized value |
|---|---:|---|
| `route` | 금지 | 없음; closed route string 필수 |
| `intent` | 조건부 허용 | `None` |
| `topic_id` | 조건부 허용 | `None` |
| `coverage_id` | 조건부 허용 | `None` |
| `pending_slot` | 조건부 허용 | `None` |

`none`, `Null`, `NULL`, `NONE `, 빈 문자열과 JSON `null`은 sentinel이 아니다. wire의 모든
field는 string이어야 하므로 JSON `null`, number, boolean, object와 array는
`FIELD_TYPE_REJECTED`다.

### 4.3 Valid examples

SUPPORTED:

```json
{
  "route": "SUPPORTED",
  "intent": "MOVE_IN_RESIDENT_REGISTRATION",
  "topic_id": "KB-MOVE-01",
  "coverage_id": "MOVE_IN_OVERVIEW_APPLICATION",
  "pending_slot": "NONE"
}
```

NO_TOPIC_MATCH:

```json
{
  "route": "NO_TOPIC_MATCH",
  "intent": "CERTIFICATE_ISSUANCE",
  "topic_id": "NONE",
  "coverage_id": "NONE",
  "pending_slot": "NONE"
}
```

NON_CIVIC:

```json
{
  "route": "NON_CIVIC",
  "intent": "NONE",
  "topic_id": "NONE",
  "coverage_id": "NONE",
  "pending_slot": "NONE"
}
```

NEEDS_FOLLOWUP:

```json
{
  "route": "NEEDS_FOLLOWUP",
  "intent": "BULKY_WASTE",
  "topic_id": "NONE",
  "coverage_id": "NONE",
  "pending_slot": "WASTE_ITEM"
}
```

## 5. 구성요소와 책임

### 5.1 `classifier_prompt.py`

- `JSON만`, canonical five-key 이름과 exact `NONE` 규칙을 명시한다.
- `I`, `T`, `C`, `P`, `∅`, `n`처럼 출력 key로 오인할 수 있는 축약을 제거한다.
- route별 field 조합을 full field names로 표현한다.
- 기존 masked question, governed catalog, approved example 최대 2개와 input upper bound를
  유지한다.

### 5.2 `upstage_classifier.py`

- 기존 `json_object`를 strict response-format builder 결과로 교체한다.
- response content를 provider-only wire parser에 전달한다.
- 기존 model `solar-pro3`, max output 128, timeout 3초, retry 0, concurrency 1,
  cost/attempt ledger를 변경하지 않는다.
- HTTP response마다 existing `ClassifierResponseStage`를 최대 한 번 emit한다.
- observer 오류와 모든 provider failure는 기존처럼 `None`으로 닫는다.

### 5.3 `classifier_contracts.py`

두 entry point를 분리하되 한 validation helper를 공유한다.

1. canonical parser:
   - 기존 JSON `null` nullable contract를 유지한다.
   - 기존 public `parse_classifier_decision()` failure는 계속
     `ValueError("CLASSIFIER_DECISION_INVALID")`다.
2. provider wire parser:
   - exact five keys와 all-string type을 확인한다.
   - nullable 4필드의 exact `NONE`을 내부 `None`으로 바꾼다.
   - normalized values를 기존 closed decision/shape/catalog validation에 전달한다.

provider wire parser의 존재 때문에 canonical parser가 `"NONE"`을 허용해서는 안 된다.
provider-specific sentinel은 transport 경계 밖으로 확산하지 않는다.

## 6. 데이터 흐름

```text
raw citizen question
→ deterministic validation/PII masking/policy gate
→ SafeQuestion + request-local ACTIVE/OFFICIAL catalog
→ canonical full-name prompt + strict response_format
→ Upstage response content (process memory only)
→ provider wire parser
→ exact key/all-string check
→ exact NONE normalization
→ existing route/intent/shape/catalog validation
→ ClassifierDecision 또는 None
→ existing grounding/source binding 또는 storage-free fallback
```

서버는 모델이 제안한 `topic_id`와 `coverage_id`를 현재 request-local catalog에서 다시 찾는다.
없는 topic, intent 불일치, coverage 불일치와 inactive/non-official record는 성공할 수 없다.

## 7. 오류·관찰·fail-closed 규칙

| Terminal stage | 조건 |
|---|---|
| `JSON_REJECTED` | UTF-8 JSON object로 decode 불가 |
| `KEY_SET_REJECTED` | exact canonical five-key가 아님 |
| `FIELD_TYPE_REJECTED` | wire field 중 하나라도 string이 아님 |
| `ENUM_SHAPE_REJECTED` | sentinel normalization 뒤 enum 또는 route별 조합 위반 |
| `CATALOG_REJECTED` | SUPPORTED topic/intent/coverage가 current catalog와 불일치 |
| `ACCEPTED` | normalization과 closed validation 모두 통과 |

- invalid response value를 stage, exception, log, report 또는 stdout에 넣지 않는다.
- response body·status detail·질문·key·DSN은 저장하지 않는다.
- fixed enum observer는 HTTP response당 terminal stage 하나만 받는다.
- observer가 실패해도 decision과 시민 fallback은 바뀌지 않는다.
- timeout/transport처럼 HTTP response가 없는 경우 기존 no-response aggregate만 사용한다.
- malformed/invalid provider output을 lexical success로 조용히 바꾸지 않는다.
- hidden retry, automatic second corrective call과 process counter reset을 금지한다.

## 8. TDD와 검증

### 8.1 RED/GREEN focused tests

1. request payload가 strict schema와 정확히 일치한다.
2. required/property key set이 canonical five-key와 같다.
3. `additionalProperties=false`이며 모든 provider field가 string이다.
4. schema에 question/source/dynamic catalog data가 없다.
5. prompt가 full canonical names와 `NONE`을 사용하고 old shorthand를 포함하지 않는다.
6. worst-case 20-topic prompt가 기존 4,096 upper bound를 넘지 않는다.
7. provider wire parser가 각 valid route shape를 수용한다.
8. nullable 4필드의 exact `NONE`만 `None`으로 정규화한다.
9. route `NONE`, JSON null, 유사 sentinel, 누락·추가 key와 non-string field를 거절한다.
10. invalid enum/shape와 current catalog mismatch를 거절한다.
11. canonical parser는 기존 JSON null을 계속 수용하고 string `"NONE"`을 거절한다.
12. response observer는 HTTP response마다 terminal stage를 정확히 한 번만 받는다.
13. observer 오류가 accepted decision/fallback을 바꾸지 않는다.
14. retry 0, attempt/cost accounting과 response body non-retention을 회귀 검증한다.

### 8.2 Area gate

- classifier contracts, prompt, transport, response-stage diagnostics tests
- Hybrid RAG synthetic UAT 48개
- official example suite 57개
- classifier fixture suite 60개
- relevant service/local composition tests
- Ruff, format check, Mypy
- repository docs, secret-pattern, protected-input, bundle, diff checks

DB migration, Web, official data와 package/lockfile이 바뀌지 않으므로 해당 영역의 수정은 없다.
최종 integration 전에는 기존 repository gate를 한 번 실행한다.

### 8.3 Corrective actual gate

offline implementation과 area/root gate가 통과하고 clean source commit이 만들어진 뒤 별도
사용자 승인을 받아야 한다.

- content-pinned fixed 20
- expected provider-free 11, outbound 최대 9
- skip 0
- retry 0, concurrency 1
- VAT 포함 USD 0.20 pre-reservation cap
- provider body/question/status detail/key/DSN retention 0
- success: 9 outbound HTTP 2xx·usage·terminal stage total, accepted decision/provider match 9
- failure: report를 FAIL로 고정하고 자동 재실행하지 않음

## 9. 버전과 계약 영향

구현 완료 시 목표:

| Axis | Before | Target |
|---|---|---|
| Application | `0.12.2-response-stage-diagnostics` | `0.12.3-structured-classifier-wire` |
| Prompt | `0.4.1-json-mode-instruction` | `0.4.2-exact-five-key-schema` |
| Tests | `2.1.5-response-stage-diagnostics` | `2.1.6-structured-classifier-wire` |
| API | `4.0.0-draft` | unchanged |
| Shared contracts | `1.0.0` | unchanged |
| DB schema | `0.5.0-local` | unchanged |
| Official data | `0.1.0-initial.2` | unchanged |
| Mock data | `0.0.0-not-populated` | unchanged |
| Dependencies/lockfile | current | unchanged |

documentation version은 written specification, plan, implementation/evidence checkpoint에서
각각 추적한다.
Documentation `2.30.2`는 Tasks 1~5 offline 구현·clean-source review evidence checkpoint다.
root wrapper는 정확히 한 번 실행되어 환경 전용 `PREFLIGHT-UV`에서 FAIL했고 재실행하지
않았으므로 PASS가 아니다. 나머지 constituent/security/scope 검사는 문서화된 skip을 제외하고
PASS했으며 provider actual call/cost는 0/USD 0이다.

## 10. 인수 기준

1. provider request가 approved strict five-key string schema를 사용한다.
2. prompt에 old shorthand가 없고 canonical key와 sentinel 규칙이 명확하다.
3. provider wire와 canonical parser가 분리되고 validation authority는 하나다.
4. exact `NONE` normalization과 모든 invalid sentinel/type/key regression이 통과한다.
5. public API/DB/data/dependency/source binding이 바뀌지 않는다.
6. 질문·provider body·status detail·key·DSN retention이 0이다.
7. focused/area와 root constituent gate가 문서화된 skip을 제외하고 통과한다. root wrapper의
   환경 전용 preflight 실패는 별도 FAIL로 보존하며 constituent PASS로 대체하지 않는다.
8. provider actual은 별도 승인 전 0이며 승인 후 정확히 한 번만 실행한다.

## 11. 롤백과 복구

- offline implementation rollback은 application/prompt/test change commit만 revert한다.
- DB migration/data rollback은 존재하지 않는다.
- strict schema actual이 request-level 4xx를 만들면 FAIL evidence를 보존하고 자동으로
  `json_object` actual을 재실행하지 않는다.
- local runtime은 provider mode를 비활성화하면 기존 deterministic/template fallback으로
  복구된다.
- historical D-105~D-111 reports와 decisions는 수정하거나 덮어쓰지 않는다.

## 12. References

- Q-LLM-014=A, D-111~D-114, A-072
- ADR-0025, ADR-0027
- `docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md`
- `docs/superpowers/specs/2026-07-27-bounded-hybrid-rag-conversation-design.md`
- `docs/superpowers/specs/2026-07-28-upstage-classifier-value-free-response-stage-diagnostics-design.md`
- `docs/implementation-notes/IMP-20260728-012-*` through `IMP-20260728-015-*`
