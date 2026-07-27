# Natural Civic Dialogue and Operations — 통합 Written Specification

- Task ID: `CHAT-NATURAL-001`
- Status: Approved / self-review 2 of 2 PASS
- Date: 2026-07-27 KST
- Human authority: Q-CLASS-001=A, Q-CLASS-002=A, Q-SCOPE-001=A,
  Q-PROD-REAL-001=A, 설계 1·2·3부 승인, actual/DB/public·remote 실행 승인
- Supersedes as implementation authority:
  `2026-07-26-certificate-category-followup-design.md`와 그 실행계획의 미구현 범위
- Preserves: 원문 DB 미저장, provider 전 PII 마스킹, ACTIVE/OFFICIAL-only,
  server-owned source, author≠reviewer, mock/official 분리

## 1. 목적과 성공 모습

시민의 자연스러운 한국어 질문을 안전하게 분류하고, 승인된 공식 KB가 있으면 근거·절차·기관까지
안내한다. 질문이 모호하면 대화 맥락을 원문 없이 구조화해 필요한 한 가지만 다시 묻는다. 네 지원
분야 밖의 행정 민원은 답을 지어내지 않고 별도 범위확대 검토 대상으로만 보관한다.

이번 구현이 끝나면 다음 질문이 서로 다른 올바른 경로를 가진다.

| 질문 | 최종 route | 시민 동작 | 저장 |
|---|---|---|---|
| `증명서 발급해야해` | `NEEDS_FOLLOWUP` / certificate | 어떤 증명서인지 질문 | text/failed row 0 |
| `가족관계증명서 어떻게 발급받아요?` | `CIVIC_SCOPE_GAP` | 현재 지원 범위 밖 안내 | 별도 queue masked text 1 |
| `청년 월세 지원 어떻게 해요?` | `CIVIC_SCOPE_GAP` | 현재 지원 범위 밖 안내 | 별도 queue masked text 1 |
| `오늘 날씨 어때요?` | `NON_CIVIC` | 민원 질문을 요청 | 모든 질문/event/review row 0 |
| 개인 처리상태·법적 판단 | policy route | 안전 안내 | 모든 질문/event/failed/review row 0 |

## 2. 범위와 비범위

### 2.1 구현 범위

1. 일반 한국어를 이름으로 오탐하는 PII rule의 최소 교정
2. deterministic safety/high-confidence fast path와 bounded Upstage classifier
3. certificate category FOLLOWUP
4. context token v2와 5종 후속대화
5. 첫 지역 선택과 새 대화 초기화
6. `CIVIC_SCOPE_GAP` 공개 계약과 별도 30일 검토 queue
7. local/private 관리자 scope-gap 조회·검토
8. WASTE-03 고정 Web builder를 일반 eligible IG 후보 작성 폼으로 교체
9. local DB reset·immutable `.2` seed·19→20 회귀
10. synthetic PII-free actual Upstage classifier 검증
11. public hardening `00700` 구현과 구성된 remote 시민 경로 검증

### 2.2 계속 비범위

- 실제 신청 제출, 처리상태 조회, 결제, 정부24·기관 내부 시스템 transaction
- GPS·내장 지도, 다국어·음성, SSO/RBAC/전자결재
- public 관리자 UI/API 활성화. 인증·권한 시스템이 없으므로 remote에서는 admin router를
  fail-closed로 비활성화한다.
- raw 대화 transcript, 시민 프로필, 질문 원문의 DB·로그·context 저장
- 모델이 출처·기관·KB·보관·candidate eligibility·승인 여부를 결정하는 동작

## 3. 검토한 접근과 선택

### A. Privacy-first hybrid pipeline — 선택

PII와 명백한 정책·지원/비민원 분류는 서버가 결정하고, 안전하게 마스킹됐지만 taxonomy가
애매한 현재 질문만 bounded LLM에 전달한다.

