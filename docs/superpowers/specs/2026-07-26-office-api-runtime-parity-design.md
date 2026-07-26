# OFFICE-API-001 기존 기관 조회 계약의 FastAPI runtime 정합 설계

- 상태: Written Specification Approved / Execution Plan Review
- 작성일: 2026-07-26 KST
- 인간 결정: `Q-API-OFFICES-001=A`
- 기준 commit: `8ebc66b65a67f106b05976112de345a8c849b631`
- 관련 결정: D-026, D-031, D-058, D-078
- 관련 ADR: ADR-0009, ADR-0011, ADR-0019, ADR-0020
- 관련 계약: `contracts/openapi-v1.yaml`의 `GET /api/v1/offices`

## 1. 목적

tracked OpenAPI에는 `GET /api/v1/offices`가 있고 PostgreSQL에는
`app_api.list_offices(text, text)`와 이를 호출하는 typed repository adapter가 있지만,
current default/local FastAPI application에는 해당 route가 없다. 평가자나 계약 소비자가
OpenAPI대로 요청하면 404가 발생하는 상태다.

사용자는 Q-API-OFFICES-001=A로 endpoint를 제거하지 않고 기존 계약대로 runtime에 구현하기로
승인했다. 이 작업은 시민이 선택한 지역과 지원 민원 분야를 OFFICIAL 기관 카드에 연결하는
read-only P1 contract-parity slice다.

## 2. 권위와 이미 확정된 동작

다음은 새로 결정하지 않고 기존 권위를 그대로 구현한다.

- `region`과 `intent` query는 둘 다 required다.
- region은 `아름동`, `도담동`, `조치원읍`만 허용한다.
- intent는 네 supported intent만 허용한다.
- valid filter에 매칭되는 기관이 없으면 HTTP 200 `{"items":[]}`다.
- DB interface는 `data_origin=OFFICIAL`만 반환한다.
- DB 결과는 `public_id`의 C collation 오름차순이다.
- 기관명·주소·전화·지도·출처·확인일은 서버가 DB record에서 결합한다.
- LLM은 호출하지 않고 기관 metadata를 생성하거나 변경하지 않는다.
- public/admin 배포, remote DB, GPS·거리 계산·내장 지도는 이 slice에 포함하지 않는다.

## 3. 승인된 접근과 기각 대안

### 선택: 기존 계약 존치와 runtime 구현

FastAPI에 route를 항상 등록하고 default application은 dependency가 없을 때 fail closed 503을
반환한다. local/private composition은 현재 `PsycopgSejongRepository`와 readiness probe를
주입한다. DB schema/function/seed는 이미 존재하므로 migration을 추가하지 않는다.

### 기각: OpenAPI에서 endpoint 제거

현재 Web이 standalone endpoint를 호출하지 않는다는 장점은 있으나, 이미 문서화된 기관 연결
surface와 생성 타입을 제거해야 한다. SFR-004의 직접 지역 선택 확장성도 낮아져 기각했다.

### 기각: OpenAPI 선언만 유지

코드 변경은 없지만 계약대로 호출하면 404가 발생한다. 평가와 인수인계에서 명백한 drift이므로
기각했다.

## 4. 공개 HTTP 계약

### 요청

```http
GET /api/v1/offices?region=아름동&intent=BULKY_WASTE
```

query는 FastAPI/Pydantic enum으로 검증한다. trim, alias, 임의 문자열 coercion은 허용하지 않는다.

### HTTP 200

```json
{
  "items": [
    {
      "id": "OFFICE-AREUM",
      "region": "아름동",
      "office_name": "아름동 행정복지센터",
      "address": "공식 데이터의 주소",
      "phone": "공식 데이터의 대표번호",
      "opening_hours": "공식 데이터 값 또는 null",
      "map_url": "https://www.sejong.go.kr/office/map",
      "source_title": "공식 출처명",
      "source_url": "https://www.sejong.go.kr/office",
      "last_verified_at": "2026-07-19"
    }
  ]
}
```

- response body는 required `items` 하나를 가진 strict object다.
- 각 item은 기존 `Office` 계약을 재사용한다.
- internal `department_label`은 기존 public `Office` 계약에 없으므로 새로 노출하지 않는다.
- valid no-match는 `items: []`이고 404가 아니다.
- 현재 DB function의 deterministic `public_id` 순서를 보존한다.

