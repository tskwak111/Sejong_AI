# 4일 local/private 핵심 개선 루프 MVP 설계

- 상태: **Approved — Q-MVP-001=A, 즉시 실행 승인**
- 승인 시각: 2026-07-22T02:10:11+09:00
- 마감: 2026-07-25 토요일
- 배포 경계: local/private only
- 관련: D-058, ADR-0020, DATA-SEED-002 승인 명세, D-045, ADR-0004, ADR-0010

## 1. 목표와 완료 정의

시민이 `/chat`에서 질문하면 서버가 원문을 request scope 밖으로 유출하지 않고 마스킹, 분류,
ACTIVE 공식 KB 검색, 근거 판정, 구조화 답변 또는 정책 폴백을 반환한다. 근거 부족 질문 한 건은
`/admin`에서 운영자가 확인·후보 작성하고 다른 승인자가 승인해 20번째 ACTIVE KB가 되며, 같은
질문을 다시 했을 때 공식 출처 답변으로 개선된다.

완료는 local/private 환경에서 아래 증거가 모두 있을 때만 주장한다.

- 초기 19 ACTIVE/OFFICIAL KB + 공식 기관 3 + 매핑 10 actual DB projection (2026-07-22 DATA-SEED PASS)
- `/api/v1/chat` SUCCESS/FOLLOWUP/FALLBACK/503와 `PRIVACY_UNRESOLVED`
- `/chat` current-tab transcript, source/office card, loading/error/empty/retry, 390/430 keyboard flow
- 실패 질문 → reason confirm → candidate → 다른 approver → 20번째 ACTIVE → same-query SUCCESS
- 최소 `/admin`과 self-approval/PII/unapproved ACTIVE 차단
- 표본 20, 회귀 1, privacy/secret/ACTIVE gate, local demo rehearsal

## 2. 비목표

- 실제 시민 DeepSeek 전송 또는 DeepSeek 품질 튜닝
- 100명 부하 결과, 자동 backup/restore scheduler, public URL/remote DB
- public admin, SSO/RBAC, `00700`, production CORS/secret/log 설정
- 고급 motion/visual polish, 새 페이지, P2 기능
- 새 production dependency

## 2.1 2026-07-22 fast-MVP 추가 확정

- Q-MVP-002=A: 개인 조회·법적 판단은 `intent=UNKNOWN`과 정확한 정책 reason, 후보 false이며
  local MVP에서는 질문 text·event·failed row를 저장하지 않는다.
- Q-DB-004=A: local/private 관리자 read capability를 immutable `00650` migration, rollback,
  pgTAP, repository adapter로 추가한다. public admin은 계속 금지한다.
- Q-API-002=A: optional UUID `Idempotency-Key`, 같은 logical retry key 유지, per-request
  correlation ID 분리와 immutable `00660` durable dedupe를 사용한다.
- durable record에는 domain-separated HMAC request digest, correlation과 무관한 claim token·5분
  lease와 안전 응답만 논리 TTL 24시간 저장한다. same-key conflict는 value-free 422, 살아 있는
  in-progress lease는 retryable 503, stale lease는 재획득하고 complete는 안전 응답을 replay한다.
  startup과 60초 주기 purge 실패 시 readiness를 닫는다.
- DATA-SEED-002 actual 4차는 승인·실행됐으나 concurrency B의 bounded
  `CAPABILITY_WRITE_DID_NOT_BLOCK`에서 중단됐다. 19/3/10 projection과 official-data 승격은 미완료다.
- 위 문장은 4차 시도의 역사적 중단 기록이다. observer 보정 뒤 승인된 supported continuation은
  immutable `.2`를 바꾸지 않고 19/3/10과 `official_data=0.1.0-initial.2`를 PASS했으며,
  2026-07-24 Q-PM actual 재실행은 최종 ACTIVE 20과 target 1을 확인했다.

## 3. 수직 흐름

