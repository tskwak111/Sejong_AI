# Bounded Hybrid RAG Conversation — 통합 Written Specification

- Task ID: `CHAT-HYBRID-RAG-001`
- Status: Review — design sections 1~3 approved, written specification awaiting user review
- Date: 2026-07-27 KST
- Human authority: Q-RAG-001=A, Q-UX-REGION-001=A, Q-UX-CERT-001=A,
  Q-COST-001=A, Q-DATA-RAG-001=A, 설계 1·2·3부 승인
- Decision authority: D-096~D-102
- Extends: ADR-0025 and
  `2026-07-27-natural-civic-dialogue-and-operations-design.md`
- Preserves: 질문 원문 DB 미저장, provider 전 PII 마스킹, ACTIVE/OFFICIAL-only,
  server-owned facts/sources/offices, author≠reviewer, mock/official 분리

## 1. 목적

현재 시민 경로는 안전 정책과 bounded Upstage classifier를 갖췄지만 KB 선택과 grounding이
주로 한국어 lexical overlap에 의존한다. 승인 질문과 의미가 같아도 단어가 다르면 근거 부족으로
닫히고, 공통 단어가 있으면 서로 다른 대형폐기물·증명서 절차가 같은 답변으로 모일 수 있다.

이번 변경은 vector DB나 embedding 없이 다음을 달성한다.

1. 자유로운 한국어 표현을 현재 ACTIVE KB topic으로 더 잘 연결한다.
2. 모델에는 topic 제안 권한만 주고 행정 사실·출처·저장 권한은 주지 않는다.
3. 현재 KB가 보증하지 않는 구체적 사실은 답하지 않는다.
4. 모호 질문은 네 분야 전체가 아니라 해당 분야의 다음 선택지만 묻는다.
5. 지역·후속질문·오류 문구를 자연스럽게 만들고 local demo 호출 한도를 현실화한다.

기준 문장 `모르면 지어내지 않고, 알면 끝까지 안내한다`는 완화하지 않는다.

## 2. 범위

### 2.1 구현 범위

- ACTIVE/OFFICIAL runtime topic catalog
- versioned non-factual topic coverage metadata
- exact/lexical/semantic/context grounding evidence
- closed Upstage topic+coverage selection
- generic move/certificate/waste/tax topic FOLLOWUP
- certificate 첫 단계 3개와 차이 설명 뒤 관련 질문
- 같은 탭에서만 유지되는 상시 지역 selector
- local interactive provider caps 80/100/160과 USD 0.20 cost stop
- route별 사용자 문구·저장 회귀
- versioned synthetic UAT, PII-free actual subset, API/Web/DB/E2E/security gate

### 2.2 비범위

- vector DB, embeddings, reranker provider
- 새 production dependency
- DB migration 또는 official `.2` 수정
- 여러 KB의 절차·수수료·출처를 한 답변에 합성
- 냉장고 폐가전 전용 수거, 재산세 세율·감면 등 새 행정 사실 작성
- 가족관계증명서·여권·청년월세 등 지원 분야 확대
- production 사용자별 rate limit, 자동 budget reset, 공개 provider 운영
- public 관리자 활성화, 실제 신청·조회·결제·기관 시스템 연계

## 3. 검토한 접근

### A. ACTIVE topic catalog + bounded semantic selection — 선택

현재 ACTIVE/OFFICIAL KB에서 작은 catalog를 만들고, 결정론적 경로가 확신하지 못할 때만
Upstage가 closed topic/coverage를 제안한다. 서버가 현재 DB 상태와 grounding evidence를
재검증한다.

- 장점: 20 topic 규모에 맞고 새 인프라 없이 paraphrase recall을 높인다.
- 단점: catalog metadata와 semantic negative regression이 필요하다.

### B. lexical dictionary 확장 — 기각

알려진 표현은 빠르게 고칠 수 있지만 새 표현마다 같은 실패가 반복되고 동의어 표가 사실상
비정형 검색 엔진이 된다.

### C. vector/embedding RAG — 후속 검토

KB가 수백~수천 건으로 늘면 유리하지만 현재 규모에서는 비용·dependency·index lifecycle과
평가 복잡도가 가치보다 크다.

## 4. 전체 흐름