### HTTP 422

query 누락, unsupported region, unsupported intent는 global public
`ValidationErrorEnvelope`를 반환한다.

- code: `VALIDATION_ERROR`
- message: `입력값을 확인해 주세요.`
- 입력값, DB category, stack을 body/log에 echo하지 않는다.

### HTTP 503

default app의 closed dependency, readiness false, DB read failure처럼 공식 기관 응답을 안전하게
만들 수 없으면 ADR-0009의 `ServiceUnavailableEnvelope`를 반환한다.

- code: `SERVICE_UNAVAILABLE`
- message: `잠시 후 다시 시도해 주세요.`
- `request_id`, `retryable=true`
- `Retry-After: 30`
- 내부 DB/provider/exception 이름과 query value를 노출하지 않는다.

tracked OpenAPI에는 기존 200에 422와 503을 명시한다. wire-compatible error 명세 추가이므로
API draft는 `3.2.0-draft→3.3.0-draft` minor로 올린다.

## 5. 구성요소 경계

### `contracts/offices.py`

- `OfficeListResponse`만 소유한다.
- 기존 `contracts.chat.Office`를 item type으로 재사용한다.
- strict model이며 `items` 기본값을 두지 않아 route가 항상 명시적으로 반환하게 한다.

### `office/response.py`

- `OfficeRecord | None → Office | None`의 서버 소유 변환을 담당한다.
- 현재 `chat.response._public_office`를 이 모듈의 공개 helper로 이동하고 chat도 같은 helper를
  사용한다.
- source metadata와 URL은 DB record만 사용한다.

### `office/service.py`

- `OfficeRepository` protocol은 기존 `list_offices(region, intent)` 한 메서드만 요구한다.
- `OfficeDirectoryService`는 typed repository 결과를 immutable tuple로 받아 public model로 변환한다.
- `GuardedOfficeDirectory`는 shared readiness probe가 false이면 repository를 호출하지 않고
  unavailable을 반환한다. read 중 database unavailable이면 probe를 unavailable로 표시한다.
- programming error나 contract validation bug를 정상 empty 결과로 숨기지 않는다.

### `api/offices.py`

- `APIRouter(prefix="/api/v1", tags=["offices"])`
- `operation_id="listOffices"`
- default dependency는 항상 fail closed하는 `ClosedOfficeDirectory`다.
- route는 200/422/503 공개 envelope만 조립하며 DB concrete type을 알지 않는다.

### `main.create_app`

- offices router는 default/local 모두 항상 등록한다.
- optional injected `office_directory` seam을 추가한다.
- default app은 route discovery/OpenAPI parity를 제공하지만 실제 read는 503이다.

### `local.create_local_app`

- 기존 repository와 `RepositoryReadinessProbe`를 재사용한다.
- `GuardedOfficeDirectory(probe, OfficeDirectoryService(repository))`를 주입한다.
- 별도 pool, credential, migration, background task를 추가하지 않는다.

## 6. 데이터 흐름

```text
required region + supported intent
  → FastAPI typed validation
  → shared readiness gate
  → PsycopgSejongRepository.list_offices
  → app_api.list_offices(region, intent)
  → OFFICIAL-only / public_id ordered rows
  → typed OfficeRecord
  → server-owned Office mapping
  → OfficeListResponse(items=[Office records])
```

이 경로는 질문 text, PII masker, chat context, event writer, failed question, LLM, idempotency 저장소를
통과하지 않는다.

## 7. 오류와 fail-closed 규칙

| 상황 | 공개 결과 | 내부 처리 |
|---|---|---|
| required query 누락/enum 불일치 | 422 `VALIDATION_ERROR` | repository 호출 0 |
| valid query/no match | 200 `items=[]` | 정상 결과 |
| default dependency | 503 `SERVICE_UNAVAILABLE` | 외부 호출 0 |
| readiness false | 503 `SERVICE_UNAVAILABLE` | office DB read 0 |
| repository DB unavailable/malformed row | 503 `SERVICE_UNAVAILABLE` | probe unavailable |
| unexpected programming error | 테스트 실패/500 | empty·공식 결과로 위장하지 않음 |

