# LLM-003 근거 제한형 Upstage 시민 답변 생성 설계

- 상태: Approved / D-074 implementation In Progress
- 작성일: 2026-07-25 KST
- 결정: Q-LLM-006=B, Q-LLM-007=A, Q-LLM-009=A, Q-LLM-011=C, Q-LLM-012=B
- 관련 결정: D-024, D-045, D-059, D-061, D-065~D-067, D-071, D-072
- 관련 ADR: ADR-0004, ADR-0005, ADR-0006, ADR-0010, ADR-0021, ADR-0022, ADR-0023
- 구현 시작 조건: [후속 실행계획](../plans/2026-07-25-grounded-live-chat-generation.md)에 대한
  사용자 승인 — D-074로 충족

## 1. 배경과 목적

현재 `/api/v1/chat`은 결정론적 분류, ACTIVE/OFFICIAL 검색, 근거 gate와 서버 소유 템플릿으로
안전하게 동작한다. LLM-002의 Upstage `solar-pro3` 합성 평가는 한국어 검수 9건 평균
4.8444/5와 낮은 비용을 확인했지만 strict schema 27/30으로 100% 기준을 충족하지 못해 전체
FAIL이었다. 이 결과는 모델 출력을 그대로 시민 계약으로 신뢰할 수 없음을 뜻하지만, 모든
오류에서 기존 템플릿으로 안전하게 복귀하는 보조 생성기로 사용하는 것까지 금지하지는 않는다.

사용자는 공개 운영이 아닌 local/private 입찰 시연 MVP에서 승인된 공식 KB를 바탕으로 질문에
맞춘 자연스러운 AI 답변을 원한다. 이 설계의 목적은 AI가 답변 표현을 넓히되 행정 사실, 정책
판정과 출처 권위는 넓히지 않는 것이다.

## 2. 범위와 비범위

### 포함

- local/private `/api/v1/chat`의 지원 범위 내 SUCCESS 후보에 대한 Upstage `solar-pro3` 호출
- 마스킹된 시민 질문과 답변에 필요한 최소 ACTIVE/OFFICIAL KB payload
- 질문에 맞춘 전체 구조화 답변 생성 시도
- 서버 발급 fact ID allowlist, strict schema와 사실 일치 검증
- 생성 성공/템플릿 fallback을 구분하는 `answer_mode`
- 8초 timeout, logical attempt 1회, hidden retry 0, concurrency 1
- process당 outbound attempt 30 상한과 durable idempotency 연동
- 공급자 장애·부적합 출력 시 답변 전체 deterministic template fallback
- Web의 접근 가능한 생성 방식 배지와 정적 설명

### 제외

- public/remote 배포 또는 실제 기관 운영에서의 시민 질문 전송
- 분류, PII 판정, 검색, 근거 gate, 후보 적격성, 출처 생성의 LLM 위임
- `FOLLOWUP`, `PRIVACY_UNRESOLVED`, `INSUFFICIENT_GROUNDING`, `PERSONAL_LOOKUP`,
  `LEGAL_JUDGMENT`, `OUT_OF_SCOPE` 또는 시스템 오류에서의 provider 호출
- CANDIDATE, mock, staging, 비공식 KB 전송
- source title, URL, verified date, office 정보의 모델 생성
- 질문·provider request/response·생성 답변의 DB, 파일, 액세스 로그 또는 오류 추적 저장
- Upstage SDK 또는 새 production dependency
- 자동 prompt 튜닝, 자동 재실행, 자동 충전, 잔액 조회

## 3. 승인 결정과 supersession

