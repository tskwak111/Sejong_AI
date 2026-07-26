# 시스템 아키텍처 기준

## 1. 권장 물리 구조

```text
Browser
  ├─ /, /chat, /admin — Next.js
  ├─ current-tab transcript + opaque 15-minute context token
  └─ HTTPS JSON
        ↓
FastAPI /api/v1
  ├─ input validation
  ├─ PII redaction
  ├─ intent/followup/fallback policy
  ├─ retrieval
  ├─ provider adapter
  ├─ response validation
  ├─ source metadata attachment
  ├─ event logging
  └─ admin workflow
        ↓
Supabase PostgreSQL
  ├─ ACTIVE KB and source metadata
  ├─ official offices/mappings
  ├─ interaction events without question text
  ├─ masked failed questions
  ├─ candidates and approval states
  └─ minimal audit events
```

## 2. 모노레포 권장 구조

```text
apps/web       Next.js
apps/api       FastAPI
packages/shared-contracts  generated/shared types
contracts      OpenAPI and JSON Schema source
supabase/migrations  timestamp-ordered executable DB authority
database       logical projection, reverse-order local compensation, absence proof
data           official/evaluation/mock separated
docs           source-of-truth, ADR, notes, reports
scripts        reproducible project tooling
```

기존 스타터는 `legacy/`로 유지한다. 신규 앱 스캐폴딩 전 Codex가 패키지 관리자, 런타임 버전, 마이그레이션 도구, CI 환경을 인터뷰한다.

## 3. Chat 처리 경계

1. 요청 검증과 길이 제한
2. optional context token의 서명·TTL·closed claim 검증; 실패하면 문맥 없음으로 계속
3. 서버 내부 PII 탐지·마스킹
4. 지원 범위/모호성/개인 조회/법적 판단 사전 규칙
5. ACTIVE KB 검색
6. 근거 충족 판단
7. 근거가 있으면 provider adapter 또는 템플릿으로 구조화 답변
8. JSON Schema 검증
9. 서버가 source_id로 출처 메타데이터 결합
10. 텍스트 없는 interaction event 저장
11. 필요한 경우 masked failed question 저장
12. SUCCESS/FOLLOWUP에만 새 구조화 context token 발급 가능; FALLBACK은 null

## 4. LLM adapter

합성 평가 공급자와 D-072/D-073가 승인한 local/private 시민 chat 목표 모델은 정확히 Upstage
`solar-pro3`로 고정한다. 합성 평가 경로는 max output 1024, concurrency 1, 논리 요청당 재시도
최대 1회, process outbound attempt 30이고 actual은 D-071에서 FAIL로 종료했다. 후속 시민 chat
경로는 timeout 8초, logical attempt 1회, hidden retry 0, concurrency 1, process cap 30이다.
도메인 서비스가 공급자 API에 직접 의존하지 않도록 provider-neutral interface를 사용한다.
현재 product runtime은 아직 deterministic template이며
[승인 대기 실행계획](superpowers/plans/2026-07-25-grounded-live-chat-generation.md) 승인 뒤에만
아래 좁은 interface를 구현한다.

```python
class GroundedAnswerGenerator(Protocol):
    async def generate(self, request: GroundedChatRequest) -> GroundedChatResult: ...
```

요구사항:

- 입력은 마스킹된 질문과 실제 답변에 필요한 최소 ACTIVE/OFFICIAL KB fact만
- 시민 입력은 supported intent·안전 마스킹·ACTIVE/OFFICIAL·grounding을 모두 통과한
  local/private 요청만; public/remote/실제 기관 운영은 disabled/template
- 출력은 최대 500자 summary와 server-issued fact ID뿐이며 strict schema와 사실 drift 검증
- timeout 8초, attempt 1, hidden retry 0, concurrency 1, process cap 30
- 공급자 장애 시 KB 템플릿 또는 안전 폴백
- 공급자 이름/모델/latency는 관측 가능하되 질문 텍스트 로그 금지
- source/office/policy/공식 fact text는 서버가 결합
- provider disabled 기본, synthetic/chat mode 상호 배타; preflight provider call·cap reset
  endpoint 금지

## 4.1 대화 문맥 경계

