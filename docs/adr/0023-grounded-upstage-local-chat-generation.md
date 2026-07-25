# ADR-0023: local/private 근거 제한형 Upstage 시민 답변 생성

- Status: Accepted design / implementation pending written-specification and plan approval
- Date: 2026-07-25
- Supersedes: ADR-0022의 local/private 실제 시민 입력 금지와 actual 통과 선행조건
- Preserves: ADR-0022의 public/remote 금지, provider abstraction, ACTIVE/OFFICIAL gate,
  cap, deterministic fallback, 서버 소유 출처 원칙

## Context

결정론적 `/api/v1/chat` MVP는 마스킹, 분류, ACTIVE/OFFICIAL 검색, 근거 gate, 구조화 템플릿과
서버 결합 출처를 제공한다. LLM-002 Upstage `solar-pro3` actual은 30회 중 strict-schema
27회로 100% criterion을 실패했지만 한국어 검수 9건 평균은 4.8444/5였고 provider 오류 때
template fallback은 동작했다.

사용자는 실제 기관 운영이나 공개 서비스가 아니라 local/private 입찰 시연 MVP에서 질문에 맞춘
자연스러운 AI 답변을 사용하기로 했다. 모델 출력을 그대로 신뢰하면 “모르면 지어내지 않고,
알면 끝까지 안내한다” 원칙과 공식 facts/source 권위를 훼손할 수 있으므로 모델의 생성 범위를
별도로 제한해야 한다.

## Decision

local/private `/api/v1/chat`에서 다음 조건을 모두 만족한 SUCCESS 후보만 Upstage exact
`solar-pro3`에 보낸다.

- 보수적 PII masker가 안전한 마스킹 질문을 생성
- deterministic supported intent
- ACTIVE + OFFICIAL KB 검색과 grounding gate 통과
- server-owned runtime 설정과 process cap 통과

`FOLLOWUP`, `PRIVACY_UNRESOLVED`, `INSUFFICIENT_GROUNDING`, `PERSONAL_LOOKUP`,
`LEGAL_JUDGMENT`, `OUT_OF_SCOPE`는 provider call 0이다. 실제 기관 운영, public/remote 배포도
별도 승인 전 call 0이다.

모델은 질문에 맞춘 summary와 서버가 해당 요청에 발급한 procedure/document/time/fee/department
fact ID만 반환한다. 서버는 strict schema, ID allowlist와 summary fact drift를 검증하고 ID를
승인 KB의 공식 text로 materialize한다. intent, status, policy, source title/URL/verified date,
office card는 항상 서버 값이다. 검증 실패, timeout 또는 provider 장애가 하나라도 있으면 모델
결과 전체를 버리고 기존 deterministic template를 반환한다.

한 요청은 timeout 8초, logical attempt 1회, hidden retry 0이다. concurrency 1과 process outbound
attempt 30 상한을 유지한다. 기존 durable idempotency가 같은 key의 provider 중복 호출을 막아야
한다. 질문·prompt·provider body·생성 답변은 DB, 파일 또는 로그에 저장하지 않는다.

SUCCESS 응답에는 `answer_mode=GENERATED|TEMPLATE`를 추가하고 Web은 각각
`AI로 정리한 공식 안내`, `공식 안내`를 텍스트 배지로 표시한다. 공급자는 기본 disabled이며
합성 평가 mode와 시민 chat mode를 분리한다. 새 SDK나 DB migration은 추가하지 않는다.

## Consequences

- local/private 데모에서 질문 맞춤 한국어를 제공하면서 공식 facts/source는 서버 권위로 유지한다.
- schema 안정성이 100%가 아니어도 시민 기능은 template로 완료된다.
- provider 사용 시 최대 8초의 추가 지연과 외부 전송·비용·공급자 장애 위험이 생긴다.
- 마스킹된 자유 입력에도 재식별 가능성·국외 처리·계정별 logging 잔여 위험이 있다. 이 위험은
  local/private MVP에서만 승인됐으며 public/실제 기관 운영 전 재승인이 필요하다.
- `answer_mode`는 공개 응답 draft와 Web/generated type을 함께 바꾸므로 후속 실행계획과 계약
  버전 갱신이 필요하다.
- LLM-002 actual FAIL 증거는 변경되지 않으며 새 경계의 local acceptance를 별도로 수행한다.

## Rejected alternatives

- AI 없이 template만 유지: 가장 안전하지만 사용자가 원하는 local 시연의 질문 맞춤 표현을
  제공하지 못해 거절.
- AI가 summary만 생성: 사실 표면은 가장 작지만 사용자가 Q-LLM-012=B로 전체 구조화 답변 시도를
  선택해 대체.
- AI가 fact text와 source를 자유 생성: 행정 사실·출처 환각을 서버가 완전히 통제하기 어려워 거절.
- 실패한 일부 AI field만 template와 혼합: 시민이 어떤 부분이 검증됐는지 알기 어렵고 상태 조합이
  폭증하므로 거절.
- provider를 모든 질문에 호출: 개인정보·정책·근거 부족 gate를 우회하므로 거절.
- Upstage SDK 추가: 기존 `httpx`로 충분하고 새 production dependency 승인이 없어 거절.

## References

- Q-LLM-006=B, Q-LLM-007=A, Q-LLM-009=A, Q-LLM-011=C, Q-LLM-012=B
- D-071, D-072
- `docs/superpowers/specs/2026-07-25-grounded-live-chat-generation-design.md`
- https://console.upstage.ai/api-keys?api=chat-reasoning
- https://www.upstage.ai/pricing/api
- https://www.upstage.ai/privacy-policy/updated-jun-01-2026