| 질문 | 확정 | 설계 반영 |
|---|---|---|
| Q-LLM-006 | B | local/private 시민 chat에 Upstage를 연결한다. public/remote는 계속 금지한다. |
| Q-LLM-007 | A | 지원 intent, 마스킹 성공, ACTIVE/OFFICIAL 검색과 근거 충분을 모두 만족할 때만 호출한다. |
| Q-LLM-008 | A였으나 후속 결정으로 대체 | 처음에는 summary만 생성하기로 했지만 Q-LLM-012=B가 전체 구조화 생성 시도로 대체한다. |
| Q-LLM-009 | A | 8초, 1회 attempt, 자동 retry 0. 실패 즉시 전체 template fallback이다. |
| Q-LLM-010 | 승인 설계에 포함 | SUCCESS 응답과 Web에 `GENERATED`/`TEMPLATE` 표시를 제공한다. |
| Q-LLM-011 | C | 마스킹 질문과 최소 ACTIVE KB를 함께 전송해 질문 맞춤 표현을 허용한다. |
| Q-LLM-012 | B | AI가 전체 구조를 제안하되 서버 검증 실패 시 일부 혼합 없이 전체 template로 대체한다. |

D-071의 LLM-002 actual FAIL 증거는 변경하지 않는다. ADR-0022의 “actual 평가를 통과해야 시민
경로를 승인한다”는 판단만 사용자의 새 local/private MVP 결정으로 대체한다. 실제 기관 운영,
public/remote 전송 금지와 서버 소유 출처 원칙은 유지한다.

## 4. 권위와 데이터 흐름

```text
raw question
  → 보수적 PII masking
  → deterministic intent·privacy·policy classification
  → ACTIVE + OFFICIAL retrieval
  → deterministic grounding gate
  ├─ 호출 불가: 기존 FOLLOWUP/FALLBACK/template 응답
  └─ 호출 가능:
       masked question + 최소 KB facts + server-issued fact IDs
       → Upstage solar-pro3 (8초, 1 attempt)
       → strict JSON/schema validation
       → ID allowlist·fact consistency·summary drift validation
       ├─ 실패: 전체 deterministic template SUCCESS
       └─ 성공: 서버가 ID를 공식 fact text로 materialize
                + 서버가 source/office/context를 결합
                → GENERATED SUCCESS
```

서버만 다음을 결정한다.

- `intent`, `answer_status`, `fallback_reason`, `candidate_eligible`
- 검색 대상과 ACTIVE/OFFICIAL 상태
- 공식 절차·서류·수수료·처리기간·담당기관의 원문
- source title, URL, verified date, source identity와 office card
- provider 호출 가능 여부와 최종 fallback

## 5. Provider 호출 자격

다음 조건을 **모두** 만족할 때만 호출한다.

1. 서버 설정이 local/private grounded-chat mode를 명시적으로 활성화했다.
2. provider, exact model, base URL, timeout, cap과 key 검증이 성공했다.
3. PII masker가 `safe_to_use=true`인 마스킹 문자열을 만들었다.
4. deterministic intent가 4개 지원 분야 중 하나다.
5. 최종 정책 결과가 `SUCCESS` 후보이며 FOLLOWUP 또는 fallback reason이 없다.
6. 검색 결과가 `ACTIVE + OFFICIAL`이고 grounding 기준을 통과했다.
7. 답변에 필요한 KB fact가 server-owned allowlist로 직렬화될 수 있다.
8. idempotency claim이 새 실행을 허용하고 process cap 30 미만이다.

다음 경로는 outbound call이 정확히 0이어야 한다.

| 경로 | 결과 |
|---|---|
| PII 미해결 | `PRIVACY_UNRESOLVED` |
| 개인 조회 | `UNKNOWN/PERSONAL_LOOKUP`, text/event/failed row 미저장 |
| 법적 판단 | `UNKNOWN/LEGAL_JUDGMENT`, text/event/failed row 미저장 |
| 지원 범위 밖 | `OUT_OF_SCOPE`, 질문 text 미저장 |
| 모호 질문 | `FOLLOWUP`, 실패 질문 아님 |
| 근거 부족 | `INSUFFICIENT_GROUNDING`, 기존 적격 실패 저장 규칙 |
| 설정 불완전·cap 소진 | 공식 template |

클라이언트가 보내는 flag, intent, source, KB ID 또는 mode로 이 gate를 우회할 수 없다.

## 6. 입력 최소화와 개인정보 경계

Provider 입력은 다음으로 제한한다.

