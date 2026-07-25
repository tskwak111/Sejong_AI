# API와 계약 관리

## 원칙

- `contracts/openapi-v1.yaml`이 HTTP 계약의 단일 초안이다.
- 프론트와 백엔드가 각자 타입을 손으로 중복 정의하지 않는다.
- 계약 변경은 영향 분석, 테스트, 버전, 구현 노트를 동반한다.
- breaking change는 인간 승인과 ADR이 필요하다.
- source metadata는 서버가 결합한다.
- API spec revision은 `3.2.0-draft`다. SUCCESS/FOLLOWUP/5개 사유별 FALLBACK,
  `PRIVACY_UNRESOLVED` 고정 문구, HTTPS 전용 출처·기관 링크, local/private admin 성공·오류
  envelope를 OpenAPI·standalone schema·Pydantic·생성 TypeScript가 같은 fixture로 검증한다.
- SUCCESS에만 required `answer_mode=GENERATED|TEMPLATE`가 있다. `GENERATED`는 provider draft를
  strict 검증한 뒤 서버가 ACTIVE/OFFICIAL record의 공식 fact·source·office를 materialize한 결과이고,
  `TEMPLATE`은 disabled/default, timeout, transport, schema, ID 또는 fact-drift 실패 때의 전체
  결정론적 공식 template이다. 두 mode 모두 서버 결합 출처를 유지하며 provider는 source/office/fact를
  생성하거나 변경할 수 없다.

## 대화 문맥 계약

- `ChatRequest.session_id`는 제거했다. optional nullable `context_token`은 최대 2048자의 signed opaque value다.
- 첫 요청은 token 누락/null을 허용한다. 만료·위변조·미지원 token은 401/403이 아니라 문맥 없는 새 요청으로 처리한다.
- `ChatResponse.context_token`은 required nullable이다. SUCCESS/FOLLOWUP은 새 token을 반환할 수 있고 FALLBACK은 반드시 null이다.
- token TTL은 15분이며 현재 탭 메모리에만 둔다. 서버 DB/session/log와 local/session storage, IndexedDB, cookie, URL에는 저장하지 않는다.
- 현재 request의 유효한 `selected_region`이 token과 충돌하면 현재 request가 우선한다. token은 인증·권한·출처·ACTIVE KB 검증에 사용하지 않는다.

## 권장 엔드포인트

```text
GET  /health
GET  /ready
POST /api/v1/chat
GET  /api/v1/offices
GET  /api/v1/admin/failed-questions
GET  /api/v1/admin/failed-questions/{id}
PATCH /api/v1/admin/failed-questions/{id}/reason
POST /api/v1/admin/kb-candidates
POST /api/v1/admin/kb-candidates/{id}/submit
PATCH /api/v1/admin/kb-candidates/{id}/review
GET  /api/v1/admin/quality-summary
```

## 데모 역할 전달

MVP에서 실제 인증 대신 검증 가능한 역할 분리를 위해 다음 헤더를 사용할 수 있다.

```text
X-Demo-Actor-Id: OPERATOR-LOCAL-001 | PM-LOCAL-001
X-Demo-Role: OPERATOR | APPROVER
```

`X-Demo-Actor-Id`는 local fixture의 `OPERATOR-LOCAL-001` 또는 `PM-LOCAL-001`만 사용한다. 이는 운영 인증이 아니며 loopback/local test 시연에서만 허용한다. 초기 public 환경에서는 `/admin`과 `/api/v1/admin/*`를 비활성화한다. 향후 공개 관리자 시연은 별도 승인된 서버측 gate, deny-by-default DB 권한/RLS, CORS/CSRF 검증을 함께 갖춘 뒤에만 허용한다.

## Chat retry 경계

- `POST /api/v1/chat`는 선택적 UUID `Idempotency-Key` header를 받는다. 같은 논리적 Web 재시도는 같은 key를 유지하며, 매 HTTP 요청의 correlation `request_id`와는 별개다.
- local/private DB에는 domain-separated HMAC request digest, 독립 claim token, 5분 lease와
  엄격히 검증된 안전한 구조화 응답만 저장한다. LLM-003의 `GENERATED` summary도 이
  제한된 24시간 중복 방지 응답에는 포함될 수 있으나 원문·마스킹 질문·prompt·provider body·
  context token·correlation ID·IP·기기 식별자는 저장하지 않는다.
- 동일 key/동일 digest의 완료 결과는 replay하며, digest 충돌은 값 없는 422, 유효 lease의 진행 중 요청은 retryable 503이다. 행의 논리 TTL은 24시간이고 startup 및 최대 60초 주기 purge 실패 시 readiness를 닫는다.

## 오류 모델

정책 폴백과 transport/system 오류를 구분한다.

- `INSUFFICIENT_GROUNDING`, `PERSONAL_LOOKUP`, `LEGAL_JUDGMENT`, `OUT_OF_SCOPE`는 정상 정책 결과이므로 HTTP 200 `ChatResponse/FALLBACK`이다.
- provider timeout·invalid JSON이 있어도 ACTIVE KB와 결정론적 template으로 안전한 답변을 만들 수 있으면 HTTP 200이다.
- 필수 분류·검색·근거 검증·응답 조립이 불능이고 안전 대체도 없을 때만 HTTP 503을 반환한다.
- HTTP 200 `ChatResponse.answer_status`에는 `SYSTEM_ERROR`가 없다. 503 요청의 비식별 interaction event에는 내부 상태로 `SYSTEM_ERROR`를 기록할 수 있다.

503은 correlation/request ID와 단일 공개 code를 반환한다. 원문 질문, 내부 provider/DB 이름, stack, provider body, 비밀값을 오류 메시지나 로그에 포함하지 않는다.

```json
{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "잠시 후 다시 시도해 주세요.",
    "request_id": "7d444840-9dc0-11d1-b245-5ffdce74fad2",
    "retryable": true
  }
}
```

공개 code는 안정성을 위해 `SERVICE_UNAVAILABLE` 하나로 유지하고, `PROVIDER_TIMEOUT`, `DATABASE_UNAVAILABLE` 같은 원인은 질문 없는 내부 구조화 로그에서만 구분한다.
