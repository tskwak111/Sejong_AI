# ADR-0027: ACTIVE topic catalog와 coverage grounding을 사용하는 제한형 Hybrid RAG

> Amended by ADR-0028 only for selectable local/private classifier-provider ownership. The
> ACTIVE/OFFICIAL catalog, grounding, source, storage and server-validation boundaries remain
> active.

- Status: Accepted — Tasks 1~9 local/offline complete; Task 10 actual FAIL recorded; Task 11 pending
- Date: 2026-07-27
- Extends: ADR-0006, ADR-0010, ADR-0023, ADR-0025
- Preserves: provider 전 PII 마스킹, ACTIVE/OFFICIAL-only, server-owned facts/sources/offices,
  질문 원문 DB 미저장, local/private provider boundary

## Context

현재 20개 ACTIVE KB의 retrieval은 intent별 lexical overlap을 중심으로 동작한다. 실측 UAT에서
`새 집으로 옮긴 뒤 행정상 거주지를 바꾸는 절차`처럼 의미는 같지만 단어가 다른 질문이
grounding에 실패했고, 대형폐기물 변경·취소·수거 질문은 공통 단어 때문에 일반 답변으로
모였다. 동의어 표만 확장하면 새로운 표현마다 같은 문제가 반복된다.

20개 KB 규모에서 vector DB와 embedding을 도입하면 별도 index lifecycle, dependency, 비용과
평가 표면이 늘어난다. 동시에 모델이 KB·답변·출처를 자유롭게 선택하게 하면 승인되지 않은
행정 사실을 사용할 위험이 있다.

## Decision

D-096~D-102와 승인된 설계 1~3부에 따라 제한형 Hybrid RAG를 채택한다.

1. request validation, PII redaction, personal/legal/privacy/policy gate가 항상 먼저다.
2. 현재 DB의 ACTIVE/OFFICIAL projection과 versioned non-factual coverage metadata의
   교집합으로 최대 20개 runtime topic catalog를 만든다.
3. exact approved example, unique strong lexical, validated context facet은 deterministic
   fast path로 처리한다.
4. 그 외 안전한 ambiguous 질문만 Upstage `solar-pro3`에 마스킹 질문과 bounded catalog를
   보낸다.
5. 모델은 closed route, intent, topic ID, coverage ID, pending slot만 제안한다.
6. 서버는 current membership, intent, coverage와 ACTIVE/OFFICIAL projection을 다시 검증한다.
7. typed grounding evidence가 없으면 성공시키지 않는다. score 0의 임의 첫 record와 invalid
   topic의 조용한 lexical fallback을 금지한다.
8. 최초 구현은 top-1 KB만 사용한다. 모델은 답변 fact, source, office, retention,
   candidate eligibility를 결정하지 않는다.
9. 지원 분야에 대응 topic이 없으면 `INSUFFICIENT_GROUNDING`, 모호하면 FOLLOWUP,
   범위 밖 행정은 `CIVIC_SCOPE_GAP`, 비행정은 `OUT_OF_SCOPE`로 닫는다.
10. topic coverage metadata와 UAT fixture는 공식 행정 데이터가 아니다. immutable `.2`와
    섞거나 새 사실을 넣지 않는다.

local interactive provider profile은 classifier 80, generator 100, combined 160,
classifier 3초, generator 8초, retry 0, concurrency 1, request hard wall 12초와 VAT 포함
USD0.20 pre-reservation stop을 사용한다. historical 20/30/40·USD0.05 actual evidence는
그 시점의 결과로 보존한다.

## Consequences

- 일상어 paraphrase recall을 높이면서 시민 답변은 계속 승인 KB 한 건에 묶인다.
- catalog/coverage metadata와 negative UAT를 유지해야 한다.
- 허용 topic 오선택 가능성은 남지만 invalid/inactive/source hallucination은 server gate가
  차단하고 48-case UAT 및 PII-free actual subset으로 회귀한다.
- 냉장고 폐가전·재산세 세율처럼 현재 KB 밖 사실은 더 자연스럽게 거절되지만 답변 범위가
  자동으로 늘어나지는 않는다.
- generic 질문은 네 분야 전체가 아니라 intent별 topic choice로 좁혀진다.
- public response field, DB schema, official data와 production dependency는 바뀌지 않는다.
  `followup_options` 값과 동작은 backend/Web/contract examples를 함께 갱신해야 한다.
- vector/embedding은 KB 규모·recall evidence가 별도 필요성을 입증할 때 새 ADR로 재검토한다.

## Rejected alternatives

- lexical keyword/alias만 계속 확장: 새로운 표현마다 유지보수가 반복돼 거절한다.
- 모든 질문에 모델 검색·답변을 위임: 비용·지연·권한·hallucination 표면 때문에 거절한다.
- vector/embedding을 즉시 도입: 현재 20 topic MVP에 과도해 거절한다.
- 모델이 선택한 topic을 server 검증 없이 사용: ACTIVE/official/source 경계를 깨뜨려 거절한다.
- 여러 KB를 초기에 합성: 절차·수수료·출처 충돌 위험 때문에 거절한다.

## 2026-07-28 A-072 strict provider wire addendum

D-111 actual은 outbound 9건 모두 HTTP 2xx와 strict usage를 통과했지만 exact canonical key
set에서 거절됐음을 확인했다. Q-LLM-014=A와 D-112~D-114에 따라 provider-only wire를 다음처럼
교정한다.

1. Upstage `response_format`은 strict `json_schema`와 exact required string five-key를 사용한다.
2. nullable `intent`, `topic_id`, `coverage_id`, `pending_slot`은 exact `NONE`을 사용한다.
3. provider-only parser가 sentinel을 canonical `None`으로 바꾸고 기존 closed route/shape/current
   catalog validator를 재사용한다.
4. canonical parser의 JSON `null` 계약과 public API는 바꾸지 않는다.
5. prompt는 full canonical field names를 사용하며 old shorthand를 제거한다.
6. fixed-stage observer, retry 0, fail-closed, body/question/key/DSN non-retention을 유지한다.
7. actual은 offline/root gate와 clean source 뒤 별도 인간 승인 없이는 실행하지 않는다.

동적 ACTIVE catalog enum은 provider schema에 복제하지 않는다. model은 계속 topic/coverage를
제안할 뿐이며 current ACTIVE/OFFICIAL membership과 source binding은 서버가 소유한다.

D-116 offline 구현은 이 addendum을 코드로 닫았다. provider wire parser는 nullable 4필드의
exact `NONE`만 내부 `None`으로 바꾸고 canonical parser의 JSON null 계약과 같은 server
validator를 재사용한다. request마다 새 strict five-key string schema를 만들며 bounded prompt는
동일한 canonical field와 sentinel을 사용한다. area 333·controlled-double actual-runner 24·
Ruff/Mypy 115 PASS이고 provider call/cost는 0이다. API/contracts/DB/data/dependency는 불변이며
Task 5 root/clean-source gate와 D-117 actual 인간 gate는 별도다.

## References

- Q-RAG-001=A, Q-DATA-RAG-001=A, Q-UX-REGION-001=A,
  Q-UX-CERT-001=A, Q-COST-001=A
- D-096~D-105, A-064~A-068
- `docs/superpowers/specs/2026-07-27-bounded-hybrid-rag-conversation-design.md`
- `docs/superpowers/plans/2026-07-27-bounded-hybrid-rag-conversation.md`
- `docs/superpowers/specs/2026-07-28-upstage-classifier-strict-five-key-wire-design.md`
- `docs/implementation-notes/IMP-20260727-021-*` through `IMP-20260728-001-*`
