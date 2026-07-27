# apps/api

세종 민원이음의 FastAPI 서비스다. health/readiness, local/private `/api/v1/chat`,
공식 기관 조회 `/api/v1/offices` 수직 흐름과 DB-001 lazy typed repository boundary를 제공한다.

## 현재 동작

- `GET /health`: 외부 의존성을 확인하지 않고 `200 {"status":"ok"}` 반환
- `GET /ready`: local app factory가 DB·설정·required projection을 확인한 경우만 200을 반환하며,
  하나라도 부족하면 503으로 닫힌다. 2026-07-22 dedicated Windows `run_local_api`는 final local DB에서
  `/ready=200`을 확인했다. import-safe 기본 앱은 의도적으로 503이며 public/remote readiness가 아니다.
- `POST /api/v1/chat`: local app factory에서 마스킹→정책 분류→ACTIVE KB 검색→근거 gate→
  구조화 응답/폴백을 수행한다. exact local grounded-chat profile에서만 Upstage 생성을 한 번
  시도하며, 그 외 설정·정책·검증·transport 실패는 공식 TEMPLATE 응답으로 돌아간다.
  import-safe 기본 앱은 의도적으로 503을 반환한다.
- `GET /api/v1/offices`: required `region`과 네 supported `intent`를 받아 기존
  `app_api.list_offices`의 OFFICIAL 기관만 `public_id` 순서로 반환한다. valid no-match는
  `200 {"items":[]}`이고 누락·미지원 query는 값 없는 422다. route는 import-safe 기본 앱에도
  항상 등록되지만 directory dependency가 닫혀 있으므로 `Retry-After: 30`을 가진 safe 503을
  반환한다. local app factory만 기존 repository와 shared readiness probe를 주입한다.
- API 4.0.0-draft는 `PRIVACY_UNRESOLVED`·`CIVIC_SCOPE_GAP`,
  SUCCESS/FOLLOWUP/FALLBACK 판별 union, text-free context v2, SUCCESS의
  `answer_mode=GENERATED|TEMPLATE`, 기관 카드, optional UUID `Idempotency-Key`, strict
  `OfficeListResponse`와 local/private 관리자 성공·오류 envelope를 엄격한 공개 계약으로
  고정한다. import-safe 기본 앱의 `/ready`와 기관 read는 계속 503이다.
- 승인된 chat/admin response와 공통 503은 strict Pydantic v2 경계 모델과 공유 합성 JSON fixture를 함께 소비한다. 숫자·문자열·boolean 간 암묵적 coercion과 스냅샷/디버그 추가 필드를 거부한다.
- 정상 완료와 일반 `Exception` 경로의 HTTP 요청 로그는 서버가 만든 UUID, method, 라우트
  템플릿, status만 JSON 한 줄로 남긴다.
- Uvicorn request-line access log, raw ASGI trace logger, INFO 미만 protocol record와 고정
  WebSocket INFO protocol record는 query·경로·client 정보 노출을 막기 위해 차단한다.
  INFO startup과 일반 error record는 유지하며, 현재 범위 밖인 WebSocket은 실행 명령에서도
  비활성화한다.

관리자 wire/Pydantic 계약과 route/service는 구현됐지만 기본/public 앱에는 router를 등록하지 않아
404를 반환한다. local/private composition이 fixed actor allowlist와 service를 명시적으로 제공할
때만 route가 등록된다.
승인된 local/private 관리자 read capability와 adapter는 local factory에만 연결되며 public
관리자 활성화와 remote DB 사용은 계속 금지한다.
요청 body·query·header·cookie·client IP·응답 본문과 provider payload는 일반 로그에 기록하지
않는다. startup, `/health`, `/ready`는 provider를 호출하지 않는다.

## 로컬 환경변수

`apps/api/.env.example`을 `apps/api/.env`로 복사한다. 비밀 칸은 의도적으로 비어 있으며,
local app factory는 `DATABASE_URL`과 최소 32-byte `CONTEXT_TOKEN_SECRET`만 allowlist로
읽는다. 둘 중 하나라도 없거나 유효하지 않으면 `/ready`, `/api/v1/chat`,
`/api/v1/offices`를 503으로 닫는다.
별도 chat 설정 로더는 exact `upstage`/`solar-pro3`/8초/zero-retry profile과
`UPSTAGE_GROUNDED_CHAT_MODE=true`일 때만 ignored local key를 읽고 optional runtime을 조립한다.
disabled·불완전·서로 충돌하는 profile에서는 real local DB app을 그대로 만들되 TEMPLATE만
사용한다. public/remote/실제 기관 운영 provider 연결은 별도 승인 전까지 금지한다.
전체 순서는 [LLM-003 local grounded chat runbook](../../docs/runbooks/LLM-003-LOCAL-GROUNDED-CHAT.md)을
따른다.

