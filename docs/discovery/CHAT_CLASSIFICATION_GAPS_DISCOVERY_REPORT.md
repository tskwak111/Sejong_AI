# CHAT-CLASSIFICATION-GAPS-001 발견 보고서

- Date: 2026-07-26 KST
- Status: Diagnosis complete / architecture decisions pending
- Branch: `codex/ACTUAL-P0-UX-GAPS-001`
- Base: `1dda881`
- Product surfaces: local/private `/api/v1/chat`, `/chat`, future `/admin`

## 1. 사용자 관측

사용자는 다음 실제 동작을 보고했다.

| Fixture ID | 기대 | 실제 관측 |
|---|---|---|
| WX | 민원과 무관함을 안내 | `PRIVACY_UNRESOLVED` |
| RENT | 현재 KB에 없는 민원으로 분류 | generic FOLLOWUP |
| SCHOLAR | 현재 KB에 없는 민원으로 분류 | `PRIVACY_UNRESOLVED` |
| FAMILY | 현재 지원 증명서와 다른 민원으로 분류 | generic FOLLOWUP |

질문 원문은 보고서·DB·로그에 복제하지 않고 fixture ID만 사용한다.

## 2. 재현 결과와 원인

### 2.1 개인정보 단계

- WX: `AMBIGUOUS_PERSON_NAME`
- SCHOLAR: `AMBIGUOUS_PERSON_NAME`
- RENT/FAMILY: 안전한 마스킹 결과 생성

WX는 일반적인 의문 표현이, SCHOLAR는 행정 명사가 각각
`_POSSIBLE_CONTEXTUAL_NAME_ANYWHERE`와 `_looks_like_contextual_person_name` 조합에서
사람 이름으로 오탐된다. 이 두 요청은 분류기나 LLM에 도달하지 않는다.

따라서 LLM 분류를 추가하는 것만으로 WX/SCHOLAR 문제는 해결되지 않는다. PII 코어의
fail-closed 원칙을 보존하면서 행정·일상어 오탐을 줄이는 별도 TDD 수정이 먼저 필요하다.

### 2.2 결정론적 분류 단계

- RENT/FAMILY: `UNKNOWN + followup_required=true`
- 명시된 날씨·맛집·버스·여권·출생신고·복지급여 용어: `OUT_OF_SCOPE`
- 지원 분야의 정확한 키워드: 기존 supported intent
- 자연어 표현 중 일부는 지원 분야여도 UNKNOWN이 될 수 있다.

현재 분류기는 네 supported intent의 작은 term table과 고정 OUT_OF_SCOPE term table만
사용한다. “민원과 무관함”, “현재 네 분야 밖이지만 행정 민원임”, “네 분야 안인데 표현이
새로움”을 서로 다른 상태로 표현하지 못한다. 세 경우 모두 명시 term이 없으면 UNKNOWN
FOLLOWUP으로 합쳐진다.

### 2.3 저장·승인 단계

현재 DB와 정책은 `INSUFFICIENT_GROUNDING`을 네 supported intent에만 허용한다.
`OUT_OF_SCOPE`는 질문 text와 failed row를 저장하지 않고 범위 확대는 별도 사업 결정이다.
따라서 RENT/SCHOLAR/FAMILY를 기존 failed-question queue에 넣는 것은 현재 계약·DB 제약·
개인정보 정책을 위반한다.

## 3. LLM 분류 적용 가능성

가능하지만 LLM 단독 분류는 권고하지 않는다. 권고 경계는 다음과 같다.

1. deterministic PII 마스킹을 먼저 통과한다.
2. 개인 조회·법적 판단과 명백한 고위험 정책은 deterministic gate가 소유한다.
3. 명백한 supported/OOS 규칙은 빠른 deterministic 경로로 처리한다.
4. 안전하지만 불확실한 질문만 Upstage 분류기에 보낸다.
5. 모델 출력은 strict enum만 허용하고 서버가 검증한다.
6. timeout·schema 오류·낮은 신뢰도는 모델 결과를 버리고 안전한 deterministic fallback으로 간다.
7. LLM은 답변·출처·KB ID·저장 여부를 결정하지 않는다.

분류 결과의 최소 의미 후보는 다음 네 가지다.

- `SUPPORTED`: 네 분야 중 하나
- `CIVIC_SCOPE_GAP`: 행정 민원이지만 현재 네 분야/KB 범위 밖
- `NON_CIVIC`: 날씨·맛집 등 민원과 무관
- `NEEDS_FOLLOWUP`: 정보가 부족해 사람에게 확인 질문 필요

## 4. 고려한 접근

### A. Hybrid deterministic + bounded LLM classifier — 권고

- 장점: 자연어 표현 대응력이 좋아지고 정책·개인정보·출처 권위는 서버에 남는다.
- 단점: 마스킹된 질문의 외부 전송, 비용·지연·quota·provider 장애와 strict-schema fallback이
  추가된다.

### B. Deterministic vocabulary만 확장

- 장점: 외부 전송·비용·지연이 없고 결과가 재현 가능하다.
- 단점: 표현을 계속 수동 추가해야 하며 새로운 문장에 약하다.

### C. 모든 안전 질문을 LLM이 단독 분류

- 장점: 구현 표면이 단순해 보이고 표현 대응 폭이 넓다.
- 단점: 정책 오분류, 공급자 장애, 비용과 개인정보 전송 범위가 커진다. 기존 ADR-0023의
  deterministic supported-intent gate도 무너뜨리므로 거절한다.

## 5. 권고 수직 흐름

1. PII false-positive 수정과 광범위한 negative regression corpus
2. 시민 분류 taxonomy와 fallback copy 확정
3. hybrid classifier interface·strict schema·provider-disabled fallback
4. `CIVIC_SCOPE_GAP` 저장 정책을 선택한 경우 별도 DB/API/admin migration
5. certificate category FOLLOWUP 계획을 새 taxonomy 뒤에 통합
6. actual local acceptance: 결과 정확도, PII 전송 0 위반, JSON 안정성, latency, cost

## 6. 미결정

### Q-CLASS-001 — 분류 실행 경계

Hybrid classifier를 채택할지 결정해야 한다. 권고는 A이며 provider disabled 기본과
deterministic fallback을 유지한다.

### Q-SCOPE-001 — 현재 범위 밖 행정 민원 저장

`CIVIC_SCOPE_GAP`을 별도 범위확대 검토 queue에 마스킹 text로 30일 저장할지, 기존처럼
OUT_OF_SCOPE 무저장을 유지할지 결정해야 한다. 기존 KB 후보 queue에 바로 넣는 것은 금지한다.

## 7. 변경·비변경

- 변경: 발견 보고서, ambiguity/decision evidence, version/changelog, 구현 노트
- 변경 없음: product/API/Web/test source, OpenAPI, DB/migration/data, provider config/call,
  dependency/lockfile, public/remote/deploy
