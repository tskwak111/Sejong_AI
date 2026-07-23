# 보안·개인정보 구현 기준

source-of-truth인 `docs/source-of-truth/PRIVACY_POLICY.md`를 요약한 엔지니어링 기준이다.

## 데이터 흐름

```text
raw request in memory
→ validate length/type
→ validate optional signed context; invalid/expired becomes no context
→ detect and redact PII
→ only redacted text reaches LLM/provider
→ answer returned
→ text-free event metadata saved
→ only eligible failure stores masked text
→ masked_question only is set to NULL after 30 days; metadata/candidate link remains
```

## 구현 요구

- raw question을 logger arguments, exception context, analytics, trace attributes에 넣지 않는다.
- request body logging middleware를 사용하지 않는다.
- 개발 환경의 print/debug도 같은 규칙을 따른다.
- 마스킹 로직은 공통 모듈로 두고 테스트한다.
- PII 감지 결과 자체도 과도한 민감정보를 만들지 않는다.
- `OUT_OF_SCOPE`는 masked text조차 저장하지 않는다.
- 실패 질문 텍스트 만료 작업은 행 DELETE가 아닌 멱등 NULL 파기이며 `text_purged_at`을 기록한다.
- 백업 복구 후 외부 요청을 받기 전에 만료 텍스트 파기를 재실행한다.
- admin candidate form에서 PII 감지 시 저장 차단 또는 명시적 정정 요구.
- service role key는 backend only.
- CORS는 명시적 origin allowlist.
- 실제 배포 전 인프라 제공사의 자동 로그와 데이터 보관 정책 확인.
- Upstage adapter는 서버 allowlist의 canonical 합성 `T-01`~`T-10`만 허용하고 클라이언트
  `is_test`나 자유 입력을 신뢰하지 않는다.
- 실제 시민·PII·민감정보·public 요청은 Upstage로 보내지 않으며 run/attempt ID에도 개인정보를 넣지 않는다.
- ACTIVE/OFFICIAL KB 최소 청크만 보내고 provider request/response body를 로깅·저장하지 않는다.
- exact `solar-pro3`, max output 1024, concurrency 1, retry 최대 1, run당 실제 outbound attempt
  총 30을 강제하고 cap/장애 시 template/policy fallback으로 전환한다.
- transcript와 15분 context token은 current-tab memory만 사용한다. token은 HMAC 무결성만 제공하므로 free text·PII·URL·공식 사실을 넣지 않고 DB/log/browser storage에 저장하지 않는다.

## Phase 1 환경·로그 구현 경계

- root 환경 예시는 변수값을 섞지 않고 Web/API 서비스별 템플릿 위치만 가리킨다.
- Web 예시는 브라우저 공개 API base URL만 허용하고, API 예시는 민감 필드를 빈 값으로 둔 채
  provider를 기본 비활성화한다. 성공 질문·범위 밖 질문 텍스트 미저장은 설정으로
  끌 수 있는 toggle이 아니라 코드·DB 단계에서 지킬 불변 정책이다.
- 현재 pure ASGI middleware는 request receive channel을 읽거나 재생하지 않는다. HTTP 응답의
  status만 관찰하고 정상 완료와 일반 `Exception` 경로에서 요청당 JSON 한 줄을 남긴다.
  프로세스 중단과 `CancelledError` 같은 `BaseException` 경로는 이 보장에 포함하지 않는다.
- 로그 필드는 서버 생성 UUID request ID, method, FastAPI route template path, status만 허용한다.
  raw path나 query를 사용하지 않으며 미매칭 경로는 `<unmatched>`로 고정한다.
- Uvicorn request-line access logger와 raw ASGI trace logger는 disabled와 propagate 차단을 함께
  적용하고 공식 실행 명령도 `--no-access-log`를 사용한다. `uvicorn.error`의 INFO 미만 protocol
  record와 고정 WebSocket INFO protocol record는 client·query 정보가 포함될 수 있어 버리고,
  INFO startup과 일반 error record는 유지한다. WebSocket은 현재 범위 밖이므로 공식 명령에
  `--ws none`도 강제한다.
- exception record는 고정 메시지로 바꾸고 args·traceback·exception text·stack을 제거한 뒤
  handler로 전달한다. 애플리케이션 예외는 middleware가 삼키지 않고 500 metadata 기록 후
  다시 전달한다.

## 자동 검사와 한계