- 장점: 비용·지연과 외부 전송을 줄이면서 새 한국어 표현 recall을 높인다.
- 단점: deterministic/LLM 결과를 합치는 route validator와 장애 경로가 필요하다.

### B. 모든 질문을 LLM이 분류 — 기각

표현 recall은 높을 수 있지만 PII·비용·지연·공급자 장애 표면이 넓고 서버 권위가 약해진다.

### C. deterministic term table만 확장 — 기각

알려진 fixture는 고치지만 새로운 표현이 들어올 때 같은 오분류가 반복된다.

## 4. 전체 요청 파이프라인

```text
HTTP request
  → strict request/context/idempotency validation
  → deterministic PII redaction
  → policy/high-confidence deterministic route
  → ambiguous-only Upstage closed classifier
  → server route validation
  → context transition
  → ACTIVE/OFFICIAL retrieval and grounding
  → grounded generation or complete template fallback
  → server-owned sources/office/context binding
  → route-specific persistence
  → typed response
```

순서는 바꿀 수 없다. PII redaction이 `safe_for_provider=false`이면 classifier와 generator 호출은
모두 0이다. classifier가 제안한 `SUPPORTED`도 서버 retrieval에서 ACTIVE 근거가 없으면
`INSUFFICIENT_GROUNDING`이다.

## 5. Closed route와 서버 검증

### 5.1 내부 classifier 결과

모델 출력은 JSON object 하나이며 추가 key를 금지한다.

```json
{
  "route": "SUPPORTED | CIVIC_SCOPE_GAP | NON_CIVIC | NEEDS_FOLLOWUP",
  "intent": "MOVE_IN_RESIDENT_REGISTRATION | CERTIFICATE_ISSUANCE | BULKY_WASTE | LOCAL_TAX_GENERAL | null",
  "topic_id": "server-known-topic-id | null",
  "pending_slot": "CERTIFICATE_KIND | REGION | WASTE_ITEM | null"
}
```

검증 규칙:

- `SUPPORTED`: intent 필수, pending_slot null
- `CIVIC_SCOPE_GAP`, `NON_CIVIC`: intent/topic/pending_slot 모두 null
- `NEEDS_FOLLOWUP`: intent는 null 또는 supported intent, pending_slot 필수
- 자유 문장, confidence, source, answer, retention, candidate field는 허용하지 않는다.
- `topic_id`는 현재 ACTIVE/OFFICIAL catalog에 존재하는 server-known ID만 허용한다.
- invalid JSON, unknown enum, forbidden combination은 출력 전체를 폐기한다.

### 5.2 공개 응답 매핑

| 내부 route | public intent | answer status / fallback reason | candidate |
|---|---|---|---|
| `SUPPORTED` + grounded | supported intent | SUCCESS | false |
| `NEEDS_FOLLOWUP` | resolved intent 또는 UNKNOWN | FOLLOWUP | false |
| `CIVIC_SCOPE_GAP` | OUT_OF_SCOPE | FALLBACK / CIVIC_SCOPE_GAP | false |
| `NON_CIVIC` | OUT_OF_SCOPE | FALLBACK / OUT_OF_SCOPE | false |
| personal lookup | UNKNOWN | FALLBACK / PERSONAL_LOOKUP | false |
| legal judgment | UNKNOWN | FALLBACK / LEGAL_JUDGMENT | false |
| unsafe redaction | UNKNOWN | FALLBACK / PRIVACY_UNRESOLVED | false |
| supported, no grounding | supported intent | FALLBACK / INSUFFICIENT_GROUNDING | true |

`CIVIC_SCOPE_GAP` enum 추가는 exhaustive consumer에 영향을 주는 공개 계약 변경으로 취급한다.
OpenAPI, JSON Schema, Pydantic, generated TypeScript, fixture와 Web label을 같은 commit series에서
갱신한다.

## 6. PII 교정

