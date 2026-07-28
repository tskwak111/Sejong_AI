# Upstage Classifier Value-Free Response-Stage Diagnostics — Written Specification

- Task ID: `A-071-RESPONSE-STAGE-DIAGNOSTICS`
- Status: Approved — TDD implementation authorized
- Date: 2026-07-28 KST
- Human authority: 사용자 `ㅇㅋ 구현해`, 후속 `명세 승인, 빠르게 구현 ㄱㄱ`
- Decision authority: D-107 후속 D-108
- Extends: ADR-0027, `CHAT-HYBRID-RAG-001`
- Preserves: 질문·provider body·status detail·key·DSN 비보관, provider 전 PII 마스킹,
  ACTIVE/OFFICIAL-only, server-owned facts/sources, retry 0, fail-closed fallback

## 1. 문제와 목적

D-107의 single-variable corrective actual은 closed classifier prompt에 명시적 `JSON만`
지시를 복원한 뒤 같은 fixed subset을 실행했다. 그 결과 9 outbound 모두 HTTP 2xx와
strict usage를 반환해 D-106의 9/9 HTTP 4xx request-validation 거절은 해소됐다.

그러나 production `QuestionClassifier`는 아래 모든 오류를 시민 경로에서 안전하게 `None`으로
합친다.

```text
HTTP response
→ envelope
→ usage
→ choice
→ finish reason
→ message/content
→ JSON
→ exact five keys
→ field types
→ enum/route shape
→ current catalog membership
```

D-107에서는 9건 모두 strict decision accepted 0이었지만 provider body를 보관하지 않았으므로
어느 단계가 원인인지 더 단정할 수 없다. 이번 수직 흐름은 실제 시민 동작이나 fallback을
바꾸지 않고, 각 response가 마지막으로 도달한 **고정 enum 단계 한 개**만 aggregate evidence로
남겨 다음 교정이 추측이 되지 않도록 한다.

## 2. 목표와 비목표

### 2.1 목표

1. production classifier와 동일한 parser 경로에서 value-free terminal stage를 한 번만 관찰한다.
2. actual report에는 단계명별 count만 기록하고 질문·응답·예외 문자열을 기록하지 않는다.
3. public parser의 성공 결과와 generic `CLASSIFIER_DECISION_INVALID` 실패 계약을 유지한다.
4. observer 유무나 observer 자체 오류가 시민 응답과 classifier decision을 바꾸지 않게 한다.
5. TDD와 offline controlled responses로 모든 stage와 exactly-once invariant를 검증한다.
6. clean committed source에서 승인된 PII-free fixed 20을 정확히 한 번 실행한다.

### 2.2 비목표

- provider response body, choice, generated JSON, status detail 또는 exception text 저장
- 질문별 response stage 공개
- prompt, token 상한, model, base URL, timeout, retry, concurrency 또는 비용 cap 동시 변경
- 시민 공개 API, shared contract, DB, migration, official/mock data 변경
- retry 추가, 자동 corrective call, public/remote/free-input provider 활성화
- strict decision을 느슨하게 수락하거나 invalid enum/topic을 lexical fallback으로 성공 처리

## 3. 검토한 접근

### A. Production parser의 typed optional observer — 선택

parser가 고정 `ClassifierResponseStage` enum 한 개를 optional observer에 전달한다.
`QuestionClassifier.classify()`의 외부 반환형은 계속 `ClassifierDecision | None`이다.

- 장점: 실제 runtime과 진단이 동일한 분기·검증을 사용하므로 drift가 없다.
- 장점: observer가 문자열·body·예외를 받을 수 없는 타입 경계를 만들 수 있다.
- 단점: production 내부 parser와 constructor에 additive optional 진단 경계가 생긴다.

### B. Actual runner가 response를 별도로 재파싱 — 기각

- 장점: production code 수정이 적다.
- 단점: runner와 runtime의 validator가 갈라져 실제 실패 단계를 잘못 분류할 수 있다.
- 단점: 같은 body를 두 parser가 다루며 보안·유지보수 표면이 늘어난다.

### C. 오류 코드 또는 provider content를 로그에 출력 — 기각

- 장점: 빠르게 사람이 확인할 수 있다.
- 단점: 질문·provider content 비보관 원칙과 metadata-only logging 경계를 깨뜨릴 수 있다.
- 단점: exception/status detail이 key·payload와 결합될 위험이 있다.

## 4. 구성요소와 책임

### 4.1 `classifier_diagnostics.py`

새 내부 모듈은 값이 고정된 enum과 observer protocol만 소유한다.

