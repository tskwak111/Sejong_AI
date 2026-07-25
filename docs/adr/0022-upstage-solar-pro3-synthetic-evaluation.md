# ADR-0022: Upstage Solar Pro 3 합성 평가와 실제 시민 경로 분리

- Status: Partially superseded by ADR-0023 for local/private citizen chat; LLM-002 historical
  evaluation boundary and evidence retained
- Date: 2026-07-23
- Supersedes: ADR-0005의 DeepSeek provider/model 선택
- Preserves: ADR-0005의 provider abstraction, 합성 전용, cap, fallback, 출처 서버 결합 원칙

> 2026-07-25 D-072/ADR-0023은 더 좁은 server-issued fact ID 검증과 전체 template fallback을
> 전제로 local/private 시민 chat을 새로 승인했다. 이 ADR의 LLM-002 합성 평가 설계와 actual
> FAIL 증거는 변경하지 않으며 public/remote/실제 기관 운영 금지는 계속 유효하다.

## Context

기존 ADR-0005는 DeepSeek `deepseek-v4-flash`를 local/private 합성 fixture 전용 공급자로
선택했다. 실제 adapter와 실제 호출은 구현되지 않았고, 결정론적 시민 chat MVP만 완성됐다.
사용자는 보유·사용할 모델을 Upstage로 바꾸고, 실제 시민 연결 전 한국어 품질·JSON 안정성·비용을
먼저 합성 평가하기로 Q-LLM-005=A를 확정했다.

## Decision

외부 합성 평가 공급자를 Upstage로 바꾸고 exact model을 `solar-pro3`로 고정한다. 직접 HTTPS API와
기존 production dependency `httpx`를 사용하며 새 SDK를 추가하지 않는다.

provider는 기본 disabled다. local/private 내부 runner가 server-owned allowlist의 canonical
`T-01`~`T-10`을 로드하고, 기존 PII masking·classification·ACTIVE/OFFICIAL retrieval·grounding을
모두 통과한 경우에만 호출한다. 실제 시민, 브라우저 자유 입력, public/remote 요청은 마스킹
성공 여부와 무관하게 provider에 보내지 않는다.

모델은 한국어 답변 구성 요소만 제안한다. intent, status, fallback, candidate eligibility,
source title/URL/verified date는 모델이 정하지 않으며 서버가 기존 결정과 KB metadata를 사용한다.
strict JSON/Pydantic 검증에 실패하면 최대 1회 재시도한 뒤 deterministic template/policy fallback을
사용한다.

한 process run은 concurrency 1, logical retry 최대 1, hidden retry 0, max output 1024,
outbound attempt 총 30 이하를 강제한다. startup, health, readiness, model list, balance,
payment/top-up, counter reset은 provider를 호출하지 않는다.

평가 통과만으로 실제 시민 `/api/v1/chat` 연결을 허용하지 않는다. 선택지 B는 공급자 처리조건,
개인정보 고지·국외 처리, 비용·쿼터, 공개 사용자 동작과 장애 계약을 다시 검토해 별도 승인한다.

## Consequences

- deterministic MVP가 계속 기본이므로 provider 장애가 시민 기능을 중단시키지 않는다.
- canonical SUCCESS 10건×3회 범위에서 한국어·JSON·비용을 비교할 수 있다.
- 질문·답변 본문을 저장하지 않아 재현 가능한 장문 샘플 artifact는 만들지 못한다. 대신 fixture ID,
  점수, 고정 사유 코드와 aggregate 지표만 남긴다.
- actual run에는 사용자가 local ignored env에 Upstage key를 준비해야 한다.
- 가격·정책·model ID는 변경될 수 있어 구현 직전과 actual run 직전에 공식 문서를 재확인한다.

## Rejected alternatives

- 실제 시민 `/chat`에 즉시 연결: 공급자 처리·보관과 사용자 동작을 충분히 검증하지 않아 거절.
- LLM에 분류·검색·출처 생성을 위임: ACTIVE-only와 server-bound source 원칙을 약화해 거절.
- Upstage SDK 추가: 기존 `httpx`로 충분하고 production dependency 승인이 없어 거절.
- Cloud에 key를 등록해 평가: local-only secret/actual gate를 위반해 거절.

## References

- Q-LLM-005=A / D-065
- `docs/superpowers/specs/2026-07-23-upstage-solar-pro3-synthetic-evaluation-design.md`
- https://console.upstage.ai/api-keys?api=chat
- https://www.upstage.ai/pricing/api
- https://www.upstage.ai/privacy-policy
