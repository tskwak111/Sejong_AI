# 테스트 전략

## 테스트 피라미드

### Unit

- 보수적 PII redaction patterns와 불확실 입력의 외부 호출 차단
- AI-001A frozen synthetic v1 74건의 exact 전체 문자열 oracle: 13개 범주, Unicode 10건,
  overlap 5건, negative 20건, Q-PII-003=A와 separator/context bypass를 함께 검증
- AI-001A 직접 category-gap 회귀 254건과 전체 privacy 1,161건: 실제형 77건은 원문
  fail-open 0(75건 마스킹·이름 모호성 2건 fail-closed), safe 219회는 오탐 0
- 독립 누적 변형 gate: 위험값 insertion 6,272건, Unicode 1,940건, separator 252건에서
  raw fail-open 0; final source SHA-256을 리뷰 전후 비교해 검증 중 소스 변경 0도 확인
- PII 마스커의 입력 1~1000자·NFKC/zero-width/control/bidi 경계, 불변 value-free finding,
  deterministic span 선택, 모호 이름·주소와 미분류 잔여 패턴의 `masked_text=None` fail-closed
- intent/followup/fallback policy
- candidate eligibility
- ACTIVE-only retrieval
- source metadata attachment
- approval guard
- retention expiration
- context token sign/verify, exact 900-second TTL, closed claims, current request precedence
- Upstage synthetic evaluator outbound cap/retry/concurrency state machine

### Contract

- OpenAPI request/response validation
- JSON Schema for chat/KB/event
- FE generated types vs API
- enum and error code compatibility
- 200 ChatResponse의 SYSTEM_ERROR 거부와 503 SERVICE_UNAVAILABLE exact envelope
- `session_id` 거부, context token required/nullability, FALLBACK-null invariant의 OpenAPI/JSON Schema 동일 fixture

### Integration

- Postgres transaction for approval→ACTIVE KB
- event without question text
- failed question storage policy
- Upstage exact `T-01`~`T-10` server fixture allowlist와 자유 입력 차단
- AI-001 consumer activation 시 provider/DB-writer spy로 raw sentinel 전달 0건,
  unresolved 결과의 provider 호출 0건과 질문-text row 생성 0건을 함께 검증
- provider timeout/empty/schema invalid의 200 안전 대체 또는 503 분기
- Upstage exact `solar-pro3`/max 1024, hidden retry off, concurrency 1, run cap 28/29/30 경계
- tampered/expired/unknown context token의 silent new-conversation 처리와 token/secret DB·로그 0건
- Supabase empty DB reset/replay와 명시적 보상 rollback/replay
- office mapping

DB-001 local baseline은 다음 영구 gate를 요구한다.

- pgTAP 6 files / 282 assertions
- real backend integration 8/8, DB URL 부재 환경 exact 8 skips(`local DB gate only`)
- 006-only compensation posture와 이전 5 files / 274 assertions 보존
- full compensation `006→005→004→003→002→001`, absence proof, reset/replay,
  두 번째 pgTAP/integration
- 두 연결 사유 확인·후보·승인 concurrency와 30일 purge 경계/멱등성
- synthetic fixture cleanup 뒤 8 table group row 합계 0
- tooling `LocalDatabaseToolingContractTests` 전체, Ruff/Mypy, root/Web/API/contract/secret/package/diff gate
- no-seed `/health=200`, `/ready=503`

과거 DB 증거만으로는 disposable local/private PostgreSQL 기준선 완료를 주장하지 않는다.
2026-07-18 fresh run은 patched `-VerifyOnly` 10.033s, full disposable DB gate 90.508s, exact one
`127.0.0.1:54322`, 두 pgTAP phase exit 0(현재 6 files/282), backend integration 8/8, 6개
compensation/absence/reset/replay, final container 0/0을 증명했다. 이어 root gate 956.658s,
package·secret·protected diff, combined patched/runner tooling 73/73가 모두 PASS했다. 이 결과는
공개 운영의 보안·용량·백업·TLS·rate limit을 증명하지 않고 A-021 해결 전 public release 근거로
사용하지 않는다.

`73f300b` remediation은 focused descendant cleanup 1/1(15.700s), full runner 50/50(318.556s),
patched tooling 24/24(262.368s), AST error 0·secret·protected gate와 독립 review 0/0/0을 통과했다.
이 code HEAD의 actual DB runner도 102.746s에 PASS해 exact loopback과 final container 0/0을 재확인했다.

### E2E

- 정상 답변과 출처
- 모호 질문 FOLLOWUP
- PERSONAL_LOOKUP
- 지역·기관 카드
- 관리자 후보 작성/자기승인 차단/승인
- REG-01 개선 전후
- `/`의 4개 지원 분야·서비스 한계·`/chat` 진입
- current-tab transcript 연속성, 새로고침 후 소멸, 503 재시도·중복 전송 방지, empty office, rejected 후보 재작성

### Non-functional

- 390px/430px, 200% zoom
- keyboard focus and modal return
- contrast 4.5:1
- average/p95/error rate
- 100 virtual users, 1 minute, cached/fixed response path

## 표본과 회귀

- `data/evaluation/`의 20개 표본을 자동 또는 반자동 실행
- 결과는 전체 민원 정확도가 아니라 MVP 표본 결과
- `REG-01`은 별도 상태 변화 테스트

## 테스트 증거

각 구현 노트에 다음을 기록한다.

- 정확한 명령
- 통과/실패 개수
- 실행시간
- 실패 로그의 안전한 요약
- 화면 검증 이미지/경로
- 미실행 항목과 이유

## 금지

- 테스트를 통과시키려고 공식 데이터 값을 임의로 변경
- mock과 공식 결과를 같은 KPI로 합산
- LLM 랜덤 결과를 고정 정답처럼 과장
- 원문 PII를 fixture로 사용
- 클라이언트 `is_test` 값만 믿고 외부 provider를 호출
- context token을 인증·공식 사실로 신뢰하거나 브라우저 storage/로그에 보관
- frozen PII oracle을 구현에 맞춰 삭제·완화하거나 실제 개인정보·공식 연락처를 fixture에 사용