- `scripts/check_secret_patterns.ps1`은 Git의 tracked+untracked nonignored active 파일을 검사하고
  legacy·cache·build·quarantine·symlink를 제외한다. explicit test path도 지원한다.
- `scripts/check_web_bundle_secrets.mjs`는 build 시 materialize된 `.next/static`과 HTML/RSC만
  검사하고 server-only JavaScript와 cache는 제외한다.
- 두 도구는 일치한 값·파일 내용을 출력하지 않고 경로·rule ID·개수만 출력한다. clean 0,
  leak 1, missing/read/tool error 2 이상이다.
- 이 검사는 알려진 pattern·marker와 byte literal을 찾는 방어선이다. Git history, process
  environment, 인프라 자동 로그, 인코딩·암호화·분할된 비밀, 공급자 측 보관은 별도 검토가
  필요하다. 동적 RSC/HTML live response와 Pages `_next/data/*.json` runtime 경로도 보증하지
  않으므로 WEB-CHAT/DEV-001D에서 live-response sentinel gate를 추가한다. 상세 실행 명령과
  범위는 `SECURITY.md`를 따른다.

## 마스킹 범위

- 주민등록번호, 전화번호, 이메일
- 접수번호, 차량번호
- 계좌/카드, 인증번호
- 이름과 상세 주소: 재현율 우선 보수적 마스킹; 불확실하면 외부 호출 없이 안전 폴백
- 민감 복지·건강 문구: 외부 provider 전송 금지

## 인간 승인 필요

- 마스킹 범위 축소
- 보관기간 변경
- 외부 LLM 실제 시민/공개 사용으로 범위 확대
- Upstage model/call cap 변경, actual 시민 연결과 잔액 추가 충전
- context token TTL·claim allowlist·저장 경계 변경
- admin public exposure
- RLS/auth 방식
- 실제 사용자 데이터 테스트

## DB-001 local baseline과 공개 차단

- 8개 업무 table은 비노출 `app_private`에 있고 forced RLS·owner-only policy가 적용된다.
- `PUBLIC`, browser role, backend capability role의 base-table 직접 권한은 0이다.
- backend login은 ignored `apps/api/.env`의 `DATABASE_URL`로만 관리하고 DB gate가 매 실행
  password를 회전한다. 관리자 DSN은 process environment에서만 사용하고 출력하지 않는다.
- 30일 파기는 DELETE가 아닌 멱등 NULL update이며 backup restore 뒤 서비스 개방 전에
  재실행해야 한다.
- local stack의 기본 개발 credential, TLS/rate-limit 부재를 전제로 runner가 actual single
  `127.0.0.1:54322`를 검증한 경우에만 사용한다. Docker/PostgreSQL port를 외부 interface에
  공개하거나 public credential로 재사용하지 않는다. Q-SEC-004=A와 Q-SEC-005=A의 두 보정도
  actual `127.0.0.1`+`::`로 판정됐다. Q-SEC-006=A/D-031의 project-local patched CLI는 source
  manifest `c293e5ac32bae030eadf383d8d9511dc16eac834e51e996273ae8b7e39616657`, patch
  `109c096480e8185d761e9ce8fba10e93efc55190c42eab978f769a6993833f7d`, runtime
  `751068e73834c5da58ac7c5287a1d66a82ad356f508637b0478d6531cdb3941c`로 고정됐다. 2026-07-18
  actual inspect는 두 Docker port view 모두 exact one `127.0.0.1:54322`였고 종료 뒤 project/all
  container는 0/0이었다. volume delete·prune은 0회다.
- 이 성공은 disposable local/private DB gate다. 개발 credential, production TLS/rate limit,
  공개 admin 보호와 원격 credential 안전성을 증명하지 않는다.
- `73f300b`는 DB child process tree를 bounded timeout으로 관리하고 descendant 종료·dispose를
  mutation tests로 고정했다. 명령 argument·child output·credential은 여전히 parent 출력에 노출하지 않는다.
- A-021 감사에서 privileged execution graph 22개 중 `00600` validator만 exact
  `search_path=pg_catalog, pg_temp`로 보정됐고 21개는 public hardening 미완료다.
  Q-SEC-003=A/D-046으로 `00700` property migration 방향은 확정했지만 public 준비까지 구현을
  보류한다. migration·compensation·전체 regression 전에는 remote/public 배포, public admin/API,
  public backend DB credential을 차단한다.
