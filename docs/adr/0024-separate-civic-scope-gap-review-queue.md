# ADR-0024: 현재 지원 범위 밖 행정 민원의 별도 범위확대 검토 큐

- Status: Accepted direction / written specification and implementation pending
- Date: 2026-07-26
- Amends: ADR-0004의 OUT_OF_SCOPE 무저장 정책에 새 행정 민원 scope-gap class를 분리
- Preserves: 원문 미저장, PII 마스킹 선행, ACTIVE-only 시민 답변, 사람의 범위 확대 승인,
  기존 KB 후보와 작성자·승인자 분리

## Context

현재 시민 분류는 네 supported intent, OUT_OF_SCOPE와 UNKNOWN을 사용한다. DB의
`failed_questions`는 네 supported intent의 `INSUFFICIENT_GROUNDING` 개선 루프만 후보로
허용하며 OUT_OF_SCOPE 질문 text와 row는 저장하지 않는다.

실제 질문 감사에서 날씨처럼 민원과 무관한 요청과, 청년 지원·장학·현재 미지원 증명서처럼
행정 민원이지만 네 분야 밖인 요청이 같은 범위 밖 결과로 합쳐지는 gap을 확인했다. 후자를
기존 failed-question queue에 넣으면 지원 intent 제약과 개인정보·승인 정책을 위반하고,
운영자가 기존 네 분야 KB로 잘못 승격할 위험이 있다.

## Decision

Q-SCOPE-001=A에 따라 안전하게 마스킹된 현재 지원 범위 밖 행정 민원을 별도
`CIVIC_SCOPE_GAP` 범위확대 검토 흐름으로 분리한다.

- 기존 `failed_questions`·KB candidate queue와 물리적·논리적으로 분리한다.
- 원문은 저장하지 않고 PII gate를 통과한 `masked_question`만 생성 후 30일 보관한다.
- 만료 시 text만 NULL로 파기하고 비텍스트 분류·검토 metadata는 유지할 수 있다.
- 이 항목은 `candidate_eligible=false`이며 기존 KB 후보·ACTIVE로 자동 전환하지 않는다.
- 운영자는 반복 수요와 분류를 검토할 수 있지만, 지원 범위 편입은 PM의 별도 제품 결정,
  공식 출처 준비, 계약/DB/data migration과 승인 계획이 있어야 한다.
- 민원과 무관한 `NON_CIVIC` 요청은 계속 text와 review row를 저장하지 않는다.
- PII unresolved, 개인 조회, 법적 판단도 이 queue에 들어가지 않는다.
- 분류에 LLM을 사용할지는 Q-CLASS-001의 별도 결정이다. 이 ADR은 provider call을 승인하지 않는다.

D-090의 설계 2부 승인으로 공개·저장 경계를 다음처럼 고정한다.

- 시민 응답은 `intent=OUT_OF_SCOPE`, `fallback.reason=CIVIC_SCOPE_GAP`,
  `candidate_eligible=false`를 사용한다.
- `CIVIC_SCOPE_GAP` row는 기존 interaction event, `failed_questions`, KB candidate와
  중복 저장하거나 연결하지 않는다.
- NON_CIVIC은 기존 `OUT_OF_SCOPE` 시민 reason을 사용하되 text/event/failed/review row를
  모두 만들지 않는다.
- FOLLOWUP은 실패·scope-gap row를 만들지 않는다.
- PERSONAL_LOOKUP, LEGAL_JUDGMENT, PRIVACY_UNRESOLVED도 이 queue에 들어가지 않으며 기존
  무저장 경계를 유지한다.

정확한 DB table/function 이름, review status, admin endpoint/UI와 migration 번호는 written
specification에서 확정한다. 그 전까지 current runtime과 DB의 OUT_OF_SCOPE 무저장 동작을
유지한다.

## Consequences

- 네 분야 밖 행정 수요를 기존 KB 품질 개선과 섞지 않고 측정할 수 있다.
- 마스킹 질문 30일 보관이라는 새 개인정보 처리 목적과 접근 통제가 생긴다.
- OpenAPI, DB forward/rollback/pgTAP, repository adapter와 admin UI 변경이 필요하다.
- scope-gap을 잘못 분류하면 불필요한 text 보관이 생기므로 PII·taxonomy 회귀 표본과 사람 검토가
  필요하다.
- 공개·원격 운영 전 개인정보 처리방침, 기록물·법무·provider 정책을 다시 승인해야 한다.

## Rejected alternatives

- 기존 `failed_questions`에 UNKNOWN으로 저장: supported-intent와 candidate workflow 불변조건을
  약화하고 잘못된 ACTIVE 승격 경로를 만들기 때문에 거절한다.
- OUT_OF_SCOPE event에 text를 추가: 현재 무저장 계약을 숨은 방식으로 깨므로 거절한다.
- 자동으로 새 KB category를 생성: 공식 범위·데이터·승인 결정 없이 시민 답변 범위를 넓혀 거절한다.

## References

- Q-SCOPE-001=A / D-085/D-090 / A-059
- ADR-0003, ADR-0004, ADR-0011, ADR-0020
- `docs/discovery/CHAT_CLASSIFICATION_GAPS_DISCOVERY_REPORT.md`