```python
class ClassifierResponseStage(str, Enum):
    HTTP_REJECTED = "HTTP_REJECTED"
    ENVELOPE_REJECTED = "ENVELOPE_REJECTED"
    USAGE_REJECTED = "USAGE_REJECTED"
    CHOICE_REJECTED = "CHOICE_REJECTED"
    FINISH_REASON_REJECTED = "FINISH_REASON_REJECTED"
    MESSAGE_REJECTED = "MESSAGE_REJECTED"
    CONTENT_REJECTED = "CONTENT_REJECTED"
    JSON_REJECTED = "JSON_REJECTED"
    KEY_SET_REJECTED = "KEY_SET_REJECTED"
    FIELD_TYPE_REJECTED = "FIELD_TYPE_REJECTED"
    ENUM_SHAPE_REJECTED = "ENUM_SHAPE_REJECTED"
    CATALOG_REJECTED = "CATALOG_REJECTED"
    ACCEPTED = "ACCEPTED"
```

observer 입력에는 위 enum 외의 값이 없다. transport/timeout은 HTTP response가 없으므로 기존
`provider_transport_no_response_count`가 계속 소유하며 가짜 response stage를 만들지 않는다.

### 4.2 `classifier_contracts.py`

closed decision parser를 다음 두 경계로 분리한다.

- 내부 diagnostic parser: `ClassifierDecision` 또는 terminal validation stage를 반환한다.
- 기존 public parser: 내부 결과를 감싸고 실패 시 항상 기존
  `ValueError("CLASSIFIER_DECISION_INVALID")`만 반환한다.

구분 기준은 다음과 같다.

| Stage | 의미 |
|---|---|
| `JSON_REJECTED` | UTF-8 JSON object로 decode할 수 없음 |
| `KEY_SET_REJECTED` | exact `route,intent,topic_id,coverage_id,pending_slot` 다섯 key가 아님 |
| `FIELD_TYPE_REJECTED` | nullable string field의 JSON type이 허용 범위 밖 |
| `ENUM_SHAPE_REJECTED` | route/intent/pending-slot enum 또는 route별 null/필수 조합 위반 |
| `CATALOG_REJECTED` | SUPPORTED decision의 current topic·intent·coverage membership 불일치 |
| `ACCEPTED` | closed decision과 current catalog validation 모두 통과 |

payload나 JSON value는 diagnostic 결과에 포함하지 않는다.

### 4.3 `upstage_classifier.py`

HTTP envelope부터 decision parser까지 동일한 terminal-stage mapping을 수행한다.
`QuestionClassifier` constructor에 optional observer를 추가하되 기본값은 `None`이다.

```python
QuestionClassifier(
    *,
    settings: UpstageClassifierSettings,
    client: httpx.AsyncClient,
    ledger: ProviderAttemptLedger,
    response_stage_observer: Callable[[ClassifierResponseStage], None] | None = None,
)
```

규칙:

1. 실제 HTTP response 하나당 terminal stage를 최대 한 번 emit한다.
2. observer가 없으면 현재 동작과 동일하다.
3. observer 예외는 삼키고 원래 decision/fallback을 바꾸지 않는다.
4. status code가 2xx가 아니면 `HTTP_REJECTED`다.
5. envelope·usage·choice·finish reason·message/content는 각각 고정 stage로 끝난다.
6. response content나 exception은 observer에 전달하지 않는다.

### 4.4 `run_hybrid_rag_actual.py`

runner는 enum count만 가지는 `_ResponseStageRecorder`를 생성해 classifier observer에 연결한다.
report에는 다음을 추가한다.

- `provider_response_stage_total`
- 위 13개 enum 각각의 snake-case count

aggregate invariant:

```text
sum(stage counts) == provider_response_stage_total
provider_response_stage_total == provider_response_count
provider response가 없는 transport case는 stage total에 포함하지 않음
```

기존 per-fixture 표에는 stage를 추가하지 않는다. fixture ID와 response stage 결합을 피하고
전체 aggregate만 남긴다.

## 5. 데이터 흐름과 보안

```text
PII-free fixed fixture
→ existing redaction/policy gate
→ existing bounded catalog request
→ Upstage HTTP response (process memory only)
→ production parser
→ ClassifierDecision | None
                  ↘ fixed enum terminal stage
                     → in-memory Counter
                     → aggregate report count
```

- body는 기존 parser가 처리하는 process memory 밖으로 복사·직렬화하지 않는다.
- observer는 enum만 받으므로 질문·provider content를 기술적으로 전달할 수 없다.
- report allowlist에는 고정 metric name과 integer count만 추가한다.
- stdout도 기존 safe field allowlist만 사용한다.
- DB, application log, trace, screenshot, error tracker write는 0이다.
- key presence boolean 외 key value는 읽거나 출력하지 않는다.

