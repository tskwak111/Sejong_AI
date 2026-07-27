# IMP-20260727-019 — local backend DB 비밀번호 불일치 진단

- Date/Time (KST): 2026-07-27
- Task ID: LOCAL-DB-AUTH-001
- Type: diagnostic-guidance
- Status: Done
- Author/Agent: 사용자 local 실행자 / Codex
- Branch: codex/ACTUAL-P0-UX-GAPS-001
- Base commit: d226f9d
- Related: DB-001, READY-001, ADR-0018, LOCAL-RUN-GUIDE-001

## 1. 사용자 요청과 완료 기준

- 요청: `sejong_local_login` password authentication failure의 원인과 복구 방법을 확인한다.
- 완료 기준: DB 장애와 credential drift를 구분하고 비밀값 없이 최소 복구 명령을 제공한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who | 사용자 local 실행자, Codex 진단자 |
| When | local API 시작이 두 번 같은 인증 오류로 종료된 직후 |
| Where | loopback PostgreSQL `127.0.0.1:54322`, ignored `apps/api/.env` |
| What | backend login credential 불일치 |
| Why | DB는 정상이나 API용 role 인증만 실패 |
| How | port/status/presence 확인 후 관리자·backend 연결을 content-free probe로 비교 |
| How much | read-only 연결 2회, DB/file write 0 |

## 3. 시작 전 상태와 실제 증거

- primary `main`은 `origin/main`보다 1 commit 뒤이며 PR #18 merge를 아직 pull하지 않았다.
- `apps/web/next-env.d.ts`에는 Next dev generated 1줄 변경이 있다.
- port 54322 LISTENING, port 8000 FREE.
- patched Supabase status exit 0.
- ignored `.env`의 `DATABASE_URL` assignment는 정확히 1개.
- content-free connection probe:
  - `ADMIN_CONNECTION=OK`
  - `BACKEND_CONNECTION=FAILED`

## 4. 원인

DB 또는 container 장애가 아니다. local PostgreSQL 관리자 credential은 유효하지만
`sejong_local_login` role의 현재 password와 ignored `.env`의 `DATABASE_URL` password가 다르다.
API pool은 이 stale DSN을 사용하므로 startup readiness 전에 인증 실패한다.

## 5. 선택한 복구

- `provision_local_database_login.py`를 사용한다.
- Supabase status의 admin DB URL은 PowerShell process environment에만 둔다.
- provisioner는 role 상태·membership을 검증하고 password를 회전한 뒤 `.env`의
  `DATABASE_URL` 한 줄만 원자 갱신한다.
- reset, seed, migration, ACTIVE row 변경은 하지 않는다.

## 6. 사용자 실행 명령

먼저 merge된 main을 받는다.

```powershell
git restore -- apps/web/next-env.d.ts
git pull --ff-only origin main
```

그다음 password와 `.env`를 동기화한다.

```powershell
$supabase = ".\.tools\supabase\v2.109.1-sejong-loopback\supabase.exe"
$status = (& $supabase status --output json 2>$null | ConvertFrom-Json)
$env:SEJONG_ADMIN_DATABASE_URL = $status.DB_URL
try {
  apps/api/.venv/Scripts/python.exe -B scripts/provision_local_database_login.py
  if ($LASTEXITCODE -ne 0) { throw "LOCAL_DB_LOGIN_PROVISION_FAILED" }
} finally {
  Remove-Item Env:SEJONG_ADMIN_DATABASE_URL -ErrorAction SilentlyContinue
}
```

기대 출력:

```text
[PASS] step=PROVISION-LOCAL-DB-LOGIN
```

그 뒤 API를 다시 시작하고 `/ready=200`을 확인한다.

## 7. 버전 전후

- application/web/api/DB/data/prompt/test/docs version: unchanged.
- 이유: 읽기 전용 진단과 사용자 복구 안내만 수행.

## 8. 테스트·명령 결과

| 검증 | 결과 |
|---|---|
| Git/port/Supabase/env presence | main behind 1, 54322 listening, Supabase OK, DB assignment 1 |
| admin read-only `SELECT 1` | PASS |
| backend read-only `SELECT 1` | FAIL |
| secret/DSN/error body 출력 | 0 |

실제 provisioner는 사용자가 수정 실행을 요청한 것이 아니므로 Codex가 실행하지 않았다.

## 9. 보안·개인정보·데이터 영향

- DSN/password를 console·문서·Git에 출력하지 않았다.
- probe는 `SELECT 1`만 수행했다.
- 복구 명령은 질문/KB/감사/official data를 변경하지 않는다.
- provisioner는 비밀번호와 ignored `DATABASE_URL`만 회전한다.

## 10. 인간이 반드시 알아야 하는 내용

- DB reset·seed를 하면 안 된다. 현재 ACTIVE 20을 보존한다.
- `.env`에 임의 비밀번호를 직접 적지 말고 provisioner를 사용한다.
- provision PASS 뒤 실행 중인 API process가 있다면 완전히 재시작한다.

## 11. AI 내부 구현 세부

- admin/backend 연결 결과만 stable enum으로 출력하고 DSN/error text는 폐기했다.

## 12. 인수인계·롤백

- provision 중 파일 write 실패 시 이전 `.env` bytes가 보존된다. 재실행하면 DB password를 다시
  회전해 동기화할 수 있다.
- 복구 후 API → `/ready` → Web 순서로 실행한다.

## 13. 남은 위험·다음 단계

- 사용자 provision 실행 결과 확인.
- PASS 후 `/ready=200`; 실패 시 stable failure step만 공유하고 DSN은 공유하지 않는다.

## 14. 자체 리뷰

- [x] 원인 재현·경계 비교
- [x] 수정 실행과 진단 분리
- [x] raw secret/DSN 출력 없음
- [x] 버전·데이터 영향 기록
- [x] INDEX 갱신