- transcript와 token은 현재 브라우저 탭 메모리에만 두고 새로고침 시 폐기한다.
- 서버 session/chat table을 만들지 않고 token·질문·답변을 DB/로그/analytics에 저장하지 않는다.
- HMAC-SHA-256 token은 암호화가 아니므로 version, enum, 서버 정의 option ID, `iat`/`exp` 외 claim을 금지한다.
- token은 인증·권한·공식 사실이 아니며 현재 요청의 안전 분류, ACTIVE KB 검색, source 결합을 매번 재실행한다.

## 5. 검색 전략

KB 20건에서는 키워드·메타데이터·question_examples를 기본으로 한다. 임베딩은 보조 점수이며, 공급자/차원에 DB를 영구 결합하지 않도록 adapter를 둔다.

초기 권장 흐름:

```text
intent filter
→ exact/keyword aliases
→ metadata/service match
→ optional embedding rerank (MVP flag off)
→ evidence threshold
```

근거 충족 기준은 코드와 테스트에서 명시해야 하며 단순 LLM 자신감 점수로 판단하지 않는다.

## 6. 관리자 승인 흐름

```text
NEW
→ REASON_CONFIRMED
→ DRAFTED
→ PENDING_APPROVAL
→ APPROVED | REJECTED
→ APPROVED transaction creates/activates KB
```

- created_by != reviewed_by
- 운영자 역할은 approve 불가
- 승인 트랜잭션과 ACTIVE 생성은 원자적
- 후보 답변/출처는 사람 입력
- audit는 action/status/field names만

## 7. 장애 전략

- LLM 실패 + KB 충분: 서버 템플릿 답변
- LLM 실패 + KB 부족: 정책 근거 부족 폴백 200; 필수 분류·검색·응답 조립과 안전 대체까지 불능일 때만 503
- DB 실패: 질문 원문을 파일/큐에 임시 저장하지 않음
- source metadata 불일치: 직접 답변 차단
- 배포 장애: 로컬 seed/고정 데모 경로; 공개 URL·녹화본은 별도 발표/배포 승인 항목

## 8. DB-001 local/private 경계

- `app_private`에는 7 enum과 8 업무 table을 두고 Data API 노출 schema에서 제외한다.
- 브라우저·`PUBLIC`·`anon`·`authenticated`는 업무 table에 직접 접근하지 않는다.
- `sejong_backend`는 NOLOGIN capability role이며 base-table DML 대신 검토된 `app_api`
  함수만 실행한다. FastAPI repository도 고정 SQL 9개만 사용한다.
- RLS는 8 table 모두 ENABLE+FORCE이고 owner-only policy를 사용한다.
- 시민 read는 `ACTIVE + OFFICIAL` KB와 `OFFICIAL` 기관만 반환한다.
- executable authority는 forward migration 6개이며 disposable-local compensation은
  `00600 → 00500 → 00400 → 00300 → 00200 → 00100`이다.
- `database/schema-v1.draft.sql`은 검증된 `0.3.0-local`의 읽기 전용 논리 투영이며 권한·함수·trigger
  실행 근거가 아니다.
- tracked source manifest와 runtime manifest는 build input과 binary authority를 분리한다. runner는
  `.tools/supabase/v2.109.1-sejong-loopback/supabase.exe`만 허용하고 stock/PATH fallback을 두지 않는다.
- 2026-07-18 actual gate는 정확히 하나의 `127.0.0.1:54322 -> 5432/tcp`, fresh pgTAP 282,
  backend integration 8/8, 6단계 compensation/absence/reset/replay와 final container 0/0을 증명했다.
  이로써 manifest `database_schema=0.3.0-local`은 disposable local/private 기준선으로 활성화됐다.
- `73f300b`는 DB child와 descendant를 bounded process tree로 실행해 timeout/failure/success 모두에서
  종료·dispose·환경 복원을 보장한다. runner 50/50, patched 24/24와 final-code DB gate가 재검증했다.
- Q-SEC-003=A/D-046/D-092의 exact 22 signature property-only `00700`은 matching
  rollback·body/owner/ACL fingerprint·전체 local regression을 통과했다. 이는 remote 배포
  완료가 아니며, 인증 없는 public admin/API와 public backend DB credential은 계속 차단한다.
