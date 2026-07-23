# LLM-002 Upstage Solar Pro 3 합성 평가 설계

- 상태: Review
- 작성일: 2026-07-23 KST
- 결정: Q-LLM-005=A
- 관련 결정: D-017, D-023, D-065
- 관련 ADR: ADR-0005(Superseded), ADR-0022
- 구현 시작 조건: 사용자의 명세 승인과 후속 실행계획 승인

## 1. 목적

결정론적 local/private 시민 답변 경로는 이미 MVP의 기준선이다. 외부 LLM은 이 기준선을
대체하지 않고, 승인된 공식 KB로 근거가 충분한 합성 질문의 한국어 표현 품질과 구조화 출력
안정성을 비교하는 제한된 평가 도구로만 도입한다.

사용자는 기존 DeepSeek 대신 Upstage를 선택했고 Q-LLM-005에서 다음 순서를 승인했다.

1. 합성 평가로 한국어 품질, JSON 안정성, 비용을 확인한다.
2. 통과 증거를 사람이 검토한다.
3. 실제 시민 자유 입력 또는 `/api/v1/chat` 연결은 별도 선택지 B와 새 승인을 받는다.

## 2. 범위

### 포함

- Upstage API를 직접 호출하는 provider-neutral adapter
- exact model `solar-pro3`
- 기존 `httpx`를 사용한 OpenAI-compatible `POST /v1/chat/completions`
- local/private 전용 내부 평가 runner
- canonical 합성 질문 `T-01`~`T-10`의 서버 allowlist
- 질문별 3회, 한 process run 최대 outbound attempt 30회
- JSON Schema/Pydantic 검증
- provider 장애 시 기존 deterministic template/policy 결과 유지
- 질문·응답 본문 없는 aggregate 평가 리포트

### 제외

- 실제 시민 질문, 브라우저 자유 입력, public/remote 요청의 Upstage 전송
- `/api/v1/chat`의 기본 또는 선택형 provider 연결
- 분류, 검색, 근거 gate, 출처 생성의 LLM 위임
- provider가 만든 출처명·URL·확인일 사용
- prompt/response, reasoning 또는 질문 본문 DB·파일·로그 저장
- Upstage SDK 또는 새 production dependency
- Cloud secret, Codex Cloud actual call, 자동 충전, 잔액 조회
- 공개 배포, remote DB, 관리자 공개

## 3. 권위와 데이터 흐름

```text
server allowlist fixture ID(T-01~T-10)
  → canonical synthetic question load
  → 기존 PII masker
  → 기존 deterministic intent/classification
  → ACTIVE + OFFICIAL KB retrieval
  → 기존 grounding gate
  → 최소 approved KB payload + output schema
  → Upstage Solar Pro 3
  → strict schema validation
  → 모델 source 필드 폐기/금지
  → 서버가 기존 KB metadata로 source 결합
  → deterministic baseline과 품질 비교
  → text-free aggregate metrics
```

외부 모델 호출 전 단계의 결과가 SUCCESS가 아니면 호출하지 않는다. 모델은 `intent`,
`answer_status`, `fallback_reason`, `candidate_eligible`, source identity를 변경할 수 없다.
모델 출력이 비어 있거나 잘렸거나 schema를 위반하면 해당 시도는 실패로 계수하고 시민 경로와
평가 결과 모두 기존 template/policy fallback을 사용한다.

## 4. 실행 경계

### 4.1 호출 허용

다음 조건이 모두 참일 때만 네트워크 호출을 허용한다.

- local/private process
- provider 기본값은 disabled이며 명시적 synthetic evaluation mode가 활성
- fixture ID가 server-owned exact allowlist `T-01`~`T-10`에 포함
- canonical CSV의 row와 expected SUCCESS가 일치
- PII masker가 안전한 결과를 반환
- ACTIVE/OFFICIAL 검색과 grounding gate가 통과
- exact provider/model/base URL과 모든 limit 검증 통과
- outbound attempt 예약 후 run cap 30 미만

클라이언트가 보낸 `is_test`, 질문 text 또는 fixture ID를 그대로 신뢰하지 않는다. 평가 runner는
저장소의 canonical fixture ID를 인자로 받아 서버가 원문을 로드한다.