safe request logging middleware는 method/path/status/request ID만 남기며 query value를 기록하지
않는 현재 정책을 유지한다.

## 8. 테스트 전략

구현은 TDD RED→GREEN 순서로 진행한다.

1. contract model
   - exact `{"items":[Office records]}`와 `items=[]`
   - internal `department_label` 미노출
2. response mapping
   - 모든 public office metadata가 record와 일치
   - chat response가 같은 helper를 사용해 wire regression 0
3. service
   - typed region/intent 전달
   - deterministic tuple/list conversion
   - readiness false에서 repository 호출 0
   - database unavailable에서 fail closed
4. route
   - success, empty, missing/invalid 422, closed 503, safe body와 Retry-After
5. generated OpenAPI
   - path, `listOffices`, required query enums, 200/422/503 schemas
6. local composition
   - ready repository 실제 injection과 closed fallback
7. shared contracts
   - generator 실행과 generated TypeScript drift 0
8. changed-area gate
   - Ruff, MyPy, full API pytest, contract check, docs/secret/diff checks

DB function·repository adapter·pgTAP는 이미 검증됐으며 migration을 바꾸지 않는다. 실제 local DB
smoke는 구현 closeout에서 비밀·DSN·질문 원문을 출력하지 않고 exact endpoint status/count만
검증한다.

## 9. 버전 계획

| 축 | Before | 구현 완료 목표 |
|---|---|---|
| Application | 0.9.1-grounded-local-chat-evidence | 0.10.0-office-directory-runtime |
| API | 3.2.0-draft | 3.3.0-draft |
| Shared contracts | 0.5.0 | 0.6.0 |
| Test suite | 1.6.1-grounded-actual | 1.7.0-office-directory |
| Documentation | 2.20.5 | spec publication에서 2.20.6, 구현 closeout에서 후속 승격 |
| DB schema | 0.4.0-local | unchanged |
| Official data | 0.1.0-initial.2 | unchanged |
| Prompt set | 0.2.0-grounded-live-chat | unchanged |

Web version은 standalone endpoint 소비가 이번 slice 범위가 아니므로 유지한다.

## 10. 보안·개인정보·비용

- 질문 원문·masked question·PII·IP·device ID 저장/처리 0
- ACTIVE KB·event·failed question·candidate write 0
- OFFICIAL 기관만 반환하고 mock/staging을 차단하는 기존 DB function 재사용
- source title/URL/verified date는 서버가 DB record에서 결합
- LLM/provider call 0, API key 사용 0, 비용 0원
- 새 production dependency 0
- public/remote/admin activation과 배포 변경 0

## 11. 롤백

- 이 slice의 Python router/service/model과 generated contract 변경만 revert한다.
- DB migration·seed·actual data가 없으므로 data rollback은 없다.
- route를 제거할 때는 tracked OpenAPI와 generated TypeScript를 같은 commit에서 이전 상태로
  되돌린다.
- PR은 인간 review 전 Draft로 유지하고 자동 merge하지 않는다.

## 12. 완료 기준

- default/local generated FastAPI OpenAPI에 `GET /api/v1/offices`가 존재한다.
- operation ID, required query, enum과 200/422/503 schema가 tracked OpenAPI와 일치한다.
- ready local repository에서 OFFICIAL matching offices만 deterministic order로 반환한다.
- valid no-match는 `200 items=[]`, unavailable은 safe 503이다.
- invalid input이나 error body/log에 query value, DSN, stack, secret가 없다.
- chat office card wire regression이 없다.
- migration, seed, official/mock data, Web, LLM, dependency 변경이 없다.
- API/unit/static/contracts/docs/secret/diff gate가 통과한다.
- 구현 노트와 INDEX, version manifest가 동기화된다.

## 13. 인간과 AI 책임

### 인간이 알아야 하는 내용

- Q-API-OFFICES-001=A는 기존 endpoint 존치와 runtime 구현을 승인한다.
- 503 응답 명시와 API draft minor version 승격이 포함된다.
- public/remote 배포나 실제 기관 운영 승인은 아니다.
- 구현 PR은 사람이 검토·merge하며 자동 merge하지 않는다.

### AI 내부 구현 세부

- module 이름, dependency override helper, immutable tuple 변환, test fixture 분할은 이 명세와
  wire contract를 지키는 범위에서 자율 처리한다.