- 보수적으로 마스킹된 현재 질문
- 서버가 확정한 intent enum
- 최종 검색된 한 개 또는 실제 답변에 필요한 최소 ACTIVE/OFFICIAL KB
- 서버 발급 fact ID와 해당 공식 text의 bounded 목록
- source를 제외한 strict output schema와 안전 지시
- 질문과 무관한 비식별 요청 식별자

다음은 전송하지 않는다.

- raw question, 마스킹 finding의 원문 값, raw PII 또는 민감정보
- 이전 대화 transcript, context token, actor/user ID, IP, device ID
- DB DSN, API key, secret, 내부 UUID, 전체 DB 또는 전체 KB
- CANDIDATE/staging/mock/거절 자료와 관리자 comment/audit
- source URL, source title, verified date의 생성 지시

마스킹된 실제 시민 질문이 외부 사업자에게 전달되는 것은 잔여 개인정보·국외 처리·계정별
logging 조건 위험을 남긴다. 사용자는 이를 local/private 비공개 MVP에 한해 승인했다. 실제 기관
운영이나 public/remote 공개 전에는 별도 개인정보 고지, 법적 근거, 국외 처리, 계정별 logging과
보관·삭제 조건을 사람이 다시 승인해야 한다.

## 7. 출력 계약과 사실 고정

### 7.1 모델 draft

모델은 source나 행정 fact text를 자유 생성하지 않고 다음 구조를 제안한다.

```json
{
  "summary": "질문에 맞춘 쉬운 말 요약",
  "procedure_step_ids": ["STEP-01", "STEP-02"],
  "required_document_ids": ["DOC-01"],
  "processing_time_id": "TIME-01",
  "fee_id": "FEE-01",
  "department_id": "DEPT-01"
}
```

- `summary`만 제한된 자연어 생성 필드이며 최대 500자다.
- 나머지는 서버가 해당 요청에 대해 발급한 ID만 허용한다.
- 추가 필드, source 필드, 알 수 없는 ID, 중복 ID, 허용하지 않은 빈 값은 금지한다.
- 자유 입력 ID나 다른 KB의 ID는 허용하지 않는다.

### 7.2 서버 검증과 materialization

서버는 다음을 모두 검증한다.

- JSON parse와 strict schema, 추가 필드 0
- 현재 검색 결과가 발급한 ID allowlist에만 포함
- 필수 절차와 공식 필드 누락·중복·충돌 0
- summary에 KB에 없는 URL, 날짜, 금액, 전화번호나 행정 단정 0
- source/office/intent/status/policy 변경 시도 0
- output 길이와 Unicode 안전성

검증 성공 뒤 ID를 서버 소유 공식 text로 치환한다. source와 office는 기존 KB metadata에서
서버가 결합한다. 검증 하나라도 실패하면 생성된 summary와 모든 ID를 버리고 기존 template
SUCCESS 전체를 반환한다. AI 일부와 template 일부를 섞지 않는다.

### 7.3 공개 응답 draft 변경

SUCCESS 응답에 다음 필드를 추가한다.

```text
answer_mode = GENERATED | TEMPLATE
```

- `GENERATED`: AI draft 검증과 서버 materialization을 모두 통과
- `TEMPLATE`: provider 미사용, timeout, 오류, cap 또는 검증 실패 뒤 공식 template

이 필드는 시민에게 답변의 작성 방식을 설명하기 위한 것이며 출처 신뢰등급이 아니다. 기존
sources는 두 mode 모두 실제 사용한 공식 KB metadata여야 한다. 계약 변경은 OpenAPI, JSON
Schema, Pydantic, generated TypeScript, API/Web fixture와 version을 동시에 갱신한다.

## 8. Runtime 설정과 공급자 추상화

기존 provider-neutral transport와 `httpx`를 재사용하며 Upstage SDK를 추가하지 않는다. 합성
평가 mode와 시민 chat mode는 별도 flag로 분리한다.

