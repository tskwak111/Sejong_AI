# ADR-0010: 서버 세션 없는 서명형 client-carried 대화 문맥

- Status: Accepted
- Date: 2026-07-14 (Q-CHAT-001)

## Context

채팅처럼 보이는 화면 연속성은 필요하지만 원문 질문·답변을 서버 세션이나 DB에 보관하면 개인정보 최소수집 원칙과 운영 복잡도가 커진다. 기존 draft의 의미가 정의되지 않은 `session_id`는 서버 저장·보관·삭제·인증 오해를 만든다.

## Decision

- 화면 transcript와 현재 문맥 token은 브라우저의 현재 탭 메모리에만 둔다. `localStorage`, `sessionStorage`, IndexedDB, cookie, Cache API, URL/query string에 저장하지 않으며 새로고침·탭 종료 시 사라진다.
- 서버에는 raw transcript와 chat/session row를 만들지 않는다. 요청·응답 전문과 token을 DB, analytics, access/error/audit log에 저장하지 않는다.
- `/api/v1/chat`은 optional nullable `context_token`을 받고, HTTP 200 `ChatResponse`는 required nullable `context_token`을 반환한다. 토큰 TTL은 15분이다. `SUCCESS`와 `FOLLOWUP`은 새 token을 발급할 수 있고 `FALLBACK`은 항상 `null`이다.
- token은 클라이언트가 해석하지 않는 versioned opaque value다. 서버는 Python 표준 라이브러리 HMAC-SHA-256과 최소 32 random bytes의 server-only `CONTEXT_TOKEN_SECRET`로 무결성을 검증한다. HMAC은 암호화가 아니므로 payload에는 허용된 closed claim만 둔다: version, intent enum, selected region enum, optional server-defined follow-up option ID, last answer status enum, issued-at, expiry. 자유 텍스트, 질문·답변, source title/URL, KB 본문, actor/user ID, PII, provider 데이터, 비밀은 금지한다.
- 만료, 서명 불일치, 알 수 없는 version/claim, future `iat`는 401/403/500이나 상세 오류를 만들지 않고 문맥 없는 새 요청처럼 처리한다. token 최대 길이는 2048자이며 이를 넘는 일반 schema 오류는 422가 가능하다.
- 현재 요청의 명시적 `selected_region`은 token claim보다 우선한다. token은 힌트일 뿐 인증·권한·개인 조회·쓰기 작업·ACTIVE KB 필터·공식 사실·근거 검증을 대신하지 않는다.
- secret 회전은 현재/직전 secret만 최대 TTL 동안 검증할 수 있다. 긴급 롤백은 새 token 발급 중단과 secret 교체로 기존 token을 최대 15분 안에 무효화한다.

### 2026-07-27 context v2 amendment

D-089/D-090의 자연스러운 구조화 대화 설계는 기존 원칙을 보존하면서 claim allowlist를
확장한다.

- v2는 기존 claim에 optional server-issued `topic_id`, closed `pending_slot`, closed
  `dialog_act`를 추가할 수 있다.
- `pending_slot` 초기 allowlist는 `CERTIFICATE_KIND`, `REGION`, `WASTE_ITEM`이다.
- `dialog_act`는 `ANSWERED`, `ASKING_SLOT`, `CHANGING_REGION`, `CHANGING_TOPIC`이다.
- `topic_id`는 문맥 hint일 뿐 authority가 아니다. 서버는 매 요청에서 해당 주제가 현재
  ACTIVE/OFFICIAL인지 다시 검증한다.
- 질문·답변 문장, 시민 프로필, source/KB 본문과 임의 model text는 계속 금지한다.
- v2 전환 시 reader는 기존 v1을 남은 최대 TTL 동안 minimal context로 읽을 수 있고 issuer는
  v2만 발급한다. 이후 v1은 silent no-context로 닫힌다.
- Web은 current-tab transcript 경계를 유지하면서 명시적 `새 대화` control로 transcript와
  context token을 함께 초기화한다.

exact serialized claim names/length와 Web/API tests는 written specification에서 고정한다.

## Public contract and versioning

`ChatRequest.session_id`를 제거하고 `context_token`을 추가하며, `ChatResponse`에 required nullable `context_token`과 FALLBACK-null 불변조건을 추가한다. 이는 공개 draft의 breaking change이므로 `contracts/AGENTS.md`에 따라 API spec revision을 `1.0.0-draft`에서 `2.0.0-draft`로 올린다. 아직 구현·외부 소비자가 없으므로 route namespace `/api/v1/chat`은 유지한다.

## Consequences and verification

서버 transcript 보관·삭제·세션 cleanup이 사라지고 브라우저 새로고침 시 대화가 사라지는 대신, 최소 구조화 문맥으로 후속질문의 챗봇 느낌을 제공한다. 토큰은 재생 가능하므로 권한 용도로 절대 사용하지 않는다.

계약·보안 테스트는 `session_id` 거부, token 누락/null 첫 요청, 정확한 900초 TTL, claim allowlist, tamper/expiry silent reset, 현재 request region 우선, FALLBACK null, token/secret의 DB·로그 0건, decoded payload의 질문·답변·URL·PII 0건, v1 read-only→v2 issue와 새로고침/새 대화 후 소멸을 검증한다. 표준 라이브러리만 사용하므로 이 결정 자체는 새 production dependency를 추가하지 않는다.
