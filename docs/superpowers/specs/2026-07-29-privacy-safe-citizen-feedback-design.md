# 개인정보 안전 시민 피드백 설계

- Status: Approved
- Date: 2026-07-29
- Decision: Q-FEEDBACK-001=A / D-138 / ADR-0029

## 1. 목표

현재 탭 메모리에서만 끝나는 만족/불만족을 실제 local/private 운영 데이터로 연결한다.
분야·사유 `기타`와 최대 300자 상세 의견을 지원하되, 원문·질문·답변은 저장하지 않고 서버가
마스킹한 상세만 30일 보관한다.

## 2. 공개 계약

### `POST /api/v1/feedback`

Request:

```json
{
  "request_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "rating": "DISSATISFIED",
  "category": "OTHER",
  "reason_code": "OTHER",
  "detail": "기타 의견"
}
```

- `rating`: `SATISFIED | DISSATISFIED`
- `category`: 지원 4개 intent 또는 `OTHER`
- `reason_code`: `INACCURATE | NOT_RELEVANT | HARD_TO_UNDERSTAND | WRONG_CONTACT | OTHER`
- `detail`: trim된 1~300자 또는 null
- 만족은 category/reason/detail을 모두 null로 강제한다.
- 불만족은 category와 reason을 필수로 한다.
- `reason_code=OTHER`이면 detail이 필수다.
- 다른 불만족 사유의 detail은 선택이다.

Response `201`:

```json
{
  "request_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  "status": "RECORDED",
  "detail_status": "MASKED"
}
```

`detail_status`: `NOT_PROVIDED | STORED | MASKED`.
같은 `request_id`와 같은 정제 payload는 같은 결과를 반환하고, 다른 payload 재사용은 409다.
마스킹 불능은 `FEEDBACK_PRIVACY_UNRESOLVED` 422, DB 비가용은 값 비노출 503이다.

### `GET /api/v1/admin/feedback-summary`

기존 `X-Demo-Actor-Id`와 `X-Demo-Role` local/private gate를 재사용한다. 응답은 전체·만족·불만족
건수, 만족률, 분야/사유별 건수, 최근 100개 이하의 폐쇄형 메타와 마스킹 상세만 포함한다.

## 3. DB

`app_private.citizen_feedback`은 UUID id, unique `response_request_id`, rating/category/reason,
`masked_detail`, `detail_was_masked`, `created_at`, `detail_expires_at`, `detail_purged_at`만 가진다.
질문·답변·provider·context·raw detail column은 존재하지 않는다.

Capability:

- `app_api.record_citizen_feedback(uuid,text,text,text,text,boolean)`
- `app_api.list_citizen_feedback(integer)`
- `app_api.summarize_citizen_feedback()`
- `app_api.purge_expired_citizen_feedback_detail()`

backend는 table 직접 권한 없이 위 함수만 실행한다. public/anon/authenticated는 실행할 수 없다.
상세 만료는 정확히 생성 후 30일이며 startup/periodic purge 실패는 `/ready`를 닫는다.

## 4. API/service

`FeedbackService`가 Pydantic shape 검증 뒤 `redact_feedback_detail()`을 호출한다. 이 프로필은
질문 마스커와 같은 고정 개인정보 탐지·치환, 이름·상세주소·고위험 숫자·비정상 유니코드 차단을
유지하되, 마스킹된 식별값 뒤에 이어지는 일반 피드백 문장을 질문용 식별값 문법으로 오인하지
않는다. raw detail은 함수 지역변수 밖으로 넘기지 않고 logger·exception·DB model에 포함하지
않는다. 마스킹이 해결되지 않으면 repository를 호출하지 않는다. 기본 앱은 closed recorder를
사용해 503을 반환하며 local app만 `PsycopgSejongRepository`를 주입한다.

## 5. Web

모든 SUCCESS/FOLLOWUP/FALLBACK 카드가 응답 `request_id`를 `FeedbackButtons`로 전달한다.
만족·불만족 모두 실제 transport 완료 후에만 감사 상태가 된다. 실패하면 버튼/입력 상태를 유지하고
재시도 문구를 보여준다. fixture mode는 DB를 쓰지 않는 명시적 in-memory recorder를 사용한다.

불만족 sheet:

- 민원 분야 `기타`
- 불만족 사유 `기타`
- 상세 textarea 최대 300자와 남은 글자 수
- 기타 사유 선택 시 상세 필수
- “개인정보를 입력하지 마세요. 서버에서 한 번 더 가립니다.” 안내
- 기존 focus trap, Escape, focus restore 유지

관리자 첫 화면은 aggregate와 최근 마스킹 의견을 표시하고 원문 복원 기능을 제공하지 않는다.

## 6. 비기능 경계

- 새 production dependency 0
- 외부 LLM 호출 0
- public deploy/remote DB 0
- secret/DSN/질문/답변/raw detail 로그·문서·fixture 0
- 390/430/desktop 반응형과 키보드 접근성 유지
- public 운영 전 signed response proof, abuse rate limit, 인증/RBAC는 별도 인간 승인