| 설정 | 규칙 |
|---|---|
| provider | `upstage` exact |
| model | `solar-pro3` exact |
| base URL | `https://api.upstage.ai/v1` exact |
| chat mode | 기본 false, local/private에서만 명시 활성 |
| synthetic mode | 별도 flag; chat mode와 동시에 활성 금지 |
| timeout | 8초 |
| logical attempt | 1 |
| hidden retry | 0 |
| concurrency | 1 |
| max output | 1024 |
| process outbound cap | 30 |

정확한 환경변수명과 typed settings 분리는 후속 실행계획에서 현재 설정 loader와 대조해 확정한다.
HTTP 요청이나 Web query로 mode/model/base/cap을 바꿀 수 없다. startup, `/health`, `/ready`,
model list, balance, payment, top-up은 provider를 호출하지 않는다.

## 9. Idempotency·동시성·cap

- 같은 `Idempotency-Key`와 같은 request digest의 동시·재시도 요청은 provider를 최대 한 번만
  호출한다.
- durable 완료 응답이 있으면 provider를 다시 호출하지 않고 같은 안전 응답을 반환한다.
- lease 충돌 또는 결과가 불명확하면 provider를 중복 호출하지 않고 template로 닫는다.
- correlation request ID와 idempotency identity는 계속 분리한다.
- process outbound cap 30은 성공·실패·timeout을 모두 attempt 예약 시점에 계수한다.
- cap reset endpoint, 자동 새 process 또는 목표 출력 수를 채우기 위한 재실행을 만들지 않는다.

DB에는 기존 idempotency 계약이 허용한 digest와 안전 응답만 유지한다. 호출자가
`Idempotency-Key`를 제공한 경우에는 엄격한 서버 검증을 통과한 최종 안전 응답이 기존 논리 TTL
24시간 동안 저장될 수 있으며, 이 응답에는 `GENERATED` summary가 포함될 수 있다. 이는 중복
provider 호출을 막고 같은 논리 응답을 재생하기 위한 기존 저장 계약의 명시적 예외다.
raw/masked question, prompt, provider payload/body, context token, request/correlation ID를 새로
저장하지 않는다. DB migration은 이 설계에 포함하지 않는다.

## 10. 오류와 fallback

| 실패 | 시민 결과 | provider 재시도 |
|---|---|---|
| disabled/config invalid | 공식 template | 0 |
| timeout | 공식 template | 0 |
| 401/403/429/5xx/network | 공식 template | 0 |
| empty/truncated/non-JSON | 공식 template | 0 |
| schema/additional field | 공식 template | 0 |
| unknown/duplicate/forbidden fact ID | 공식 template | 0 |
| summary fact drift | 공식 template | 0 |
| idempotency lease/cap | 공식 template | 0 |

안전한 template가 있는 SUCCESS 요청에서 provider 실패는 HTTP 200이다. template도 만들 수 없는
시스템 불능만 기존 `SERVICE_UNAVAILABLE` HTTP 503 계약을 따른다. 시민 응답에는 내부 provider
오류, key, body 또는 상세 reason을 노출하지 않는다.

## 11. 로그·보관·감사

허용 로그·metric:

- provider/model의 고정 식별자, attempt 수, latency bucket, outcome enum
- input/output token 수, aggregate 비용, fallback count, cap 잔여량
- 질문과 연결할 수 없는 bounded run metric

금지:

- raw/masked question, prompt, provider request/response, reasoning, 생성 답변
- source/KB 전문, context token, idempotency key, request digest, 내부 UUID
- key, DSN, balance, 계정 정보

시민 질문과 생성 답변의 일반 DB·파일·trace 저장을 새로 만들지 않는다. 단, §9의 기존 durable
idempotency 안전 응답 24시간 보관은 같은 논리 요청의 중복 실행 방지를 위한 제한된 예외다.
기존 질문 저장 정책은 deterministic policy 결과가 계속 소유한다.

## 12. Web·접근성

- GENERATED SUCCESS에는 `AI로 정리한 공식 안내` 배지를 표시한다.
- TEMPLATE SUCCESS에는 `공식 안내` 배지를 표시한다.
- 배지는 색상만으로 구분하지 않고 텍스트를 제공한다.
- source 카드에는 기존처럼 공식 출처명·URL·확인일을 표시한다.
- 정적 설명에 “AI가 표현을 정리할 수 있으나 행정 사실과 출처는 승인된 공식 KB에서 서버가
  결합하며, 오류 시 공식 템플릿을 사용한다”를 명시한다.