```text
raw request scope
  -> redact_question
     -> unresolved: HTTP 200 PRIVACY_UNRESOLVED, text/source/context/office/provider/failed-row 0
     -> safe masked text
        -> deterministic intent classifier
        -> ambiguity gate -> FOLLOWUP
        -> policy gate -> PERSONAL_LOOKUP / LEGAL_JUDGMENT / OUT_OF_SCOPE
        -> ACTIVE+OFFICIAL KB lexical retrieval
        -> grounding gate
           -> grounded: server template SUCCESS + server-bound sources/optional office
           -> insufficient: FALLBACK + masked failed-question row
        -> metadata interaction event
  -> signed 15-minute client-carried context for SUCCESS/FOLLOWUP only
```

LLM provider는 이 흐름 뒤의 optional adapter seam으로만 남는다. 7월 25일 시민 경로는 항상
deterministic template를 사용한다.

## 4. 분류·검색·근거 gate

- intent는 기존 6개 값만 사용한다: 4개 지원 intent, `OUT_OF_SCOPE`, `UNKNOWN`.
- classifier는 bounded normalize + 승인된 키워드/구문 table이다. 두 지원 intent가 같은 최고
  우선순위로 충돌하거나 필수 대상이 빠지면 `FOLLOWUP`이다.
- personal lookup과 legal judgment high-signal policy rule은 retrieval보다 먼저 적용한다.
- 검색 입력은 `masked_text`, 선택된 region, signed context의 enum/ID뿐이다.
- repository는 intent별 `ACTIVE AND OFFICIAL` records만 반환한다.
- rank는 exact normalized question-example match, title/keyword token overlap, procedure/document field
  coverage 순의 deterministic tuple이다. 동점은 stable KB ID 순이다.
- SUCCESS는 top record의 intent 일치와 최소 1개의 질문 의미 token match를 모두 요구한다.
  금액·기한·법적 효과처럼 high-risk answer field는 top record의 해당 field가 비어 있으면 생성하지
  않는다. 조건을 못 채우면 `INSUFFICIENT_GROUNDING`이다.
- source title/URL/verified date와 office card는 LLM/template이 만들지 않고 DB record에서만 결합한다.

## 5. PII consumer와 응답 계약

- public `FallbackReason`에 `PRIVACY_UNRESOLVED`를 추가한다. 기존 값은 삭제·재해석하지 않는다.
- response는 HTTP 200 `answer_status=FALLBACK`, `intent=UNKNOWN`, `confidence=null`,
  `sources=[]`, `context_token=null`, `fallback.candidate_eligible=false`, office 없음이다.
- 시민 문구는 개인정보를 빼거나 표현을 바꿔 다시 질문하라는 고정 서버 copy다.
- unresolved raw/masked text, finding detail, source/context/office/provider payload, failed-question row,
  candidate는 모두 0이다. 7월 25일 local MVP는 DB event도 만들지 않고 safe request count만
  process-local test spy로 검증한다. 영속 metadata reason migration은 reserved `00700` 이후 별도다.
- 안전한 masked text만 classifier/retriever/failure writer에 전달한다. 실제 시민 text는 masked여도
  DeepSeek로 보내지 않는다.

## 6. context token

- HMAC-SHA-256, 900초, server secret은 local env에만 둔다.
- claims allowlist: schema version, issued/expiry epoch, last intent, selected region, answer status,
  optional followup-option ID. ADR-0010과 개인정보 정책의 더 좁은 기존 경계를 따라 ACTIVE KB ID는
  넣지 않는다.
- 질문·답변·masked text·PII·URL·source fact·actor/role은 넣지 않는다.
- invalid/expired/tampered token은 오류나 로그 없이 context 없음으로 reset한다.
- FALLBACK은 token을 반환하지 않는다. browser storage와 서버 DB/log에 token을 저장하지 않는다.

## 7. 실패·승인 상태 머신

```text
INSUFFICIENT_GROUNDING event
  -> failed NEW
  -> OPERATOR reason confirm
  -> REASON_CONFIRMED
  -> OPERATOR candidate create DRAFT
  -> submit PENDING_APPROVAL
  -> different APPROVER: APPROVED + atomic ACTIVE KB
  -> same query re-run SUCCESS
```

