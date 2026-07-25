# apps/api

세종 민원이음의 FastAPI 서비스다. health/readiness와 local/private `/api/v1/chat`
수직 흐름, DB-001 lazy typed repository boundary를 제공한다.

## 현재 동작

- `GET /health`: 외부 의존성을 확인하지 않고 `200 {"status":"ok"}` 반환
- `GET /ready`: local app factory가 DB·설정·required projection을 확인한 경우만 200을 반환하며,
  하나라도 부족하면 503으로 닫힌다. 2026-07-22 dedicated Windows `run_local_api`는 final local DB에서
  `/ready=200`을 확인했다. import-safe 기본 앱은 의도적으로 503이며 public/remote readiness가 아니다.
- `POST /api/v1/chat`: local app factory에서 마스킹→정책 분류→ACTIVE KB 검색→근거 gate→
  구조화 응답/폴백을 수행한다. import-safe 기본 앱은 의도적으로 503을 반환한다.
- API 3.1.0-draft는 `PRIVACY_UNRESOLVED`, SUCCESS/FOLLOWUP/FALLBACK 판별 union, SUCCESS 기관 카드, optional UUID `Idempotency-Key`와 local/private 관리자 성공·오류 envelope를 엄격한 공개 계약으로 고정한다. import-safe 기본 앱의 `/ready`는 계속 503이다.
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
실제 local DB용 관리자 read capability와 adapter는 별도 migration 승인 전까지 연결하지 않는다.
실제 외부 LLM 호출도 후속 수직 흐름이다. 요청 body·query·header·cookie·client IP·응답 본문은
일반 로그에 기록하지 않는다.

## 로컬 환경변수

`apps/api/.env.example`을 `apps/api/.env`로 복사한다. 비밀 칸은 의도적으로 비어 있으며,
local app factory는 `DATABASE_URL`과 최소 32-byte `CONTEXT_TOKEN_SECRET`만 allowlist로
읽는다. 둘 중 하나라도 없거나 유효하지 않으면 `/ready`와 `/api/v1/chat`을 503으로 닫는다.
외부 provider는 기본 비활성이고 현재 결정론적 MVP 경로에서 호출하지 않는다. Q-LLM-005=A의
Upstage exact `solar-pro3` adapter/evaluator/runner는 local/private synthetic-only로 구현돼
offline security/architecture review를 통과했지만 실제 key/network/model-quality 평가는 아직
실행하지 않았다. 시민 자유입력·public/remote provider 연결은 별도 승인 전까지 금지한다.

DB-001 `0.4.0-local`의 Docker-backed 검증 gate는 실제 single loopback binding을
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

Q-SEC-003=A/D-046의 `00700` 방향은 확정됐지만 public 준비까지 구현 보류다. 이 DB credential과
repository는 계속 local/private 전용이며 public admin/API, public backend DB credential과
remote/public 배포는 `00700` 전체 검증 전 금지한다.

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

2026-07-23 final closeout은 API 1,640 PASS, DB-only 8 skip, 기존 Starlette warning 1,
subtests 5, Ruff format/check와 strict Mypy 64 files PASS다. 첫 parallel performance 실행은
`2.007s`로 threshold를 넘었지만 같은 test isolated 3회 `1.07s`/`1.18s`/`1.06s`와 full isolated
suite가 PASS했다. parallel-load artifact로 기록하며 performance code는 바꾸지 않았다. clean
disposable API DB integration 8/8과 root `verify.ps1 -Offline` aggregate도 PASS했다.

`uv.lock`은 저장소에 포함하며, 의존성 변경이 승인된 경우에만 다시 생성한다.

Codex managed sandbox가 사용자 uv cache를 읽지 못하는 경우에만 Git-ignored
`.superpowers/uv-cache`를 `UV_CACHE_DIR`로 지정한다. 일반 개발자 환경의 필수 설정은
아니다.
