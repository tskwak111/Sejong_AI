# 관측성 정책

## 목표

오류·지연·품질을 진단하되 질문 원문과 개인정보를 관측 시스템에 보내지 않는다.

## 허용 로그/메트릭

- request_id
- route, method, status code
- intent, answer_status, fallback_reason
- source_count와 source ID
- latency, timeout, retry count
- provider name/model identifier
- provider run attempt count, cap outcome, token usage와 price-snapshot 기반 aggregate cost
- selected region(읍면동)
- candidate/audit state transition IDs
- is_test/mock/source label

위 목록은 제품 단계 전체에서 구조화된 도메인 event/metric으로 사용할 수 있는 최대 범위다.
현재 Phase 1 HTTP transport log는 다음 네 필드만 허용한다.

```text
request_id   # 서버가 생성한 UUID
method       # 제한된 HTTP method
path         # FastAPI route template, 미매칭은 <unmatched>
status       # HTTP status code
```

transport log에는 intent·source·region·provider·DB 정보도 넣지 않는다. 후속 도메인 event는
질문 없는 별도 schema와 테스트가 생긴 뒤에만 위 최대 목록의 필드를 사용할 수 있다.

## 금지

- raw/masked question을 일반 application log에 출력
- 전체 answer text
- provider request/response body
- API key, Authorization header, cookies
- DB connection string
- chat context token, decoded claim, context signing secret

masked_question은 failed_questions 도메인 저장소에만 보관하고 일반 logger에는 넣지 않는다.

## 현재 구현

- request body·query·raw path·header·cookie·Authorization·client IP를 읽는 logging middleware를
  사용하지 않는다.
- Uvicorn request-line access log와 raw ASGI trace log는 query·raw path·client 정보 노출
  가능성 때문에 disabled+non-propagating이며 실행 명령에도 `--no-access-log`를 사용한다.
- `uvicorn.error`의 INFO 미만 protocol record와 고정 WebSocket INFO protocol record는
  client·query 정보가 포함될 수 있어 버린다. INFO startup과 일반 error record는 유지하며,
  exception record는 generic message로 치환하고 args·traceback·exception text·stack을 제거한다.
- WebSocket은 현재 제품 범위 밖이므로 공식 Uvicorn 명령에서도 `--ws none`으로 비활성화한다.
- application exception은 safe 500 metadata 한 줄을 기록한 뒤 다시 전달한다. 정상 완료 및
  일반 `Exception` 경로의 HTTP 요청은 정확히 한 줄, lifespan/websocket scope는 0줄이다.
  프로세스 중단과 `CancelledError` 같은 `BaseException` 경로는 요청당 한 줄 보장 밖이다.
- bundle scanner는 build 시 materialize된 `.next/static`, app HTML/RSC, pages HTML만 검사한다.
  동적 RSC/HTML live response와 Pages `_next/data/*.json` runtime 경로는 보증하지 않으며,
  WEB-CHAT/DEV-001D에서 live-response sentinel gate를 추가한다. 로컬 secret/bundle scanner의
  전체 범위와 한계는 `SECURITY.md` 및 `docs/07_SECURITY_PRIVACY.md`를 따른다. 이 검사는 외부
  인프라 log 설정 검토를 대체하지 않는다.

## KPI 출처 라벨

- EVENT: 실제 비식별 이벤트 집계
- EVALUATION: 표본/회귀 테스트
- MOCK: UI 시연용

대시보드는 라벨을 숨기지 않는다.

## 경보 후보

- source-less SUCCESS > 0
- self-approval attempt > 0
- PII test leak > 0
- provider timeout rate
- p95 latency
- retention deletion failures
- provider outbound attempt/cost cap violation
- context token/storage leak sentinel