### 4.2 고정 설정

| 항목 | 값 |
|---|---|
| provider | `upstage` |
| model | `solar-pro3` |
| base URL | `https://api.upstage.ai/v1` |
| temperature | 낮은 고정값(구현계획에서 exact 값 테스트 고정) |
| max output tokens | 1024 |
| max input tokens | 평가 payload 4096 이하 |
| concurrency | 1 |
| logical retry | 최대 1회 |
| HTTP hidden retry | 0 |
| process run outbound attempt | 최대 30 |
| default enabled | false |

모델·base URL·cap은 CLI나 HTTP 요청으로 덮어쓰지 않는다. 시작, health, readiness에서 provider를
호출하지 않는다. model 목록, 잔액, 결제, 자동 충전, counter reset endpoint도 호출·구현하지 않는다.

## 5. 입력·출력 계약

### 입력 허용

- server-loaded synthetic question의 마스킹 결과
- 기존 deterministic intent
- 답변에 필요한 ACTIVE/OFFICIAL KB 최소 필드
- source를 제외한 답변 구조 schema
- fixture와 무관한 비식별 run/attempt ID

### 입력 금지

- 실제 시민 또는 운영자 자유 입력
- raw PII, secret, DB DSN, context token
- 전체 DB dump 또는 candidate/staging/mock 자료
- 승인되지 않은 KB
- source title, URL, verified date를 생성하라는 지시

### 출력

모델은 시민용 한국어 답변 구성 요소만 반환한다. strict schema는 추가 필드를 금지하며 source,
intent, status, candidate eligibility는 서버 값만 사용한다. 유효하지 않은 JSON을 문자열 repair로
추측하지 않는다. 첫 시도가 retryable한 경우에만 동일한 안전 payload로 1회 재시도한다.

## 6. 평가 프로토콜

### 6.1 평가 집합

- 권위: `data/evaluation/sample_questions_20.csv`
- 허용: exact `T-01`~`T-10`
- 제외: FOLLOWUP, INSUFFICIENT_GROUNDING, PERSONAL_LOOKUP, LEGAL_JUDGMENT,
  OUT_OF_SCOPE 및 이후 추가된 임의 row
- 반복: 각 3회
- 최대 outbound attempt: 재시도를 포함해 30회

재시도가 발생하면 30회 안에서 남은 계획 실행 수가 줄어든다. cap을 늘리거나 새 process를
자동 시작해 목표 30개 출력을 채우지 않는다.

### 6.2 자동 지표

- outbound attempt·retry·timeout·429·empty·truncated·schema-invalid 개수
- strict JSON/schema valid 비율
- forbidden/additional/source field 0건
- model/provider/latency/input·output token 수
- deterministic fallback 사용 건수
- fixture별 실행 횟수
- provider request/response 본문 없이 aggregate 비용 추정

### 6.3 한국어 품질 검수

PM은 fixture별 첫 valid 결과 10건을 다음 5개 항목으로 1~5점 평가한다.

1. 자연스러운 한국어와 쉬운 말
2. 질문에 대한 직접성
3. 승인 KB 핵심 절차·서류·주의사항의 보존
4. 근거에 없는 단정·과장 부재
5. 다음 행동의 명확성

원문 질문과 답변은 provider 로그나 장기 평가 artifact에 저장하지 않는다. 검수 화면은 local
process memory에서만 보여주고, 기록에는 fixture ID, 항목별 점수, PASS/FAIL, 원문 없는 짧은
고정 사유 코드만 남긴다.

### 6.4 통과 기준

- 실행한 모든 provider 결과의 strict JSON/schema valid 100%
- forbidden/source field, PII/secret/raw question persistence 0
- 공식 KB와 모순되는 중대 사실 0
- PM 5개 항목 평균 4.0/5 이상, 개별 항목 3 미만 0
- hidden retry 0, concurrency 1, run outbound attempt 30 이하
- timeout/429/invalid 출력에서도 deterministic fallback 성공 100%
- 실제 token usage 기반 총 추정 비용이 USD 0.05 이내

하나라도 실패하면 provider는 disabled 상태를 유지한다. 기준을 낮추거나 실제 시민 경로에
연결하지 않고 원인을 기록한 뒤 prompt/model/cap 변경을 별도 승인받는다.