- FOLLOWUP, OUT_OF_SCOPE, PRIVACY_UNRESOLVED는 failed row 0.
- Q-MVP-002=A/D-059의 좁은 local MVP 정책에 따라 PERSONAL_LOOKUP와 LEGAL_JUDGMENT는
  질문 text·interaction event·failed row를 남기지 않고 candidate도 부적격이다.
- 후보 대표 질문은 PII core를 다시 통과해야 한다. finding이 있거나 unresolved면 value-free 422로
  거부하고 입력을 echo/log하지 않는다.
- 20번째 record는 `KB-WASTE-03`, official source를 기존 PM-approved staging에서 가져오며 author와
  reviewer identity가 달라야 한다.
- Q-PM-DEMO-001=B/D-068에서 개인조회 무저장 시연(#4)과 별도의
  INSUFFICIENT_GROUNDING 승인 루프(#5)를 분리한다.

## 8. 최소 API와 관리자 계약

- 기존 OpenAPI path를 유지하고 성공 body를 typed schema로 완성한다.
- list는 `{items, total}` envelope, create는 생성 ID/status, submit/review/reason confirm은 갱신된
  ID/status를 반환한다. error는 공통 value-free envelope를 사용한다.
- local demo actor는 server-validated fixed header allowlist로만 선택한다. 이 header는 인증이 아니며
  public mode에서는 admin router를 등록하지 않는다.
- audit는 action/actor/target/status/changed field metadata만 보이고 질문·답변 snapshot은 반환하지 않는다.

## 9. Frontend 경계

- Frontend 팀원은 `apps/web/src/**`, `tools/web-e2e/e2e/**`, 자신의 새 note와 INDEX append만 소유한다.
- owner가 contract/generated package와 package/lockfile 변경을 맡는다.
- fixture-first로 모든 화면 상태를 구현한다. default는 fixture이며 명시적 `ADMIN_UI_MODE=actual`은
  contract-frozen typed same-origin client를 사용한다. 2026-07-24 opt-in actual browser는
  real `/chat`·`/admin`·local API/DB 19→20 흐름을 PASS했다.
- transcript/context는 React memory만 사용하며 local/session storage, cookie, analytics에 쓰지 않는다.
- 390/430/desktop, semantic labels, visible focus, contrast 4.5:1, status text+icon을 최소 gate로 둔다.

## 10. 오류·복구

- DB/provider 장애라도 loaded ACTIVE snapshot으로 안전 응답 가능하면 200 template를 사용한다.
- 안전한 근거가 없으면 503 `SERVICE_UNAVAILABLE`; 질문 text를 error/log에 넣지 않는다.
- data release는 `.1`을 수정하지 않고 `.2` create-once다. actual 실패 시 `.2`는 보존하고
  `official_data`를 올리지 않는다.
- 후보 승인 transaction 실패 시 candidate와 ACTIVE KB가 부분 반영되면 안 된다.

## 11. 버전 전략

- 이 명세 문서화 시 product spec `2.2.5→2.3.0`, docs `2.10.9→2.11.0`.
- `PRIVACY_UNRESOLVED`와 initial admin response freeze는 API `3.0.0-draft`, shared `0.3.0`이었다.
  Approved idempotency continuation은 API `3.1.0-draft`, shared `0.4.0`으로 갱신하고 generated
  TypeScript/fixtures를 같은 change에서 동기화한다.
- DATA actual PASS 때만 official data를 `0.1.0-initial.2`로 올린다.
- 20번째 ACTIVE candidate는 DB runtime data lineage로 기록하고 immutable initial `.2` artifact에는
  섞지 않는다.

## 12. 인간/AI 경계

Q-MVP-001=A는 이 문서와 실행계획, DATA-SEED-002 실행, 위 local/private public-contract draft
변경을 승인한다. 팀원 계정 MFA/PR 병합, PM 역할의 20번째 source 검수, public/remote/DeepSeek
citizen/새 dependency/데이터 삭제 권한은 포함하지 않는다.

후속 D-068과 사용자의 PM source confirmation은 이 local/private Q-PM rehearsal의 기존 approved
자료 사용과 별도 승인자 시연을 허용했다. 이는 public admin 인증/RBAC 또는 remote/public 배포
승인이 아니다.