현재 contextual person-name heuristic가 일반 의문 표현과 행정 명사를 사람 이름으로 오인한다.
교정은 허용 목록을 무한히 늘리지 않고 다음 순서를 따른다.

1. frozen positive PII corpus를 그대로 통과시킨다.
2. 실제 오탐과 일반 행정 문장 negative corpus를 먼저 RED test로 추가한다.
3. 이름 판단은 이름 주변의 명시적 관계·호칭·자기소개 문맥과 형태 조건을 함께 요구한다.
4. 안전성을 증명할 수 없는 변경은 적용하지 않는다.
5. 일반어 false positive 목표는 acceptance corpus에서 0이고 기존 positive recall은 감소 0이다.

## 7. 자연스러운 FOLLOWUP과 context token v2

### 7.1 context v2 claims

서버 issuer는 다음 closed claims만 발급한다.

```text
version=2
issued_at, expires_at, nonce
last_intent
selected_region
answer_status
topic_id?
pending_slot? = CERTIFICATE_KIND | REGION | WASTE_ITEM
dialog_act? = ANSWERED | ASKING_SLOT | CHANGING_REGION | CHANGING_TOPIC
```

금지 claims: raw/masked question, answer/source/office body, transcript, 이름·주소·전화번호, auth role.
TTL은 15분이다. v1 token은 최대 남은 TTL 동안 decode만 하고 v2 issuer만 사용한다. invalid/expired
token은 오류를 노출하지 않고 no-context로 처리한다. topic은 매 요청 ACTIVE/OFFICIAL catalog에서
재검증한다.

### 7.2 전이

| 현재 상태 | 시민 입력 | 다음 동작 |
|---|---|---|
| certificate + `CERTIFICATE_KIND` | 등본/초본 등 | 해당 topic retrieval |
| success topic | `비용은요?` | 같은 topic의 fee만 grounded answer |
| success topic | `준비물은요?` | required documents |
| success topic | `온라인도 돼요?` | approved channel/procedure |
| success topic | `어디로 가요?` | selected region이 없으면 REGION FOLLOWUP, 있으면 official office |
| any supported | 지역 선택/변경 | selected_region 갱신 후 office 재결합 |
| any | 새 분야의 명백한 질문 | CHANGING_TOPIC 후 새 intent |
| Web 새 대화 | 클릭 | transcript와 context token 모두 폐기 |

generic `증명서 발급해야해`는 `CERTIFICATE_ISSUANCE`,
`pending_slot=CERTIFICATE_KIND`로 다음 5개 server-owned option을 반환한다.

1. 주민등록등본 발급
2. 주민등록초본 발급
3. 등본과 초본의 차이
4. 주민등록표 열람
5. 무인민원발급기 이용

## 8. Provider 경계·오류·성능

### 8.1 호출 예산

| 목적 | timeout | attempts | retry | input/output | process sub-cap |
|---|---:|---:|---:|---:|---:|
| classifier | 3초 | 1 | 0 | 1,024자 / 128 token | 20 |
| grounded generator | 8초 | 1 | 0 | 기존 4,096 token / 1,024 token | 30 |

- 요청당 provider 최대 2회, process combined cap 40
- hidden retry/counter reset 금지, concurrency 1
- synthetic actual run VAT 포함 USD 0.05 hard stop
- 요청 hard wall 12초
- deterministic local p95 목표 1초 이하
- classifier-only p95 목표 3.5초 이하

Web은 2초 뒤 `질문 분야를 확인하고 있어요`, 6초 뒤
`공식 안내를 정리하고 있어요`를 표시한다. timer는 응답 시 해제하고 screen reader live region을
중복 announce하지 않는다.

### 8.2 오류 행렬