```text
strict request/context/idempotency validation
  → deterministic PII redaction
  → personal/legal/privacy/policy gate
  → one-request ACTIVE knowledge snapshot
  → exact approved/high-confidence deterministic selection
  → context topic/facet resolution
  → ambiguous-only Upstage closed topic+coverage selection
  → server catalog membership/intent/coverage validation
  → typed grounding evidence gate
  → top-1 ACTIVE KB
  → grounded generation or complete template
  → server-owned source/office/context
  → route-specific persistence
  → typed response
```

이 순서는 바꿀 수 없다. `safe_for_provider=false`이면 topic selector와 answer generator 호출은
모두 0이다.

## 5. ACTIVE knowledge snapshot과 topic catalog

### 5.1 request-local snapshot

- deterministic intent가 확실하면 해당 intent의 `list_active_kb()`를 한 번 호출한다.
- intent가 불확실해 semantic catalog가 필요하면 네 intent의 기존 read를 병렬 실행한다.
- 한 요청 안에서는 같은 immutable snapshot을 selection, grounding, response에 재사용한다.
- DB read API나 migration을 새로 만들지 않는다.
- snapshot은 process cache로 보관하지 않는다. 관리자가 20번째 KB를 ACTIVE로 승인한 직후 다음
  요청부터 반영되도록 한다.

### 5.2 versioned metadata

새 artifact:

```text
data/retrieval/topic-coverage.v1.json
data/retrieval/README.md
apps/api/tests/chat/fixtures/hybrid-rag-uat.v1.json
```

`topic-coverage.v1.json`은 행정 사실이 아닌 검색 경계다.

```json
{
  "schema_version": 1,
  "data_kind": "NON_FACTUAL_RETRIEVAL_METADATA",
  "topics": [
    {
      "topic_id": "KB-WASTE-01",
      "intent": "BULKY_WASTE",
      "coverage_id": "GENERAL_FURNITURE_DISPOSAL",
      "coverage_label": "일반 가구류의 대형폐기물 배출 절차. 폐가전 전용 수거와 품목별 미승인 요금은 제외"
    }
  ]
}
```

규칙:

- free-form answer, fee, deadline, source URL, office, legal conclusion을 넣지 않는다.
- topic ID는 official release 또는 runtime governed ACTIVE record와 연결될 수 있어야 한다.
- runtime catalog에는 metadata와 현재 ACTIVE/OFFICIAL snapshot의 교집합만 포함한다.
- runtime catalog 크기는 1~20이다. 0 또는 21 이상이면 provider selection을 사용하지 않는다.
- provider에는 topic ID, intent, service name, coverage ID/label, 승인 질문 예시 앞의 최대
  2개만 전달한다.
- question examples와 service name은 DB projection에서 가져오며 metadata가 덮어쓰지 않는다.
- 마스킹 질문은 기존 최대 1,024자를 유지하고, catalog를 포함한 전체 provider message는
  기존 보수적 입력 추정값 4,096 token 이하여야 한다. 초과하면 catalog를 임의 절단하거나
  일부 topic만 숨기지 않고 provider 호출 0의 안전 FOLLOWUP으로 닫는다.

## 6. Closed selector contract

내부 provider 결과의 target schema:

```json
{
  "route": "SUPPORTED | NO_TOPIC_MATCH | CIVIC_SCOPE_GAP | NON_CIVIC | NEEDS_FOLLOWUP",
  "intent": "supported-intent | null",
  "topic_id": "catalog-topic-id | null",
  "coverage_id": "catalog-coverage-id | null",
  "pending_slot": "DOMAIN | TOPIC_CHOICE | CERTIFICATE_KIND | REGION | WASTE_ITEM | null"
}
```

조합 규칙:

- `SUPPORTED`: supported intent, topic ID, coverage ID 필수; pending slot null
- `NO_TOPIC_MATCH`: supported intent 필수; topic/coverage/pending slot null
- `CIVIC_SCOPE_GAP`, `NON_CIVIC`: 나머지 값 모두 null
- `NEEDS_FOLLOWUP`:
  - `DOMAIN`이면 intent null
  - `TOPIC_CHOICE`, `CERTIFICATE_KIND`, `REGION`, `WASTE_ITEM`이면 supported intent 필수
  - topic/coverage는 null