DB-001 `0.5.0-local`의 Docker-backed 검증 gate는 실제 single loopback binding을
reset 전에 먼저 확인하고, 안전할 때만 로컬 DB reset 뒤
`sejong_local_login` password를 매번
새로 만들거나 회전하고, 무시된 `apps/api/.env`의 `DATABASE_URL` 한 줄만 갱신한다.
이때 `.env` 전체 bytes를 읽지만 다른 줄과 provider key는 파싱하지 않고 byte-identical하게
보존하며 값을 출력하지 않는다. 이 계정은 직접 table DML이
아니라 `sejong_backend` capability만 상속한다. `.2` initial 19/3/10 local DB projection은
검증됐고, dedicated Windows application probe도 final DB에서 `/ready=200`을 확인했다. 이 actual
evidence는 public admin, remote DB, deployment 또는 import-safe 기본 앱의 readiness를 활성화하지 않는다.
내부 repository는 schema-qualified fixed capability SQL만 사용하고 native DB diagnostic을
SQLSTATE 기반 고정 domain error로 축약한다.

Q-SEC-003=A/D-046/D-092의 exact 22-signature `00700`은 property-only migration,
matching rollback과 전체 local regression을 통과했다. 이 DB credential과 admin repository는
계속 local/private 전용이며 인증 없는 public admin/API와 public backend DB credential은
비활성이다. remote 시민 경로는 ADR-0026의 configured-target smoke를 별도로 통과해야 한다.

## 로컬 명령

저장소 루트에서 실행한다.

```powershell
.\.tools\uv\uv.exe sync --project apps/api --frozen
.\.tools\uv\uv.exe run --directory apps/api --frozen pytest -q
.\.tools\uv\uv.exe run --directory apps/api --frozen ruff format --check .
.\.tools\uv\uv.exe run --directory apps/api --frozen ruff check .
.\.tools\uv\uv.exe run --directory apps/api --frozen mypy src tests
.\.tools\uv\uv.exe run --project apps/api --frozen python scripts/run_local_api.py
```

API 서버는 저장소 루트의 전용 runner로만 시작한다. 이 runner는 Windows에서 psycopg 호환 event
loop를 Uvicorn보다 먼저 선택하고, 유효한 local 설정이 없으면 서버를 시작하지 않으며,
`127.0.0.1` 단일 worker와 access log 비활성 경계를 고정한다. 다른 포트가 필요할 때만
1024~65535 범위의 정수를 `--port 8123`처럼 전달한다.

OFFICE-API-001 closeout 당시 실제 Docker/Supabase endpoint smoke는 prerequisite 부재로
Pending이었고 injected local integration을 포함한 API 전체 2,043 PASS, DB-only 8 skip,
subtests 5 PASS와 shared contract 90/90 PASS로 경계를 검증했다. PR #15 병합 뒤 최신 main의
read-only local actual smoke는 process-only CSPRNG context secret과 existing allowlisted local
DB 설정을 사용해 `/ready=200`, match `200/count=1`, valid empty `200/count=0`을 PASS했다.
`.env` 복사, record/DSN 출력, purge/reset/seed/write와 provider call은 0이다. broad API
baseline에는 기존 Starlette deprecation warning 1건이 있다.

기관 조회를 롤백할 때는 router, typed service/readiness guard, strict model/shared mapper,
tracked OpenAPI와 generated TypeScript를 함께 이전 상태로 되돌린다. DB migration·seed·공식
데이터 변경은 없으므로 data rollback은 필요 없다.

grounded provider actual 전에는 runbook의 provider-disabled regression을 먼저 통과해야 한다.
actual은 offline 전체 gate 뒤 별도 local 인간 단계이며 Cloud·CI에서 실행하지 않는다.

2026-07-23 final closeout은 API 1,640 PASS, DB-only 8 skip, 기존 Starlette warning 1,
subtests 5, Ruff format/check와 strict Mypy 64 files PASS다. 첫 parallel performance 실행은
`2.007s`로 threshold를 넘었지만 같은 test isolated 3회 `1.07s`/`1.18s`/`1.06s`와 full isolated
suite가 PASS했다. parallel-load artifact로 기록하며 performance code는 바꾸지 않았다. clean
disposable API DB integration 8/8과 root `verify.ps1 -Offline` aggregate도 PASS했다.

`uv.lock`은 저장소에 포함하며, 의존성 변경이 승인된 경우에만 다시 생성한다.

Codex managed sandbox가 사용자 uv cache를 읽지 못하는 경우에만 Git-ignored
`.superpowers/uv-cache`를 `UV_CACHE_DIR`로 지정한다. 일반 개발자 환경의 필수 설정은
아니다.