| 실패 | 결과 |
|---|---|
| PII 안전 문자열 생성 실패 | PRIVACY_UNRESOLVED, provider/storage 0 |
| classifier timeout/429/5xx/invalid JSON/cap | 출력 폐기, 저장 없는 안전한 domain FOLLOWUP |
| NON_CIVIC/CIVIC_SCOPE_GAP | answer generator 호출 0 |
| ACTIVE search/grounding 실패 | INSUFFICIENT_GROUNDING |
| generation/source/fact validation 실패 | 생성 일부를 쓰지 않고 전체 template |
| invalid/expired context | no-context로 재분류 |
| scope queue write 실패 | 시민 정책 응답 유지, 저장 성공을 주장하지 않음 |
| application DB 불능 | 503 SERVICE_UNAVAILABLE, temp/raw 질문 저장 0 |

## 9. `CIVIC_SCOPE_GAP` 데이터·API·관리자

### 9.1 migration

local/private 기능은 immutable forward
`20260727000680_civic_scope_gap_queue.sql`과 matching rollback,
`supabase/tests/database/010_civic_scope_gap_queue_test.sql`로 추가한다. 이미 적용된
00100~00670은 수정하지 않는다.

table `app_private.civic_scope_gaps`:

| column | rule |
|---|---|
| `id uuid` | PK, server/DB 생성 |
| `masked_question text` | PII-safe only, nullable after purge |
| `status text` | `NEW | PLANNED | DISMISSED` |
| `created_at`, `updated_at` | timestamptz |
| `text_expires_at` | created_at + 30 days |
| `text_purged_at` | purge 때 설정 |
| `reviewed_by`, `reviewed_at`, `review_comment` | terminal state에서 필수 |

금지:

- interaction event, failed question, KB candidate, ACTIVE KB로의 FK
- raw question, answer snapshot, source snapshot, context token
- 자동 candidate 또는 ACTIVE 전환

backend capabilities:

- `app_api.record_civic_scope_gap(text)`
- `app_api.list_civic_scope_gaps(text)`
- `app_api.review_civic_scope_gap(uuid,text,text,text,text)`
- `app_api.purge_expired_civic_scope_gap_text()`

`NEW → PLANNED|DISMISSED`만 허용하고 terminal state 재검토는 거부한다. review actor는
local/private APPROVER header capability를 사용한다.

### 9.2 API

- `GET /api/v1/admin/civic-scope-gaps?status=NEW|PLANNED|DISMISSED`
- `PATCH /api/v1/admin/civic-scope-gaps/{id}/review`

review body:

```json
{"decision":"PLANNED | DISMISSED","review_comment":"non-empty"}
```

public/remote에서는 admin router가 계속 비활성이다. 시민 chat 기록은 best-effort이고 queue write
장애가 chat 정책 응답을 503으로 바꾸지 않는다.

## 10. 일반 KB 후보 작성

Backend의 기존 eligible IG 검증·공식 source allowlist·별도 승인자 invariant를 재사용한다.
Web의 WASTE-03 고정 draft builder만 일반 구조화 폼으로 교체한다.

필수 입력:

- failure ID, title, representative question
- category, answer summary, procedure steps
- required documents, processing time, fee, department, caution
- official source title/URL, last verified date

클라이언트가 public KB ID를 지정하지 않는다. server가 ID를 결합한다. mock·PII·허용되지 않은
source URL·자기승인·review comment 없음은 거부한다. 화면은 DRAFTED, PENDING_APPROVAL,
APPROVED, REJECTED 상태와 count를 구분하고 `운영자가 작성한 공식 KB 후보`라고 표시한다.

## 11. public/remote hardening과 실행 승인

사용자는 2026-07-27 actual Upstage, DB reset/seed, public/remote 작업을 승인했다. 이 승인은
다음 안전 조건으로 실행한다.

1. public hardening migration `20260727000700_privileged_function_search_path.sql`은 ADR-0018의
   exact 22 signature property만 `search_path=pg_catalog, pg_temp`로 변경한다.