## 7. 비용 기준

2026-07-23 확인한 Upstage 공개 가격은 Solar Pro 3 input USD 0.15/1M tokens, cached input
USD 0.015/1M tokens, output USD 0.60/1M tokens이며 표시 가격에 VAT 10%가 포함되지 않는다.

입력 4096, 출력 1024 tokens의 비캐시 최악값을 30회 모두 사용하면:

```text
30 × ((4096 × 0.15 / 1,000,000) + (1024 × 0.60 / 1,000,000))
= USD 0.036864 before VAT
≈ USD 0.040551 including 10% VAT
```

따라서 한 run의 보수적 상한은 VAT 포함 USD 0.05로 둔다. 실제 청구액은 공급자 계정·환율·정책에
따라 달라질 수 있으므로 리포트는 provider token usage와 위 가격 snapshot을 함께 표시한다.
잔액 조회·추가 충전·자동 재실행은 하지 않는다.

## 8. 개인정보·공급자 정책 판단

Upstage의 2026-07-07 개인정보 처리방침은 Console Playground 대화, Async API 결과, 별도 동의한
API logging, Free Tier request/response에 서로 다른 처리·보관 조건을 제시하고 AWS US 국외
처리 정보를 포함한다. 계정의 실제 계약·동의 상태를 저장소에서 검증할 수 없으므로 실제 시민
질문은 마스킹 여부와 관계없이 보내지 않는다.

이 설계의 합성 fixture에는 실제 개인정보를 넣지 않는다. API key는 ignored local environment에만
두고 Git, GitHub, Codex Cloud, 브라우저, 문서, 명령 출력과 로그에 넣지 않는다.

## 9. 장애와 롤백

- 설정 불완전/disabled: 네트워크 호출 0, 평가 runner는 bounded reason으로 중단
- timeout/429/5xx/empty/truncated/schema invalid: 최대 1회 retry, 이후 deterministic fallback
- cap 30: 추가 호출 0, partial aggregate 리포트
- key 유출 의심: 실행 중지, key 폐기·재발급, tracked/current/history scan
- rollback: provider flag off, local key 제거, adapter/evaluator 변경 revert

기존 `/api/v1/chat`, API 계약, DB schema, official data, Web은 이 수직 흐름에서 바뀌지 않으므로
provider rollback 뒤에도 local/private deterministic MVP는 그대로 동작해야 한다.

## 10. 구현 단위

명세 승인 뒤 작성할 실행계획은 다음 순서를 사용한다.

1. provider-neutral typed contract와 exact config/cap tests
2. Upstage `httpx` transport와 JSON validation/fallback tests
3. server-owned fixture allowlist와 evaluation runner
4. aggregate cost/quality report schema
5. local secret preflight와 no-content logging tests
6. offline 전체 regression
7. 사용자가 local key를 준비한 뒤 별도 actual synthetic run

actual call은 구현·offline 검증과 사용자 실행계획 승인 후에만 한다.

## 11. 인간과 AI 책임

### 인간이 확인·승인

- 이 명세와 후속 실행계획
- local Upstage key 준비와 actual 합성 평가 실행 시점
- 10개 한국어 결과의 PM 점수
- 실패 시 prompt/model/cap 변경
- 선택지 B인 실제 시민/free-input/provider 연결

### AI가 자율 처리

- 같은 경계 안의 파일 분리, helper, typed model, test fixture
- `httpx` transport, strict validation, retry/cap 상태 머신
- 원문 없는 aggregate 지표와 문서 링크
- formatting/lint/type/test 보정

## 12. 공식 참고자료

- Upstage Chat API/API key example: https://console.upstage.ai/api-keys?api=chat
- Upstage API pricing: https://www.upstage.ai/pricing/api
- Upstage billing: https://console.upstage.ai/billing
- Upstage privacy policy: https://www.upstage.ai/privacy-policy
- Solar Pro 3 announcement: https://www.upstage.ai/blog/en/solar-pro-3-0323

마케팅 성능 주장은 이 프로젝트의 평가 결과로 사용하지 않는다. 구현 직전과 actual run 직전에
model ID, API 형식, 가격, 개인정보 처리방침을 다시 확인한다.