- unknown key, free text, confidence, answer, source, retention, candidate field는 금지

모델은 catalog 밖 ID를 새로 만들 수 없다. 파싱 성공 뒤에도 서버가 다음을 순서대로 확인한다.

1. topic ID가 current request snapshot에 존재
2. record category와 returned intent 일치
3. coverage ID가 그 topic의 versioned metadata에 존재
4. record가 `KnowledgeRecord` ACTIVE/OFFICIAL projection
5. pending slot 조합이 intent와 일치

하나라도 실패하면 모델 출력 전체를 버리고 저장 없는 안전 FOLLOWUP으로 닫는다.

## 7. Grounding evidence

성공에는 다음 typed evidence 중 하나가 필요하다.

| evidence | 조건 |
|---|---|
| `EXACT_APPROVED_EXAMPLE` | normalized 질문이 해당 KB 승인 예시와 정확히 일치 |
| `UNIQUE_LEXICAL_MATCH` | intent 안에서 의미 anchor가 있고 top-1이 고유하며 score 기준 충족 |
| `VALIDATED_SEMANTIC_COVERAGE` | closed provider topic+coverage가 runtime 검증 통과 |
| `VALIDATED_CONTEXT_FACET` | 서명 context topic이 current ACTIVE이며 질문이 승인 field facet |

`allow_contextual_detail: bool`처럼 호출자가 임의로 넓힐 수 있는 경계 대신 typed evidence를
grounding 함수가 받는다.

추가 규칙:

- score가 모두 0이면 lexical 첫 record를 사용하지 않는다.
- topic이 invalid하면 다른 top-1으로 조용히 fallback하지 않는다.
- initial implementation은 KB 한 건만 사용한다.
- generation은 선택된 record의 server-issued fact ID만 사용할 수 있다.
- source title/URL/date/office는 모델 입력·출력이 아니라 서버 projection에서 결합한다.
- 생성 실패·fact mismatch·source mismatch는 생성 일부를 버리고 같은 KB의 전체 template로
  답한다.

## 8. route와 저장

| 상황 | 공개 결과 | 시민 질문 저장 |
|---|---|---|
| grounded topic | SUCCESS | 원문·masked text 0, 기존 value-free event만 |
| 두 topic이 모호 | FOLLOWUP | failed row 0 |
| supported intent지만 topic 없음 | FALLBACK / INSUFFICIENT_GROUNDING | 안전한 masked failed question |
| 범위 밖 행정 민원 | FALLBACK / CIVIC_SCOPE_GAP | 별도 30일 scope queue |
| 날씨 등 비행정 | FALLBACK / OUT_OF_SCOPE | text/event/failed/scope row 0 |
| personal/legal/privacy unresolved | 기존 policy fallback | text/event/failed/scope row 0 |
| classifier cap/timeout/invalid JSON | domain FOLLOWUP | text/event/failed/scope row 0 |
| generation 실패 | 같은 grounded KB TEMPLATE | 질문 text 0 |
| DB 불능으로 안전 응답 불가 | 503 SERVICE_UNAVAILABLE | temp/raw 저장 0 |

`INSUFFICIENT_GROUNDING`만 기존 사유 확인→후보→별도 승인→ACTIVE 흐름에 들어간다.
`CIVIC_SCOPE_GAP`은 자동 candidate/ACTIVE로 연결하지 않는다.

## 9. context와 topic 전환

context token은 기존 15분 signed v2를 유지하고 free text를 추가하지 않는다.

- `topic_id`, `last_intent`, `pending_slot`, `selected_region`, `dialog_act`만 사용한다.
- context topic은 매 요청 current ACTIVE snapshot에서 재검증한다.
- `수수료`, `준비물`, `처리기간`, `어디`, `온라인`은 current record의 해당 승인 field가 있을
  때만 `VALIDATED_CONTEXT_FACET`으로 답한다.
- `취소하려면?`처럼 같은 intent의 다른 topic을 요구하면 intent sibling catalog로 재선택한다.
- 새 분야를 명시하면 이전 topic을 버리고 `CHANGING_TOPIC`으로 처리한다.
- invalid/expired token은 no-context로 재분류하고 오류 정보를 노출하지 않는다.