- loading, 8초 지연, fallback 전환에서 focus, `aria-live`, 키보드와 390/430/desktop 동작을
  검증한다.

## 13. 테스트와 인수 기준

### 집중 테스트

1. 지원+근거충분 요청은 provider 1회와 `GENERATED`를 반환한다.
2. 모든 제외 정책 경로는 provider call 0이다.
3. 공식 절차·서류·시간·수수료·기관·source는 서버 KB 값과 byte/equality 기준으로 일치한다.
4. timeout, auth, rate limit, network, empty, invalid JSON, schema, unknown ID, fact drift는 모두
   1 attempt 뒤 `TEMPLATE`로 성공한다.
5. 동일 idempotency key의 동시·재시도는 provider call 1 이하이다.
6. process cap 30 이후 call 0과 template fallback을 보장한다.
7. request/response/DB/log에서 raw question·PII·secret·provider body 0을 확인한다.
8. `answer_mode` 계약 drift와 Web badge/a11y를 검증한다.

### 영역·전체 gate

- API lint, typecheck, unit/integration
- contracts generate/check와 fixture
- Web lint, typecheck, unit, build, 390/430/desktop E2E
- provider-disabled 전체 sample 20/20과 개선 회귀 유지
- repository docs, secret/current-tree, root offline gate

### local actual acceptance

- 지원 질문 10개를 local/private에서 실행한다.
- source 표기 100%, server-owned 공식 facts 불일치 0, PII/secret persistence 0
- 장애 강제 1개 이상에서 `TEMPLATE` fallback 시연
- 예상·실제 outbound/token/비용을 원문 없는 aggregate로 기록
- 이 결과는 local demo 증거이며 public 운영 승인이나 전체 민원 정확도 보장이 아니다.

## 14. 배포·롤백

### 활성화

1. written specification 승인(D-073)
2. 실행계획 승인
3. TDD 구현과 독립 보안/계약 검토
4. provider-disabled 전체 회귀
5. 사용자가 ignored local env에서만 chat mode를 활성화
6. local actual acceptance

### 롤백

- chat mode flag를 false로 바꾸고 key를 제거하면 네트워크 호출 0의 기존 template 경로로
  복귀해야 한다.
- contract가 이미 배포되지 않은 local draft 단계에서는 변경 commit을 revert한다.
- key 유출 의심 시 즉시 실행 중지, key 폐기·재발급, tracked/current/history scan을 수행한다.
- public/remote 활성화는 별도 설계·개인정보·보안·비용·배포 승인 전까지 금지한다.

## 15. 인간과 AI 책임

### 인간이 확인·승인

- 이 written specification과 후속 실행계획
- 마스킹 질문의 local/private Upstage 전송 잔여 위험
- 공개 응답 `answer_mode`와 Web 배지
- local actual 실행 시점과 비용
- public/remote/실제 기관 운영의 별도 개인정보·계약·배포 결정

### AI가 자율 처리

- provider-neutral interface와 typed model의 내부 파일 분리
- fact ID 발급·검증 helper와 test double/fixture
- 기존 `httpx` transport, timeout/cap/idempotency의 같은 계약 내 구현
- lint/formatting/명명과 원문 없는 aggregate metric

## 16. 공식 참고자료

- Upstage Chat API/API key example: https://console.upstage.ai/api-keys?api=chat-reasoning
- Upstage API pricing: https://www.upstage.ai/pricing/api
- Upstage privacy policy (`Last Revised: May 21, 2026`; page verified 2026-07-25):
  https://www.upstage.ai/privacy-policy/updated-jun-01-2026

공급자 문서는 변할 수 있으므로 구현 시작과 local actual 직전에 model/API/가격/처리조건을
다시 확인한다. 마케팅 성능 주장은 프로젝트 인수 증거로 사용하지 않는다.