## 6. 오류와 fail-closed 경계

- stage recorder가 없거나 실패해도 classifier의 기존 decision/fallback은 동일하다.
- invalid provider response는 계속 `None`이며 시민에게 내부 stage를 노출하지 않는다.
- stage invariant가 깨지면 actual report acceptance는 FAIL이고 재실행하지 않는다.
- report write 또는 secret/protected-input preflight가 실패하면 network 전에 중단한다.
- actual 실패 뒤 prompt/schema/token을 즉석 수정하거나 두 번째 호출을 하지 않는다.

## 7. TDD와 검증

### 7.1 RED/GREEN 단위 테스트

controlled `httpx.MockTransport` response로 아래를 각각 한 건씩 검증한다.

- non-2xx
- invalid envelope
- invalid/missing usage
- empty/invalid choice
- non-stop finish reason
- invalid message
- blank/non-string content
- invalid JSON
- wrong key set
- wrong field type
- invalid enum/route shape
- invalid catalog membership
- accepted decision

각 테스트는 다음을 동시에 확인한다.

```text
decision은 기존 계약대로 반환 또는 None
observer count는 정확히 1
observer value는 expected enum
response/question/provider body는 observer와 report에 없음
```

public `parse_classifier_decision()`의 generic ValueError와 observer exception isolation도
별도 회귀 테스트로 고정한다.

### 7.2 Runner/report 테스트

- 모든 enum count가 고정 순서로 report에 한 번씩 나타난다.
- total invariant와 response count 일치를 검증한다.
- 질문·payload·provider content sentinel·key·DSN이 stdout/report에 0이다.
- actual acceptance는 기존 9 accepted decisions/matches 조건을 완화하지 않는다.

### 7.3 집중 gate

- classifier contracts/prompt/transport/security tests
- actual runner tests
- Ruff check/format, Mypy
- repository docs, secret scan, diff check

전체 Web/DB/official-data gate는 변경 영역이 아니므로 actual source commit 전 반복하지 않는다.

## 8. Exact-one actual gate

written specification과 실행계획 승인 뒤에만 실행한다.

1. D-107 current report를
   `archive/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL-20260728-D107-2XX-DECISION-REJECT-FAIL.md`
   로 보존한다.
2. code/test/runner/version을 commit하고 clean source SHA를 고정한다.
3. secret/protected-input/fixture hash/profile/report-absence preflight를 network 없이 검증한다.
4. fixed 20만 선택한다.
5. expected provider-free 11, outbound 9, privacy/policy outbound 0을 유지한다.
6. `solar-pro3`, 3초, retry 0, concurrency 1, 80/100/160, USD 0.20을 유지한다.
7. actual command는 정확히 한 번만 실행한다.
8. 성공/실패와 stage counts를 기록하고 어떤 결과라도 재실행하지 않는다.
9. process-scoped mode 종료 뒤 ignored `.env` false/false와 lock 0을 확인한다.

## 9. 버전 계획

written specification checkpoint:

- documentation `2.29.4 → 2.29.5`
- application/prompt/test/API/DB/data/dependency 불변

구현 완료 목표:

- application `0.12.1-bounded-hybrid-rag → 0.12.2-response-stage-diagnostics`
- test suite `2.1.4-json-mode-regression → 2.1.5-response-stage-diagnostics`
- documentation은 구현·actual evidence patch로 별도 증가
- prompt set `0.4.1-json-mode-instruction` 유지
- Web/API/shared contract/DB/official/mock data/dependency 유지

## 10. 롤백과 인수인계

- production 내부 진단 변경은 구현 commit을 revert한다.
- actual report는 감사 증거이므로 삭제하거나 덮어쓰지 않고 archive한다.
- rollback 뒤 classifier는 observer 없이 기존 `ClassifierDecision | None` 동작으로 돌아간다.
- DB/data migration rollback은 없다.
- 다음 개발자는 A-071 stage aggregate만으로 단일 후속 가설을 세우며 provider body를 요구하거나
  여러 prompt/token 변수를 동시에 바꾸지 않는다.

## 11. 완료 기준

- written spec과 실행계획 승인
- every stage RED→GREEN과 existing classifier behavior 회귀 PASS
- observer enum-only/exactly-once/exception-isolated
- report aggregate invariant와 forbidden-value 0
- clean committed exact source에서 actual 정확히 1회
- retry 0, cost ≤ USD 0.20, key/DSN/body/question 저장 0
- decision·ambiguity·version·TASKS·implementation note 동기화
- 결과가 FAIL이면 그대로 기록하고 다음 실제 호출을 다시 인간 gate로 닫음