## 10. 분야별 FOLLOWUP

### 10.1 증명서

generic certificate의 첫 선택지는 정확히 세 개다.

1. 주민등록등본 발급
2. 주민등록초본 발급
3. 등본과 초본의 차이

세 번째는 `KB-CERT-01`로 SUCCESS를 반환한다. Web은 response source가 `KB-CERT-01`일 때
`주민등록표 열람`, `무인민원발급기 이용` 두 client suggestion을 표시한다. suggestion은
답변이나 사실이 아니며 클릭하면 새 chat request로 서버 검증을 다시 거친다.

가족관계증명서·여권은 이 선택지에 넣지 않고 `CIVIC_SCOPE_GAP`이다.

### 10.2 전입·주민등록

generic 질문은 최대 네 개를 제시한다.

- 전입신고 방법
- 방문 신고 준비물
- 온라인 전입신고
- 주민등록 통보서비스

법적 판단·개인 상태 조회는 topic choice 전에 policy gate가 처리한다.

### 10.3 대형폐기물

generic 질문은 current ACTIVE catalog에서 최대 다섯 개를 제시한다.

- 배출 신청
- 결제·스티커·변경·환불
- 침대 프레임 관련 승인 안내—20번째가 ACTIVE인 경우만
- 매트리스 수수료
- 배출요일·수거 문의

냉장고의 폐가전 전용 수거·미승인 수수료 질문은 `NO_TOPIC_MATCH` 후
`INSUFFICIENT_GROUNDING`이다.

### 10.4 지방세

`재산세 일반 안내`처럼 목적이 모호하면 다음 current ACTIVE topic 중 최대 다섯 개를 제시한다.

- 지방세 온라인 납부
- 자동차세 납부
- 지방세 납세증명서
- 세목별 과세증명서
- 지방세 납부확인서

재산세 부과 기준·세율·감면·개인 고지액은 현재 근거로 성공시키지 않는다.

Followup response는 기존 공개 `followup_options: string[]`을 유지한다. 새 field를 추가하지
않지만 option 값과 동작이 바뀌므로 OpenAPI/JSON Schema 예시, backend, generated consumer,
Web fixture를 함께 갱신한다. topic 선택지는 current ACTIVE record의 server-owned service label이며,
클릭하면 같은 context token과 그 label을 새 질문으로 보내 전체 server 검증을 다시 거친다.

## 11. 지역 선택

- 입력창 바로 위에 항상 compact하게 표시한다.
- 미선택: `거주 지역 선택 · 선택사항`
- 선택 후: `<지역명> · 변경`
- 첫 화면부터 보이며 일반 질문 답변의 필수 조건이 아니다.
- `새 대화`는 transcript, context token, topic, pending slot을 버리지만 same-tab React state의
  region은 유지한다.
- reload, new tab, browser close에서는 region을 초기화한다.
- local/session storage, cookie, server profile, DB에 저장하지 않는다.
- native/select-equivalent keyboard interaction, visible focus, accessible name, 44px target,
  본문 대비 4.5:1 이상을 요구한다.

## 12. 사용자 문구

| 상황 | 문구 |
|---|---|
| unknown domain | `어떤 민원 안내가 필요한지 조금만 더 알려주세요.` |
| certificate | `어떤 주민등록 증명서가 필요하신가요?` |
| supported topic choice | `<분야>에서 어떤 안내가 필요하신가요?` |
| insufficient grounding | `지원 분야이지만 현재 승인된 공식 자료에서 직접 답할 근거를 찾지 못했어요.` |
| civic scope gap | `아직 지원하지 않는 민원이에요. 지원 범위 확대 검토 대상으로 분류할 수 있어요.` |
| non-civic | `현재는 세종시 행정 민원 안내를 도와드리고 있어요.` |
| provider failure/cap | `잠시 정확한 분류가 어려워요. 아래 분야를 골라 주세요.` |

시민 문구에는 provider 이름, API key, quota count, 내부 route, stack trace를 표시하지 않는다.
scope/failed queue write는 best-effort이므로 저장 성공을 단정하는 문구를 쓰지 않는다.

## 13. local provider budget

새 local interactive profile:

| lane | process cap | timeout | retry | request max |
|---|---:|---:|---:|---:|
| classifier | 80 | 3초 | 0 | 1 |
| generator | 100 | 8초 | 0 | 1 |
| combined | 160 | request hard wall 12초 | hidden retry 0 | 2 |

추가 경계:

- concurrency 1
- VAT 포함 process cost cap USD 0.20
- 실제 누적 cost와 다음 lane의 configured worst-case cost를 합쳐 cap을 넘으면 호출 전에 차단
- process 실행 중 counter/cost reset 금지
- process restart 시 초기화되며 자동·주기적 reset 없음
- cap/timeout/invalid provider response는 저장 없는 FOLLOWUP 또는 grounded TEMPLATE
- `UPSTAGE_*_MODE=false`이면 outbound 0

기존 20/30/40·USD0.05 actual acceptance evidence는 역사적 결과로 보존한다. 새 target은
구현·검증 전 완료 상태가 아니다. production rate limit과 public provider 운영은 별도 결정이다.

## 14. versioned UAT와 acceptance

### 14.1 offline corpus

`hybrid-rag-uat.v1.json`은 정확히 48개 synthetic case를 가지며 실제 개인정보는 포함하지 않는다.
privacy group은 명백한 테스트 전용 PII-shaped 값을 사용할 수 있지만 provider expected-use는
항상 0이고 report에는 원문을 기록하지 않는다.

| group | count |
|---|---:|
| 네 intent 자유 paraphrase SUCCESS | 20 |
| 같은 intent 안의 topic distinction | 8 |
| generic intent FOLLOWUP | 4 |
| supported but no topic → IG | 4 |
| civic scope/non-civic | 4 |
| context facet/topic change | 4 |
| privacy/policy 저장 경계 | 4 |

각 case는 expected route, intent, topic ID 또는 null, fallback/followup, provider expected-use,
storage policy를 명시한다. 질문은 사용자가 보고한 비식별 문장과 합성 문장만 사용하며
official fact로 표시하지 않는다.

### 14.2 필수 회귀

- immutable `.2`의 승인 질문 예시 57/57 올바른 KB
- 기존 frozen classifier 60/60, skip 0
- 새 UAT 48/48, skip 0
- 다음 핵심 사례:
  - `새 집으로 옮긴 뒤 행정상 거주지를 바꾸는 절차` → MOVE success
  - `큰 장롱` → WASTE general success
  - `대형폐기물 취소` → WASTE-02
  - `냉장고 전용 수거` → IG
  - generic certificate → 정확히 3 options
  - family certificate/young rent → scope gap
  - `재산세 일반 안내` → TAX topic followup
  - 재산세 세율/감면 → IG
  - weather → OUT_OF_SCOPE, row 0
  - phone+move → phone masked, move success, raw value leak 0

### 14.3 actual subset

offline 전체 gate 뒤 UAT에서 PII-free 20개를 고정 선택해 actual Upstage를 한 번 실행한다.

- paraphrase 8
- topic distinction 4
- no-topic/followup 4
- scope/non-civic 4

raw provider payload, 질문 본문, key를 report에 저장하지 않는다. case ID, route/topic match,
outbound count, token aggregate, VAT 포함 cost만 기록한다.

### 14.4 영역·전체 gate

- API: format/lint/type/test, catalog/classifier/retrieval/grounding/service/storage
- contracts: OpenAPI/JSON Schema/Pydantic/generated TypeScript drift
- Web: lint/type/test/build, 390/430/desktop E2E, keyboard/focus/accessibility
- DB: IG row→admin list→candidate→different approver→ACTIVE regression, policy/scope row separation
- root: repository docs, package/lockfile, secret/PII scan, protected diff, `git diff --check`

수직 흐름마다 집중 테스트를 실행하고, 통합 직전에 영역 gate, Draft PR 전 저장소 전체 gate를
한 번 실행한다.

## 15. 구현 순서

### Slice 1 — metadata와 server catalog

RED: metadata validator, active intersection, max 20, inactive/mock exclusion, request snapshot.
GREEN: versioned metadata/loader, typed catalog builder, current repository reads 재사용.

### Slice 2 — semantic selector와 grounding