2. matching rollback과 catalog/behavior pgTAP을 만든다. 함수 body, GRANT, data는 바꾸지 않는다.
3. remote target·credential·allowed origin이 실제 환경에 구성된 경우에만 deploy한다.
4. secret/DSN은 출력·commit하지 않는다. migration/seed 실패 시 official_data를 승격하지 않는다.
5. remote 시민 `/health`, `/ready`, `/api/v1/chat`, `/api/v1/offices`만 검증한다.
6. 인증 없는 `/admin`과 관리자 API는 remote/public에서 비활성임을 negative test한다.
7. 실제 Upstage 검증은 synthetic PII-free allowlisted fixture만 사용한다.
8. public/remote target이 구성되지 않았으면 코드·migration·runbook 검증까지 완료하고
   `Not executed: target not configured`로 증거를 남긴다. target을 추측하거나 새 계정을 만들지 않는다.

## 12. 계약·버전 목표

| 축 | 설계 문서 후 | 구현 목표 |
|---|---|---|
| product spec | 2.6.0 | 유지 |
| application | 0.10.0-office-directory-runtime | 0.11.0-natural-dialogue |
| Web | 0.6.0-answer-mode | 0.7.0-natural-dialogue |
| API | 3.3.0-draft | 4.0.0-draft |
| shared contracts | 0.6.0 | 1.0.0 |
| DB | 0.4.0-local | 0.5.0-local, public evidence 별도 |
| prompt set | 0.2.0-grounded-live-chat | 0.3.0-hybrid-classifier |
| test suite | 1.8.0-local-demo-readiness | 1.9.0-natural-dialogue |
| docs | 2.23.0 | 구현 노트에서 순차 증가 |

API/shared major bump는 새 fallback enum을 모르는 exhaustive consumer의 호환성 파괴 가능성을
정직하게 반영한다. context token v2는 wire request/response field를 늘리지 않지만 old token
read-only TTL compatibility를 보장한다.

## 13. 수직 구현 순서

### Slice 1 — 안전한 분류와 증명서 FOLLOWUP

PII negative corpus → hybrid classifier contract/adapter/limits → server routing →
certificate FOLLOWUP → provider-failure tests.

### Slice 2 — 구조화 문맥과 자연스러운 후속대화

context v2 → fee/docs/online/office followups → region select/change → new conversation →
Web latency and accessibility.

### Slice 3 — 범위확대 운영

00680 forward/rollback/pgTAP → repository/service/API → local admin UI →
general candidate form and state views → purge.

### Integration — actual/local/public

00700 security hardening → clean DB reset → immutable `.2` formal seed →
19→20 approval regression → actual Upstage synthetic run → configured remote deploy/smoke.

## 14. Acceptance criteria

1. 보고된 4개 오분류 fixture가 정확한 route를 반환한다.
2. exact 60 synthetic classification: supported variants 20, non-civic 10,
   civic scope gap 10, followup 10, policy/privacy 10; skip 0.
3. 일반 한국어 PII negative false positive 0; frozen positive regression 감소 0.
4. fee/docs/online/office/region-or-topic-change 후속대화 5종 PASS.
5. provider failure 7종이 안전한 FOLLOWUP/template로 닫힌다.
6. NON_CIVIC/PERSONAL/LEGAL/PRIVACY 질문 text·event·failed/review row 0.
7. CIVIC_SCOPE_GAP 별도 row 1, 30일 purge, candidate/ACTIVE link 0.
8. ACTIVE/OFFICIAL-only, source mismatch 0.
9. API/Pydantic/generated TS/Web drift 0.
10. 390/430/desktop, keyboard, focus, new conversation E2E PASS.
11. raw question/transcript/token/secret leak 0, new production dependency 0.
12. local DB reset·`.2` seed 19 ACTIVE/office 3/mapping 10, 별도 승인으로 20 ACTIVE,
    `/ready=200`.
