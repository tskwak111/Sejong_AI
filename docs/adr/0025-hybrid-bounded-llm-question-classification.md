# ADR-0025: deterministic safety gate와 bounded LLM의 hybrid 질문 분류

> Amended by ADR-0028 for selectable local/private classifier-provider ownership. The
> deterministic safety, validation, storage and fallback boundaries in this ADR remain active.

- Status: Accepted / integrated / local runtime composition corrected
- Date: 2026-07-27
- Amends: ADR-0023의 provider 전 deterministic supported-intent gate
- Preserves: PII 마스킹 선행, policy gate, ACTIVE-only retrieval, server-owned source,
  provider-disabled default, local/private only, fail-closed fallback

## Context

현재 분류기는 네 supported intent와 고정 OUT_OF_SCOPE term table을 사용한다. 실제 질문 감사에서
일반적인 지원 표현을 UNKNOWN으로 놓치고, 민원과 무관한 요청·현재 범위 밖 행정 민원·지원 분야의
새 표현을 구분하지 못하는 문제가 확인됐다. term table만 계속 확장하면 알려진 문구는 고칠 수
있지만 새 표현마다 같은 문제가 반복된다.

기존 ADR-0023은 deterministic supported intent와 ACTIVE/OFFICIAL grounding을 Upstage 시민 답변
생성의 선행조건으로 둔다. 질문 분류에 LLM을 사용하면 이 provider 데이터 경계를 명시적으로
확장해야 한다.

## Decision

Q-CLASS-001=A에 따라 local/private MVP 질문 분류에 hybrid architecture를 채택한다.

1. backend deterministic PII redaction이 안전한 `SafeQuestion`을 만들기 전에는 provider를
   호출하지 않는다.
2. PERSONAL_LOOKUP, LEGAL_JUDGMENT와 명백한 policy/safety 결과는 deterministic server gate가
   소유한다.
3. 명백한 supported intent와 명백한 NON_CIVIC은 deterministic fast path로 처리한다.
4. 안전하지만 taxonomy가 애매한 현재 질문만 Upstage exact `solar-pro3` classifier에 보낸다.
5. 모델은 자유 문장 없이 폐쇄형 분류 결과만 제안한다.
6. 서버는 schema와 조합을 검증하고 실제 retrieval, grounding, fallback, 저장과 source를 결정한다.
7. 모델은 답변·출처·KB ID·기관·candidate eligibility·보관 여부를 생성하거나 결정하지 않는다.
8. timeout, quota, malformed JSON, invalid enum과 불확실 결과는 모델 출력을 폐기하고 text를
   저장하지 않는 deterministic safe fallback으로 닫는다.

planned closed route는 `SUPPORTED`, `CIVIC_SCOPE_GAP`, `NON_CIVIC`, `NEEDS_FOLLOWUP`이다.
`SUPPORTED`만 네 existing supported intent 중 하나를 함께 가질 수 있다. exact wire schema와
confidence 표현은 written specification에서 확정한다.

분류 호출과 기존 grounded answer generation은 서로 다른 목적이다. 한 시민 요청이 분류 후
SUCCESS 생성까지 가면 최대 두 번의 provider 호출 가능성이 생긴다. Q-CLASS-002=A에 따라
다음 경계를 확정한다.

- classifier: 요청당 최대 1 attempt, timeout 3초, retry 0, 입력 1,024자, 출력 128 token,
  process sub-cap 20
- grounded generation: 기존 timeout 8초, 1 attempt, retry 0, process sub-cap 30
- combined provider process cap: classifier와 generation을 합쳐 최대 40 outbound attempt
- local synthetic acceptance run cost stop line: VAT 포함 USD 0.05
- 각 시민 요청의 최대 provider 호출: classifier 1 + grounded generation 1

sub-cap 합계보다 combined cap이 작으므로 어느 경로도 전체 process budget을 독점할 수 없다.
모든 cap은 fail closed이며 hidden retry와 process 내 counter reset은 금지한다. 이 결정은
실행 상한만 승인한다. exact schema written specification, 실행계획과 별도 local actual 승인을
마치기 전 classifier actual call은 계속 금지한다.

## Consequences

- 새로운 한국어 표현을 네 분야·scope gap·non-civic으로 더 잘 구분할 수 있다.
- 안전하게 마스킹된 질문이라도 기존보다 더 이른 단계에서 외부 provider로 전송될 수 있다.
- ambiguous 요청에 network latency와 비용이 추가되고 provider 장애 경로가 늘어난다.
- strict enum과 server validation으로 모델 권한을 분류 제안에만 제한한다.
- 한 요청은 최악의 경우 3초 분류 뒤 8초 생성까지 걸릴 수 있으므로 UI는 단계별 기다림 문구와
  전체 fail-closed 경로를 가져야 한다. 실제 latency acceptance 기준은 written spec에서 정한다.
- PII false positive는 provider 이전 문제이므로 별도 deterministic TDD 수정이 계속 필요하다.
- D-092는 PII-free allowlisted actual classifier run을 승인했다. ADR-0026에 따라 remote 시민
  검증은 provider-disabled가 기본이며, real citizen/free-input outbound와 실제 기관 운영은
  개인정보·약관·법무 운영 gate 전까지 call 0이다.
- 2026-07-27 `CLASSIFIER-RUNTIME-WIRING-001`은 adapter·service까지만 구현되고
  `create_local_app()` 조립이 빠졌던 결함을 교정했다. exact classifier profile은 실제 local
  시민 route에 주입되고, combined profile은 classifier와 grounded generator가 같은
  `ProviderAttemptLedger`를 공유한다. 공개·원격 승인 범위는 변하지 않는다.

## Rejected alternatives

- deterministic term table만 확장: 장기 자연어 recall 한계를 해결하지 못해 거절한다.
- 모든 안전 질문을 LLM이 단독 분류: 비용·지연·오분류 표면과 provider 의존성이 커져 거절한다.
- raw 질문을 provider에 전달: PII 선행 원칙을 위반해 거절한다.
- 모델이 답변·출처·저장 여부까지 결정: 공식 KB와 server authority를 훼손해 거절한다.

## References

- Q-CLASS-001=A / Q-CLASS-002=A / D-086~D-087 / A-058/A-060
- ADR-0004, ADR-0005, ADR-0023, ADR-0024
- `docs/discovery/CHAT_CLASSIFICATION_GAPS_DISCOVERY_REPORT.md`