RED: closed `coverage_id`, invalid combinations, no arbitrary top-1, typed evidence, no-topic mapping.
GREEN: classifier contract/prompt/adapter, server validator, retrieval/grounding orchestration.

### Slice 3 — context와 분야별 FOLLOWUP

RED: generic move/certificate/waste/tax, fee/docs/office, topic switch, certificate 3 options.
GREEN: pending slot transition, server-owned choices, response examples.

### Slice 4 — Web UX와 local budget

RED: always-visible region, new-chat region retention, reload reset, context suggestions,
provider failure copy, 80/100/160 and USD0.20 pre-reservation.
GREEN: Web state/components, settings/ledger/cost accounting.

### Slice 5 — operations and integration

RED: IG admin row, scope/policy/provider row separation, 48 UAT, actual 20, browser matrix.
GREEN: integration corrections, full gate, version/doc/note/handoff.

새 production dependency 또는 DB migration이 필요해지면 이 계획을 중단하고 별도 인간 승인을
받는다.

## 16. 롤백과 복구

- feature rollback: catalog/semantic selector를 제거하고 기존 deterministic lexical/template로
  복귀한다.
- provider rollback: `UPSTAGE_CLASSIFIER_MODE=false`,
  `UPSTAGE_GROUNDED_CHAT_MODE=false`로 outbound 0.
- metadata rollback: versioned file과 loader를 함께 되돌린다. official `.2`는 건드리지 않는다.
- Web rollback: 기존 region/certificate option behavior로 되돌리되 public contract field는 동일하다.
- DB rollback은 없다. 새 migration/data write가 없기 때문이다.
- actual test 뒤 provider process를 종료해 in-memory ledger를 폐기한다. 질문이나 payload를
  복구·보관하지 않는다.

## 17. 버전 목표

| 축 | 현재 | 구현 목표 |
|---|---|---|
| product spec | 2.6.0 | 유지 |
| application | 0.11.1-classifier-runtime | 0.12.0-bounded-hybrid-rag |
| Web | 0.7.0-natural-dialogue | 0.8.0-guided-chat |
| API | 4.0.0-draft | 유지—새 public field 없음 |
| shared contracts | 1.0.0 | 유지 또는 example-only patch |
| DB | 0.5.0-local | 유지 |
| official data | 0.1.0-initial.2 | 유지 |
| prompt set | 0.3.1-hybrid-classifier | 0.4.0-topic-coverage |
| test suite | 1.9.2-classifier-runtime | 2.0.0-bounded-hybrid-rag |
| documentation | 2.25.1 | 2.26.0 written specification |

실제 구현 결과에 따라 목표 version은 실행계획과 완료 노트에서 한 번 더 검증한다.

## 18. 인간과 AI 책임

### 인간이 알아야 하는 내용

- 새 공식 사실을 추가하지 않으므로 냉장고·재산세 상세는 당분간 근거 부족이다.
- 마스킹된 ambiguous 질문은 local/private에서 Upstage로 전송될 수 있다.
- followup option의 값과 사용자 동작이 바뀐다.
- USD0.20은 local process cap이며 production 예산·rate limit이 아니다.
- actual provider, public/remote, official-data 추가는 각각 별도 권위 경계를 유지한다.

### AI 내부 구현 세부

- typed helper/file split, deterministic scoring constants, fixture generator, component split,
  formatting·lint 조정은 이 명세 안에서 자율 처리할 수 있다.

## 19. 자체 검토 결과

- Placeholder scan: PASS — 빈 값이나 미완성 요구 없음.
- Internal consistency: PASS — catalog는 ACTIVE snapshot과 교집합, top-1과 server-owned source가
  모든 SUCCESS 경로에서 일치한다.
- Scope check: PASS — DB migration, new facts, vector/embedding을 제외한 단일 vertical feature다.
- Ambiguity check: PASS — generic 재산세는 topic FOLLOWUP, 세율·감면은 IG로 구분했다.
- Privacy/security check: PASS — provider 전 redaction, invalid model output 무저장, source 생성 금지.
- Compatibility check: PASS — public response field는 유지하며 option behavior만 synchronized update한다.

이 문서는 사용자 written-spec review 전 구현 권위가 아니다. 승인 후 별도 실행계획이 RED/GREEN
task, exact file, 명령, checkpoint를 고정한다.