13. actual Upstage run은 PII-free fixture, outbound/cost cap 준수, 결과와 비용만 집계.
14. public hardening pgTAP·rollback PASS. 구성된 remote가 있으면 citizen smoke PASS와 admin
    negative PASS; 없으면 정확한 미실행 이유 기록.

## 15. 테스트 전략

- 각 변경은 RED test → 최소 구현 → GREEN → area gate 순서다.
- Slice 1: privacy, classification, chat service/response, LLM adapter tests.
- Slice 2: context/service/Web unit, 390/430/desktop Playwright.
- Slice 3: DB pgTAP/rollback/replay, repository/admin API/Web E2E.
- Integration: shared generate/check, API full, Web lint/type/test/build, DB full, root verify,
  docs/package/secret/diff.
- 실제 provider·DB·remote 검증은 unit gate 후 한 번씩 수행하고 raw payload를 출력하지 않는다.

## 16. 롤백·복구

- Slice 1/2: code revert, provider modes false, v2 issuer 비활성 후 남은 v1 TTL read-only.
- 00680: terminal scope rows가 없고 retention 증거를 보존한 상태에서 matching rollback.
- 00700: matching rollback으로 exact 22 function property를 이전 값으로 복원.
- DB reset/seed: approved `.2` seed-cycle과 verify-final runbook을 다시 실행한다.
- remote: 마지막 검증된 version으로 rollback하고 admin-disabled/config/secret을 재확인한다.
- 어느 롤백도 raw 질문 복구나 deleted text 복원을 시도하지 않는다.

## 17. 인간/AI 책임

### 인간이 알아야 하는 내용

- 공개 계약 major bump, 외부 provider 전송, DB reset/seed, remote 시민 배포가 승인 범위다.
- 인증 없는 public admin은 승인에 포함하지 않고 계속 차단한다.
- 실제 신청 처리 시스템이 아니며 안내·운영센터다.
- remote target/credential이 없으면 배포 자체는 완료할 수 없다.

### AI 내부 구현 세부

- helper 분리, typed enum, fixture 작성, internal query mapping, Web component 분할,
  formatting·lint·test tuning은 이 계약 안에서 자율 처리한다.

## 18. 자체 검토 기록

### Review 1 — 요구·정책·계약 완전성

- Status: PASS — 2026-07-27 KST
- Evidence: 설계 1~3부, D-085~D-092, reported 4 fixtures와 acceptance 대조
- 발견/보정:
  - historical public/remote 금지 문구를 D-092 이후 경계와 구분했다.
  - public 작업 승인이 인증 없는 admin 공개나 real citizen outbound로 확대되지 않도록
    ADR-0026을 추가했다.
  - A-052를 disposable clean DB로 해소하고 product spec 문서 버전을 동기화했다.

### Review 2 — 저장소 구현 가능성·충돌

- Status: PASS — 2026-07-27 KST
- Evidence: exact source paths, 00680/00700 ordering, rollback/pgTAP, version/dependency 검토
- 발견/보정:
  - review capability가 actor ID·role·decision·comment를 모두 받도록 signature를 5개 인자로
    바로잡았다.
  - generated TypeScript 권위가 `packages/shared-contracts/src/generated/api.ts`임을 확인했다.
  - current 9 forward/rollback 뒤 `00680`, 마지막 public property migration `00700` 순서를
    고정하고 기존 migration 불변 원칙과 충돌이 없음을 확인했다.
  - FastAPI `create_app()`가 admin router를 opt-in으로만 include하므로 remote negative gate를
    새 인증 없이 유지할 수 있음을 확인했다.
  - 새 production dependency가 필요하지 않으며 기존 `httpx`, Pydantic, PostgreSQL과 Web
    toolchain으로 구현 가능함을 확인했다.

두 자체 검토 결과 구현을 막는 A/Blocker 또는 계약 모순은 없다. 다음 권위는 이 명세를
구체적 RED/GREEN task로 분해하는 실행계획이다.
